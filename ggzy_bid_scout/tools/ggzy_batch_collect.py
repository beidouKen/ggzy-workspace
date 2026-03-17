"""
ggzy_batch_collect.py — 全国公共资源交易平台批量采集工具

流程：
  列表页 → 提取 detail_url → 进入详情页 → 保存 JSON

批处理策略：
  - 每批 10 条
  - 原始数据保存 data/raw/
  - 结构化数据保存 data/structured/
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import requests

from tools.ggzy_list_fetch import fetch_pages, FetchConfig, BidListItem
from tools.ggzy_detail_fetch import fetch_detail, DetailResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ggzy_batch_collect")

BATCH_SIZE = 10
BASE_DIR = PROJECT_ROOT / "data"
RAW_DIR = BASE_DIR / "raw"
STRUCTURED_DIR = BASE_DIR / "structured"


def _ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    STRUCTURED_DIR.mkdir(parents=True, exist_ok=True)


def _load_existing_ids(structured_path: Path) -> set[str]:
    """加载已采集的记录 ID 用于去重。"""
    if not structured_path.exists():
        return set()
    try:
        data = json.loads(structured_path.read_text(encoding="utf-8"))
        return {item.get("record_id", "") for item in data.get("items", []) if item.get("record_id")}
    except (json.JSONDecodeError, KeyError):
        return set()


def batch_collect(
    keyword: str = "体育",
    max_pages: int = 5,
    time_range: str = "1m",
    delay_list: float = 1.0,
    delay_detail: float = 1.0,
    output_name: str = "bid_data",
) -> dict:
    """
    批量采集招标信息。

    Args:
        keyword: 搜索关键词
        max_pages: 最大列表页数
        time_range: 时间范围
        delay_list: 列表页间隔（秒）
        delay_detail: 详情页间隔（秒）
        output_name: 输出文件名前缀

    Returns:
        采集统计结果
    """
    _ensure_dirs()

    structured_path = STRUCTURED_DIR / f"{output_name}.json"
    existing_ids = _load_existing_ids(structured_path)
    logger.info("Existing records: %d", len(existing_ids))

    # Phase 1: Collect list data
    logger.info("Phase 1: Fetching list pages (keyword=%s, pages=%d)...", keyword, max_pages)
    config = FetchConfig(keyword=keyword, time_range=time_range)
    list_results = fetch_pages(
        start_page=1, max_pages=max_pages, config=config, delay=delay_list,
    )

    all_list_items: list[BidListItem] = []
    for page_result in list_results:
        for item in page_result.items:
            if item.record_id not in existing_ids:
                all_list_items.append(item)

    total_available = list_results[0].total if list_results else 0
    logger.info(
        "Phase 1 complete: %d new items to process (skipped %d existing, total available: %d)",
        len(all_list_items), len(existing_ids), total_available,
    )

    # Save raw list data
    raw_list_path = RAW_DIR / f"{output_name}_list.json"
    raw_list_data = {
        "fetch_time": datetime.now().isoformat(),
        "keyword": keyword,
        "pages": max_pages,
        "total_available": total_available,
        "items": [asdict(item) for item in all_list_items],
    }
    raw_list_path.write_text(json.dumps(raw_list_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Phase 2: Fetch detail pages in batches
    logger.info("Phase 2: Fetching detail pages...")
    session = requests.Session()
    detail_results: list[dict] = []
    success_count = 0
    fail_count = 0

    for batch_start in range(0, len(all_list_items), BATCH_SIZE):
        batch = all_list_items[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        logger.info(
            "Batch %d: processing items %d-%d of %d",
            batch_num, batch_start + 1, batch_start + len(batch), len(all_list_items),
        )

        for i, list_item in enumerate(batch):
            try:
                detail = fetch_detail(list_item.detail_url, session=session)
                detail.region = list_item.region or detail.region

                detail_dict = asdict(detail)
                detail_dict["record_id"] = list_item.record_id
                detail_dict["business_type"] = list_item.business_type
                detail_dict["info_type"] = list_item.info_type
                detail_dict["attachments"] = [
                    {"name": a.name, "url": a.url} for a in detail.attachments
                ]
                detail_results.append(detail_dict)
                success_count += 1

            except Exception as exc:
                logger.warning(
                    "Failed to fetch detail for %s: %s",
                    list_item.detail_url[:60], exc,
                )
                detail_results.append({
                    "title": list_item.title,
                    "publish_date": list_item.publish_date,
                    "region": list_item.region,
                    "detail_url": list_item.detail_url,
                    "record_id": list_item.record_id,
                    "business_type": list_item.business_type,
                    "info_type": list_item.info_type,
                    "error": str(exc),
                })
                fail_count += 1

            if i < len(batch) - 1:
                time.sleep(delay_detail)

        # Save intermediate raw data after each batch
        raw_batch_path = RAW_DIR / f"{output_name}_batch_{batch_num}.json"
        raw_batch_path.write_text(
            json.dumps(detail_results[-len(batch):], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Batch %d saved: %s", batch_num, raw_batch_path.name)

        if batch_start + BATCH_SIZE < len(all_list_items):
            time.sleep(delay_list)

    # Phase 3: Save structured output
    logger.info("Phase 3: Saving structured data...")

    # Merge with existing data
    if structured_path.exists():
        try:
            existing_data = json.loads(structured_path.read_text(encoding="utf-8"))
            existing_items = existing_data.get("items", [])
        except (json.JSONDecodeError, KeyError):
            existing_items = []
    else:
        existing_items = []

    all_items = existing_items + detail_results

    # Deduplicate by record_id
    seen_ids: set[str] = set()
    unique_items: list[dict] = []
    for item in all_items:
        rid = item.get("record_id", "")
        if rid and rid in seen_ids:
            continue
        seen_ids.add(rid)
        unique_items.append(item)

    dup_count = len(all_items) - len(unique_items)

    structured_output = {
        "meta": {
            "keyword": keyword,
            "last_fetch_time": datetime.now().isoformat(),
            "total_items": len(unique_items),
            "total_available": total_available,
            "pages_fetched": max_pages,
        },
        "items": unique_items,
    }

    structured_path.write_text(
        json.dumps(structured_output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Structured data saved: %s (%d items)", structured_path, len(unique_items))

    stats = {
        "keyword": keyword,
        "pages_fetched": len(list_results),
        "total_available": total_available,
        "items_processed": len(all_list_items),
        "success": success_count,
        "fail": fail_count,
        "duplicates_removed": dup_count,
        "total_stored": len(unique_items),
        "success_rate": success_count / len(all_list_items) * 100 if all_list_items else 0,
    }

    logger.info(
        "Batch collect complete: %d/%d success (%.1f%%), %d total stored, %d duplicates removed",
        success_count, len(all_list_items), stats["success_rate"],
        len(unique_items), dup_count,
    )

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="ggzy.gov.cn batch bid collector")
    parser.add_argument("--keyword", default="体育", help="Search keyword")
    parser.add_argument("--pages", type=int, default=5, help="Max list pages to fetch")
    parser.add_argument("--time-range", default="1m", help="Time range: today/3d/10d/1m/6m")
    parser.add_argument("--delay-list", type=float, default=1.0, help="Delay between list pages (sec)")
    parser.add_argument("--delay-detail", type=float, default=1.0, help="Delay between detail pages (sec)")
    parser.add_argument("--output", default="bid_data", help="Output file name prefix")
    parser.add_argument("--no-report", action="store_true", help="Skip report generation")
    args = parser.parse_args()

    stats = batch_collect(
        keyword=args.keyword,
        max_pages=args.pages,
        time_range=args.time_range,
        delay_list=args.delay_list,
        delay_detail=args.delay_detail,
        output_name=args.output,
    )

    print(f"\n{'='*60}")
    print("Batch Collection Summary")
    print(f"{'='*60}")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    if not args.no_report and stats.get("total_stored", 0) > 0:
        try:
            from tools.export_report import export_all
            report_name = "bid_report"
            report_result = export_all(input_name=args.output, output_name=report_name)
            print(f"\n{'='*60}")
            print("Report Generation")
            print(f"{'='*60}")
            for k, v in report_result.items():
                print(f"  {k}: {v}")
        except Exception as exc:
            logger.warning("Report generation failed: %s", exc)


if __name__ == "__main__":
    main()
