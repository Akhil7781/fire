"""
Unit tests for Sentinel-2 L2A Pilot Quality & Annotation Readiness Audit v2 (Stage 8.8).

Verifies:
- Original rejected chip (PILOT_04_NORTH) remains recorded as REJECT
- Replacement chip exists in data/reference/ds08/pilot/replacement/
- Replacement raster has 5 bands, 512x512, float32, projected CRS, 10m spacing
- Replacement raster has correct band order (B02, B03, B04, B11, B12)
- Replacement raster has finite values across all bands
- Replacement raster has no empty bands
- Replacement raster zero_fill_pct <= 1.0% (and verified 0.0%)
- Large all-band-zero regions are detected and trigger rejection
- Strict UNLABELED policy (zero ground-truth fire class labels)
- Zero synthetic paths or images used
- Invariant integrity of all 5 frozen predecessor artifacts
- Audit v2 contains all required records (21 chips: 20 original + 1 replacement)
- PILOT_05_CENTRAL resolution documented with objective diagnostic
- Active pilot cohort contains 20 ANNOTATION_READY chips with 0 duplicates
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import rasterio

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PILOT_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "pilot"
CHIPS_DIR = PILOT_DIR / "chips"
METADATA_DIR = PILOT_DIR / "metadata"
REPLACEMENT_DIR = PILOT_DIR / "replacement"
AUDIT_DIR = PILOT_DIR / "audit"

AUDIT_V2_JSON_PATH = AUDIT_DIR / "pilot_quality_audit_v2.json"
AUDIT_V2_CSV_PATH = AUDIT_DIR / "pilot_quality_audit_v2.csv"
AUDIT_V2_MD_PATH = AUDIT_DIR / "pilot_quality_summary_v2.md"

FROZEN_HASHES = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
}


def test_original_rejected_chip_retained():
    """Verifies that original PILOT_04_NORTH files remain preserved for audit provenance."""
    orig_chips = list(CHIPS_DIR.glob("*PILOT_04_NORTH*.tif"))
    orig_meta = list(METADATA_DIR.glob("*PILOT_04_NORTH*.json"))
    assert len(orig_chips) == 1, "Original PILOT_04_NORTH GeoTIFF missing!"
    assert len(orig_meta) == 1, "Original PILOT_04_NORTH metadata missing!"

    # Verify that in audit v2 it remains recorded as REJECT
    with open(AUDIT_V2_JSON_PATH, "r", encoding="utf-8") as f:
        audit_json = json.load(f)

    p04 = next(c for c in audit_json["chips"] if c["candidate_id"] == "PILOT_04_NORTH")
    assert p04["audit_role"] == "ORIGINAL_REJECTED"
    assert p04["annotation_status"] == "REJECT"
    assert "swath-edge truncation" in p04["review_reason"].lower()
    assert p04["spatial_coverage"]["zero_fill_pct"] > 50.0


def test_replacement_chip_existence_and_storage():
    """Verifies that replacement chip exists separately in data/reference/ds08/pilot/replacement/."""
    assert REPLACEMENT_DIR.exists()
    repl_tifs = list(REPLACEMENT_DIR.glob("PILOT_04_NORTH_REPLACEMENT*.tif"))
    repl_jsons = list(REPLACEMENT_DIR.glob("PILOT_04_NORTH_REPLACEMENT*.json"))
    repl_previews = list(REPLACEMENT_DIR.glob("PILOT_04_NORTH_REPLACEMENT*.png"))

    assert len(repl_tifs) == 1, "Expected exactly 1 replacement GeoTIFF."
    assert len(repl_jsons) == 1, "Expected exactly 1 replacement JSON sidecar."
    assert len(repl_previews) >= 2, "Expected RGB and SWIR preview PNGs for replacement."


def test_replacement_raster_integrity():
    """Verifies replacement chip has 5 bands, 512x512, float32, projected CRS, 10m spacing."""
    repl_tif = list(REPLACEMENT_DIR.glob("PILOT_04_NORTH_REPLACEMENT*.tif"))[0]
    with rasterio.open(repl_tif) as src:
        assert src.count == 5, f"Expected 5 bands, got {src.count}"
        assert src.width == 512, f"Expected 512 width, got {src.width}"
        assert src.height == 512, f"Expected 512 height, got {src.height}"
        assert all(dt == "float32" for dt in src.dtypes), f"Expected float32, got {src.dtypes}"
        assert src.crs is not None and src.crs.is_projected, "Missing projected CRS"
        assert src.crs.to_epsg() == 32643, f"Expected EPSG:32643, got {src.crs.to_epsg()}"

        dx = abs(src.transform.a)
        dy = abs(src.transform.e)
        assert pytest.approx(dx, abs=0.05) == 10.0, f"dx != 10m: {dx}"
        assert pytest.approx(dy, abs=0.05) == 10.0, f"dy != 10m: {dy}"

        arr = src.read()
        assert np.all(np.isfinite(arr)), "Replacement contains non-finite values"


def test_replacement_band_order_and_non_empty():
    """Verifies correct band order (B02, B03, B04, B11, B12) and no empty bands."""
    repl_json = list(REPLACEMENT_DIR.glob("PILOT_04_NORTH_REPLACEMENT*.json"))[0]
    meta = json.loads(repl_json.read_text(encoding="utf-8"))
    assert meta["extraction"]["band_order"] == ["B02", "B03", "B04", "B11", "B12"]

    repl_tif = list(REPLACEMENT_DIR.glob("PILOT_04_NORTH_REPLACEMENT*.tif"))[0]
    with rasterio.open(repl_tif) as src:
        arr = src.read()
        for idx in range(5):
            b_arr = arr[idx]
            assert np.sum(b_arr > 0) > 1000, f"Band {idx+1} appears empty"


def test_replacement_zero_fill_and_spatial_coverage():
    """Verifies replacement zero_fill_pct <= 1.0% (specifically 0.0%) and complete spatial coverage."""
    repl_tif = list(REPLACEMENT_DIR.glob("PILOT_04_NORTH_REPLACEMENT*.tif"))[0]
    with rasterio.open(repl_tif) as src:
        arr = src.read()
        all_zero_mask = (arr == 0.0).all(axis=0)
        zero_fill_count = int(np.sum(all_zero_mask))
        zero_fill_pct = (zero_fill_count / (512 * 512)) * 100.0

        assert zero_fill_pct <= 1.0, f"Replacement zero-fill {zero_fill_pct:.2f}% exceeds 1.0% threshold"
        assert zero_fill_pct == 0.0, f"Expected 0.0% zero-fill, got {zero_fill_pct:.4f}%"


def test_strengthened_zero_fill_rejection_detection():
    """Verifies that the strengthened validator detects large zero regions and flags them."""
    from scripts.audit_sentinel_pilot_quality_v2 import audit_spatial_coverage_strengthened

    # Mock truncated raster
    dummy_arr = np.ones((5, 512, 512), dtype=np.float32)
    dummy_arr[:, :, :300] = 0.0  # >50% zero fill

    orig_p04_tif = list(CHIPS_DIR.glob("*PILOT_04_NORTH*.tif"))[0]
    with rasterio.open(orig_p04_tif) as src:
        res = audit_spatial_coverage_strengthened(src, dummy_arr, 31.66, 71.15)
        assert res["is_swath_truncated"] is True
        assert res["rejection_flag"] == "REJECT_SWATH_TRUNCATION"
        assert res["zero_fill_pct"] > 1.0


def test_strict_unlabeled_policy_across_replacement():
    """Verifies zero ground-truth fire class labels in replacement metadata."""
    forbidden_classes = ["Industrial Fire", "Forest Fire", "Agricultural Fire", "Other Thermal Source"]
    for json_path in REPLACEMENT_DIR.glob("*.json"):
        content = json_path.read_text(encoding="utf-8")
        assert "client_secret" not in content.lower()
        assert "access_token" not in content.lower()
        assert "bearer" not in content.lower()

        data = json.loads(content)
        assert data["label_status"] == "UNLABELED"
        assert data["firms_metadata"]["association_status"] == "candidate_context_only"

        for fc in forbidden_classes:
            assert fc not in content


def test_no_synthetic_paths():
    """Verifies no synthetic or quarantined datasets are referenced in audit v2."""
    with open(AUDIT_V2_JSON_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "synthetic" not in content.lower()
    assert "quarantine" not in content.lower()
    assert "dior" not in content.lower()
    assert "fasdd" not in content.lower()


def test_audit_v2_artifacts_schema_and_contents():
    """Verifies schema, counts, and contents of pilot_quality_audit_v2.json, .csv, and summary_v2.md."""
    assert AUDIT_V2_JSON_PATH.exists()
    assert AUDIT_V2_CSV_PATH.exists()
    assert AUDIT_V2_MD_PATH.exists()

    with open(AUDIT_V2_JSON_PATH, "r", encoding="utf-8") as f:
        audit_json = json.load(f)

    assert audit_json["status"] == "STAGE_8.8_QUALITY_RESOLUTION_AUDIT_COMPLETE"
    assert audit_json["audit_version"] == "v2"
    assert audit_json["total_chips_audited"] == 21

    # Active pilot cohort
    active = audit_json["active_pilot_cohort_summary"]
    assert active["active_chips_count"] == 20
    assert active["ANNOTATION_READY"] == 20
    assert active["REQUIRES_REVIEW"] == 0
    assert active["REJECT"] == 0
    assert active["unique_scenes"] == 20
    assert active["unique_tiles"] == 20
    assert active["duplicates"] == 0

    # Overall audited
    assert audit_json["all_audited_chips_summary"]["ANNOTATION_READY"] == 20
    assert audit_json["all_audited_chips_summary"]["REJECT"] == 1

    # CSV checks
    with open(AUDIT_V2_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 21
        assert "zero_fill_pct" in reader.fieldnames
        assert "audit_role" in reader.fieldnames


def test_pilot_05_central_diagnostic_resolution():
    """Verifies that PILOT_05_CENTRAL resolution is backed by objective diagnostic data."""
    with open(AUDIT_V2_JSON_PATH, "r", encoding="utf-8") as f:
        audit_json = json.load(f)

    diag = audit_json["pilot_05_central_diagnostic_resolution"]
    assert diag["candidate_id"] == "PILOT_05_CENTRAL"
    assert diag["total_pixels_gt1"] == 1568
    assert diag["pct_pixels_gt1"] == pytest.approx(0.5981, abs=0.01)
    assert diag["center_target_clear"] is True
    assert diag["unobstructed_ground_pct"] > 95.0
    assert diag["resolution_status"] == "ANNOTATION_READY"


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
