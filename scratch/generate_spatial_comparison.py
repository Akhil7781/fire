"""
Stage 8.19G: Generate STAGE8_19G_SPATIAL_COMPARISON.json
Performs true polygon-to-polygon distance calculations for all 22,090 cross-fold pairs,
records comparison with Stage 8.19F, and outputs machine-readable JSON per Section 18.
"""

from collections import Counter
import json
from pathlib import Path
from pyproj import Geod, Transformer
from shapely.geometry import box, Polygon

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_V4_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19e" / "ds08_expansion_candidates_v4.json"
OUTPUT_JSON_PATH = PROJECT_ROOT / "docs" / "stage8_19g" / "STAGE8_19G_SPATIAL_COMPARISON.json"


def get_native_utm_box(r, half_m=2560.0):
    zone = int(r["mgrs_tile"][1:3])
    t_to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{32600 + zone}", always_xy=True)
    e, n = t_to_utm.transform(r["longitude"], r["latitude"])
    return box(e - half_m, n - half_m, e + half_m, n + half_m), zone, (e, n)


def sample_poly_pts(b, n_per_edge=25):
    coords = list(b.exterior.coords)
    pts = []
    for k in range(4):
        p0 = coords[k]
        p1 = coords[k + 1]
        for s in range(n_per_edge):
            frac = s / n_per_edge
            pts.append((p0[0] + frac * (p1[0] - p0[0]), p0[1] + frac * (p1[1] - p0[1])))
    return pts


def generate_spatial_comparison():
    with open(MANIFEST_V4_PATH, "r", encoding="utf-8") as f:
        v4 = json.load(f)

    records = v4["records"]
    exp = [r for r in records if r["candidate_stratum_id"] != "STR-7"]
    n_exp = len(exp)
    geod = Geod(ellps="WGS84")

    utm_data = {}
    for r in exp:
        cid = r["chip_id"]
        b, zone, center_en = get_native_utm_box(r)
        pts = sample_poly_pts(b, n_per_edge=25)
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

                _, _, d_center_m = geod.inv(c1["longitude"], c1["latitude"], c2["longitude"], c2["latitude"])
                d_center_km = d_center_m / 1000.0

                if d_center_km < 65.0:
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
                            "zones": [d1["zone"], d2["zone"]]
                        })

                    if d_poly_km <= 50.000000:
                        violations_le_50km += 1

                    if d_poly_km < min_dist_km:
                        min_dist_km = d_poly_km
                        closest_pair = [cid1, cid2]

    margin_m = (min_dist_km - 50.0) * 1000.0
    status = "REFERENCE_METRIC_CONFIRMED" if (violations_le_50km == 0 and min_dist_km > 50.000000) else "SPATIAL_METRIC_FAILURE_REQUIRES_REPAIR"

    result = {
        "manifest_version": "v4",
        "chip_footprint_definition": "512x512 pixels @ 10m GSD = 5120m x 5120m square bounding box centered at candidate coordinates in native UTM CRS",
        "reference_geometry_method": "True polygon-to-polygon Euclidean minimum separation (Shapely GEOS distance) on dense footprint boundaries",
        "reference_crs_strategy": "Pair-specific Azimuthal Equidistant (AEQD) projection centered at geographic midpoint of each candidate pair (+proj=aeqd +lat_0=lat_mid +lon_0=lon_mid +datum=WGS84)",
        "pairs_evaluated": cross_fold_pairs,
        "stage8_19f_min_km": 50.101722,
        "stage8_19g_min_km": round(min_dist_km, 6),
        "stage8_19f_closest_pair": ["DS08_EXP_S3_004", "DS08_EXP_S4_004"],
        "stage8_19g_closest_pair": closest_pair,
        "stage8_19f_violations": 0,
        "stage8_19g_violations": violations_le_50km,
        "margin_m": round(margin_m, 2),
        "pairs_under_55km": len(pairs_below_55km),
        "detailed_pairs_under_55km": sorted(pairs_below_55km, key=lambda x: x["distance_km"]),
        "status": status
    }

    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Written spatial comparison results to: {OUTPUT_JSON_PATH}")


if __name__ == "__main__":
    generate_spatial_comparison()
