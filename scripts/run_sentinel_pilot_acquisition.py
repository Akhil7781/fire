"""
Sentinel-2 L2A Dataset Acquisition Pilot Script (Stage 8.6).

Acquires a 20-chip pilot of real Sentinel-2 Level-2A imagery across geographically
diverse regions of India (North, Central, South, East, West) using the official
Copernicus Data Space Ecosystem (CDSE) Sentinel Hub Processing API.

Strict Invariants:
1. 20 real Sentinel-2 chips (512 x 512, 10 m resolution, 5 bands).
2. Fixed canonical band order: B02, B03, B04, B11, B12.
3. FLOAT32 reflectance, native 20m B11/B12 resampled to 10m via BILINEAR.
4. Scene-level cloud cover <= 10.0% (strictly enforced).
5. Temporal gap <= 48.0 hours where FIRMS-associated.
6. NO labels created: label_status = 'UNLABELED', association_status = 'candidate_context_only'.
7. ZERO synthetic images, ZERO model modifications, ZERO embedding generation.
8. Zero credential or token leakage.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
import numpy as np
import pandas as pd
from PIL import Image
import pyarrow.parquet as pq
import pyproj
import rasterio
from rasterio.transform import from_origin
import requests
from shapely.geometry import Point, box, mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load root-level .env
load_dotenv(PROJECT_ROOT / ".env")

from scripts.test_cdse_auth import (
    effective_client_id,
    effective_client_secret,
)
from scripts.test_sentinel_catalog import (
    get_cdse_access_token,
    get_collection_band_summaries,
    search_sentinel2_catalog,
)
import dateutil.parser
from scripts.find_valid_sentinel_candidate import (
    evaluate_candidate_scene,
)


def parse_iso_datetime(dt_str: str) -> datetime:
    """Parses ISO 8601 UTC datetime string to aware datetime."""
    clean = dt_str.replace("Z", "+00:00")
    return dateutil.parser.isoparse(clean)

PROCESSING_API_URL = "https://sh.dataspace.copernicus.eu/process/v1"
TIMEOUT_SECONDS = 60

CHIP_PIXELS = 512
PIXEL_RESOLUTION_M = 10.0
CHIP_SPAN_M = CHIP_PIXELS * PIXEL_RESOLUTION_M  # 5120.0 m
MAX_CLOUD_COVER_PCT = 10.0
MAX_TEMPORAL_GAP_HOURS = 48.0
BAND_ORDER = ["B02", "B03", "B04", "B11", "B12"]
PILOT_TARGET_COUNT = 20

PILOT_BASE_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "pilot"
CHIPS_DIR = PILOT_BASE_DIR / "chips"
METADATA_DIR = PILOT_BASE_DIR / "metadata"
PREVIEW_DIR = PILOT_BASE_DIR / "preview"
AUDIT_SUMMARY_PATH = PILOT_BASE_DIR / "pilot_audit_summary.json"

EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [{
      bands: ["B02", "B03", "B04", "B11", "B12"],
      units: "REFLECTANCE"
    }],
    output: {
      id: "default",
      bands: 5,
      sampleType: "FLOAT32"
    }
  };
}

function evaluatePixel(sample) {
  return [sample.B02, sample.B03, sample.B04, sample.B11, sample.B12];
}
"""


def get_utm_epsg(lon: float) -> Tuple[int, int, str]:
    """Computes UTM zone and EPSG code for any longitude in India."""
    zone = int((lon + 180) // 6) + 1
    epsg = 32600 + zone
    crs_uri = f"http://www.opengis.net/def/crs/EPSG/0/{epsg}"
    return zone, epsg, crs_uri


def compute_aoi_for_point(
    lat: float,
    lon: float,
    span_m: float = CHIP_SPAN_M,
) -> Dict[str, Any]:
    """
    Computes a projected 5.12 km x 5.12 km Area of Interest centered on (lat, lon)
    using the appropriate UTM Zone projection.
    """
    zone, epsg, crs_uri = get_utm_epsg(lon)
    to_utm = pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    to_wgs = pyproj.Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)

    center_x, center_y = to_utm.transform(lon, lat)
    half_span = span_m / 2.0

    min_x = round(center_x - half_span, 2)
    max_x = round(center_x + half_span, 2)
    min_y = round(center_y - half_span, 2)
    max_y = round(center_y + half_span, 2)

    utm_bbox = [min_x, min_y, max_x, max_y]

    wgs_min_lon, wgs_min_lat = to_wgs.transform(min_x, min_y)
    wgs_max_lon, wgs_max_lat = to_wgs.transform(max_x, max_y)
    wgs_bbox = [
        round(wgs_min_lon, 6),
        round(wgs_min_lat, 6),
        round(wgs_max_lon, 6),
        round(wgs_max_lat, 6),
    ]

    utm_geom = mapping(box(min_x, min_y, max_x, max_y))

    return {
        "center_wgs84": {"latitude": lat, "longitude": lon},
        "center_utm": {"x": round(center_x, 2), "y": round(center_y, 2)},
        "chip_span_meters": span_m,
        "utm_zone": zone,
        "utm_epsg": epsg,
        "utm_crs_uri": crs_uri,
        "utm_bbox": utm_bbox,
        "wgs84_bbox": wgs_bbox,
        "utm_geometry": utm_geom,
    }


def classify_indian_region(lat: float, lon: float) -> str:
    """Classifies an Indian coordinate into broad geographic regions."""
    if lat >= 27.0:
        return "NORTH"
    elif lat < 16.0:
        return "SOUTH"
    elif lon >= 83.0:
        return "EAST"
    elif lon < 75.0 and lat <= 27.0:
        return "WEST"
    else:
        return "CENTRAL"


def build_processing_payload(
    aoi: Dict[str, Any],
    time_from: str,
    time_to: str,
    width: int = CHIP_PIXELS,
    height: int = CHIP_PIXELS,
) -> Dict[str, Any]:
    """Constructs Sentinel Hub Processing API request payload."""
    return {
        "input": {
            "bounds": {
                "bbox": aoi["utm_bbox"],
                "properties": {
                    "crs": aoi["utm_crs_uri"]
                }
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": time_from,
                            "to": time_to
                        },
                        "maxCloudCoverage": 10,
                        "mosaickingOrder": "mostRecent"
                    },
                    "processing": {
                        "upsampling": "BILINEAR",
                        "downsampling": "BILINEAR"
                    }
                }
            ]
        },
        "output": {
            "width": width,
            "height": height,
            "responses": [
                {
                    "identifier": "default",
                    "format": {
                        "type": "image/tiff"
                    }
                }
            ]
        },
        "evalscript": EVALSCRIPT
    }


def execute_processing_request(
    access_token: str,
    payload: Dict[str, Any],
    url: str = PROCESSING_API_URL,
    timeout: int = TIMEOUT_SECONDS,
    max_retries: int = 3,
) -> bytes:
    """Submits POST request to Sentinel Hub Processing API and retrieves GeoTIFF bytes."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "image/tiff",
        "Content-Type": "application/json",
    }

    last_err = ""
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                if len(resp.content) == 0:
                    raise RuntimeError("Processing API returned HTTP 200 but content is empty.")
                return resp.content
            elif resp.status_code in (408, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(attempt * 2)
                continue
            else:
                last_err = f"HTTP {resp.status_code}: {resp.text[:300]}"
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_err = str(exc)
            if attempt < max_retries:
                time.sleep(attempt * 2)
                continue

    raise RuntimeError(f"Processing API request failed after {max_retries} attempts: {last_err}")


def validate_chip_raster(
    tiff_path: Path,
    expected_lat: float,
    expected_lon: float,
    expected_epsg: int,
    expected_bands: int = 5,
    expected_dim: int = CHIP_PIXELS,
    expected_res: float = PIXEL_RESOLUTION_M,
) -> Dict[str, Any]:
    """Rigorous 17-point validation of extracted GeoTIFF raster."""
    if not tiff_path.exists():
        raise FileNotFoundError(f"Raster file does not exist: {tiff_path}")
    if tiff_path.stat().st_size == 0:
        raise ValueError(f"Raster file is 0 bytes: {tiff_path}")

    val_res = {}
    with rasterio.open(tiff_path) as src:
        val_res["file_readable"] = True
        val_res["driver"] = src.driver

        if src.count != expected_bands:
            raise ValueError(f"Expected {expected_bands} bands, got {src.count}")
        val_res["band_count"] = src.count

        if src.width != expected_dim or src.height != expected_dim:
            raise ValueError(f"Expected {expected_dim}x{expected_dim}, got {src.width}x{src.height}")
        val_res["width"] = src.width
        val_res["height"] = src.height

        dtypes = list(src.dtypes)
        if not all(dt == "float32" for dt in dtypes):
            raise ValueError(f"Expected all bands float32, got {dtypes}")
        val_res["dtypes"] = dtypes

        crs = src.crs
        if crs is None or crs.to_epsg() != expected_epsg:
            raise ValueError(f"Expected CRS EPSG:{expected_epsg}, got {crs}")
        val_res["crs"] = str(crs)

        transform = src.transform
        dx = abs(transform.a)
        dy = abs(transform.e)
        if abs(dx - expected_res) > 0.05 or abs(dy - expected_res) > 0.05:
            raise ValueError(f"Expected pixel resolution ~{expected_res}m, got {dx}m x {dy}m")
        val_res["pixel_resolution_m"] = [round(dx, 4), round(dy, 4)]

        bounds = src.bounds
        val_res["bounds"] = {
            "left": round(bounds.left, 2),
            "bottom": round(bounds.bottom, 2),
            "right": round(bounds.right, 2),
            "top": round(bounds.top, 2),
        }

        # Check coordinate containment
        transformer = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        pt_x, pt_y = transformer.transform(expected_lon, expected_lat)
        in_bounds = (bounds.left <= pt_x <= bounds.right) and (bounds.bottom <= pt_y <= bounds.top)
        val_res["center_point_inside_chip"] = in_bounds
        if not in_bounds:
            raise ValueError(f"Center point ({pt_x:.2f}, {pt_y:.2f}) outside raster bounds: {bounds}")

        # Per-band statistics
        raster_data = src.read()
        band_stats = {}
        for idx, band_name in enumerate(BAND_ORDER):
            b_arr = raster_data[idx]
            finite_mask = np.isfinite(b_arr)
            valid_count = int(np.sum(finite_mask))
            nodata_count = int(np.sum(~finite_mask))

            if valid_count == 0:
                raise ValueError(f"Band {idx+1} ({band_name}) is entirely empty (0 valid pixels).")

            valid_vals = b_arr[finite_mask]
            min_val = float(np.min(valid_vals))
            max_val = float(np.max(valid_vals))
            mean_val = float(np.mean(valid_vals))
            std_val = float(np.std(valid_vals))

            band_stats[band_name] = {
                "band_index": idx + 1,
                "band_name": band_name,
                "min": round(min_val, 6),
                "max": round(max_val, 6),
                "mean": round(mean_val, 6),
                "std": round(std_val, 6),
                "valid_pixel_count": valid_count,
                "nodata_pixel_count": nodata_count,
                "total_pixel_count": int(b_arr.size),
            }

        val_res["band_statistics"] = band_stats
        val_res["is_valid"] = True

    return val_res


def generate_preview_images(
    tiff_path: Path,
    preview_dir: Path,
    file_prefix: str,
) -> Dict[str, Path]:
    """Generates non-authoritative RGB and SWIR false-color PNG preview images."""
    preview_dir.mkdir(parents=True, exist_ok=True)

    with rasterio.open(tiff_path) as src:
        arr = src.read()  # (5, 512, 512), order: [B02, B03, B04, B11, B12]

    def to_rgb_img(r_band: np.ndarray, g_band: np.ndarray, b_band: np.ndarray) -> Image.Image:
        stack = np.stack([r_band, g_band, b_band], axis=-1)
        stack = np.nan_to_num(stack, nan=0.0, posinf=1.0, neginf=0.0)
        p2, p98 = np.percentile(stack, (2, 98))
        if p98 <= p2:
            p98 = p2 + 1e-4
        scaled = np.clip((stack - p2) / (p98 - p2), 0.0, 1.0)
        uint8_arr = (scaled * 255.0).astype(np.uint8)
        return Image.fromarray(uint8_arr)

    # RGB: B04 (idx 2), B03 (idx 1), B02 (idx 0)
    rgb_img = to_rgb_img(arr[2], arr[1], arr[0])
    rgb_path = preview_dir / f"{file_prefix}_rgb_preview.png"
    rgb_img.save(rgb_path, format="PNG")

    # SWIR: B12 (idx 4), B11 (idx 3), B04 (idx 2)
    swir_img = to_rgb_img(arr[4], arr[3], arr[2])
    swir_path = preview_dir / f"{file_prefix}_swir_preview.png"
    swir_img.save(swir_path, format="PNG")

    return {
        "rgb_preview": rgb_path,
        "swir_preview": swir_path,
    }


def save_pilot_sidecar_json(
    json_path: Path,
    candidate_id: str,
    firms_info: Dict[str, Any],
    sentinel2_info: Dict[str, Any],
    extraction_info: Dict[str, Any],
) -> None:
    """Saves metadata sidecar JSON, strictly enforcing zero secret leakage and label_status = UNLABELED."""
    data = {
        "status": "VALIDATED_PILOT_CHIP_EXTRACTION",
        "candidate_id": candidate_id,
        "label_status": "UNLABELED",
        "pilot_phase": "STAGE_8.6_PILOT_ACQUISITION",
        "firms_metadata": {
            "detection_id": firms_info.get("detection_id"),
            "latitude": firms_info.get("latitude"),
            "longitude": firms_info.get("longitude"),
            "acquisition_datetime_utc": firms_info.get("acquisition_datetime_utc"),
            "frp": firms_info.get("frp"),
            "association_status": "candidate_context_only",
            "geographic_region": firms_info.get("region"),
        },
        "sentinel2_scene": {
            "product_id": sentinel2_info.get("product_id"),
            "platform": sentinel2_info.get("platform"),
            "acquisition_datetime_utc": sentinel2_info.get("acquisition_datetime_utc"),
            "temporal_gap_hours": sentinel2_info.get("temporal_gap_hours"),
            "cloud_cover_pct": sentinel2_info.get("cloud_cover_pct"),
            "collection": sentinel2_info.get("collection", "sentinel-2-l2a"),
            "tile_id": sentinel2_info.get("tile_id"),
        },
        "extraction": {
            "processing_api_endpoint": extraction_info["processing_api_endpoint"],
            "aoi_geometry": extraction_info["aoi_geometry"],
            "aoi_bbox_utm": extraction_info["aoi_bbox_utm"],
            "aoi_bbox_wgs84": extraction_info["aoi_bbox_wgs84"],
            "projected_crs": extraction_info["projected_crs"],
            "output_crs": extraction_info["output_crs"],
            "output_width_pixels": extraction_info["output_width_pixels"],
            "output_height_pixels": extraction_info["output_height_pixels"],
            "output_resolution_meters": extraction_info["output_resolution_meters"],
            "band_order": extraction_info["band_order"],
            "input_units": extraction_info["input_units"],
            "resampling_method": extraction_info["resampling_method"],
            "output_dtype": extraction_info["output_dtype"],
            "extraction_timestamp_utc": extraction_info["extraction_timestamp_utc"],
            "file_size_bytes": extraction_info["file_size_bytes"],
            "sha256_checksum": extraction_info["sha256_checksum"],
            "previews": extraction_info.get("previews", {}),
            "band_statistics": extraction_info.get("band_statistics", {}),
        },
    }

    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def discover_pilot_candidates(
    access_token: str,
    target_count: int = PILOT_TARGET_COUNT,
    max_cloud: float = MAX_CLOUD_COVER_PCT,
    max_gap: float = MAX_TEMPORAL_GAP_HOURS,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Discovers diverse Indian candidate locations and validates them against the CDSE STAC Catalog.
    Aims for 4 candidates from each of 5 geographic regions: NORTH, CENTRAL, SOUTH, EAST, WEST.
    """
    print("\n[1/4] Discovering candidate pool from authoritative 2025 FIRMS detections...")
    collection_bands = get_collection_band_summaries(access_token)

    table = pq.read_table(
        PROJECT_ROOT / "data" / "interim" / "causal_features_2025.parquet",
        columns=["detection_id", "latitude", "longitude", "acq_datetime_utc", "frp", "partition"],
    )
    df = table.to_pandas()
    df["month"] = df["acq_datetime_utc"].dt.month
    march_df = df[df["month"] == 3].copy()
    march_df["region"] = march_df.apply(
        lambda r: classify_indian_region(r["latitude"], r["longitude"]), axis=1
    )

    regions = ["NORTH", "CENTRAL", "SOUTH", "EAST", "WEST"]
    quota_per_region = target_count // len(regions)  # 4 each

    accepted_candidates: List[Dict[str, Any]] = []
    rejected_records: List[Dict[str, Any]] = []
    seen_products: set = set()
    candidate_counter = 1

    import datetime as dt_mod

    for reg in regions:
        reg_df = march_df[march_df["region"] == reg]
        print(f"      Scanning region {reg} ({len(reg_df)} available detections, target: {quota_per_region})...")
        sampled = reg_df.sample(n=min(60, len(reg_df)), random_state=42 + len(reg))

        reg_accepted = 0
        for _, row in sampled.iterrows():
            if reg_accepted >= quota_per_region:
                break

            lat = float(row["latitude"])
            lon = float(row["longitude"])
            det_id = str(row["detection_id"])
            det_dt = row["acq_datetime_utc"].strftime("%Y-%m-%dT%H:%M:%SZ")

            firms_rec = {
                "detection_id": det_id,
                "latitude": lat,
                "longitude": lon,
                "acq_datetime_utc": det_dt,
                "frp": float(row["frp"]),
                "partition": str(row["partition"]),
                "region": reg,
            }

            target_dt = parse_iso_datetime(det_dt)
            start_dt = target_dt - dt_mod.timedelta(hours=max_gap)
            end_dt = target_dt + dt_mod.timedelta(hours=max_gap)
            dt_range = f"{start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            query_bbox = [lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05]

            try:
                cat_results = search_sentinel2_catalog(
                    access_token=access_token,
                    bbox=query_bbox,
                    datetime_range=dt_range,
                    limit=5,
                )
            except Exception as e:
                rejected_records.append({
                    "detection_id": det_id,
                    "region": reg,
                    "reason": f"STAC API query error: {str(e)}",
                })
                continue

            features = cat_results.get("features", [])
            if not features:
                rejected_records.append({
                    "detection_id": det_id,
                    "region": reg,
                    "reason": "No candidate Sentinel-2 scene found in ±48h window",
                })
                continue

            # Evaluate features
            candidate_found_for_row = False
            for feat in features:
                product_id = feat.get("id")
                if product_id in seen_products:
                    rejected_records.append({
                        "detection_id": det_id,
                        "product_id": product_id,
                        "region": reg,
                        "reason": f"Duplicate scene {product_id} already selected for another candidate",
                    })
                    continue

                eval_res = evaluate_candidate_scene(
                    firms_record=firms_rec,
                    scene_feature=feat,
                    collection_bands=collection_bands,
                    max_cloud=max_cloud,
                    max_gap_hours=max_gap,
                    required_bands=BAND_ORDER,
                )

                if eval_res["is_valid"]:
                    cand_id = f"PILOT_{candidate_counter:02d}_{reg}"
                    candidate_counter += 1
                    seen_products.add(product_id)
                    reg_accepted += 1
                    candidate_found_for_row = True

                    tile_id = feat.get("properties", {}).get("sentinel:tile_id", "")
                    if not tile_id and "_" in product_id:
                        parts = product_id.split("_")
                        for p in parts:
                            if p.startswith("T") and len(p) == 6:
                                tile_id = p
                                break

                    accepted_candidates.append({
                        "candidate_id": cand_id,
                        "firms_record": firms_rec,
                        "scene_eval": eval_res,
                        "product_id": product_id,
                        "tile_id": tile_id,
                        "region": reg,
                    })
                    print(
                        f"        Accepted [{cand_id}]: Scene={product_id[:35]}... "
                        f"Cloud={eval_res['cloud_cover_pct']:.1f}% Gap={eval_res['exact_time_gap_hours']:.2f}h"
                    )
                    break
                else:
                    reasons = "; ".join(eval_res.get("rejection_reasons", []))
                    rejected_records.append({
                        "detection_id": det_id,
                        "product_id": product_id,
                        "region": reg,
                        "reason": reasons,
                    })

        print(f"      Region {reg}: {reg_accepted}/{quota_per_region} candidates validated.")

    print(f"\n      Total validated candidates across India: {len(accepted_candidates)}/{target_count}")
    print(f"      Total rejected candidate evaluations: {len(rejected_records)}")
    return accepted_candidates, rejected_records


def run_pilot_acquisition() -> Dict[str, Any]:
    """Executes the complete Stage 8.6 Real Sentinel-2 Dataset Acquisition Pilot."""
    print("=" * 80)
    print("STAGE 8.6 — REAL SENTINEL-2 DATASET ACQUISITION PILOT")
    print("=" * 80)

    # 1. Credentials
    client_id = effective_client_id
    client_secret = effective_client_secret
    if not client_id or not client_secret:
        raise RuntimeError("CDSE credentials not configured in environment or .env file.")

    print("[Step 1] Authenticating with Copernicus Data Space Ecosystem...")
    access_token = get_cdse_access_token(client_id, client_secret)
    print("         OAuth authentication successful.")

    # 2. Discover Candidates
    accepted_candidates, rejected_records = discover_pilot_candidates(
        access_token=access_token,
        target_count=PILOT_TARGET_COUNT,
        max_cloud=MAX_CLOUD_COVER_PCT,
        max_gap=MAX_TEMPORAL_GAP_HOURS,
    )

    if len(accepted_candidates) < PILOT_TARGET_COUNT:
        print(
            f"[WARNING] Discovered {len(accepted_candidates)} viable candidates (target was {PILOT_TARGET_COUNT}). "
            "Proceeding without relaxing frozen criteria."
        )

    # 3. Create Output Directories
    CHIPS_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    # 4. Extract Each Chip via Processing API
    print(f"\n[Step 2] Extracting {len(accepted_candidates)} real Sentinel-2 chips via Processing API...")
    extracted_records: List[Dict[str, Any]] = []
    validation_failures: List[Dict[str, Any]] = []

    for idx, cand in enumerate(accepted_candidates, start=1):
        cand_id = cand["candidate_id"]
        firms_rec = cand["firms_record"]
        scene_eval = cand["scene_eval"]
        product_id = cand["product_id"]

        lat = firms_rec["latitude"]
        lon = firms_rec["longitude"]
        s2_dt_str = scene_eval["datetime_utc"]
        s2_date = s2_dt_str[:10].replace("-", "")

        file_prefix = f"{cand_id}_sentinel2_{s2_date}_chip"
        tif_path = CHIPS_DIR / f"{file_prefix}.tif"
        json_path = METADATA_DIR / f"{file_prefix}.json"

        print(f"\n  [{idx:02d}/{len(accepted_candidates):02d}] Processing {cand_id} ({firms_rec['region']})...")
        print(f"       Coordinates: ({lat:.5f}°N, {lon:.5f}°E)")
        print(f"       Scene:       {product_id}")
        print(f"       Cloud Cover: {scene_eval['cloud_cover_pct']:.1f}%")
        print(f"       Time Gap:    {scene_eval['exact_time_gap_hours']:.2f}h")

        # Compute AOI
        aoi = compute_aoi_for_point(lat, lon, span_m=CHIP_SPAN_M)

        # Narrow temporal window around scene timestamp (±5 minutes)
        s2_dt = parse_iso_datetime(s2_dt_str)
        import datetime as dt_mod
        t_from = (s2_dt - dt_mod.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        t_to = (s2_dt + dt_mod.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

        payload = build_processing_payload(aoi, time_from=t_from, time_to=t_to)

        # Execute Request
        try:
            raw_tiff_bytes = execute_processing_request(access_token, payload)
            with open(tif_path, "wb") as f:
                f.write(raw_tiff_bytes)
            tif_sha256 = hashlib.sha256(raw_tiff_bytes).hexdigest()
            print(f"       Downloaded GeoTIFF: {len(raw_tiff_bytes)} bytes, SHA256: {tif_sha256[:16]}...")
        except Exception as exc:
            print(f"       [ERROR] Extraction failed: {exc}")
            validation_failures.append({
                "candidate_id": cand_id,
                "stage": "processing_api_download",
                "error": str(exc),
            })
            continue

        # Validate Raster
        try:
            val_results = validate_chip_raster(
                tiff_path=tif_path,
                expected_lat=lat,
                expected_lon=lon,
                expected_epsg=aoi["utm_epsg"],
            )
            print(f"       Validation: PASSED (Shape={val_results['width']}x{val_results['height']}, Bands={val_results['band_count']}, CRS={val_results['crs']})")
        except Exception as val_exc:
            print(f"       [ERROR] Raster validation failed: {val_exc}")
            validation_failures.append({
                "candidate_id": cand_id,
                "stage": "raster_validation",
                "error": str(val_exc),
            })
            continue

        # Previews
        previews = generate_preview_images(tif_path, PREVIEW_DIR, file_prefix)

        # Save Metadata Sidecar
        extraction_info = {
            "processing_api_endpoint": PROCESSING_API_URL,
            "aoi_geometry": aoi["utm_geometry"],
            "aoi_bbox_utm": aoi["utm_bbox"],
            "aoi_bbox_wgs84": aoi["wgs84_bbox"],
            "projected_crs": f"EPSG:{aoi['utm_epsg']}",
            "output_crs": f"EPSG:{aoi['utm_epsg']}",
            "output_width_pixels": CHIP_PIXELS,
            "output_height_pixels": CHIP_PIXELS,
            "output_resolution_meters": PIXEL_RESOLUTION_M,
            "band_order": BAND_ORDER,
            "input_units": "REFLECTANCE",
            "resampling_method": "BILINEAR (native 20m B11/B12 resampled to 10m common grid)",
            "output_dtype": "FLOAT32",
            "extraction_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "file_size_bytes": len(raw_tiff_bytes),
            "sha256_checksum": tif_sha256,
            "previews": {k: str(v) for k, v in previews.items()},
            "band_statistics": val_results["band_statistics"],
        }

        sentinel2_info = {
            "product_id": product_id,
            "platform": scene_eval["platform"],
            "acquisition_datetime_utc": s2_dt_str,
            "temporal_gap_hours": scene_eval["exact_time_gap_hours"],
            "cloud_cover_pct": scene_eval["cloud_cover_pct"],
            "collection": "sentinel-2-l2a",
            "tile_id": cand["tile_id"],
        }

        save_pilot_sidecar_json(
            json_path=json_path,
            candidate_id=cand_id,
            firms_info=firms_rec,
            sentinel2_info=sentinel2_info,
            extraction_info=extraction_info,
        )
        json_sha256 = hashlib.sha256(json_path.read_bytes()).hexdigest()

        extracted_records.append({
            "candidate_id": cand_id,
            "region": firms_rec["region"],
            "coordinates": {"lat": lat, "lon": lon},
            "product_id": product_id,
            "tile_id": cand["tile_id"],
            "s2_datetime_utc": s2_dt_str,
            "cloud_cover_pct": scene_eval["cloud_cover_pct"],
            "temporal_gap_hours": scene_eval["exact_time_gap_hours"],
            "tif_path": str(tif_path),
            "tif_sha256": tif_sha256,
            "json_path": str(json_path),
            "json_sha256": json_sha256,
            "previews": {k: str(v) for k, v in previews.items()},
            "band_statistics": val_results["band_statistics"],
        })

    # 5. Compile Pilot Diversity Audit Summary
    print("\n[Step 3] Compiling pilot diversity and quality audit summary...")
    unique_products = list({r["product_id"] for r in extracted_records})
    unique_tiles = list({r["tile_id"] for r in extracted_records if r["tile_id"]})
    cloud_vals = [r["cloud_cover_pct"] for r in extracted_records]
    gap_vals = [r["temporal_gap_hours"] for r in extracted_records]

    region_counts = {}
    for r in extracted_records:
        reg = r["region"]
        region_counts[reg] = region_counts.get(reg, 0) + 1

    # Aggregate per-band statistics across all extracted chips
    overall_band_stats = {}
    for band_name in BAND_ORDER:
        b_mins = [r["band_statistics"][band_name]["min"] for r in extracted_records]
        b_maxs = [r["band_statistics"][band_name]["max"] for r in extracted_records]
        b_means = [r["band_statistics"][band_name]["mean"] for r in extracted_records]
        b_stds = [r["band_statistics"][band_name]["std"] for r in extracted_records]
        overall_band_stats[band_name] = {
            "min_observed": round(float(np.min(b_mins)), 6),
            "max_observed": round(float(np.max(b_maxs)), 6),
            "mean_of_means": round(float(np.mean(b_means)), 6),
            "mean_std": round(float(np.mean(b_stds)), 6),
        }

    audit_summary = {
        "status": "STAGE_8.6_PILOT_ACQUISITION_SUCCESS",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "pilot_size_target": PILOT_TARGET_COUNT,
        "pilot_size_acquired": len(extracted_records),
        "validation_failure_count": len(validation_failures),
        "total_candidate_evaluations_rejected": len(rejected_records),
        "label_status_policy": "STRICT_UNLABELED (no ground-truth fire classes assigned)",
        "synthetic_data_policy": "STRICT_REAL_ONLY (0 synthetic images used)",
        "diversity_metrics": {
            "unique_sentinel2_products": len(unique_products),
            "unique_tiles": len(unique_tiles),
            "geographic_region_distribution": region_counts,
        },
        "quality_metrics": {
            "cloud_cover_pct": {
                "min": round(float(np.min(cloud_vals)), 4) if cloud_vals else 0.0,
                "max": round(float(np.max(cloud_vals)), 4) if cloud_vals else 0.0,
                "mean": round(float(np.mean(cloud_vals)), 4) if cloud_vals else 0.0,
                "threshold_enforced": MAX_CLOUD_COVER_PCT,
            },
            "temporal_gap_hours": {
                "min": round(float(np.min(gap_vals)), 4) if gap_vals else 0.0,
                "max": round(float(np.max(gap_vals)), 4) if gap_vals else 0.0,
                "mean": round(float(np.mean(gap_vals)), 4) if gap_vals else 0.0,
                "threshold_enforced": MAX_TEMPORAL_GAP_HOURS,
            },
            "raster_format": {
                "dimensions": f"{CHIP_PIXELS}x{CHIP_PIXELS}",
                "bands": len(BAND_ORDER),
                "resolution_meters": PIXEL_RESOLUTION_M,
                "data_type": "float32",
                "units": "REFLECTANCE",
                "resampling": "BILINEAR",
                "band_order": BAND_ORDER,
            },
        },
        "overall_per_band_reflectance": overall_band_stats,
        "extracted_chips": extracted_records,
        "validation_failures": validation_failures,
        "sample_rejected_evaluations": rejected_records[:20],
    }

    with open(AUDIT_SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2)

    summary_sha256 = hashlib.sha256(AUDIT_SUMMARY_PATH.read_bytes()).hexdigest()
    print(f"\n[Step 4] Saved pilot audit summary:")
    print(f"         Path:   {AUDIT_SUMMARY_PATH}")
    print(f"         SHA256: {summary_sha256}")
    print(f"         Acquired: {len(extracted_records)}/{PILOT_TARGET_COUNT} chips")
    print(f"         Validation Failures: {len(validation_failures)}")
    print("=" * 80)

    return audit_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Stage 8.6 Sentinel-2 Pilot Acquisition.")
    args = parser.parse_args()

    try:
        summary = run_pilot_acquisition()
        if summary["pilot_size_acquired"] < PILOT_TARGET_COUNT:
            print(f"[INFO] Completed with {summary['pilot_size_acquired']} chips.")
        return 0
    except Exception as exc:
        print(f"\n[FATAL ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
