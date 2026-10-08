# Stage 8.33: Generalization Gap Forensic Audit

**Scope:** Development Cohort Only ($N=131$: Train $N=107$, Val $N=24$)  
**Protocol:** Zero Access to Frozen 2026 Test Set (`FROZEN_TEST_ACCESS_STAGE_8_33 = FALSE`)  
**Objective:** Explain why development cross-validation achieves high performance (Random: 100%, Spatial CV: 87.79%) while unseen test distributions encounter generalization barriers.

---

## 1. Development Cohort Composition

- **Total Development Events:** 131 (Train: 107, Validation: 24)
- **Class Breakdown:**
  - Other / Persistent: 42 (32.1%)
  - Industrial Fire: 35 (26.7%)
  - Forest Fire: 27 (20.6%)
  - Agricultural Fire: 27 (20.6%)

- **Temporal Breakdown:**
  - 2016–2020: 26 events (19.8%)
  - 2021–2023: 32 events (24.4%)
  - 2024: 49 events (37.4%)
  - 2025: 24 events (18.3%)

---

## 2. Spatial Clustering and Proximity Analysis

An audit of pairwise geodetic distances across all development events reveals:
- **Events within 1 km of each other:** 8 pairs
- **Events within 5 km of each other:** 16 pairs
- **Cross-split pairs within 5 km (Train $\leftrightarrow$ Val):** 10 pairs

### Root Cause of Overly Optimistic Random-Split Validation:
When events within 1–5 km of each other are randomly assigned to train and validation folds, the model encounters near-identical feature representations (identical historical recurrence histograms, identical nearest-facility distances, identical ecoregion biomes). This allows naive models to achieve **100% validation accuracy** through spatial co-location leakage rather than learning general physical fire dynamics.

---

## 3. Severe Regional Class Asymmetry

Cross-tabulation of spatial macro-regions against fire classes illustrates marked geographical specialization:

| Macro-Region | Agricultural | Forest | Industrial | Persistent | Total | Primary Dynamic |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **North** (Lat $\ge 26.0$) | 23 | 9 | 6 | 7 | 45 | **85.2% of all Agricultural fires** (Indo-Gangetic crop burning) |
| **Central East** ($20 \le \text{lat} < 26$, $\text{lon} \ge 78$) | 1 | 8 | 4 | 22 | 35 | **62.9% Persistent** (Eastern coalfield anomalies & central forests) |
| **South** (Lat $< 20.0$) | 0 | 8 | 17 | 7 | 32 | **53.1% Industrial**, **0% Agricultural** (Southern manufacturing hubs) |
| **Central West** ($20 \le \text{lat} < 26$, $\text{lon} < 78$) | 3 | 2 | 8 | 6 | 19 | Western petrochemical & industrial complexes |

### Generalization Implication:
- Holding out the **North** region removes almost the entirety of agricultural training support (leaving only 4 agricultural examples across Central regions).
- Holding out the **South** evaluates a region with zero agricultural fires, testing whether the model falsely invents agricultural predictions where none exist.
- Models relying on latitude/longitude coordinates (`centroid_lat`, `centroid_lon`) memorize this regional clustering instead of learning invariant physical signals.

---

## 4. Key Physical Feature Shifts (Train 2018–2024 vs Val 2025)

Standardized shift ($d = (\mu_{val} - \mu_{train}) / \sigma_{pooled}$) across validation periods:

| Feature | Train Mean $\pm$ Std | Val Mean $\pm$ Std | Standardized Shift ($d$) |
|:---|:---:|:---:|:---:|
| `current_frp` | 17.864 $\pm$ 16.943 | 16.74 $\pm$ 14.582 | -0.07 |
| `current_delta_ti` | 38.511 $\pm$ 8.661 | 39.238 $\pm$ 9.677 | +0.08 |
| `dist_to_fac_km` | 136.679 $\pm$ 173.654 | 101.222 $\pm$ 89.948 | -0.26 |
| `within_1km_fac` | 0.234 $\pm$ 0.425 | 0.083 $\pm$ 0.282 | -0.42 |
| `hist_count_2km` | 6.551 $\pm$ 12.218 | 7.458 $\pm$ 17.903 | +0.06 |
| `hist_active_days_full` | 6.028 $\pm$ 10.707 | 5.5 $\pm$ 12.283 | -0.05 |
| `hist_distinct_calendar_months` | 1.243 $\pm$ 1.878 | 0.917 $\pm$ 1.666 | -0.18 |
| `forest_biome_score` | 0.393 $\pm$ 0.491 | 0.583 $\pm$ 0.504 | +0.38 |
| `agri_heartland_score` | 0.196 $\pm$ 0.399 | 0.083 $\pm$ 0.282 | -0.33 |

---

## 5. Summary of Generalization Gap Drivers

1. **Spatial Leakage in Non-Spatial Splits:** Random cross-validation permits geographically co-located events to bleed across partitions, masking vulnerability to unseen regions.
2. **Metric Sensitivity on Small Cohorts:** On $N=28$, each misclassification represents 3.57% accuracy. Even a model with 85%+ generalization potential can score 78.57% due to just two ambiguous threshold edge-cases.
3. **Persistent vs. Industrial Near-Facility Disentanglement:** Continuous flares situated directly inside refinery complexes share `dist_to_fac_km < 1 km`. Without dedicated recurrence weighting, models prioritize facility proximity over multi-year recurrence history.
4. **Forest vs. Agricultural Diurnal & Intensity Overlap:** Moderate-intensity forest fires in winter/spring have similar instantaneous FRP (5–20 MW) to stubble burning, requiring temporal overpass history and biome context to separate.
5. **Direct Coordinate Memorization:** Features such as `centroid_lat` and `centroid_lon` allow neural networks to fit geographic boundaries rather than transferable thermal physics.

---
*Generated autonomously under Stage 8.33 strict test-lock constraints.*
