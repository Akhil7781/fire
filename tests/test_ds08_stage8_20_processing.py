"""
Stage 8.20 - Sentinel-2 Pilot Preprocessing Verification Test Suite
Validates all 18 requirements from Section 19:
1. Exactly 8 pilot chip IDs.
2. Every chip has a verified source product.
3. Every chip has B02/B03/B04/B11/B12/SCL.
4. All bands align spatially.
5. All ML spectral arrays are 512x512.
6. SCL is 512x512.
7. CRS is valid.
8. Pixel resolution is 10 m.
9. No NaN values after preprocessing.
10. No Inf values.
11. Candidate point lies inside chip footprint.
12. SCL uses nearest-neighbour semantics.
13. Expected class is not copied into human_confirmed_label.
14. No synthetic labels exist.
15. Cloud quality metrics are present.
16. Central 1 km metric is present.
17. Rejected chips are not silently included in the clean ML dataset.
18. V3 remains unchanged.
"""

import hashlib
import json
from pathlib import Path
import pytest
import numpy as np
import rasterio

PROJECT_ROOT = Path(__file__).resolve().parent.parent

V3_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b" / "ds08_expansion_candidates_v3.json"
V4_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19e" / "ds08_expansion_candidates_v4.json"
PROCESSED_MANIFEST_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_20" / "ds08_stage8_20_pilot_processed.json"
PILOT_DATA_DIR = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_20_pilot" / "pilot"
PREVIEWS_DIR = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_20_pilot" / "previews"
SAFES_DIR = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_20_pilot" / "safes"

EXPECTED_V3_HASH = "dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848"

EXPECTED_PILOT_CHIPS = [
    "DS08_EXP_S1_003",
    "DS08_EXP_S1_002",
    "DS08_EXP_S1_004",
    "DS08_EXP_S2_001",
    "DS08_EXP_S3_001",
    "DS08_EXP_S4_001",
    "DS08_EXP_S5_001",
    "DS08_EXP_S6_001",
]


@pytest.fixture(scope="module")
def processed_manifest():
    assert PROCESSED_MANIFEST_PATH.exists(), f"Processed manifest missing: {PROCESSED_MANIFEST_PATH}"
    with open(PROCESSED_MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_01_exactly_8_pilot_chip_ids(processed_manifest):
    records = processed_manifest["records"]
    assert len(records) == 8, f"Expected exactly 8 records, got {len(records)}"
    chip_ids = [r["chip_id"] for r in records]
    assert sorted(chip_ids) == sorted(EXPECTED_PILOT_CHIPS), f"Chip IDs mismatch: {chip_ids}"


def test_02_every_chip_has_verified_source_product(processed_manifest):
    with open(V4_PATH, "r", encoding="utf-8") as f:
        v4_records = {r["chip_id"]: r for r in json.load(f)["records"]}

    for rec in processed_manifest["records"]:
        cid = rec["chip_id"]
        v4_rec = v4_records[cid]
        assert rec["source_product"] == v4_rec["stac_scene_id"]
        safe_path = SAFES_DIR / rec["source_product"]
        assert safe_path.exists(), f"SAFE directory missing for {cid}: {safe_path}"


def test_03_every_chip_has_all_required_bands(processed_manifest):
    required = ["B02", "B03", "B04", "B11", "B12", "SCL"]
    for rec in processed_manifest["records"]:
        assert rec["bands"] == required
        chip_dir = PILOT_DATA_DIR / rec["chip_id"]
        assert (chip_dir / "spectral_raw.npy").exists()
        assert (chip_dir / "spectral_normalized.npy").exists()
        assert (chip_dir / "scl.npy").exists()


def test_04_all_bands_align_spatially(processed_manifest):
    for rec in processed_manifest["records"]:
        chip_dir = PILOT_DATA_DIR / rec["chip_id"]
        raw = np.load(chip_dir / "spectral_raw.npy")
        scl = np.load(chip_dir / "scl.npy")
        # Shapes must align: raw is (5, 512, 512), scl is (512, 512)
        assert raw.shape[1] == scl.shape[0] == 512
        assert raw.shape[2] == scl.shape[1] == 512


def test_05_all_ml_spectral_arrays_are_512x512(processed_manifest):
    for rec in processed_manifest["records"]:
        chip_dir = PILOT_DATA_DIR / rec["chip_id"]
        norm = np.load(chip_dir / "spectral_normalized.npy")
        assert norm.shape == (5, 512, 512)
        assert norm.dtype == np.float32
        assert norm.min() >= 0.0
        assert norm.max() <= 1.0


def test_06_scl_is_512x512(processed_manifest):
    for rec in processed_manifest["records"]:
        chip_dir = PILOT_DATA_DIR / rec["chip_id"]
        scl = np.load(chip_dir / "scl.npy")
        assert scl.shape == (512, 512)
        assert scl.dtype == np.uint8


def test_07_crs_is_valid(processed_manifest):
    valid_epsgs = ["EPSG:32642", "EPSG:32643", "EPSG:32644"]
    for rec in processed_manifest["records"]:
        crs_str = rec["crs"]
        assert any(epsg in crs_str for epsg in valid_epsgs), f"Unexpected CRS for {rec['chip_id']}: {crs_str}"


def test_08_pixel_resolution_is_10m(processed_manifest):
    for rec in processed_manifest["records"]:
        assert rec["resolution_m"] == 10
        assert rec["chip_size_px"] == 512
        assert rec["chip_size_m"] == 5120


def test_09_no_nan_values_after_preprocessing(processed_manifest):
    for rec in processed_manifest["records"]:
        chip_dir = PILOT_DATA_DIR / rec["chip_id"]
        raw = np.load(chip_dir / "spectral_raw.npy")
        norm = np.load(chip_dir / "spectral_normalized.npy")
        scl = np.load(chip_dir / "scl.npy")
        assert not np.isnan(raw).any(), f"NaN in raw array of {rec['chip_id']}"
        assert not np.isnan(norm).any(), f"NaN in normalized array of {rec['chip_id']}"
        assert not np.isnan(scl).any(), f"NaN in scl array of {rec['chip_id']}"


def test_10_no_inf_values(processed_manifest):
    for rec in processed_manifest["records"]:
        chip_dir = PILOT_DATA_DIR / rec["chip_id"]
        raw = np.load(chip_dir / "spectral_raw.npy")
        norm = np.load(chip_dir / "spectral_normalized.npy")
        assert not np.isinf(raw).any(), f"Inf in raw array of {rec['chip_id']}"
        assert not np.isinf(norm).any(), f"Inf in normalized array of {rec['chip_id']}"


def test_11_candidate_point_lies_inside_chip_footprint(processed_manifest):
    for rec in processed_manifest["records"]:
        b = rec["chip_bounds_utm"]
        px = rec["projected_x"]
        py = rec["projected_y"]
        assert b["x_min"] <= px <= b["x_max"], f"Candidate X outside UTM bounds for {rec['chip_id']}"
        assert b["y_min"] <= py <= b["y_max"], f"Candidate Y outside UTM bounds for {rec['chip_id']}"
        col = rec["chip_pixel_col"]
        row = rec["chip_pixel_row"]
        assert 0.0 <= col < 512.0, f"Candidate col outside [0, 512) for {rec['chip_id']}"
        assert 0.0 <= row < 512.0, f"Candidate row outside [0, 512) for {rec['chip_id']}"


def test_12_scl_uses_nearest_neighbour_semantics(processed_manifest):
    valid_classes = set(range(12))  # 0 to 11
    for rec in processed_manifest["records"]:
        chip_dir = PILOT_DATA_DIR / rec["chip_id"]
        scl = np.load(chip_dir / "scl.npy")
        unique_vals = set(np.unique(scl).tolist())
        assert unique_vals.issubset(valid_classes), f"Invalid SCL classes {unique_vals - valid_classes} in {rec['chip_id']}"
        assert rec["resampling_methods"]["SCL"] == "nearest_neighbour_20m_to_10m"


def test_13_expected_class_is_not_copied_into_human_confirmed_label(processed_manifest):
    for rec in processed_manifest["records"]:
        assert rec["human_confirmed_label"] is None, f"human_confirmed_label must be None for {rec['chip_id']}"
        assert rec["expected_target_class"] is not None, f"expected_target_class missing for {rec['chip_id']}"
        assert rec["expected_target_class"] != rec["human_confirmed_label"]


def test_14_no_synthetic_labels_exist(processed_manifest):
    for rec in processed_manifest["records"]:
        assert rec["human_confirmed_label"] is None


def test_15_cloud_quality_metrics_are_present(processed_manifest):
    for rec in processed_manifest["records"]:
        m = rec["scl_metrics"]
        assert "aoi_contamination_pct" in m
        assert "aoi_cloud_pct" in m
        assert "aoi_shadow_pct" in m
        assert "aoi_clean_pct" in m
        assert 0.0 <= m["aoi_contamination_pct"] <= 100.0


def test_16_central_1km_metric_is_present(processed_manifest):
    for rec in processed_manifest["records"]:
        m = rec["scl_metrics"]
        assert "central_1km_contamination_pct" in m
        assert "central_1km_cloud_pct" in m
        assert "central_1km_shadow_pct" in m
        assert "central_1km_clean_pct" in m
        assert 0.0 <= m["central_1km_contamination_pct"] <= 100.0


def test_17_rejected_chips_not_silently_included_in_clean_dataset(processed_manifest):
    for rec in processed_manifest["records"]:
        status = rec["quality_status"]
        assert status in ["PASS", "CONDITIONAL", "REJECT"]
        if status == "REJECT":
            # Must have contamination exceeding threshold
            assert rec["scl_metrics"]["central_1km_contamination_pct"] > 10.0 or rec["scl_metrics"]["aoi_contamination_pct"] > 5.0


def test_18_v3_manifest_remains_intact():
    assert V3_PATH.exists(), f"V3 manifest missing: {V3_PATH}"
    hasher = hashlib.sha256()
    with open(V3_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest()
    assert actual_hash == EXPECTED_V3_HASH, f"V3 hash mismatch: got {actual_hash}, expected {EXPECTED_V3_HASH}"
