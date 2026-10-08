# Stage 8.32 Final Neural-Only Test Evaluation Report

**Date:** October 4, 2026  
**Auditor:** Autonomous Agentic AI (Advanced Coding & Scientific Audit Team)  
**Model Type:** **DEEP LEARNING ONLY** (`GroupedCausalThermalClassifier`)  
**Classical ML Components:** **NONE (0%)**  
**Test Evaluation Count:** **1** (Strictly Single Run)  
**Evaluated Cohort:** Frozen 2026 Independent Test Cohort ($N=28$)  
**Registry Dependency:** **ZERO**  
**Causal Horizon:** $H_0$ (Alert Time)  

---

## 1. Primary Benchmark Results

| Metric | Measured Value | 95% Bootstrap CI | 95% Wilson Score CI | Benchmark ($\ge 85\%$) |
| :--- | :---: | :---: | :---: | :---: |
| **Accuracy** | **78.57%** (22/28) | [60.71%, 92.86%] | [60.46%, 89.79%] | **UNMET** |
| **Macro F1** | **0.7800** | [0.5771, 0.9247] | — | **UNMET** |
| **Balanced Accuracy** | **80.00%** | [62.62%, 93.18%] | — | **UNMET** |

---

## 2. Per-Class Performance Breakdown

| Class ID | Target Class | Support | Precision | Recall | F1 Score | TP | FP | FN |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | **Industrial Fire** | 6 | 0.6667 | 1.0000 | **0.8000** | 6 | 3 | 0 |
| 1 | **Forest Fire** | 6 | 0.7143 | 0.8333 | **0.7692** | 5 | 2 | 1 |
| 2 | **Agricultural Fire** | 6 | 0.8000 | 0.6667 | **0.7273** | 4 | 1 | 2 |
| 3 | **Other / Persistent** | 10 | 1.0000 | 0.7000 | **0.8235** | 7 | 0 | 3 |

---

## 3. Confusion Matrix

| True \ Predicted | Industrial Fire | Forest Fire | Agricultural Fire | Persistent / Other |
| :--- | :---: | :---: | :---: | :---: |
| **Industrial Fire** | 6 | 0 | 0 | 0 |
| **Forest Fire** | 0 | 5 | 1 | 0 |
| **Agricultural Fire** | 0 | 2 | 4 | 0 |
| **Persistent / Other** | 3 | 0 | 0 | 7 |

---

## 4. Small-Sample Uncertainty Quantification ($N=28$)

- **Single-Event Shift Granularity:** Each individual event equals **3.57%** of test accuracy.
- **95% Wilson Score Interval:** [60.46%, 89.79%]
- **Zero Test Tuning:** Architecture was selected strictly on Train/Val. Exactly 1 test evaluation was performed.

---

## 5. Test Errors
- **`EVT_825_FOR_FOR_EVT_2026_UK_CHAMOLI`**: True = `Forest Fire`, Pred = `Agricultural Fire` (P(True) = 0.160, P(Pred) = 0.829, DistFac = 208.0 km, HistCount = 0.0)
- **`EVT_825_AGR_AGR_EVT_2026_BR_BUXAR_RABI`**: True = `Agricultural Fire`, Pred = `Forest Fire` (P(True) = 0.139, P(Pred) = 0.840, DistFac = 201.5 km, HistCount = 0.0)
- **`EVT_825_AGR_AGR_EVT_2026_TN_THANJAVUR_KHARIF`**: True = `Agricultural Fire`, Pred = `Forest Fire` (P(True) = 0.163, P(Pred) = 0.793, DistFac = 124.0 km, HistCount = 0.0)
- **`EVT_825_PER_PER_SRC_02`**: True = `Other / Persistent`, Pred = `Industrial Fire` (P(True) = 0.078, P(Pred) = 0.905, DistFac = 146.4 km, HistCount = 5.0)
- **`EVT_825_PER_PER_SRC_03`**: True = `Other / Persistent`, Pred = `Industrial Fire` (P(True) = 0.246, P(Pred) = 0.741, DistFac = 158.1 km, HistCount = 5.0)
- **`EVT_825_PER_PER_SRC_49`**: True = `Other / Persistent`, Pred = `Industrial Fire` (P(True) = 0.229, P(Pred) = 0.759, DistFac = 53.2 km, HistCount = 5.0)
