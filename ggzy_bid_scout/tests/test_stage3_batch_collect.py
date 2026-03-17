"""
Stage3 Self-Check Script - Batch Collection Verification

Acceptance Criteria (max_pages=5):
  - Total records collected: >= 50
  - Success rate: >= 90%
  - Duplicate rate: < 5%
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.ggzy_batch_collect import batch_collect

REPORT_LINES: list[str] = []


def log(msg: str, level: str = "INFO") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    REPORT_LINES.append(line)
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("utf-8", errors="replace").decode("ascii", errors="replace"))


def test_batch_collect() -> dict:
    """Run batch collection with max_pages=5 and return stats."""
    log("=" * 60)
    log("TEST 1: Batch collection (keyword=体育, max_pages=5)")
    log("=" * 60)

    stats = batch_collect(
        keyword="体育",
        max_pages=5,
        time_range="1m",
        delay_list=1.0,
        delay_detail=1.0,
        output_name="stage3_test_data",
    )

    log("")
    log("Batch collection stats:")
    for k, v in stats.items():
        log(f"  {k}: {v}")

    return stats


def verify_structured_output() -> dict:
    """Verify structured output file integrity."""
    log("")
    log("=" * 60)
    log("TEST 2: Structured output verification")
    log("=" * 60)

    structured_path = PROJECT_ROOT / "data" / "structured" / "stage3_test_data.json"
    if not structured_path.exists():
        log(f"[X] Structured output not found: {structured_path}", "FAIL")
        return {"exists": False}

    data = json.loads(structured_path.read_text(encoding="utf-8"))
    meta = data.get("meta", {})
    items = data.get("items", [])

    log(f"  File: {structured_path}")
    log(f"  Meta: {json.dumps(meta, ensure_ascii=False)}")
    log(f"  Total items: {len(items)}")

    has_meta = all(k in meta for k in ("keyword", "last_fetch_time", "total_items"))
    log(f"  {'[OK]' if has_meta else '[X]'} Meta fields present", "PASS" if has_meta else "FAIL")

    if items:
        required_fields = {"title", "publish_date", "detail_url", "record_id"}
        sample = items[0]
        present = required_fields.intersection(sample.keys())
        all_fields = present == required_fields
        log(f"  {'[OK]' if all_fields else '[X]'} Required fields in items ({len(present)}/{len(required_fields)})",
            "PASS" if all_fields else "FAIL")

        with_content = sum(1 for it in items if it.get("content_text") and len(it["content_text"]) > 20)
        log(f"  Items with content_text: {with_content}/{len(items)}")

        with_error = sum(1 for it in items if it.get("error"))
        log(f"  Items with errors: {with_error}/{len(items)}")

    record_ids = [it.get("record_id") for it in items if it.get("record_id")]
    unique_ids = set(record_ids)
    dup_in_file = len(record_ids) - len(unique_ids)
    log(f"  Duplicates in file: {dup_in_file}")

    return {
        "exists": True,
        "total": len(items),
        "has_meta": has_meta,
        "dup_in_file": dup_in_file,
    }


def verify_raw_batches() -> int:
    """Verify raw batch files were written."""
    log("")
    log("=" * 60)
    log("TEST 3: Raw batch file verification")
    log("=" * 60)

    raw_dir = PROJECT_ROOT / "data" / "raw"
    batch_files = sorted(raw_dir.glob("stage3_test_data_batch_*.json"))
    list_file = raw_dir / "stage3_test_data_list.json"

    log(f"  List file exists: {list_file.exists()}")
    log(f"  Batch files found: {len(batch_files)}")

    for bf in batch_files:
        try:
            items = json.loads(bf.read_text(encoding="utf-8"))
            log(f"    {bf.name}: {len(items)} items")
        except Exception as exc:
            log(f"    {bf.name}: ERROR - {exc}", "WARN")

    return len(batch_files)


def evaluate(stats: dict, output_info: dict) -> bool:
    """Evaluate against Stage3 acceptance criteria."""
    log("")
    log("=" * 60)
    log("ACCEPTANCE CRITERIA EVALUATION")
    log("=" * 60)

    total_collected = stats.get("total_stored", 0)
    success = stats.get("success", 0)
    processed = stats.get("items_processed", 0)
    dup_removed = stats.get("duplicates_removed", 0)

    success_rate = stats.get("success_rate", 0)
    dup_rate = dup_removed / total_collected * 100 if total_collected > 0 else 0

    # Criterion 1: >= 50 records
    c1 = total_collected >= 50
    log(f"  {'[OK]' if c1 else '[X]'} Total collected: {total_collected} (threshold: >= 50)",
        "PASS" if c1 else "FAIL")

    # Criterion 2: >= 90% success rate
    c2 = success_rate >= 90
    log(f"  {'[OK]' if c2 else '[X]'} Success rate: {success}/{processed} ({success_rate:.1f}%) (threshold: >= 90%)",
        "PASS" if c2 else "FAIL")

    # Criterion 3: < 5% duplicates
    c3 = dup_rate < 5
    log(f"  {'[OK]' if c3 else '[X]'} Duplicate rate: {dup_removed}/{total_collected} ({dup_rate:.1f}%) (threshold: < 5%)",
        "PASS" if c3 else "FAIL")

    # Criterion 4: structured file valid
    c4 = output_info.get("exists", False) and output_info.get("has_meta", False)
    log(f"  {'[OK]' if c4 else '[X]'} Structured output valid",
        "PASS" if c4 else "FAIL")

    all_pass = c1 and c2 and c3 and c4
    return all_pass


def main() -> None:
    log("=" * 60)
    log("Stage3 Self-Check - Batch Collection")
    log(f"Start time: {datetime.now().isoformat()}")
    log("=" * 60)

    start_time = time.time()

    stats = test_batch_collect()
    output_info = verify_structured_output()
    verify_raw_batches()
    all_pass = evaluate(stats, output_info)

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

    if all_pass:
        log("\n>> Stage3 ACCEPTED - ready for Stage4 <<", "PASS")
    else:
        log(f"\n>> Stage3 NOT ACCEPTED - {fail_count} failure(s) <<", "FAIL")

    # Save logs
    log_dir = PROJECT_ROOT / "data" / "raw"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "stage3_test_log.txt"
    log_path.write_text("\n".join(REPORT_LINES), encoding="utf-8")
    log(f"Test log saved: {log_path}")

    # Save test result
    result_path = log_dir / "stage3_test_result.json"
    result_path.write_text(
        json.dumps({"stats": stats, "output_info": output_info, "pass": all_pass},
                    ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
