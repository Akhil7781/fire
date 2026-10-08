import pyarrow.parquet as pq
import pandas as pd
import numpy as np
import math
from collections import defaultdict, Counter

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

# Read sample of causal features
print("Loading causal features sample...")
table = pq.read_table("data/interim/causal_features_2025.parquet", columns=["latitude", "longitude", "acq_datetime_utc", "frp"])
df = table.to_pandas()
print(f"Loaded {len(df)} rows.")

# Filter high FRP detections (> 10 MW)
high_frp = df[df["frp"] >= 10.0].copy()
print(f"High FRP count: {len(high_frp)}")

# Assign regions
high_frp["region"] = [classify_indian_region_v2(row.latitude, row.longitude) for row in high_frp.itertuples()]
print("Region counts in high FRP:")
print(high_frp["region"].value_counts())

# Test spatial thinning: ensure candidates within same stratum are spaced by at least 35-40 km
def select_spatially_dispersed(df_subset, n_target, min_dist_km=35.0):
    selected = []
    shuffled = df_subset.sample(frac=1.0, random_state=42)
    for row in shuffled.itertuples():
        too_close = False
        for s in selected:
            if haversine_km(row.latitude, row.longitude, s["latitude"], s["longitude"]) < min_dist_km:
                too_close = True
                break
        if not too_close:
            selected.append({
                "latitude": row.latitude,
                "longitude": row.longitude,
                "acq_datetime_utc": row.acq_datetime_utc,
                "frp": row.frp,
                "region": row.region
            })
            if len(selected) == n_target:
                break
    return selected

selected_points = []
for reg, n_req in [("NORTH", 52), ("CENTRAL", 57), ("SOUTH", 42), ("EAST", 47), ("WEST", 37)]:
    sub = high_frp[high_frp["region"] == reg]
    sel = select_spatially_dispersed(sub, n_req, min_dist_km=35.0)
    print(f"Region {reg}: required {n_req}, selected {len(sel)}")
    selected_points.extend(sel)

print(f"\nTotal dispersed points: {len(selected_points)}")

# Now test connected components at 50 km
n_pts = len(selected_points)
adj = {i: set() for i in range(n_pts)}
for i in range(n_pts):
    for j in range(i+1, n_pts):
        d = haversine_km(selected_points[i]["latitude"], selected_points[i]["longitude"],
                         selected_points[j]["latitude"], selected_points[j]["longitude"])
        if d <= 50.0:
            adj[i].add(j)
            adj[j].add(i)

visited = set()
comps = []
for i in range(n_pts):
    if i not in visited:
        comp = []
        q = [i]
        visited.add(i)
        while q:
            curr = q.pop(0)
            comp.append(curr)
            for nbr in adj[curr]:
                if nbr not in visited:
                    visited.add(nbr)
                    q.append(nbr)
        comps.append(comp)

print(f"Total clusters at 50 km: {len(comps)}")
sizes = [len(c) for c in comps]
print(f"Cluster sizes: max={max(sizes)}, min={min(sizes)}, mean={np.mean(sizes):.2f}")
print(f"Singletons: {sum(1 for s in sizes if s == 1)}")
