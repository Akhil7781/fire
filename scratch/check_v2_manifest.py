import json
import re
from collections import Counter

with open('data/reference/ds08/manifests/stage8_19a/ds08_expansion_candidates_v2.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

records = data['records']
safe_regex = re.compile(r'^S2[ABC]_MSIL2A_\d{8}T\d{6}_N\d{4}_R\d{3}_T[0-9A-Z]{5}_\d{8}T\d{6}\.SAFE$')

failures = []
required_fields = [
    'chip_id', 'candidate_stratum_id', 'candidate_stratum_name',
    'expected_target_class', 'expected_class_id', 'human_confirmed_label',
    'annotation_status', 'confirmed_bounding_boxes', 'primary_sampling_unit',
    'incident_id', 'facility_or_location_name', 'state', 'latitude', 'longitude',
    'geographic_region', 'event_year', 's2_acquisition_year', 'stac_scene_id',
    'sensing_time_utc', 'cloud_cover_pct', 'mgrs_tile', 'temporal_phase',
    'delta_time_hours', 'temporal_matching_tier', 'corroboration_source',
    'is_primary_chip', 'spatial_group_id', 'assigned_fold', 'image_status'
]

for idx, r in enumerate(records):
    # 1. Missing fields
    for field_name in required_fields:
        if field_name not in r:
            failures.append(f"Record {r.get('chip_id', idx)} missing field {field_name}")
    
    # 2. Product ID regex
    pid = r['stac_scene_id']
    if not safe_regex.match(pid):
        failures.append(f"Record {r['chip_id']} invalid product ID: {pid}")
        
    # 3. Coordinates
    lat, lon = r['latitude'], r['longitude']
    if not (8.0 <= lat <= 38.0 and 68.0 <= lon <= 98.0):
        failures.append(f"Record {r['chip_id']} out of India bounding box: lat={lat}, lon={lon}")
        
    # 4. Cloud cover
    cc = r['cloud_cover_pct']
    if not (0.0 <= cc <= 20.0):
        failures.append(f"Record {r['chip_id']} cloud cover out of spec: {cc}")
        
    # 5. Temporal gap
    if r['candidate_stratum_id'] in ['STR-1', 'STR-2', 'STR-3', 'STR-4']:
        dt_h = r['delta_time_hours']
        if dt_h > 48.0 or dt_h < 0.0:
            failures.append(f"Record {r['chip_id']} delta time out of spec: {dt_h}h")

# 6. Incident grouping
incident_to_folds = {}
for r in records:
    inc = r['incident_id']
    f_name = r['assigned_fold']
    if inc not in incident_to_folds:
        incident_to_folds[inc] = set()
    incident_to_folds[inc].add(f_name)

for inc, f_set in incident_to_folds.items():
    if len(f_set) > 1:
        failures.append(f"Incident {inc} split across folds: {f_set}")

# 7. Scene grouping
scene_to_folds = {}
for r in records:
    sc = r['stac_scene_id']
    f_name = r['assigned_fold']
    if sc not in scene_to_folds:
        scene_to_folds[sc] = set()
    scene_to_folds[sc].add(f_name)

for sc, f_set in scene_to_folds.items():
    if len(f_set) > 1:
        failures.append(f"Scene {sc} split across folds: {f_set}")

# 8. Unlabeled candidate status for expansion
for r in records:
    if r['candidate_stratum_id'] != 'STR-7':
        if r['human_confirmed_label'] is not None:
            failures.append(f"Expansion record {r['chip_id']} has premature human label: {r['human_confirmed_label']}")
        if r['annotation_status'] != 'UNLABELED_CANDIDATE':
            failures.append(f"Expansion record {r['chip_id']} status not UNLABELED_CANDIDATE: {r['annotation_status']}")
        if len(r['confirmed_bounding_boxes']) > 0:
            failures.append(f"Expansion record {r['chip_id']} has premature confirmed boxes")
    else:
        if r['human_confirmed_label'] is None:
            failures.append(f"Pilot record {r['chip_id']} missing human confirmed label")
        if r['assigned_fold'] != 'BENCHMARK_HELD_OUT':
            failures.append(f"Pilot record {r['chip_id']} fold not BENCHMARK_HELD_OUT: {r['assigned_fold']}")

print("Audit check completed.")
print(f"Total failures detected: {len(failures)}")
if failures:
    for f in failures[:10]:
        print("  FAIL:", f)
else:
    print("ALL AUDIT INTEGRITY CHECKS PASSED WITH 0 FAILURES!")
