# Stage 8.36 — Final Blind Evaluation Report

**Evaluation Timestamp:** 2026-10-04  
**Evaluation Mode:** STRICT BLIND INDEPENDENT TEST EVALUATION  
**Model Architecture:** `Architecture1_StaticMLP` (Pure PyTorch Deep Learning)  
**Test Evaluation Counter:** 1 (Terminal Evaluation)  
**Frozen Cohort Size:** $N = 28$ events  
**Manifest SHA-256:** `5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c`  
**Checkpoint SHA-256:** `5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2`  

---

## 1. Executive Summary & Core Results

| Metric | Stage 8.36 Value | 95% Confidence Interval | Benchmark >= 0.85 Status |
|:---|:---:|:---:|:---:|
| **Overall Accuracy** | **78.57%** (22/28) | Wilson: [60.46%, 89.79%] <br> Bootstrap: [60.71%, 92.86%] | NOT ACHIEVED |
| **Macro-F1** | **0.8021** | Bootstrap: [0.6369, 0.9226] | NOT ACHIEVED |
| **Balanced Accuracy** | **81.67%** | Bootstrap: [65.83%, 93.75%] | NOT ACHIEVED |
| **Weighted-F1** | **0.7946** | — | — |

*Note: With $N=28$, each single event represents **3.5714 percentage points** of accuracy.*

---

## 2. Per-Class Performance Breakdown

| Class ID | Target Class Name | Support | Precision | Recall | F1-Score | Status |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| 0 | **Industrial Fire** | 6 | 1.0000 | 1.0000 | **1.0000** | Optimal |
| 1 | **Forest Fire** | 6 | 0.8333 | 0.8333 | **0.8333** | Sub-optimal |
| 2 | **Agricultural Fire** | 6 | 0.5000 | 0.8333 | **0.6250** | Sub-optimal |
| 3 | **Persistent / Other** | 10 | 1.0000 | 0.6000 | **0.7500** | Sub-optimal |

---

## 3. Confusion Matrix ($4 \times 4$)

```
                     Industrial   Forest   Agricultural   Persistent
Industrial               6            0        0              0         
Forest                   0            5        1              0         
Agricultural             0            1        5              0         
Persistent               0            0        4              6         
```

*Figure saved to:* `artifacts/stage8_36/confusion_matrix.png`

---

## 4. Historical Benchmark Comparison

| Stage & Pipeline | Model Type | Accuracy | Macro-F1 | Balanced Acc | Deep Learning Only? |
|:---|:---|:---:|:---:|:---:|:---:|
| **Stage 8.31 (Prior)** | Hybrid Static MLP + Random Forest | 85.71% (24/28) | 0.8231 | 83.33% | No (Ensemble) |
| **Stage 8.32 (Prior)** | Grouped Gated Classifier ($N=131$) | 78.57% (22/28) | 0.7800 | 80.00% | **Yes** |
| **Stage 8.36 (Final)** | **Architecture1_StaticMLP ($N=165$)** | **78.57% (22/28)** | **0.8021** | **81.67%** | **Yes (Pure PyTorch)** |

---

## 5. Detailed Error Analysis (6 Discrepancies)

### Event: `EVT_825_FOR_FOR_EVT_2026_OD_KOTGARH`
- **True Class:** Forest Fire (ID: 1)
- **Predicted Class:** Agricultural Fire (ID: 2)
- **Confidence:** 0.3739
- **Predicted Probabilities:**
  - Industrial: 0.1156
  - Forest: 0.3582
  - Agricultural: 0.3739
  - Persistent: 0.1523
- **Key Features:**
  - `dist_to_fac_km`: 253.43 km (within 1km: 0.0)
  - `forest_biome_score`: 1.0000
  - `agri_heartland_score`: 0.0000
  - `hist_count_full`: 0
  - `hist_distinct_calendar_months`: 0
  - `current_frp`: 3.5 MW

### Event: `EVT_825_AGR_AGR_EVT_2026_RJ_KOTA_RABI`
- **True Class:** Agricultural Fire (ID: 2)
- **Predicted Class:** Forest Fire (ID: 1)
- **Confidence:** 0.4136
- **Predicted Probabilities:**
  - Industrial: 0.1311
  - Forest: 0.4136
  - Agricultural: 0.3627
  - Persistent: 0.0926
- **Key Features:**
  - `dist_to_fac_km`: 307.53 km (within 1km: 0.0)
  - `forest_biome_score`: 0.0000
  - `agri_heartland_score`: 1.0000
  - `hist_count_full`: 0
  - `hist_distinct_calendar_months`: 0
  - `current_frp`: 24.8 MW

### Event: `EVT_825_PER_PER_SRC_03`
- **True Class:** Other / Persistent Thermal Source (ID: 3)
- **Predicted Class:** Agricultural Fire (ID: 2)
- **Confidence:** 0.3589
- **Predicted Probabilities:**
  - Industrial: 0.1153
  - Forest: 0.1797
  - Agricultural: 0.3589
  - Persistent: 0.3462
- **Key Features:**
  - `dist_to_fac_km`: 158.14 km (within 1km: 0.0)
  - `forest_biome_score`: 0.0000
  - `agri_heartland_score`: 0.0000
  - `hist_count_full`: 5
  - `hist_distinct_calendar_months`: 1
  - `current_frp`: 7.7 MW

### Event: `EVT_825_PER_PER_SRC_06`
- **True Class:** Other / Persistent Thermal Source (ID: 3)
- **Predicted Class:** Agricultural Fire (ID: 2)
- **Confidence:** 0.3929
- **Predicted Probabilities:**
  - Industrial: 0.1073
  - Forest: 0.1470
  - Agricultural: 0.3929
  - Persistent: 0.3529
- **Key Features:**
  - `dist_to_fac_km`: 111.77 km (within 1km: 0.0)
  - `forest_biome_score`: 0.0000
  - `agri_heartland_score`: 1.0000
  - `hist_count_full`: 5
  - `hist_distinct_calendar_months`: 1
  - `current_frp`: 4.9 MW

### Event: `EVT_825_PER_PER_SRC_49`
- **True Class:** Other / Persistent Thermal Source (ID: 3)
- **Predicted Class:** Agricultural Fire (ID: 2)
- **Confidence:** 0.3670
- **Predicted Probabilities:**
  - Industrial: 0.1128
  - Forest: 0.1687
  - Agricultural: 0.3670
  - Persistent: 0.3515
- **Key Features:**
  - `dist_to_fac_km`: 53.18 km (within 1km: 0.0)
  - `forest_biome_score`: 0.0000
  - `agri_heartland_score`: 0.0000
  - `hist_count_full`: 5
  - `hist_distinct_calendar_months`: 1
  - `current_frp`: 7.4 MW

### Event: `EVT_825_PER_PER_SRC_52`
- **True Class:** Other / Persistent Thermal Source (ID: 3)
- **Predicted Class:** Agricultural Fire (ID: 2)
- **Confidence:** 0.3905
- **Predicted Probabilities:**
  - Industrial: 0.1183
  - Forest: 0.1354
  - Agricultural: 0.3905
  - Persistent: 0.3558
- **Key Features:**
  - `dist_to_fac_km`: 113.83 km (within 1km: 0.0)
  - `forest_biome_score`: 0.0000
  - `agri_heartland_score`: 1.0000
  - `hist_count_full`: 5
  - `hist_distinct_calendar_months`: 1
  - `current_frp`: 7.7 MW


---

## 6. Scientific Protocol Verification
1. **Zero Retraining Commitment:** The evaluation was executed with weights frozen directly from Stage 8.35. No parameter updates or threshold search occurred.
2. **Deterministic Inference:** Standard PyTorch deterministic execution with frozen mean/std standardizers.
3. **Causal Integrity:** Features strictly constrained to $t \le t_0$ and pre-alert history $t \le t_0 - 7$ days. Zero post-event lookahead.
4. **Registry Independence:** No lookup against `persistent_source_manifest.json`. Zero target-proxy features.
