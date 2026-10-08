# Forensic Reconciliation Report: 2025 Chronological Validation Discrepancy

**Date:** October 4, 2026  
**Audit Stage:** Stage 8.31 Task 1  
**Target:** Reconcile Stage 8.26 (70.83%) vs Stage 8.30 (87.50%) on 2025 Chronological Partition  
**Status:** `RESOLVED` (`VERIFIED_MODEL_AND_FEATURE_CAPACITY_DIFFERENCE`)  

---

## 1. Executive Summary

| Evaluation Attribute | Stage 8.26 (Phase AA Split 2) | Stage 8.30 (Validation Holdout) | Reconciliation Status |
| :--- | :---: | :---: | :---: |
| **Accuracy** | **70.83%** (17/24) | **87.50%** (21/24) | Reconciled (+4 correct events) |
| **Macro-F1** | 0.7005 | 0.8731 | Reconciled (+0.1726) |
| **Balanced Accuracy** | 0.6964 | 0.8929 | Reconciled (+0.1965) |
| **Physical Event Count** | 24 | 24 | **IDENTICAL COHORT** |
| **Event Identities** | Exactly same 24 events | Exactly same 24 events | **IDENTICAL EVENTS** |
| **Class Distribution** | 4 Ind, 7 For, 7 Agr, 6 Per | 4 Ind, 7 For, 7 Agr, 6 Per | **IDENTICAL CLASSES** |
| **Features Used** | 16 basic tabular features | 129 multi-scale causal features | **DIFFERENT FEATURE SPACE** |
| **Model Architecture** | Simple 1-layer MLP (dim=32) | RegistryFreeCausalClassifier | **DIFFERENT MODEL CAPACITY** |
| **Historical Recurrence** | None | Multi-scale FIRMS (30d..full) | **PRIMARY SIGNAL DRIVER** |
| **Persistent Registry Used** | NO | NO | **BOTH REGISTRY-FREE** |
| **Leakage Detected** | NO | NO | **BOTH VALID CAUSAL EVALUATIONS** |

---

## 2. Forensic Findings & Root Cause Analysis

### Question 1: Is the 87.50% result a different cohort?
**NO.** Lineage tracing of `ds08_stage8_25_physical_events.parquet` confirms that both stages evaluated the exact same 24 events with identical timestamps, locations, and labels:
- Industrial Fire (4 events)
- Forest Fire (7 events)
- Agricultural Fire (7 events)
- Other Thermal Source / Persistent (6 events)

### Question 2: Why did Stage 8.26 score 70.83% while Stage 8.30 scored 87.50%?
1. **Model Architecture**: Stage 8.26 trained a tiny 32-hidden-unit MLP without class weighting, representation regularization, or early stopping. Stage 8.30 deployed a full fusion network combining GRU embeddings with tabular projections.
2. **Feature Informativeness**: Stage 8.26 used only 16 raw retrospective scalar features. It had **zero information on prior multi-year recurrence**.
3. **The Exact Failure in Stage 8.26**:
   Stage 8.26 confusion matrix on 2025:
   ```
                    PREDICTED (Stage 8.26)
   TRUE CLASS    IND   FOR   AGR   PER   Total
   Industrial     2     1     0     1      4
   Forest         0     6     1     0      7
   Agricultural   0     4     3     0      7
   Persistent     0     0     0     6      6
   ```
   In Stage 8.26, **4 out of 7 agricultural fires were misclassified as forest fires**, and 1 industrial fire was misclassified as forest. Agricultural F1 was a dismal **0.5455**.
4. **The Resolution in Stage 8.30**:
   In Stage 8.30, the introduction of multi-scale historical recurrence and ecoregion scores enabled the model to recognize that the agricultural events in Punjab/Haryana/UP occurred in agricultural heartlands with near-zero historical multi-year recurrence, lifting agricultural classification from 3/7 to 6/7, and overall accuracy from 17/24 (70.83%) to 21/24 (87.50%).

---

## 3. Explicit Audit Declaration

```
OLD_2025_RESULT=70.83%
NEW_2025_RESULT=87.50%
SAME_COHORT=YES
SAME_FEATURES=NO
SAME_SPLIT=YES
SAME_MODEL=NO
LEAKAGE_DIFFERENCE=NO
RESOLUTION=The discrepancy is a genuine capability gain driven by multi-scale historical FIRMS recurrence and ecoregion context resolving agricultural vs forest confusion.
```
