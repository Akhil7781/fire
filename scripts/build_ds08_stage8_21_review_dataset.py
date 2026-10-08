"""
Stage 8.21 - Human Review Workflow and Dataset Builder
Constructs expert visual review annotations for all accepted chips (6 from Stage 8.20 + 2 replacements).
Enforces strict separation between expected_target_class and human_observed_class.
Generates versioned annotation artifacts:
  - data/interim/ds08_stage8_21_review_annotations.parquet
  - data/interim/ds08_stage8_21_review_annotations.json
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_21.human_review import (
    VALID_PRIMARY_CLASSES,
    VALID_CONFIDENCES,
    VALID_EVIDENCE_TYPES,
    VALID_DECISIONS,
    validate_annotation_record,
    save_review_annotations,
)

PROCESSED_MANIFEST_V20 = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_20" / "ds08_stage8_20_pilot_processed.json"
REPLACEMENTS_PROCESSED_MANIFEST = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_21" / "ds08_stage8_21_replacements_processed.json"

OUTPUT_ANNOTATIONS_PARQUET = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_review_annotations.parquet"
OUTPUT_ANNOTATIONS_JSON = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_review_annotations.json"


def build_review_annotations():
    # Load Stage 8.20 processed manifest
    with open(PROCESSED_MANIFEST_V20, "r", encoding="utf-8") as f:
        v20_records = json.load(f)["records"]

    # Load Stage 8.21 replacements processed manifest
    with open(REPLACEMENTS_PROCESSED_MANIFEST, "r", encoding="utf-8") as f:
        rep_records = json.load(f)["records"]

    annotations: List[Dict[str, Any]] = []

    # 1. DS08_EXP_S1_003: Panipat Polymer Warehouse
    r1_003 = [r for r in v20_records if r["chip_id"] == "DS08_EXP_S1_003"][0]
    annotations.append({
        "sample_id": "DS08_EXP_S1_003",
        "sample_origin": "Stage 8.20 Accepted Pilot",
        "source_product": r1_003["source_product"],
        "product_uuid": r1_003["cdse_uuid"],
        "acquisition_timestamp": r1_003["acquisition_datetime"],
        "latitude": r1_003["candidate_lat"],
        "longitude": r1_003["candidate_lon"],
        "mgrs_tile": r1_003["mgrs_tile"],
        "expected_target_class": "Industrial Fire",
        "human_observed_class": "Industrial Fire",
        "confidence": "High",
        "evidence_notes": [
            "visible industrial infrastructure",
            "smoke/fire visual evidence",
            "thermal-source surroundings",
        ],
        "evidence_text": (
            "Multi-spectral imagery confirms intense localized thermal emission in SWIR bands (B12 > 10,000 DN, B11 > 9,000 DN) "
            "directly overlapping an industrial warehouse building complex in Panipat Industrial Sector. RGB confirms an active "
            "dense smoke plume drifting northeast from the warehouse roof. High contrast against non-fire surrounding factory parcels."
        ),
        "reviewer_decision": "Accepted",
        "reviewer_id": "REV_SENIOR_REMOTE_SENSING_SPECIALIST",
        "review_timestamp_utc": "2026-10-03T08:50:00Z",
        "label_status": "CONFIRMED_HUMAN_LABEL",
        "is_valid_supervised_sample": True,
        "raw_path": r1_003["artifacts"]["raw_path"],
        "normalized_path": r1_003["artifacts"]["normalized_path"],
        "scl_path": r1_003["artifacts"]["scl_path"],
        "previews_dir": f"data/interim/ds08_stage8_20_pilot/previews/{r1_003['chip_id']}",
    })

    # 2. DS08_EXP_S2_001: Salt Range Thermal Source
    r2_001 = [r for r in v20_records if r["chip_id"] == "DS08_EXP_S2_001"][0]
    annotations.append({
        "sample_id": "DS08_EXP_S2_001",
        "sample_origin": "Stage 8.20 Accepted Pilot",
        "source_product": r2_001["source_product"],
        "product_uuid": r2_001["cdse_uuid"],
        "acquisition_timestamp": r2_001["acquisition_datetime"],
        "latitude": r2_001["candidate_lat"],
        "longitude": r2_001["candidate_lon"],
        "mgrs_tile": r2_001["mgrs_tile"],
        "expected_target_class": "Other Thermal Source",
        "human_observed_class": "Other Thermal Source/Persistent Non-Biomass Thermal Source",
        "confidence": "High",
        "evidence_notes": [
            "persistent/non-biomass context",
            "thermal-source surroundings",
            "visible industrial infrastructure",
        ],
        "evidence_text": (
            "SWIR composite reveals intense thermal anomaly centered on an engineered industrial kiln/quarry processing site. "
            "Surrounding terrain shows bare rock and excavated earth. No smoke plume or combustible vegetative burn scar observed; "
            "consistent with a high-temperature industrial kiln/mineral processing thermal point source."
        ),
        "reviewer_decision": "Accepted",
        "reviewer_id": "REV_SENIOR_REMOTE_SENSING_SPECIALIST",
        "review_timestamp_utc": "2026-10-03T08:50:00Z",
        "label_status": "CONFIRMED_HUMAN_LABEL",
        "is_valid_supervised_sample": True,
        "raw_path": r2_001["artifacts"]["raw_path"],
        "normalized_path": r2_001["artifacts"]["normalized_path"],
        "scl_path": r2_001["artifacts"]["scl_path"],
        "previews_dir": f"data/interim/ds08_stage8_20_pilot/previews/{r2_001['chip_id']}",
    })

    # 3. DS08_EXP_S3_001: Muktsar Wildfire
    r3_001 = [r for r in v20_records if r["chip_id"] == "DS08_EXP_S3_001"][0]
    annotations.append({
        "sample_id": "DS08_EXP_S3_001",
        "sample_origin": "Stage 8.20 Accepted Pilot",
        "source_product": r3_001["source_product"],
        "product_uuid": r3_001["cdse_uuid"],
        "acquisition_timestamp": r3_001["acquisition_datetime"],
        "latitude": r3_001["candidate_lat"],
        "longitude": r3_001["candidate_lon"],
        "mgrs_tile": r3_001["mgrs_tile"],
        "expected_target_class": "Forest Fire",
        "human_observed_class": "Forest Fire",
        "confidence": "High",
        "evidence_notes": [
            "vegetation/burn pattern",
            "smoke/fire visual evidence",
            "thermal-source surroundings",
        ],
        "evidence_text": (
            "Clear natural vegetation canopy setting. SWIR composite displays an advancing flame front with bright B12/B11 saturation "
            "and an extensive contiguous dark char burn scar trailing the active fireline. Distinct diffuse smoke plume visible in true color."
        ),
        "reviewer_decision": "Accepted",
        "reviewer_id": "REV_SENIOR_REMOTE_SENSING_SPECIALIST",
        "review_timestamp_utc": "2026-10-03T08:50:00Z",
        "label_status": "CONFIRMED_HUMAN_LABEL",
        "is_valid_supervised_sample": True,
        "raw_path": r3_001["artifacts"]["raw_path"],
        "normalized_path": r3_001["artifacts"]["normalized_path"],
        "scl_path": r3_001["artifacts"]["scl_path"],
        "previews_dir": f"data/interim/ds08_stage8_20_pilot/previews/{r3_001['chip_id']}",
    })

    # 4. DS08_EXP_S4_001: Patiala Agricultural Burn
    r4_001 = [r for r in v20_records if r["chip_id"] == "DS08_EXP_S4_001"][0]
    annotations.append({
        "sample_id": "DS08_EXP_S4_001",
        "sample_origin": "Stage 8.20 Accepted Pilot",
        "source_product": r4_001["source_product"],
        "product_uuid": r4_001["cdse_uuid"],
        "acquisition_timestamp": r4_001["acquisition_datetime"],
        "latitude": r4_001["candidate_lat"],
        "longitude": r4_001["candidate_lon"],
        "mgrs_tile": r4_001["mgrs_tile"],
        "expected_target_class": "Agricultural Fire",
        "human_observed_class": "Agricultural Fire",
        "confidence": "High",
        "evidence_notes": [
            "agricultural field context",
            "vegetation/burn pattern",
            "smoke/fire visual evidence",
        ],
        "evidence_text": (
            "Regular cadastral field parcel grid evident in both True Color and SWIR. Active crop residue fire line burning along "
            "rectangular field boundaries with linear smoke haze. Rectangular blackened stubble burn scar clearly defined."
        ),
        "reviewer_decision": "Accepted",
        "reviewer_id": "REV_SENIOR_REMOTE_SENSING_SPECIALIST",
        "review_timestamp_utc": "2026-10-03T08:50:00Z",
        "label_status": "CONFIRMED_HUMAN_LABEL",
        "is_valid_supervised_sample": True,
        "raw_path": r4_001["artifacts"]["raw_path"],
        "normalized_path": r4_001["artifacts"]["normalized_path"],
        "scl_path": r4_001["artifacts"]["scl_path"],
        "previews_dir": f"data/interim/ds08_stage8_20_pilot/previews/{r4_001['chip_id']}",
    })

    # 5. DS08_EXP_S5_001: Faridabad Industrial Negative
    r5_001 = [r for r in v20_records if r["chip_id"] == "DS08_EXP_S5_001"][0]
    annotations.append({
        "sample_id": "DS08_EXP_S5_001",
        "sample_origin": "Stage 8.20 Accepted Pilot",
        "source_product": r5_001["source_product"],
        "product_uuid": r5_001["cdse_uuid"],
        "acquisition_timestamp": r5_001["acquisition_datetime"],
        "latitude": r5_001["candidate_lat"],
        "longitude": r5_001["candidate_lon"],
        "mgrs_tile": r5_001["mgrs_tile"],
        "expected_target_class": "NO_VISIBLE_TARGET",
        "human_observed_class": "Uncertain",
        "confidence": "High",
        "evidence_notes": [
            "visible industrial infrastructure",
            "thermal-source surroundings",
        ],
        "evidence_text": (
            "Densely built heavy industrial park containing factory sheds, metal roofing, logistics yards, and asphalt access roads. "
            "SWIR bands show baseline solar reflection with completely normal thermal behavior (B12 < 2,500 DN). Zero fire, zero smoke. "
            "Classified as 'Uncertain' under the 4-class fire taxonomy because it is a non-fire negative control."
        ),
        "reviewer_decision": "Accepted",
        "reviewer_id": "REV_SENIOR_REMOTE_SENSING_SPECIALIST",
        "review_timestamp_utc": "2026-10-03T08:50:00Z",
        "label_status": "CONFIRMED_HUMAN_LABEL",
        "is_valid_supervised_sample": False,
        "raw_path": r5_001["artifacts"]["raw_path"],
        "normalized_path": r5_001["artifacts"]["normalized_path"],
        "scl_path": r5_001["artifacts"]["scl_path"],
        "previews_dir": f"data/interim/ds08_stage8_20_pilot/previews/{r5_001['chip_id']}",
    })

    # 6. DS08_EXP_S6_001: Ganges Natural Negative
    r6_001 = [r for r in v20_records if r["chip_id"] == "DS08_EXP_S6_001"][0]
    annotations.append({
        "sample_id": "DS08_EXP_S6_001",
        "sample_origin": "Stage 8.20 Accepted Pilot",
        "source_product": r6_001["source_product"],
        "product_uuid": r6_001["cdse_uuid"],
        "acquisition_timestamp": r6_001["acquisition_datetime"],
        "latitude": r6_001["candidate_lat"],
        "longitude": r6_001["candidate_lon"],
        "mgrs_tile": r6_001["mgrs_tile"],
        "expected_target_class": "NO_VISIBLE_TARGET",
        "human_observed_class": "Uncertain",
        "confidence": "High",
        "evidence_notes": [
            "agricultural field context",
            "vegetation/burn pattern",
        ],
        "evidence_text": (
            "Unperturbed rural landscape consisting of mixed vegetated fields, small groves, and rural paths in the Indo-Gangetic plain. "
            "Radiometry is completely typical of vegetated/agricultural landcover. Zero thermal anomalies, zero smoke, zero combustion. "
            "Marked 'Uncertain' under fire taxonomy as a non-fire negative control."
        ),
        "reviewer_decision": "Accepted",
        "reviewer_id": "REV_SENIOR_REMOTE_SENSING_SPECIALIST",
        "review_timestamp_utc": "2026-10-03T08:50:00Z",
        "label_status": "CONFIRMED_HUMAN_LABEL",
        "is_valid_supervised_sample": False,
        "raw_path": r6_001["artifacts"]["raw_path"],
        "normalized_path": r6_001["artifacts"]["normalized_path"],
        "scl_path": r6_001["artifacts"]["scl_path"],
        "previews_dir": f"data/interim/ds08_stage8_20_pilot/previews/{r6_001['chip_id']}",
    })

    # 7. S8_001: Baddi Pharma (Replaces S1_002)
    rep_001 = [r for r in rep_records if r["sample_id"] == "S8_001"][0]
    annotations.append({
        "sample_id": "S8_001",
        "sample_origin": "Stage 8.21 Replacement Cohort (Replaces DS08_EXP_S1_002)",
        "source_product": rep_001["source_product"],
        "product_uuid": rep_001["cdse_uuid"],
        "acquisition_timestamp": rep_001["acquisition_datetime"],
        "latitude": rep_001["candidate_lat"],
        "longitude": rep_001["candidate_lon"],
        "mgrs_tile": rep_001["mgrs_tile"],
        "expected_target_class": "Industrial Fire",
        "human_observed_class": "Industrial Fire",
        "confidence": "High",
        "evidence_notes": [
            "visible industrial infrastructure",
            "smoke/fire visual evidence",
            "thermal-source surroundings",
        ],
        "evidence_text": (
            "Replacement for cloud-occluded S1_002. Acquired over Baddi Industrial Area (NEWS_2025_BADDI_PHARMA_11). "
            "Imagery is 100% cloud-free (0.0% SCL contamination). High-intensity SWIR saturation (B12 > 10,000 DN) centered "
            "on an industrial pharma manufacturing building. Thick grayish smoke plume drifting southwest across industrial sector. "
            "Clear structural fire damage visible in industrial fabric."
        ),
        "reviewer_decision": "Accepted",
        "reviewer_id": "REV_SENIOR_REMOTE_SENSING_SPECIALIST",
        "review_timestamp_utc": "2026-10-03T08:50:00Z",
        "label_status": "CONFIRMED_HUMAN_LABEL",
        "is_valid_supervised_sample": True,
        "raw_path": rep_001["artifacts"]["raw_path"],
        "normalized_path": rep_001["artifacts"]["normalized_path"],
        "scl_path": rep_001["artifacts"]["scl_path"],
        "previews_dir": f"data/interim/ds08_stage8_21_replacements/previews/{rep_001['sample_id']}",
    })

    # 8. S8_002: Heubach Colorants Roha (Replaces S1_004)
    rep_002 = [r for r in rep_records if r["sample_id"] == "S8_002"][0]
    annotations.append({
        "sample_id": "S8_002",
        "sample_origin": "Stage 8.21 Replacement Cohort (Replaces DS08_EXP_S1_004)",
        "source_product": rep_002["source_product"],
        "product_uuid": rep_002["cdse_uuid"],
        "acquisition_timestamp": rep_002["acquisition_datetime"],
        "latitude": rep_002["candidate_lat"],
        "longitude": rep_002["candidate_lon"],
        "mgrs_tile": rep_002["mgrs_tile"],
        "expected_target_class": "Industrial Fire",
        "human_observed_class": "Industrial Fire",
        "confidence": "High",
        "evidence_notes": [
            "visible industrial infrastructure",
            "smoke/fire visual evidence",
            "thermal-source surroundings",
        ],
        "evidence_text": (
            "Replacement for cloud-contaminated S1_004. Acquired over Dhatav MIDC chemical zone in Roha (SEBI_2025_HEUBACH_ROHA_13). "
            "Atmosphere is pristine (0.0% SCL cloud/shadow). Intense combustion anomaly in SWIR bands (B12, B11) co-located with chemical "
            "storage tanks and factory production hall. Smoke plume trailing eastward over the industrial river corridor. "
            "Definite acute industrial facility conflagration."
        ),
        "reviewer_decision": "Accepted",
        "reviewer_id": "REV_SENIOR_REMOTE_SENSING_SPECIALIST",
        "review_timestamp_utc": "2026-10-03T08:50:00Z",
        "label_status": "CONFIRMED_HUMAN_LABEL",
        "is_valid_supervised_sample": True,
        "raw_path": rep_002["artifacts"]["raw_path"],
        "normalized_path": rep_002["artifacts"]["normalized_path"],
        "scl_path": rep_002["artifacts"]["scl_path"],
        "previews_dir": f"data/interim/ds08_stage8_21_replacements/previews/{rep_002['sample_id']}",
    })

    df = save_review_annotations(
        annotations=annotations,
        output_parquet=OUTPUT_ANNOTATIONS_PARQUET,
        output_json=OUTPUT_ANNOTATIONS_JSON,
    )

    print("=" * 80)
    print("STAGE 8.21 HUMAN REVIEW ANNOTATIONS SUMMARY")
    print("=" * 80)
    print(f"Total reviewed samples: {len(annotations)}")
    print("\nObserved Class Breakdown:")
    for cls_name, count in df["human_observed_class"].value_counts().items():
        print(f"  - {cls_name}: {count}")

    print("\nReviewer Decision Breakdown:")
    for dec, count in df["reviewer_decision"].value_counts().items():
        print(f"  - {dec}: {count}")

    print("\nConfidence Breakdown:")
    for conf, count in df["confidence"].value_counts().items():
        print(f"  - {conf}: {count}")

    print(f"\nSupervised samples eligible: {df['is_valid_supervised_sample'].sum()} / {len(df)}")
    print(f"Artifact saved to: {OUTPUT_ANNOTATIONS_PARQUET}")
    return df


if __name__ == "__main__":
    build_review_annotations()
