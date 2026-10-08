# Stage 8.31 Final Independent Test Evaluation Report

**Date:** October 4, 2026  
**Auditor:** Autonomous Agentic AI (Advanced Coding & Scientific Audit Team)  
**Test Evaluation Count:** **1** (Strictly Single Run)  
**Evaluated Cohort:** Frozen 2026 Independent Test Cohort ($N=28$)  
**Registry Dependency:** **ZERO** (`persistent_source_manifest.json` completely excluded)  
**Causal Horizon:** $H_0$ (First Detection / Alert Time Only)  

---

## 1. Primary Benchmark Results

| Metric | Measured Value | 95% Bootstrap CI | 95% Wilson Score CI | Benchmark ($\ge 85\%$) |
| :--- | :---: | :---: | :---: | :---: |
| **Accuracy** | **85.71%** (24/28) | [71.43%, 96.43%] | [68.51%, 94.30%] | **MET** |
| **Macro F1** | **0.8231** | [0.6378, 0.9530] | — | **UNMET** |
| **Balanced Accuracy** | **83.33%** | [66.67%, 95.83%] | — | **UNMET** |

---

## 2. Per-Class Performance Breakdown

| Class ID | Target Class | Support | Precision | Recall | F1 Score | TP | FP | FN |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | **Industrial Fire** | 6 | 0.8571 | 1.0000 | **0.9231** | 6 | 1 | 0 |
| 1 | **Forest Fire** | 6 | 0.7143 | 0.8333 | **0.7692** | 5 | 2 | 1 |
| 2 | **Agricultural Fire** | 6 | 0.7500 | 0.5000 | **0.6000** | 3 | 1 | 3 |
| 3 | **Other / Persistent** | 10 | 1.0000 | 1.0000 | **1.0000** | 10 | 0 | 0 |

---

## 3. Confusion Matrix

| True \ Predicted | Industrial Fire | Forest Fire | Agricultural Fire | Persistent / Other |
| :--- | :---: | :---: | :---: | :---: |
| **Industrial Fire** | 6 | 0 | 0 | 0 |
| **Forest Fire** | 0 | 5 | 1 | 0 |
| **Agricultural Fire** | 1 | 2 | 3 | 0 |
| **Persistent / Other** | 0 | 0 | 0 | 10 |

---

## 4. Small-Sample Uncertainty Quantification ($N=28$)

- **Single-Event Granularity:** With $N=28$, each individual event accounts for **3.57%** of overall accuracy.
- **Statistical Significance:** The 95% Wilson confidence interval for accuracy is [68.51%, 94.30%], reflecting genuine statistical bounds given sample size.
- **No Test Tuning:** The test set was touched exactly 1 time(s). Zero hyperparameters, thresholds, or feature representations were adapted on test data.

---

## 5. Detailed Test Error Audit
- **`EVT_825_FOR_FOR_EVT_2026_UK_CHAMOLI`**: True Class = `Forest Fire`, Predicted = `Agricultural Fire` (P(True) = 0.270, P(Pred) = 0.704, DistFac = 208.0 km, HistCount = 0.0)
- **`EVT_825_AGR_AGR_EVT_2026_MP_HARDA_RABI`**: True Class = `Agricultural Fire`, Predicted = `Industrial Fire` (P(True) = 0.405, P(Pred) = 0.427, DistFac = 310.4 km, HistCount = 0.0)
- **`EVT_825_AGR_AGR_EVT_2026_RJ_KOTA_RABI`**: True Class = `Agricultural Fire`, Predicted = `Forest Fire` (P(True) = 0.352, P(Pred) = 0.580, DistFac = 307.5 km, HistCount = 0.0)
- **`EVT_825_AGR_AGR_EVT_2026_TN_THANJAVUR_KHARIF`**: True Class = `Agricultural Fire`, Predicted = `Forest Fire` (P(True) = 0.276, P(Pred) = 0.451, DistFac = 124.0 km, HistCount = 0.0)
