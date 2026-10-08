"""
Tests for Stage 8.19A: DS08 Expansion Candidate Manifest v2 Audit and Reconciliation.
Verifies all 6 issues and 10 verification dimensions:
1. Exact fold table reconciliation (Folds 1-5 have 47 chips each = 235; STR-7 has 15; sum = 250).
2. Spatial split reconciliation with approved 50 km buffer (minimum inter-fold distance > 50.0 km).
3. Candidate vs confirmed label taxonomy decoupling (all 235 expansion labels null and UNLABELED_CANDIDATE).
4. ESA Sentinel-2 L2A product naming format regex (_Txxxxx_).
5. Temporal gaps (<= 48h for combustion strata) and cloud cover (<= 20.0%).
6. Geographic bounds and regional quotas (55/60/45/50/40 = 250).
7. Incident and scene grouping into identical folds.
8. DEC-U1 year separation and 2024 industrial fire quotas.
9. Preservation of Stage 8.19 prior artifacts.
10. Delivery of all Stage 8.19A documentation files.
"""

from collections import Counter
import json
import math
from pathlib import Path
import re

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_V2_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19a"
DOCS_V2_DIR = PROJECT_ROOT / "docs" / "stage8_19a"
REVIEW_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "review"

S2_SAFE_REGEX = re.compile(r"^S2[ABC]_MSIL2A_\d{8}T\d{6}_N\d{4}_R\d{3}_T[0-9A-Z]{5}_\d{8}T\d{6}\.SAFE$")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return R * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


@pytest.fixture(scope="module")
def manifest_v2():
    json_path = MANIFEST_V2_DIR / "ds08_expansion_candidates_v2.json"
    assert json_path.exists(), f"Manifest v2 JSON not found at {json_path}"
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_manifest_v2_files_exist():
    assert (MANIFEST_V2_DIR / "ds08_expansion_candidates_v2.json").exists()
    assert (MANIFEST_V2_DIR / "ds08_expansion_candidates_v2.csv").exists()
    assert (MANIFEST_V2_DIR / "ds08_expansion_candidates_v2.parquet").exists()


def test_record_counts_and_separation(manifest_v2):
    records = manifest_v2["records"]
    assert len(records) == 250
    assert manifest_v2["total_chips"] == 250
    assert manifest_v2["pilot_benchmark_held_out"] == 15
    assert manifest_v2["expansion_candidates_count"] == 235

    exp_records = [r for r in records if r["candidate_stratum_id"] != "STR-7"]
    pilot_records = [r for r in records if r["candidate_stratum_id"] == "STR-7"]
    assert len(exp_records) == 235
    assert len(pilot_records) == 15


def test_fold_table_exact_reconciliation(manifest_v2):
    records = manifest_v2["records"]
    exp_records = [r for r in records if r["candidate_stratum_id"] != "STR-7"]
    pilot_records = [r for r in records if r["candidate_stratum_id"] == "STR-7"]

    # Check 5 folds have exactly 47 chips
    fold_counts = Counter(r["assigned_fold"] for r in exp_records)
    for k in range(1, 6):
        fold_name = f"Fold {k}"
        assert fold_counts[fold_name] == 47, f"{fold_name} has {fold_counts[fold_name]} chips, expected 47"

    # Check pilot chips are held out
    for r in pilot_records:
        assert r["assigned_fold"] == "BENCHMARK_HELD_OUT"

    # Check strata totals
    strata_counts = Counter(r["candidate_stratum_id"] for r in records)
    assert strata_counts["STR-1"] == 10
    assert strata_counts["STR-2"] == 35
    assert strata_counts["STR-3"] == 55
    assert strata_counts["STR-4"] == 55
    assert strata_counts["STR-5"] == 40
    assert strata_counts["STR-6"] == 40
    assert strata_counts["STR-7"] == 15
    assert sum(strata_counts.values()) == 250


def test_spatial_split_50km_buffer(manifest_v2):
    exp_records = [r for r in manifest_v2["records"] if r["candidate_stratum_id"] != "STR-7"]
    n_exp = len(exp_records)

    min_inter_fold_dist = 999999.0
    violations = 0

    for i in range(n_exp):
        for j in range(i + 1, n_exp):
            f1 = exp_records[i]["assigned_fold"]
            f2 = exp_records[j]["assigned_fold"]
            if f1 != f2:
                dist = haversine_km(
                    exp_records[i]["latitude"], exp_records[i]["longitude"],
                    exp_records[j]["latitude"], exp_records[j]["longitude"]
                )
                if dist < min_inter_fold_dist:
                    min_inter_fold_dist = dist
                if dist <= 50.0:
                    violations += 1

    assert violations == 0, f"Detected {violations} cross-fold pairs within 50 km buffer!"
    assert min_inter_fold_dist > 50.0, f"Minimum inter-fold distance {min_inter_fold_dist:.2f} km is <= 50.0 km"


def test_incident_and_scene_grouping(manifest_v2):
    records = manifest_v2["records"]
    
    # Check incidents
    incident_folds = {}
    for r in records:
        inc = r["incident_id"]
        f = r["assigned_fold"]
        if inc not in incident_folds:
            incident_folds[inc] = set()
        incident_folds[inc].add(f)
    for inc, folds in incident_folds.items():
        assert len(folds) == 1, f"Incident {inc} split across folds: {folds}"

    # Check scenes
    scene_folds = {}
    for r in records:
        sc = r["stac_scene_id"]
        f = r["assigned_fold"]
        if sc not in scene_folds:
            scene_folds[sc] = set()
        scene_folds[sc].add(f)
    for sc, folds in scene_folds.items():
        assert len(folds) == 1, f"STAC Scene {sc} split across folds: {folds}"


def test_taxonomy_decoupling(manifest_v2):
    records = manifest_v2["records"]
    for r in records:
        if r["candidate_stratum_id"] != "STR-7":
            # Expansion records must be unlabeled candidates
            assert r["human_confirmed_label"] is None
            assert r["annotation_status"] == "UNLABELED_CANDIDATE"
            assert r["confirmed_bounding_boxes"] == []
            assert r["expected_target_class"] is not None
        else:
            # Pilot records must have confirmed labels
            assert r["human_confirmed_label"] is not None
            assert r["annotation_status"] == "COMPLETED_ADJUDICATED"


def test_esa_safe_product_naming(manifest_v2):
    records = manifest_v2["records"]
    for r in records:
        pid = r["stac_scene_id"]
        assert S2_SAFE_REGEX.match(pid), f"Product ID {pid} failed ESA SAFE regex"
        assert "_T" in pid, f"Product ID {pid} missing '_T' MGRS prefix"


def test_metadata_and_temporal_deltas(manifest_v2):
    records = manifest_v2["records"]
    for r in records:
        # Cloud cover check
        assert 0.0 <= r["cloud_cover_pct"] <= 20.0
        # Temporal delta check for combustion strata
        if r["candidate_stratum_id"] in ["STR-1", "STR-2", "STR-3", "STR-4"]:
            assert 0.0 <= r["delta_time_hours"] <= 48.0


def test_geographic_bounds_and_regional_quotas(manifest_v2):
    records = manifest_v2["records"]
    for r in records:
        assert 8.0 <= r["latitude"] <= 38.0
        assert 68.0 <= r["longitude"] <= 98.0

    reg_counts = Counter(r["geographic_region"] for r in records)
    assert reg_counts["NORTH"] == 55
    assert reg_counts["CENTRAL"] == 60
    assert reg_counts["SOUTH"] == 45
    assert reg_counts["EAST"] == 50
    assert reg_counts["WEST"] == 40
    assert sum(reg_counts.values()) == 250


def test_dec_u1_year_tracking(manifest_v2):
    records = manifest_v2["records"]
    # Separate fields check
    for r in records:
        assert "event_year" in r
        assert "s2_acquisition_year" in r
        assert r["event_year"] in [2024, 2025]
        assert r["s2_acquisition_year"] in [2024, 2025]

    s1_records = [r for r in records if r["candidate_stratum_id"] == "STR-1"]
    s1_years = Counter(r["event_year"] for r in s1_records)
    assert s1_years[2025] == 8
    assert s1_years[2024] == 2


def test_prior_stage8_19_artifacts_preserved():
    stage8_19_manifest = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19" / "ds08_expansion_candidates_v1.json"
    assert stage8_19_manifest.exists()
    assert (PROJECT_ROOT / "docs" / "stage8_19" / "STAGE8_19_DISCOVERY_AUDIT_REPORT.md").exists()


def test_documentation_deliverables_exist():
    assert (DOCS_V2_DIR / "stage8_19a_fold_reconciliation.md").exists()
    assert (DOCS_V2_DIR / "stage8_19a_spatial_split_reconciliation.md").exists()
    assert (DOCS_V2_DIR / "stage8_19a_candidate_vs_confirmed_taxonomy.md").exists()
    assert (DOCS_V2_DIR / "stage8_19a_manifest_integrity_audit.md").exists()
    assert (DOCS_V2_DIR / "STAGE8_19A_AUDIT_REPORT.md").exists()
    assert (REVIEW_DIR / "stage8_19a_audit_report.md").exists()
    assert (DOCS_V2_DIR / "STAGE8_19A_ACQUISITION_READINESS_AUDIT.md").exists()
    assert (REVIEW_DIR / "stage8_19a_acquisition_readiness_audit.md").exists()


def test_wgs84_geodesic_center_distances(manifest_v2):
    from pyproj import Geod
    geod = Geod(ellps="WGS84")
    exp_records = [r for r in manifest_v2["records"] if r["candidate_stratum_id"] != "STR-7"]
    n_exp = len(exp_records)

    min_geod_dist = 999999.0
    violations = 0

    for i in range(n_exp):
        for j in range(i + 1, n_exp):
            if exp_records[i]["assigned_fold"] != exp_records[j]["assigned_fold"]:
                _, _, d_m = geod.inv(
                    exp_records[i]["longitude"], exp_records[i]["latitude"],
                    exp_records[j]["longitude"], exp_records[j]["latitude"]
                )
                d_km = d_m / 1000.0
                if d_km < min_geod_dist:
                    min_geod_dist = d_km
                if d_km <= 50.0:
                    violations += 1

    assert violations == 0, f"Detected {violations} center pairs <= 50.0 km"
    assert min_geod_dist > 50.0, f"Minimum geodesic center distance {min_geod_dist:.4f} km is <= 50.0 km"
