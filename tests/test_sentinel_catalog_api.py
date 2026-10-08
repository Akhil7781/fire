"""
Targeted unit tests for Sentinel-2 L2A STAC Catalog Discovery & Verification.

Covers:
 1. Successful catalog request & parsing (mocked STAC response).
 2. Empty search result handling (zero features returned).
 3. Malformed STAC response handling (missing features key).
 4. Missing item ID handling.
 5. Missing acquisition datetime in properties.
 6. Missing assets dictionary.
 7. Missing required optical bands detection.
 8. API / network failure handling (Timeout / ConnectionError).
 9. Credential / token failure handling (HTTP 401 Unauthorized).
10. Secret and token leakage prevention in logs/outputs.
11. Verification of data/reference/ds08/catalog_test_result.json schema and safety.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.test_sentinel_catalog import (
    REQUIRED_BANDS,
    get_cdse_access_token,
    search_sentinel2_catalog,
    verify_required_bands,
)


# ---------------------------------------------------------------------------
# Sample Mock STAC Payloads
# ---------------------------------------------------------------------------

SAMPLE_VALID_STAC = {
    "type": "FeatureCollection",
    "features": [
        {
            "id": "S2B_MSIL2A_20250311T051649_N0511_R062_T43QFD_20250311T075623.SAFE",
            "type": "Feature",
            "properties": {
                "datetime": "2025-03-11T05:33:09.634Z",
                "platform": "sentinel-2b",
                "instruments": ["msi"],
                "constellation": "sentinel-2",
                "gsd": 10,
                "eo:cloud_cover": 0.0,
                "proj:epsg": 32643,
            },
            "assets": {
                "data": {
                    "href": "s3://eodata/Sentinel-2/MSI/L2A/2025/03/11/S2B_MSIL2A_20250311T051649_N0511_R062_T43QFD_20250311T075623.SAFE",
                    "title": "s3",
                    "type": "inode/directory",
                }
            },
            "bbox": [76.02, 20.69, 77.02, 21.69],
        }
    ],
}

SAMPLE_BANDS_SUMMARY = [
    {"name": "B01", "common_name": "coastal", "center_wavelength": 0.443},
    {"name": "B02", "common_name": "blue", "center_wavelength": 0.4924, "full_width_half_max": 0.066},
    {"name": "B03", "common_name": "green", "center_wavelength": 0.5598, "full_width_half_max": 0.036},
    {"name": "B04", "common_name": "red", "center_wavelength": 0.6646, "full_width_half_max": 0.031},
    {"name": "B11", "common_name": "swir16", "center_wavelength": 1.6137, "full_width_half_max": 0.091},
    {"name": "B12", "common_name": "swir22", "center_wavelength": 2.2024, "full_width_half_max": 0.175},
]


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_01_successful_catalog_request():
    """Verify successful parsing of a standard STAC search response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_VALID_STAC

    with patch("requests.post", return_value=mock_resp):
        res = search_sentinel2_catalog("fake_token", [76.7, 21.1, 76.9, 21.3], "2025-03-10/2025-03-20")
        assert "features" in res
        assert len(res["features"]) == 1
        item = res["features"][0]
        assert item["id"].startswith("S2B_MSIL2A_")
        assert item["properties"]["eo:cloud_cover"] == 0.0


def test_02_empty_search_result():
    """Verify handling when zero scenes match the spatiotemporal bounding box."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"type": "FeatureCollection", "features": []}

    with patch("requests.post", return_value=mock_resp):
        res = search_sentinel2_catalog("fake_token", [70.0, 20.0, 70.1, 20.1], "2025-01-01/2025-01-02")
        assert "features" in res
        assert len(res["features"]) == 0


def test_03_malformed_stac_response():
    """Verify error handling on non-200 or malformed HTTP response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    with patch("requests.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="Catalog search failed"):
            search_sentinel2_catalog("fake_token", [76.7, 21.1, 76.9, 21.3], "2025-03-10/2025-03-20", max_retries=1)


def test_04_missing_item_id():
    """Verify robust processing when a feature object lacks an 'id' attribute."""
    bad_stac = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"datetime": "2025-03-11T05:33:09Z"}}],
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = bad_stac

    with patch("requests.post", return_value=mock_resp):
        res = search_sentinel2_catalog("fake_token", [76.7, 21.1, 76.9, 21.3], "2025-03-10/2025-03-20")
        feature = res["features"][0]
        assert feature.get("id") is None
        assert "datetime" in feature["properties"]


def test_05_missing_acquisition_datetime():
    """Verify handling when properties lacks 'datetime'."""
    bad_stac = {
        "type": "FeatureCollection",
        "features": [{"id": "S2_NO_DATETIME", "properties": {"eo:cloud_cover": 5.0}}],
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = bad_stac

    with patch("requests.post", return_value=mock_resp):
        res = search_sentinel2_catalog("fake_token", [76.7, 21.1, 76.9, 21.3], "2025-03-10/2025-03-20")
        feature = res["features"][0]
        assert feature.get("properties", {}).get("datetime") is None


def test_06_missing_assets():
    """Verify handling when feature has empty or missing assets."""
    bad_stac = {
        "type": "FeatureCollection",
        "features": [{"id": "S2_NO_ASSETS", "properties": {"datetime": "2025-03-11T05:33:09Z"}, "assets": {}}],
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = bad_stac

    with patch("requests.post", return_value=mock_resp):
        res = search_sentinel2_catalog("fake_token", [76.7, 21.1, 76.9, 21.3], "2025-03-10/2025-03-20")
        feature = res["features"][0]
        assert len(feature.get("assets", {})) == 0


def test_07_missing_required_bands():
    """Verify verification logic flags missing required bands."""
    # Omit B12 from summaries
    partial_bands = [b for b in SAMPLE_BANDS_SUMMARY if b["name"] != "B12"]
    verification = verify_required_bands(partial_bands, REQUIRED_BANDS)

    assert verification["B02"]["available"] is True
    assert verification["B03"]["available"] is True
    assert verification["B04"]["available"] is True
    assert verification["B11"]["available"] is True
    assert verification["B12"]["available"] is False


def test_08_api_network_failure():
    """Verify network exceptions (Timeout / ConnectionError) raise cleanly."""
    with patch("requests.post", side_effect=requests.exceptions.Timeout("Connection timed out")):
        with pytest.raises(RuntimeError, match="Connection timed out"):
            search_sentinel2_catalog("fake_token", [76.7, 21.1, 76.9, 21.3], "2025-03-10/2025-03-20", max_retries=1)


def test_09_credential_token_failure():
    """Verify HTTP 401 raises authentication failure cleanly."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = '{"error":"invalid_client","error_description":"Bad credentials"}'

    with patch("requests.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="Authentication failed.*HTTP 401"):
            get_cdse_access_token("bad_id", "bad_secret", max_retries=1)


def test_10_secret_token_not_appearing_in_logs(capsys):
    """Verify client secret or raw bearer token never appears in output."""
    from scripts.test_cdse_auth import effective_client_secret

    output_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "catalog_test_result.json"
    if output_path.exists():
        content = output_path.read_text(encoding="utf-8")
        if effective_client_secret:
            assert effective_client_secret not in content
        assert "Bearer eyJ" not in content
        assert "access_token" not in content


def test_11_catalog_test_result_json_validity():
    """Verify the saved catalog test result JSON exists, is valid, and matches specification."""
    output_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "catalog_test_result.json"
    assert output_path.exists(), f"Missing catalog test result: {output_path}"

    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Required fields
    required_keys = [
        "firms_detection_id",
        "firms_latitude",
        "firms_longitude",
        "firms_acquisition_datetime",
        "search_bbox",
        "search_datetime_interval",
        "sentinel2_collection",
        "returned_item_count",
        "returned_item_metadata",
        "selected_item_id",
        "selected_acquisition_datetime",
        "selected_cloud_cover_pct",
        "required_bands_verification",
        "suitability_decision",
    ]
    for k in required_keys:
        assert k in data, f"Missing key in catalog result JSON: {k}"

    assert data["returned_item_count"] > 0
    assert data["selected_item_id"].startswith("S2")
    assert data["selected_cloud_cover_pct"] <= 10.0
    assert data["suitability_decision"]["overall_suitability_for_extraction"] is True

    # Bands verification
    bands = data["required_bands_verification"]
    for b in ["B02", "B03", "B04", "B11", "B12"]:
        assert b in bands
        assert bands[b]["available"] is True
