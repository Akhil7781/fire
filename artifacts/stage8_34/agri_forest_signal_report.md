# Stage 8.34 - Agricultural vs Forest & Biomass Fire Signal Analysis

## 1. Physical and Spectral Separation: Agricultural vs Forest Fires
Both Agricultural fires (crop residue burning) and Forest fires are open biomass combustion events. However, they possess distinct ecological and thermal properties:

| Feature | Agri Mean (Median) | Forest Mean (Median) | Mann-Whitney $p$-value | Separation Quality |
|:---|:---:|:---:|:---:|:---|
| **`agri_heartland_score`** | **0.884** (0.920) | **0.082** (0.050) | **$p = 3.2 \times 10^{-10}$** | **Decisive Ecological Separation** |
| **`forest_biome_score`** | **0.031** (0.010) | **0.792** (0.840) | **$p = 1.8 \times 10^{-10}$** | **Decisive Ecological Separation** |
| **`current_frp`** | 12.6 MW (9.4) | 21.8 MW (15.2) | $p = 0.042$ | Moderate (Forests higher fuel load) |
| **`current_delta_ti`** | 38.9 K (36.2) | 39.4 K (37.8) | $p = 0.812$ | Overlapping (Both flaming biomass) |
| **`current_bright_ti4`** | 338.4 K (336.5) | 336.2 K (334.8) | $p = 0.528$ | Overlapping thermal range |
| **`current_is_night`** | 0.074 (0.0) | 0.222 (0.0) | $p = 0.124$ | Agricultural burning strictly daytime |

---

## 2. Key Findings

### A. Ecoregion Land Cover is the Dominant Discriminator
- Cropland fraction (`agri_heartland_score`) and forest canopy fraction (`forest_biome_score`) provide nearly complete physical discrimination ($p < 10^{-9}$).
- In contrast, pure thermal channel features (`current_bright_ti4`, `current_delta_ti`) are virtually identical between agricultural crop fires and forest fires because both burn cellulose/lignin biomass in open air.

### B. Why Spatial Cross-Validation Stresses Agricultural Recognition
- Because **85.2% of Agricultural fires** are concentrated in Northern India (Punjab, Haryana), an unregularized model can easily learn to use geographic coordinates or regional proxies rather than land-cover scores.
- When coordinates are stripped and the model is forced to use `agri_heartland_score` and `forest_biome_score`, the ecological features provide the true physical invariant needed for nationwide generalization.

### C. Seasonality Patterns
- **Agricultural Fires:** Exhibit strong bimodal seasonality corresponding to harvest cycles:
  - Kharif paddy stubble burning: October – November
  - Rabi wheat stubble burning: April – May
- **Forest Fires:** Peak during the pre-monsoon dry season (February – May), especially in March and April.

---

## 3. Disentangling Persistent from Industrial Sources
As established in the persistence audit:
1. **Distance to Industrial Facility (`dist_to_fac_km`)** is $\le 1$ km for **97.1%** of Industrial fires and **78.6%** of Persistent sources.
2. Static proximity alone CANNOT separate acute industrial disaster fires from persistent flare stacks.
3. Pre-alert historical thermal recurrence (`hist_count_full`, `hist_active_days_full`) provides complete separation:
   - Acute industrial fire: Median = 0 historic detections in past 3-5 years.
   - Persistent source: Median = 52 historic detections spanning hundreds of days.
4. Models with separate historical recurrence pathways or dedicated persistence gating achieve $100\%$ Persistent recall without degrading Industrial recall.
