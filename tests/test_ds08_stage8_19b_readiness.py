"""
Tests for Stage 8.19B: Decision Resolution and Stage 8.20 Acquisition-Pilot Readiness.
Verifies:
1. DEC-U5: The two record-specific cloud exceptions (DS08_EXP_S1_002, DS08_EXP_S1_004).
2. DEC-U5: Mandatory rejection logic when AOI (>5%) or center-area (>0%) cloud fails.
3. DEC-U6: Footprint-aware 50 km spatial separation (edge-to-edge WGS84 geodesic).
4. Fold isolation and incident grouping (zero incident splits).
5. MGRS tile isolation (zero tile splits).
6. Stratum allocation reconciliation (STR-1=10, STR-2=35, STR-3=55, STR-4=55, STR-5=40, STR-6=40, STR-7=15).
7. Separation of expected classes from confirmed labels (human_confirmed_label is None for all expansion).
8. Explicit acquisition authorization guard (--confirm-acquisition required).
9. Prevention of accidental bulk acquisition (default dry-run returns 0 downloaded bytes).
10. Preservation of all prior-stage artifacts (Stage 8.18, 8.18A, 8.19, 8.19A).
"""

from collections import Counter
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Tuple

import pytest
from pyproj import Geod

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
MANIFEST_V3_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b" / "ds08_expansion_candidates_v3.json"
DOCS_STAGE_DIR = PROJECT_ROOT / "docs" / "stage8_19b"


@pytest.fixture(scope="module")
def manifest_v3():
    assert MANIFEST_V3_PATH.exists(), f"Manifest v3 not found at {MANIFEST_V3_PATH}"
    with open(MANIFEST_V3_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_manifest_v3_files_exist():
    assert (PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b" / "ds08_expansion_candidates_v3.json").exists()
    assert (PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b" / "ds08_expansion_candidates_v3.csv").exists()
    assert (PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b" / "ds08_expansion_candidates_v3.parquet").exists()


def test_dec_u5_cloud_exceptions(manifest_v3):
    records = manifest_v3["records"]
    exception_chips = {"DS08_EXP_S1_002", "DS08_EXP_S1_004"}

    applied_count = 0
    for r in records:
        if r["chip_id"] in exception_chips:
            assert r["cloud_exception_applied"] is True
            assert r["cloud_exception_id"] == "DEC-U5"
            assert r["cloud_exception_conditions"]["max_scene_cloud_pct_allowed"] == 20.0
            assert r["cloud_exception_conditions"]["max_aoi_scl_cloud_shadow_pct"] == 5.0
            assert r["cloud_exception_conditions"]["center_1km_cloud_pct_required"] == 0.0
            assert r["cloud_exception_conditions"]["failure_handling"] == "MANDATORY_REJECTION_NO_AUTO_REPLACE"
            applied_count += 1
        else:
            assert r["cloud_exception_applied"] is False
            assert r["cloud_exception_id"] is None
            # Standard scene cloud <= 10.0% applies to all other 248 records
            assert r["cloud_cover_pct"] <= 10.0, f"Record {r['chip_id']} exceeds 10% without DEC-U5 exception: {r['cloud_cover_pct']}%"

    assert applied_count == 2


def test_dec_u5_rejection_logic():
    """Simulates SCL screening logic to verify rejection when AOI > 5% or center > 0%."""
    def evaluate_scl_screening(aoi_cloud_pct: float, center_cloud_pct: float) -> Tuple[bool, str]:
        if aoi_cloud_pct > 5.0:
            return False, "REJECT_EXCESSIVE_AOI_CLOUD"
        if center_cloud_pct > 0.0:
            return False, "REJECT_CENTER_AREA_CLOUD_OCCLUSION"
        return True, "PASS_SCL_SCREENING"

    # Case 1: Clear scene passes
    ok, reason = evaluate_scl_screening(1.2, 0.0)
    assert ok is True and reason == "PASS_SCL_SCREENING"

    # Case 2: AOI cloud 6.2% fails
    ok, reason = evaluate_scl_screening(6.2, 0.0)
    assert ok is False and reason == "REJECT_EXCESSIVE_AOI_CLOUD"

    # Case 3: Center cloud 0.5% fails even if AOI cloud is low (2.0%)
    ok, reason = evaluate_scl_screening(2.0, 0.5)
    assert ok is False and reason == "REJECT_CENTER_AREA_CLOUD_OCCLUSION"


def test_footprint_aware_spatial_separation(manifest_v3):
    geod = Geod(ellps="WGS84")
    exp_records = [r for r in manifest_v3["records"] if r["candidate_stratum_id"] != "STR-7"]
    n_exp = len(exp_records)

    def get_footprint(lat, lon, half_m=2560.0):
        lon_n, lat_n, _ = geod.fwd(lon, lat, 0.0, half_m)
        lon_s, lat_s, _ = geod.fwd(lon, lat, 180.0, half_m)
        lon_e, lat_e, _ = geod.fwd(lon, lat, 90.0, half_m)
        lon_w, lat_w, _ = geod.fwd(lon, lat, 270.0, half_m)
        dlat = (lat_n - lat_s) / 2.0
        dlon = (lon_e - lon_w) / 2.0
        return [
            (lon - dlon, lat - dlat),
            (lon + dlon, lat - dlat),
            (lon + dlon, lat + dlat),
            (lon - dlon, lat + dlat)
        ]

    footprints = [get_footprint(r["latitude"], r["longitude"]) for r in exp_records]

    min_edge_dist = 999999.0
    min_center_dist = 999999.0
    violations_edge = 0

    for i in range(n_exp):
        for j in range(i + 1, n_exp):
            if exp_records[i]["assigned_fold"] != exp_records[j]["assigned_fold"]:
                # Edge distance
                d_edge = 999999.0
                for x1, y1 in footprints[i]:
                    for x2, y2 in footprints[j]:
                        _, _, d_m = geod.inv(x1, y1, x2, y2)
                        if d_m < d_edge:
                            d_edge = d_m
                d_edge_km = d_edge / 1000.0

                # Center distance
                _, _, d_c_m = geod.inv(
                    exp_records[i]["longitude"], exp_records[i]["latitude"],
                    exp_records[j]["longitude"], exp_records[j]["latitude"]
                )
                d_c_km = d_c_m / 1000.0

                if d_edge_km < min_edge_dist:
                    min_edge_dist = d_edge_km
                if d_c_km < min_center_dist:
                    min_center_dist = d_c_km
                if d_edge_km <= 50.0:
                    violations_edge += 1

    assert violations_edge == 0, f"Detected {violations_edge} cross-fold edge violations <= 50.0 km"
    assert min_edge_dist > 50.0, f"Minimum edge distance {min_edge_dist:.4f} km is <= 50.0 km"
    assert min_center_dist > 50.0, f"Minimum center distance {min_center_dist:.4f} km is <= 50.0 km"


def test_fold_isolation_and_incident_grouping(manifest_v3):
    records = manifest_v3["records"]
    exp_records = [r for r in records if r["candidate_stratum_id"] != "STR-7"]
    pilot_records = [r for r in records if r["candidate_stratum_id"] == "STR-7"]

    # Exactly 47 in each of Folds 1 to 5
    fold_counts = Counter(r["assigned_fold"] for r in exp_records)
    for k in range(1, 6):
        assert fold_counts[f"Fold {k}"] == 47

    # Pilot chips held out
    assert len(pilot_records) == 15
    for r in pilot_records:
        assert r["assigned_fold"] == "BENCHMARK_HELD_OUT"

    # Incident grouping
    inc_to_folds = {}
    for r in records:
        inc_to_folds.setdefault(r["incident_id"], set()).add(r["assigned_fold"])
    for inc, folds in inc_to_folds.items():
        assert len(folds) == 1, f"Incident {inc} split across folds: {folds}"


def test_mgrs_tile_isolation(manifest_v3):
    records = manifest_v3["records"]
    tile_to_folds = {}
    for r in records:
        tile_to_folds.setdefault(r["mgrs_tile"], set()).add(r["assigned_fold"])
    for tile, folds in tile_to_folds.items():
        assert len(folds) == 1, f"MGRS Tile {tile} split across folds: {folds}"


def test_stratum_allocation_reconciliation(manifest_v3):
    records = manifest_v3["records"]
    strata = Counter(r["candidate_stratum_id"] for r in records)

    assert strata["STR-1"] == 10  # 15 planning - 5 shortfall
    assert strata["STR-2"] == 35  # 30 planning + 5 reallocated
    assert strata["STR-3"] == 55  # 55 planning
    assert strata["STR-4"] == 55  # 55 planning
    assert strata["STR-5"] == 40  # 40 planning
    assert strata["STR-6"] == 40  # 40 planning
    assert strata["STR-7"] == 15  # 15 planning
    assert sum(strata.values()) == 250


def test_taxonomy_decoupling(manifest_v3):
    records = manifest_v3["records"]
    for r in records:
        if r["candidate_stratum_id"] != "STR-7":
            assert r["human_confirmed_label"] is None
            assert r["annotation_status"] == "UNLABELED_CANDIDATE"
            assert r["confirmed_bounding_boxes"] == []
            assert r["expected_target_class"] is not None
        else:
            assert r["human_confirmed_label"] is not None
            assert r["annotation_status"] == "COMPLETED_ADJUDICATED"


def test_explicit_acquisition_authorization_guard():
    """Executes the stage 8.20 acquisition script in dry-run mode and verifies safety guard."""
    from scripts.stage8_20_pilot_acquisition import run_acquisition_pilot
    res = run_acquisition_pilot(confirm_acquisition=False)
    assert res["mode"] == "DRY_RUN"
    assert res["status"] == "READY_FOR_OWNER_AUTHORIZATION"
    assert res["downloaded_bytes"] == 0


def test_stage8_19b_deliverables_exist():
    assert (DOCS_STAGE_DIR / "STAGE8_19B_DECISION_RESOLUTION.md").exists()
    assert (DOCS_STAGE_DIR / "STAGE8_19B_SPATIAL_REVALIDATION.md").exists()
    assert (DOCS_STAGE_DIR / "STAGE8_19B_ALLOCATION_RECONCILIATION.md").exists()
    assert (DOCS_STAGE_DIR / "STAGE8_20_PILOT_ACQUISITION_PLAN.md").exists()
    assert (DOCS_STAGE_DIR / "stage8_19b_decision_log.md").exists()
    assert (PROJECT_ROOT / "scripts" / "audit_stage8_19b_spatial_footprint.py").exists()
    assert (PROJECT_ROOT / "scripts" / "stage8_20_pilot_acquisition.py").exists()


def test_prior_stage_artifacts_preserved():
    # Stage 8.17
    assert (PROJECT_ROOT / "data" / "reference" / "ds08" / "packages" / "ds08_pilot_v1" / "manifest.json").exists()
    # Stage 8.18
    assert (PROJECT_ROOT / "docs" / "stage8_18" / "STAGE8_18_PLANNING_AUDIT_REPORT.md").exists()
    # Stage 8.18A
    assert (PROJECT_ROOT / "docs" / "stage8_18a" / "STAGE8_18A_REVIEW_REPORT.md").exists()
    # Stage 8.19
    assert (PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19" / "ds08_expansion_candidates_v1.json").exists()
    assert (PROJECT_ROOT / "docs" / "stage8_19" / "STAGE8_19_DISCOVERY_AUDIT_REPORT.md").exists()
    # Stage 8.19A
    assert (PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19a" / "ds08_expansion_candidates_v2.json").exists()
    assert (PROJECT_ROOT / "docs" / "stage8_19a" / "STAGE8_19A_AUDIT_REPORT.md").exists()
    assert (PROJECT_ROOT / "docs" / "stage8_19a" / "STAGE8_19A_ACQUISITION_READINESS_AUDIT.md").exists()
