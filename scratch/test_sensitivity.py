"""
Numerical sensitivity test for polygon footprint distance on the closest pair.
"""

from shapely.geometry import box, Polygon
from pyproj import Transformer, Geod

c1 = {"chip_id": "DS08_EXP_S3_004", "mgrs_tile": "T43SEN", "lat": 30.85742, "lon": 74.37711}
c2 = {"chip_id": "DS08_EXP_S4_004", "mgrs_tile": "T43SDN", "lat": 30.79358, "lon": 73.80075}

half_m = 2560.0
geod = Geod(ellps="WGS84")

# Native UTM box
t1_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
t2_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)

e1, n1 = t1_to_utm.transform(c1["lon"], c1["lat"])
e2, n2 = t2_to_utm.transform(c2["lon"], c2["lat"])

box1_utm = box(e1 - half_m, n1 - half_m, e1 + half_m, n1 + half_m)
box2_utm = box(e2 - half_m, n2 - half_m, e2 + half_m, n2 + half_m)

# 1. Native UTM distance
d_utm = box1_utm.distance(box2_utm)

# 2. AEQD projection centered at midpoint
lat_mid = (c1["lat"] + c2["lat"]) / 2.0
lon_mid = (c1["lon"] + c2["lon"]) / 2.0
aeqd_crs = f"+proj=aeqd +lat_0={lat_mid} +lon_0={lon_mid} +x_0=0 +y_0=0 +datum=WGS84 +units=m"

t1_aeqd = Transformer.from_crs("EPSG:32643", aeqd_crs, always_xy=True)
t2_aeqd = Transformer.from_crs("EPSG:32643", aeqd_crs, always_xy=True)

# Test with different sampling densities along edge: 4, 10, 50, 100, 500
print("=== SENSITIVITY TEST: DENSITY OF POLYGON EDGE SAMPLES ===")
for n_samples in [4, 10, 25, 50, 100, 500]:
    def sample_poly(b, n):
        coords = list(b.exterior.coords)
        pts = []
        for k in range(4):
            p0, p1 = coords[k], coords[k + 1]
            for s in range(n):
                f = s / n
                pts.append((p0[0] + f*(p1[0] - p0[0]), p0[1] + f*(p1[1] - p0[1])))
        return pts

    p1 = Polygon([t1_aeqd.transform(x, y) for x, y in sample_poly(box1_utm, n_samples)])
    p2 = Polygon([t2_aeqd.transform(x, y) for x, y in sample_poly(box2_utm, n_samples)])
    d_m = p1.distance(p2)
    print(f"  n_samples={n_samples:3d} per edge: distance = {d_m:.6f} m ({d_m/1000.0:.6f} km)")

# Test vertex ordering: clockwise vs counter-clockwise
print("\n=== SENSITIVITY TEST: VERTEX ORDERING (CW vs CCW) ===")
coords_cw = [(e1 - half_m, n1 - half_m), (e1 - half_m, n1 + half_m), (e1 + half_m, n1 + half_m), (e1 + half_m, n1 - half_m)]
coords_ccw = [(e1 - half_m, n1 - half_m), (e1 + half_m, n1 - half_m), (e1 + half_m, n1 + half_m), (e1 - half_m, n1 + half_m)]
p1_cw = Polygon([t1_aeqd.transform(x, y) for x, y in coords_cw])
p1_ccw = Polygon([t1_aeqd.transform(x, y) for x, y in coords_ccw])
p2 = Polygon([t2_aeqd.transform(x, y) for x, y in box2_utm.exterior.coords])
d_cw = p1_cw.distance(p2)
d_ccw = p1_ccw.distance(p2)
print(f"  CW distance:  {d_cw:.6f} m")
print(f"  CCW distance: {d_ccw:.6f} m")
print(f"  Difference:   {abs(d_cw - d_ccw):.10f} m")

# Test transformation ordering: (lon, lat) -> UTM -> AEQD vs (lon, lat) -> AEQD
print("\n=== SENSITIVITY TEST: TRANSFORMATION ORDERING ===")
# Direct WGS84 -> AEQD:
t_wgs_to_aeqd = Transformer.from_crs("EPSG:4326", aeqd_crs, always_xy=True)
# Footprint defined in UTM, then reprojected UTM -> WGS84 -> AEQD
t_utm_to_wgs = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)
wgs_coords1 = [t_utm_to_wgs.transform(x, y) for x, y in box1_utm.exterior.coords]
wgs_coords2 = [t_utm_to_wgs.transform(x, y) for x, y in box2_utm.exterior.coords]
p1_via_wgs = Polygon([t_wgs_to_aeqd.transform(x, y) for x, y in wgs_coords1])
p2_via_wgs = Polygon([t_wgs_to_aeqd.transform(x, y) for x, y in wgs_coords2])
d_via_wgs = p1_via_wgs.distance(p2_via_wgs)
print(f"  UTM -> AEQD:              {d_ccw:.6f} m")
print(f"  UTM -> WGS84 -> AEQD:     {d_via_wgs:.6f} m")
print(f"  Difference:               {abs(d_ccw - d_via_wgs):.10f} m")
