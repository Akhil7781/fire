"""
Unit test suite for Stage 8.19: Read-only Candidate Discovery and STAC Manifest Building.
Verifies compliance with DEC-U1 to DEC-U4, manifest integrity, 7 strata allocations,
regional quotas, spatial 5-fold cross-validation balance, zero spatial leakage,
and immutability of predecessor stages.
"""

import json
import math
from pathlib import Path
import pytest
import pandas as pd
import pyarrow.parquet as pq

WORKSPACE_ROOT = Path("d:/DATA PREPROCESSING")
MANIFEST_DIR = WORKSPACE_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19"
DOCS_STAGE_DIR = WORKSPACE_ROOT / "docs" / "stage8_19"
PILOT_PACKAGE_DIR = WORKSPACE_ROOT / "data" / "reference" / "ds08" / "packages" / "ds08_pilot_v1"
AUDIT_REVIEW_DIR = WORKSPACE_ROOT / "data" / "reference" / "ds08" / "annotations" / "review"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def test_1_stage8_19_deliverables_exist():
    """Verify that all manifest formats and audit reports exist and are non-empty."""
    required_files = [
        MANIFEST_DIR / "ds08_expansion_candidates_v1.json",
        MANIFEST_DIR / "ds08_expansion_candidates_v1.csv",
        MANIFEST_DIR / "ds08_expansion_candidates_v1.parquet",
        DOCS_STAGE_DIR / "stage8_19_industrial_year_distribution.md",
        DOCS_STAGE_DIR / "stage8_19_spatial_fold_verification.md",
        DOCS_STAGE_DIR / "STAGE8_19_DISCOVERY_AUDIT_REPORT.md",
        AUDIT_REVIEW_DIR / "stage8_19_discovery_audit_report.md",
    ]
    for p in required_files:
        assert p.exists(), f"Missing required file: {p}"
        assert p.stat().st_size > 0, f"File is empty: {p}"


def test_2_candidate_manifest_cohort_and_strata_quotas():
    """Verify total candidate count is 250, partitioned across the 7 physical strata."""
    json_path = MANIFEST_DIR / "ds08_expansion_candidates_v1.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_chips"] == 250
    assert data["pilot_benchmark_held_out"] == 15
    assert data["expansion_candidates_count"] == 235

    records = data["records"]
    assert len(records) == 250

    from collections import Counter
    strata_counts = Counter(r["stratum_id"] for r in records)
    assert strata_counts["STR-1"] == 10, f"Expected 10 STR-1, got {strata_counts['STR-1']}"
    assert strata_counts["STR-2"] == 35, f"Expected 35 STR-2, got {strata_counts['STR-2']}"
    assert strata_counts["STR-3"] == 55, f"Expected 55 STR-3, got {strata_counts['STR-3']}"
    assert strata_counts["STR-4"] == 55, f"Expected 55 STR-4, got {strata_counts['STR-4']}"
    assert strata_counts["STR-5"] == 40, f"Expected 40 STR-5, got {strata_counts['STR-5']}"
    assert strata_counts["STR-6"] == 40, f"Expected 40 STR-6, got {strata_counts['STR-6']}"
    assert strata_counts["STR-7"] == 15, f"Expected 15 STR-7, got {strata_counts['STR-7']}"

    assert sum(strata_counts.values()) == 250


def test_3_regional_quotas_pan_india():
    """Verify regional distribution strictly meets 55 North, 60 Central, 45 South, 50 East, 40 West."""
    json_path = MANIFEST_DIR / "ds08_expansion_candidates_v1.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data["records"]
    from collections import Counter
    reg_counts = Counter(r["geographic_region"] for r in records)

    assert reg_counts["NORTH"] == 55
    assert reg_counts["CENTRAL"] == 60
    assert reg_counts["SOUTH"] == 45
    assert reg_counts["EAST"] == 50
    assert reg_counts["WEST"] == 40
    assert sum(reg_counts.values()) == 250


def test_4_dec_u1_industrial_fire_year_separation():
    """Verify DEC-U1 requirements: distinct year fields, 8 in 2025 and 2 in 2024, no duplicate incidents."""
    json_path = MANIFEST_DIR / "ds08_expansion_candidates_v1.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    s1_records = [r for r in data["records"] if r["stratum_id"] == "STR-1"]
    assert len(s1_records) == 10

    # Ensure separate fields
    for r in s1_records:
        assert "event_year" in r
        assert "s2_acquisition_year" in r
        assert r["event_year"] in (2024, 2025)
        assert r["s2_acquisition_year"] in (2024, 2025)
        assert r["is_primary_chip"] is True
        assert r["target_class"] == "Industrial Fire"
        assert r["class_id"] == 1

    # Check year breakdown: 8 from 2025, 2 from 2024
    from collections import Counter
    years = Counter(r["event_year"] for r in s1_records)
    assert years[2025] == 8
    assert years[2024] == 2

    # Check incident uniqueness
    inc_ids = [r["incident_id"] for r in s1_records]
    assert len(set(inc_ids)) == 10, "Duplicate incident_id detected in Stratum 1 primary chips!"


def test_5_dec_u2_annotation_readiness():
    """Verify DEC-U2: all expansion chips are UNLABELED_CANDIDATE, pilot chips are COMPLETED_ADJUDICATED."""
    json_path = MANIFEST_DIR / "ds08_expansion_candidates_v1.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for r in data["records"]:
        if r["stratum_id"] == "STR-7":
            assert r["annotation_status"] == "COMPLETED_ADJUDICATED"
            assert r["image_status"] == "DOWNLOADED_AND_VALIDATED"
        else:
            assert r["annotation_status"] == "UNLABELED_CANDIDATE"
            assert r["image_status"] == "PENDING_DOWNLOAD"


def test_6_spatial_5_fold_cross_validation_balance():
    """Verify each of Folds 1 to 5 receives exactly 47 chips with balanced strata."""
    json_path = MANIFEST_DIR / "ds08_expansion_candidates_v1.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    fold_counts = data["fold_counts"]
    for k in range(1, 6):
        fold_name = f"Fold {k}"
        assert fold_counts[fold_name] == 47, f"{fold_name} has {fold_counts[fold_name]} chips, expected 47"

    assert fold_counts["BENCHMARK_HELD_OUT"] == 15

    # Check stratum balance in each fold
    from collections import Counter
    for k in range(1, 6):
        f_name = f"Fold {k}"
        f_records = [r for r in data["records"] if r["assigned_fold"] == f_name]
        assert len(f_records) == 47
        sc = Counter(r["stratum_id"] for r in f_records)
        assert sc["STR-1"] == 2
        assert sc["STR-2"] == 7
        assert sc["STR-3"] == 11
        assert sc["STR-4"] == 11
        assert sc["STR-5"] == 8
        assert sc["STR-6"] == 8


def test_7_spatial_autocorrelation_zero_leakage():
    """Verify minimum distance between candidates in different folds is > 30.0 km."""
    json_path = MANIFEST_DIR / "ds08_expansion_candidates_v1.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    expansion_records = [r for r in data["records"] if r["assigned_fold"] != "BENCHMARK_HELD_OUT"]
    n_exp = len(expansion_records)

    min_dist = 999999.0
    violations = 0

    for i in range(n_exp):
        for j in range(i + 1, n_exp):
            r1 = expansion_records[i]
            r2 = expansion_records[j]
            if r1["assigned_fold"] != r2["assigned_fold"]:
                d = haversine_km(r1["latitude"], r1["longitude"], r2["latitude"], r2["longitude"])
                if d < min_dist:
                    min_dist = d
                if d <= 30.0:
                    violations += 1

    assert violations == 0, f"Detected {violations} cross-fold spatial leakage violations <= 30 km"
    assert min_dist > 30.0, f"Minimum cross-fold distance {min_dist} km is not > 30 km"


def test_8_csv_and_parquet_synchronization():
    """Verify CSV and Parquet manifests match JSON record count and columns."""
    csv_path = MANIFEST_DIR / "ds08_expansion_candidates_v1.csv"
    parquet_path = MANIFEST_DIR / "ds08_expansion_candidates_v1.parquet"

    df_csv = pd.read_csv(csv_path)
    assert len(df_csv) == 250
    assert "event_year" in df_csv.columns
    assert "s2_acquisition_year" in df_csv.columns
    assert "assigned_fold" in df_csv.columns

    table_pq = pq.read_table(parquet_path)
    assert table_pq.num_rows == 250
    assert "event_year" in table_pq.column_names
    assert "s2_acquisition_year" in table_pq.column_names
    assert "assigned_fold" in table_pq.column_names


def test_9_predecessor_artifacts_preserved():
    """Verify predecessor stages (17, 18, 18A) remain immutable."""
    assert PILOT_PACKAGE_DIR.exists()
    pilot_manifest = json.load(open(PILOT_PACKAGE_DIR / "manifest.json", "r", encoding="utf-8"))
    assert pilot_manifest["total_chips"] == 15

    stage8_18_dir = WORKSPACE_ROOT / "docs" / "stage8_18"
    assert stage8_18_dir.exists()
    assert len(list(stage8_18_dir.glob("*"))) >= 8

    stage8_18a_dir = WORKSPACE_ROOT / "docs" / "stage8_18a"
    assert stage8_18a_dir.exists()
    assert len(list(stage8_18a_dir.glob("*"))) >= 9
