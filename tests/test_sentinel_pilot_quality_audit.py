"""
Unit tests for Sentinel-2 L2A Pilot Quality & Annotation Readiness Audit (Stage 8.7).

Verifies:
- All 20 pilot chips and metadata files discovered
- Raster integrity (5 bands, 512x512, float32, projected CRS, 10m resolution)
- Reflectance quality and finite values across all 20 rasters
- Metadata-to-chip correspondence and checksum consistency
- Strict UNLABELED policy (zero ground-truth fire class labels)
- Audit artifacts schema and consistency (JSON, CSV, MD)
- Correct annotation readiness classifications (18 ANNOTATION_READY, 1 REQUIRES_REVIEW, 1 REJECT)
- Duplicate / redundancy detection (20 unique products, 20 unique tiles)
- Invariant integrity of all 5 frozen predecessor artifacts
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Dict

import numpy as np
import pytest
import rasterio

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PILOT_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "pilot"
CHIPS_DIR = PILOT_DIR / "chips"
METADATA_DIR = PILOT_DIR / "metadata"
PREVIEWS_DIR = PILOT_DIR / "preview"
AUDIT_DIR = PILOT_DIR / "audit"

AUDIT_JSON_PATH = AUDIT_DIR / "pilot_quality_audit.json"
AUDIT_CSV_PATH = AUDIT_DIR / "pilot_quality_audit.csv"
AUDIT_MD_PATH = AUDIT_DIR / "pilot_quality_summary.md"

FROZEN_HASHES = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
}


def test_pilot_inventory_counts():
    """Verifies that all 20 pilot chips, 20 metadata files, and 40 previews exist."""
    chips = list(CHIPS_DIR.glob("*.tif"))
    metadata = list(METADATA_DIR.glob("*.json"))
    previews = list(PREVIEWS_DIR.glob("*.png"))

    assert len(chips) == 20, f"Expected 20 GeoTIFF chips, found {len(chips)}"
    assert len(metadata) == 20, f"Expected 20 metadata JSONs, found {len(metadata)}"
    assert len(previews) == 40, f"Expected 40 preview PNGs (20 RGB + 20 SWIR), found {len(previews)}"


def test_raster_integrity_across_all_chips():
    """Verifies 5-band, 512x512, float32, projected CRS, 10m spacing for every chip."""
    chips = sorted(list(CHIPS_DIR.glob("*.tif")))
    assert len(chips) == 20

    for tif_path in chips:
        with rasterio.open(tif_path) as src:
            assert src.count == 5, f"{tif_path.name}: expected 5 bands, got {src.count}"
            assert src.width == 512, f"{tif_path.name}: width != 512"
            assert src.height == 512, f"{tif_path.name}: height != 512"
            assert all(dt == "float32" for dt in src.dtypes), f"{tif_path.name}: not float32"
            assert src.crs is not None and src.crs.is_projected, f"{tif_path.name}: missing projected CRS"

            dx = abs(src.transform.a)
            dy = abs(src.transform.e)
            assert pytest.approx(dx, abs=0.05) == 10.0, f"{tif_path.name}: dx != 10m"
            assert pytest.approx(dy, abs=0.05) == 10.0, f"{tif_path.name}: dy != 10m"

            arr = src.read()
            assert np.all(np.isfinite(arr)), f"{tif_path.name}: contains non-finite values"


def test_metadata_chip_correspondence():
    """Verifies that each chip has a corresponding metadata JSON matching checksum and candidate_id."""
    chips = sorted(list(CHIPS_DIR.glob("*.tif")))
    for tif_path in chips:
        parts = tif_path.stem.split("_")
        cand_id = f"{parts[0]}_{parts[1]}_{parts[2]}"

        # Matching JSON sidecar
        matching_json = [jp for jp in METADATA_DIR.glob("*.json") if cand_id in jp.stem]
        assert len(matching_json) == 1, f"Missing or ambiguous sidecar for {cand_id}"

        json_path = matching_json[0]
        with open(json_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        assert meta["candidate_id"] == cand_id
        assert meta["label_status"] == "UNLABELED"

        # Checksum check
        calc_sha = hashlib.sha256(tif_path.read_bytes()).hexdigest()
        assert meta["extraction"]["sha256_checksum"] == calc_sha


def test_strict_unlabeled_policy_across_metadata():
    """Verifies zero ground-truth fire class labels in any metadata file."""
    forbidden_classes = ["Industrial Fire", "Forest Fire", "Agricultural Fire", "Other Thermal Source"]
    for json_path in METADATA_DIR.glob("*.json"):
        content = json_path.read_text(encoding="utf-8")
        assert "client_secret" not in content.lower()
        assert "access_token" not in content.lower()
        assert "bearer" not in content.lower()

        data = json.loads(content)
        assert data["label_status"] == "UNLABELED"
        assert data["firms_metadata"]["association_status"] == "candidate_context_only"

        for fc in forbidden_classes:
            assert fc not in content


def test_audit_artifacts_schema_and_integrity():
    """Verifies schema and contents of pilot_quality_audit.json, .csv, and summary.md."""
    assert AUDIT_JSON_PATH.exists()
    assert AUDIT_CSV_PATH.exists()
    assert AUDIT_MD_PATH.exists()

    with open(AUDIT_JSON_PATH, "r", encoding="utf-8") as f:
        audit_json = json.load(f)

    assert audit_json["status"] == "STAGE_8.7_QUALITY_AUDIT_COMPLETE"
    assert audit_json["total_chips_audited"] == 20
    assert len(audit_json["chips"]) == 20
    assert "scientific_limitation_statement" in audit_json

    # CSV checks
    with open(AUDIT_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 20
        expected_cols = [
            "chip_id", "product_id", "tile_id", "region", "crs", "width", "height",
            "resolution_m", "valid_pixel_pct", "nodata_pct", "cloud_concern", "shadow_concern",
            "haze_concern", "b02_max", "b03_max", "b04_max", "b11_max", "b12_max",
            "b02_gt1_pct", "b03_gt1_pct", "b04_gt1_pct", "b11_gt1_pct", "b12_gt1_pct",
            "duplicate_status", "annotation_status", "review_reason"
        ]
        assert reader.fieldnames == expected_cols


def test_annotation_readiness_decisions():
    """Verifies that the audit correctly classifies each chip."""
    with open(AUDIT_JSON_PATH, "r", encoding="utf-8") as f:
        audit_json = json.load(f)

    summary = audit_json["annotation_readiness_summary"]
    assert summary["ANNOTATION_READY"] == 18
    assert summary["REQUIRES_REVIEW"] == 1
    assert summary["REJECT"] == 1

    chips = {c["candidate_id"]: c for c in audit_json["chips"]}

    # PILOT_04_NORTH must be REJECT due to 51.2% swath-edge truncation
    assert chips["PILOT_04_NORTH"]["annotation_status"] == "REJECT"
    assert "swath-edge truncation" in chips["PILOT_04_NORTH"]["review_reason"]

    # PILOT_05_CENTRAL must be REQUIRES_REVIEW due to visible-band cloud saturation
    assert chips["PILOT_05_CENTRAL"]["annotation_status"] == "REQUIRES_REVIEW"
    assert "Visible bands" in chips["PILOT_05_CENTRAL"]["review_reason"]

    # Sample ANNOTATION_READY check
    assert chips["PILOT_01_NORTH"]["annotation_status"] == "ANNOTATION_READY"
    assert chips["PILOT_06_CENTRAL"]["annotation_status"] == "ANNOTATION_READY"
    assert chips["PILOT_13_EAST"]["annotation_status"] == "ANNOTATION_READY"
    assert chips["PILOT_20_WEST"]["annotation_status"] == "ANNOTATION_READY"


def test_duplicate_detection():
    """Verifies 20 unique products, 20 unique tiles, and 0 duplicate products."""
    with open(AUDIT_JSON_PATH, "r", encoding="utf-8") as f:
        audit_json = json.load(f)

    dup_summary = audit_json["duplicate_summary"]
    assert dup_summary["unique_products"] == 20
    assert dup_summary["unique_tiles"] == 20
    assert dup_summary["duplicate_count"] == 0


def test_frozen_predecessor_integrity():
    """Strict invariant: verifies all 5 frozen artifacts remain byte-for-byte unmodified."""
    for rel_path, expected_hash in FROZEN_HASHES.items():
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists(), f"Missing frozen artifact: {rel_path}"
        actual_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, (
            f"MUTATION DETECTED in frozen artifact {rel_path}!\n"
            f"Expected: {expected_hash}\n"
            f"Actual:   {actual_hash}"
        )
