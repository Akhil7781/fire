import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.test_sentinel_catalog import get_cdse_access_token, search_sentinel2_catalog
from scripts.test_cdse_auth import effective_client_id, effective_client_secret

token = get_cdse_access_token(effective_client_id, effective_client_secret)
incidents = json.load(open("data/reference/ds05/industrial_incidents.json", "r", encoding="utf-8"))
print(f"Testing CDSE STAC query for first 3 incidents...")

for inc in incidents[:3]:
    lat, lon = inc["latitude"], inc["longitude"]
    start_str = inc["event_start"]
    dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
    t_min = (dt - timedelta(hours=48)).isoformat()
    t_max = (dt + timedelta(hours=48)).isoformat()
    bbox = [lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05]
    res = search_sentinel2_catalog(token, bbox, f"{t_min}/{t_max}", limit=5)
    features = res.get("features", [])
    print(f"{inc['incident_id']}: found {len(features)} S2 L2A scenes in 48h")
    for f in features:
        props = f.get("properties", {})
        cc = props.get("eo:cloud_cover")
        dt_s2 = props.get("datetime")
        print(f"   scene={f.get('id')} dt={dt_s2} cloud={cc}%")
