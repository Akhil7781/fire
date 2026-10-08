"""
Stage 8.19F: Independent Full Spatial Reproduction Script.
Directly loads Manifest v4 and recomputes all 22,090 cross-fold native UTM footprint distances,
structural isolation (tile, incident), and fold balance.
"""

from collections import Counter
import json
from pathlib import Path
from pyproj import Geod, Transformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_V4_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19e" / "ds08_expansion_candidates_v4.json"
OUTPUT_JSON_PATH = PROJECT_ROOT / "docs" / "stage8_19f" / "STAGE8_19F_SPATIAL_REPRODUCTION.json"


def reproduce_spatial_audit():
    with open(MANIFEST_V4_PATH, "r", encoding="utf-8") as f:
        v4 = json.load(f)

    records = v4["records"]
    exp = [r for r in records if r["candidate_stratum_id"] != "STR-7"]
    pilot_bench = [r for r in records if r["candidate_stratum_id"] == "STR-7"]

    assert len(records) == 250, f"Expected 250 records, got {len(records)}"
    assert len(exp) == 235, f"Expected 235 expansion records, got {len(exp)}"
    assert len(pilot_bench) == 15, f"Expected 15 pilot benchmark records, got {len(pilot_bench)}"

    geod = Geod(ellps="WGS84")

    # 1. Structural Invariants
    fold_counts = Counter(r["assigned_fold"] for r in exp)
    for k in range(1, 6):
        fn = f"Fold {k}"
        assert fold_counts[fn] == 47, f"Fold {fn} count mismatch: {fold_counts[fn]}"

    for r in pilot_bench:
        assert r["assigned_fold"] == "BENCHMARK_HELD_OUT"

    # Tile isolation
    tile_to_folds = {}
    for r in exp:
        tile_to_folds.setdefault(r["mgrs_tile"], set()).add(r["assigned_fold"])
    tile_splits = sum(1 for tile, folds in tile_to_folds.items() if len(folds) > 1)

    # Incident isolation
    inc_to_folds = {}
    for r in exp:
        inc_to_folds.setdefault(r["incident_id"], set()).add(r["assigned_fold"])
    inc_splits = sum(1 for inc, folds in inc_to_folds.items() if len(folds) > 1)

    # 2. Native UTM Footprint Geometry
    transformers_to_utm = {}
    transformers_to_wgs = {}

    def get_native_corners(r, half_m=2560.0):
        zone = int(r["mgrs_tile"][1:3])
        if zone not in transformers_to_utm:
            transformers_to_utm[zone] = Transformer.from_crs("EPSG:4326", f"EPSG:{32600 + zone}", always_xy=True)
            transformers_to_wgs[zone] = Transformer.from_crs(f"EPSG:{32600 + zone}", "EPSG:4326", always_xy=True)
        e, n = transformers_to_utm[zone].transform(r["longitude"], r["latitude"])
        corners_utm = [
            (e - half_m, n - half_m),
            (e + half_m, n - half_m),
            (e + half_m, n + half_m),
            (e - half_m, n + half_m),
        ]
        return [transformers_to_wgs[zone].transform(x, y) for x, y in corners_utm]

    def densify_corners(corners, num_steps=50):
        dense = []
        n = len(corners)
        for i in range(n):
            x1, y1 = corners[i]
            x2, y2 = corners[(i + 1) % n]
            for s in range(num_steps):
                frac = s / float(num_steps)
                dense.append((x1 + frac * (x2 - x1), y1 + frac * (y2 - y1)))
        return dense

    corners_map = {r["chip_id"]: get_native_corners(r) for r in exp}
    dense_corners_map = {r["chip_id"]: densify_corners(corners_map[r["chip_id"]], 25) for r in exp}

    def native_footprint_dist_km(cid1, cid2):
        c1 = dense_corners_map[cid1]
        c2 = dense_corners_map[cid2]
        return min(geod.inv(x1, y1, x2, y2)[2] for x1, y1 in c1 for x2, y2 in c2) / 1000.0

    # 3. Check repaired records
    r_by_id = {r["chip_id"]: r for r in exp}
    assert r_by_id["DS08_EXP_S4_018"]["assigned_fold"] == "Fold 3"
    assert r_by_id["DS08_EXP_S5_016"]["assigned_fold"] == "Fold 3"
    assert r_by_id["DS08_EXP_S4_043"]["assigned_fold"] == "Fold 4"

    # 4. Evaluate all 22,090 cross-fold pairs
    n_exp = len(exp)
    total_cross_fold = 0
    violations_le_50 = 0
    pairs_under_55 = 0
    min_dist_km = 999999.0
    closest_pair = None
    all_under_55_pairs = []

    for i in range(n_exp):
        for j in range(i + 1, n_exp):
            r1, r2 = exp[i], exp[j]
            if r1["assigned_fold"] != r2["assigned_fold"]:
                total_cross_fold += 1
                d = native_footprint_dist_km(r1["chip_id"], r2["chip_id"])
                if d <= 50.000000:
                    violations_le_50 += 1
                if d < 55.000000:
                    pairs_under_55 += 1
                    all_under_55_pairs.append({
                        "chip1": r1["chip_id"],
                        "fold1": r1["assigned_fold"],
                        "chip2": r2["chip_id"],
                        "fold2": r2["assigned_fold"],
                        "distance_km": round(d, 4),
                        "strata": f"{r1['candidate_stratum_id']}/{r2['candidate_stratum_id']}"
                    })
                if d < min_dist_km:
                    min_dist_km = d
                    closest_pair = (r1["chip_id"], r1["assigned_fold"], r2["chip_id"], r2["assigned_fold"])

    all_under_55_pairs.sort(key=lambda x: x["distance_km"])

    margin_m = (min_dist_km - 50.0) * 1000.0

    result = {
        "manifest_version": "v4",
        "geometry_method": "Native UTM raster footprint polygon (EPSG:32600+zone, 5120m x 5120m, rotated via grid convergence, densified edge-to-edge on WGS84 ellipsoid via pyproj.Geod)",
        "chip_size_m": 5120,
        "cross_fold_pairs": total_cross_fold,
        "violations_le_50km": violations_le_50,
        "minimum_separation_km": round(min_dist_km, 4),
        "minimum_margin_m": round(margin_m, 2),
        "closest_pair": [f"{closest_pair[0]} ({closest_pair[1]})", f"{closest_pair[2]} ({closest_pair[3]})"],
        "pairs_under_55km": pairs_under_55,
        "mgrs_tile_splits": tile_splits,
        "incident_splits": inc_splits,
        "fold_counts": {k: fold_counts[k] for k in sorted(fold_counts.keys())},
        "benchmark_held_out_count": len(pilot_bench),
        "repaired_pair_status": "PROVEN (DS08_EXP_S4_018 and DS08_EXP_S5_016 are co-located in Fold 3; zero cross-fold edge distance)",
        "reassignment_swap": "PROVEN (DS08_EXP_S4_018 in Fold 3, DS08_EXP_S4_043 in Fold 4)",
        "nearest_pairs_under_55km": all_under_55_pairs[:10],
        "status": "PROVEN" if (violations_le_50 == 0 and min_dist_km > 50.0 and tile_splits == 0 and inc_splits == 0) else "NOT_REPRODUCED"
    }

    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("=" * 70)
    print("STAGE 8.19F: INDEPENDENT SPATIAL REPRODUCTION RESULTS")
    print("=" * 70)
    print(f"Total cross-fold pairs evaluated: {total_cross_fold}")
    print(f"Violations <= 50.000000 km: {violations_le_50}")
    print(f"Global minimum separation: {min_dist_km:.4f} km ({margin_m:+.2f} m margin)")
    print(f"Globally closest pair: {closest_pair[0]} ({closest_pair[1]}) vs {closest_pair[2]} ({closest_pair[3]})")
    print(f"Pairs under 55 km: {pairs_under_55}")
    print(f"MGRS tile splits: {tile_splits}")
    print(f"Incident splits: {inc_splits}")
    print(f"Status: {result['status']}")


if __name__ == "__main__":
    reproduce_spatial_audit()
