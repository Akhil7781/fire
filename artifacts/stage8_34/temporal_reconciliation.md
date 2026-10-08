# Stage 8.34 - Temporal Discrepancy Reconciliation Report

## Executive Summary
In Stage 8.33, two conflicting temporal evaluation metrics were reported:
1. **Holdout 2025 (Train $\le 2024 \to$ Val 2025):** Accuracy = **83.33%** (20/24), Macro-F1 = **0.8183**, Balanced Accuracy = **0.8304**.
2. **Pooled Multi-Period Forward Chaining:** Accuracy = **47.62%** (40/84), Macro-F1 = **0.4840**.

This audit proves conclusively that **both metrics were mathematically accurate under their respective operational rules**, but the pooled forward chaining was severely distorted by a **historical catalogue expansion pathology**.

---

## Root Cause Analysis: The 2024 Persistent Source Expansion

A year-by-class cross-tabulation of the trusted development cohort ($N=131$) reveals:

| Year | Agricultural Fire | Forest Fire | Industrial Fire | Persistent / Other | Total Events |
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

### Crucial Findings:
1. **Zero Persistent Sources Prior to 2024:** Between 2016 and 2023 ($N=58$ events), there was **not a single record** belonging to Class 3 (Persistent / Other Thermal Source) in the dataset. All 42 persistent development sources were catalogued starting in 2024 (36 in 2024, 6 in 2025).
2. **Split 2 Pathology:** In Split 2 (Train $\le 2023 \to$ Test 2024), the training set had **zero examples of Class 3**, while the 2024 test set was **73.5% Class 3** (36 out of 49 events). 
   - A 4-class classifier cannot predict a class it has never seen.
   - Recall on Class 3 was strictly **0.00%**.
   - Consequently, Split 2 achieved only **24.49% accuracy** (12/49).
3. **Split 1 Pathology:** In Split 1 (Train $\le 2022 \to$ Test 2023), neither train nor test had Class 3, so it was actually an accidental 3-class evaluation (8/11 = 72.73%).
4. **The Pooling Distortion:**
   $$\text{Pooled Accuracy} = \frac{8 + 12 + 20}{11 + 49 + 24} = \frac{40}{84} = 47.62\%$$
   The pooled metric gave a 58.3% weight ($49/84$) to Split 2, an impossible split where 73.5% of labels were absent from training.

---

## Comparison of Protocols

| Metric | Protocol A: Operational Holdout (2025) | Protocol B: Pooled Multi-Period Chaining |
|---|---|---|
| **Training Set** | Events $\le 2024$ ($N=107$) | Rolling ($\le 2022, \le 2023, \le 2024$) |
| **Validation Set** | Year 2025 ($N=24$) | Years 2023, 2024, 2025 ($N=84$) |
| **Class Balance** | All 4 classes present in both | Split 1 has 3 classes; Split 2 missing Class 3 |
| **Accuracy** | **83.33%** (20/24) | **47.62%** (40/84) |
| **Macro-F1** | **0.8183** | **0.4840** |
| **Scientific Validity** | **VALID & CANONICAL** | **STRUCTURALLY INVALID** |

---

## Canonical Temporal Protocol Decision
1. **Resolution:** The contradiction is fully resolved and mathematically explained.
2. **Canonical Temporal Benchmark:** Protocol A (Train $\le 2024 \to$ Val 2025) is designated as the **CANONICAL_TEMPORAL_EVALUATION** benchmark:
   - Canonical Temporal Accuracy: **83.33%**
   - Canonical Temporal Macro-F1: **0.8183**
3. Multi-period forward chaining prior to 2024 is deprecated for 4-class models because historical data prior to 2024 did not monitor or annotate persistent thermal sources.
