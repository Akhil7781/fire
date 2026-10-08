"""
Stage 8.19B: Standalone Reproducible Spatial Footprint Audit Script.
Verifies footprint-aware 50 km cross-fold separation, MGRS tile isolation,
and incident isolation on the authoritative Manifest v3.
"""

from collections import Counter
import json
from pathlib import Path
import sys
from typing import List, Tuple

from pyproj import Geod

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_V3_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b" / "ds08_expansion_candidates_v3.json"


def get_footprint_corners(geod: Geod, lat: float, lon: float, half_m: float = 2560.0) -> List[Tuple[float, float]]:
    lon_n, lat_n, _ = geod.fwd(lon, lat, 0.0, half_m)
    lon_s, lat_s, _ = geod.fwd(lon, lat, 180.0, half_m)
    lon_e, lat_e, _ = geod.fwd(lon, lat, 90.0, half_m)
    lon_w, lat_w, _ = geod.fwd(lon, lat, 270.0, half_m)
    dlat = (lat_n - lat_s) / 2.0
    dlon = (lon_e - lon_w) / 2.0
    return [
        (lon - dlon, lat - dlat),
        (lon + dlon, lat - dlat),
        (lon + dlon, lat + dlat),
        (lon - dlon, lat + dlat)
    ]


def footprint_edge_distance_km(geod: Geod, poly1: List[Tuple[float, float]], poly2: List[Tuple[float, float]]) -> float:
    min_d = 999999999.0
    for x1, y1 in poly1:
        for x2, y2 in poly2:
            _, _, d = geod.inv(x1, y1, x2, y2)
            if d < min_d:
                min_d = d
    return min_d / 1000.0


def audit_spatial_footprint():
    print("=" * 75)
    print("STAGE 8.19B: REPRODUCIBLE FOOTPRINT-AWARE SPATIAL AUDIT")
    print("=" * 75)

    with open(MANIFEST_V3_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data["records"]
    exp_records = [r for r in records if r["candidate_stratum_id"] != "STR-7"]
    pilot_records = [r for r in records if r["candidate_stratum_id"] == "STR-7"]
    n_exp = len(exp_records)
    geod = Geod(ellps="WGS84")

    # 1. Fold Capacities
    fold_counts = Counter(r["assigned_fold"] for r in exp_records)
    print("\n[1/5] Checking Fold Capacities (Target: exactly 47 chips in Folds 1-5):")
    for k in range(1, 6):
        f_name = f"Fold {k}"
        cnt = fold_counts[f_name]
        print(f"  {f_name}: {cnt} chips")
        assert cnt == 47, f"Fold capacity violation: {f_name} has {cnt} chips"

    assert len(pilot_records) == 15
    for r in pilot_records:
        assert r["assigned_fold"] == "BENCHMARK_HELD_OUT"
    print("  Pilot Benchmark (STR-7): 15 chips held out (BENCHMARK_HELD_OUT)")

    # 2. Footprint-Aware Separation
    print("\n[2/5] Evaluating Footprint-to-Footprint Geodesic Distances (WGS84)...")
    footprints = [get_footprint_corners(geod, r["latitude"], r["longitude"]) for r in exp_records]

    min_inter_edge = 999999.0
    min_inter_center = 999999.0
    min_pair_edge = None
    min_pair_center = None
    edge_violations = 0

    for i in range(n_exp):
        for j in range(i + 1, n_exp):
            if exp_records[i]["assigned_fold"] != exp_records[j]["assigned_fold"]:
                d_edge = footprint_edge_distance_km(geod, footprints[i], footprints[j])
                _, _, d_center_m = geod.inv(
                    exp_records[i]["longitude"], exp_records[i]["latitude"],
                    exp_records[j]["longitude"], exp_records[j]["latitude"]
                )
                d_center = d_center_m / 1000.0

                if d_edge < min_inter_edge:
                    min_inter_edge = d_edge
                    min_pair_edge = (exp_records[i], exp_records[j])
                if d_center < min_inter_center:
                    min_inter_center = d_center
                    min_pair_center = (exp_records[i], exp_records[j])
                if d_edge <= 50.0:
                    edge_violations += 1

    print(f"  Minimum Footprint Edge-to-Edge Distance: {min_inter_edge:.4f} km")
    print(f"    Closest Pair: {min_pair_edge[0]['chip_id']} ({min_pair_edge[0]['assigned_fold']}) vs {min_pair_edge[1]['chip_id']} ({min_pair_edge[1]['assigned_fold']})")
    print(f"  Minimum Center-to-Center Distance: {min_inter_center:.4f} km")
    print(f"    Closest Pair: {min_pair_center[0]['chip_id']} ({min_pair_center[0]['assigned_fold']}) vs {min_pair_center[1]['chip_id']} ({min_pair_center[1]['assigned_fold']})")
    print(f"  Cross-Fold Footprint Edge Violations (<= 50.0 km): {edge_violations}")
    assert edge_violations == 0, f"Found {edge_violations} cross-fold footprint violations <= 50.0 km!"
    assert min_inter_edge > 50.0, f"Minimum footprint distance {min_inter_edge:.4f} km <= 50.0 km"

    # 3. MGRS Tile Isolation
    print("\n[3/5] Checking MGRS Tile Isolation Across Folds...")
    tile_to_folds = {}
    for r in records:
        tile_to_folds.setdefault(r["mgrs_tile"], set()).add(r["assigned_fold"])
    tile_splits = {t: f_set for t, f_set in tile_to_folds.items() if len(f_set) > 1}
    print(f"  MGRS Tile Splits across folds: {len(tile_splits)}")
    assert len(tile_splits) == 0, f"MGRS Tile splits detected: {tile_splits}"

    # 4. Incident Isolation
    print("\n[4/5] Checking Physical Incident Isolation Across Folds...")
    inc_to_folds = {}
    for r in records:
        inc_to_folds.setdefault(r["incident_id"], set()).add(r["assigned_fold"])
    inc_splits = {inc: f_set for inc, f_set in inc_to_folds.items() if len(f_set) > 1}
    print(f"  Incident Splits across folds: {len(inc_splits)}")
    assert len(inc_splits) == 0, f"Incident splits detected: {inc_splits}"

    # 5. Summary
    print("\n[5/5] Spatial Audit Status: 100% PASS")
    print("=" * 75)


if __name__ == "__main__":
    audit_spatial_footprint()
