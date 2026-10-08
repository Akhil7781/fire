import json
import math
from collections import defaultdict, Counter
import numpy as np

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

p = "data/reference/ds08/manifests/stage8_19/ds08_expansion_candidates_v1.json"
with open(p, "r", encoding="utf-8") as f:
    d = json.load(f)
records = [r for r in d["records"] if r["stratum_id"] != "STR-7"]
n = len(records)

print(f"Testing spatial clustering on actual {n} expansion candidates...")

# Compute all pairwise distances
dists = []
for i in range(n):
    for j in range(i+1, n):
        dist = haversine_km(records[i]["latitude"], records[i]["longitude"],
                            records[j]["latitude"], records[j]["longitude"])
        dists.append(dist)

print(f"Overall pairwise distances: min={min(dists):.2f} km, max={max(dists):.2f} km, median={np.median(dists):.2f} km")
print(f"Pairs < 30 km: {sum(1 for x in dists if x < 30.0)}")
print(f"Pairs < 40 km: {sum(1 for x in dists if x < 40.0)}")
print(f"Pairs < 50 km: {sum(1 for x in dists if x < 50.0)}")

for R in [30.0, 40.0, 50.0]:
    adj = {i: set() for i in range(n)}
    for i in range(n):
        for j in range(i+1, n):
            # incident grouping
            if records[i]["incident_id"] and records[j]["incident_id"] and records[i]["incident_id"] == records[j]["incident_id"]:
                adj[i].add(j); adj[j].add(i)
                continue
            dist = haversine_km(records[i]["latitude"], records[i]["longitude"],
                                records[j]["latitude"], records[j]["longitude"])
            if dist <= R:
                adj[i].add(j); adj[j].add(i)
    
    visited = set()
    comps = []
    for i in range(n):
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
    
    sizes = [len(c) for c in comps]
    print(f"\n--- Buffer R = {R:.1f} km ---")
    print(f"  Total clusters: {len(comps)}")
    print(f"  Max cluster size: {max(sizes)} chips ({max(sizes)/n*100:.1f}%)")
    print(f"  Singletons (1 chip): {sum(1 for s in sizes if s == 1)}")
    print(f"  Clusters > 1 chip: {sum(1 for s in sizes if s > 1)}")
