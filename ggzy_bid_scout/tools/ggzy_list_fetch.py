"""
ggzy_list_fetch.py — 全国公共资源交易平台（ggzy.gov.cn）列表页采集工具

功能：
  1. 通过 API 查询交易公告列表
  2. 支持关键词、省份、时间范围筛选
  3. 支持翻页采集
  4. 返回结构化 JSON 数据

API 端点：POST https://www.ggzy.gov.cn/information/pubTradingInfo/getTradList
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

BASE_URL = "https://www.ggzy.gov.cn"
API_URL = f"{BASE_URL}/information/pubTradingInfo/getTradList"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": f"{BASE_URL}/deal/dealList.html",
    "Origin": BASE_URL,
}

DEAL_TIME_MAP = {
    "today": "01",
    "3d": "02",
    "10d": "03",
    "1m": "04",
    "6m": "05",
    "custom": "06",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ggzy_list_fetch")


@dataclass
class BidListItem:
    """列表页单条记录的结构化表示。"""
    title: str
    publish_date: str
    region: str
    platform: str
    detail_url: str
    business_type: str = ""
    info_type: str = ""
    record_id: str = ""


@dataclass
class PageResult:
    """单页采集结果。"""
    page: int
    total: int
    total_pages: int
    page_size: int
    items: list[BidListItem]


@dataclass
class FetchConfig:
    """采集配置。"""
    keyword: str = "体育"
    time_range: str = "1m"
    begin_date: str = ""
    end_date: str = ""
    source_type: str = "1"
    timeout: int = 15
    retry_count: int = 3
    retry_delay: float = 2.0


def _compute_date_range(time_range: str) -> tuple[str, str]:
    """根据 time_range 代码计算日期区间。"""
    now = datetime.now()
    end_date = now.strftime("%Y-%m-%d")

    offset_days = {
        "today": 0,
        "3d": 3,
        "10d": 10,
        "1m": 30,
        "6m": 180,
    }
    days = offset_days.get(time_range, 30)
    begin_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    return begin_date, end_date


def _build_form_data(
    config: FetchConfig,
    page: int,
    begin_date: str,
    end_date: str,
) -> dict[str, str]:
    """构建 API 请求的 form data。"""
    deal_time = DEAL_TIME_MAP.get(config.time_range, "04")
    return {
        "TIMEBEGIN_SHOW": begin_date,
        "TIMEEND_SHOW": end_date,
        "TIMEBEGIN": begin_date,
        "TIMEEND": end_date,
        "SOURCE_TYPE": config.source_type,
        "DEAL_TIME": deal_time,
        "isShowAll": "1",
        "PAGENUMBER": str(page),
        "FINDTXT": config.keyword,
    }


def _parse_record(raw: dict[str, Any]) -> BidListItem:
    """将 API 返回的原始记录转换为结构化对象。"""
    url_path = raw.get("url") or ""
    detail_url = f"{BASE_URL}{url_path}" if url_path else ""

    return BidListItem(
        title=raw.get("title") or "",
        publish_date=raw.get("publishTime") or "",
        region=raw.get("provinceText") or "",
        platform=raw.get("transactionSourcesPlatformText") or "",
        detail_url=detail_url,
        business_type=raw.get("businessTypeText") or "",
        info_type=raw.get("informationTypeText") or "",
        record_id=raw.get("id") or "",
    )


def fetch_page(
    page: int = 1,
    config: FetchConfig | None = None,
    session: requests.Session | None = None,
) -> PageResult:
    """
    采集指定页的列表数据。

    Args:
        page: 页码（从 1 开始）
        config: 采集配置
        session: requests 会话（可复用连接）

    Returns:
        PageResult 包含当前页所有记录

    Raises:
        RuntimeError: API 请求失败或响应异常
    """
    if config is None:
        config = FetchConfig()

    if config.begin_date and config.end_date:
        begin_date, end_date = config.begin_date, config.end_date
    else:
        begin_date, end_date = _compute_date_range(config.time_range)

    form_data = _build_form_data(config, page, begin_date, end_date)
    http = session or requests.Session()
    http.headers.update(DEFAULT_HEADERS)

    last_error: Exception | None = None
    for attempt in range(1, config.retry_count + 1):
        try:
            resp = http.post(API_URL, data=form_data, timeout=config.timeout)
            resp.raise_for_status()

            body = resp.json()
            if body.get("code") != 200:
                raise RuntimeError(
                    f"API returned code={body.get('code')}, message={body.get('message')}"
                )

            data = body.get("data", {})
            records = data.get("records", [])
            items = [_parse_record(r) for r in records]

            result = PageResult(
                page=int(data.get("current", page)),
                total=int(data.get("total", 0)),
                total_pages=int(data.get("pages", 0)),
                page_size=int(data.get("size", 20)),
                items=items,
            )
            logger.info(
                "Page %d: %d items (total=%d, pages=%d)",
                page, len(items), result.total, result.total_pages,
            )
            return result

        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error = exc
            logger.warning(
                "Attempt %d/%d failed for page %d: %s",
                attempt, config.retry_count, page, exc,
            )
            if attempt < config.retry_count:
                time.sleep(config.retry_delay * attempt)

    raise RuntimeError(
        f"Failed to fetch page {page} after {config.retry_count} attempts: {last_error}"
    )


def fetch_pages(
    start_page: int = 1,
    max_pages: int = 3,
    config: FetchConfig | None = None,
    delay: float = 1.0,
) -> list[PageResult]:
    """
    批量采集多页数据。

    Args:
        start_page: 起始页码
        max_pages: 最大采集页数
        config: 采集配置
        delay: 每页间隔（秒）

    Returns:
        PageResult 列表
    """
    if config is None:
        config = FetchConfig()

    results: list[PageResult] = []
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    for page_num in range(start_page, start_page + max_pages):
        result = fetch_page(page=page_num, config=config, session=session)
        results.append(result)

        if page_num >= result.total_pages:
            logger.info("Reached last page (%d/%d), stopping.", page_num, result.total_pages)
            break

        if page_num < start_page + max_pages - 1:
            time.sleep(delay)

    return results


def save_results(
    results: list[PageResult],
    output_path: Path,
) -> None:
    """将采集结果保存为 JSON 文件。"""
    all_items = []
    for page_result in results:
        for item in page_result.items:
            all_items.append(asdict(item))

    meta = {
        "fetch_time": datetime.now().isoformat(),
        "pages_fetched": len(results),
        "total_items": len(all_items),
        "total_available": results[0].total if results else 0,
    }

    output = {"meta": meta, "items": all_items}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved %d items to %s", len(all_items), output_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ggzy.gov.cn 招标信息列表采集工具"
    )
    parser.add_argument("--keyword", default="体育", help="搜索关键词")
    parser.add_argument("--pages", type=int, default=3, help="采集页数")
    parser.add_argument("--start-page", type=int, default=1, help="起始页码")
    parser.add_argument("--time-range", default="1m", choices=list(DEAL_TIME_MAP.keys()),
                        help="时间范围: today/3d/10d/1m/6m/custom")
    parser.add_argument("--begin-date", default="", help="自定义开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="", help="自定义结束日期 (YYYY-MM-DD)")
    parser.add_argument("--delay", type=float, default=1.0, help="每页间隔秒数")
    parser.add_argument("--output", default="", help="输出文件路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出到 stdout")

    args = parser.parse_args()

    config = FetchConfig(
        keyword=args.keyword,
        time_range=args.time_range,
        begin_date=args.begin_date,
        end_date=args.end_date,
    )

    results = fetch_pages(
        start_page=args.start_page,
        max_pages=args.pages,
        config=config,
        delay=args.delay,
    )

    if args.output:
        save_results(results, Path(args.output))
    elif args.json:
        all_items = []
        for pr in results:
            all_items.extend(asdict(item) for item in pr.items)
        print(json.dumps(all_items, ensure_ascii=False, indent=2))
    else:
        total_items = sum(len(r.items) for r in results)
        print(f"\n{'='*60}")
        print(f"采集完成: {len(results)} 页, {total_items} 条记录")
        if results:
            print(f"总可用记录: {results[0].total}")
        print(f"{'='*60}")
        for pr in results:
            print(f"\n--- 第 {pr.page} 页 ({len(pr.items)} 条) ---")
            for i, item in enumerate(pr.items, 1):
                print(f"  {i}. [{item.publish_date}] {item.title[:60]}")
                print(f"     地区: {item.region} | 平台: {item.platform or 'N/A'}")
                print(f"     URL: {item.detail_url}")

    output_path = args.output or str(
        Path(__file__).parent.parent / "data" / "raw" / "list_fetch_result.json"
    )
    if not args.output:
        save_results(results, Path(output_path))


if __name__ == "__main__":
    main()
