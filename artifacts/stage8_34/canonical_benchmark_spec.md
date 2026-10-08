# Stage 8.34 - Canonical Development Benchmark Specification

## Purpose
This document establishes the **SINGLE, CANONICAL, PERMANENT EVALUATION SUITE** for DS08 thermal-source attribution. No arbitrary or undocumented splits are permitted. All model comparisons and architectural decisions must strictly be evaluated on these deterministic protocols.

**STRICT TEST LOCK GUARANTEE:**
- Total development events: **$N = 131$** (2016–2025).
- Frozen 2026 independent test set ($N=28$): **PERMANENTLY LOCKED & UNTOUCHED** (`FROZEN_TEST_ACCESSED = FALSE`, `TEST_EVALUATION_COUNT = 0`).

---

## 1. Primary Benchmark: CANONICAL_SPATIAL_CV
- **Evaluation Purpose:** Measures generalization across unseen geographic macro-regions in India without spatial proximity shortcuts.
- **Protocol:** Outer 4-Fold Macro-Region Cross-Validation. For each fold, one entire macro-region is held out as the outer test set. Inner 5-fold stratified cross-validation on training regions is used for early stopping.
- **Primary Metric:** **Macro-F1 (Mean $\pm$ Std across 4 folds)**.
- **Secondary Metrics:** Balanced Accuracy, Worst Fold Macro-F1.

### Spatial Fold Partitions:
| Fold Name | Outer Held-out Region | Outer Test Size ($N$) | Outer Train Size ($N$) | Dominant Regional Class |
|:---|:---|:---:|:---:|:---|
| **Fold 0** | **North** (Lat $\ge 26^\circ$) | 45 | 86 | Agricultural Fire (51.1%) |
| **Fold 1** | **Central_East** (Lat $20^\circ-26^\circ$, Lon $\ge 78^\circ$) | 35 | 96 | Persistent Source (62.9%) |
| **Fold 2** | **Central_West** (Lat $20^\circ-26^\circ$, Lon $< 78^\circ$) | 19 | 112 | Industrial Fire (42.1%) |
| **Fold 3** | **South** (Lat $< 20^\circ$) | 32 | 99 | Industrial Fire (53.1%) |

---

## 2. Secondary Benchmark: CANONICAL_TEMPORAL_CV
- **Evaluation Purpose:** Measures forward temporal generalization to the subsequent operational year under causal constraints.
- **Protocol:** Operational Holdout.
  - **Train Partition:** All events observed on or before December 31, 2024 ($N=107$).
  - **Validation Partition:** All events observed during calendar year 2025 ($N=24$).
- **Class Balance:** All 4 classes are present in both Train and Validation partitions:
  - Train $\le 2024$: Industrial=31, Forest=20, Agricultural=20, Persistent=36 ($N=107$).
  - Val 2025: Industrial=4, Forest=7, Agricultural=7, Persistent=6 ($N=24$).
- **Canonical Metrics:** Accuracy = **83.33%**, Macro-F1 = **0.8183**, Balanced Accuracy = **0.8304**.

---

## 3. Diagnostic Benchmark: CANONICAL_RANDOM_CV
- **Evaluation Purpose:** Measures in-distribution cross-validation performance under stratified random partitioning.
- **Protocol:** 5-Fold Stratified Cross-Validation (seed=42).
- **Split Sizes:** 4 folds of $N=26$, 1 fold of $N=27$.
- **Use Case:** Sanity checking and baseline diagnostic verification.

---

## 4. Evaluation Invariants & Rules
1. **Zero Raw Coordinates:** The primary model must NOT ingest `centroid_lat` or `centroid_lon` to prevent regional memorization.
2. **Scaler Isolation:** All standardizers and scalers must be fitted **exclusively on the fold's training partition** and applied to validation/test partitions without lookahead.
3. **No Registry Usage:** No static persistent source manifest or ground truth lookup tables may be loaded or queried.
4. **Causal Time Horizons:** All features must adhere strictly to $t \le t_0$ (current thermal) and $t \le t_0 - 7$ days (historical recurrence).
