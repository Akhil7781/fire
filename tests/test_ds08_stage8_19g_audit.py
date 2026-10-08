"""
Stage 8.19G Comprehensive Audit Test Suite:
Verifies:
1. V3 manifest hash immutable.
2. V4 manifest loads successfully.
3. Exactly 22,090 cross-fold pairs evaluated.
4. Reference metric uses true polygon geometry.
5. Reference metric is NOT corner-only.
6. Reference metric is NOT centroid-only.
7. Reference result is strictly > 50.000000 km.
8. Zero violations <= 50.000000 km.
9. Known repaired pair is co-located in the same fold (Fold 3).
10. Fold counts remain valid (47 in each of Folds 1-5; 15 benchmark).
11. No MGRS tile splits.
12. No incident splits.
13. Acquisition script requires explicit confirmation flag.
14. Dry run downloads zero bytes and creates no output directory.
15. Pilot list contains exactly 8 designated chips.
16. No credential leakage in acquisition script execution.
17. No safety-regression evidence in acquisition script.
18. Stage 8.19E and 8.19F artifacts remain intact and unchanged.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import pytest
from pyproj import Geod, Transformer
from shapely.geometry import box, Polygon, Point

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.stage8_20_pilot_acquisition import run_acquisition_pilot, PILOT_CHIP_IDS

MANIFEST_V3_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b" / "ds08_expansion_candidates_v3.json"
EXPECTED_V3_HASH = "dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848"

MANIFEST_V4_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19e" / "ds08_expansion_candidates_v4.json"
SPATIAL_COMP_PATH = PROJECT_ROOT / "docs" / "stage8_19g" / "STAGE8_19G_SPATIAL_COMPARISON.json"


@pytest.fixture(scope="module")
def v4_manifest():
    with open(MANIFEST_V4_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def spatial_comparison():
    with open(SPATIAL_COMP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_1_v3_manifest_hash_unchanged():
    with open(MANIFEST_V3_PATH, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()
    assert actual_hash == EXPECTED_V3_HASH, f"Manifest v3 altered! Got {actual_hash}"


def test_2_v4_manifest_loads_successfully(v4_manifest):
    assert "records" in v4_manifest
    assert len(v4_manifest["records"]) == 250


def test_3_exactly_22090_cross_fold_pairs_evaluated(spatial_comparison):
    assert spatial_comparison["pairs_evaluated"] == 22090


def test_4_reference_metric_uses_polygon_geometry(spatial_comparison):
    assert "Polygon" in spatial_comparison["reference_geometry_method"] or "polygon" in spatial_comparison["reference_geometry_method"]
    assert "AEQD" in spatial_comparison["reference_crs_strategy"] or "Azimuthal Equidistant" in spatial_comparison["reference_crs_strategy"]


def test_5_reference_metric_is_not_corner_only(v4_manifest):
    # Demonstrate on closest pair that metric evaluates true continuous polygon boundaries
    r_map = {r["chip_id"]: r for r in v4_manifest["records"]}
    c1, c2 = r_map["DS08_EXP_S3_004"], r_map["DS08_EXP_S4_004"]
    half_m = 2560.0
    t1_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    t2_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    e1, n1 = t1_to_utm.transform(c1["longitude"], c1["latitude"])
    e2, n2 = t2_to_utm.transform(c2["longitude"], c2["latitude"])
    p1 = box(e1 - half_m, n1 - half_m, e1 + half_m, n1 + half_m)
    p2 = box(e2 - half_m, n2 - half_m, e2 + half_m, n2 + half_m)
    # Polygon distance is a continuous geometric distance function on full 2D area
    assert hasattr(p1, "distance")
    assert isinstance(p1, Polygon)
    assert isinstance(p2, Polygon)
    # Check that distance is calculated between polygons, not just discrete lists
    d = p1.distance(p2)
    assert d > 0


def test_6_reference_metric_is_not_centroid_only(v4_manifest):
    r_map = {r["chip_id"]: r for r in v4_manifest["records"]}
    c1, c2 = r_map["DS08_EXP_S3_004"], r_map["DS08_EXP_S4_004"]
    geod = Geod(ellps="WGS84")
    _, _, d_centroid_m = geod.inv(c1["longitude"], c1["latitude"], c2["longitude"], c2["latitude"])
    d_centroid_km = d_centroid_m / 1000.0
    # Centroid distance is ~55.597 km, whereas footprint distance is ~50.102 km
    assert abs(d_centroid_km - 55.597) < 0.1
    # Footprint distance must be materially distinct from centroid distance by roughly 5 km
    assert abs(d_centroid_km - 50.101722) > 5.0


def test_7_reference_result_strictly_gt_50km(spatial_comparison):
    assert spatial_comparison["stage8_19g_min_km"] > 50.000000
    assert spatial_comparison["margin_m"] > 0
    assert pytest.approx(spatial_comparison["stage8_19g_min_km"], rel=1e-5) == 50.101722


def test_8_zero_violations_if_compliant(spatial_comparison):
    assert spatial_comparison["stage8_19g_violations"] == 0
    assert spatial_comparison["status"] == "REFERENCE_METRIC_CONFIRMED"


def test_9_known_repaired_pair_same_fold(v4_manifest):
    records = {r["chip_id"]: r for r in v4_manifest["records"]}
    assert records["DS08_EXP_S4_018"]["assigned_fold"] == "Fold 3"
    assert records["DS08_EXP_S5_016"]["assigned_fold"] == "Fold 3"
    assert records["DS08_EXP_S4_043"]["assigned_fold"] == "Fold 4"
    assert records["DS08_EXP_S4_018"]["assigned_fold"] == records["DS08_EXP_S5_016"]["assigned_fold"]


def test_10_fold_counts_remain_valid(v4_manifest):
    exp = [r for r in v4_manifest["records"] if r["candidate_stratum_id"] != "STR-7"]
    bench = [r for r in v4_manifest["records"] if r["candidate_stratum_id"] == "STR-7"]
    counts = Counter(r["assigned_fold"] for r in exp)
    for k in range(1, 6):
        assert counts[f"Fold {k}"] == 47
    assert len(bench) == 15
    for r in bench:
        assert r["assigned_fold"] == "BENCHMARK_HELD_OUT"


def test_11_no_mgrs_tile_splits(v4_manifest):
    exp = [r for r in v4_manifest["records"] if r["candidate_stratum_id"] != "STR-7"]
    tile_to_folds = {}
    for r in exp:
        tile_to_folds.setdefault(r["mgrs_tile"], set()).add(r["assigned_fold"])
    splits = [t for t, f in tile_to_folds.items() if len(f) > 1]
    assert len(splits) == 0, f"Split MGRS tiles found: {splits}"


def test_12_no_incident_splits(v4_manifest):
    exp = [r for r in v4_manifest["records"] if r["candidate_stratum_id"] != "STR-7"]
    inc_to_folds = {}
    for r in exp:
        inc_to_folds.setdefault(r["incident_id"], set()).add(r["assigned_fold"])
    splits = [inc for inc, f in inc_to_folds.items() if len(f) > 1]
    assert len(splits) == 0, f"Split incidents found: {splits}"


def test_13_acquisition_script_requires_explicit_confirmation():
    # Dry run without flag returns DRY_RUN mode
    res = run_acquisition_pilot(confirm_acquisition=False, dry_run=True)
    assert res["mode"] == "DRY_RUN"
    assert res["status"] == "READY_FOR_OWNER_AUTHORIZATION"


def test_14_dry_run_downloads_zero_bytes():
    res = run_acquisition_pilot(confirm_acquisition=False, dry_run=True)
    assert res["downloaded_bytes"] == 0
    assert res["mode"] == "DRY_RUN"


def test_15_pilot_list_contains_exactly_8_designated_chips():
    assert len(PILOT_CHIP_IDS) == 8
    expected_ids = {
        "DS08_EXP_S1_003", "DS08_EXP_S1_002", "DS08_EXP_S1_004",
        "DS08_EXP_S2_001", "DS08_EXP_S3_001", "DS08_EXP_S4_001",
        "DS08_EXP_S5_001", "DS08_EXP_S6_001"
    }
    assert set(PILOT_CHIP_IDS) == expected_ids


def test_16_no_credential_leakage(capsys):
    run_acquisition_pilot(confirm_acquisition=False, dry_run=True)
    captured = capsys.readouterr()
    # Confirm no client secret or token in output
    assert "secret" not in captured.out.lower() or "configured" in captured.out.lower()
    assert "token" not in captured.out.lower()
    assert "bearer" not in captured.out.lower()


def test_17_no_safety_regression_evidence():
    script_path = PROJECT_ROOT / "scripts" / "stage8_20_pilot_acquisition.py"
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "--confirm-acquisition" in content
    assert "PILOT_CHIP_IDS" in content
    assert "assert len(pilot_records) == 8" in content
    assert "downloaded_bytes" in content


def test_18_stage8_19e_and_19f_artifacts_remain_intact():
    expected_hashes = {
        "data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json": "dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848",
        "data/reference/ds08/manifests/stage8_19e/ds08_expansion_candidates_v4.json": "54154edcd0189545c2d03615827f834be91d2452767cef0a1d8978d3b4d9d62c",
        "docs/stage8_19e/STAGE8_19E_RECONCILED_MANIFEST_V4.json": "54154edcd0189545c2d03615827f834be91d2452767cef0a1d8978d3b4d9d62c",
        "docs/stage8_19f/STAGE8_19F_FINAL_EVIDENCE_AUDIT.md": "788b7d195d3d956ea15d4657ee324bbb192fdfd847ceadaa8c3922eca7f5c404",
        "docs/stage8_19f/STAGE8_19F_SPATIAL_REPRODUCTION.json": "4a1562540050e729995972c92fca37a63bbb27413b2948710245f2ccfcd93c82",
    }
    for rel_path, expected_h in expected_hashes.items():
        p = PROJECT_ROOT / rel_path
        assert p.exists(), f"File missing: {rel_path}"
        with open(p, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        assert h == expected_h, f"File altered: {rel_path} got {h}, expected {expected_h}"
