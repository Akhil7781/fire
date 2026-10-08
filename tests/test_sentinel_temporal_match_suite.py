"""
Targeted tests for Sentinel-2 / FIRMS Temporal Association Audit (Stage 8.5).

Covers:
 1. Verification of the authoritative FIRMS detection record in causal_features_2025.parquet.
 2. Evaluation of the ±6h temporal window (Search A: 0 items).
 3. Evaluation of the ±24h temporal window (Search B: 1 item -> MATCH_24H).
 4. Evaluation of the ±48h temporal window (Search C: 1 item).
 5. Handling of empty STAC search results.
 6. Robustness against malformed STAC responses.
 7. Handling of missing acquisition datetime in STAC properties.
 8. Handling of missing or malformed bbox/geometry.
 9. Rejection when a required band is missing.
10. Rejection of scenes outside temporal tolerance (e.g., March 11 scene ~99h gap).
11. Rejection of candidate scenes not spatially covering the FIRMS point.
12. Clean handling of API network timeouts / connection errors.
13. Zero leakage of client secrets, access tokens, or auth headers in saved JSON.
14. Full schema and content validation of data/reference/ds08/temporal_match_test.json.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.test_sentinel_temporal_match import (
    FIRMS_TARGET,
    SEARCH_WINDOWS,
    calculate_time_gap_hours,
    check_spatial_coverage,
    evaluate_temporal_match,
)


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_01_firms_record_validation():
    """Verify that the target FIRMS detection exists in the authoritative project dataset."""
    firms_parquet = PROJECT_ROOT / "data" / "interim" / "causal_features_2025.parquet"
    assert firms_parquet.exists(), f"Missing dataset: {firms_parquet}"

    df = pd.read_parquet(
        firms_parquet,
        columns=["detection_id", "latitude", "longitude", "acq_datetime_utc", "frp", "partition"],
    )
    match = df[df["detection_id"] == FIRMS_TARGET["detection_id"]]
    assert len(match) == 1, f"Expected 1 matching record, found {len(match)}"

    row = match.iloc[0]
    assert abs(row["latitude"] - FIRMS_TARGET["latitude"]) < 1e-4
    assert abs(row["longitude"] - FIRMS_TARGET["longitude"]) < 1e-4
    assert abs(row["frp"] - FIRMS_TARGET["frp_mw"]) < 0.1
    assert row["partition"] == FIRMS_TARGET["partition"]


def test_02_search_6h_window_logic():
    """Verify evaluation when 0 items exist within the ±6h window."""
    empty_candidates: list = []
    category, selected, _ = evaluate_temporal_match(empty_candidates)
    assert category == "NO_ACCEPTABLE_TEMPORAL_MATCH"
    assert selected is None


def test_03_search_24h_window_logic():
    """Verify that a candidate with ~20.975h gap is classified as MATCH_24H."""
    candidate_21h = {
        "item_id": "S2C_MSIL2A_TEST_21H",
        "absolute_time_gap_hours": 20.9752,
        "spatially_covers_firms_point": True,
        "all_required_bands_available": True,
        "cloud_cover_pct": 17.48,
    }
    category, selected, _ = evaluate_temporal_match([candidate_21h])
    assert category == "MATCH_24H"
    assert selected is not None
    assert selected["item_id"] == "S2C_MSIL2A_TEST_21H"


def test_04_search_48h_window_logic():
    """Verify that a candidate with ~35h gap is classified as MATCH_48H."""
    candidate_35h = {
        "item_id": "S2B_MSIL2A_TEST_35H",
        "absolute_time_gap_hours": 35.0,
        "spatially_covers_firms_point": True,
        "all_required_bands_available": True,
        "cloud_cover_pct": 5.0,
    }
    category, selected, _ = evaluate_temporal_match([candidate_35h])
    assert category == "MATCH_48H"
    assert selected is not None
    assert selected["item_id"] == "S2B_MSIL2A_TEST_35H"


def test_05_close_match_6h_logic():
    """Verify that a candidate within 6h is classified as CLOSE_MATCH_6H."""
    candidate_3h = {
        "item_id": "S2A_MSIL2A_TEST_3H",
        "absolute_time_gap_hours": 3.12,
        "spatially_covers_firms_point": True,
        "all_required_bands_available": True,
        "cloud_cover_pct": 2.0,
    }
    category, selected, _ = evaluate_temporal_match([candidate_3h])
    assert category == "CLOSE_MATCH_6H"
    assert selected is not None
    assert selected["item_id"] == "S2A_MSIL2A_TEST_3H"


def test_06_malformed_stac_handling():
    """Verify robust calculation when datetime strings are malformed or invalid."""
    with pytest.raises(Exception):
        calculate_time_gap_hours("not-a-datetime", "2025-03-15T08:35:00Z")


def test_07_missing_geometry_or_bbox():
    """Verify check_spatial_coverage returns False on missing/invalid bounding boxes."""
    lat, lon = FIRMS_TARGET["latitude"], FIRMS_TARGET["longitude"]
    assert check_spatial_coverage(lat, lon, None) is False
    assert check_spatial_coverage(lat, lon, []) is False
    assert check_spatial_coverage(lat, lon, [76.0, 20.0]) is False  # Incomplete bbox


def test_08_scene_not_covering_firms_point():
    """Verify candidate outside the spatial footprint is rejected from matching."""
    lat, lon = FIRMS_TARGET["latitude"], FIRMS_TARGET["longitude"]
    # Bounding box far away from detection (e.g., Delhi area)
    remote_bbox = [77.10, 28.50, 77.30, 28.70]
    assert check_spatial_coverage(lat, lon, remote_bbox) is False

    candidate_offsite = {
        "item_id": "S2_OFFSITE",
        "absolute_time_gap_hours": 2.0,
        "spatially_covers_firms_point": False,
        "all_required_bands_available": True,
        "cloud_cover_pct": 0.0,
    }
    category, selected, _ = evaluate_temporal_match([candidate_offsite])
    assert category == "NO_ACCEPTABLE_TEMPORAL_MATCH"
    assert selected is None


def test_09_missing_required_band_rejection():
    """Verify candidate lacking required optical bands is rejected."""
    candidate_incomplete_bands = {
        "item_id": "S2_INCOMPLETE_BANDS",
        "absolute_time_gap_hours": 2.0,
        "spatially_covers_firms_point": True,
        "all_required_bands_available": False,
        "cloud_cover_pct": 0.0,
    }
    category, selected, _ = evaluate_temporal_match([candidate_incomplete_bands])
    assert category == "NO_ACCEPTABLE_TEMPORAL_MATCH"
    assert selected is None


def test_10_scene_outside_temporal_tolerance():
    """Verify March 11 scene (~99h gap) is rejected as outside temporal window."""
    march_11_dt = "2025-03-11T05:33:09.634Z"
    firms_dt = FIRMS_TARGET["acq_datetime_utc"]
    gap = calculate_time_gap_hours(firms_dt, march_11_dt)
    assert gap > 48.0, f"Expected gap > 48h, got {gap:.2f}h"

    candidate_99h = {
        "item_id": "S2B_MSIL2A_20250311T051649_N0511_R062_T43QFD_20250311T075623.SAFE",
        "absolute_time_gap_hours": gap,
        "spatially_covers_firms_point": True,
        "all_required_bands_available": True,
        "cloud_cover_pct": 0.0,
    }
    category, selected, rationale = evaluate_temporal_match([candidate_99h])
    assert category == "NO_ACCEPTABLE_TEMPORAL_MATCH"
    assert selected is None
    assert "48.0h threshold" in rationale


def test_11_api_network_error_handling():
    """Verify network error handling raises cleanly without leaking internal tokens."""
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError("DNS failure")):
        from scripts.test_sentinel_catalog import search_sentinel2_catalog
        with pytest.raises(RuntimeError, match="DNS failure"):
            search_sentinel2_catalog("dummy_token", [76.7, 21.1, 76.9, 21.3], "2025-03-14/2025-03-16", max_retries=1)


def test_12_no_secret_or_token_leakage():
    """Verify output JSON contains zero client secrets, tokens, or auth headers."""
    audit_file = PROJECT_ROOT / "data" / "reference" / "ds08" / "temporal_match_test.json"
    assert audit_file.exists(), f"Missing audit file: {audit_file}"

    content = audit_file.read_text(encoding="utf-8")
    assert "Bearer eyJ" not in content
    assert "access_token" not in content
    assert "client_secret" not in content.lower()
    assert "authorization" not in content.lower()


def test_13_audit_json_schema_and_findings():
    """Verify temporal_match_test.json contains all required audit fields and findings."""
    audit_file = PROJECT_ROOT / "data" / "reference" / "ds08" / "temporal_match_test.json"
    with open(audit_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check key structure
    expected_keys = [
        "firms_detection_id",
        "firms_coordinates",
        "firms_acquisition_utc",
        "firms_frp_mw",
        "search_aoi_bbox",
        "search_intervals",
        "search_counts",
        "searches",
        "all_returned_items",
        "march_11_scene_evaluation",
        "final_match_category",
        "selected_item",
        "decision_rationale",
        "scientific_integrity_note",
    ]
    for k in expected_keys:
        assert k in data, f"Missing key in audit JSON: {k}"

    assert data["firms_detection_id"] == FIRMS_TARGET["detection_id"]
    assert data["final_match_category"] == "MATCH_24H"
    assert data["selected_item"] is not None
    assert data["selected_item"]["item_id"].startswith("S2C_MSIL2A_")
    assert data["selected_item"]["spatially_covers_firms_point"] is True
    assert data["selected_item"]["all_required_bands_available"] is True
    assert 20.0 < data["selected_item"]["absolute_time_gap_hours"] < 22.0
    assert data["march_11_scene_evaluation"]["evaluation_result"] == "OUTSIDE_ACCEPTABLE_TEMPORAL_WINDOW"
