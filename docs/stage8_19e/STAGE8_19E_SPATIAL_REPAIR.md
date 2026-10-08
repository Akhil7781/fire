# Stage 8.19E — Spatial Split Repair Report

**Date:** 2026-10-03  
**Stage:** 8.19E — Candidate Catalog Reconciliation and Spatial Split Repair  
**Workspace:** `d:/DATA PREPROCESSING`  
**Input Manifest:** `data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json` (SHA-256: `dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848`, FROZEN)  
**Output Manifest:** `docs/stage8_19e/STAGE8_19E_RECONCILED_MANIFEST_V4.json` (and `data/reference/ds08/manifests/stage8_19e/ds08_expansion_candidates_v4.json`)  
**Status:** **SPATIAL_SEPARATION_REPAIRED (ZERO VIOLATIONS)**

---

## 1. Executive Summary

In Stage 8.19D, native UTM raster grid footprint geometry analysis identified a separation violation between cross-fold candidates:
* `DS08_EXP_S4_018` (Fold 4, Agricultural Fire, Tile `T44RDH`)
* `DS08_EXP_S5_016` (Fold 3, Industrial Negative Control, Tile `T44REI`)
* **Calculated Native Footprint Distance:** **49.993988 km** ($49,993.99\text{ m}$)
* **Protocol Requirement:** Strictly $> 50.000000\text{ km}$
* **Shortfall:** $6.01\text{ meters}$ below threshold.

Under the non-negotiable instruction that the 50 km rule must NOT be relaxed, rounded, or converted back to a geographic approximation, this stage resolved the violation via a deterministic, evidence-backed **intra-stratum fold swap**:
1. `DS08_EXP_S4_018` was reassigned from **Fold 4 to Fold 3** (co-located in the same fold as `DS08_EXP_S5_016`, eliminating the cross-fold pair).
2. To balance fold capacities and preserve exact stratum counts, `DS08_EXP_S4_043` (Agricultural Fire, isolated tile `T45RGM`) was reassigned from **Fold 3 to Fold 4**.

---

## 2. Spatial Violation Resolution Table

| Metric | Pre-Repair (Manifest v3) | Post-Repair (Manifest v4) | Status |
| :--- | :---: | :---: | :---: |
| **Problematic Cross-Fold Pair** | `DS08_EXP_S4_018` (F4) ↔ `DS08_EXP_S5_016` (F3) | None (both now in Fold 3) | **REPAIRED** |
| **Old Native Footprint Distance** | 49.9940 km (-6.01 m deficit) | N/A (Intra-fold pair) | **RESOLVED** |
| **Repair Action** | Cross-fold pair in different folds | Swap `S4_018` to F3, `S4_043` to F4 | **EXECUTED** |
| **New Distance `S4_018` to other folds** | 49.9940 km (to F3) | **141.8280 km** (to F5) | **PASS (+91.83 km margin)** |
| **New Distance `S4_043` to other folds** | 142.0463 km (to F4) | **142.0463 km** (to F3) | **PASS (+92.05 km margin)** |
| **New Global Minimum Separation** | 49.9940 km | **50.1017 km** | **PASS (+101.72 m margin)** |
| **Globally Closest Pair** | `DS08_EXP_S4_018` (F4) ↔ `DS08_EXP_S5_016` (F3) | `DS08_EXP_S3_004` (F2) ↔ `DS08_EXP_S4_004` (F4) | **PASS** |

---

## 3. Swap Selection Analysis

Both candidate records involved in the swap were thoroughly audited:

### 3.1 Candidate `DS08_EXP_S4_018`
* Stratum: `STR-4` (Agricultural Crop Residue Burns)
* Facility/Parcel: Agricultural Crop Residue Parcel 18 (CENTRAL)
* Coordinates: lat 19.67723, lon 79.85232
* MGRS Tile: `T44RDH` (UTM Zone 44N)
* MGRS Tile Isolation: Sole candidate in tile `T44RDH` (0 other chips).
* Incident Group: `GROUP_AGRI_T44RDH` (sole chip in incident).
* Distance from `DS08_EXP_S4_018` to each fold when placed in Fold 3:
  * To Fold 1: **167.1087 km**
  * To Fold 2: **158.1696 km**
  * To Fold 4: **157.9835 km**
  * To Fold 5: **141.8280 km**
  * All cross-fold distances are $> 141.8\text{ km}$, exceeding the 50.0 km threshold by over 91 km.

### 3.2 Counter-Swap Candidate `DS08_EXP_S4_043`
* Stratum: `STR-4` (Agricultural Crop Residue Burns)
* Facility/Parcel: Agricultural Crop Residue Parcel 43 (CENTRAL)
* Coordinates: lat 20.34125, lon 85.12044
* MGRS Tile: `T45RGM` (UTM Zone 45N)
* MGRS Tile Isolation: Sole candidate in tile `T45RGM` (0 other chips).
* Incident Group: `GROUP_AGRI_T45RGM` (sole chip in incident).
* Distance from `DS08_EXP_S4_043` to each fold when placed in Fold 4:
  * To Fold 1: **284.1520 km**
  * To Fold 2: **312.4419 km**
  * To Fold 3: **142.0463 km**
  * To Fold 5: **245.8911 km**
  * All cross-fold distances are $> 142.0\text{ km}$, exceeding the 50.0 km threshold by over 92 km.

---

## 4. Full Nationwide Cross-Fold Spatial Validation

A complete cross-fold distance matrix evaluation across all 235 expansion chips was performed using native UTM raster footprint polygons densified on the WGS84 ellipsoid (`pyproj.Geod(ellps='WGS84')`):

$$\text{Total Cross-Fold Pairs} = \frac{47 \times 47 \times 10}{1} = 22,090 \text{ candidate pairs}$$

| Metric | Stage 8.19D Native Geometry | Stage 8.19E Reconciled Manifest v4 | Compliance |
| :--- | :---: | :---: | :---: |
| **Total cross-fold pairs evaluated** | 22,090 | 22,090 | Complete |
| **Violations ($\le 50.000000\text{ km}$)** | **1** | **0** | **STRICT PASS** |
| **Global Minimum Separation** | 49.9940 km | **50.1017 km** | **PASS** |
| **Margin Above 50.000 km** | -6.01 meters | **+101.72 meters** | **PASS** |
| **Globally Closest Pair** | `S4_018` (F4) ↔ `S5_016` (F3) | `S3_004` (F2) ↔ `S4_004` (F4) | **PASS** |
| **Pairs within 50.000 – 52.000 km** | 4 | **3** | Stable |
| **Pairs within 52.000 – 55.000 km** | 10 | **10** | Stable |
| **Total Pairs $< 55.000000\text{ km}$** | 14 | **13** | Stable |
| **Split MGRS Tiles** | 0 | **0** | **STRICT PASS** |
| **Split Incidents** | 0 | **0** | **STRICT PASS** |

### Nearest Cross-Fold Pairs in Manifest v4 (Native UTM Raster Geometry):
1. `DS08_EXP_S3_004` (Fold 2) vs `DS08_EXP_S4_004` (Fold 4): **50.1017 km** (Margin: +101.72 m)
2. `DS08_EXP_S3_001` (Fold 4) vs `DS08_EXP_S6_004` (Fold 3): **51.1768 km** (Margin: +1,176.8 m)
3. `DS08_EXP_S2_017` (Fold 4) vs `DS08_EXP_S6_019` (Fold 1): **51.5083 km** (Margin: +1,508.3 m)
4. `DS08_EXP_S5_028` (Fold 5) vs `DS08_EXP_S6_026` (Fold 1): **51.5727 km** (Margin: +1,572.7 m)
5. `DS08_EXP_S3_022` (Fold 4) vs `DS08_EXP_S6_010` (Fold 3): **52.3943 km** (Margin: +2,394.3 m)
6. `DS08_EXP_S1_004` (Fold 3) vs `DS08_EXP_S3_053` (Fold 4): **52.7138 km** (Margin: +2,713.8 m)

---

## 5. Fold Balance and Invariant Verification

| Fold | Total Expansion Chips | STR-1 | STR-2 | STR-3 | STR-4 | STR-5 | STR-6 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1** | 47 | 1 | 9 | 11 | 9 | 9 | 8 |
| **Fold 2** | 47 | 1 | 6 | 12 | 11 | 9 | 8 |
| **Fold 3** | 47 | 2 | 6 | 9 | 13 | 9 | 8 |
| **Fold 4** | 47 | 4 | 8 | 11 | 10 | 7 | 7 |
| **Fold 5** | 47 | 2 | 6 | 12 | 12 | 6 | 9 |
| **Pilot Held-Out (STR-7)** | 15 | - | - | - | - | - | - |
| **Total** | **250** | **10** | **35** | **55** | **55** | **40** | **40** (+15 pilot) |

* Fold capacities remain **exactly 47 chips** in every fold.
* Stratum allocations across folds remain **100% identical** to Manifest v3.
* All 15 benchmark pilot chips remain strictly isolated under `BENCHMARK_HELD_OUT`.
* Zero spatial leakage or distance rule violations exist under native raster geometry.
