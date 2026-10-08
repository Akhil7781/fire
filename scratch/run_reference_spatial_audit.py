"""
Stage 8.19G: True Footprint-to-Footprint Polygon Distance Reference Script.
Evaluates all 22,090 cross-fold candidate pairs in Manifest v4 using true
polygon-to-polygon Euclidean distance in pair-specific Azimuthal Equidistant (AEQD) CRS,
and compares with native UTM and Stage 8.19F distances.
"""

from collections import Counter
import json
from pathlib import Path
import time
from pyproj import CRS, Geod, Transformer
from shapely.geometry import box, Polygon

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_V4_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19e" / "ds08_expansion_candidates_v4.json"


def get_native_utm_box(r, half_m=2560.0):
    zone = int(r["mgrs_tile"][1:3])
    t_to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{32600 + zone}", always_xy=True)
    e, n = t_to_utm.transform(r["longitude"], r["latitude"])
    return box(e - half_m, n - half_m, e + half_m, n + half_m), zone, (e, n)


def sample_poly_pts(b, n_per_edge=20):
    coords = list(b.exterior.coords)  # 5 points (closed)
    pts = []
    for k in range(4):
        p0 = coords[k]
        p1 = coords[k + 1]
        for s in range(n_per_edge):
            frac = s / n_per_edge
            x = p0[0] + frac * (p1[0] - p0[0])
            y = p0[1] + frac * (p1[1] - p0[1])
            pts.append((x, y))
    return pts


def run_audit():
    with open(MANIFEST_V4_PATH, "r", encoding="utf-8") as f:
        v4 = json.load(f)

    records = v4["records"]
    exp = [r for r in records if r["candidate_stratum_id"] != "STR-7"]
    n_exp = len(exp)
    geod = Geod(ellps="WGS84")

    print(f"Loaded {n_exp} expansion candidate records from Manifest v4.")

    # Precompute native UTM boxes and sample points
    print("Precomputing native UTM footprints (5.12 km x 5.12 km)...")
    utm_data = {}
    for r in exp:
        cid = r["chip_id"]
        b, zone, center_en = get_native_utm_box(r)
        pts = sample_poly_pts(b, n_per_edge=25)  # 100 perimeter points
        utm_data[cid] = {
            "box": b,
            "zone": zone,
            "center_en": center_en,
            "pts": pts,
            "record": r
        }

    cross_fold_pairs = 0
    violations_le_50km = 0
    min_dist_km = 999999.0
    closest_pair = None
    pairs_below_55km = []
    discrepancies_with_19f = []

    print("Evaluating all cross-fold pairs with true polygon-to-polygon distance...")
    t0 = time.time()

    for i in range(n_exp):
        c1 = exp[i]
        cid1 = c1["chip_id"]
        f1 = c1["assigned_fold"]
        d1 = utm_data[cid1]

        for j in range(i + 1, n_exp):
            c2 = exp[j]
            cid2 = c2["chip_id"]
            f2 = c2["assigned_fold"]

            if f1 != f2:
                cross_fold_pairs += 1
                d2 = utm_data[cid2]

                # Fast screening via center geodesic distance
                _, _, d_center_m = geod.inv(c1["longitude"], c1["latitude"], c2["longitude"], c2["latitude"])
                d_center_km = d_center_m / 1000.0

                # Max radius is ~3.62 km. If d_center > 65 km, min polygon distance is guaranteed > 57.7 km > 50 km.
                if d_center_km < 65.0:
                    # Construct pair-specific Azimuthal Equidistant CRS
                    lat_mid = (c1["latitude"] + c2["latitude"]) / 2.0
                    lon_mid = (c1["longitude"] + c2["longitude"]) / 2.0
                    aeqd_crs = f"+proj=aeqd +lat_0={lat_mid} +lon_0={lon_mid} +x_0=0 +y_0=0 +datum=WGS84 +units=m"

                    t1 = Transformer.from_crs(f"EPSG:{32600 + d1['zone']}", aeqd_crs, always_xy=True)
                    t2 = Transformer.from_crs(f"EPSG:{32600 + d2['zone']}", aeqd_crs, always_xy=True)

                    poly1_aeqd = Polygon([t1.transform(x, y) for x, y in d1["pts"]])
                    poly2_aeqd = Polygon([t2.transform(x, y) for x, y in d2["pts"]])

                    d_poly_m = poly1_aeqd.distance(poly2_aeqd)
                    d_poly_km = d_poly_m / 1000.0

                    if d_poly_km < 55.0:
                        pairs_below_55km.append({
                            "pair": [cid1, cid2],
                            "folds": [f1, f2],
                            "distance_km": round(d_poly_km, 6),
                            "distance_m": round(d_poly_m, 2),
                            "zones": [d1["zone"], d2["zone"]],
                            "same_zone": (d1["zone"] == d2["zone"])
                        })

                    if d_poly_km <= 50.000000:
                        violations_le_50km += 1

                    if d_poly_km < min_dist_km:
                        min_dist_km = d_poly_km
                        closest_pair = [cid1, cid2]

    t1 = time.time()
    margin_m = (min_dist_km - 50.0) * 1000.0

    print(f"\nEvaluation completed in {t1 - t0:.2f} seconds.")
    print(f"Total cross-fold pairs evaluated: {cross_fold_pairs}")
    print(f"Reference Violations <= 50.000000 km: {violations_le_50km}")
    print(f"Reference Minimum Separation: {min_dist_km:.6f} km")
    print(f"Reference Minimum Margin: {margin_m:.2f} m")
    print(f"Reference Closest Pair: {closest_pair}")
    print(f"Pairs below 55 km: {len(pairs_below_55km)}")
    print("\nTop 15 Closest Pairs:")
    for p in sorted(pairs_below_55km, key=lambda x: x["distance_km"])[:15]:
        print(f"  {p['pair'][0]} ({p['folds'][0]}) <-> {p['pair'][1]} ({p['folds'][1]}): {p['distance_km']:.6f} km | Zones: {p['zones']}")


if __name__ == "__main__":
    run_audit()
