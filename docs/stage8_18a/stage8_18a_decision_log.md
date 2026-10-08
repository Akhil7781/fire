# STAGE 8.18A — PROTOCOL REVIEW DECISION LOG
**Comparative Evolution: Original Proposals, Revised Specifications, Rationale, and Unresolved Decisions**

- **Document Version:** 2.0.0
- **Stage:** Stage 8.18A — Protocol Review & Sign-Off Preparation
- **Status:** **REVISED SPECIFICATION — LOCKED FOR HUMAN REVIEW**
- **Prior Reference:** `docs/stage8_18/stage8_18_decision_log.md` (Version 1.0.0, Preserved)

---

## 1. Architectural Decisions Summary Table

The table below details the six core protocol defects identified during the Stage 8.18 review, the original proposal, the revised Stage 8.18A specification, the scientific rationale, and current resolution status.

| Issue # | Domain / Area | Original Proposal (Stage 8.18) | Revised Specification (Stage 8.18A) | Scientific & Empirical Rationale | Status |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **ISSUE-01** | **Geographic Partitioning** | Heuristic bounding conditions (`lat >= 27.0`, `lon >= 83.0`), creating northeast overlap, island territory ambiguity, and execution order dependence (`PILOT_03_NORTH` misclassified). | Two-tiered partition: Tier 1 MHA Zonal Councils, Tier 2 disjoint mathematical coordinate tree (`classify_indian_region_v2`) with $\text{Lon} \ge 84.0^\circ$ for East. Allocation totals verified: 55 North, 60 Central, 45 South, 50 East, 40 West ($N=250$). | Eliminates spatial overlap, correctly classifies northeastern states in East, and proves mutual exclusivity and exhaustiveness mathematically. | **RESOLVED** |
| **ISSUE-02** | **Acute Industrial Fire Unit** | Quota of 35 chips specified without formal hierarchy between incidents, scenes, and chips. | Strict 3-tier hierarchy: Incident (`incident_id`, Primary Sampling Unit), Scene (`scene_id`), Chip (`chip_id`). Exactly one primary chip per incident in 35-quota. Multi-temporal chips inherit `incident_id` and must be co-located in the same CV fold. | Prevents pseudo-replication and eliminates spatial-temporal data leakage across cross-validation splits. | **RESOLVED** |
| **ISSUE-03** | **Temporal Tiers & Combustion Phases** | Four proximity tiers based solely on absolute delta time $|\Delta t| \le 48\text{ h}$, without physical combustion phase distinction. | Formal separation into `ACTIVE_COMBUSTION` (Tiers 1 & 2, $|\Delta t| \le 6\text{h}$) vs `POST_COMBUSTION_SCAR` (Tiers 3 & 4, $6\text{h} < |\Delta t| \le 48\text{h}$). Strict tagging rules: `DIRECT_FIRE_VISIBLE` prohibited on post-event scars. Distinct benchmark evaluation suites. | Prevents visual evidence contradictions and eliminates invalid scoring penalties on extinguished fires. | **RESOLVED** |
| **ISSUE-04** | **Spatial Buffering & 5-Fold CV** | Flat $150\text{ km}$ buffer around all candidate chips prior to 5-fold cross-validation. | Replaced flat $150\text{ km}$ buffer with Sentinel-2 MGRS Tile Blocking ($100 \times 100\text{ km}$) + $30\text{--}50\text{ km}$ cross-tile buffer. Verified via graph percolation on 250 real candidate coordinates. | Empirical proof showed $150\text{ km}$ causes network percolation into an 85-chip giant component (34% of dataset), making balanced 5-fold CV impossible. At $50\text{ km}$, max cluster is 8 chips (3.2%), enabling 5 balanced folds of 50 chips. | **RESOLVED** |
| **ISSUE-05** | **Agreement Metrics & Edge Cases** | Generic thresholds for Cohen's Kappa, mean IoU, and flag Jaccard without handling edge cases or prevalence skew. | Formal mathematical handling of: (a) Degenerate Kappa ($P_e = P_o = 1.0 \implies \kappa \equiv 1.00$); (b) Kappa Paradox via PABAK and Gwet's $AC_1$; (c) Empty box sets excluded from IoU denominator; (d) Hungarian bipartite matched IoU; (e) Box Detection F1; (f) Mandatory adjudication for rare `Industrial Fire`. | Prevents metric breakdown, zero-division crashes, and skewed reporting in negative or rare-class cohorts. | **RESOLVED** |
| **ISSUE-06** | **Decision Log & Documentation** | Standalone planning document without formal comparative audit. | Dedicated Stage 8.18A versioned review package (`docs/stage8_18a/`) with cross-referenced specs, updated machine-readable sampling plans (`sampling_plan_v2.json`, `sampling_plan_v2.csv`), and full audit report. | Provides complete, immutable provenance and transparent tracking of protocol refinements. | **RESOLVED** |

---

## 2. Detailed Decision Records

### Decision Record 1: Geographic Partition Mutual Exclusivity and Exhaustiveness
- **Original Proposal:** In Stage 8.18, regions were defined by overlapping bounding conditions where points with $\text{Lat} \ge 27.0^\circ$ and $\text{Lon} \ge 83.0^\circ$ (Northeast India) were ambiguously classified. In the pilot acquisition script, sequential `if-elif` logic caused `PILOT_03_NORTH` (Sikkim, Lat 27.20, Lon 87.73) to be labeled `NORTH` instead of `EAST`.
- **Revised Specification:** Stage 8.18A defines a two-tier classification: Tier 1 maps administrative state/UT boundaries per Ministry of Home Affairs Zonal Councils; Tier 2 defines a strictly disjoint mathematical fallback decision tree `classify_indian_region_v2` where all coordinates $\text{Lon} \ge 84.0^\circ\text{E}$ are classified as `EAST`.
- **Rationale:** Ensures that all coordinates in the India bounding box ($\text{Lat} \in [6.0^\circ, 38.0^\circ]$, $\text{Lon} \in [68.0^\circ, 98.0^\circ]$) map to exactly one region with zero overlaps and zero gaps.
- **Verification:** Mathematical proof documented; regional quotas verified ($55 + 60 + 45 + 50 + 40 = 250$).

### Decision Record 2: Acute Industrial Fire Sampling Unit Hierarchy
- **Original Proposal:** Quota of 35 acute industrial fire chips specified without distinguishing ground incidents, satellite scenes, and image chips.
- **Revised Specification:** The Primary Sampling Unit (PSU) is explicitly defined as the unique ground incident (`incident_id`), verified by non-FIRMS external corroboration. Each of the 35 target samples must represent a distinct physical incident. Multi-temporal chips of the same incident are preserved as secondary research chips (`is_primary_chip = false`) and must share the same CV fold.
- **Rationale:** Prevents pseudo-replication and eliminates data leakage across cross-validation splits.

### Decision Record 3: Separation of Combustion Phases in Temporal Matching
- **Original Proposal:** Four temporal matching tiers based solely on absolute time difference $|\Delta t| \le 48\text{h}$.
- **Revised Specification:** Tiers 1 and 2 ($|\Delta t| \le 6\text{h}$) represent `ACTIVE_COMBUSTION` (flaming/smoldering); Tiers 3 and 4 ($6\text{h} < |\Delta t| \le 48\text{h}$) represent `POST_COMBUSTION_SCAR` (burn scar/damage). On post-combustion chips, `DIRECT_FIRE_VISIBLE` is strictly prohibited unless active hot embers with SWIR saturation are verified. Model evaluations are decoupled into active fire detection vs. burn scar mapping benchmarks.
- **Rationale:** Eliminates visual evidence contradictions and ensures fair, physically sound model evaluation.

### Decision Record 4: Resolution of the 150 km Buffer Percolation Defect
- **Original Proposal:** Enforce a flat $150\text{ km}$ buffer around all candidate chips prior to 5-fold cross-validation.
- **Revised Specification:** Replace the $150\text{ km}$ buffer with Sentinel-2 MGRS Tile Blocking ($100 \times 100\text{ km}$) and a $30\text{--}50\text{ km}$ cross-border separation buffer.
- **Rationale:** Empirical testing on 250 real candidate coordinates proved that a $150\text{ km}$ buffer causes network percolation across the Indo-Gangetic and Central belts, creating an 85-point mega-cluster (34% of the dataset) that makes balanced 5-fold CV impossible. At $50\text{ km}$, the largest cluster contains only 8 chips (3.2%), enabling 5 perfectly balanced folds of 50 chips each.

### Decision Record 5: Formal Inter-Annotator Agreement Metrics & Edge-Case Rules
- **Original Proposal:** High-level agreement thresholds without handling edge cases or prevalence skew.
- **Revised Specification:** Explicitly defined Cohen's Kappa degenerate handling ($\kappa \equiv 1.00$ when $P_o = P_e = 1.0$), PABAK and Gwet's $AC_1$ for prevalence-skew mitigation, Hungarian bipartite matched IoU, detection F1-score, and mandatory senior adjudication for rare `Industrial Fire` disagreements. Empty bounding-box chips are excluded from IoU calculations as True Negative consensus.
- **Rationale:** Guarantees numerical stability and prevents metric distortion.

---

## 3. Unresolved Decisions Requiring Human Sign-Off

The following four items remain pending human approval before proceeding to Stage 8.19 (Candidate Discovery):

### DEC-U1: Candidate Discovery Temporal Window for Industrial Fires (2024 vs. 2025 Only)
- **Context:** Historical records indicate approximately 12–14 major verified acute industrial fires occurred in India during 2025. Given Sentinel-2 revisit cycles (5 days) and monsoon cloud cover, clear overpasses within $\le 48\text{h}$ may yield fewer than the target 35 candidate scenes.
- **Decision Required:** Should candidate discovery be permitted to expand into calendar year **2024** for verified major industrial incidents (e.g., Surat, Dahej, Dombivli chemical fires) if 2025 yields fewer than 20 viable scenes?
- **Recommendation:** Approve 2024 expansion for Stratum 1 (Acute Industrial Fires) only, while maintaining 2025 strictly for all other strata.

### DEC-U2: Double-Blind Human Annotation Labor Allocation
- **Context:** Double-blind annotation of 235 candidate chips requires 470 individual annotation tasks plus adjudication.
- **Decision Required:** Confirm whether internal team members will perform the dual-pass annotation or if an external annotation service will be engaged.
- **Recommendation:** Proceed with internal two-pass protocol using the existing Stage 8.16 adjudication interface.

### DEC-U3: CDSE Query Batching & Rate-Limiting Policy
- **Context:** Querying Copernicus Data Space Ecosystem (CDSE) for 235 candidate scenes requires STAC catalog searches and eventual raster downloads.
- **Decision Required:** Confirm batch size limit (e.g., maximum 50 scenes per query batch) and throttling policy to avoid API rate limits.
- **Recommendation:** Enforce batch size of 50 scenes with 2.0-second delay between requests.

### DEC-U4: Formal Authorization to Transition to Stage 8.19
- **Decision Required:** Formal sign-off on the revised Stage 8.18A protocol deliverables, authorizing the transition to Stage 8.19 (Read-only Candidate Discovery & STAC Manifest Building).
- **Condition:** No imagery rasters will be downloaded and no models will be trained during Stage 8.19 without subsequent approval.
