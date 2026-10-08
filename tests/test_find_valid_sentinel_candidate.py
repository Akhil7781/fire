"""
Unit tests for Sentinel-2 L2A Candidate Discovery & Verification (Stage 8.5).

Verifies strict enforcement of:
- Scene-level cloud cover <= 10.0%
- Temporal gap <= 48.0 hours
- Spatial coverage (bounding box and exact geometry)
- Required bands availability (B02, B03, B04, B11, B12)
- Rejection behavior when any criterion is violated
- Artifact schema and security invariants
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, List
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.find_valid_sentinel_candidate import (
    FIRMS_VALIDATED_TARGET,
    MAX_CLOUD_COVER_PCT,
    MAX_TEMPORAL_GAP_HOURS,
    REQUIRED_BANDS,
    build_validated_candidate_artifact,
    calculate_time_gap_hours,
    check_spatial_coverage,
    classify_temporal_match,
    evaluate_candidate_scene,
    parse_iso_datetime,
    verify_bands_available,
)

# Mock collection band summaries with all required bands
MOCK_FULL_BANDS = [
    {"name": "B01", "common_name": "coastal"},
    {"name": "B02", "common_name": "blue"},
    {"name": "B03", "common_name": "green"},
    {"name": "B04", "common_name": "red"},
    {"name": "B08", "common_name": "nir"},
    {"name": "B11", "common_name": "swir16"},
    {"name": "B12", "common_name": "swir22"},
]

# Mock collection missing B12
MOCK_MISSING_BANDS = [
    {"name": "B02", "common_name": "blue"},
    {"name": "B03", "common_name": "green"},
    {"name": "B04", "common_name": "red"},
    {"name": "B11", "common_name": "swir16"},
]

# Base valid Sentinel-2 scene feature
MOCK_VALID_SCENE = {
    "id": "S2B_MSIL2A_20250311T051649_N0511_R062_T43QFD_20250311T075623.SAFE",
    "bbox": [76.0, 20.5, 77.5, 22.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [[76.0, 20.5], [77.5, 20.5], [77.5, 22.0], [76.0, 22.0], [76.0, 20.5]]
        ],
    },
    "properties": {
        "datetime": "2025-03-11T05:33:09.634Z",
        "eo:cloud_cover": 0.0,
        "platform": "sentinel-2b",
    },
}


def test_classify_temporal_match():
    """Verifies strict classification into hierarchical bins."""
    assert classify_temporal_match(0.0) == "CLOSE_MATCH_6H"
    assert classify_temporal_match(2.614) == "CLOSE_MATCH_6H"
    assert classify_temporal_match(6.0) == "CLOSE_MATCH_6H"
    assert classify_temporal_match(6.001) == "MATCH_24H"
    assert classify_temporal_match(24.0) == "MATCH_24H"
    assert classify_temporal_match(24.001) == "MATCH_48H"
    assert classify_temporal_match(48.0) == "MATCH_48H"
    assert classify_temporal_match(48.001) == "NO_ACCEPTABLE_TEMPORAL_MATCH"
    assert classify_temporal_match(120.0) == "NO_ACCEPTABLE_TEMPORAL_MATCH"


def test_calculate_time_gap_hours():
    """Verifies decimal hour computation between UTC timestamps."""
    gap = calculate_time_gap_hours("2025-03-11T08:10:00Z", "2025-03-11T05:33:09.634Z")
    assert pytest.approx(gap, abs=0.0001) == 2.613991

    gap_rev = calculate_time_gap_hours("2025-03-11T05:33:09.634Z", "2025-03-11T08:10:00Z")
    assert pytest.approx(gap_rev, abs=0.0001) == 2.613991


def test_check_spatial_coverage():
    """Verifies bounding box and polygon point-in-polygon containment."""
    lat = 21.63424
    lon = 76.66431

    # In bbox and in geometry
    assert check_spatial_coverage(lat, lon, [76.0, 20.5, 77.5, 22.0], MOCK_VALID_SCENE["geometry"]) is True

    # Out of bbox (longitude outside)
    assert check_spatial_coverage(lat, lon, [77.0, 20.5, 78.0, 22.0]) is False

    # Out of bbox (latitude outside)
    assert check_spatial_coverage(lat, lon, [76.0, 22.0, 77.0, 23.0]) is False

    # Empty or invalid bbox
    assert check_spatial_coverage(lat, lon, []) is False
    assert check_spatial_coverage(lat, lon, None) is False


def test_verify_bands_available():
    """Verifies detection of present vs missing required bands."""
    all_ok, present = verify_bands_available(MOCK_FULL_BANDS, REQUIRED_BANDS)
    assert all_ok is True
    assert present == REQUIRED_BANDS

    missing_ok, present_missing = verify_bands_available(MOCK_MISSING_BANDS, REQUIRED_BANDS)
    assert missing_ok is False
    assert "B12" not in present_missing


def test_cloud_cover_strictly_enforced():
    """Verifies that any scene with cloud cover > 10.0% is rejected."""
    # 0.0% accepted
    res_0 = evaluate_candidate_scene(FIRMS_VALIDATED_TARGET, MOCK_VALID_SCENE, MOCK_FULL_BANDS)
    assert res_0["is_valid"] is True

    # 10.0% boundary accepted
    scene_10 = json.loads(json.dumps(MOCK_VALID_SCENE))
    scene_10["properties"]["eo:cloud_cover"] = 10.0
    res_10 = evaluate_candidate_scene(FIRMS_VALIDATED_TARGET, scene_10, MOCK_FULL_BANDS)
    assert res_10["is_valid"] is True

    # 10.01% rejected
    scene_10_01 = json.loads(json.dumps(MOCK_VALID_SCENE))
    scene_10_01["properties"]["eo:cloud_cover"] = 10.01
    res_10_01 = evaluate_candidate_scene(FIRMS_VALIDATED_TARGET, scene_10_01, MOCK_FULL_BANDS)
    assert res_10_01["is_valid"] is False
    assert any("Cloud cover" in r for r in res_10_01["rejection_reasons"])

    # 17.48% (the previous test scene) rejected
    scene_17 = json.loads(json.dumps(MOCK_VALID_SCENE))
    scene_17["properties"]["eo:cloud_cover"] = 17.48
    res_17 = evaluate_candidate_scene(FIRMS_VALIDATED_TARGET, scene_17, MOCK_FULL_BANDS)
    assert res_17["is_valid"] is False
    assert any("Cloud cover" in r for r in res_17["rejection_reasons"])


def test_temporal_gap_strictly_enforced():
    """Verifies that scenes with gap > 48.0h are rejected."""
    # Scene exactly 48.0h away -> accepted
    scene_48h = json.loads(json.dumps(MOCK_VALID_SCENE))
    scene_48h["properties"]["datetime"] = "2025-03-13T08:10:00Z"
    res_48 = evaluate_candidate_scene(FIRMS_VALIDATED_TARGET, scene_48h, MOCK_FULL_BANDS)
    assert res_48["is_valid"] is True
    assert res_48["match_category"] == "MATCH_48H"

    # Scene 48.1h away -> rejected
    scene_48_1h = json.loads(json.dumps(MOCK_VALID_SCENE))
    scene_48_1h["properties"]["datetime"] = "2025-03-13T08:16:00Z"
    res_48_1 = evaluate_candidate_scene(FIRMS_VALIDATED_TARGET, scene_48_1h, MOCK_FULL_BANDS)
    assert res_48_1["is_valid"] is False
    assert any("Temporal gap" in r for r in res_48_1["rejection_reasons"])
    assert res_48_1["match_category"] == "NO_ACCEPTABLE_TEMPORAL_MATCH"


def test_spatial_coverage_rejection():
    """Verifies that scenes outside the coordinate bounding box are rejected."""
    scene_far = json.loads(json.dumps(MOCK_VALID_SCENE))
    scene_far["bbox"] = [80.0, 15.0, 81.0, 16.0]
    scene_far["geometry"] = {
        "type": "Polygon",
        "coordinates": [[[80.0, 15.0], [81.0, 15.0], [81.0, 16.0], [80.0, 16.0], [80.0, 15.0]]]
    }
    res_far = evaluate_candidate_scene(FIRMS_VALIDATED_TARGET, scene_far, MOCK_FULL_BANDS)
    assert res_far["is_valid"] is False
    assert any("Spatial footprint" in r for r in res_far["rejection_reasons"])


def test_missing_bands_rejection():
    """Verifies that scenes lacking any required band are rejected."""
    res_missing = evaluate_candidate_scene(FIRMS_VALIDATED_TARGET, MOCK_VALID_SCENE, MOCK_MISSING_BANDS)
    assert res_missing["is_valid"] is False
    assert any("Missing required bands" in r for r in res_missing["rejection_reasons"])


def test_build_validated_candidate_artifact():
    """Verifies artifact dictionary formatting and validation error handling."""
    valid_eval = evaluate_candidate_scene(FIRMS_VALIDATED_TARGET, MOCK_VALID_SCENE, MOCK_FULL_BANDS)
    artifact = build_validated_candidate_artifact(FIRMS_VALIDATED_TARGET, valid_eval)

    assert artifact["status"] == "VALIDATED_FOR_EXTRACTION"
    assert artifact["criteria_enforced"]["max_cloud_cover_pct"] == 10.0
    assert artifact["criteria_enforced"]["max_temporal_gap_hours"] == 48.0
    assert artifact["firms_detection"]["detection_id"] == FIRMS_VALIDATED_TARGET["detection_id"]
    assert artifact["sentinel2_scene"]["item_id"] == MOCK_VALID_SCENE["id"]
    assert artifact["sentinel2_scene"]["cloud_cover_pct"] == 0.0
    assert artifact["sentinel2_scene"]["spatially_covers_firms_point"] is True
    assert artifact["sentinel2_scene"]["bands_available"] == REQUIRED_BANDS

    # Attempting to build artifact on invalid eval raises ValueError
    invalid_eval = dict(valid_eval, is_valid=False, rejection_reasons=["Test failure"])
    with pytest.raises(ValueError, match="Cannot build artifact"):
        build_validated_candidate_artifact(FIRMS_VALIDATED_TARGET, invalid_eval)


def test_validated_artifact_on_disk():
    """Verifies that the generated artifact file on disk strictly meets all requirements."""
    artifact_path = Path("data/reference/ds08/validated_extraction_candidate.json")
    assert artifact_path.exists(), f"Missing artifact: {artifact_path}"

    with open(artifact_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["status"] == "VALIDATED_FOR_EXTRACTION"
    assert data["criteria_enforced"]["max_cloud_cover_pct"] == 10.0
    assert data["criteria_enforced"]["max_temporal_gap_hours"] == 48.0

    firms = data["firms_detection"]
    assert firms["detection_id"] == "b18ce007dc003134da73556195ff1c84b9cecc89cf80a03cc3421eae8ce91624"
    assert pytest.approx(firms["latitude"], abs=1e-4) == 21.63424
    assert pytest.approx(firms["longitude"], abs=1e-4) == 76.66431
    assert firms["partition"] == "train"

    s2 = data["sentinel2_scene"]
    assert s2["item_id"].startswith("S2")
    assert s2["cloud_cover_pct"] <= 10.0
    assert s2["exact_time_gap_hours"] <= 48.0
    assert s2["spatially_covers_firms_point"] is True
    for band in REQUIRED_BANDS:
        assert band in s2["bands_available"]


def test_no_secret_or_token_leakage():
    """Verifies that credentials and tokens are never written into the artifact."""
    artifact_path = Path("data/reference/ds08/validated_extraction_candidate.json")
    content = artifact_path.read_text(encoding="utf-8")

    assert "client_secret" not in content.lower()
    assert "access_token" not in content.lower()
    assert "bearer" not in content.lower()
    assert "authorization" not in content.lower()
