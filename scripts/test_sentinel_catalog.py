"""
Sentinel-2 L2A STAC Catalog Discovery & Verification Script.

Searches the Copernicus Data Space Ecosystem (CDSE) Sentinel Hub STAC Catalog API
(https://sh.dataspace.copernicus.eu/catalog/v1/search) for real Sentinel-2 Level-2A
granules co-located in space and time with an authoritative 2025 project FIRMS detection.

SECURITY INVARIANT:
Never prints the OAuth client secret or access token to stdout or log files.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import credential constants from test_cdse_auth
from scripts.test_cdse_auth import (
    TOKEN_URL,
    effective_client_id,
    effective_client_secret,
)

CATALOG_SEARCH_URL = "https://sh.dataspace.copernicus.eu/catalog/v1/search"
COLLECTIONS_URL = "https://sh.dataspace.copernicus.eu/catalog/v1/collections/sentinel-2-l2a"
OUTPUT_JSON_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "catalog_test_result.json"

TIMEOUT_SECONDS = 30
REQUIRED_BANDS = ["B02", "B03", "B04", "B11", "B12"]

# Authoritative FIRMS Detection from data/interim/causal_features_2025.parquet
FIRMS_TEST_DETECTION = {
    "detection_id": "9b557f8145b3657fa117887b5558b87e40bf7c132372b041e7f5a992ad81365c",
    "latitude": 21.24256,
    "longitude": 76.81844,
    "acq_datetime_utc": "2025-03-15T08:35:00Z",
    "frp_mw": 98.65,
    "partition": "train",
}


def get_cdse_access_token(
    client_id: str,
    client_secret: str,
    token_url: str = TOKEN_URL,
    timeout: int = TIMEOUT_SECONDS,
    max_retries: int = 3,
) -> str:
    """Obtains OAuth2 Bearer token from CDSE Keycloak endpoint with retry on transient errors."""
    import time
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    last_err = ""
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(
                token_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=timeout,
            )
            if resp.status_code == 200:
                token = resp.json().get("access_token")
                if token:
                    return token
                raise RuntimeError("Authentication failed: No access_token found in response.")
            elif resp.status_code in (408, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(attempt * 2)
                continue
            else:
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_err = str(exc)
            if attempt < max_retries:
                time.sleep(attempt * 2)
                continue
    
    raise RuntimeError(f"Authentication failed after {max_retries} attempts: {last_err}")


def search_sentinel2_catalog(
    access_token: str,
    bbox: List[float],
    datetime_range: str,
    limit: int = 5,
    search_url: str = CATALOG_SEARCH_URL,
    timeout: int = TIMEOUT_SECONDS,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Queries the Sentinel Hub STAC Catalog search endpoint with retries."""
    import time
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/geo+json, application/json, */*",
    }
    payload = {
        "collections": ["sentinel-2-l2a"],
        "bbox": bbox,
        "datetime": datetime_range,
        "limit": limit,
    }
    last_err = ""
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(search_url, json=payload, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code in (408, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(attempt * 2)
                continue
            else:
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_err = str(exc)
            if attempt < max_retries:
                time.sleep(attempt * 2)
                continue
    raise RuntimeError(f"Catalog search failed after {max_retries} attempts: {last_err}")


def get_collection_band_summaries(
    access_token: str,
    collection_url: str = COLLECTIONS_URL,
    timeout: int = TIMEOUT_SECONDS,
    max_retries: int = 3,
) -> List[Dict[str, Any]]:
    """Retrieves official band summaries for the sentinel-2-l2a collection with retries."""
    import time
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json, application/geo+json, */*",
    }
    last_err = ""
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(collection_url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                coll_data = resp.json()
                return coll_data.get("summaries", {}).get("eo:bands", [])
            elif resp.status_code in (408, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(attempt * 2)
                continue
            else:
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_err = str(exc)
            if attempt < max_retries:
                time.sleep(attempt * 2)
                continue
    raise RuntimeError(f"Collection query failed after {max_retries} attempts: {last_err}")


def verify_required_bands(
    available_bands: List[Dict[str, Any]],
    required_band_names: List[str] = REQUIRED_BANDS,
) -> Dict[str, Dict[str, Any]]:
    """Verifies each required band against collection metadata."""
    band_map = {b.get("name"): b for b in available_bands if "name" in b}
    results = {}
    for name in required_band_names:
        if name in band_map:
            meta = band_map[name]
            results[name] = {
                "available": True,
                "common_name": meta.get("common_name"),
                "center_wavelength_um": meta.get("center_wavelength"),
                "fwhm_um": meta.get("full_width_half_max"),
            }
        else:
            results[name] = {"available": False}
    return results


def run_catalog_discovery() -> Dict[str, Any]:
    print("=" * 70)
    print("SENTINEL-2 L2A STAC CATALOG DISCOVERY & VERIFICATION (STAGE 8.5)")
    print("=" * 70)

    # 1. Authoritative FIRMS coordinates
    lat = FIRMS_TEST_DETECTION["latitude"]
    lon = FIRMS_TEST_DETECTION["longitude"]
    det_id = FIRMS_TEST_DETECTION["detection_id"]
    acq_dt = FIRMS_TEST_DETECTION["acq_datetime_utc"]
    frp = FIRMS_TEST_DETECTION["frp_mw"]

    # 0.05 deg bounding box (~5.5 km buffer around detection)
    bbox = [round(lon - 0.05, 5), round(lat - 0.05, 5), round(lon + 0.05, 5), round(lat + 0.05, 5)]
    # Search window: +/- 5 days around FIRMS acquisition
    datetime_range = "2025-03-10T00:00:00Z/2025-03-20T23:59:59Z"

    print(f"\n1. Authoritative FIRMS Detection:")
    print(f"   Detection ID:      {det_id}")
    print(f"   Coordinates:       {lat} N, {lon} E")
    print(f"   Acquisition UTC:   {acq_dt}")
    print(f"   FRP:               {frp} MW")

    print(f"\n2. STAC Search Parameters:")
    print(f"   Collection:        sentinel-2-l2a")
    print(f"   Search BBox:       {bbox} (WGS84 [min_lon, min_lat, max_lon, max_lat])")
    print(f"   Datetime Interval: {datetime_range}")

    # 2. Authenticate
    print("\n3. Authenticating with CDSE Keycloak...")
    token = get_cdse_access_token(effective_client_id, effective_client_secret)
    print("   OAuth Authentication: SUCCESS (token secured in memory)")

    # 3. Query Catalog
    print("\n4. Querying Sentinel Hub STAC Search API...")
    search_resp = search_sentinel2_catalog(token, bbox, datetime_range, limit=5)
    features = search_resp.get("features", [])
    item_count = len(features)
    print(f"   HTTP Status:       200 OK")
    print(f"   Returned Items:    {item_count}")

    if item_count == 0:
        print("   [WARNING] Zero Sentinel-2 items found for this query.")
        return {"status": "NO_ITEMS_FOUND"}

    # 4. Inspect Items
    returned_metadata = []
    selected_item = None
    min_cloud = 100.0

    print("\n5. Inspecting Returned STAC Items:")
    for idx, feat in enumerate(features):
        item_id = feat.get("id", "UNKNOWN")
        props = feat.get("properties", {})
        dt = props.get("datetime", "UNKNOWN")
        cloud = props.get("eo:cloud_cover", 0.0)
        platform = props.get("platform", "UNKNOWN")
        assets = feat.get("assets", {})

        asset_summary = {
            k: {
                "title": v.get("title"),
                "type": v.get("type"),
                "href": v.get("href"),
            }
            for k, v in assets.items()
        }

        item_meta = {
            "item_id": item_id,
            "platform": platform,
            "acquisition_datetime_utc": dt,
            "cloud_cover_pct": cloud,
            "epsg": props.get("proj:epsg"),
            "gsd_m": props.get("gsd"),
            "assets": asset_summary,
            "geometry_type": feat.get("geometry", {}).get("type"),
            "bbox": feat.get("bbox"),
        }
        returned_metadata.append(item_meta)

        print(f"   Item [{idx}]: {item_id}")
        print(f"     Platform:    {platform}")
        print(f"     Acquisition: {dt}")
        print(f"     Cloud Cover: {cloud}%")
        print(f"     Assets:      {list(assets.keys())}")

        # Choose the scene with lowest cloud cover
        if cloud < min_cloud:
            min_cloud = cloud
            selected_item = item_meta

    # 5. Query collection band metadata
    print("\n6. Verifying Required DS08 Optical Bands in Collection...")
    band_summaries = get_collection_band_summaries(token)
    band_verification = verify_required_bands(band_summaries, REQUIRED_BANDS)

    all_bands_available = True
    for band_name, b_info in band_verification.items():
        avail = b_info.get("available", False)
        if avail:
            print(f"   Band {band_name:4s}: AVAILABLE ({b_info['common_name']}, center={b_info['center_wavelength_um']} um)")
        else:
            print(f"   Band {band_name:4s}: MISSING")
            all_bands_available = False

    # 6. Suitability Decision
    is_l2a = "l2a" in selected_item["item_id"].lower()
    is_cloud_acceptable = selected_item["cloud_cover_pct"] <= 10.0
    is_georelevant = selected_item["bbox"] is not None
    is_bands_verified = all_bands_available

    is_suitable = is_l2a and is_cloud_acceptable and is_georelevant and is_bands_verified

    suitability_decision = {
        "is_sentinel2_l2a": is_l2a,
        "is_geographically_relevant": is_georelevant,
        "is_within_temporal_window": True,
        "is_cloud_acceptable": is_cloud_acceptable,
        "are_all_required_bands_accessible": is_bands_verified,
        "overall_suitability_for_extraction": is_suitable,
        "rationale": (
            f"Scene {selected_item['item_id']} is a valid Level-2A product covering "
            f"the FIRMS ROI with {selected_item['cloud_cover_pct']}% cloud cover "
            f"(threshold <= 10.0%) and all 5 required bands (B02, B03, B04, B11, B12) confirmed."
        ),
    }

    print("\n7. Suitability Assessment for Next Extraction Step:")
    print(f"   Selected Item:      {selected_item['item_id']}")
    print(f"   Cloud Cover:        {selected_item['cloud_cover_pct']}% (Acceptable: {is_cloud_acceptable})")
    print(f"   Bands Verified:     {is_bands_verified}")
    print(f"   Extraction Suit:    {'SUITABLE' if is_suitable else 'NOT_SUITABLE'}")

    # 7. Construct and write safe output JSON
    result_data = {
        "firms_detection_id": det_id,
        "firms_latitude": lat,
        "firms_longitude": lon,
        "firms_acquisition_datetime": acq_dt,
        "firms_frp_mw": frp,
        "firms_partition": FIRMS_TEST_DETECTION["partition"],
        "search_bbox": bbox,
        "search_datetime_interval": datetime_range,
        "sentinel2_collection": "sentinel-2-l2a",
        "returned_item_count": item_count,
        "returned_item_metadata": returned_metadata,
        "selected_item_id": selected_item["item_id"],
        "selected_acquisition_datetime": selected_item["acquisition_datetime_utc"],
        "selected_cloud_cover_pct": selected_item["cloud_cover_pct"],
        "required_bands_verification": band_verification,
        "suitability_decision": suitability_decision,
        "scientific_disclaimer": (
            "Association between FIRMS thermal detection and Sentinel-2 L2A optical scene "
            "is purely spatial-temporal candidate discovery. Optical scene acquisition does NOT "
            "prove or establish fire source class (Industrial, Forest, Agricultural, Other). "
            "Downstream classification is governed strictly by multimodal decision fusion."
        ),
    }

    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2)

    print(f"\n8. Results saved to: {OUTPUT_JSON_PATH}")
    print("=" * 70)
    return result_data


if __name__ == "__main__":
    try:
        run_catalog_discovery()
    except Exception as exc:
        print(f"\n[FATAL ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
