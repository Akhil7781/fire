# Stage 8.19G — Spatial Metric Validation and Footprint Geometry Audit

**Date:** 2026-10-03  
**Auditor / Reviewer Role:** Senior Geospatial Validation Engineer, Computational Geometry Specialist & Remote-Sensing Scientist  
**Workspace:** `d:/DATA PREPROCESSING`  
**Manifest Under Audit:** `data/reference/ds08/manifests/stage8_19e/ds08_expansion_candidates_v4.json`  
**Predecessor Reports:** `docs/stage8_19f/STAGE8_19F_FINAL_EVIDENCE_AUDIT.md`, `docs/stage8_19f/STAGE8_19F_SPATIAL_REPRODUCTION.json`  
**Result Status:** **REFERENCE_METRIC_CONFIRMED**

---

## 1. Executive Summary

Stage 8.19G conducted an independent micro-audit of the spatial separation metrics used in Stages 8.19D, 8.19E, and 8.19F. The objective was to determine whether the reported cross-fold separation of **50.101722 km** was derived using a mathematically valid footprint-to-footprint distance metric, or whether it relied on a corner/centroid approximation that could conceal sub-50 km violations.

A rigorous reference metric was designed and implemented:
1. Every $5.12\text{ km} \times 5.12\text{ km}$ candidate chip was constructed in its native UTM grid geometry as a planar polygon.
2. For each pair of candidates, a pair-specific **Azimuthal Equidistant (AEQD)** projection centered at their geographic midpoint was constructed, preserving radial distances with less than $13\text{ cm}$ distortion over 50 km.
3. The true minimum Euclidean distance between the two polygons was evaluated via `shapely.geometry.Polygon.distance()` (GEOS C-library), evaluating the infimum distance across all interior and boundary points.

Evaluation across all **22,090 cross-fold pairs** confirms:
* **Violations $\le 50.000000\text{ km}$:** Exactly **0**
* **Global Minimum Separation:** **50.101722 km** ($50,101.72\text{ m}$)
* **Closest Pair:** `DS08_EXP_S3_004` (Fold 2) $\longleftrightarrow$ `DS08_EXP_S4_004` (Fold 4)
* **Margin Above 50.0 km Threshold:** **+101.72 meters**
* **Metric Classification:** **CASE A — Equivalent (`REFERENCE_METRIC_CONFIRMED`)**

---

## 2. Baseline Integrity

Before running any script or creating new artifacts, baseline SHA-256 hashes were verified:
* `data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json`: `dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848` (**EXACT MATCH, FROZEN**)
* `data/reference/ds08/manifests/stage8_19e/ds08_expansion_candidates_v4.json`: `54154edcd0189545c2d03615827f834be91d2452767cef0a1d8978d3b4d9d62c`
* `docs/stage8_19e/STAGE8_19E_RECONCILED_MANIFEST_V4.json`: `54154edcd0189545c2d03615827f834be91d2452767cef0a1d8978d3b4d9d62c`
* `scripts/stage8_20_pilot_acquisition.py`: `1352f568fce72f411209587adaff8d286441edbd83e4749475a04929c87450a1`

---

## 3. Analysis of Stage 8.19D/E/F Spatial Implementations

Inspection of existing repository scripts revealed the exact methods previously employed:

### 3.1 `scripts/audit_stage8_19b_spatial_footprint.py`
* **Implementation:** Lines 34–41:
  ```python
  def footprint_edge_distance_km(geod: Geod, poly1: List[Tuple[float, float]], poly2: List[Tuple[float, float]]) -> float:
      min_d = 999999999.0
      for x1, y1 in poly1:
          for x2, y2 in poly2:
              _, _, d = geod.inv(x1, y1, x2, y2)
              if d < min_d:
                  min_d = d
      return min_d / 1000.0
  ```
* **Audit Finding:** Despite the function name `footprint_edge_distance_km`, `poly1` and `poly2` were 4-element lists of corner coordinates produced by `get_footprint_corners()`. This was strictly a **4-corner-to-4-corner geodesic check** (16 pairwise distance evaluations), not a continuous edge or polygon check.

### 3.2 `tests/test_ds08_stage8_19e_audit.py`
* **Implementation:** Lines 125–129:
  ```python
  def min_dist(cid1, cid2):
      c1 = corners[cid1]
      c2 = corners[cid2]
      return min(geod.inv(x1, y1, x2, y2)[2] for x1, y1 in c1 for x2, y2 in c2) / 1000.0
  ```
* **Audit Finding:** Similar to 8.19B, `corners` contained only the 4 reprojected footprint corners. This was a corner-to-corner geodesic approximation.

### 3.3 `scratch/run_spatial_reproduction.py` (Stage 8.19F)
* **Implementation:** Computed corner distance for all pairs, and for candidate pairs with distance $< 55.0\text{ km}$, evaluated 30 sample points along each edge (`get_densified_edges_wgs84`).
* **Audit Finding:** A significant improvement over corner-only, but still a discrete point approximation rather than a true continuous polygon-to-polygon metric.

---

## 4. Required Reference Metric Definition and Mathematical Formulation

To eliminate all approximation risks, the Stage 8.19G reference metric was defined and implemented as follows:

### 4.1 Native Grid Construction
Each Sentinel-2 chip represents $512 \times 512$ pixels at $10\text{ m}$ Ground Sampling Distance (GSD), spanning exactly $5120\text{ m} \times 5120\text{ m}$ in physical extent. The chip bounding box is defined in the candidate's native UTM projection (determined by MGRS UTM zone, EPSG:32642 to 32645):
$$\mathcal{B}_{\text{native}} = [E_0 - 2560\text{ m}, E_0 + 2560\text{ m}] \times [N_0 - 2560\text{ m}, N_0 + 2560\text{ m}]$$

### 4.2 Pair-Specific Common Projected CRS (AEQD)
To compare two chips $(C_1, C_2)$ that may reside in different UTM zones or separated across India:
1. Compute the geographic midpoint:
   $$\lambda_{\text{mid}} = \frac{\lambda_1 + \lambda_2}{2}, \quad \phi_{\text{mid}} = \frac{\phi_1 + \phi_2}{2}$$
2. Construct a pair-specific **Azimuthal Equidistant (AEQD)** projection:
   $$\text{CRS}_{\text{pair}} = \texttt{+proj=aeqd +lat\_0=}\phi_{\text{mid}}\texttt{ +lon\_0=}\lambda_{\text{mid}}\texttt{ +datum=WGS84 +units=m}$$
3. **Distortion Proof:** In an AEQD projection centered at the pair midpoint, radial distances from the origin are preserved exactly ($k_r = 1.000000$). For two chips separated by $\sim 50\text{ km}$, each chip is approximately $25\text{ km}$ from the origin. The tangential scale distortion at radius $r = 25\text{ km}$ is:
   $$k_\theta = \frac{r/R}{\sin(r/R)} \approx 1 + \frac{1}{6}\left(\frac{r}{R}\right)^2 \approx 1 + \frac{1}{6}\left(\frac{25000}{6371000}\right)^2 \approx 1 + 2.57 \times 10^{-6}$$
   Across a $50\text{ km}$ distance, this scale factor introduces an upper-bound distortion of at most:
   $$50,000\text{ m} \times 2.57 \times 10^{-6} \approx 0.128\text{ meters} \quad (\approx 13\text{ cm})$$
   This is three orders of magnitude smaller than the chip pixel resolution ($10\text{ m}$) and completely negligible relative to the $+101.72\text{ m}$ compliance margin.

### 4.3 True Polygon-to-Polygon Euclidean Distance
Both footprints are reprojected from their native UTM zones into $\text{CRS}_{\text{pair}}$ as `shapely.geometry.Polygon` objects. The distance is evaluated using GEOS:
$$D_{\text{reference}}(P_1, P_2) = \inf_{p \in P_1, q \in P_2} \|p - q\|_2$$
This evaluates the exact mathematical infimum between any point on $P_1$ (corners, boundary edges, and interior) and any point on $P_2$.

---

## 5. Full Evaluation Across All 22,090 Cross-Fold Pairs

The reference algorithm was executed across all 22,090 cross-fold pairs in Manifest v4:

| Metric | Stage 8.19F Reported | Stage 8.19G True Polygon Reference | Discrepancy |
| :--- | :---: | :---: | :---: |
| **Cross-Fold Candidate Pairs** | 22,090 | 22,090 | 0 |
| **Violations ($\le 50.000000\text{ km}$)** | **0** | **0** | **0** |
| **Global Minimum Separation** | **50.101722 km** | **50.101722 km** | **0.000000 km** |
| **Globally Closest Pair** | `DS08_EXP_S3_004` $\leftrightarrow$ `DS08_EXP_S4_004` | `DS08_EXP_S3_004` $\leftrightarrow$ `DS08_EXP_S4_004` | Identical |
| **Margin Above 50.0 km Threshold** | **+101.72 m** | **+101.72 m** | **0.00 m** |
| **Pairs Separated by $< 55.0\text{ km}$** | **13** | **13** | **0** |

### Top 13 Closest Pairs (Reference Metric):
1. `DS08_EXP_S3_004` (Fold 2) $\leftrightarrow$ `DS08_EXP_S4_004` (Fold 4): **50.101722 km** (Zones: 43N, 43N)
2. `DS08_EXP_S3_001` (Fold 4) $\leftrightarrow$ `DS08_EXP_S6_004` (Fold 3): **51.176847 km** (Zones: 43N, 43N)
3. `DS08_EXP_S2_017` (Fold 4) $\leftrightarrow$ `DS08_EXP_S6_019` (Fold 1): **51.508270 km** (Zones: 44N, 44N)
4. `DS08_EXP_S5_028` (Fold 5) $\leftrightarrow$ `DS08_EXP_S6_026` (Fold 1): **51.572741 km** (Zones: 45N, 45N)
5. `DS08_EXP_S3_022` (Fold 4) $\leftrightarrow$ `DS08_EXP_S6_010` (Fold 3): **52.394256 km** (Zones: 44N, 44N)
6. `DS08_EXP_S1_004` (Fold 3) $\leftrightarrow$ `DS08_EXP_S3_053` (Fold 4): **52.713782 km** (Zones: 42N, 43N)
7. `DS08_EXP_S2_023` (Fold 1) $\leftrightarrow$ `DS08_EXP_S3_034` (Fold 5): **52.737481 km** (Zones: 43N, 43N)
8. `DS08_EXP_S3_006` (Fold 3) $\leftrightarrow$ `DS08_EXP_S4_011` (Fold 2): **53.555523 km** (Zones: 42N, 42N)
9. `DS08_EXP_S1_005` (Fold 4) $\leftrightarrow$ `DS08_EXP_S4_001` (Fold 3): **53.646979 km** (Zones: 43N, 43N)
10. `DS08_EXP_S3_055` (Fold 2) $\leftrightarrow$ `DS08_EXP_S5_036` (Fold 1): **53.976233 km** (Zones: 43N, 43N)
11. `DS08_EXP_S2_011` (Fold 1) $\leftrightarrow$ `DS08_EXP_S5_010` (Fold 3): **54.105569 km** (Zones: 44N, 44N)
12. `DS08_EXP_S4_005` (Fold 5) $\leftrightarrow$ `DS08_EXP_S6_008` (Fold 1): **54.668989 km** (Zones: 43N, 43N)
13. `DS08_EXP_S2_032` (Fold 1) $\leftrightarrow$ `DS08_EXP_S5_038` (Fold 2): **54.686238 km** (Zones: 43N, 43N)

---

## 6. Known Closest-Pair Detailed Analysis (Section 9)

### 6.1 `DS08_EXP_S3_004` vs `DS08_EXP_S4_004`
* **Candidate 1:** `DS08_EXP_S3_004` (Fold 2, Forest Fire, MGRS `T43SEN`, lat: 30.85742, lon: 74.37711)
* **Candidate 2:** `DS08_EXP_S4_004` (Fold 4, Agricultural Fire, MGRS `T43SDN`, lat: 30.79358, lon: 73.80075)
* **Center Geodesic Distance:** **55.597099 km** ($55,597.10\text{ m}$)
* **Stage 8.19F Reported Distance:** **50.101722 km**
* **True AEQD Polygon Distance:** **50.101722 km**
* **Native UTM Zone 43 Euclidean Polygon Distance:** **50.086504 km** (Difference is attributable to the UTM projection scale factor $k \approx 0.9997$ at this latitude/central meridian offset)
* **Absolute Discrepancy (8.19F vs Reference):** **0.000000 km** ($0.00\text{ mm}$)
* **Threshold Margin:** **+101.72 meters** strictly above 50.000000 km.

**Geometric Explanation for Exact Equivalence:**
The vector connecting the centers of `DS08_EXP_S3_004` and `DS08_EXP_S4_004` lies along an azimuth where the west-southwest corner of Chip 1 directly points towards the east-northeast corner of Chip 2. Because both chips are convex squares aligned to the UTM grid, the geometric infimum between the two square polygons is achieved precisely at the corner-to-corner vertex pair. Thus, the corner distance and true polygon distance coincide to sub-millimeter precision.

### 6.2 Repaired Pair Check: `DS08_EXP_S4_018` vs `DS08_EXP_S5_016`
* `DS08_EXP_S4_018`: Assigned to **Fold 3**
* `DS08_EXP_S5_016`: Assigned to **Fold 3**
* `DS08_EXP_S4_043`: Assigned to **Fold 4** (counter-swapped)
* Both previously violating candidates are now **co-located in Fold 3**. They are never evaluated as a cross-fold pair, and their minimum distance to any candidate in another fold exceeds $140\text{ km}$.

---

## 7. Numerical Sensitivity and Robustness (Section 10)

A multi-parameter sensitivity analysis was conducted on the closest pair:
* **Edge Sample Density:** Polygons constructed with 4, 10, 25, 50, 100, and 500 boundary sample points per edge evaluated to identical distances: **50101.721719 m**.
* **Vertex Ordering:** Clockwise (CW) vs Counter-Clockwise (CCW) polygon construction produced identical distances (difference = **$0.0000000000\text{ m}$**).
* **Transformation Pipeline:** Reprojecting native UTM $\rightarrow$ AEQD versus native UTM $\rightarrow$ WGS84 $\rightarrow$ AEQD produced identical distances (difference = **$0.0000000000\text{ m}$**).

---

## 8. Chip Footprint vs Product Footprint Distinction (Section 11 & 12)

* **Chip Footprint:** Defined strictly as the $5120\text{ m} \times 5120\text{ m}$ ground extent ($512 \times 512$ pixels at $10\text{ m}$ GSD) centered at the candidate coordinates in native UTM.
* **Product Footprint:** The satellite granule footprint (`GeoFootprint`, $\sim 110\text{ km} \times 110\text{ km}$) was used *only* in Stage 8.19F to confirm candidate spatial containment. It was **never conflated** with the chip footprint for the 50 km cross-fold separation rule.

---

## 9. Conclusion

The Stage 8.19F spatial separation results are **MATHEMATICALLY VALID AND REPRODUCED**:
* Global minimum separation: **50.101722 km**
* Violations $\le 50.000000\text{ km}$: **0**
* Status: **REFERENCE_METRIC_CONFIRMED**
