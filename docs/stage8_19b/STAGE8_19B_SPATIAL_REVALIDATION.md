# Stage 8.19B — Footprint-Aware Spatial Revalidation & Leakage Audit

## Executive Summary

Stage 8.19B upgrades the cross-validation spatial split protocol from a center-based point approximation to a **geodesically rigorous, footprint-aware edge-to-edge isolation model**.

Using the WGS84 ellipsoid and the exact physical boundaries of all $5.12\text{ km} \times 5.12\text{ km}$ candidate chip footprints ($26.21\text{ km}^2$), the cross-validation assignment has been re-clustered and re-balanced.

### Key Audit Metrics in Manifest v3:
| Metric | Center-Based Split (v2) | Footprint-Aware Split (v3) | Target Standard | Status |
|:---|:---:|:---:|:---:|:---:|
| **Minimum Edge-to-Edge Distance** | $43.8213\text{ km}$ | **$\mathbf{50.0079\text{ km}}$** | $> 50.0000\text{ km}$ | **PASS** |
| **Footprint Edge Violations ($\le 50.0\text{ km}$)** | 9 pairs | **0 pairs** | 0 pairs | **PASS** |
| **Minimum Center-to-Center Distance** | $50.1595\text{ km}$ | **$\mathbf{55.5971\text{ km}}$** | $> 50.0000\text{ km}$ | **PASS** |
| **Expansion Fold Distribution** | 47 / 47 / 47 / 47 / 47 | **47 / 47 / 47 / 47 / 47** | Exactly 47 per fold | **PASS** |
| **Pilot Benchmark Isolation** | 15 chips held out | **15 chips held out** | Held out outside CV | **PASS** |
| **MGRS Tile Splits Across Folds** | 0 | **0** | 0 splits | **PASS** |
| **Physical Incident Splits Across Folds** | 0 | **0** | 0 splits | **PASS** |

---

## 1. Footprint Geometry & Geodesic Methodology

### 1.1 Physical Chip Geometry
Every Sentinel-2 chip in DS08 is specified as:
- **Raster Width $\times$ Height:** $512 \times 512$ pixels
- **Ground Sampling Distance (GSD):** $10.0\text{ m}$
- **Ground Footprint Dimensions:** $5,120\text{ m} \times 5,120\text{ m}$ ($5.12\text{ km} \times 5.12\text{ km}$)
- **Area:** $26.2144\text{ km}^2$

For each chip center $(\text{lat}_c, \text{lon}_c)$, the four bounding corner coordinates $(\text{lat}_i, \text{lon}_i)$ are computed on the WGS84 ellipsoid ($a = 6378137.0\text{ m}, f = 1/298.257223563$) using direct geodesic projection:
$$\text{North Half-Step: } 2,560\text{ m at azimuth } 0^\circ, \quad \text{South Half-Step: } 2,560\text{ m at azimuth } 180^\circ$$
$$\text{East Half-Step: } 2,560\text{ m at azimuth } 90^\circ, \quad \text{West Half-Step: } 2,560\text{ m at azimuth } 270^\circ$$

The resulting bounding polygon $\mathcal{P}_i$ defines the continuous physical territory imaged by the sensor.

### 1.2 Inter-Footprint Geodesic Distance
The distance between two chips $A$ and $B$ is the minimum geodesic distance between any point on $\mathcal{P}_A$ and any point on $\mathcal{P}_B$:
$$D_{\text{edge}}(A, B) = \min_{\mathbf{p}_A \in \mathcal{P}_A, \, \mathbf{p}_B \in \mathcal{P}_B} \text{GeodesicWGS84}(\mathbf{p}_A, \mathbf{p}_B)$$

Because both footprints are convex polygons, $D_{\text{edge}}$ is computed by evaluating the pairwise geodesic distance between all corner vertices and edge segments.

---

## 2. Spatial Graph Construction & Percolation Analysis

A graph $\mathcal{G} = (\mathcal{V}, \mathcal{E})$ was constructed over all 235 expansion candidates ($\mathcal{V} = \{1, \dots, 235\}$):

$$\{i, j\} \in \mathcal{E} \iff \begin{cases}
\text{incident\_id}_i = \text{incident\_id}_j & \text{(Incident Grouping Axiom)} \\
\text{stac\_scene\_id}_i = \text{stac\_scene\_id}_j & \text{(Scene / Tile Grouping Axiom)} \\
D_{\text{edge}}(i, j) \le 50.0000\text{ km} & \text{(Footprint Edge Buffer Rule)}
\end{cases}$$

### Graph Analysis Findings:
- **Total Connected Components:** 190 clusters
- **Cluster Size Breakdown:**
  - Size 1 (isolated chips): 165 clusters (86.8%)
  - Size 2: 15 clusters (7.9%)
  - Size 3: 5 clusters (2.6%)
  - Size 4: 2 clusters (1.1%)
  - Size 5: 1 cluster (0.5%)
  - Size 6: 2 clusters (1.1%)
- **Maximum Cluster Size:** **6 chips** (only $2.56\%$ of the 235 expansion candidates).
- **Percolation Verification:** Graph percolation ratio is $2.56\% \ll 20.0\%$. Zero percolation occurs across India, confirming that a 50 km edge-to-edge buffer is fully compatible with balanced cross-validation.

---

## 3. Stratified Bin-Packing & Fold Allocation

The 190 clusters were sorted in descending order of size and packed into 5 cross-validation folds using greedy stratified bin-packing with capacity constraint $C_k = 47$:

| Stratum ID | Stratum Name | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Fold 5 | Held-Out Benchmark | Total Chips |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **STR-1** | Confirmed Acute Industrial Fires | 1 | 1 | 2 | 4 | 2 | 0 | **10** |
| **STR-2** | Persistent Non-Biomass Thermal | 9 | 6 | 6 | 8 | 6 | 0 | **35** |
| **STR-3** | Active Forest Wildfires | 11 | 12 | 9 | 11 | 12 | 0 | **55** |
| **STR-4** | Agricultural Crop Residue Burns | 9 | 11 | 13 | 10 | 12 | 0 | **55** |
| **STR-5** | Industrial Negative Controls | 9 | 9 | 9 | 7 | 6 | 0 | **40** |
| **STR-6** | Natural & Agri Negative Controls | 8 | 8 | 8 | 7 | 9 | 0 | **40** |
| **STR-7** | Pilot Benchmark Cohort (Frozen) | 0 | 0 | 0 | 0 | 0 | 15 | **15** |
| **Total** | | **47** | **47** | **47** | **47** | **47** | **15** | **250** |

### Accounting Confirmation:
- **Each CV fold contains exactly 47 chips** ($47 \times 5 = 235$).
- **Benchmark stratum contains exactly 15 chips** ($235 + 15 = 250$).
- **Stratum representation is balanced across all folds.**

---

## 4. Empirical Spatial Separation Audit

Pairwise distances between all chips assigned to different cross-validation folds were audited:

### 4.1 Minimum Distances
- **Minimum Footprint Edge-to-Edge Distance:** **$50.0079\text{ km}$**
  - *Closest Cross-Fold Pair:* `DS08_EXP_S4_018` (Fold 4, Agricultural Burn in UP) vs `DS08_EXP_S5_016` (Fold 3, Industrial Negative Control in UP).
- **Minimum Center-to-Center Geodesic Distance:** **$55.5971\text{ km}$**
  - *Closest Cross-Fold Pair:* `DS08_EXP_S3_004` (Fold 2) vs `DS08_EXP_S4_004` (Fold 4).
- **Cross-Fold Pairs with Edge Distance $\le 50.0\text{ km}$:** **0 pairs**.

### 4.2 Distance Distribution Between Different Folds:
```
Cross-Fold Separation Histogram (22,090 inter-fold pairs):
  [  0.0 km -  50.0 km]: 0 pairs (PASS: ZERO LEAKAGE)
  [ 50.0 km - 100.0 km]: 24 pairs
  [100.0 km - 250.0 km]: 298 pairs
  [         > 250.0 km]: 21,768 pairs
```

---

## 5. MGRS Tile & Physical Incident Grouping Verification

1. **MGRS Tile Grouping:**
   - Any chips residing in the same Sentinel-2 MGRS grid tile share common atmospheric and sensor swath characteristics.
   - Result: All chips from any single MGRS tile are assigned to the identical fold. **0 MGRS tile splits exist across folds.**
2. **Physical Incident Grouping:**
   - Any chips originating from the same physical industrial disaster or ground incident are hard-locked to the same fold, ensuring zero temporal leakage between multi-temporal passes.
   - Result: **0 incident splits exist across folds.**

---

## 6. Audit Script Reproducibility

The spatial revalidation is fully automated and reproducible via:
```bash
python scripts/audit_stage8_19b_spatial_footprint.py
```
**Status: Certified 100% PASS.**
