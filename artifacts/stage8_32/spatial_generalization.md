# Stage 8.32 Geographic Generalization Audit Report

**Date:** October 4, 2026  
**Auditor:** Autonomous Agentic AI (Advanced Coding & Scientific Audit Team)  
**Evaluation Scope:** Strictly **TRAIN (2018-2024, N=107)** and **VAL (2025 Holdout, N=24)**.  
**Frozen 2026 Test Set:** **0 EVALUATIONS / UNTOUCHED**  

---

## 1. Generalization Partition Matrix

| Evaluation Split | Train Size | Val Size | Val Accuracy | Val Macro-F1 | Val Balanced Acc | Industrial F1 | Forest F1 | Agricultural F1 | Persistent F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **RANDOM_SPLIT** (Stratified 80/20) | 104 | 27 | **100.00%** | **1.0000** | **100.00%** | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **TEMPORAL_SPLIT** (2018-24 vs 2025) | 107 | 24 | **91.67%** | **0.9093** | **90.18%** | 0.8571 | 0.8571 | 1.0000 | 0.9231 |
| **SPATIAL_BLOCK_SPLIT** (Central-West Holdout) | 112 | 19 | **94.74%** | **0.9020** | **87.50%** | 0.9412 | 0.6667 | 1.0000 | 1.0000 |
| **SPATIAL_BLOCK_CV** (All-India 4-Fold) | 131 | 131 | **87.79%** | **0.8660** | **86.46%** | 0.8788 | 0.7797 | 0.8400 | 0.9655 |

---

## 2. Confusion Matrices

### A. RANDOM_SPLIT (N=27)
```
                    Ind  For  Agr  Per
Industrial Fire   [7, 0, 0, 0]
Forest Fire       [0, 6, 0, 0]
Agricultural Fire [0, 0, 5, 0]
Persistent        [0, 0, 0, 9]
```

### B. TEMPORAL_SPLIT (2025 Chronological Holdout, N=24)
```
                    Ind  For  Agr  Per
Industrial Fire   [3, 1, 0, 0]
Forest Fire       [0, 6, 0, 1]
Agricultural Fire [0, 0, 7, 0]
Persistent        [0, 0, 0, 6]
```

### C. SPATIAL_BLOCK_SPLIT (Central-West Geographic Holdout, N=19)
```
                    Ind  For  Agr  Per
Industrial Fire   [8, 0, 0, 0]
Forest Fire       [1, 1, 0, 0]
Agricultural Fire [0, 0, 3, 0]
Persistent        [0, 0, 0, 6]
```

---

## 3. Scientific Assessment of Geographic Memorization vs Transferability

1. **Random vs Spatial Generalization Gap:**
   - Under Random Split, events from the same geographic clusters can appear in both training and validation, yielding high performance (100.00% accuracy).
   - Under Spatial Block Split (evaluating events in an entirely unobserved geographic region), the model achieves **94.74% accuracy** and **0.9020 Macro-F1**.
   - Under nationwide 4-Fold Spatial Block Cross-Validation across all 131 events, out-of-region accuracy is **87.79%** and Macro-F1 is **0.8660**.
2. **Persistent Source Generalization:**
   - Pre-alert historical recurrence counts and temporal density transfer across geographic regions, preserving high Persistent F1 (1.0000) without spatial memorization.
3. **Agricultural vs Forest Transferability:**
   - Agricultural fires rely on distinctive flat thermal signatures, rabi/kharif seasonal windows, and daytime ratio, but boundary friction occurs in mixed forest-agriculture transitions.
