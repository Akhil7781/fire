"""
Builds the machine-readable 20-chip DS08 pilot annotation manifest (Stage 8.9).

Extracts the 20 active annotation-ready pilot chips (18 valid original + 1 resolved PILOT_05 + 1 replacement PILOT_04).
Sets:
- annotation_status = "NOT_STARTED"
- review_status = "NOT_STARTED"
- annotation_version = "v1.0"
- Strictly zero assigned source classes.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

AUDIT_V2_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "pilot" / "audit" / "pilot_quality_audit_v2.json"
MANIFEST_JSON_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "pilot_manifest.json"
MANIFEST_CSV_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "pilot_manifest.csv"

def build_manifest():
    with open(AUDIT_V2_PATH, "r", encoding="utf-8") as f:
        audit_data = json.load(f)

    chips = audit_data["chips"]
    # Filter for active pilot members (excludes ORIGINAL_REJECTED)
    active_chips = [c for c in chips if c.get("is_active_pilot_member", False)]

    if len(active_chips) != 20:
        raise ValueError(f"Expected 20 active pilot chips, got {len(active_chips)}")

    manifest_entries = []
    csv_rows = []

    for idx, c in enumerate(active_chips, start=1):
        cid = c["candidate_id"]
        reg = c["firms_context"]["geographic_region"]
        pid = c["sentinel2_metadata"]["product_id"]
        tid = c["sentinel2_metadata"]["tile_id"]
        s2_acq = c["sentinel2_metadata"]["acquisition_utc"]
        cld = c["sentinel2_metadata"]["cloud_cover_pct"]
        det_id = c["firms_context"]["detection_id"]
        lat = c["firms_context"]["latitude"]
        lon = c["firms_context"]["longitude"]
        frp = c["firms_context"]["frp"]
        firms_acq = c["firms_context"]["acquisition_utc"]

        entry = {
            "pilot_index": idx,
            "chip_id": cid,
            "region": reg,
            "product_id": pid,
            "tile_id": tid,
            "acquisition_datetime_utc": s2_acq,
            "cloud_cover_pct": cld,
            "firms_detection_id": det_id,
            "firms_latitude": lat,
            "firms_longitude": lon,
            "firms_frp": frp,
            "firms_acquisition_datetime_utc": firms_acq,
            "annotation_status": "NOT_STARTED",
            "annotation_version": "v1.0",
            "review_status": "NOT_STARTED",
            "assigned_annotator_pass1": None,
            "assigned_annotator_pass2": None,
            "adjudication_status": "NOT_REQUIRED",
        }
        manifest_entries.append(entry)

        csv_rows.append({
            "pilot_index": idx,
            "chip_id": cid,
            "region": reg,
            "product_id": pid,
            "tile_id": tid,
            "acquisition_datetime_utc": s2_acq,
            "cloud_cover_pct": cld,
            "firms_detection_id": det_id,
            "firms_latitude": lat,
            "firms_longitude": lon,
            "firms_frp": frp,
            "annotation_status": "NOT_STARTED",
            "annotation_version": "v1.0",
            "review_status": "NOT_STARTED",
        })

    manifest_doc = {
        "status": "STAGE_8.9_ANNOTATION_MANIFEST_CREATED",
        "created_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_active_pilot_chips": len(manifest_entries),
        "annotation_status_summary": {
            "NOT_STARTED": len(manifest_entries),
            "IN_PROGRESS": 0,
            "COMPLETED": 0,
        },
        "review_status_summary": {
            "NOT_STARTED": len(manifest_entries),
            "IN_REVIEW": 0,
            "APPROVED": 0,
        },
        "chips": manifest_entries,
    }

    MANIFEST_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_JSON_PATH, "w", encoding="utf-8") as jf:
        json.dump(manifest_doc, jf, indent=2)

    with open(MANIFEST_CSV_PATH, "w", newline="", encoding="utf-8") as cf:
        fieldnames = [
            "pilot_index", "chip_id", "region", "product_id", "tile_id",
            "acquisition_datetime_utc", "cloud_cover_pct", "firms_detection_id",
            "firms_latitude", "firms_longitude", "firms_frp", "annotation_status",
            "annotation_version", "review_status"
        ]
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"Successfully generated annotation manifest:")
    print(f"  JSON: {MANIFEST_JSON_PATH} ({len(manifest_entries)} chips)")
    print(f"  CSV:  {MANIFEST_CSV_PATH} ({len(csv_rows)} rows)")

if __name__ == "__main__":
    build_manifest()
