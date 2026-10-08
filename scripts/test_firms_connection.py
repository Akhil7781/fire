"""
Test script for verifying NASA FIRMS Area API connectivity with a 1-day historical request.
DO NOT print or expose the FIRMS_MAP_KEY.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.acquisition.firms_client import (
    DEFAULT_INDIA_BBOX,
    FIRMSAcquisitionClient,
    FIRMSChunkRequest,
)


def run_api_smoke_test() -> int:
    print("\n" + "=" * 70)
    print("NASA FIRMS AREA API SMOKE TEST (1-DAY HISTORICAL CHUNK)")
    print("=" * 70)

    try:
        client = FIRMSAcquisitionClient()
    except Exception as e:
        print(f"[FAIL] Failed to initialize FIRMSAcquisitionClient: {e}")
        return 1

    # Single-day historical request for 2024-10-01 (India Bounding Box)
    test_chunk = FIRMSChunkRequest(
        source="VIIRS_NOAA20_SP",
        bbox=DEFAULT_INDIA_BBOX,
        start_date="2024-10-01",
        day_range=1,
        end_date="2024-10-01",
        is_burn_in_context=True,
        target_dir=PROJECT_ROOT / "data" / "raw_context" / "2024_Q4",
        filename="VIIRS_NOAA20_SP_2024-10-01_to_2024-10-01_test.csv",
    )

    print(f"  Target Product:   {test_chunk.source}")
    print(f"  India Bounding:   {test_chunk.bbox}")
    print(f"  Test Date:        {test_chunk.start_date} (1 day)")
    print(f"  Target File:      {test_chunk.filename}")
    print("  Sending request to NASA FIRMS API...")

    record = client.fetch_chunk(test_chunk, max_retries=3, overwrite=True)

    if record.download_status != "SUCCESS":
        print(f"\n[FAIL] Test request failed: {record.error_message}")
        return 1

    print("\n[SUCCESS] Response received and validated successfully!")
    print(f"  Status:           {record.download_status}")
    print(f"  Saved File:       {record.file_path}")
    print(f"  Row Count:        {record.row_count} active fire detections")
    print(f"  SHA-256 Checksum: {record.sha256_checksum[:16]}... (length: 64)")

    # Read and inspect the saved CSV header and sample
    with open(record.file_path, "r", encoding="utf-8") as f:
        header = f.readline().strip()
        first_row = f.readline().strip()

    columns = [c.strip() for c in header.split(",")]
    print(f"\n  Columns Returned ({len(columns)} columns):")
    for i, col in enumerate(columns, start=1):
        print(f"    {i:2d}. {col}")

    print(f"\n  First Data Row Sample:")
    print(f"    {first_row}")

    # Remove temporary test file so directory remains clean before full download
    try:
        Path(record.file_path).unlink()
        print("\n  Cleaned up temporary test file.")
    except Exception:
        pass

    print("\nAPI test passed all verification checks.")
    print("=" * 70 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(run_api_smoke_test())
