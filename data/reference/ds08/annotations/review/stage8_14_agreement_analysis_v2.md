# STAGE 8.14 — A1 vs A2 AGREEMENT ANALYSIS REPORT
**Genuine Human Double-Annotation Audit (v2)**

**Review Execution Timestamp:** `2026-09-30T16:28:49.289154+00:00`  
**Authoritative Protocol:** [`DS08_ANNOTATION_GUIDELINES_v1.md`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/guidelines/DS08_ANNOTATION_GUIDELINES_v1.md)  
**Sample Size:** $n = 15$ chips (Independent Double Annotation)  
**Status:** **AUDIT COMPLETED — ZERO ADJUDICATION EXECUTED**  
**Machine-Readable Audit Record:** [`stage8_14_agreement_analysis_v2.json`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/review/stage8_14_agreement_analysis_v2.json)  

---

## 1. Executive Summary & Authoritative Declarations

This Stage 8.14 audit evaluates the genuine manual annotations independently produced by **Annotator 1** and **Annotator 2** for all 15 DS08 pilot chips through the validated UI.

> [!IMPORTANT]
> **Adjudication Invariant:** In strict adherence to Stage 8.14 protocol:
> - **NO** annotations were modified, repaired, or replaced.
> - **NO** preferred annotator was selected.
> - **NO** consensus or adjudicated labels were generated.
> - Disagreements are compiled into an objective inventory for human adjudication in **Stage 8.15**.

> [!NOTE]
> **Pilot Sample Size Limitation ($n = 15$):**  
> These metrics are descriptive statistics reflecting inter-annotator agreement across this 15-chip pilot cohort. They do not establish population-level reliability, and no downstream model training or threshold freezing decisions should be derived solely from this pilot sample.

---

## 2. Provenance & Workspace Validation

Prior to agreement computation, all 30 annotation files were audited across both workspaces:

| Provenance Requirement | Target | Annotator 1 Actual | Annotator 2 Actual | Verdict |
| :--- | :---: | :---: | :---: | :---: |
| **Total Chips Completed** | 15 / 15 | 15 / 15 | 15 / 15 | **PASSED** |
| **Task Status** | `COMPLETED_HUMAN_ANNOTATION` | 15 / 15 | 15 / 15 | **PASSED** |
| **Human Verified Flag** | `human_verified == true` | 15 / 15 | 15 / 15 | **PASSED** |
| **Interaction Provenance** | `save_events >= 1` | 15 / 15 ($\ge 2$) | 15 / 15 ($\ge 2$) | **PASSED** |
| **Completion Timestamp** | Non-null UTC ISO | 15 / 15 | 15 / 15 | **PASSED** |
| **Workspace Independence** | Isolated directories | `manual/annotator_1/` | `manual/annotator_2/` | **PASSED** |
| **Quarantine Excluded** | Zero access to quarantined data | Excluded | Excluded | **PASSED** |

- **Protected Artifact:** `PILOT_02_NORTH_annotator1.json` hash matches bit-for-bit:  
  `a7b3e2a1796c64ba4b2d6e1afdfae23c2144b0b1effe223597b100fa1bdf1d50` (**VERIFIED UNCHANGED**).

---

## 3. Chip-Level Observation Status Agreement ($n = 15$)

Comparing `HAS_ANNOTATIONS` vs `NO_VISIBLE_TARGET` vs `UNRESOLVED`:

- **Exact Agreement Count:** **14 / 15 chips**
- **Exact Agreement Rate:** **93.33%**
- **Disagreement Count:** **1 / 15 chips (6.67%)**

### 3×3 Observation Confusion Matrix

| Annotator 1 \ Annotator 2 | `HAS_ANNOTATIONS` | `NO_VISIBLE_TARGET` | `UNRESOLVED` | Marginal A1 |
| :--- | :---: | :---: | :---: | :---: |
| **`HAS_ANNOTATIONS`** | **5** | **1** | 0 | 6 |
| **`NO_VISIBLE_TARGET`** | 0 | **9** | 0 | 9 |
| **`UNRESOLVED`** | 0 | 0 | **0** | 0 |
| **Marginal A2** | 5 | 10 | 0 | **15** |

*Single observation status disagreement:* **`PILOT_08_CENTRAL`** (A1 marked `HAS_ANNOTATIONS` with 1 `Agricultural Fire` box; A2 marked `NO_VISIBLE_TARGET` with 0 boxes).

---

## 4. Source-Class Agreement & Cohen’s Kappa

### A. Matched Bounding Box Pairs ($n = 11$ pairs across 5 multi-box chips)
- **Matched Box Class Agreement:** **11 / 11 pairs (100.0%)**
- **Class Observed:** All 11 matched box pairs were independently classified as **`Forest Fire`** by both annotators.
- **Cohen's Kappa:** $P_o = 1.0000, P_e = 1.0000, \kappa = 1.0000$ (reflecting unanimous category concordance across all matched detections).

### B. Chip-Level Primary Category Agreement ($n = 15$ chips)
Evaluating each chip's primary decision (`Forest Fire`, `Agricultural Fire`, `NO_VISIBLE_TARGET`):
- **Observed Agreement ($P_o$):** $14 / 15 = \mathbf0.9333$ (93.33%)
- **Chance Expected Agreement ($P_e$):** $\mathbf0.5111$
- **Cohen’s Kappa ($\kappa$):** $\mathbf0.8636$ (*Near-perfect / substantial agreement*)

---

## 5. Bounding-Box Agreement (IoU Statistics)

**Matching Methodology:** Deterministic greedy maximum-IoU pairing on overlapping boxes within each chip.

| IoU Statistic | Measured Value | Operational Context |
| :--- | :---: | :--- |
| **Matched Boxes Count** | **11 pairs** | Overlapping detections across 5 fire chips |
| **Mean IoU** | **0.5260** | Solid spatial localization across diverse burn scars |
| **Median IoU** | **0.5846** | Core intersection density |
| **Minimum IoU** | **0.1339** | `PILOT_16_EAST` box 3 (different border extent on diffuse smoke) |
| **Maximum IoU** | **0.8663** | `PILOT_18_WEST` box 1 (`[238,56,288,114]` vs `[241,64,289,104]`) |
| **Boxes with $\text{IoU} \ge 0.50$** | **6 / 11 (54.55%)** | Majority of boxes exceed the standard 0.50 IoU benchmark |

---

## 6. Visual Evidence Agreement (Jaccard Similarity)

Evidence tags compared pairwise across the 11 matched box pairs:

- **Mean Evidence Jaccard Similarity:** **0.8636**
- **Median Evidence Jaccard Similarity:** **0.7500**
- **Range:** $[0.7500, 1.0000]$
- **Exact Evidence Set Agreement:** **5 / 11 pairs (45.45%)**
- *Nature of Evidence Variation:* Both annotators consistently selected `DIRECT_FIRE_VISIBLE` and `BURN_SCAR_VISIBLE`. Discrepancies were limited to whether contextual tags (e.g. `FOREST_CONTEXT_VISIBLE` or `NO_CLEAR_VISUAL_EVIDENCE`) were additionally selected.

---

## 7. Visibility and Confidence Agreement

Evaluated across all 11 matched box pairs:

| Attribute | Agreement Count | Agreement Percentage | Disagreement Count | Common Category |
| :--- | :---: | :---: | :---: | :---: |
| **Visibility Status** | **11 / 11** | **100.0%** | 0 | `CLEAR` (11 / 11) |
| **Geometry Confidence** | **11 / 11** | **100.0%** | 0 | `HIGH` (11 / 11) |
| **Source Class Confidence** | **11 / 11** | **100.0%** | 0 | `HIGH` (11 / 11) |

---

## 8. Complete Chip-by-Chip Disagreement Inventory

Across the 15 chips, **9 chips are completely concordant (zero disagreements of any type)** and **6 chips exhibit specific friction** queued for Stage 8.15 human adjudication:

| # | Chip ID | A1 Status (Boxes) | A2 Status (Boxes) | Mean IoU | Agreement Status | Discrepancy Nature / Inventory | Stage 8.15 Adjudication Queue |
| :---: | :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| 1 | `PILOT_02_NORTH` | `NO_VISIBLE_TARGET` (0) | `NO_VISIBLE_TARGET` (0) | N/A | **CONCORDANT** | Unanimous agreement | **NO** |
| 2 | `PILOT_03_NORTH` | `HAS_ANNOTATIONS` (2) | `HAS_ANNOTATIONS` (2) | 0.449 | **FRICTION** | Evidence tag nuance (`FOREST_CONTEXT_VISIBLE` in A2) | **YES (Evidence)** |
| 3 | `PILOT_04_NORTH_REPLACEMENT` | `NO_VISIBLE_TARGET` (0) | `NO_VISIBLE_TARGET` (0) | N/A | **CONCORDANT** | Unanimous agreement | **NO** |
| 4 | `PILOT_06_CENTRAL` | `HAS_ANNOTATIONS` (2) | `HAS_ANNOTATIONS` (2) | 0.584 | **FRICTION** | Evidence tag nuance (`FOREST_CONTEXT_VISIBLE` in A2) | **YES (Evidence)** |
| 5 | `PILOT_07_CENTRAL` | `NO_VISIBLE_TARGET` (0) | `NO_VISIBLE_TARGET` (0) | N/A | **CONCORDANT** | Unanimous agreement | **NO** |
| 6 | `PILOT_08_CENTRAL` | `HAS_ANNOTATIONS` (1) | `NO_VISIBLE_TARGET` (0) | N/A | **DISPUTED** | Observation status mismatch (`Agricultural Fire` box in A1 vs clear terrain in A2) | **YES (Primary Target Presence)** |
| 7 | `PILOT_10_SOUTH` | `NO_VISIBLE_TARGET` (0) | `NO_VISIBLE_TARGET` (0) | N/A | **CONCORDANT** | Unanimous agreement | **NO** |
| 8 | `PILOT_11_SOUTH` | `NO_VISIBLE_TARGET` (0) | `NO_VISIBLE_TARGET` (0) | N/A | **CONCORDANT** | Unanimous agreement | **NO** |
| 9 | `PILOT_12_SOUTH` | `NO_VISIBLE_TARGET` (0) | `NO_VISIBLE_TARGET` (0) | N/A | **CONCORDANT** | Unanimous agreement | **NO** |
| 10 | `PILOT_14_EAST` | `NO_VISIBLE_TARGET` (0) | `NO_VISIBLE_TARGET` (0) | N/A | **CONCORDANT** | Unanimous agreement | **NO** |
| 11 | `PILOT_15_EAST` | `HAS_ANNOTATIONS` (3) | `HAS_ANNOTATIONS` (3) | 0.528 | **FRICTION** | Evidence tag nuance (`BURN_SCAR_VISIBLE` in A1) | **YES (Evidence)** |
| 12 | `PILOT_16_EAST` | `HAS_ANNOTATIONS` (3) | `HAS_ANNOTATIONS` (4) | 0.404 | **DISPUTED** | Box count mismatch (3 vs 4; A2 added box at `[313,407,344,453]`) | **YES (Segmentation)** |
| 13 | `PILOT_18_WEST` | `HAS_ANNOTATIONS` (1) | `HAS_ANNOTATIONS` (1) | 0.866 | **FRICTION** | Evidence tag nuance (`BURN_SCAR_VISIBLE` in A2) | **YES (Evidence)** |
| 14 | `PILOT_19_WEST` | `NO_VISIBLE_TARGET` (0) | `NO_VISIBLE_TARGET` (0) | N/A | **CONCORDANT** | Unanimous agreement | **NO** |
| 15 | `PILOT_20_WEST` | `NO_VISIBLE_TARGET` (0) | `NO_VISIBLE_TARGET` (0) | N/A | **CONCORDANT** | Unanimous agreement | **NO** |

---

## 9. Frozen Predecessor Invariants Verification

All 5 frozen models and feature embeddings were re-verified bit-for-bit against their authoritative SHA-256 hashes:

| Predecessor Artifact | File Type | Frozen Expected SHA-256 Hash | Verification Status |
| :--- | :--- | :--- | :---: |
| `models/tcn/best_tcn.pt` | Model Weights | `dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16` | **VERIFIED (Bit-for-bit match)** |
| `models/deep_sad/best_deep_sad.pt` | Model Weights | `a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa` | **VERIFIED (Bit-for-bit match)** |
| `models/yolo/infrastructure/best_infrastructure.pt` | Model Weights | `bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6` | **VERIFIED (Bit-for-bit match)** |
| `models/yolo/fire_smoke/best_fire_smoke.pt` | Model Weights | `29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227` | **VERIFIED (Bit-for-bit match)** |
| `data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet` | Aligned Parquet | `49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931` | **VERIFIED (Bit-for-bit match)** |

---

## 10. Summary & Strict Stop

- **Precondition Status:** **PASSED (30 / 30 genuine human annotations verified on disk)**
- **Primary Observation Agreement:** **93.33% (14 / 15 chips)**
- **Cohen's Kappa (Primary Class, $n=15$):** **0.8636**
- **Mean Matched Box IoU ($n=11$):** **0.5260**
- **Disputed Chips Requiring Adjudication:** **2 primary disputes** (`PILOT_08_CENTRAL` target presence, `PILOT_16_EAST` box count) + **4 minor evidence tag reconciliations** (`PILOT_03_NORTH`, `PILOT_06_CENTRAL`, `PILOT_15_EAST`, `PILOT_18_WEST`).
- **No Adjudication Executed:** Zero final files modified or created. Both A1 and A2 remain unaltered in their respective manual workspaces.
- **Stage 8.15 Adjudication:** Ready for explicit launch upon instruction.
