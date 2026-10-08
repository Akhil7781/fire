# Model Card: DS08 Causal 4-Class Thermal-Source Attribution Model

## 1. Model Details
- **Model Name:** DS08 Industrial/Thermal-Source Attribution Classifier
- **Architecture:** `Architecture1_StaticMLP` (Pure PyTorch Multi-Layer Perceptron)
- **Version:** Stage 8.36 Final Release
- **Date:** October 2026
- **Model Framework:** PyTorch 2.x
- **Model Parameters:** 3,244 trainable parameters
  - Layer 1: `Linear(41, 48)` + `LayerNorm(48)` + `GELU` + `Dropout(0.15)`
  - Layer 2: `Linear(48, 24)` + `LayerNorm(24)` + `GELU` + `Dropout(0.15)`
  - Output Head: `Linear(24, 4)`
- **Model Checkpoint SHA-256:** `5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2`
- **License / Access:** Internal Research & Operational Deployment Baseline

---

## 2. Intended Use
- **Primary Intended Use:** Real-time causal attribution of thermal anomalies detected by VIIRS/MODIS sensors at alert receipt ($t_0$). Specifically categorizes an active thermal detection cluster into one of 4 operational classes:
  1. `Industrial Fire` (accidents, refinery fires, factory chemical blazes)
  2. `Forest Fire` (wildfires, forest canopy/understory burns)
  3. `Agricultural Fire` (stubble burning, crop residue disposal)
  4. `Other / Persistent Thermal Source` (steel mills, cement kilns, gas flares, continuous hot industrial processes)
- **Out-of-Scope Use Cases:**
  - Raw optical image object detection (thermal detection is sourced from NASA FIRMS).
  - Post-disaster retrospective damage assessment (model operates causally at $H0$).
  - Global extrapolations outside the Indian subcontinent without retraining/re-standardization.

---

## 3. Data & Feature Provenance
- **Training Cohort:** $N = 165$ multi-year verified thermal events across India (2016–2025).
  - Spatial coverage: 4 macro-regions (North, Central-East, Central-West, South).
  - Temporal training split: $N = 125$ events ($\le 2024$), validation split: $N = 40$ events (2025).
- **Test Cohort (Frozen Independent Benchmark):** $N = 28$ events strictly from 2026 (`independent_test_manifest.json`, SHA-256: `5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c`).
- **Feature Design (41 Causal Modalities):**
  - **Thermal Anomaly Dynamics (14 features):** Alert-time FRP, brightness temperatures (TI4, TI5, Delta-TI), night detection flag, cumulative detection count, elapsed hours, mean/max/std FRP so far, FRP trend.
  - **Industrial Facility Proximity (6 features):** Distance to nearest industrial facility (km), binary thresholds (1km, 5km), facility baseline FRP, deviation, facility z-score.
  - **Ecoregion Context (3 features):** Forest biome score, agricultural heartland score, Sentinel-2 availability flag.
  - **Pre-Alert Historical Recurrence (18 features):** Pre-alert FIRMS history strictly constrained to $t \le t_0 - 7$ days (1km, 2km, 5km historical counts, active days, distinct calendar months, dispersion, recent count windows: 30d, 90d, 365d, historical night ratio, historical mean Delta-TI).
- **Strict Invariants:**
  - **Registry-Free:** Zero lookup against `persistent_source_manifest.json`.
  - **Coordinate-Free:** No raw latitude/longitude inputs.
  - **Target-Proxy Free:** Zero `associated_*` label columns.

---

## 4. Final Evaluation Metrics (Frozen 2026 Test Benchmark)

The model was evaluated **EXACTLY ONCE** on the untouched 2026 independent test cohort ($N=28$):

| Overall Metric | Result | 95% Confidence Interval |
|:---|:---:|:---:|
| **Accuracy** | **78.57%** (22/28) | Wilson: [60.46%, 100.00%] \| Bootstrap: [60.71%, 92.86%] |
| **Macro-F1** | **0.8021** | Bootstrap: [0.6369, 0.9226] |
| **Balanced Accuracy** | **81.67%** | Bootstrap: [65.83%, 93.75%] |
| **Weighted-F1** | **0.7946** | — |

### Per-Class Performance:
- **Industrial Fire:** Precision = **1.0000**, Recall = **1.0000**, F1 = **1.0000** ($6/6$)
- **Forest Fire:** Precision = **0.8333**, Recall = **0.8333**, F1 = **0.8333** ($5/6$)
- **Agricultural Fire:** Precision = **0.5000**, Recall = **0.8333**, F1 = **0.6250** ($5/6$)
- **Persistent / Other:** Precision = **1.0000**, Recall = **0.6000**, F1 = **0.7500** ($6/10$)

---

## 5. Limitations & Operational Nuance
1. **Sample Granularity:** With $N=28$, each event shifts accuracy by $3.57\%$. Wilson confidence intervals are wide ($[60.46\%, 100\%]$).
2. **Persistent-to-Agricultural Confusion:** 4 persistent events with low historical recurrence (5 observations over 1 distinct month) were classified as Agricultural Fire. In the absence of an operational registry, low-frequency persistent sources mimic seasonal agricultural burning patterns.
3. **Pure Deep Learning Constraint:** While achieving strong macro-F1 (0.8021), pure neural networks on small tabular cohorts exhibit slightly higher boundary softness between agricultural and low-count persistent events than hybrid tree ensembles.
