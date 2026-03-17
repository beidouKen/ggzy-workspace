"""
Stage1 Self-Check Script - List Fetch Capability Verification

Acceptance Criteria:
  1. List fetch >= 10 items
  2. Pagination: reach page 3
  3. detail_url accessible
  4. Stability: 3 consecutive successful runs
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.ggzy_list_fetch import fetch_page, fetch_pages, FetchConfig, PageResult

REPORT_LINES: list[str] = []


def log(msg: str, level: str = "INFO") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    REPORT_LINES.append(line)
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("utf-8", errors="replace").decode("ascii", errors="replace"))


def test_single_page_fetch() -> PageResult | None:
    """Test 1: Fetch page 1, verify >= 10 items."""
    log("=" * 60)
    log("TEST 1: Single page fetch (page 1)")
    log("=" * 60)

    config = FetchConfig(keyword="体育", time_range="1m")
    result = fetch_page(page=1, config=config)

    log(f"  Items: {len(result.items)}")
    log(f"  Total available: {result.total}")
    log(f"  Total pages: {result.total_pages}")

    if len(result.items) >= 10:
        log("  [OK] PASS: list fetch >= 10 items", "PASS")
    else:
        log(f"  [X] FAIL: only got {len(result.items)} items, need >= 10", "FAIL")

    for i, item in enumerate(result.items[:5]):
        title_safe = item.title[:50].encode("ascii", errors="replace").decode("ascii")
        log(f"  [{i+1}] {title_safe} | {item.publish_date} | {item.region}")

    return result


def test_pagination() -> list[PageResult]:
    """Test 2: Paginated fetch (pages 1-3)."""
    log("")
    log("=" * 60)
    log("TEST 2: Pagination (pages 1-3)")
    log("=" * 60)

    config = FetchConfig(keyword="体育", time_range="1m")
    results = fetch_pages(start_page=1, max_pages=3, config=config, delay=1.5)

    page_nums = [r.page for r in results]
    total_items = sum(len(r.items) for r in results)

    log(f"  Pages fetched: {len(results)}")
    log(f"  Page numbers: {page_nums}")
    log(f"  Total items: {total_items}")

    if len(results) >= 3:
        log("  [OK] PASS: reached page 3", "PASS")
    else:
        log(f"  [X] FAIL: only reached page {len(results)}", "FAIL")

    all_ids = []
    for r in results:
        ids = [item.record_id for item in r.items]
        all_ids.extend(ids)

    unique_ids = set(all_ids)
    dup_count = len(all_ids) - len(unique_ids)
    log(f"  Record IDs: {len(all_ids)}, unique: {len(unique_ids)}, duplicates: {dup_count}")
    if dup_count == 0:
        log("  [OK] PASS: no duplicate records", "PASS")
    else:
        log(f"  [!] WARN: found {dup_count} duplicates", "WARN")

    return results


def test_detail_url_validity(results: list[PageResult]) -> None:
    """Test 3: Verify detail_url accessibility."""
    log("")
    log("=" * 60)
    log("TEST 3: detail_url validity check")
    log("=" * 60)

    all_items = []
    for r in results:
        all_items.extend(r.items)

    if not all_items:
        log("  [X] FAIL: no items to test", "FAIL")
        return

    sample_indices = [0, len(all_items) // 4, len(all_items) // 2,
                      3 * len(all_items) // 4, len(all_items) - 1]
    sample_items = [all_items[i] for i in sample_indices if i < len(all_items)]

    success_count = 0
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })

    for item in sample_items:
        url = item.detail_url
        try:
            resp = session.get(url, timeout=10, allow_redirects=True)
            status = resp.status_code
            ok = status == 200
            if ok:
                success_count += 1
            symbol = "[OK]" if ok else "[X]"
            log(f"  {symbol} [{status}] {url[:80]}...")
        except Exception as exc:
            log(f"  [X] [ERR] {url[:80]}... -> {exc}")
        time.sleep(0.5)

    rate = success_count / len(sample_items) * 100 if sample_items else 0
    log(f"  URL access rate: {success_count}/{len(sample_items)} ({rate:.0f}%)")
    if rate >= 80:
        log(f"  [OK] PASS: detail_url access rate >= 80%", "PASS")
    else:
        log(f"  [X] FAIL: detail_url access rate only {rate:.0f}%", "FAIL")


def test_stability() -> None:
    """Test 4: Stability - 3 consecutive runs."""
    log("")
    log("=" * 60)
    log("TEST 4: Stability (3 consecutive single-page fetches)")
    log("=" * 60)

    config = FetchConfig(keyword="体育", time_range="1m")
    success_count = 0

    for run in range(1, 4):
        try:
            result = fetch_page(page=1, config=config)
            if len(result.items) >= 10:
                success_count += 1
                log(f"  Run {run}: [OK] {len(result.items)} items")
            else:
                log(f"  Run {run}: [X] only {len(result.items)} items")
        except Exception as exc:
            log(f"  Run {run}: [X] error: {exc}")

        if run < 3:
            time.sleep(2)

    if success_count == 3:
        log("  [OK] PASS: 3/3 consecutive runs successful", "PASS")
    else:
        log(f"  [X] FAIL: only {success_count}/3 successful", "FAIL")


def save_test_report(results: list[PageResult]) -> None:
    """Save test result data to JSON."""
    output_dir = PROJECT_ROOT / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    all_items = []
    for r in results:
        for item in r.items:
            all_items.append(asdict(item))

    report_data = {
        "test_time": datetime.now().isoformat(),
        "keyword": "体育",
        "pages_tested": len(results),
        "total_items": len(all_items),
        "items": all_items,
    }

    output_path = output_dir / "stage1_test_result.json"
    output_path.write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log(f"\nTest data saved: {output_path}")


def main() -> None:
    log("=" * 60)
    log("Stage1 Self-Check - List Fetch Capability")
    log(f"Start time: {datetime.now().isoformat()}")
    log("=" * 60)

    start_time = time.time()

    page1_result = test_single_page_fetch()
    pagination_results = test_pagination()
    test_detail_url_validity(pagination_results)
    test_stability()
    save_test_report(pagination_results)

    elapsed = time.time() - start_time

    log("")
    log("=" * 60)
    log("TEST SUMMARY")
    log("=" * 60)

    pass_count = sum(1 for line in REPORT_LINES if "[PASS]" in line)
    fail_count = sum(1 for line in REPORT_LINES if "[FAIL]" in line)
    warn_count = sum(1 for line in REPORT_LINES if "[WARN]" in line)

    log(f"  PASS: {pass_count}")
    log(f"  FAIL: {fail_count}")
    log(f"  WARN: {warn_count}")
    log(f"  Elapsed: {elapsed:.1f}s")

    if fail_count == 0:
        log("\n>> Stage1 ACCEPTED - ready for Stage2 <<", "PASS")
    else:
        log(f"\n>> Stage1 NOT ACCEPTED - {fail_count} failure(s) <<", "FAIL")

    log_path = PROJECT_ROOT / "data" / "raw" / "stage1_test_log.txt"
    log_path.write_text("\n".join(REPORT_LINES), encoding="utf-8")
    log(f"Test log saved: {log_path}")


if __name__ == "__main__":
    main()
