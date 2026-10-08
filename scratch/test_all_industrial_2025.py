import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.test_sentinel_catalog import get_cdse_access_token, search_sentinel2_catalog
from scripts.test_cdse_auth import effective_client_id, effective_client_secret

token = get_cdse_access_token(effective_client_id, effective_client_secret)
incidents = json.load(open("data/reference/ds05/industrial_incidents.json", "r", encoding="utf-8"))
print(f"Testing all {len(incidents)} 2025 industrial incidents...")

results = []
total_viable_scenes = 0

for i, inc in enumerate(incidents):
    inc_id = inc["incident_id"]
    lat, lon = inc["latitude"], inc["longitude"]
    start_str = inc["event_start"]
    dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
    t_min = (dt - timedelta(hours=48)).isoformat()
    t_max = (dt + timedelta(hours=48)).isoformat()
    bbox = [lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05]
    
    time.sleep(2.0)  # DEC-U3 rate limiting compliance
    try:
        res = search_sentinel2_catalog(token, bbox, f"{t_min}/{t_max}", limit=10)
        features = res.get("features", [])
        viable_in_inc = []
        for f in features:
            props = f.get("properties", {})
            cc = props.get("eo:cloud_cover")
            s2_dt_str = props.get("datetime")
            dt_s2 = datetime.fromisoformat(s2_dt_str.replace("Z", "+00:00"))
            delta_h = abs((dt_s2 - dt).total_seconds()) / 3600.0
            if cc is not None and cc <= 20.0 and delta_h <= 48.0:
                viable_in_inc.append({
                    "scene_id": f.get("id"),
                    "cloud_cover": cc,
                    "s2_datetime": s2_dt_str,
                    "delta_hours": round(delta_h, 2)
                })
        
        results.append({
            "incident_id": inc_id,
            "facility_name": inc["facility_name"],
            "state": inc.get("state"),
            "event_start": start_str,
            "viable_scenes_count": len(viable_in_inc),
            "scenes": viable_in_inc
        })
        total_viable_scenes += len(viable_in_inc)
        print(f"[{i+1}/{len(incidents)}] {inc_id}: {len(viable_in_inc)} viable scenes (cloud<=20%, dt<=48h)")
    except Exception as e:
        print(f"[{i+1}/{len(incidents)}] {inc_id} ERROR: {e}")

print(f"\nTOTAL VIABLE 2025 INDUSTRIAL SCENES FOUND: {total_viable_scenes}")
with open("scratch/industrial_2025_stac_results.json", "w", encoding="utf-8") as f:
    json.dump({"total_viable_scenes": total_viable_scenes, "results": results}, f, indent=2)
