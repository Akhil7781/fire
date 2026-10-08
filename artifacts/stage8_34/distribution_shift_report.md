# Stage 8.34 - Distribution Shift Forensic Audit Report

## 1. Spatial Distribution Shift: $P(\text{class} \mid \text{region})$

A complete cross-tabulation across geographic macro-regions in India ($N=131$ dev events):

| Region | Agricultural Fire | Forest Fire | Industrial Fire | Persistent / Other | Total Events | Dominant Class |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **North** (Lat $\ge 26^\circ$) | **23** (51.1%) | 9 (20.0%) | 6 (13.3%) | 7 (15.6%) | 45 | Agricultural (51.1%) |
| **Central_East** (Lat $20^\circ-26^\circ$, Lon $\ge 78^\circ$) | 1 (2.9%) | 8 (22.9%) | 4 (11.4%) | **22** (62.9%) | 35 | Persistent (62.9%) |
| **Central_West** (Lat $20^\circ-26^\circ$, Lon $< 78^\circ$) | 3 (15.8%) | 2 (10.5%) | **8** (42.1%) | 6 (31.6%) | 19 | Industrial (42.1%) |
| **South** (Lat $< 20^\circ$) | **0** (0.0%) | 8 (25.0%) | **17** (53.1%) | 7 (21.9%) | 32 | Industrial (53.1%) |
| **Total** | **27** | **27** | **35** | **42** | **131** | - |

### Key Spatial Vulnerabilities:
1. **Severe Regional Specialization:**
   - **85.19% of Agricultural Fires** (23 out of 27) are located in the **North** region (Punjab / Haryana crop burning belt).
   - **52.38% of Persistent Thermal Sources** (22 out of 42) are concentrated in the **Central_East** coalfield belts (Jharia, Raniganj, Dhanbad).
   - **48.57% of Industrial Fires** (17 out of 35) are in the **South** region.
   - **Zero Agricultural Fires** exist in the South development cohort.
2. **Impact on Spatial Cross-Validation:**
   - When **North** is held out as the outer test fold:
     - Outer Train has only **4 agricultural fire events** across all of Central and South India.
     - Outer Test has **23 agricultural fire events**.
     - The classifier has virtually no agricultural training data, resulting in poor Agricultural recall on the North fold.
   - This explains why **North is universally the worst spatial fold** across every tested architecture in Stage 8.33.
3. **The Hazard of Raw Coordinate Features:**
   - If raw coordinates (`centroid_lat`, `centroid_lon`) are provided to a neural network, the network effortlessly exploits them as a proxy shortcut ($Lat > 26^\circ \implies Agricultural$, $Lat < 20^\circ \implies Industrial$).
   - In cross-regional deployment, this shortcut collapses. **Raw coordinates must therefore be excluded from the primary model.**

---

## 2. Temporal Distribution Shift: $P(\text{class} \mid \text{year})$

| Year | Agricultural Fire | Forest Fire | Industrial Fire | Persistent / Other | Total |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 2016 | 1 | 2 | 1 | 0 | 4 |
| 2017 | 1 | 0 | 1 | 0 | 2 |
| 2018 | 1 | 1 | 2 | 0 | 4 |
| 2019 | 2 | 2 | 3 | 0 | 7 |
| 2020 | 2 | 2 | 5 | 0 | 9 |
| 2021 | 3 | 3 | 5 | 0 | 11 |
| 2022 | 3 | 3 | 4 | 0 | 10 |
| 2023 | 3 | 3 | 5 | 0 | 11 |
| **2024** | 4 | 4 | 5 | **36** | **49** |
| **2025** | 7 | 7 | 4 | **6** | **24** |
| **Total** | 27 | 27 | 35 | **42** | **131** |

### Key Temporal Vulnerabilities:
1. **The 2024 Persistent Label Discontinuity:**
   - 2016–2023: Zero persistent source labels collected.
   - 2024: 36 persistent source labels added.
   - 2025: 6 persistent source labels added.
2. **Consequence:** Forward-chaining splits before 2024 cannot train on Persistent sources. Only the Train $\le 2024 \to$ Val 2025 split possesses valid 4-class data in both train and validation partitions.

---

## 3. Recommended Pipeline Adjustments
1. **Feature Exclusion:** Exclude `centroid_lat` and `centroid_lon` from primary input representations to prevent regional memorization.
2. **Modality Reliance:** Force the network to rely on physical land cover (`forest_biome_score`, `agri_heartland_score`), thermal dynamics (`delta_ti`, `frp`, `is_night`), and historical recurrence (`hist_total_detections`, `hist_active_days_span`, etc.) rather than spatial coordinates.
3. **Temporal Benchmark Definition:** Standardize on Train $\le 2024 \to$ Val 2025 as the single canonical temporal validation partition.
