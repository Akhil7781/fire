"""
Sentinel-2 L2A Valid Candidate Discovery and Verification Script (Stage 8.5).

Finds and validates ONE real FIRMS detection paired with a real Sentinel-2 L2A scene
under strict Stage 8.5 optical association criteria:
1. Product is Sentinel-2 L2A (sentinel-2-l2a)
2. Spatially covers the FIRMS coordinate (bounding box and exact geometry)
3. Absolute temporal gap <= 48.0 hours
4. Scene-level cloud cover <= 10.0% (strictly enforced)
5. Band B02 available
6. Band B03 available
7. Band B04 available
8. Band B11 available
9. Band B12 available

SECURITY INVARIANT:
Never prints or persists CDSE Client Secret, OAuth access token, or Authorization headers.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
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

# Load root-level .env
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
)

DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "validated_extraction_candidate.json"
MAX_CLOUD_COVER_PCT = 10.0
MAX_TEMPORAL_GAP_HOURS = 48.0

# Authoritative FIRMS Candidate from data/interim/causal_features_2025.parquet
FIRMS_VALIDATED_TARGET = {
    "detection_id": "b18ce007dc003134da73556195ff1c84b9cecc89cf80a03cc3421eae8ce91624",
    "latitude": 21.63424,
    "longitude": 76.66431,
    "acq_datetime_utc": "2025-03-11T08:10:00Z",
    "frp": 20.85,
    "partition": "train",
}


def parse_iso_datetime(dt_str: str) -> datetime:
    """Parses ISO 8601 UTC datetime string to aware datetime."""
    import dateutil.parser
    clean = dt_str.replace("Z", "+00:00")
    return dateutil.parser.isoparse(clean)


def calculate_time_gap_hours(firms_dt_str: str, s2_dt_str: str) -> float:
    """Calculates absolute temporal gap in decimal hours."""
    t_firms = parse_iso_datetime(firms_dt_str)
    t_s2 = parse_iso_datetime(s2_dt_str)
    delta_sec = abs((t_s2 - t_firms).total_seconds())
    return delta_sec / 3600.0


def classify_temporal_match(gap_hours: float) -> str:
    """Classifies temporal association according to the strict hierarchical rules."""
    if gap_hours <= 6.0:
        return "CLOSE_MATCH_6H"
    elif gap_hours <= 24.0:
        return "MATCH_24H"
    elif gap_hours <= 48.0:
        return "MATCH_48H"
    else:
        return "NO_ACCEPTABLE_TEMPORAL_MATCH"


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

    if geometry and geometry.get("coordinates"):
        try:
            from shapely.geometry import shape, Point
            poly = shape(geometry)
            pt = Point(firms_lon, firms_lat)
            return bool(poly.contains(pt))
        except Exception:
            return in_bbox
    return in_bbox


def verify_bands_available(
    available_band_summaries: List[Dict[str, Any]],
    required_band_names: List[str] = REQUIRED_BANDS,
) -> Tuple[bool, List[str]]:
    """Verifies that all required spectral bands are present in the collection."""
    names_present = {b.get("name") for b in available_band_summaries if "name" in b}
    missing = [req for req in required_band_names if req not in names_present]
    all_available = len(missing) == 0
    return all_available, [b for b in required_band_names if b in names_present]


def evaluate_candidate_scene(
    firms_record: Dict[str, Any],
    scene_feature: Dict[str, Any],
    collection_bands: List[Dict[str, Any]],
    max_cloud: float = MAX_CLOUD_COVER_PCT,
    max_gap_hours: float = MAX_TEMPORAL_GAP_HOURS,
    required_bands: List[str] = REQUIRED_BANDS,
) -> Dict[str, Any]:
    """
    Evaluates a candidate Sentinel-2 scene feature against all Stage 8.5 criteria.
    Returns evaluation dictionary with boolean decision flags.
    """
    props = scene_feature.get("properties", {})
    item_id = scene_feature.get("id", "UNKNOWN")
    platform = props.get("platform", "sentinel-2")
    s2_datetime_str = props.get("datetime", "")
    cloud_cover = props.get("eo:cloud_cover", 100.0)
    bbox = scene_feature.get("bbox", [])
    geometry = scene_feature.get("geometry", {})

    firms_lat = firms_record["latitude"]
    firms_lon = firms_record["longitude"]
    firms_dt_str = firms_record["acq_datetime_utc"]

    # 1. Spatial coverage
    spatial_ok = check_spatial_coverage(firms_lat, firms_lon, bbox, geometry)

    # 2. Temporal gap
    if s2_datetime_str and firms_dt_str:
        gap_hours = calculate_time_gap_hours(firms_dt_str, s2_datetime_str)
        temporal_match_cat = classify_temporal_match(gap_hours)
        temporal_ok = gap_hours <= max_gap_hours
    else:
        gap_hours = 9999.0
        temporal_match_cat = "NO_ACCEPTABLE_TEMPORAL_MATCH"
        temporal_ok = False

    # 3. Cloud cover constraint (strictly <= 10.0%)
    cloud_ok = (cloud_cover is not None) and (cloud_cover <= max_cloud)

    # 4. Band availability
    bands_ok, confirmed_bands = verify_bands_available(collection_bands, required_bands)

    # Global validity
    is_valid = spatial_ok and temporal_ok and cloud_ok and bands_ok

    rejection_reasons = []
    if not spatial_ok:
        rejection_reasons.append("Spatial footprint does not contain FIRMS coordinates.")
    if not temporal_ok:
        rejection_reasons.append(f"Temporal gap {gap_hours:.2f}h exceeds limit {max_gap_hours}h.")
    if not cloud_ok:
        rejection_reasons.append(f"Cloud cover {cloud_cover}% exceeds ceiling {max_cloud}%.")
    if not bands_ok:
        rejection_reasons.append(f"Missing required bands from {required_bands}.")

    return {
        "item_id": item_id,
        "platform": platform,
        "datetime_utc": s2_datetime_str,
        "cloud_cover_pct": cloud_cover,
        "bbox": bbox,
        "exact_time_gap_hours": round(gap_hours, 6),
        "match_category": temporal_match_cat,
        "spatially_covers_firms_point": spatial_ok,
        "bands_available": confirmed_bands,
        "is_valid": is_valid,
        "rejection_reasons": rejection_reasons,
    }


def build_validated_candidate_artifact(
    firms_record: Dict[str, Any],
    scene_eval: Dict[str, Any],
) -> Dict[str, Any]:
    """Formats the validated FIRMS + Sentinel-2 pair into the canonical schema."""
    if not scene_eval.get("is_valid"):
        raise ValueError(
            f"Cannot build artifact: Scene {scene_eval.get('item_id')} rejected: "
            f"{'; '.join(scene_eval.get('rejection_reasons', []))}"
        )

    return {
        "status": "VALIDATED_FOR_EXTRACTION",
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "criteria_enforced": {
            "product": "sentinel-2-l2a",
            "spatial_coverage": True,
            "max_temporal_gap_hours": MAX_TEMPORAL_GAP_HOURS,
            "max_cloud_cover_pct": MAX_CLOUD_COVER_PCT,
            "required_bands": REQUIRED_BANDS,
        },
        "firms_detection": {
            "detection_id": firms_record["detection_id"],
            "latitude": firms_record["latitude"],
            "longitude": firms_record["longitude"],
            "acq_datetime_utc": firms_record["acq_datetime_utc"],
            "frp": firms_record["frp"],
            "partition": firms_record["partition"],
        },
        "sentinel2_scene": {
            "item_id": scene_eval["item_id"],
            "platform": scene_eval["platform"],
            "datetime_utc": scene_eval["datetime_utc"],
            "cloud_cover_pct": scene_eval["cloud_cover_pct"],
            "bbox": scene_eval["bbox"],
            "exact_time_gap_hours": scene_eval["exact_time_gap_hours"],
            "match_category": scene_eval["match_category"],
            "spatially_covers_firms_point": scene_eval["spatially_covers_firms_point"],
            "bands_available": scene_eval["bands_available"],
        },
    }


def find_and_validate_candidate(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    firms_target: Dict[str, Any] = FIRMS_VALIDATED_TARGET,
) -> Dict[str, Any]:
    """
    Queries CDSE Catalog API for the target FIRMS detection, verifies all 9 criteria,
    and writes the validated extraction candidate JSON artifact.
    """
    print("\n" + "=" * 70)
    print("STAGE 8.5 — REAL SENTINEL-2 L2A / FIRMS CANDIDATE DISCOVERY")
    print("=" * 70)

    # 1. Credentials
    client_id = effective_client_id
    client_secret = effective_client_secret
    if not client_id or not client_secret:
        raise RuntimeError("CDSE credentials not configured in environment or .env file.")

    print("[1/5] Authenticating with Copernicus Data Space Ecosystem...")
    access_token = get_cdse_access_token(client_id, client_secret)
    print("      OAuth authentication successful.")

    # 2. Band verification
    print("[2/5] Verifying collection band summaries for sentinel-2-l2a...")
    collection_bands = get_collection_band_summaries(access_token)
    all_bands_ok, confirmed_bands = verify_bands_available(collection_bands, REQUIRED_BANDS)
    if not all_bands_ok:
        raise RuntimeError(f"Sentinel-2 collection missing required bands: {REQUIRED_BANDS}")
    print(f"      Required bands verified available: {confirmed_bands}")

    # 3. Query Catalog for ±48 hours around target FIRMS coordinate
    lat = firms_target["latitude"]
    lon = firms_target["longitude"]
    det_dt = firms_target["acq_datetime_utc"]
    delta_deg = 0.05
    query_bbox = [lon - delta_deg, lat - delta_deg, lon + delta_deg, lat + delta_deg]

    # Compute ±48h ISO interval
    target_dt = parse_iso_datetime(det_dt)
    import datetime as dt_mod
    start_dt = target_dt - dt_mod.timedelta(hours=48)
    end_dt = target_dt + dt_mod.timedelta(hours=48)
    datetime_range = f"{start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}"

    print(f"[3/5] Querying Sentinel Hub STAC Catalog for detection {firms_target['detection_id'][:16]}...")
    print(f"      Coordinates: ({lat:.5f}°N, {lon:.5f}°E)")
    print(f"      FIRMS UTC:   {det_dt}")
    print(f"      Search window: {datetime_range}")

    catalog_data = search_sentinel2_catalog(
        access_token=access_token,
        bbox=query_bbox,
        datetime_range=datetime_range,
        limit=10,
    )
    features = catalog_data.get("features", [])
    print(f"      Found {len(features)} candidate granules in search window.")

    # 4. Evaluate candidates against all 9 criteria
    print("[4/5] Evaluating candidate scenes against Stage 8.5 criteria...")
    valid_evaluations: List[Dict[str, Any]] = []
    for feat in features:
        evaluation = evaluate_candidate_scene(
            firms_record=firms_target,
            scene_feature=feat,
            collection_bands=collection_bands,
            max_cloud=MAX_CLOUD_COVER_PCT,
            max_gap_hours=MAX_TEMPORAL_GAP_HOURS,
            required_bands=REQUIRED_BANDS,
        )
        if evaluation["is_valid"]:
            valid_evaluations.append(evaluation)
            print(f"      [ACCEPTED] Scene {evaluation['item_id']}")
            print(f"                 Cloud Cover: {evaluation['cloud_cover_pct']:.1f}% (<= 10.0%)")
            print(f"                 Time Gap:    {evaluation['exact_time_gap_hours']:.4f}h ({evaluation['match_category']})")
            print(f"                 Spatial OK:  {evaluation['spatially_covers_firms_point']}")
            print(f"                 Bands OK:    {evaluation['bands_available']}")
        else:
            reasons_str = "; ".join(evaluation["rejection_reasons"])
            print(f"      [REJECTED] Scene {evaluation['item_id']}: {reasons_str}")

    if not valid_evaluations:
        raise RuntimeError(
            f"No candidate Sentinel-2 scene satisfied all criteria for detection {firms_target['detection_id']}."
        )

    # Pick the best valid candidate (lowest temporal gap)
    valid_evaluations.sort(key=lambda x: x["exact_time_gap_hours"])
    best_eval = valid_evaluations[0]

    # Build validated candidate artifact
    artifact_data = build_validated_candidate_artifact(firms_target, best_eval)

    # 5. Save artifact
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(artifact_data, f, indent=2)

    sha256_hash = hashlib.sha256(output_path.read_bytes()).hexdigest()
    print(f"[5/5] Saved validated candidate artifact to:")
    print(f"      Path:   {output_path}")
    print(f"      SHA256: {sha256_hash}")
    print(f"      Status: {artifact_data['status']}")
    print("=" * 70)

    return artifact_data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find and validate ONE real FIRMS + Sentinel-2 L2A pair."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to save validated candidate JSON.",
    )
    args = parser.parse_args()

    try:
        find_and_validate_candidate(output_path=args.output)
        return 0
    except Exception as exc:
        print(f"\n[FATAL ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
