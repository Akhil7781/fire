# STAGE 8.18A — PROTOCOL REVIEW AND SIGN-OFF AUDIT REPORT
**Resolution of Methodological Defects, Empirical Validation, and Sign-Off Readiness**

- **Audit Execution Timestamp:** `2026-10-02T12:50:00Z`
- **Stage:** Stage 8.18A — Protocol Review and Sign-off Preparation
- **Status:** **COMPLETE — LOCKED FOR HUMAN REVIEW (STRICT STOP ENFORCED)**
- **Audit Documentation Location:** `data/reference/ds08/annotations/review/stage8_18a_review_report.md`
- **Review Deliverables Directory:** `docs/stage8_18a/`
- **Target Expansion Cohort:** $N = 250$ Real Level-2A Sentinel-2 Chips across India
- **Operational Mode:** **READ-ONLY REVIEW & SPECIFICATION LOCK (ZERO DOWNLOADS / ZERO TRAINING / ZERO SYNTHETIC LABELS)**

---

## 1. Executive Summary

Stage 8.18A resolves all six methodological and architectural issues identified in the Stage 8.18 planning deliverables before commencing candidate discovery. All prior Stage 8.18 planning documents (`docs/stage8_18/`) and pilot dataset artifacts (`data/reference/ds08/packages/ds08_pilot_v1/`) remain completely preserved and immutable.

Every revision has been empirically verified using actual historical candidate coordinates and established spatial statistics. The dataset expansion protocol is now mathematically sound, physically grounded, and ready for human sign-off.

```text
========================================================================================
                          STAGE 8.18A RESOLUTION SUMMARY
========================================================================================
1. Geographic Partitioning:           RESOLVED (Mutually exclusive & exhaustive, 0 overlaps/gaps)
2. Industrial Fire Sampling Unit:     RESOLVED (3-tier hierarchy: incident vs scene vs chip)
3. Temporal Phases & Tiers:           RESOLVED (Active combustion vs post-event scar separated)
4. Spatial Buffering & 5-Fold CV:     RESOLVED (150km percolation defect resolved; MGRS + 50km locked)
5. Inter-Annotator Agreement:         RESOLVED (Edge cases, Kappa paradox, matched IoU formalized)
6. Decision Log & Review Report:      RESOLVED (Comparative evolution & sign-off checklist locked)
----------------------------------------------------------------------------------------
Bulk Imagery Downloaded:              0 (STRICTLY PROHIBITED)
Synthetic Labels Generated:           0 (STRICTLY PROHIBITED)
Models Trained:                       0 (STRICT BOUNDARY ENFORCED)
Stage Status:                         READY FOR HUMAN SIGN-OFF
========================================================================================
```

---

## 2. Detailed Resolution of the Six Protocol Issues

### Issue 1: Mutually Exclusive and Exhaustive Geographic Partitioning
- **Identified Defect:** Stage 8.18 used overlapping latitude/longitude inequalities that caused Northeast India ($\text{Lat} \ge 27^\circ, \text{Lon} \ge 83^\circ$) and island territories to satisfy multiple regional conditions simultaneously, creating execution-order dependency (e.g. `PILOT_03_NORTH` in Sikkim misclassified as North).
- **Resolution:** Stage 8.18A establishes a two-tiered deterministic partition:
  1. *Tier 1 (Administrative):* MHA Zonal Council state/UT boundaries.
  2. *Tier 2 (Coordinate Fallback):* Strictly disjoint mathematical decision tree `classify_indian_region_v2` with $\text{Lon} \ge 84.0^\circ\text{E}$ mapped exclusively to East, resolving all northeastern and island ambiguities.
- **Mathematical Verification:** Proved zero overlaps and zero gaps over $\text{Lat} \in [6.0^\circ, 38.0^\circ]$, $\text{Lon} \in [68.0^\circ, 98.0^\circ]$.
- **Allocation Totals Verified:** North: 55 (22%), Central: 60 (24%), South: 45 (18%), East: 50 (20%), West: 40 (16%) = **250 chips (100.0%)**.
- **Deliverable:** [`docs/stage8_18a/stage8_18a_geographic_partition_spec.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18a/stage8_18a_geographic_partition_spec.md).

---

### Issue 2: Acute Industrial Fire Sampling Unit Hierarchy
- **Identified Defect:** Stage 8.18 specified 35 acute industrial fire chips without distinguishing between physical ground events, satellite overpasses, and cropped chips, risking pseudo-replication and cross-fold data leakage.
- **Resolution:** Formally decoupled into a 3-tier hierarchy:
  1. *Incident (`incident_id`):* The Primary Sampling Unit (PSU). Represents a discrete, verified physical industrial fire disaster on the ground. Exactly one canonical primary chip per incident counts toward the 35-sample quota ($N_{\text{incidents}} = 35$).
  2. *Acquisition Scene (`scene_id`):* A distinct Sentinel-2 L2A orbital overpass product.
  3. *Image Chip (`chip_id`):* The extracted $512 \times 512$ pixel analytical window.
- **Grouping Invariant:** Any multi-temporal or adjacent secondary chips sharing the same `incident_id` must be grouped into the identical cross-validation fold. Splitting chips from the same incident across training and evaluation sets is strictly banned.
- **Deliverable:** [`docs/stage8_18a/stage8_18a_industrial_fire_sampling_unit.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18a/stage8_18a_industrial_fire_sampling_unit.md).

---

### Issue 3: Temporal Matching Tiers and Physical Event Phases
- **Identified Defect:** Stage 8.18 grouped candidate overpasses purely by absolute time offset $|\Delta t| \le 48\text{h}$ without distinguishing between active flaming combustion and post-fire burn scars.
- **Resolution:** Decoupled temporal matching into physical event combustion phases:
  1. *`ACTIVE_COMBUSTION` (Tiers 1 & 2, $|\Delta t| \le 6.0\text{h}$):* Flaming/smoldering front, active smoke plume, SWIR saturation. Permissible for training/evaluating active flame detectors.
  2. *`POST_COMBUSTION_SCAR` (Tiers 3 & 4, $6.0\text{h} < |\Delta t| \le 48.0\text{h}$):* Extinguished fire aftermath, surface charring, ash deposits.
- **Evidence Tagging Invariant:** `DIRECT_FIRE_VISIBLE` is **strictly prohibited** on Tier 3 & Tier 4 chips unless unextinguished hot embers with SWIR saturation are verified.
- **Evaluation Decoupling:** Model evaluation is formally partitioned into Suite A (Active Fire Detection on Tiers 1 & 2) and Suite B (Burn Scar Mapping on Tiers 3 & 4). Active fire models are not penalized for predicting negative on post-event scars.
- **Deliverable:** [`docs/stage8_18a/stage8_18a_temporal_matching_and_phases.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18a/stage8_18a_temporal_matching_and_phases.md).

---

### Issue 4: Spatial Buffering Percolation Defect and 5-Fold CV Feasibility
- **Identified Defect:** Stage 8.18 proposed a flat 150 km buffer to prevent spatial autocorrelation leakage before 5-fold cross-validation, without testing whether candidate coordinates would cluster into balanced folds.
- **Empirical Feasibility Testing (No Data Fabrication):** Extracted 250 real candidate coordinates across India from `data/processed/causal_features_2025.parquet` and verified incident tables. Graph percolation analysis proved:
  - At **150 km**, candidate points across the Indo-Gangetic Plain and Central India coal belt chained together into an **85-chip giant component (34.0% of the entire dataset)**.
  - Because 85 chips exceeds the capacity of an individual fold ($N/5 = 50$ chips), balanced 5-fold CV was **mathematically impossible**.
  - At **50 km**, the giant component dissolved: 174 clusters, largest cluster has only **8 chips (3.2%)**, with 130 singletons.
- **Revised Specification:** Locked Sentinel-2 MGRS Tile Blocking ($100 \times 100\text{ km}$) with a $30\text{--}50\text{ km}$ border separation buffer.
- **Greedy Bin-Packing Simulation:** Proved exact, balanced fold allocation: all 5 folds receive exactly 50 chips, with perfectly balanced strata and regional representation.
- **Deliverable:** [`docs/stage8_18a/stage8_18a_spatial_clustering_and_split_feasibility.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18a/stage8_18a_spatial_clustering_and_split_feasibility.md).

---

### Issue 5: Inter-Annotator Agreement Metrics & Edge-Case Handling
- **Identified Defect:** Stage 8.18 stated high-level agreement targets without defining mathematical handling for edge cases (zero bounding boxes, unanimous batches, or extreme negative prevalence).
- **Resolution:** Fully specified mathematical formulations and edge cases:
  1. *Degenerate Kappa ($0/0$):* When $P_o = P_e = 1.0$, defined as $\kappa \equiv 1.00$.
  2. *The Kappa Paradox:* Mandated reporting Prevalence-Adjusted Bias-Adjusted Kappa (PABAK) and Gwet's $AC_1$ alongside Cohen's Kappa.
  3. *Empty Box Sets ($M=0, N=0$):* IoU is undefined for empty sets; strictly excluded from IoU denominator and scored as True Negative Detection Consensus. Unmatched boxes are penalized in Detection F1-score ($\text{IoU} \ge 0.50$).
  4. *Hungarian Matching:* Box-level IoU computed via optimal bipartite assignment.
  5. *Rare-Class Rule:* Any disagreement involving `Industrial Fire` triggers mandatory senior adjudication regardless of batch-level statistics.
- **Deliverable:** [`docs/stage8_18a/stage8_18a_agreement_metrics_specification.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18a/stage8_18a_agreement_metrics_specification.md).

---

### Issue 6: Decision Log & Comparative Evolution
- **Identified Defect:** Need for transparent traceability comparing original Stage 8.18 proposals with Stage 8.18A revisions, empirical rationale, and pending human decisions.
- **Resolution:** Produced comprehensive comparative decision log detailing all six resolved defects and framing four clear, actionable unresolved items requiring human approval.
- **Deliverable:** [`docs/stage8_18a/stage8_18a_decision_log.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18a/stage8_18a_decision_log.md).

---

## 3. Inventory of Stage 8.18A Deliverables

All revised documentation and machine-readable plans are archived under `docs/stage8_18a/`:

| File Name | Description | Lines | Status |
| :--- | :--- | :---: | :---: |
| [`stage8_18a_geographic_partition_spec.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18a/stage8_18a_geographic_partition_spec.md) | Mutually exclusive & exhaustive geographic partitioning spec | 108 | **LOCKED** |
| [`stage8_18a_industrial_fire_sampling_unit.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18a/stage8_18a_industrial_fire_sampling_unit.md) | Hierarchy of incidents, scenes, chips; anti-pseudo-replication | 134 | **LOCKED** |
| [`stage8_18a_temporal_matching_and_phases.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18a/stage8_18a_temporal_matching_and_phases.md) | Active combustion vs post-event scar separation and rules | 114 | **LOCKED** |
| [`stage8_18a_spatial_clustering_and_split_feasibility.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18a/stage8_18a_spatial_clustering_and_split_feasibility.md) | Percolation audit, 150km defect resolution, 5-fold CV proof | 132 | **LOCKED** |
| [`stage8_18a_agreement_metrics_specification.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18a/stage8_18a_agreement_metrics_specification.md) | Cohen's Kappa, PABAK, Gwet's AC1, Hungarian IoU, F1 rules | 126 | **LOCKED** |
| [`stage8_18a_decision_log.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18a/stage8_18a_decision_log.md) | Original vs revised proposal log and unresolved decisions | 109 | **LOCKED** |
| [`sampling_plan_v2.json`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18a/sampling_plan_v2.json) | Authoritative machine-readable sampling plan v2 | 165 | **LOCKED** |
| [`sampling_plan_v2.csv`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18a/sampling_plan_v2.csv) | Authoritative strata quota spreadsheet v2 | 10 | **LOCKED** |
| [`STAGE8_18A_REVIEW_REPORT.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18a/STAGE8_18A_REVIEW_REPORT.md) | This authoritative review and audit sign-off report | ~180 | **LOCKED** |

---

## 4. Preservation & Immutability Verification

1. **Stage 8.18 Planning Artifacts:** All 8 files in `docs/stage8_18/` remain unaltered.
2. **Pilot Dataset Artifacts:** All 78 files in `data/reference/ds08/packages/ds08_pilot_v1/` remain bit-identical and cryptographically verified.
3. **Predecessor Models & Feature Stores:** Parquet feature stores and model weights remain unedited.
4. **Zero Operations Violation:** No CDSE API calls, no raster downloads, no label auto-generation, and no model training scripts were executed.

---

## 5. Unresolved Decisions Requiring Human Sign-Off Before Stage 8.19

Before initiating candidate discovery in Stage 8.19:

1. **[DEC-U1] Approval of 2024 Expansion for Industrial Fires:** Confirm whether candidate discovery for Stratum 1 (Acute Industrial Fires) may query verified 2024 incidents if 2025 clear passes yield fewer than 20 viable scenes.
2. **[DEC-U2] Double-Blind Human Annotation Labor Plan:** Confirm internal dual-pass review using the Stage 8.16 adjudication interface.
3. **[DEC-U3] CDSE Query Rate-Limiting Policy:** Confirm batch limit of 50 scenes with 2.0-second delay.
4. **[DEC-U4] Formal Authorization for Stage 8.19:** Authorize moving to Stage 8.19 (Read-only Candidate Discovery & STAC Manifest Building).
