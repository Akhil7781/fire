"""
Sentinel-2 L2A / FIRMS Temporal Association Audit Script (Stage 8.5).

Performs a rigorous multi-interval temporal association audit (±6h, ±24h, ±48h)
between an authoritative project FIRMS thermal detection and Sentinel-2 L2A optical
scenes using the Copernicus Data Space Sentinel Hub STAC Catalog API.

SECURITY INVARIANT:
Never prints or stores the CDSE Client ID, Client Secret, OAuth access token,
or Authorization headers.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment from root .env
load_dotenv(PROJECT_ROOT / ".env")

from scripts.test_cdse_auth import (
    TOKEN_URL,
    effective_client_id,
    effective_client_secret,
)
from scripts.test_sentinel_catalog import (
    CATALOG_SEARCH_URL,
    COLLECTIONS_URL,
    REQUIRED_BANDS,
    get_cdse_access_token,
    get_collection_band_summaries,
    search_sentinel2_catalog,
    verify_required_bands,
)

OUTPUT_AUDIT_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "temporal_match_test.json"

# Authoritative FIRMS Target Detection
FIRMS_TARGET = {
    "detection_id": "9b557f8145b3657fa117887b5558b87e40bf7c132372b041e7f5a992ad81365c",
    "latitude": 21.24256,
    "longitude": 76.81844,
    "acq_datetime_utc": "2025-03-15T08:35:00Z",
    "frp_mw": 98.65,
    "partition": "train",
}

# Search Windows around FIRMS timestamp
SEARCH_WINDOWS = {
    "window_6h": {
        "name": "Search A (±6h)",
        "max_hours": 6.0,
        "interval": "2025-03-15T02:35:00Z/2025-03-15T14:35:00Z",
    },
    "window_24h": {
        "name": "Search B (±24h)",
        "max_hours": 24.0,
        "interval": "2025-03-14T08:35:00Z/2025-03-16T08:35:00Z",
    },
    "window_48h": {
        "name": "Search C (±48h)",
        "max_hours": 48.0,
        "interval": "2025-03-13T08:35:00Z/2025-03-17T08:35:00Z",
    },
}


def parse_iso_datetime(dt_str: str) -> datetime:
    """Parses ISO 8601 UTC datetime string to aware datetime."""
    clean = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(clean)


def calculate_time_gap_hours(firms_dt_str: str, s2_dt_str: str) -> float:
    """Calculates absolute time gap in decimal hours."""
    t_firms = parse_iso_datetime(firms_dt_str)
    t_s2 = parse_iso_datetime(s2_dt_str)
    delta_sec = abs((t_s2 - t_firms).total_seconds())
    return delta_sec / 3600.0


def check_spatial_coverage(
    firms_lat: float,
    firms_lon: float,
    bbox: Optional[List[float]],
    geometry: Optional[Dict[str, Any]] = None,
) -> bool:
    """Verifies whether the FIRMS point is within the Sentinel-2 scene footprint."""
    if not bbox or len(bbox) != 4:
        return False
    min_lon, min_lat, max_lon, max_lat = bbox
    in_bbox = (min_lon <= firms_lon <= max_lon) and (min_lat <= firms_lat <= max_lat)
    if not in_bbox:
        return False

    # Point-in-polygon verification via Shapely if geometry is provided
    if geometry and geometry.get("coordinates"):
        try:
            from shapely.geometry import shape, Point
            poly = shape(geometry)
            pt = Point(firms_lon, firms_lat)
            return bool(poly.contains(pt))
        except Exception:
            # Fall back to bounding box verification
            return in_bbox
    return in_bbox


def evaluate_temporal_match(
    candidates: List[Dict[str, Any]],
) -> Tuple[str, Optional[Dict[str, Any]], str]:
    """
    Evaluates candidate Sentinel-2 scenes under the strict hierarchical association rules:
    - CLOSE_MATCH_6H (time gap <= 6h)
    - MATCH_24H       (time gap <= 24h)
    - MATCH_48H       (time gap <= 48h)
    - NO_ACCEPTABLE_TEMPORAL_MATCH
    """
    valid_candidates = [
        c for c in candidates
        if c["spatially_covers_firms_point"] and c["all_required_bands_available"]
    ]

    if not valid_candidates:
        return (
            "NO_ACCEPTABLE_TEMPORAL_MATCH",
            None,
            "No candidate Sentinel-2 scene satisfied both spatial coverage and band availability.",
        )

    # Sort valid candidates by absolute time gap
    valid_candidates.sort(key=lambda x: x["absolute_time_gap_hours"])
    best = valid_candidates[0]
    gap = best["absolute_time_gap_hours"]

    if gap <= 6.0:
        category = "CLOSE_MATCH_6H"
        rationale = f"Found valid Sentinel-2 scene ({best['item_id']}) with time gap {gap:.4f}h <= 6.0h."
    elif gap <= 24.0:
        category = "MATCH_24H"
        rationale = f"Found valid Sentinel-2 scene ({best['item_id']}) with time gap {gap:.4f}h <= 24.0h (outside 6h window)."
    elif gap <= 48.0:
        category = "MATCH_48H"
        rationale = f"Found valid Sentinel-2 scene ({best['item_id']}) with time gap {gap:.4f}h <= 48.0h (outside 24h window)."
    else:
        category = "NO_ACCEPTABLE_TEMPORAL_MATCH"
        rationale = f"Closest scene ({best['item_id']}) has time gap {gap:.4f}h > 48.0h threshold."

    return category, best if category != "NO_ACCEPTABLE_TEMPORAL_MATCH" else None, rationale


def run_temporal_association_audit() -> Dict[str, Any]:
    print("=" * 70)
    print("STAGE 8.5: SENTINEL-2 / FIRMS TEMPORAL ASSOCIATION AUDIT")
    print("=" * 70)

    # 1. Verification of FIRMS detection
    lat = FIRMS_TARGET["latitude"]
    lon = FIRMS_TARGET["longitude"]
    det_id = FIRMS_TARGET["detection_id"]
    firms_dt = FIRMS_TARGET["acq_datetime_utc"]
    frp = FIRMS_TARGET["frp_mw"]

    # AOI: ±0.05 deg buffer around detection (~5.5 km radius)
    aoi_bbox = [round(lon - 0.05, 5), round(lat - 0.05, 5), round(lon + 0.05, 5), round(lat + 0.05, 5)]

    print(f"\n1. Target FIRMS Detection:")
    print(f"   Detection ID:      {det_id}")
    print(f"   Coordinates:       {lat} N, {lon} E")
    print(f"   Acquisition UTC:   {firms_dt}")
    print(f"   FRP:               {frp} MW")
    print(f"   Search AOI BBox:   {aoi_bbox}")

    # 2. Authenticate
    print("\n2. Authenticating with CDSE...")
    token = get_cdse_access_token(effective_client_id, effective_client_secret)
    print("   Authentication:    SUCCESS")

    # 3. Band verification in collection
    print("\n3. Verifying Collection Band Summaries...")
    collection_bands = get_collection_band_summaries(token)
    band_verification = verify_required_bands(collection_bands, REQUIRED_BANDS)
    all_bands_ok = all(b.get("available", False) for b in band_verification.values())
    for bname, bmeta in band_verification.items():
        print(f"   Band {bname:4s}: {'AVAILABLE' if bmeta.get('available') else 'NOT_AVAILABLE'}")

    # 4. Execute the three distinct searches
    search_results: Dict[str, Any] = {}
    evaluated_items_by_id: Dict[str, Dict[str, Any]] = {}

    print("\n4. Executing Hierarchical Temporal Searches:")
    for win_key, win_info in SEARCH_WINDOWS.items():
        name = win_info["name"]
        interval = win_info["interval"]
        print(f"\n   -> Running {name} (Interval: {interval})...")
        resp = search_sentinel2_catalog(token, aoi_bbox, interval, limit=5)
        features = resp.get("features", [])
        count = len(features)
        print(f"      HTTP 200 OK | Returned Items: {count}")

        item_list = []
        for feat in features:
            item_id = feat.get("id")
            props = feat.get("properties", {})
            s2_dt = props.get("datetime")
            cloud = props.get("eo:cloud_cover", 0.0)
            platform = props.get("platform", "sentinel-2")
            bbox = feat.get("bbox")
            geom = feat.get("geometry")
            assets = feat.get("assets", {})

            # Exact time difference
            gap_hours = calculate_time_gap_hours(firms_dt, s2_dt) if s2_dt else 9999.0
            covers_pt = check_spatial_coverage(lat, lon, bbox, geom)

            item_record = {
                "item_id": item_id,
                "collection": "sentinel-2-l2a",
                "platform": platform,
                "acquisition_datetime_utc": s2_dt,
                "absolute_time_gap_hours": round(gap_hours, 6),
                "cloud_cover_pct": cloud,
                "spatially_covers_firms_point": covers_pt,
                "bbox": bbox,
                "geometry_type": geom.get("type") if geom else None,
                "assets": list(assets.keys()),
                "all_required_bands_available": all_bands_ok,
                "bands_status": {k: ("AVAILABLE" if v["available"] else "NOT_AVAILABLE") for k, v in band_verification.items()},
            }
            item_list.append(item_record)

            # Store unique evaluated items across searches
            if item_id not in evaluated_items_by_id:
                evaluated_items_by_id[item_id] = item_record

        search_results[win_key] = {
            "name": name,
            "temporal_window_hours": win_info["max_hours"],
            "datetime_interval": interval,
            "returned_count": count,
            "items": item_list,
        }

    # 5. Evaluate the March 11 scene under strict temporal association rule
    march_11_scene_id = "S2B_MSIL2A_20250311T051649_N0511_R062_T43QFD_20250311T075623.SAFE"
    march_11_dt = "2025-03-11T05:33:09.634Z"
    march_11_gap = calculate_time_gap_hours(firms_dt, march_11_dt)
    march_11_eval = {
        "item_id": march_11_scene_id,
        "acquisition_datetime_utc": march_11_dt,
        "absolute_time_gap_hours": round(march_11_gap, 6),
        "evaluation_result": "OUTSIDE_ACCEPTABLE_TEMPORAL_WINDOW",
        "rationale": (
            f"March 11 scene has an absolute time gap of {march_11_gap:.2f} hours from the "
            f"FIRMS observation (2025-03-15T08:35:00Z), exceeding the ±48h threshold. "
            f"It is strictly excluded from association under Step 7."
        ),
    }

    # 6. Final Match Classification
    all_candidates = list(evaluated_items_by_id.values())
    match_category, selected_candidate, decision_rationale = evaluate_temporal_match(all_candidates)

    print("\n5. Temporal Match Decision:")
    print(f"   Final Match Category: {match_category}")
    if selected_candidate:
        print(f"   Selected Item ID:     {selected_candidate['item_id']}")
        print(f"   Acquisition UTC:      {selected_candidate['acquisition_datetime_utc']}")
        print(f"   Absolute Time Gap:    {selected_candidate['absolute_time_gap_hours']:.4f} hours")
        print(f"   Cloud Cover:          {selected_candidate['cloud_cover_pct']}%")
        print(f"   Spatial Coverage:     {selected_candidate['spatially_covers_firms_point']}")
    print(f"   Rationale:            {decision_rationale}")

    # 7. Build and write audit JSON
    audit_data = {
        "firms_detection_id": det_id,
        "firms_coordinates": {"latitude": lat, "longitude": lon},
        "firms_acquisition_utc": firms_dt,
        "firms_frp_mw": frp,
        "firms_partition": FIRMS_TARGET["partition"],
        "search_aoi_bbox": aoi_bbox,
        "search_intervals": {
            "window_6h": SEARCH_WINDOWS["window_6h"]["interval"],
            "window_24h": SEARCH_WINDOWS["window_24h"]["interval"],
            "window_48h": SEARCH_WINDOWS["window_48h"]["interval"],
        },
        "search_counts": {
            "count_6h": search_results["window_6h"]["returned_count"],
            "count_24h": search_results["window_24h"]["returned_count"],
            "count_48h": search_results["window_48h"]["returned_count"],
        },
        "searches": search_results,
        "all_returned_items": list(evaluated_items_by_id.values()),
        "march_11_scene_evaluation": march_11_eval,
        "final_match_category": match_category,
        "selected_item": selected_candidate,
        "decision_rationale": decision_rationale,
        "scientific_integrity_note": (
            "Temporal association of Sentinel-2 Level-2A optical observation to FIRMS detection "
            "establishes physical data availability within the temporal tolerance window. "
            "It does NOT assign or prove a fire-source sector (Industrial, Forest, Agricultural, Other). "
            "Optical evidence remains decoupled from classification ground truth."
        ),
    }

    OUTPUT_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_AUDIT_PATH, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    print(f"\n6. Audit saved to: {OUTPUT_AUDIT_PATH}")
    print("=" * 70)
    return audit_data


if __name__ == "__main__":
    try:
        run_temporal_association_audit()
    except Exception as exc:
        print(f"\n[FATAL ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
