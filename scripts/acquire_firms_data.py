"""
Full acquisition script for NASA FIRMS VIIRS NOAA-20 SP India datasets.
Downloads:
1. Primary 2025 Dataset: 2025-01-01 to 2025-12-31 (73 chunks of 5 days) -> data/raw/2025/
2. Context Q4 2024 Dataset: 2024-10-01 to 2024-12-31 (19 chunks of <=5 days) -> data/raw_context/2024_Q4/

Features:
- Resumable: Skips already-downloaded valid files.
- Atomic saves: Prevents partial files on interruption.
- Manifest generation: Detailed JSON and CSV manifests.
- Post-download verification: Confirms date coverage, chunk counts, and header consistency.
"""

from __future__ import annotations

import csv
import datetime
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.acquisition.firms_client import (
    DEFAULT_INDIA_BBOX,
    FIRMSAcquisitionClient,
    FIRMSChunkRequest,
    ManifestRecord,
    generate_date_chunks,
)


def verify_downloaded_corpus(
    chunks: List[FIRMSChunkRequest],
    expected_chunk_count: int,
    expected_start: datetime.date,
    expected_end: datetime.date,
    dataset_name: str,
) -> Tuple[bool, List[str]]:
    """
    Verifies date coverage, chunk count, file existence, and header consistency.
    """
    errors: List[str] = []

    if len(chunks) != expected_chunk_count:
        errors.append(
            f"Chunk count mismatch for {dataset_name}: {len(chunks)} chunks generated, "
            f"expected {expected_chunk_count}."
        )

    covered_dates: set[datetime.date] = set()
    standard_header: Optional[str] = None

    for i, chunk in enumerate(chunks):
        target = chunk.target_file
        if not target.exists():
            errors.append(f"Missing file: {target}")
            continue

        size = target.stat().st_size
        if size == 0:
            errors.append(f"Unexpected empty file: {target}")
            continue

        with open(target, "r", encoding="utf-8") as f:
            header = f.readline().strip()
            if standard_header is None:
                standard_header = header
            elif header != standard_header:
                errors.append(f"Header mismatch in {target.name}: '{header}' vs '{standard_header}'")

        # Track date coverage
        c_start = datetime.datetime.strptime(chunk.start_date, "%Y-%m-%d").date()
        c_end = datetime.datetime.strptime(chunk.end_date, "%Y-%m-%d").date()
        curr = c_start
        while curr <= c_end:
            covered_dates.add(curr)
            curr += datetime.timedelta(days=1)

    # Check continuous date coverage
    curr = expected_start
    while curr <= expected_end:
        if curr not in covered_dates:
            errors.append(f"Missing date in {dataset_name} coverage: {curr}")
        curr += datetime.timedelta(days=1)

    is_valid = len(errors) == 0
    return is_valid, errors


def run_acquisition(overwrite: bool = False) -> int:
    print("\n" + "#" * 75)
    print("# NASA FIRMS REPRODUCIBLE DATA ACQUISITION MODULE")
    print("#" * 75 + "\n")

    t_start = time.perf_counter()
    client = FIRMSAcquisitionClient(inter_request_sleep_sec=0.4)

    raw_2025_dir = PROJECT_ROOT / "data" / "raw" / "2025"
    raw_context_dir = PROJECT_ROOT / "data" / "raw_context" / "2024_Q4"
    manifests_dir = PROJECT_ROOT / "data" / "manifests"

    raw_2025_dir.mkdir(parents=True, exist_ok=True)
    raw_context_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    # 1. Define Primary 2025 Chunks (73 chunks of 5 days)
    start_2025 = datetime.date(2025, 1, 1)
    end_2025 = datetime.date(2025, 12, 31)
    chunks_2025 = generate_date_chunks(
        start_date=start_2025,
        end_date=end_2025,
        max_days_per_chunk=5,
        source="VIIRS_NOAA20_SP",
        bbox=DEFAULT_INDIA_BBOX,
        target_dir=raw_2025_dir,
        is_burn_in_context=False,
    )

    # 2. Define Context Q4 2024 Chunks (19 chunks of <=5 days)
    start_2024 = datetime.date(2024, 10, 1)
    end_2024 = datetime.date(2024, 12, 31)
    chunks_2024 = generate_date_chunks(
        start_date=start_2024,
        end_date=end_2024,
        max_days_per_chunk=5,
        source="VIIRS_NOAA20_SP",
        bbox=DEFAULT_INDIA_BBOX,
        target_dir=raw_context_dir,
        is_burn_in_context=True,
    )

    all_chunks = chunks_2025 + chunks_2024
    print(f"  Total 2025 Chunks:     {len(chunks_2025)} (expected 73)")
    print(f"  Total Q4 2024 Chunks:  {len(chunks_2024)} (expected 19)")
    print(f"  Grand Total Requests:  {len(all_chunks)} chunks")
    print(f"  Target Bounding Box:   {DEFAULT_INDIA_BBOX}")

    manifest_records: List[ManifestRecord] = []
    success_2025 = 0
    success_2024 = 0
    failures = 0
    total_rows = 0

    print("\nStarting chunk retrieval (with resumability and exponential backoff)...")
    for i, chunk in enumerate(all_chunks, start=1):
        target_name = chunk.filename
        ds_type = "Q4 2024 CONTEXT" if chunk.is_burn_in_context else "PRIMARY 2025"

        print(f"[{i:02d}/{len(all_chunks):02d}] Fetching {ds_type}: {chunk.start_date} to {chunk.end_date}...", end=" ", flush=True)

        record = client.fetch_chunk(chunk, max_retries=5, overwrite=overwrite)
        manifest_records.append(record)

        if record.download_status in ("SUCCESS", "SKIPPED_EXISTING"):
            status_tag = "DOWNLOADED" if record.download_status == "SUCCESS" else "EXISTS (VERIFIED)"
            print(f"[{status_tag}] {record.row_count} rows")
            total_rows += record.row_count
            if chunk.is_burn_in_context:
                success_2024 += 1
            else:
                success_2025 += 1
        else:
            print(f"[FAILED] {record.error_message}")
            failures += 1

    # Save Manifest (JSON and CSV)
    json_manifest_path = manifests_dir / "download_manifest.json"
    csv_manifest_path = manifests_dir / "download_manifest.csv"

    manifest_dicts = [asdict(r) for r in manifest_records]
    with open(json_manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_dicts, f, indent=2)

    if manifest_records:
        with open(csv_manifest_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(manifest_dicts[0].keys()))
            writer.writeheader()
            writer.writerows(manifest_dicts)

    elapsed = time.perf_counter() - t_start

    # Post-Download Verification
    print("\n" + "=" * 75)
    print("POST-DOWNLOAD VERIFICATION")
    print("=" * 75)

    valid_2025, errors_2025 = verify_downloaded_corpus(
        chunks=chunks_2025,
        expected_chunk_count=73,
        expected_start=start_2025,
        expected_end=end_2025,
        dataset_name="Primary 2025",
    )
    valid_2024, errors_2024 = verify_downloaded_corpus(
        chunks=chunks_2024,
        expected_chunk_count=19,
        expected_start=start_2024,
        expected_end=end_2024,
        dataset_name="Context Q4 2024",
    )

    if valid_2025:
        print("  [PASS] Primary 2025: Exactly 73 chunks, full continuous date coverage (2025-01-01 to 2025-12-31).")
    else:
        print(f"  [FAIL] Primary 2025 errors: {errors_2025}")

    if valid_2024:
        print("  [PASS] Context Q4 2024: Exactly 19 chunks, full continuous date coverage (2024-10-01 to 2024-12-31).")
    else:
        print(f"  [FAIL] Context Q4 2024 errors: {errors_2024}")

    print("\n" + "=" * 75)
    print("ACQUISITION SUMMARY")
    print("=" * 75)
    print(f"  Runtime:                    {elapsed:.2f} seconds")
    print(f"  Successful 2025 Chunks:     {success_2025} / 73")
    print(f"  Successful Q4 2024 Chunks:  {success_2024} / 19")
    print(f"  Failed Chunks:              {failures}")
    print(f"  Total Downloaded Rows:      {total_rows:,} records")
    print(f"  Primary 2025 Raw Directory: {raw_2025_dir}")
    print(f"  Context Raw Directory:      {raw_context_dir}")
    print(f"  Manifest JSON Path:         {json_manifest_path}")
    print(f"  Manifest CSV Path:          {csv_manifest_path}")
    print(f"  Full Date Coverage Valid:   {valid_2025 and valid_2024}\n")

    return 0 if (valid_2025 and valid_2024 and failures == 0) else 1


if __name__ == "__main__":
    overwrite_flag = "--overwrite" in sys.argv
    sys.exit(run_acquisition(overwrite=overwrite_flag))
