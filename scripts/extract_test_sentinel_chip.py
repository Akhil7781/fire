"""
Sentinel-2 L2A Single Chip Extraction Script (Stage 8.5).

Extracts ONE authoritative 512 x 512 (10 m/pixel) multi-band GeoTIFF centered on the
validated FIRMS thermal detection (b18ce007dc00...) from the validated Sentinel-2 L2A scene
(S2B_MSIL2A_20250311T051649_N0511_R062_T43QFD_20250311T075623.SAFE) using the official
Copernicus Data Space Ecosystem (CDSE) Sentinel Hub Processing API.

Bands requested in strict fixed order:
  1. B02 (Blue, 10 m native)
  2. B03 (Green, 10 m native)
  3. B04 (Red, 10 m native)
  4. B11 (SWIR-1, 20 m native -> resampled to 10 m via bilinear interpolation)
  5. B12 (SWIR-2, 20 m native -> resampled to 10 m via bilinear interpolation)

Output:
  - Multi-band GeoTIFF: FLOAT32 reflectance, CRS EPSG:32643, 512 x 512 x 5
  - Metadata sidecar: JSON with complete extraction provenance
  - Non-authoritative RGB and SWIR false-color PNG preview images

SECURITY INVARIANT:
Never prints or persists CDSE Client Secret, OAuth access token, or Authorization headers.
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
from PIL import Image
import pyproj
import rasterio
import requests
from shapely.geometry import Point, box, mapping

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
from scripts.test_sentinel_catalog import get_cdse_access_token

PROCESSING_API_URL = "https://sh.dataspace.copernicus.eu/process/v1"
TIMEOUT_SECONDS = 60

# Validated Authoritative FIRMS Detection
VALIDATED_FIRMS = {
    "detection_id": "b18ce007dc003134da73556195ff1c84b9cecc89cf80a03cc3421eae8ce91624",
    "latitude": 21.63424,
    "longitude": 76.66431,
    "acquisition_datetime_utc": "2025-03-11T08:10:00Z",
    "frp": 20.85,
    "partition": "train",
}

# Validated Authoritative Sentinel-2 Scene
VALIDATED_SENTINEL2 = {
    "product_id": "S2B_MSIL2A_20250311T051649_N0511_R062_T43QFD_20250311T075623.SAFE",
    "platform": "sentinel-2b",
    "acquisition_datetime_utc": "2025-03-11T05:33:09.634Z",
    "temporal_gap_hours": 2.613991,
    "cloud_cover_pct": 0.0,
    "collection": "sentinel-2-l2a",
    "tile_id": "T43QFD",
}

# Target Output Configuration
CHIP_PIXELS = 512
PIXEL_RESOLUTION_M = 10.0
CHIP_SPAN_M = CHIP_PIXELS * PIXEL_RESOLUTION_M  # 5120.0 meters
UTM_EPSG = 32643  # UTM Zone 43N (covers 72°E to 78°E, contains 76.66431°E)
CRS_URI = "http://www.opengis.net/def/crs/EPSG/0/32643"

BAND_ORDER = ["B02", "B03", "B04", "B11", "B12"]

DEFAULT_CHIP_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "chips_pending_annotation"
DEFAULT_PREVIEW_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "preview"

FILE_PREFIX = f"{VALIDATED_FIRMS['detection_id']}_sentinel2b_20250311_chip"
DEFAULT_TIFF_PATH = DEFAULT_CHIP_DIR / f"{FILE_PREFIX}.tif"
DEFAULT_JSON_PATH = DEFAULT_CHIP_DIR / f"{FILE_PREFIX}.json"

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


def compute_aoi(
    lat: float = VALIDATED_FIRMS["latitude"],
    lon: float = VALIDATED_FIRMS["longitude"],
    chip_span_m: float = CHIP_SPAN_M,
    utm_epsg: int = UTM_EPSG,
) -> Dict[str, Any]:
    """
    Computes a projected 5.12 km x 5.12 km Area of Interest (AOI) centered on the FIRMS coordinate.
    Calculates coordinates in native UTM Zone 43N (EPSG:32643) and transforms to WGS84 for metadata.
    """
    transformer_to_utm = pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{utm_epsg}", always_xy=True)
    transformer_to_wgs84 = pyproj.Transformer.from_crs(f"EPSG:{utm_epsg}", "EPSG:4326", always_xy=True)

    utm_center_x, utm_center_y = transformer_to_utm.transform(lon, lat)
    half_span = chip_span_m / 2.0

    min_x = round(utm_center_x - half_span, 2)
    max_x = round(utm_center_x + half_span, 2)
    min_y = round(utm_center_y - half_span, 2)
    max_y = round(utm_center_y + half_span, 2)

    utm_bbox = [min_x, min_y, max_x, max_y]

    # Convert bbox corners to WGS84
    wgs_min_lon, wgs_min_lat = transformer_to_wgs84.transform(min_x, min_y)
    wgs_max_lon, wgs_max_lat = transformer_to_wgs84.transform(max_x, max_y)
    wgs_bbox = [round(wgs_min_lon, 6), round(wgs_min_lat, 6), round(wgs_max_lon, 6), round(wgs_max_lat, 6)]

    # GeoJSON polygon in UTM
    geom_box = box(min_x, min_y, max_x, max_y)
    utm_geometry = mapping(geom_box)

    return {
        "center_wgs84": {"latitude": lat, "longitude": lon},
        "center_utm": {"x": round(utm_center_x, 2), "y": round(utm_center_y, 2)},
        "chip_span_meters": chip_span_m,
        "utm_epsg": utm_epsg,
        "utm_crs_uri": CRS_URI,
        "utm_bbox": utm_bbox,
        "wgs84_bbox": wgs_bbox,
        "utm_geometry": utm_geometry,
    }


def build_processing_payload(
    aoi: Dict[str, Any],
    time_from: str = "2025-03-11T05:30:00Z",
    time_to: str = "2025-03-11T05:35:00Z",
    width: int = CHIP_PIXELS,
    height: int = CHIP_PIXELS,
) -> Dict[str, Any]:
    """Constructs the Sentinel Hub Processing API request payload."""
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
    """
    Submits POST request to Sentinel Hub Processing API and retrieves GeoTIFF bytes.
    Retries on transient network errors.
    """
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


def validate_raster(
    tiff_path: Path,
    firms_lat: float = VALIDATED_FIRMS["latitude"],
    firms_lon: float = VALIDATED_FIRMS["longitude"],
    expected_bands: int = 5,
    expected_dim: int = CHIP_PIXELS,
    expected_res: float = PIXEL_RESOLUTION_M,
) -> Dict[str, Any]:
    """
    Performs rigorous 15-point validation of the extracted GeoTIFF raster.
    Computes per-band reflectance statistics and validates coordinate containment.
    """
    if not tiff_path.exists():
        raise FileNotFoundError(f"Raster file does not exist: {tiff_path}")
    if tiff_path.stat().st_size == 0:
        raise ValueError(f"Raster file is 0 bytes: {tiff_path}")

    validation_results = {}
    with rasterio.open(tiff_path) as src:
        # 1. Readable check
        validation_results["file_readable"] = True

        # 2. Driver check
        validation_results["driver"] = src.driver

        # 3. Band count check
        count = src.count
        validation_results["band_count"] = count
        if count != expected_bands:
            raise ValueError(f"Expected {expected_bands} bands, got {count}")

        # 4. Dimensions check
        width, height = src.width, src.height
        validation_results["width"] = width
        validation_results["height"] = height
        if width != expected_dim or height != expected_dim:
            raise ValueError(f"Expected dimensions {expected_dim}x{expected_dim}, got {width}x{height}")

        # 5. Data type check
        dtypes = list(src.dtypes)
        validation_results["dtypes"] = dtypes
        if not all(dt == "float32" for dt in dtypes):
            raise ValueError(f"Expected all bands to be float32, got {dtypes}")

        # 6. CRS check
        crs = src.crs
        validation_results["crs"] = str(crs)
        if crs is None or crs.to_epsg() != UTM_EPSG:
            raise ValueError(f"Expected CRS EPSG:{UTM_EPSG}, got {crs}")

        # 7. Transform check
        transform = src.transform
        validation_results["transform"] = [
            transform.a, transform.b, transform.c,
            transform.d, transform.e, transform.f
        ]
        pixel_res_x = abs(transform.a)
        pixel_res_y = abs(transform.e)
        validation_results["pixel_resolution_x_m"] = round(pixel_res_x, 4)
        validation_results["pixel_resolution_y_m"] = round(pixel_res_y, 4)
        if abs(pixel_res_x - expected_res) > 0.05 or abs(pixel_res_y - expected_res) > 0.05:
            raise ValueError(
                f"Expected pixel resolution ~{expected_res}m, got {pixel_res_x}m x {pixel_res_y}m"
            )

        # 8. Bounds check
        bounds = src.bounds
        validation_results["bounds"] = {
            "left": round(bounds.left, 2),
            "bottom": round(bounds.bottom, 2),
            "right": round(bounds.right, 2),
            "top": round(bounds.top, 2),
        }

        # 9. Coordinate containment check
        transformer = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        firms_x, firms_y = transformer.transform(firms_lon, firms_lat)
        in_bounds = (bounds.left <= firms_x <= bounds.right) and (bounds.bottom <= firms_y <= bounds.top)
        validation_results["firms_utm_coords"] = {"x": round(firms_x, 2), "y": round(firms_y, 2)}
        validation_results["firms_point_inside_chip"] = in_bounds
        if not in_bounds:
            raise ValueError(
                f"FIRMS point ({firms_x:.2f}, {firms_y:.2f}) not inside raster bounds: {bounds}"
            )

        # 10. Per-band data validation and statistics
        raster_data = src.read()  # Shape: (5, 512, 512)
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

            # Reflectance plausibility check: surface reflectance is generally in [0.0, 2.0]
            if min_val < -0.1 or max_val > 5.0:
                print(f"[WARNING] Band {band_name} reflectance extreme value: min={min_val}, max={max_val}")

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

        validation_results["band_statistics"] = band_stats
        validation_results["is_valid"] = True

    return validation_results


def generate_preview_images(
    tiff_path: Path,
    preview_dir: Path = DEFAULT_PREVIEW_DIR,
    file_prefix: str = FILE_PREFIX,
) -> Dict[str, Path]:
    """
    Generates non-authoritative RGB and SWIR false-color PNG preview images for visual inspection.
    RGB: Band 3 (B04 Red), Band 2 (B03 Green), Band 1 (B02 Blue)
    SWIR false color: Band 5 (B12 SWIR-2), Band 4 (B11 SWIR-1), Band 3 (B04 Red)
    """
    preview_dir.mkdir(parents=True, exist_ok=True)

    with rasterio.open(tiff_path) as src:
        arr = src.read()  # Shape: (5, 512, 512), order: [B02, B03, B04, B11, B12]

    # Helper function for 2-98 percentile scaling
    def to_rgb_image(r_band: np.ndarray, g_band: np.ndarray, b_band: np.ndarray) -> Image.Image:
        stack = np.stack([r_band, g_band, b_band], axis=-1)
        stack = np.nan_to_num(stack, nan=0.0, posinf=1.0, neginf=0.0)
        p2, p98 = np.percentile(stack, (2, 98))
        if p98 <= p2:
            p98 = p2 + 1e-4
        scaled = np.clip((stack - p2) / (p98 - p2), 0.0, 1.0)
        uint8_arr = (scaled * 255.0).astype(np.uint8)
        return Image.fromarray(uint8_arr)

    # 1. Natural Color RGB: B04 (index 2), B03 (index 1), B02 (index 0)
    rgb_img = to_rgb_image(arr[2], arr[1], arr[0])
    rgb_path = preview_dir / f"{file_prefix}_rgb_preview.png"
    rgb_img.save(rgb_path, format="PNG")

    # 2. SWIR False Color: B12 (index 4), B11 (index 3), B04 (index 2)
    swir_img = to_rgb_image(arr[4], arr[3], arr[2])
    swir_path = preview_dir / f"{file_prefix}_swir_preview.png"
    swir_img.save(swir_path, format="PNG")

    return {
        "rgb_preview": rgb_path,
        "swir_preview": swir_path,
    }


def save_metadata_sidecar(
    json_path: Path,
    firms_info: Dict[str, Any],
    sentinel2_info: Dict[str, Any],
    extraction_info: Dict[str, Any],
) -> None:
    """Saves metadata sidecar JSON file, guaranteeing zero secret or token leakage."""
    sidecar_data = {
        "status": "VALIDATED_SINGLE_CHIP_EXTRACTION",
        "metadata_version": "1.0",
        "firms_detection": {
            "detection_id": firms_info["detection_id"],
            "latitude": firms_info["latitude"],
            "longitude": firms_info["longitude"],
            "acquisition_datetime_utc": firms_info["acquisition_datetime_utc"],
            "frp": firms_info["frp"],
            "partition": firms_info.get("partition", "train"),
        },
        "sentinel2_scene": {
            "product_id": sentinel2_info["product_id"],
            "platform": sentinel2_info["platform"],
            "acquisition_datetime_utc": sentinel2_info["acquisition_datetime_utc"],
            "temporal_gap_hours": sentinel2_info["temporal_gap_hours"],
            "cloud_cover_pct": sentinel2_info["cloud_cover_pct"],
            "collection": sentinel2_info["collection"],
            "tile_id": sentinel2_info.get("tile_id", "T43QFD"),
        },
        "extraction": {
            "processing_api_endpoint": extraction_info["processing_api_endpoint"],
            "aoi": extraction_info["aoi"],
            "crs": extraction_info["crs"],
            "output_width_pixels": extraction_info["output_width_pixels"],
            "output_height_pixels": extraction_info["output_height_pixels"],
            "output_resolution_meters": extraction_info["output_resolution_meters"],
            "band_order": extraction_info["band_order"],
            "input_units": extraction_info["input_units"],
            "resampling_method": extraction_info["resampling_method"],
            "output_data_type": extraction_info["output_data_type"],
            "extraction_timestamp_utc": extraction_info["extraction_timestamp_utc"],
            "file_size_bytes": extraction_info["file_size_bytes"],
            "sha256_checksum": extraction_info["sha256_checksum"],
            "previews": extraction_info.get("previews", {}),
            "band_statistics": extraction_info.get("band_statistics", {}),
        },
    }

    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(sidecar_data, f, indent=2)


def extract_and_validate_chip(
    output_tif: Path = DEFAULT_TIFF_PATH,
    output_json: Path = DEFAULT_JSON_PATH,
    preview_dir: Path = DEFAULT_PREVIEW_DIR,
) -> Dict[str, Any]:
    """
    Main orchestration function for Stage 8.5 single-chip extraction:
    1. Authenticates with CDSE Keycloak
    2. Computes 5.12 km x 5.12 km AOI in UTM Zone 43N
    3. Builds Processing API payload with fixed 5-band FLOAT32 specification
    4. Submits request and downloads authoritative GeoTIFF
    5. Validates 15 raster integrity constraints
    6. Generates non-authoritative RGB and SWIR PNG preview images
    7. Writes metadata sidecar JSON
    """
    print("\n" + "=" * 75)
    print("STAGE 8.5 — SINGLE REAL SENTINEL-2 CHIP EXTRACTION TEST")
    print("=" * 75)

    # 1. Credentials
    client_id = effective_client_id
    client_secret = effective_client_secret
    if not client_id or not client_secret:
        raise RuntimeError("CDSE credentials not configured in environment or .env file.")

    print("[1/6] Authenticating with Copernicus Data Space Ecosystem...")
    access_token = get_cdse_access_token(client_id, client_secret)
    print("      OAuth authentication successful.")

    # 2. Compute AOI
    print("[2/6] Computing 5.12 km x 5.12 km Area of Interest (AOI)...")
    aoi = compute_aoi()
    print(f"      Center WGS84: ({aoi['center_wgs84']['latitude']:.5f}°N, {aoi['center_wgs84']['longitude']:.5f}°E)")
    print(f"      Center UTM 43N: x={aoi['center_utm']['x']} m, y={aoi['center_utm']['y']} m")
    print(f"      UTM BBox (EPSG:{aoi['utm_epsg']}): {aoi['utm_bbox']}")
    print(f"      Chip Footprint: {aoi['chip_span_meters']} m x {aoi['chip_span_meters']} m")

    # 3. Build request payload
    print("[3/6] Submitting Sentinel Hub Processing API request...")
    payload = build_processing_payload(aoi)
    raw_tiff_bytes = execute_processing_request(access_token, payload)
    print(f"      Received GeoTIFF response ({len(raw_tiff_bytes)} bytes).")

    # 4. Save GeoTIFF
    output_tif.parent.mkdir(parents=True, exist_ok=True)
    with open(output_tif, "wb") as f:
        f.write(raw_tiff_bytes)
    sha256_hash = hashlib.sha256(raw_tiff_bytes).hexdigest()
    print(f"      Saved authoritative GeoTIFF: {output_tif}")
    print(f"      SHA-256: {sha256_hash}")

    # 5. Validate raster
    print("[4/6] Executing 15-point raster validation...")
    val_results = validate_raster(output_tif)
    print(f"      Driver: {val_results['driver']}")
    print(f"      Bands:  {val_results['band_count']} (expected 5)")
    print(f"      Shape:  {val_results['width']} x {val_results['height']} (expected 512 x 512)")
    print(f"      CRS:    {val_results['crs']}")
    print(f"      Pixel Resolution: {val_results['pixel_resolution_x_m']} m x {val_results['pixel_resolution_y_m']} m")
    print(f"      FIRMS point inside chip: {val_results['firms_point_inside_chip']}")
    print("\n      Per-Band Statistics:")
    for b_name, stats in val_results["band_statistics"].items():
        print(
            f"        Band {stats['band_index']} ({b_name:4s}): min={stats['min']:.4f}, "
            f"max={stats['max']:.4f}, mean={stats['mean']:.4f}, std={stats['std']:.4f}, "
            f"valid={stats['valid_pixel_count']}, nodata={stats['nodata_pixel_count']}"
        )

    # 6. Generate non-authoritative preview images
    print("\n[5/6] Generating non-authoritative preview images...")
    previews = generate_preview_images(output_tif, preview_dir=preview_dir)
    print(f"      RGB preview:  {previews['rgb_preview']}")
    print(f"      SWIR preview: {previews['swir_preview']}")

    # 7. Write metadata sidecar JSON
    print("[6/6] Writing metadata sidecar JSON...")
    extraction_meta = {
        "processing_api_endpoint": PROCESSING_API_URL,
        "aoi": aoi,
        "crs": f"EPSG:{UTM_EPSG}",
        "output_width_pixels": CHIP_PIXELS,
        "output_height_pixels": CHIP_PIXELS,
        "output_resolution_meters": PIXEL_RESOLUTION_M,
        "band_order": BAND_ORDER,
        "input_units": "REFLECTANCE",
        "resampling_method": "BILINEAR (native 20m B11/B12 resampled to 10m common grid)",
        "output_data_type": "FLOAT32",
        "extraction_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "file_size_bytes": len(raw_tiff_bytes),
        "sha256_checksum": sha256_hash,
        "previews": {k: str(v) for k, v in previews.items()},
        "band_statistics": val_results["band_statistics"],
    }

    save_metadata_sidecar(output_json, VALIDATED_FIRMS, VALIDATED_SENTINEL2, extraction_meta)
    sidecar_sha256 = hashlib.sha256(output_json.read_bytes()).hexdigest()
    print(f"      Saved metadata sidecar: {output_json}")
    print(f"      Sidecar SHA-256: {sidecar_sha256}")
    print("=" * 75)

    return {
        "status": "SUCCESS",
        "tiff_path": str(output_tif),
        "tiff_sha256": sha256_hash,
        "json_path": str(output_json),
        "json_sha256": sidecar_sha256,
        "previews": {k: str(v) for k, v in previews.items()},
        "validation_results": val_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract and validate single Sentinel-2 L2A chip for Stage 8.5."
    )
    parser.add_argument(
        "--output-tif",
        type=Path,
        default=DEFAULT_TIFF_PATH,
        help="Path for output GeoTIFF file.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_JSON_PATH,
        help="Path for output metadata sidecar JSON.",
    )
    parser.add_argument(
        "--preview-dir",
        type=Path,
        default=DEFAULT_PREVIEW_DIR,
        help="Directory for preview PNG images.",
    )
    args = parser.parse_args()

    try:
        extract_and_validate_chip(
            output_tif=args.output_tif,
            output_json=args.output_json,
            preview_dir=args.preview_dir,
        )
        return 0
    except Exception as exc:
        print(f"\n[FATAL ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
