import json
import math
from pathlib import Path
from collections import defaultdict, Counter
import dateutil.parser

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def classify_indian_region_v2(lat: float, lon: float) -> str:
    if lon >= 84.0:
        return "EAST"
    if lat < 16.0:
        return "SOUTH"
    if lat >= 28.0:
        return "NORTH"
    if lon < 76.0:
        return "WEST"
    return "CENTRAL"

# Load Pilot manifest
pilot_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "packages" / "ds08_pilot_v1" / "manifest.json"
with open(pilot_path, "r", encoding="utf-8") as f:
    pilot_data = json.load(f)

pilot_chips = pilot_data["chips"]
print(f"Loaded {len(pilot_chips)} pilot chips.")

# Load verified industrial STAC results for 2025 and 2024
ind_2025 = json.load(open("scratch/industrial_2025_verified_stac.json", "r", encoding="utf-8"))["results"]
ind_2024 = json.load(open("scratch/industrial_2024_verified_stac.json", "r", encoding="utf-8"))["results"]

viable_2025 = [x for x in ind_2025 if x["viable_scenes_count"] > 0]
viable_2024 = [x for x in ind_2024 if x["viable_scenes_count"] > 0]

print(f"Viable unique industrial incidents: 2025={len(viable_2025)}, 2024={len(viable_2024)}")
for x in viable_2025:
    print(f"  2025: {x['incident_id']} -> {x['scenes'][0]['scene_id']}")
for x in viable_2024:
    print(f"  2024: {x['incident_id']} -> {x['scenes'][0]['scene_id']}")
