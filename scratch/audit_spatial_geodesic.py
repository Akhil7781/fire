import json
import math
from pyproj import Geod
from shapely.geometry import Polygon

with open('data/reference/ds08/manifests/stage8_19a/ds08_expansion_candidates_v2.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

exp = [r for r in data['records'] if r['candidate_stratum_id'] != 'STR-7']
n = len(exp)
geod = Geod(ellps='WGS84')

# 1. Center-to-center geodesic
min_center_geod = 999999.0
min_pair_center = None
violations_center = 0

for i in range(n):
    for j in range(i + 1, n):
        if exp[i]['assigned_fold'] != exp[j]['assigned_fold']:
            _, _, d = geod.inv(exp[i]['longitude'], exp[i]['latitude'], exp[j]['longitude'], exp[j]['latitude'])
            d_km = d / 1000.0
            if d_km < min_center_geod:
                min_center_geod = d_km
                min_pair_center = (exp[i], exp[j])
            if d_km <= 50.0:
                violations_center += 1

print(f"Minimum Center-to-Center Geodesic Distance (WGS84): {min_center_geod:.4f} km")
print(f"  Chip 1: {min_pair_center[0]['chip_id']} ({min_pair_center[0]['assigned_fold']}, Lat {min_pair_center[0]['latitude']}, Lon {min_pair_center[0]['longitude']})")
print(f"  Chip 2: {min_pair_center[1]['chip_id']} ({min_pair_center[1]['assigned_fold']}, Lat {min_pair_center[1]['latitude']}, Lon {min_pair_center[1]['longitude']})")
print(f"  Center violations <= 50.0 km: {violations_center}")

# 2. Footprint-to-footprint geodesic
# A chip is 512 pixels x 10m = 5,120m x 5,120m.
# Half-width in meters = 2,560m.
# In local projection, footprint bounding box extends +/- 2560m in easting and northing.
# Let's compute edge-to-edge distance between footprints.
# For each chip center (lat, lon), we can calculate the 4 corners using geodesic direct:
def get_chip_footprint_corners(lat, lon, half_side_m=2560.0):
    # Approximating bounding corners on WGS84:
    # North offset:
    lon_n, lat_n, _ = geod.fwd(lon, lat, 0.0, half_side_m)
    lon_s, lat_s, _ = geod.fwd(lon, lat, 180.0, half_side_m)
    lon_e, lat_e, _ = geod.fwd(lon, lat, 90.0, half_side_m)
    lon_w, lat_w, _ = geod.fwd(lon, lat, 270.0, half_side_m)
    dlat = (lat_n - lat_s) / 2.0
    dlon = (lon_e - lon_w) / 2.0
    return Polygon([
        (lon - dlon, lat - dlat),
        (lon + dlon, lat - dlat),
        (lon + dlon, lat + dlat),
        (lon - dlon, lat + dlat)
    ])

footprints = [get_chip_footprint_corners(r['latitude'], r['longitude']) for r in exp]

# Using shapely or geodesic to compute minimum edge-to-edge distance:
# Note: distance between two rectangles separated by ~50km center distance:
# Edge-to-edge distance D_edge approx = D_center - 2 * half_diagonal (in direction of separation).
# Max half-diagonal = sqrt(2560^2 + 2560^2) = 3620.386 m = 3.62 km.
# So D_edge is approximately D_center - 5.12 km to 7.24 km depending on orientation.
min_footprint_dist = 999999.0
min_pair_footprint = None
footprint_violations_50km = 0

for i in range(n):
    for j in range(i + 1, n):
        if exp[i]['assigned_fold'] != exp[j]['assigned_fold']:
            # Exact distance between poly i and poly j
            poly1 = footprints[i]
            poly2 = footprints[j]
            # Approximate distance by taking center distance minus bounds
            # Or using geod on nearest points on bounding box:
            p1_near, p2_near = poly1.exterior.distance(poly2.exterior), None
            # Compute geodesic between closest points on exterior
            # Or more simply: min over all corner and edge midpoints
            pts1 = list(poly1.exterior.coords)
            pts2 = list(poly2.exterior.coords)
            local_min_d = 999999.0
            for x1, y1 in pts1:
                for x2, y2 in pts2:
                    _, _, dist_m = geod.inv(x1, y1, x2, y2)
                    if dist_m < local_min_d:
                        local_min_d = dist_m
            d_km = local_min_d / 1000.0
            if d_km < min_footprint_dist:
                min_footprint_dist = d_km
                min_pair_footprint = (exp[i], exp[j])
            if d_km <= 50.0:
                footprint_violations_50km += 1

print(f"\nMinimum Footprint-to-Footprint Distance (WGS84): {min_footprint_dist:.4f} km")
print(f"  Chip 1: {min_pair_footprint[0]['chip_id']} ({min_pair_footprint[0]['assigned_fold']})")
print(f"  Chip 2: {min_pair_footprint[1]['chip_id']} ({min_pair_footprint[1]['assigned_fold']})")
print(f"  Footprint pairs <= 50.0 km: {footprint_violations_50km}")

# 3. MGRS Tile Grouping Check
tile_to_folds = {}
for r in data['records']:
    t = r['mgrs_tile']
    f = r['assigned_fold']
    if t not in tile_to_folds:
        tile_to_folds[t] = set()
    tile_to_folds[t].add(f)

tile_splits = {t: folds for t, folds in tile_to_folds.items() if len(folds) > 1}
print(f"\nMGRS Tile Splits across folds: {len(tile_splits)}")
if tile_splits:
    for t, folds in list(tile_splits.items())[:5]:
        print(f"  Tile {t} split across {folds}")

# 4. Incident Grouping Check
inc_to_folds = {}
for r in data['records']:
    inc = r['incident_id']
    f = r['assigned_fold']
    if inc not in inc_to_folds:
        inc_to_folds[inc] = set()
    inc_to_folds[inc].add(f)

inc_splits = {inc: folds for inc, folds in inc_to_folds.items() if len(folds) > 1}
print(f"Incident Splits across folds: {len(inc_splits)}")
if inc_splits:
    for inc, folds in list(inc_splits.items())[:5]:
        print(f"  Incident {inc} split across {folds}")
