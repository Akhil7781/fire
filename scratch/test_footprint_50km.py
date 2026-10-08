import json
from collections import Counter
from pyproj import Geod
from shapely.geometry import Polygon

with open('data/reference/ds08/manifests/stage8_19a/ds08_expansion_candidates_v2.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

exp = [r for r in data['records'] if r['candidate_stratum_id'] != 'STR-7']
n = len(exp)
geod = Geod(ellps='WGS84')

# Create footprint polygons for all 235 chips
# Half-width = 2560m
def get_footprint(lat, lon, half_m=2560.0):
    lon_n, lat_n, _ = geod.fwd(lon, lat, 0.0, half_m)
    lon_s, lat_s, _ = geod.fwd(lon, lat, 180.0, half_m)
    lon_e, lat_e, _ = geod.fwd(lon, lat, 90.0, half_m)
    lon_w, lat_w, _ = geod.fwd(lon, lat, 270.0, half_m)
    dlat = (lat_n - lat_s) / 2.0
    dlon = (lon_e - lon_w) / 2.0
    # 4 corners
    return [
        (lon - dlon, lat - dlat),
        (lon + dlon, lat - dlat),
        (lon + dlon, lat + dlat),
        (lon - dlon, lat + dlat)
    ]

chip_corners = [get_footprint(r['latitude'], r['longitude']) for r in exp]

def footprint_edge_dist_km(c1, c2):
    min_d = 999999999.0
    for x1, y1 in c1:
        for x2, y2 in c2:
            _, _, d = geod.inv(x1, y1, x2, y2)
            if d < min_d:
                min_d = d
    return min_d / 1000.0

print("Building adjacency graph with footprint-to-footprint edge distance <= 50.0 km...")
adj = {i: set() for i in range(n)}
for i in range(n):
    for j in range(i + 1, n):
        r1, r2 = exp[i], exp[j]
        # Incident rule
        if r1['incident_id'] and r2['incident_id'] and r1['incident_id'] == r2['incident_id']:
            adj[i].add(j); adj[j].add(i)
            continue
        # Scene rule
        if r1['stac_scene_id'] == r2['stac_scene_id']:
            adj[i].add(j); adj[j].add(i)
            continue
        # Footprint edge-to-edge distance
        d_edge = footprint_edge_dist_km(chip_corners[i], chip_corners[j])
        if d_edge <= 50.0:
            adj[i].add(j); adj[j].add(i)

visited = set()
components = []
for i in range(n):
    if i not in visited:
        comp = []
        queue = [i]
        visited.add(i)
        while queue:
            curr = queue.pop(0)
            comp.append(curr)
            for nbr in adj[curr]:
                if nbr not in visited:
                    visited.add(nbr)
                    queue.append(nbr)
        components.append(comp)

print(f"Total connected components: {len(components)}")
comp_sizes = [len(c) for c in components]
print(f"Cluster sizes: min={min(comp_sizes)}, max={max(comp_sizes)}")
print(f"Cluster size distribution: {dict(Counter(comp_sizes))}")

# Try bin packing into 5 folds of 47 chips
components.sort(key=lambda c: len(c), reverse=True)
fold_caps = {f"Fold {k}": 0 for k in range(1, 6)}
fold_assignment = {}
target = 47

success = True
for comp in components:
    c_size = len(comp)
    valid_folds = [f for f in fold_caps if fold_caps[f] + c_size <= target]
    if not valid_folds:
        print(f"FAILED: Cannot fit component of size {c_size} into any fold without exceeding {target}!")
        print(f"Current fold capacities: {fold_caps}")
        success = False
        break
    best_fold = min(valid_folds, key=lambda f: fold_caps[f])
    for idx in comp:
        fold_assignment[idx] = best_fold
    fold_caps[best_fold] += c_size

if success:
    print("\nSUCCESS! Perfectly packed into 5 folds:")
    for f, count in fold_caps.items():
        print(f"  {f}: {count} chips")
    
    # Verify minimum edge distance between folds
    min_inter_edge = 999999.0
    min_inter_center = 999999.0
    violations_edge = 0
    for i in range(n):
        for j in range(i + 1, n):
            if fold_assignment[i] != fold_assignment[j]:
                d_edge = footprint_edge_dist_km(chip_corners[i], chip_corners[j])
                _, _, d_center_m = geod.inv(exp[i]['longitude'], exp[i]['latitude'], exp[j]['longitude'], exp[j]['latitude'])
                d_center = d_center_m / 1000.0
                if d_edge < min_inter_edge:
                    min_inter_edge = d_edge
                if d_center < min_inter_center:
                    min_inter_center = d_center
                if d_edge <= 50.0:
                    violations_edge += 1
    print(f"\nMinimum Inter-Fold Edge-to-Edge Distance: {min_inter_edge:.4f} km")
    print(f"Minimum Inter-Fold Center-to-Center Distance: {min_inter_center:.4f} km")
    print(f"Footprint Edge Violations <= 50.0 km: {violations_edge}")
