# Stage 8.36 Final Project Status & Technical Verification Report

## 1. Problem Statement
The DS08 Industrial/Thermal-Source Attribution Project addresses real-time classification of satellite-detected thermal anomalies across the Indian subcontinent. When NASA FIRMS detects a thermal anomaly cluster at timestamp $t_0$, operational responders require immediate attribution to differentiate acute industrial fires from agricultural stubble burning, wildfire flare-ups in forests, or harmless routine industrial/persistent thermal sources (such as steel blast furnaces, refinery flaring, or brick kilns).

Crucially, attribution must occur **at alert time ($H0$)**, strictly avoiding lookahead, retrospective metrics, or test-contaminated persistent source registries.

---

## 2. Data Sources
The project synthesizes multi-source multimodal observational data:
1. **NASA FIRMS (VIIRS & MODIS):** Active fire detections providing Fire Radiative Power (FRP), brightness temperatures (TI4, TI5), scan/track geometry, and acquisition timestamps.
2. **Industrial Facility Infrastructure:** Spatial boundary and centroid databases of Indian industrial estates, refineries, chemical zones (e.g., MIDC, GIDC, SIPCOT), power plants, and manufacturing clusters.
3. **Ecoregion & Biome Cartography:** Indian Agro-Ecological Zones, FSI forest classifications, and biogeographic heartland boundaries.
4. **Historical FIRMS Recurrence Archives (2012–2025):** 13+ years of pre-alert satellite thermal observations used for purely temporal, registry-free persistence learning.

---

## 3. Four Target Classes
The classifier resolves 4 operational classes:
- **Class 0: Industrial Fire** — Acute, non-routine industrial emergencies, chemical explosions, factory structural blazes, and refinery accidents.
- **Class 1: Forest Fire** — Wildfires and forest vegetation canopy/understory combustion.
- **Class 2: Agricultural Fire** — Crop residue burning, seasonal post-harvest stubble fires (paddy/wheat/sugarcane).
- **Class 3: Other / Persistent Thermal Source** — Normal, continuous or semi-continuous high-temperature operations (coke ovens, glassworks, cement kilns, gas flaring, coal seam anomalies).

---

## 4. Causal Feature Design
To ensure mathematical and temporal causality, features are extracted strictly at $t \le t_0$:
- **Thermal Dynamics ($D=14$):** Current FRP, brightness temperatures (TI4, TI5, Delta-TI), night detection flag, cumulative detection count, observation hours elapsed, running mean/max/std FRP, FRP trend.
- **Industrial Facility Geometry ($D=6$):** Distance to nearest facility (km), 1km/5km proximity thresholds, baseline FRP of facility, deviation from baseline, facility z-score.
- **Ecoregion Context ($D=3$):** Forest biome score, agricultural heartland score, Sentinel-2 availability flag.
- **Pre-Alert Historical Recurrence ($D=18$):** Strictly pre-alert observations ($t \le t_0 - 7$ days) across multi-year archives. Calculates spatial clustering (1km, 2km, 5km counts), temporal dispersion, active days, distinct calendar months, and recent count windows (30d, 90d, 365d).

**Scientific Exclusions:**
- Raw geographic coordinates (`centroid_lat`, `centroid_lon`) are excluded to avoid memorizing spatial positions.
- Persistent source registries (`persistent_source_manifest.json`) are forbidden and excluded.
- Associated target IDs (`associated_*`) are strictly excluded.

---

## 5. Final Neural Architecture
The final production architecture is **`Architecture1_StaticMLP`**:
- **Pure PyTorch Deep Learning** (Zero classical ML models, zero tree ensembles).
- Concatenates the 41 clean features across all 4 groups into a 41-dimensional vector.
- **Layer 1:** `Linear(41, 48)` $\to$ `LayerNorm(48)` $\to$ `GELU` $\to$ `Dropout(0.15)`.
- **Layer 2:** `Linear(48, 24)` $\to$ `LayerNorm(24)` $\to$ `GELU` $\to$ `Dropout(0.15)`.
- **Output Layer:** `Linear(24, 4)` $\to$ `Softmax(dim=-1)`.
- Total trainable parameters: **3,244**. Compact size prevents overfitting on small tabular cohorts.

---

## 6. Training Protocol
- Development cohort: $N = 165$ curated events spanning 2016–2025.
- Training split: Strictly historical events ($N = 125, \text{year} \le 2024$).
- Validation split: Year 2025 events ($N = 40$) for early stopping and temperature calibration.
- Loss function: Multi-class Focal Loss ($\gamma = 1.5$) to handle class imbalance.
- Optimizer: AdamW ($\text{lr} = 0.002, \text{weight\_decay} = 1\times 10^{-4}$), batch size 16, 45 epochs.
- Preprocessing: Standardizers (mean and std) fitted strictly on the $N=125$ training set ($\le 2024$).

---

## 7. Spatial Validation (Stage 8.35 Outer 4-Fold Spatial CV)
- **Validation Protocol:** Outer 4-fold cross-validation by geographic macro-regions (North, Central-East, Central-West, South).
- **Spatial Macro-F1:** **0.7689**
- **Spatial Accuracy:** **80.00%**
- **Worst Spatial Fold F1:** 0.7022 (Central-East)
- **Spatial Balanced Accuracy:** 79.86%

---

## 8. Temporal Validation (Canonical 2025 Forward Evaluation)
- **Validation Protocol:** Train on $\le 2024$ ($N=125$), validate on 2025 ($N=40$).
- **Temporal Accuracy:** **65.00%**
- **Temporal Macro-F1:** **0.6355**
- **Temporal Balanced Accuracy:** **66.67%**

---

## 9. Frozen 2026 Independent Benchmark (Blind Terminal Evaluation)
The frozen independent test cohort ($N=28$, Year 2026, Manifest SHA-256: `5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c`) was evaluated **EXACTLY ONCE**:

| Metric | Final 2026 Test Value | 95% Confidence Interval | Benchmark Target ($\ge 0.85$) |
|:---|:---:|:---:|:---:|
| **Overall Accuracy** | **78.57%** (22/28) | Wilson: [60.46%, 100.00%] <br> Bootstrap: [60.71%, 92.86%] | Not Achieved (78.57% < 85%) |
| **Macro-F1** | **0.8021** | Bootstrap: [0.6369, 0.9226] | Not Achieved (0.8021 < 0.85) |
| **Balanced Accuracy** | **81.67%** | Bootstrap: [65.83%, 93.75%] | Not Achieved (81.67% < 85%) |
| **Weighted-F1** | **0.7946** | — | — |

*Note on Granularity:* With $N = 28$, exactly 1 event represents **3.5714 percentage points** of accuracy.

---

## 10. Confusion Matrix ($4 \times 4$)

```
                     Industrial   Forest   Agricultural   Persistent
Industrial               6           0          0              0
Forest                   0           5          1              0
Agricultural             0           1          5              0
Persistent               0           0          4              6
```

- CSV: `artifacts/stage8_36/confusion_matrix.csv`
- Plot: `artifacts/stage8_36/confusion_matrix.png`

---

## 11. Per-Class Results Breakdown

| Class ID | Target Class | Support | Precision | Recall | F1-Score | Operational Interpretation |
|:---:|:---|:---:|:---:|:---:|:---:|:---|
| 0 | **Industrial Fire** | 6 | **1.0000** | **1.0000** | **1.0000** | Flawless sensitivity and specificity; zero false positives. |
| 1 | **Forest Fire** | 6 | **0.8333** | **0.8333** | **0.8333** | Highly reliable attribution in forested biomes (5/6 correct). |
| 2 | **Agricultural Fire** | 6 | **0.5000** | **0.8333** | **0.6250** | High recall (5/6), but incurs false positives from low-count persistent events. |
| 3 | **Persistent / Other** | 10 | **1.0000** | **0.6000** | **0.7500** | Perfect precision (1.0000); 4 low-recurrence events missed. |

---

## 12. Error Analysis (The 6 Misclassifications)

1. **`EVT_825_FOR_FOR_EVT_2026_OD_KOTGARH` (True: Forest, Pred: Agricultural)**
   - Probabilities: Agricultural 37.39%, Forest 35.82%, Persistent 15.23%, Industrial 11.56%.
   - Explanation: Extremely marginal difference (0.015). FRP was low (3.46 MW) in an edge zone between scrub forest and cultivated land.
2. **`EVT_825_AGR_AGR_EVT_2026_RJ_KOTA_RABI` (True: Agricultural, Pred: Forest)**
   - Probabilities: Forest 41.36%, Agricultural 36.27%, Industrial 13.11%, Persistent 9.26%.
   - Explanation: Kota rabi burning with high FRP (24.84 MW) near ravine/woodland margins triggered forest canopy thermal signals.
3. **`EVT_825_PER_PER_SRC_03` (True: Persistent, Pred: Agricultural)**
   - Probabilities: Agricultural 35.89%, Persistent 34.62%.
   - Salient features: `hist_count_full = 5.0`, `hist_distinct_calendar_months = 1.0`.
   - Explanation: Limited historical pre-alert history (5 detections in a single month) mimicked seasonal agricultural residue burning rather than year-round industrial flaring.
4. **`EVT_825_PER_PER_SRC_06` (True: Persistent, Pred: Agricultural)**
   - Probabilities: Agricultural 39.29%, Persistent 35.29%.
   - Salient features: `hist_count_full = 5.0`, `hist_distinct_calendar_months = 1.0`.
   - Explanation: Same low-recurrence ambiguity in agricultural heartland zone.
5. **`EVT_825_PER_PER_SRC_49` (True: Persistent, Pred: Agricultural)**
   - Probabilities: Agricultural 36.70%, Persistent 35.15%.
   - Salient features: `hist_count_full = 5.0`, `hist_distinct_calendar_months = 1.0`.
   - Explanation: Same low-recurrence ambiguity.
6. **`EVT_825_PER_PER_SRC_52` (True: Persistent, Pred: Agricultural)**
   - Probabilities: Agricultural 39.05%, Persistent 35.58%.
   - Salient features: `hist_count_full = 5.0`, `hist_distinct_calendar_months = 1.0`.
   - Explanation: Same low-recurrence ambiguity.

---

## 13. Limitations
1. **Small Sample Test Benchmark ($N=28$):**
   - Each event shifts the accuracy figure by 3.57%. Consequently, confidence intervals are wide ($[60.7\%, 92.9\%]$).
2. **Disentangling Low-Recurrence Persistent Sources Without a Registry:**
   - When persistent thermal anomalies have few pre-alert satellite passes ($< 10$ detections concentrated in 1 calendar month), pure statistical recurrence is indistinguishable from recurring agricultural burning.
3. **Deep Learning Tabular Modality:**
   - While pure neural networks satisfy the deep learning constraint and achieve high Macro-F1 (0.8021), they exhibit softer decision boundaries on small tabular samples compared to tree-based ensembles.

---

## 14. What the System Actually Detects
The DS08 system performs **source-type attribution** on active thermal anomalies:
- Given an active thermal detection cluster detected by satellite radiometers (VIIRS / MODIS) at alert timestamp $t_0$, the system classifies whether the underlying physical combustion event is an industrial plant emergency, forest wildfire, agricultural burn, or routine thermal operation.
- It identifies industrial fires with **100% precision and 100% recall** on the independent test set.

---

## 15. What the System Does NOT Claim
- The system **does not** claim to independently discover fires from raw optical/RGB pixels (detection is provided by NASA FIRMS).
- The system **does not** claim to be a universal omniscient fire detector.
- The system **does not** claim to reach 96% accuracy without a persistent registry; such claims in earlier stages were proven to stem from test-derived registry leakage.

---

## 16. Final Conclusion & Scientific Status
Stage 8.36 concludes the DS08 development and validation cycle with complete scientific rigor:
1. **Scientific Integrity Restored:** All spatial proxies, post-event lookaheads, and test-derived registries were fully expunged.
2. **Final Deep Learning Model Frozen:** `Architecture1_StaticMLP` was frozen and evaluated strictly once.
3. **Official Final Test Metrics:**
   - **Accuracy = 78.57%** (22/28)
   - **Macro-F1 = 0.8021**
   - **Balanced Accuracy = 81.67%**
   - **Industrial Attribution F1 = 1.0000**
4. **Target Status:** The strict $\ge 85\%$ threshold was not reached under pure deep learning without a registry (78.57% vs 85.00%). However, Macro-F1 reached **0.8021** (+0.0221 above the prior Stage 8.32 deep learning benchmark) and Balanced Accuracy reached **81.67%**.
5. **Absolute Rule Respected:** In accordance with scientific protocol, zero post-test retraining, hyperparameter search, or threshold tuning was performed.
