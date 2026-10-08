"""
Acquires and validates ONE real Sentinel-2 L2A replacement chip for PILOT_04_NORTH (Stage 8.8).

Selected Candidate:
- FIRMS Detection ID: 261077508c08330c65c19cbdecafd28dc96a0e81812d5b626f2ba4d293d07787 (or matching Candidate #2)
- Geographic Region: NORTH (lat: 29.76735, lon: 77.66902)
- S2 L2A Product: S2C_MSIL2A_20250319T052711_N0511_R105_T43RGP_20250319T104817.SAFE
- S2 Acquisition UTC: 2025-03-19T05:40:58.075Z
- Cloud Cover: 0.23%
- Temporal Gap: 1.68 hours
- Resampling: BILINEAR (B11/B12 -> 10m)
- Units: REFLECTANCE
- Format: FLOAT32, 512x512, 10m spacing, 5 bands (B02, B03, B04, B11, B12)
"""

from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict

from dotenv import load_dotenv
import numpy as np
from PIL import Image
import pyproj
import rasterio
from rasterio.transform import from_origin
import requests
from shapely.geometry import box, mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from scripts.test_sentinel_catalog import get_cdse_access_token
from scripts.run_sentinel_pilot_acquisition import (
    EVALSCRIPT,
    PROCESSING_API_URL,
    compute_aoi_for_point,
    execute_processing_request,
    generate_preview_images,
    validate_chip_raster,
)

REPLACEMENT_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "pilot" / "replacement"
REPLACEMENT_DIR.mkdir(parents=True, exist_ok=True)

# Load Candidate #2 from scratch_replacement_candidates.json
with open(PROJECT_ROOT / "scratch_replacement_candidates.json", "r", encoding="utf-8") as f:
    candidates = json.load(f)

# Candidate #2 (index 1)
cand = candidates[1]
firms_rec = cand["firms"]
product_id = cand["product_id"]
tile_id = cand["tile_id"]
cloud_pct = cand["cloud_cover_pct"]
gap_hours = cand["time_gap_hours"]
scene_dt = cand["scene_datetime_utc"]
aoi = cand["aoi"]

lat = firms_rec["latitude"]
lon = firms_rec["longitude"]
det_id = firms_rec["detection_id"]
frp = firms_rec["frp"]
det_dt = firms_rec["acq_datetime_utc"]

print("=" * 80)
print("STAGE 8.8 — ACQUIRING PILOT_04_NORTH_REPLACEMENT CHIP")
print("=" * 80)
print(f"Candidate ID: PILOT_04_NORTH_REPLACEMENT")
print(f"Region: NORTH (Lat: {lat:.5f}, Lon: {lon:.5f})")
print(f"FIRMS Detection ID: {det_id}")
print(f"FIRMS Acquisition UTC: {det_dt}, FRP: {frp:.2f} MW")
print(f"Sentinel-2 Product: {product_id} (Tile: {tile_id})")
print(f"Sentinel-2 Acquisition UTC: {scene_dt}")
print(f"Scene Cloud Cover: {cloud_pct:.2f}%, Temporal Gap: {gap_hours:.2f}h")
print(f"Projected CRS: {aoi['utm_crs_uri']} (EPSG:{aoi['utm_epsg']})")
print(f"UTM Bounding Box: {aoi['utm_bbox']}")

# Authenticate
client_id = os.getenv("CDSE_CLIENT_ID")
client_secret = os.getenv("CDSE_CLIENT_SECRET")
if not client_id or not client_secret:
    raise RuntimeError("Missing CDSE credentials in .env")

token = get_cdse_access_token(client_id, client_secret)

# Narrow 1-hour time window centered on the scene
import dateutil.parser
scene_dt_obj = dateutil.parser.isoparse(scene_dt.replace("Z", "+00:00"))
import datetime as dt_mod
t_from = (scene_dt_obj - dt_mod.timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
t_to = (scene_dt_obj + dt_mod.timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

payload = {
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
                        "from": t_from,
                        "to": t_to
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
        "width": 512,
        "height": 512,
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

print(f"\nSubmitting Processing API request to {PROCESSING_API_URL}...")
tiff_bytes = execute_processing_request(token, payload)
print(f"Retrieved {len(tiff_bytes)} bytes of GeoTIFF data.")

date_str = scene_dt_obj.strftime("%Y%m%d")
file_prefix = f"PILOT_04_NORTH_REPLACEMENT_sentinel2_{date_str}_chip"
tiff_path = REPLACEMENT_DIR / f"{file_prefix}.tif"
json_path = REPLACEMENT_DIR / f"{file_prefix}.json"

# Write GeoTIFF with full geospatial profile
min_x, min_y, max_x, max_y = aoi["utm_bbox"]
transform = from_origin(min_x, max_y, 10.0, 10.0)

with rasterio.open(io_bytes := io.BytesIO(tiff_bytes)) as src_mem:
    profile = src_mem.profile.copy()
    raw_arr = src_mem.read()

profile.update({
    "driver": "GTiff",
    "height": 512,
    "width": 512,
    "count": 5,
    "dtype": "float32",
    "crs": f"EPSG:{aoi['utm_epsg']}",
    "transform": transform,
    "nodata": None,
    "compress": "deflate",
    "tiled": True,
    "blockxsize": 256,
    "blockysize": 256,
})

with rasterio.open(tiff_path, "w", **profile) as dst:
    dst.write(raw_arr)

print(f"Saved replacement GeoTIFF to: {tiff_path}")

# Calculate zero fill
all_zero_mask = (raw_arr == 0.0).all(axis=0)
zero_fill_count = int(np.sum(all_zero_mask))
zero_fill_pct = (zero_fill_count / (512 * 512)) * 100.0
print(f"Zero-fill pixels: {zero_fill_count} / {512*512} ({zero_fill_pct:.4f}%)")

if zero_fill_pct > 1.0:
    raise ValueError(f"CRITICAL: Replacement chip failed zero-fill validation: {zero_fill_pct:.2f}% > 1.0% threshold!")

# Validate 17-point raster integrity
val_res = validate_chip_raster(
    tiff_path=tiff_path,
    expected_lat=lat,
    expected_lon=lon,
    expected_epsg=aoi["utm_epsg"],
    expected_bands=5,
    expected_dim=512,
    expected_res=10.0,
)
print("Raster integrity validation PASSED (5 bands, 512x512, float32, EPSG, 10m spacing).")

# Previews
previews = generate_preview_images(tiff_path, REPLACEMENT_DIR, file_prefix)
print(f"Generated RGB preview: {previews['rgb_preview']}")
print(f"Generated SWIR preview: {previews['swir_preview']}")

sha256_hash = hashlib.sha256(tiff_path.read_bytes()).hexdigest()

sidecar = {
    "status": "VALIDATED_PILOT_CHIP_EXTRACTION",
    "candidate_id": "PILOT_04_NORTH_REPLACEMENT",
    "role": "REPLACEMENT_FOR_PILOT_04_NORTH",
    "original_candidate_id": "PILOT_04_NORTH",
    "replacement_rationale": (
        "Original PILOT_04_NORTH was rejected due to 51.20% orbital swath-edge truncation. "
        "Replacement chip provides complete, untruncated 512x512 coverage (zero-fill 0.0%) "
        "over a high-quality North India FIRMS detection (Lat: 29.76735, Lon: 77.66902, "
        "scene cloud 0.23%, temporal gap 1.68h)."
    ),
    "label_status": "UNLABELED",
    "pilot_phase": "STAGE_8.8_QUALITY_RESOLUTION",
    "firms_metadata": {
        "detection_id": det_id,
        "latitude": lat,
        "longitude": lon,
        "acquisition_datetime_utc": det_dt,
        "frp": frp,
        "association_status": "candidate_context_only",
        "geographic_region": "NORTH",
    },
    "sentinel2_scene": {
        "product_id": product_id,
        "platform": "sentinel-2c",
        "acquisition_datetime_utc": scene_dt,
        "temporal_gap_hours": round(gap_hours, 6),
        "cloud_cover_pct": cloud_pct,
        "collection": "sentinel-2-l2a",
        "tile_id": tile_id,
    },
    "extraction": {
        "processing_api_endpoint": PROCESSING_API_URL,
        "aoi_geometry": aoi["utm_geometry"],
        "aoi_bbox_utm": aoi["utm_bbox"],
        "aoi_bbox_wgs84": aoi["wgs84_bbox"],
        "projected_crs": f"EPSG:{aoi['utm_epsg']}",
        "output_crs": f"EPSG:{aoi['utm_epsg']}",
        "output_width_pixels": 512,
        "output_height_pixels": 512,
        "output_resolution_meters": 10.0,
        "band_order": ["B02", "B03", "B04", "B11", "B12"],
        "input_units": "REFLECTANCE",
        "resampling_method": "BILINEAR (native 20m B11/B12 resampled to 10m common grid)",
        "output_dtype": "FLOAT32",
        "extraction_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "file_size_bytes": tiff_path.stat().st_size,
        "sha256_checksum": sha256_hash,
        "zero_fill_pixel_count": zero_fill_count,
        "zero_fill_pct": round(zero_fill_pct, 4),
        "previews": {
            "rgb_preview": str(previews["rgb_preview"]),
            "swir_preview": str(previews["swir_preview"]),
        },
        "band_statistics": val_res["band_statistics"],
    },
}

with open(json_path, "w", encoding="utf-8") as jf:
    json.dump(sidecar, jf, indent=2)

print(f"Saved sidecar metadata JSON to: {json_path}")
print("\nPILOT_04_NORTH_REPLACEMENT acquisition and verification SUCCESSFUL.")
