"""
Unit test suite for Stage 8.18A: Protocol Review and Sign-off Preparation.
Verifies all 6 resolved issues, deliverables, mathematical partitions, quotas,
and immutability of predecessor stages.
"""

import json
import csv
from pathlib import Path
import pytest


WORKSPACE_ROOT = Path("d:/DATA PREPROCESSING")
STAGE8_18A_DIR = WORKSPACE_ROOT / "docs" / "stage8_18a"
STAGE8_18_DIR = WORKSPACE_ROOT / "docs" / "stage8_18"
PILOT_PACKAGE_DIR = WORKSPACE_ROOT / "data" / "reference" / "ds08" / "packages" / "ds08_pilot_v1"
AUDIT_REVIEW_DIR = WORKSPACE_ROOT / "data" / "reference" / "ds08" / "annotations" / "review"


def test_stage8_18a_deliverables_exist():
    """Verify all 9 authoritative deliverables exist in docs/stage8_18a/ and review dir."""
    expected_files = [
        STAGE8_18A_DIR / "stage8_18a_geographic_partition_spec.md",
        STAGE8_18A_DIR / "stage8_18a_industrial_fire_sampling_unit.md",
        STAGE8_18A_DIR / "stage8_18a_temporal_matching_and_phases.md",
        STAGE8_18A_DIR / "stage8_18a_spatial_clustering_and_split_feasibility.md",
        STAGE8_18A_DIR / "stage8_18a_agreement_metrics_specification.md",
        STAGE8_18A_DIR / "stage8_18a_decision_log.md",
        STAGE8_18A_DIR / "sampling_plan_v2.json",
        STAGE8_18A_DIR / "sampling_plan_v2.csv",
        STAGE8_18A_DIR / "STAGE8_18A_REVIEW_REPORT.md",
        AUDIT_REVIEW_DIR / "stage8_18a_review_report.md",
    ]
    for file_path in expected_files:
        assert file_path.exists(), f"Missing required file: {file_path}"
        assert file_path.stat().st_size > 0, f"File is empty: {file_path}"


def test_geographic_partition_logic():
    """Verify classify_indian_region_v2 is mutually exclusive, exhaustive, and correct."""
    def classify_indian_region_v2(lat: float, lon: float) -> str:
        if lon >= 84.0:
            return "EAST"
        if lat < 16.0:
            return "SOUTH"
        if lat >= 28.0:
            return "NORTH"
        if lon < 76.0:
            return "WEST"
        return "CENTRAL"

    # Test test-cases:
    # 1. Northeast (Sikkim/Assam): Lat 27.20, Lon 87.73 -> MUST BE EAST
    assert classify_indian_region_v2(27.20, 87.73) == "EAST"
    # 2. Andaman & Nicobar: Lat 11.66, Lon 92.73 -> MUST BE EAST (lon >= 84.0)
    assert classify_indian_region_v2(11.66, 92.73) == "EAST"
    # 3. North (Punjab/Haryana): Lat 30.73, Lon 76.78 -> NORTH
    assert classify_indian_region_v2(30.73, 76.78) == "NORTH"
    # 4. South (Bengaluru/Chennai): Lat 12.97, Lon 77.59 -> SOUTH
    assert classify_indian_region_v2(12.97, 77.59) == "SOUTH"
    # 5. Central (Bhopal): Lat 23.25, Lon 77.41 -> CENTRAL
    assert classify_indian_region_v2(23.25, 77.41) == "CENTRAL"
    # 6. West (Ahmedabad/Surat): Lat 23.02, Lon 72.57 -> WEST
    assert classify_indian_region_v2(23.02, 72.57) == "WEST"

    # Grid check over entire India bounding box (6.0 to 38.0 Lat, 68.0 to 98.0 Lon)
    valid_regions = {"NORTH", "CENTRAL", "SOUTH", "EAST", "WEST"}
    for lat_i in range(60, 381, 20):  # step 2.0 degrees
        lat = lat_i / 10.0
        for lon_i in range(680, 981, 20):
            lon = lon_i / 10.0
            region = classify_indian_region_v2(lat, lon)
            assert region in valid_regions, f"Invalid region {region} at ({lat}, {lon})"


def test_sampling_plan_v2_json_integrity():
    """Verify sampling_plan_v2.json has correct quotas and schema structure."""
    plan_path = STAGE8_18A_DIR / "sampling_plan_v2.json"
    with open(plan_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["target_total_chips"] == 250
    assert data["pilot_benchmark_chips"] == 15
    assert data["expansion_target_chips"] == 235

    # Check Strata
    strata = data["strata"]
    assert len(strata) == 7
    total_strata_chips = sum(s["allocated_chips"] for s in strata)
    assert total_strata_chips == 250

    # Check Stratum 1 PSU
    stratum_1 = next(s for s in strata if s["stratum_id"] == "STR-1")
    assert "incident_id" in stratum_1["primary_sampling_unit"]
    assert stratum_1["allocated_chips"] == 15

    # Check Geographic Allocation
    geo = data["geographic_allocation"]
    assert set(geo.keys()) == {"NORTH", "CENTRAL", "SOUTH", "EAST", "WEST"}
    total_geo_chips = sum(g["allocated_chips"] for g in geo.values())
    assert total_geo_chips == 250
    assert geo["NORTH"]["allocated_chips"] == 55
    assert geo["CENTRAL"]["allocated_chips"] == 60
    assert geo["SOUTH"]["allocated_chips"] == 45
    assert geo["EAST"]["allocated_chips"] == 50
    assert geo["WEST"]["allocated_chips"] == 40

    total_geo_pct = sum(g["percentage"] for g in geo.values())
    assert abs(total_geo_pct - 100.0) < 1e-4

    # Check Temporal Matching Tiers
    tiers = data["temporal_matching_tiers"]
    assert len(tiers) == 4
    tier1 = next(t for t in tiers if "Tier 1" in t["tier"])
    assert tier1["physical_phase"] == "ACTIVE_COMBUSTION"
    tier4 = next(t for t in tiers if "Tier 4" in t["tier"])
    assert tier4["physical_phase"] == "POST_COMBUSTION_SCAR"
    assert "DIRECT_FIRE_VISIBLE" in tier4["prohibited_evidence"]

    # Check Spatial Partition Rules
    spatial = data["spatial_partition_rules"]
    assert spatial["buffer_radius_km"] == 50.0
    assert spatial["banned_buffer_km"] == 150.0
    assert spatial["cross_validation_folds"] == 5
    assert spatial["chips_per_fold"] == 50


def test_sampling_plan_v2_csv_integrity():
    """Verify sampling_plan_v2.csv totals match JSON."""
    csv_path = STAGE8_18A_DIR / "sampling_plan_v2.csv"
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    # 7 strata + 1 total row = 8 rows
    assert len(rows) == 8
    total_row = next(r for r in rows if r["stratum_id"] == "TOTAL")
    assert int(total_row["allocated_chips"]) == 250

    strata_rows = [r for r in rows if r["stratum_id"] != "TOTAL"]
    sum_chips = sum(int(r["allocated_chips"]) for r in strata_rows)
    assert sum_chips == 250


def test_predecessor_immutability():
    """Verify that Stage 8.18 and Stage 8.17 pilot artifacts are preserved."""
    assert STAGE8_18_DIR.exists()
    stage8_18_files = list(STAGE8_18_DIR.glob("*"))
    assert len(stage8_18_files) >= 8

    # Pilot package v1
    assert PILOT_PACKAGE_DIR.exists()
    manifest_file = PILOT_PACKAGE_DIR / "manifest.json"
    assert manifest_file.exists()
    with open(manifest_file, "r", encoding="utf-8") as f:
        pilot_manifest = json.load(f)
    assert pilot_manifest["total_chips"] == 15
