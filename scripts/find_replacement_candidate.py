"""
Search and identify an optimal replacement candidate for PILOT_04_NORTH.
Must be:
- Region: NORTH (lat >= 27.0)
- Real Sentinel-2 L2A from 2025
- Cloud cover <= 10.0%
- Temporal gap <= 48.0 hours
- Strict AOI interior containment in scene geometry (buffer > 1 km to ensure zero swath edge truncation)
- Not a duplicate of any existing pilot scene
"""

from __future__ import annotations
import datetime as dt_mod
import glob
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
import pandas as pd
import pyarrow.parquet as pq
from shapely.geometry import box, shape

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from scripts.find_valid_sentinel_candidate import evaluate_candidate_scene
from scripts.run_sentinel_pilot_acquisition import (
    compute_aoi_for_point,
    parse_iso_datetime,
)
from scripts.test_sentinel_catalog import (
    get_cdse_access_token,
    get_collection_band_summaries,
    search_sentinel2_catalog,
)

client_id = os.getenv("CDSE_CLIENT_ID")
client_secret = os.getenv("CDSE_CLIENT_SECRET")
token = get_cdse_access_token(client_id, client_secret)
bands_summary = get_collection_band_summaries(token)

table = pq.read_table(
    PROJECT_ROOT / "data" / "interim" / "causal_features_2025.parquet",
    columns=["detection_id", "latitude", "longitude", "acq_datetime_utc", "frp", "partition"],
)
df = table.to_pandas()
df["month"] = df["acq_datetime_utc"].dt.month
# Focus on North India: lat >= 27.0, within central/northern states
north = df[(df["month"] == 3) & (df["latitude"] >= 27.0) & (df["longitude"] >= 75.0) & (df["longitude"] <= 82.0)].copy()
print(f"Total candidate North detections in 75-82E: {len(north)}")

used_products = set()
used_tiles = set()
for f in glob.glob(str(PROJECT_ROOT / "data/reference/ds08/pilot/metadata/*.json")):
    with open(f, "r", encoding="utf-8") as fp:
        meta = json.load(fp)
        used_products.add(meta["sentinel2_scene"]["product_id"])
        used_tiles.add(meta["sentinel2_scene"]["tile_id"])

print(f"Loaded {len(used_products)} already-used products.")

# Sample 50 detections deterministically
sample = north.sample(n=min(50, len(north)), random_state=42)
candidates = []

for idx, (_, row) in enumerate(sample.iterrows()):
    lat = float(row["latitude"])
    lon = float(row["longitude"])
    det_id = str(row["detection_id"])
    det_dt = row["acq_datetime_utc"].strftime("%Y-%m-%dT%H:%M:%SZ")

    aoi = compute_aoi_for_point(lat, lon)
    aoi_box = box(*aoi["wgs84_bbox"])

    target_dt = parse_iso_datetime(det_dt)
    start_dt = target_dt - dt_mod.timedelta(hours=48)
    end_dt = target_dt + dt_mod.timedelta(hours=48)
    dt_range = f"{start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    bbox = [lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05]

    try:
        cat_res = search_sentinel2_catalog(token, bbox=bbox, datetime_range=dt_range, limit=5)
    except Exception as exc:
        continue

    features = cat_res.get("features", [])
    for feat in features:
        pid = feat.get("id")
        if pid in used_products:
            continue
        cld = feat.get("properties", {}).get("eo:cloud_cover", 100.0)
        if cld > 10.0:
            continue

        geom = shape(feat["geometry"])
        # Check that AOI buffered by 0.015 degrees (~1.5 km) is strictly inside scene footprint
        buffered_aoi = aoi_box.buffer(0.015)
        if not geom.contains(buffered_aoi):
            continue

        tile_id = feat.get("properties", {}).get("sentinel:tile_id", "")
        if not tile_id and "_" in pid:
            parts = pid.split("_")
            for p in parts:
                if p.startswith("T") and len(p) == 6:
                    tile_id = p
                    break

        firms_rec = {
            "detection_id": det_id,
            "latitude": lat,
            "longitude": lon,
            "acq_datetime_utc": det_dt,
            "frp": float(row["frp"]),
            "partition": str(row["partition"]),
            "region": "NORTH",
        }

        eval_res = evaluate_candidate_scene(
            firms_record=firms_rec,
            scene_feature=feat,
            collection_bands=bands_summary,
            max_cloud=10.0,
            max_gap_hours=48.0,
            required_bands=["B02", "B03", "B04", "B11", "B12"],
        )

        if eval_res["is_valid"]:
            candidates.append({
                "firms": firms_rec,
                "product_id": pid,
                "tile_id": tile_id,
                "cloud_cover_pct": cld,
                "time_gap_hours": eval_res["exact_time_gap_hours"],
                "scene_datetime_utc": feat.get("properties", {}).get("datetime"),
                "aoi": aoi,
            })
            print(f"Candidate #{len(candidates)}: {pid} (Tile: {tile_id})")
            print(f"  FIRMS: Lat={lat:.5f}, Lon={lon:.5f}, FRP={row['frp']:.2f}, UTC={det_dt}")
            print(f"  Scene: Cloud={cld:.2f}%, Gap={eval_res['exact_time_gap_hours']:.2f}h, UTC={feat.get('properties', {}).get('datetime')}")
            break

    if len(candidates) >= 5:
        break

print(f"\nDiscovered {len(candidates)} high-quality replacement candidates.")
with open(PROJECT_ROOT / "scratch_replacement_candidates.json", "w", encoding="utf-8") as out_f:
    json.dump(candidates, out_f, indent=2)
print("Saved candidates to scratch_replacement_candidates.json")
