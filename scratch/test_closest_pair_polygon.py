import json
from shapely.geometry import box, Polygon, Point
from pyproj import Transformer, Geod, CRS

with open('data/reference/ds08/manifests/stage8_19e/ds08_expansion_candidates_v4.json', 'r', encoding='utf-8') as f:
    v4 = json.load(f)

r_map = {r['chip_id']: r for r in v4['records']}

c1 = r_map['DS08_EXP_S3_004']
c2 = r_map['DS08_EXP_S4_004']

geod = Geod(ellps="WGS84")

# 1. Center geodesic distance
_, _, d_center_m = geod.inv(c1['longitude'], c1['latitude'], c2['longitude'], c2['latitude'])
print(f"Center-to-Center Geodesic Distance: {d_center_m / 1000.0:.6f} km ({d_center_m:.2f} m)")

# 2. Footprint in native UTM
zone1 = int(c1['mgrs_tile'][1:3])
zone2 = int(c2['mgrs_tile'][1:3])
t1_to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{32600 + zone1}", always_xy=True)
t2_to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{32600 + zone2}", always_xy=True)

e1, n1 = t1_to_utm.transform(c1['longitude'], c1['latitude'])
e2, n2 = t2_to_utm.transform(c2['longitude'], c2['latitude'])
half_m = 2560.0

poly1_utm = box(e1 - half_m, n1 - half_m, e1 + half_m, n1 + half_m)
poly2_utm = box(e2 - half_m, n2 - half_m, e2 + half_m, n2 + half_m)

# Since both are in Zone 43:
if zone1 == zone2:
    d_utm_m = poly1_utm.distance(poly2_utm)
    print(f"Native UTM Zone 43 Euclidean Polygon Distance: {d_utm_m / 1000.0:.6f} km ({d_utm_m:.2f} m)")

# 3. Corner-to-corner geodesic distance
t1_to_wgs = Transformer.from_crs(f"EPSG:{32600 + zone1}", "EPSG:4326", always_xy=True)
t2_to_wgs = Transformer.from_crs(f"EPSG:{32600 + zone2}", "EPSG:4326", always_xy=True)

corners1_wgs = [t1_to_wgs.transform(x, y) for x, y in poly1_utm.exterior.coords[:4]]
corners2_wgs = [t2_to_wgs.transform(x, y) for x, y in poly2_utm.exterior.coords[:4]]

d_corners_m = min(geod.inv(x1, y1, x2, y2)[2] for x1, y1 in corners1_wgs for x2, y2 in corners2_wgs)
print(f"Corner-to-Corner Geodesic Distance: {d_corners_m / 1000.0:.6f} km ({d_corners_m:.2f} m)")

# 4. Pair-Specific Azimuthal Equidistant (AEQD)
lat_mid = (c1['latitude'] + c2['latitude']) / 2.0
lon_mid = (c1['longitude'] + c2['longitude']) / 2.0
aeqd_crs = f"+proj=aeqd +lat_0={lat_mid} +lon_0={lon_mid} +x_0=0 +y_0=0 +datum=WGS84 +units=m"

t1_to_aeqd = Transformer.from_crs(f"EPSG:{32600 + zone1}", aeqd_crs, always_xy=True)
t2_to_aeqd = Transformer.from_crs(f"EPSG:{32600 + zone2}", aeqd_crs, always_xy=True)

# Reproject dense exterior coordinates
def get_dense_poly(utm_poly, transformer, n_samples_per_edge=50):
    coords = list(utm_poly.exterior.coords)
    dense_pts = []
    for k in range(4):
        p_start = coords[k]
        p_end = coords[k + 1]
        for s in range(n_samples_per_edge):
            f = s / n_samples_per_edge
            x = p_start[0] + f * (p_end[0] - p_start[0])
            y = p_start[1] + f * (p_end[1] - p_start[1])
            dense_pts.append(transformer.transform(x, y))
    return Polygon(dense_pts)

poly1_aeqd = get_dense_poly(poly1_utm, t1_to_aeqd, n_samples_per_edge=100)
poly2_aeqd = get_dense_poly(poly2_utm, t2_to_aeqd, n_samples_per_edge=100)

d_aeqd_m = poly1_aeqd.distance(poly2_aeqd)
print(f"True AEQD Polygon-to-Polygon Distance: {d_aeqd_m / 1000.0:.6f} km ({d_aeqd_m:.2f} m)")

# 5. Geodesic distance on dense points
t1_to_wgs_dense = get_dense_poly(poly1_utm, t1_to_wgs, n_samples_per_edge=100)
t2_to_wgs_dense = get_dense_poly(poly2_utm, t2_to_wgs, n_samples_per_edge=100)
pts1 = list(t1_to_wgs_dense.exterior.coords)
pts2 = list(t2_to_wgs_dense.exterior.coords)
d_geod_dense_m = min(geod.inv(x1, y1, x2, y2)[2] for x1, y1 in pts1 for x2, y2 in pts2)
print(f"Dense Geodesic Boundary Distance (400 samples): {d_geod_dense_m / 1000.0:.6f} km ({d_geod_dense_m:.2f} m)")
