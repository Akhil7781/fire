"""
Stage 8.19F: Fast & Rigorous Independent Spatial Reproduction Script.
Loads Manifest v4, recomputes all 22,090 cross-fold native UTM footprint distances,
structural isolation (tile, incident), and fold balance.
Outputs docs/stage8_19f/STAGE8_19F_SPATIAL_REPRODUCTION.json according to Section 17.
"""

from collections import Counter
import json
from pathlib import Path
from pyproj import Geod, Transformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_V4_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19e" / "ds08_expansion_candidates_v4.json"
OUTPUT_JSON_PATH = PROJECT_ROOT / "docs" / "stage8_19f" / "STAGE8_19F_SPATIAL_REPRODUCTION.json"


def run_spatial_reproduction():
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

    # 2. Footprint Construction
    transformers_to_utm = {}
    transformers_to_wgs = {}

    def get_corners_wgs84(r):
        tile = r["mgrs_tile"]
        zone = int(tile[1:3])
        if zone not in transformers_to_utm:
            transformers_to_utm[zone] = Transformer.from_crs("EPSG:4326", f"EPSG:{32600 + zone}", always_xy=True)
            transformers_to_wgs[zone] = Transformer.from_crs(f"EPSG:{32600 + zone}", "EPSG:4326", always_xy=True)
        e, n = transformers_to_utm[zone].transform(r["longitude"], r["latitude"])
        half_m = 2560.0
        c_utm = [
            (e - half_m, n - half_m),
            (e + half_m, n - half_m),
            (e + half_m, n + half_m),
            (e - half_m, n + half_m)
        ]
        return [transformers_to_wgs[zone].transform(x, y) for x, y in c_utm]

    def get_densified_edges_wgs84(r, n_samples=25):
        # Samples along all 4 edges in UTM then transforms to WGS84
        tile = r["mgrs_tile"]
        zone = int(tile[1:3])
        if zone not in transformers_to_utm:
            transformers_to_utm[zone] = Transformer.from_crs("EPSG:4326", f"EPSG:{32600 + zone}", always_xy=True)
            transformers_to_wgs[zone] = Transformer.from_crs(f"EPSG:{32600 + zone}", "EPSG:4326", always_xy=True)
        e, n = transformers_to_utm[zone].transform(r["longitude"], r["latitude"])
        half_m = 2560.0
        xs = [e - half_m, e + half_m]
        ys = [n - half_m, n + half_m]
        points_utm = []
        # bottom & top edges
        for i in range(n_samples):
            frac = i / (n_samples - 1)
            x = xs[0] + frac * (xs[1] - xs[0])
            points_utm.append((x, ys[0]))
            points_utm.append((x, ys[1]))
        # left & right edges
        for i in range(1, n_samples - 1):
            frac = i / (n_samples - 1)
            y = ys[0] + frac * (ys[1] - ys[0])
            points_utm.append((xs[0], y))
            points_utm.append((xs[1], y))
        return [transformers_to_wgs[zone].transform(x, y) for x, y in points_utm]

    print("Computing footprint corners for all 235 expansion candidates...")
    chip_corners = {r["chip_id"]: get_corners_wgs84(r) for r in exp}
    chip_centers = {r["chip_id"]: (r["longitude"], r["latitude"]) for r in exp}

    # 3. Pairwise Cross-Fold Analysis
    n_exp = len(exp)
    cross_fold_pairs = 0
    violations_le_50km = 0
    min_dist_km = 999999.0
    closest_pair = None
    pairs_below_55km = []

    # First pass: center-to-center fast screening
    for i in range(n_exp):
        c1 = exp[i]
        cid1 = c1["chip_id"]
        f1 = c1["assigned_fold"]
        lon1, lat1 = chip_centers[cid1]
        for j in range(i + 1, n_exp):
            c2 = exp[j]
            cid2 = c2["chip_id"]
            f2 = c2["assigned_fold"]
            if f1 != f2:
                cross_fold_pairs += 1
                _, _, d_center_m = geod.inv(lon1, lat1, chip_centers[cid2][0], chip_centers[cid2][1])
                d_center_km = d_center_m / 1000.0
                
                # Max chip radius is ~3.62 km (5.12 * sqrt(2) / 2)
                # If center distance > 65 km, footprint distance is guaranteed > 57.7 km > 50 km.
                if d_center_km < 65.0:
                    # Precise corner evaluation
                    d_corners = min(
                        geod.inv(x1, y1, x2, y2)[2]
                        for x1, y1 in chip_corners[cid1]
                        for x2, y2 in chip_corners[cid2]
                    ) / 1000.0

                    # If close to threshold, also check densified edges
                    if d_corners < 55.0:
                        dens1 = get_densified_edges_wgs84(c1, n_samples=30)
                        dens2 = get_densified_edges_wgs84(c2, n_samples=30)
                        d_dens = min(
                            geod.inv(x1, y1, x2, y2)[2]
                            for x1, y1 in dens1
                            for x2, y2 in dens2
                        ) / 1000.0
                        d_actual = d_dens
                    else:
                        d_actual = d_corners

                    if d_actual < 55.0:
                        pairs_below_55km.append({
                            "pair": [cid1, cid2],
                            "folds": [f1, f2],
                            "distance_km": round(d_actual, 6)
                        })

                    if d_actual <= 50.000000:
                        violations_le_50km += 1

                    if d_actual < min_dist_km:
                        min_dist_km = d_actual
                        closest_pair = [cid1, cid2]
                else:
                    # Guaranteed > 50 km
                    pass

    margin_m = (min_dist_km - 50.0) * 1000.0

    print(f"Total cross-fold pairs evaluated: {cross_fold_pairs}")
    print(f"Violations <= 50.0 km: {violations_le_50km}")
    print(f"Minimum separation: {min_dist_km:.6f} km")
    print(f"Minimum margin: {margin_m:.2f} m")
    print(f"Closest pair: {closest_pair}")
    print(f"Pairs below 55 km: {len(pairs_below_55km)}")
    for p in sorted(pairs_below_55km, key=lambda x: x["distance_km"]):
        print(f"  {p['pair'][0]} ({p['folds'][0]}) <-> {p['pair'][1]} ({p['folds'][1]}): {p['distance_km']:.4f} km")

    # Check repaired pair specifically
    r_map = {r["chip_id"]: r for r in exp}
    s4_018 = r_map["DS08_EXP_S4_018"]
    s5_016 = r_map["DS08_EXP_S5_016"]
    s4_043 = r_map["DS08_EXP_S4_043"]
    print("\nRepaired pair check:")
    print(f"  DS08_EXP_S4_018 fold: {s4_018['assigned_fold']}")
    print(f"  DS08_EXP_S5_016 fold: {s5_016['assigned_fold']}")
    print(f"  DS08_EXP_S4_043 fold: {s4_043['assigned_fold']}")
    assert s4_018["assigned_fold"] == "Fold 3"
    assert s5_016["assigned_fold"] == "Fold 3"
    assert s4_043["assigned_fold"] == "Fold 4"
    print("  -> Both DS08_EXP_S4_018 and DS08_EXP_S5_016 are in Fold 3! (Co-located, 0 cross-fold violation)")

    status = "PROVEN" if (violations_le_50km == 0 and min_dist_km > 50.000000 and tile_splits == 0 and inc_splits == 0) else "BLOCKED"

    result_json = {
        "manifest_version": "v4",
        "geometry_method": "Native UTM EPSG:326xx 5120m bounding box projected to WGS84 with Karney ellipsoidal geodesic distance",
        "chip_size_m": 5120,
        "cross_fold_pairs": cross_fold_pairs,
        "violations_le_50km": violations_le_50km,
        "minimum_separation_km": round(min_dist_km, 6),
        "minimum_margin_m": round(margin_m, 2),
        "closest_pair": closest_pair,
        "mgrs_tile_splits": tile_splits,
        "incident_splits": inc_splits,
        "fold_counts": {f"Fold {k}": fold_counts[f"Fold {k}"] for k in range(1, 6)},
        "benchmark_held_out_count": len(pilot_bench),
        "pairs_below_55km_count": len(pairs_below_55km),
        "pairs_below_55km": sorted(pairs_below_55km, key=lambda x: x["distance_km"]),
        "repaired_pair_check": {
            "DS08_EXP_S4_018_fold": s4_018["assigned_fold"],
            "DS08_EXP_S5_016_fold": s5_016["assigned_fold"],
            "DS08_EXP_S4_043_fold": s4_043["assigned_fold"],
            "co_located_same_fold": (s4_018["assigned_fold"] == s5_016["assigned_fold"])
        },
        "status": status
    }

    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result_json, f, indent=2)
    print(f"\nWritten spatial reproduction results to: {OUTPUT_JSON_PATH}")


if __name__ == "__main__":
    run_spatial_reproduction()
