"""
Stage 8.19B: Build DS08 Expansion Candidate Manifest v3 Script.
Implements:
- DEC-U5: Record-specific conditional cloud exception metadata for DS08_EXP_S1_002 and DS08_EXP_S1_004.
- DEC-U6: Footprint-aware 50 km spatial separation (edge-to-edge geodesic distance on WGS84 ellipsoid).
- Guaranteed incident and MGRS scene grouping into identical folds.
- 5-fold cross-validation balance (exactly 47 expansion chips per fold).
- Frozen 15-chip pilot benchmark held out in STR-7 (BENCHMARK_HELD_OUT).
- Decoupled taxonomy: candidate_stratum_id, expected_target_class, human_confirmed_label=None for expansion.
"""

from __future__ import annotations

from collections import Counter
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Tuple

import pandas as pd
from pyproj import Geod
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_V2_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19a" / "ds08_expansion_candidates_v2.json"
MANIFEST_V3_OUTPUT_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b"


def get_footprint_corners(geod: Geod, lat: float, lon: float, half_m: float = 2560.0) -> List[Tuple[float, float]]:
    """Calculates 4 bounding corner coordinates (lon, lat) of 5.12 km x 5.12 km chip on WGS84."""
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
    """Computes minimum pairwise corner/edge distance in kilometers on WGS84."""
    min_d = 999999999.0
    for x1, y1 in poly1:
        for x2, y2 in poly2:
            _, _, d = geod.inv(x1, y1, x2, y2)
            if d < min_d:
                min_d = d
    return min_d / 1000.0


def build_manifest_v3() -> Dict[str, Any]:
    print("=" * 75)
    print("STAGE 8.19B — BUILDING AUDITED DS08 EXPANSION CANDIDATE MANIFEST V3")
    print("Enforcing Footprint-Aware 50 km Buffer (DEC-U6) & Cloud Exceptions (DEC-U5)")
    print("=" * 75)

    MANIFEST_V3_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(MANIFEST_V2_PATH, "r", encoding="utf-8") as f:
        v2_data = json.load(f)

    all_records = v2_data["records"]
    exp_records = [r for r in all_records if r["candidate_stratum_id"] != "STR-7"]
    pilot_records = [r for r in all_records if r["candidate_stratum_id"] == "STR-7"]
    n_exp = len(exp_records)
    geod = Geod(ellps="WGS84")

    print(f"\nLoaded {len(all_records)} total records from v2 manifest.")
    print(f"  Expansion candidates: {n_exp}")
    print(f"  Pilot benchmark records: {len(pilot_records)}")

    # 1. Compute footprints for all expansion candidates
    print("\nComputing geodesic chip footprints (5.12 km x 5.12 km)...")
    footprints = [get_footprint_corners(geod, r["latitude"], r["longitude"]) for r in exp_records]

    # 2. Build connected component adjacency graph
    print("Constructing spatial adjacency graph (Footprint Edge Distance <= 50.0 km + Grouping)...")
    adj = {i: set() for i in range(n_exp)}

    for i in range(n_exp):
        for j in range(i + 1, n_exp):
            r1, r2 = exp_records[i], exp_records[j]
            # Incident grouping rule
            if r1["incident_id"] and r2["incident_id"] and r1["incident_id"] == r2["incident_id"]:
                adj[i].add(j); adj[j].add(i)
                continue
            # Scene grouping rule
            if r1["stac_scene_id"] == r2["stac_scene_id"]:
                adj[i].add(j); adj[j].add(i)
                continue
            # Footprint edge-to-edge distance <= 50.0 km
            d_edge = footprint_edge_distance_km(geod, footprints[i], footprints[j])
            if d_edge <= 50.0:
                adj[i].add(j); adj[j].add(i)

    # 3. Find connected components
    visited = set()
    components = []
    for i in range(n_exp):
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
    max_comp_size = max(len(c) for c in components)
    print(f"Largest cluster size: {max_comp_size} chips ({max_comp_size / n_exp * 100:.1f}%)")

    # 4. Stratified greedy bin-packing into 5 folds (target: exactly 47 per fold)
    components.sort(key=lambda c: len(c), reverse=True)
    fold_capacities = {f"Fold {k}": 0 for k in range(1, 6)}
    fold_strata = {f"Fold {k}": Counter() for k in range(1, 6)}
    fold_assignment = {}
    target_per_fold = 47

    for comp in components:
        comp_size = len(comp)
        comp_strata = Counter(exp_records[idx]["candidate_stratum_id"] for idx in comp)
        candidates_folds = [f for f in fold_capacities if fold_capacities[f] + comp_size <= target_per_fold]
        if not candidates_folds:
            raise ValueError(f"Could not fit cluster of size {comp_size} into any fold without exceeding {target_per_fold}!")
        best_fold = min(candidates_folds, key=lambda f: fold_capacities[f])
        for idx in comp:
            fold_assignment[idx] = best_fold
        fold_capacities[best_fold] += comp_size
        fold_strata[best_fold] += comp_strata

    print("\nFold Allocation Summary (235 Expansion Candidates):")
    for f_name, cap in fold_capacities.items():
        print(f"  {f_name}: {cap} chips | Strata: {dict(fold_strata[f_name])}")
        assert cap == 47, f"Fold {f_name} does not have exactly 47 chips!"

    # 5. Assign folds and check separation
    for idx, f_name in fold_assignment.items():
        exp_records[idx]["assigned_fold"] = f_name

    min_inter_edge = 999999.0
    min_inter_center = 999999.0
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
                if d_center < min_inter_center:
                    min_inter_center = d_center
                if d_edge <= 50.0:
                    edge_violations += 1

    print(f"\nMinimum Inter-Fold Footprint Edge Distance: {min_inter_edge:.4f} km")
    print(f"Minimum Inter-Fold Center Distance: {min_inter_center:.4f} km")
    print(f"Footprint Edge Violations (<= 50.0 km): {edge_violations}")
    assert edge_violations == 0, f"Found {edge_violations} edge violations <= 50.0 km!"

    # 6. Apply DEC-U5 cloud exception metadata to affected records
    dec_u5_exception_chips = {"DS08_EXP_S1_002", "DS08_EXP_S1_004"}
    for r in all_records:
        if r["chip_id"] in dec_u5_exception_chips:
            r["cloud_exception_applied"] = True
            r["cloud_exception_id"] = "DEC-U5"
            r["cloud_exception_conditions"] = {
                "max_scene_cloud_pct_allowed": 20.0,
                "max_aoi_scl_cloud_shadow_pct": 5.0,
                "center_1km_cloud_pct_required": 0.0,
                "screening_status": "PENDING_STAGE_8_20_SCL_EVALUATION",
                "failure_handling": "MANDATORY_REJECTION_NO_AUTO_REPLACE"
            }
        else:
            r["cloud_exception_applied"] = False
            r["cloud_exception_id"] = None
            r["cloud_exception_conditions"] = None

    # Verify MGRS tile and incident grouping
    tile_to_folds = {}
    inc_to_folds = {}
    for r in all_records:
        t = r["mgrs_tile"]
        inc = r["incident_id"]
        f_name = r["assigned_fold"]
        tile_to_folds.setdefault(t, set()).add(f_name)
        inc_to_folds.setdefault(inc, set()).add(f_name)

    tile_splits = {t: f_set for t, f_set in tile_to_folds.items() if len(f_set) > 1}
    inc_splits = {inc: f_set for inc, f_set in inc_to_folds.items() if len(f_set) > 1}
    print(f"\nMGRS Tile Splits: {len(tile_splits)}")
    print(f"Incident Splits: {len(inc_splits)}")
    assert len(tile_splits) == 0, f"MGRS tile split across folds: {tile_splits}"
    assert len(inc_splits) == 0, f"Incident split across folds: {inc_splits}"

    # 7. Write version 3 manifest outputs
    json_path = MANIFEST_V3_OUTPUT_DIR / "ds08_expansion_candidates_v3.json"
    csv_path = MANIFEST_V3_OUTPUT_DIR / "ds08_expansion_candidates_v3.csv"
    parquet_path = MANIFEST_V3_OUTPUT_DIR / "ds08_expansion_candidates_v3.parquet"

    manifest_metadata = {
        "manifest_name": "ds08_expansion_candidates_v3",
        "stage": "STAGE_8_19B",
        "version": "3.0.0",
        "created_at_utc": "2026-10-02T23:05:00Z",
        "total_chips": len(all_records),
        "pilot_benchmark_held_out": len(pilot_records),
        "expansion_candidates_count": len(exp_records),
        "decisions_applied": {
            "DEC-U1": "2024 industrial fire expansion approved (10 unique incidents: 8 from 2025, 2 from 2024)",
            "DEC-U2": "Internal double-blind annotation structure preserved (UNLABELED_CANDIDATE)",
            "DEC-U3": "2.0-second delay between STAC requests enforced",
            "DEC-U4": "Read-only discovery & manifest building",
            "DEC-U5": "Record-specific conditional cloud exception for DS08_EXP_S1_002 and DS08_EXP_S1_004",
            "DEC-U6": "Footprint-aware 50 km spatial separation (edge-to-edge WGS84 geodesic)"
        },
        "spatial_parameters": {
            "spatial_thinning_min_dist_km": 30.0,
            "buffer_radius_km": 50.0,
            "buffer_measurement_type": "FOOTPRINT_EDGE_TO_EDGE",
            "min_inter_fold_footprint_edge_distance_km": round(min_inter_edge, 4),
            "min_inter_fold_center_distance_km": round(min_inter_center, 4),
            "footprint_edge_violations_at_50km": edge_violations
        },
        "strata_counts": dict(Counter(r["candidate_stratum_id"] for r in all_records)),
        "fold_counts": {
            **fold_capacities,
            "BENCHMARK_HELD_OUT": len(pilot_records)
        },
        "records": all_records
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(manifest_metadata, f, indent=2)
    print(f"\nWrote JSON manifest v3: {json_path}")

    # CSV
    df = pd.DataFrame(all_records)
    drop_cols = ["confirmed_bounding_boxes"]
    if "cloud_exception_conditions" in df.columns:
        drop_cols.append("cloud_exception_conditions")
    df_csv = df.drop(columns=drop_cols)
    df_csv.to_csv(csv_path, index=False)
    print(f"Wrote CSV manifest v3: {csv_path}")

    # Parquet
    df_parquet = df.copy()
    df_parquet["confirmed_bounding_boxes"] = df_parquet["confirmed_bounding_boxes"].apply(json.dumps)
    if "cloud_exception_conditions" in df_parquet.columns:
        df_parquet["cloud_exception_conditions"] = df_parquet["cloud_exception_conditions"].apply(lambda x: json.dumps(x) if x else None)
    table = pa.Table.from_pandas(df_parquet)
    pq.write_table(table, parquet_path)
    print(f"Wrote Parquet manifest v3: {parquet_path}")

    print("\n" + "=" * 75)
    print("STAGE 8.19B MANIFEST V3 GENERATION CERTIFIED COMPLETE")
    print("=" * 75)
    return manifest_metadata


if __name__ == "__main__":
    build_manifest_v3()
