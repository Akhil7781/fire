import json
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

p = "data/reference/ds08/manifests/stage8_19/ds08_expansion_candidates_v1.json"
with open(p, "r", encoding="utf-8") as f:
    d = json.load(f)
records = [r for r in d["records"] if r["stratum_id"] != "STR-7"]
n = len(records)

# Build graph at R = 50.0 km
R = 50.0
adj = {i: set() for i in range(n)}
for i in range(n):
    for j in range(i+1, n):
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

print(f"50 km Clusters: {len(comps)}, Max size: {max(len(c) for c in comps)}")

# Greedy bin packing into 5 folds
comps.sort(key=lambda c: len(c), reverse=True)
fold_capacities = {f"Fold {k}": 0 for k in range(1, 6)}
fold_strata = {f"Fold {k}": Counter() for k in range(1, 6)}
fold_assignment = {}
target = 47

for comp in comps:
    comp_size = len(comp)
    comp_strata = Counter(records[idx]["stratum_id"] for idx in comp)
    avail = [f for f in fold_capacities if fold_capacities[f] + comp_size <= target]
    if not avail:
        avail = [min(fold_capacities, key=fold_capacities.get)]
    best = min(avail, key=lambda f: fold_capacities[f])
    for idx in comp:
        fold_assignment[idx] = best
    fold_capacities[best] += comp_size
    fold_strata[best] += comp_strata

print("\nFold capacities at 50 km:")
for f, c in fold_capacities.items():
    print(f"  {f}: {c} chips | {dict(fold_strata[f])}")

# Check minimum distance between different folds
min_dist = 999999.0
viol = 0
for i in range(n):
    for j in range(i+1, n):
        f1, f2 = fold_assignment[i], fold_assignment[j]
        if f1 != f2:
            dist = haversine_km(records[i]["latitude"], records[i]["longitude"],
                                records[j]["latitude"], records[j]["longitude"])
            if dist < min_dist:
                min_dist = dist
            if dist <= 50.0:
                viol += 1

print(f"\nMinimum inter-fold distance: {min_dist:.2f} km")
print(f"Cross-fold violations (dist <= 50 km): {viol}")
