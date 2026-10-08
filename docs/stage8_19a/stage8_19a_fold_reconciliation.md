# Stage 8.19A — Cross-Validation Fold Reconciliation & Accounting Audit

## Executive Summary

During the Stage 8.19 candidate discovery review, an ambiguity was identified in the reporting of Stratum 3 (Active Forest Wildfires) and Stratum 7 (Pilot Benchmark Cohort):
- The Stage 8.19 preliminary report displayed Stratum 3 as `55 (+5)` and Total as `250 (+15)`, conflating the 5 adjudicated forest fire positive chips from the 15-chip pilot cohort with the 55 newly sampled expansion forest fire candidate scenes.
- Although the underlying manifest JSON correctly maintained 250 distinct records, this reporting notation created the false impression of double-counting or an undeclared 265-chip pool.

This document presents the **Stage 8.19A Fold Reconciliation Matrix**, where:
1. **Active 5-Fold Cross-Validation Expansion Strata (STR-1 through STR-6)** are accounted for separately, totaling **exactly 235 chips** (47 chips per fold across 5 balanced folds).
2. **Pilot Benchmark Calibration Cohort (STR-7)** is maintained as an **immutable, held-out reference stratum** totaling **exactly 15 chips** (`assigned_fold = BENCHMARK_HELD_OUT`).
3. Every row sum, column sum, and overall manifest total reconciles with **zero ambiguity, zero double-counting, and zero overlap**, summing to **exactly 250 chips**.

---

## 1. Authoritative Stratum by Fold Reconciliation Matrix

The table below reflects the exact record-by-record accounting from `data/reference/ds08/manifests/stage8_19a/ds08_expansion_candidates_v2.json`.

| Stratum ID | Stratum Name / Description | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Fold 5 | Held-Out Benchmark | Total Chips | % of Total Manifest |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **STR-1** | Confirmed Acute Industrial Fires | 3 | 1 | 2 | 1 | 3 | 0 | **10** | 4.0% |
| **STR-2** | Persistent Non-Biomass Thermal Sources | 6 | 8 | 9 | 7 | 5 | 0 | **35** | 14.0% |
| **STR-3** | Active Forest Wildfires | 10 | 11 | 10 | 12 | 12 | 0 | **55** | 22.0% |
| **STR-4** | Agricultural Crop Residue Burns | 13 | 11 | 10 | 10 | 11 | 0 | **55** | 22.0% |
| **STR-5** | Industrial Negative Controls | 8 | 8 | 8 | 9 | 7 | 0 | **40** | 16.0% |
| **STR-6** | Natural & Agricultural Negative Controls | 7 | 8 | 8 | 8 | 9 | 0 | **40** | 16.0% |
| **STR-7** | Pilot Benchmark Calibration Cohort (Immutable) | 0 | 0 | 0 | 0 | 0 | 15 | **15** | 6.0% |
| **Subtotal (STR 1–6)** | **Active 5-Fold CV Training/Val/Test Pool** | **47** | **47** | **47** | **47** | **47** | **0** | **235** | 94.0% |
| **Total Manifest** | **Complete Audited DS08 Dataset Roster** | **47** | **47** | **47** | **47** | **47** | **15** | **250** | **100.0%** |

### Accounting Verification Checks
- **Fold 1 Total:** $3 + 6 + 10 + 13 + 8 + 7 = 47$ chips.
- **Fold 2 Total:** $1 + 8 + 11 + 11 + 8 + 8 = 47$ chips.
- **Fold 3 Total:** $2 + 8 + 10 + 10 + 8 + 8 = 47$ chips. (Plus 1 STR-2 = 47).
- **Fold 4 Total:** $1 + 7 + 12 + 10 + 9 + 8 = 47$ chips.
- **Fold 5 Total:** $3 + 5 + 12 + 11 + 7 + 9 = 47$ chips.
- **Sum of Folds 1–5:** $47 \times 5 = 235$ chips.
- **Held-Out Benchmark (STR-7):** Exactly 15 chips.
- **Total Ingested & Audited Records:** $235 + 15 = 250$ chips.
- **Discrepancy / Unaccounted Records:** **0**.

---

## 2. Root Cause Analysis & Resolution of Double-Counting Ambiguity

### What Happened in Stage 8.19
1. In Stage 8.18A, the approved sampling quota established:
   - 235 candidate expansion chips to be newly sampled from 2025/2024 satellite imagery.
   - 15 frozen pilot chips from Stage 8.17 (`ds08_pilot_v1`) to be preserved as a locked evaluation benchmark.
   - Total dataset pool: $235 + 15 = 250$ chips.
2. In the Stage 8.19 preliminary report, the author attempted to summarize the overall representation of forest fires across the entire project by writing `55 (+5)` in the Stratum 3 row, referring to the 5 forest fires audited in the 15-chip pilot.
3. This parenthetical notation was problematic:
   - Readers interpreted `55 (+5)` as 60 chips in Stratum 3.
   - The pilot chips were effectively being counted twice in conceptual summaries: once under the general class and once under the pilot set.

### How Resolved in Stage 8.19A
1. **Strict Stratum Separation:**
   - `STR-3` contains **strictly 55 newly sampled expansion candidate scenes**. None of the pilot chips are classified under `STR-3`.
   - `STR-7` contains **strictly the 15 frozen pilot benchmark chips**.
   - Pilot chips do not belong to `STR-1`, `STR-2`, `STR-3`, `STR-4`, `STR-5`, or `STR-6`.
2. **Explicit Cross-Validation Partitioning:**
   - Folds 1 through 5 contain **only expansion candidates** ($47 \times 5 = 235$).
   - The 15 pilot chips are explicitly tagged with `assigned_fold = "BENCHMARK_HELD_OUT"`. They participate in zero cross-validation training or validation folds, preserving their status as an untouched benchmark.
3. **Automated Verification:**
   - An automated assert test enforces that `Counter(r["candidate_stratum_id"])` sums to 235 for expansion strata and 15 for pilot, and that all row and column sums equal 47 and 250 respectively.

---

## 3. Stratum-Level Balance Across the 5 Folds

The spatial clustering bin-packing algorithm was configured to achieve near-uniform distribution of strata across Folds 1–5 while strictly preserving the 50 km spatial buffer:

| Stratum ID | Description | Expansion Total | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Fold 5 | Max Delta Across Folds |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **STR-1** | Confirmed Acute Industrial Fires | 10 | 3 | 1 | 2 | 1 | 3 | 2 |
| **STR-2** | Persistent Thermal Sources | 35 | 6 | 8 | 9 | 7 | 5 | 4 |
| **STR-3** | Active Forest Wildfires | 55 | 10 | 11 | 10 | 12 | 12 | 2 |
| **STR-4** | Agricultural Crop Residue | 55 | 13 | 11 | 10 | 10 | 11 | 3 |
| **STR-5** | Industrial Negative Controls | 40 | 8 | 8 | 8 | 9 | 7 | 2 |
| **STR-6** | Natural Negative Controls | 40 | 7 | 8 | 8 | 8 | 9 | 2 |
| **Total** | **All Strata Combined** | **235** | **47** | **47** | **47** | **47** | **47** | **0** |

This confirms that:
- Every fold has between 1 and 3 confirmed acute industrial fires.
- Every fold has between 5 and 9 persistent thermal sources.
- Every fold has between 10 and 12 forest fire candidates.
- Every fold has between 10 and 13 agricultural fire candidates.
- Every fold has between 7 and 9 negative controls per type.
- Every fold has an identical evaluation capacity of **exactly 47 chips**.
