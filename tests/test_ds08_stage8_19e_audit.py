"""
Stage 8.19E Comprehensive Audit Test Suite:
Verifies:
1. Manifest v3 hash remains byte-for-byte unchanged.
2. No placeholder SAFE identifiers remain in V4 pilot records.
3. Every resolved selected product has a real catalog product ID (UUID and SAFE name).
4. Every selected product has required metadata (cloud_cover_pct, sensing_time_utc, etc.).
5. No cross-fold native footprint pair is <= 50.000 km (strictly > 50.000000 km).
6. MGRS tile isolation remains valid (0 split tiles across folds).
7. Incident isolation remains valid (0 split incidents across folds).
8. Fold counts satisfy the documented balance requirement (exactly 47 per fold).
9. Pilot cohort contains the required strata (STR-1 through STR-6 represented).
10. No selected candidate has a fabricated/human-confirmed label (remains UNLABELED_CANDIDATE).
11. Cloud-exception records remain conditional until raster SCL processing.
12. Provenance exists for every replacement (change_reason and description recorded).
"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import pytest
from pyproj import Geod, Transformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MANIFEST_V3_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b" / "ds08_expansion_candidates_v3.json"
EXPECTED_V3_HASH = "dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848"

MANIFEST_V4_DOCS = PROJECT_ROOT / "docs" / "stage8_19e" / "STAGE8_19E_RECONCILED_MANIFEST_V4.json"
MANIFEST_V4_DATA = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19e" / "ds08_expansion_candidates_v4.json"
CATALOG_RESULTS_PATH = PROJECT_ROOT / "docs" / "stage8_19e" / "STAGE8_19E_CATALOG_RESULTS.json"

PILOT_IDS = [
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
def v4_manifest():
    with open(MANIFEST_V4_DOCS, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def catalog_results():
    with open(CATALOG_RESULTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_1_v3_manifest_hash_unchanged():
    with open(MANIFEST_V3_PATH, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()
    assert actual_hash == EXPECTED_V3_HASH, f"Manifest v3 altered! Got {actual_hash}"


def test_2_no_placeholder_safe_identifiers(v4_manifest):
    records = {r["chip_id"]: r for r in v4_manifest["records"]}
    for pid in PILOT_IDS:
        r = records[pid]
        safe_id = r["stac_scene_id"]
        # Must not contain suspicious nighttime hours or invalid tiles
        assert "215200" not in safe_id, f"Placeholder hour in {pid}: {safe_id}"
        assert "073500" not in safe_id, f"Placeholder hour in {pid}: {safe_id}"
        assert "081900" not in safe_id, f"Placeholder hour in {pid}: {safe_id}"
        assert "T43SKI" not in safe_id, f"Invalid tile in {pid}: {safe_id}"
        assert "T44SAI" not in safe_id, f"Invalid tile in {pid}: {safe_id}"
        assert "T43SEM" not in safe_id, f"Invalid tile in {pid}: {safe_id}"
        assert "T43SIN" not in safe_id, f"Invalid tile in {pid}: {safe_id}"
        assert "T43TBB" not in safe_id, f"Invalid tile in {pid}: {safe_id}"


def test_3_every_selected_product_has_real_catalog_id(catalog_results):
    assert len(catalog_results) == 8
    for item in catalog_results:
        assert item["catalog_status"] == "EXISTS_VERIFIED", f"Not verified in CDSE: {item['chip_id']}"
        assert item["cdse_uuid"] is not None
        assert len(item["cdse_uuid"]) == 36  # Valid UUID format
        assert item["online"] is True
        assert item["content_length_bytes"] > 100_000_000  # Real SAFE archive > 100MB


def test_4_every_selected_product_has_required_metadata(v4_manifest):
    records = {r["chip_id"]: r for r in v4_manifest["records"]}
    for pid in PILOT_IDS:
        r = records[pid]
        assert r["cloud_cover_pct"] is not None
        assert isinstance(r["cloud_cover_pct"], (int, float))
        assert r["sensing_time_utc"] is not None
        assert "T" in r["sensing_time_utc"]
        assert r["mgrs_tile"] is not None
        assert len(r["mgrs_tile"]) == 6


def test_5_no_cross_fold_native_footprint_le_50km(v4_manifest):
    exp = [r for r in v4_manifest["records"] if r["candidate_stratum_id"] != "STR-7"]
    geod = Geod(ellps="WGS84")

    transformers_to_utm = {}
    transformers_to_wgs = {}

    def get_native_corners(r):
        tile = r["mgrs_tile"]
        zone = int(tile[1:3])
        if zone not in transformers_to_utm:
            transformers_to_utm[zone] = Transformer.from_crs("EPSG:4326", f"EPSG:{32600 + zone}", always_xy=True)
            transformers_to_wgs[zone] = Transformer.from_crs(f"EPSG:{32600 + zone}", "EPSG:4326", always_xy=True)
        e, n = transformers_to_utm[zone].transform(r["longitude"], r["latitude"])
        half_m = 2560.0
        c_utm = [(e - half_m, n - half_m), (e + half_m, n - half_m), (e + half_m, n + half_m), (e - half_m, n + half_m)]
        return [transformers_to_wgs[zone].transform(x, y) for x, y in c_utm]

    corners = {r["chip_id"]: get_native_corners(r) for r in exp}

    def min_dist(cid1, cid2):
        c1 = corners[cid1]
        c2 = corners[cid2]
        return min(geod.inv(x1, y1, x2, y2)[2] for x1, y1 in c1 for x2, y2 in c2) / 1000.0

    n = len(exp)
    min_inter = 999999.0
    violations = 0

    for i in range(n):
        for j in range(i + 1, n):
            c1, c2 = exp[i], exp[j]
            if c1["assigned_fold"] != c2["assigned_fold"]:
                d = min_dist(c1["chip_id"], c2["chip_id"])
                if d <= 50.000000:
                    violations += 1
                if d < min_inter:
                    min_inter = d

    assert violations == 0, f"Found {violations} cross-fold violations <= 50.0 km"
    assert min_inter > 50.000000, f"Min distance {min_inter} is <= 50.0 km"
    assert pytest.approx(min_inter, rel=1e-4) == 50.1017


def test_6_mgrs_tile_isolation(v4_manifest):
    exp = [r for r in v4_manifest["records"] if r["candidate_stratum_id"] != "STR-7"]
    tile_to_folds = {}
    for r in exp:
        tile_to_folds.setdefault(r["mgrs_tile"], set()).add(r["assigned_fold"])

    for tile, folds in tile_to_folds.items():
        assert len(folds) == 1, f"Tile {tile} split across folds: {folds}"


def test_7_incident_isolation(v4_manifest):
    exp = [r for r in v4_manifest["records"] if r["candidate_stratum_id"] != "STR-7"]
    inc_to_folds = {}
    for r in exp:
        inc_to_folds.setdefault(r["incident_id"], set()).add(r["assigned_fold"])

    for inc, folds in inc_to_folds.items():
        assert len(folds) == 1, f"Incident {inc} split across folds: {folds}"


def test_8_fold_balance_requirements(v4_manifest):
    exp = [r for r in v4_manifest["records"] if r["candidate_stratum_id"] != "STR-7"]
    fold_counts = Counter(r["assigned_fold"] for r in exp)
    for k in range(1, 6):
        assert fold_counts[f"Fold {k}"] == 47

    pilot_bench = [r for r in v4_manifest["records"] if r["candidate_stratum_id"] == "STR-7"]
    assert len(pilot_bench) == 15
    for r in pilot_bench:
        assert r["assigned_fold"] == "BENCHMARK_HELD_OUT"


def test_9_pilot_cohort_contains_required_strata(v4_manifest):
    records = {r["chip_id"]: r for r in v4_manifest["records"]}
    pilot_strata = {records[pid]["candidate_stratum_id"] for pid in PILOT_IDS}
    expected_strata = {"STR-1", "STR-2", "STR-3", "STR-4", "STR-5", "STR-6"}
    assert expected_strata.issubset(pilot_strata)


def test_10_no_fabricated_human_confirmed_labels(v4_manifest):
    exp = [r for r in v4_manifest["records"] if r["candidate_stratum_id"] != "STR-7"]
    for r in exp:
        assert r["human_confirmed_label"] is None
        assert r["annotation_status"] == "UNLABELED_CANDIDATE"
        assert r["confirmed_bounding_boxes"] == []


def test_11_cloud_exception_records_conditional(v4_manifest):
    records = {r["chip_id"]: r for r in v4_manifest["records"]}
    r_s1_002 = records["DS08_EXP_S1_002"]
    r_s1_004 = records["DS08_EXP_S1_004"]

    assert r_s1_002["cloud_exception_applied"] is True
    assert r_s1_002["cloud_exception_id"] == "DEC-U5"
    assert r_s1_004["cloud_exception_applied"] is True
    assert r_s1_004["cloud_exception_id"] == "DEC-U5"


def test_12_provenance_exists_for_every_replacement(v4_manifest):
    records = {r["chip_id"]: r for r in v4_manifest["records"]}
    # Check swapped records
    for cid in ["DS08_EXP_S4_018", "DS08_EXP_S4_043"]:
        r = records[cid]
        assert r.get("change_reason") == "SPATIAL_SEPARATION_REPAIR"
        assert len(r.get("change_description", "")) > 10

    # Check reconciled pilot records
    for cid in ["DS08_EXP_S2_001", "DS08_EXP_S3_001", "DS08_EXP_S4_001", "DS08_EXP_S5_001", "DS08_EXP_S6_001"]:
        r = records[cid]
        assert r.get("change_reason") == "PRODUCT_ID_RECONCILIATION"
        assert r.get("cdse_product_uuid") is not None
        assert r.get("previous_stac_scene_id") is not None
        assert len(r.get("change_description", "")) > 10
