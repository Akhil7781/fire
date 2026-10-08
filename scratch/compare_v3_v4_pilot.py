import json

with open('data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json', 'r', encoding='utf-8') as f:
    v3 = json.load(f)
with open('data/reference/ds08/manifests/stage8_19e/ds08_expansion_candidates_v4.json', 'r', encoding='utf-8') as f:
    v4 = json.load(f)

v3_map = {r['chip_id']: r for r in v3['records']}
v4_map = {r['chip_id']: r for r in v4['records']}

pilot_ids = [
    'DS08_EXP_S1_003', 'DS08_EXP_S1_002', 'DS08_EXP_S1_004',
    'DS08_EXP_S2_001', 'DS08_EXP_S3_001', 'DS08_EXP_S4_001',
    'DS08_EXP_S5_001', 'DS08_EXP_S6_001'
]

print('=== PILOT COHORT COMPARISON V3 vs V4 ===')
for pid in pilot_ids:
    r3 = v3_map[pid]
    r4 = v4_map[pid]
    print(f"\n--- {pid} ({r4['candidate_stratum_id']}) ---")
    print(f"  Target Class: {r4['expected_target_class']}")
    print(f"  Coord: ({r4['latitude']}, {r4['longitude']})")
    print(f"  V3 Product: {r3.get('stac_scene_id')}")
    print(f"  V4 Product: {r4.get('stac_scene_id')}")
    print(f"  V4 UUID: {r4.get('cdse_product_uuid')}")
    print(f"  V3 Sensing: {r3.get('sensing_time_utc')}")
    print(f"  V4 Sensing: {r4.get('sensing_time_utc')}")
    print(f"  V3 Tile: {r3.get('mgrs_tile')} vs V4 Tile: {r4.get('mgrs_tile')}")
    print(f"  Change Reason: {r4.get('change_reason')}")
    print(f"  Keys in r4: {[k for k in r4.keys() if 'date' in k or 'time' in k or 'event' in k]}")
