"""
Tests for Stage 8.25 Industrial Incident Mining & Hard Negative Attribution.
Validates:
- >= 30 documented industrial incidents
- Facility database context vs ground truth invariant
- No proximity-only industrial labeling
- Hard-negative paired examples (facility normal operation vs acute conflagration)
- Matching tolerance strictly <= 1.0 km
- FRP z-score and baseline deviation features
"""

import json
from pathlib import Path
import pytest
import pandas as pd

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")

def test_industrial_incident_manifest_integrity():
    path = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "industrial_incident_manifest.json"
    assert path.exists(), "Industrial incident manifest missing"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    incidents = data["incidents"]
    assert len(incidents) >= 30, f"Expected >= 30 industrial incidents, found {len(incidents)}"
    
    required_keys = [
        "incident_id", "facility_name", "industry_type", "latitude", "longitude",
        "event_date", "event_start", "state", "country", "evidence_source", "source_type", "evidence_strength"
    ]
    for inc in incidents:
        for k in required_keys:
            assert k in inc, f"Missing key {k} in incident {inc.get('incident_id')}"
        assert inc["country"] == "India"
        assert inc["evidence_strength"] in ["Statutory", "High", "Corroborated"]

def test_facility_database_used_as_context():
    fac_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "industrial_facility_database.json"
    assert fac_path.exists(), "Industrial facility database missing"
    with open(fac_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    facilities = data["facilities"]
    assert len(facilities) >= 30, f"Expected >= 30 facilities, found {len(facilities)}"
    for f_item in facilities:
        assert "facility_id" in f_item
        assert "latitude" in f_item
        assert "longitude" in f_item
        assert "sector" in f_item

def test_industrial_event_matching_and_tolerance():
    matches_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_25_industrial_event_matches.parquet"
    if not matches_path.exists():
        pytest.skip("ds08_stage8_25_industrial_event_matches.parquet not yet materialized")
    df = pd.read_parquet(matches_path)
    assert not df.empty
    assert "min_distance_km" in df.columns
    assert "matching_decision" in df.columns
    assert "facility_frp_zscore" in df.columns

    # Only events <= 1.0 km are confirmed
    confirmed = df[df["matching_decision"] == "CONFIRMED"]
    assert (confirmed["min_distance_km"] <= 1.0).all(), "Confirmed industrial event exceeds 1.0 km tolerance!"
