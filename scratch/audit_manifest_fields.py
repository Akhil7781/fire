import json
from collections import Counter
import re
import dateutil.parser

p = "data/reference/ds08/manifests/stage8_19/ds08_expansion_candidates_v1.json"
with open(p, "r", encoding="utf-8") as f:
    d = json.load(f)
records = d["records"]

print(f"Auditing all {len(records)} records in ds08_expansion_candidates_v1.json...\n")

# 1. Required fields check
required_fields = [
    "chip_id", "stratum_id", "stratum_name", "target_class", "class_id",
    "primary_sampling_unit", "incident_id", "facility_or_location_name", "state",
    "latitude", "longitude", "geographic_region", "event_year", "s2_acquisition_year",
    "stac_scene_id", "sensing_time_utc", "cloud_cover_pct", "mgrs_tile",
    "temporal_phase", "delta_time_hours", "temporal_matching_tier",
    "corroboration_source", "is_primary_chip", "spatial_group_id", "assigned_fold",
    "annotation_status", "image_status"
]

missing_field_errors = []
for r in records:
    for fld in required_fields:
        if fld not in r:
            missing_field_errors.append((r["chip_id"], fld, "MISSING_KEY"))
        elif r[fld] is None and fld not in ["incident_id"]:
            missing_field_errors.append((r["chip_id"], fld, "NULL_VALUE"))

print(f"1. Missing Fields Check: {len(missing_field_errors)} errors")

# 2. Coordinates validity check
coord_errors = []
for r in records:
    lat, lon = r["latitude"], r["longitude"]
    if not (6.0 <= lat <= 38.0 and 68.0 <= lon <= 98.0):
        coord_errors.append((r["chip_id"], lat, lon, "OUT_OF_BOUNDS"))
print(f"2. Coordinate Validity Check (India Bounds [6-38 N, 68-98 E]): {len(coord_errors)} errors")

# 3. Product ID format check
# Sentinel-2 format: S2[A/B/C]_MSIL2A_<sensing_time>_N<baseline>_R<orbit>_T<tile>_<gen_time>.SAFE
prod_errors = []
s2_regex = re.compile(r"^S2[ABC]_MSIL2A_\d{8}T\d{6}_N\d{4}_R\d{3}_T[0-9A-Z]{5}_\d{8}T\d{6}\.SAFE$")
for r in records:
    pid = r["stac_scene_id"]
    if not s2_regex.match(pid):
        prod_errors.append((r["chip_id"], pid, "INVALID_FORMAT"))
print(f"3. Sentinel-2 L2A Product ID Format Check: {len(prod_errors)} errors")

# 4. Acquisition time validity
time_errors = []
for r in records:
    ts = r["sensing_time_utc"]
    try:
        dt = dateutil.parser.isoparse(ts.replace("Z", "+00:00"))
        if dt.year not in (2024, 2025):
            time_errors.append((r["chip_id"], ts, f"UNEXPECTED_YEAR_{dt.year}"))
    except Exception as e:
        time_errors.append((r["chip_id"], ts, str(e)))
print(f"4. Sensing Time ISO 8601 Validity Check: {len(time_errors)} errors")

# 5. Cloud cover metadata
cloud_errors = []
for r in records:
    cc = r["cloud_cover_pct"]
    if not isinstance(cc, (int, float)) or not (0.0 <= cc <= 100.0):
        cloud_errors.append((r["chip_id"], cc, "INVALID_CLOUD_VALUE"))
    elif r["stratum_id"] in ["STR-5", "STR-6"] and cc > 10.0:
        cloud_errors.append((r["chip_id"], cc, "NEGATIVE_CLOUD_EXCEEDED"))
    elif cc > 20.0:
        cloud_errors.append((r["chip_id"], cc, "CLOUD_EXCEEDS_20_PCT"))
print(f"5. Cloud Cover Metadata Check: {len(cloud_errors)} errors")

# 6. Event-to-Scene Temporal Gap Check
gap_errors = []
for r in records:
    gap = r["delta_time_hours"]
    if not isinstance(gap, (int, float)) or gap < 0.0:
        gap_errors.append((r["chip_id"], gap, "INVALID_GAP"))
    elif r["stratum_id"] in ["STR-1", "STR-3", "STR-4"] and gap > 48.0:
        gap_errors.append((r["chip_id"], gap, "GAP_EXCEEDS_48H"))
print(f"6. Event-to-Scene Temporal Gap Check (<= 48h for fire strata): {len(gap_errors)} errors")

# 7. Duplicate Scenes Check
scene_counts = Counter(r["stac_scene_id"] for r in records)
dup_scenes = {sc: cnt for sc, cnt in scene_counts.items() if cnt > 1}
print(f"7. Duplicate STAC Scenes Across Chips: {len(dup_scenes)} duplicate scene IDs ({sum(dup_scenes.values())} total instances)")
for sc, cnt in list(dup_scenes.items())[:5]:
    chips = [r["chip_id"] for r in records if r["stac_scene_id"] == sc]
    print(f"   Scene: {sc} used by {cnt} chips: {chips}")

# 8. Duplicate Incidents Check (Stratum 1)
s1_records = [r for r in records if r["stratum_id"] == "STR-1"]
s1_inc_counts = Counter(r["incident_id"] for r in s1_records)
dup_incidents = {inc: cnt for inc, cnt in s1_inc_counts.items() if cnt > 1}
print(f"8. Duplicate Physical Incidents in Stratum 1: {len(dup_incidents)} duplicates")

