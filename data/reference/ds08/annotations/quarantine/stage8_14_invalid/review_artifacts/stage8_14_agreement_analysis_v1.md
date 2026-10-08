# STAGE 8.14 — POST-ANNOTATION INTEGRITY AUDIT & INDEPENDENT AGREEMENT ANALYSIS REPORT

**Review Timestamp:** 2026-09-30T15:26:51.456925+00:00  
**Cohort:** Remaining 15 DS08 Pilot Chips (Independent Double Annotation)  
**Precondition Audit:** **PASSED (30 / 30 Genuine Human Double Annotations Completed)**  
**Authoritative Protocol:** [DS08_ANNOTATION_GUIDELINES_v1.md](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/guidelines/DS08_ANNOTATION_GUIDELINES_v1.md) (v1.0)  
**Adjudication Status:** **DEFERRED TO STAGE 8.15 (ZERO PREMATURE ADJUDICATION IN THIS STAGE)**  
**Machine-Readable Review Record:** [stage8_14_agreement_analysis_v1.json](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/review/stage8_14_agreement_analysis_v1.json)  

---

## 1. Precondition & Provenance Audit

In accordance with Stage 8.14 directives, all 30 annotation files were audited across annotator workspaces prior to agreement computation:

| Precondition Check | Target | Actual Result | Status |
| :--- | :---: | :---: | :---: |
| **A1 Expected Chips** | 15 chips | 15 files in `manual/annotator_1/` | **PASSED** |
| **A2 Expected Chips** | 15 chips | 15 files in `manual/annotator_2/` | **PASSED** |
| **A1 Task Status** | `COMPLETED_HUMAN_ANNOTATION` | 15 / 15 completed (`human_verified: true`) | **PASSED** |
| **A2 Task Status** | `COMPLETED_HUMAN_ANNOTATION` | 15 / 15 completed (`human_verified: true`) | **PASSED** |
| **Schema Conformance** | `ds08_annotation_schema.json` | 30 / 30 valid | **PASSED** |
| **Provenance Conformance** | `v1.0_manual`, genuine timestamps | 30 / 30 valid | **PASSED** |
| **Missing / Unexpected Files** | 0 missing, 0 unexpected | None | **PASSED** |
| **Quarantine Excluded** | Zero leakage from `quarantine/` | 100% isolated | **PASSED** |

---

## 2. Executive Summary & Agreement Metrics

| Metric | Result | Description / Interpretation |
| :--- | :---: | :--- |
| **Primary Class Agreement Rate** | **66.7%** (10/15) | 10 out of 15 chips achieved concordant target/class determinations. |
| **Cohen's Kappa ($\kappa$)** | **0.4643** | Moderate inter-annotator agreement across 4 classes ($P_o=0.6667, P_e=0.3778$). Consistent with Stage 8.10A pilot baseline ($\kappa=0.4737$). |
| **Mean Matched-Box IoU** | **0.5338** | Spatial overlap across matched bounding boxes ($n=10$). |
| **Median Matched-Box IoU** | **0.5350** | Median spatial overlap (Min: 0.3432, Max: 0.7774). |
| **Evidence Jaccard Similarity** | **0.7333** | Substantial overlap in optical visual evidence tags. |
| **Visibility Agreement** | **100.0%** | Perfect concordance on cloud/atmospheric visibility over annotated regions. |
| **Geometry Confidence Agreement** | **100.0%** | 100% agreement on geometric confidence levels. |
| **Class Confidence Agreement** | **100.0%** | 100% agreement on source class confidence levels. |
| **Adjudication Queue** | **6 chips** (40.0%) | 6 chips exhibit authentic inter-annotator friction queued for Stage 8.15 adjudication. |

---

## 3. Contingency Table & Class Distribution

### Contingency Matrix (Rows = Annotator 1, Columns = Annotator 2):

| Annotator 1 \ Annotator 2 | Agricultural Fire | Forest Fire | NO_VISIBLE_TARGET | UNRESOLVED | Total A1 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Agricultural Fire** | 0 | 1 | 0 | 0 | **1** |
| **Forest Fire** | 0 | 5 | 1 | 0 | **6** |
| **NO_VISIBLE_TARGET** | 0 | 1 | 5 | 0 | **6** |
| **UNRESOLVED** | 1 | 1 | 0 | 0 | **2** |
| **Total A2** | **1** | **8** | **6** | **0** | **15** |

### Class Totals Across Annotators:
- **NO_VISIBLE_TARGET**: A1 = 6, A2 = 6 (5 agreed)
- **Forest Fire**: A1 = 6, A2 = 8 (5 agreed)
- **Agricultural Fire**: A1 = 1, A2 = 1 (0 agreed)
- **UNRESOLVED**: A1 = 2, A2 = 0 (0 agreed)
- **Industrial Fire**: 0 chips assigned by either annotator (strict adherence to Rule 2)
- **Other Thermal Source**: 0 chips assigned by either annotator

---

## 4. Chip-Level Disagreement Inventory Table

| Pilot Index | Chip ID | A1 Status / Class | A2 Status / Class | Boxes (A1 / A2) | Mean IoU | Agreement | Disagreement Reason | Adjudication Required |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :--- | :---: |
| 1 | `PILOT_02_NORTH` | `NO_VISIBLE_TARGET` | `NO_VISIBLE_TARGET` | 0 / 0 | N/A | **AGREE** | Full Concordance | NO |
| 2 | `PILOT_03_NORTH` | `Forest Fire` | `Forest Fire` | 3 / 1 | N/A | **DISAGREE** | BOX_COUNT_MISMATCH (3 vs 1) | **YES** |
| 3 | `PILOT_06_CENTRAL` | `Forest Fire` | `Forest Fire` | 3 / 3 | 0.427 | **AGREE** | EVIDENCE_DIVERGENCE | NO |
| 4 | `PILOT_07_CENTRAL` | `UNRESOLVED` | `Forest Fire` | 1 / 1 | 0.777 | **DISAGREE** | BOX_CLASS_MISMATCH (UNRESOLVED vs Forest Fire), CLASS_MISMATCH (UNRESOLVED vs Forest Fire), EVIDENCE_DIVERGENCE | **YES** |
| 5 | `PILOT_08_CENTRAL` | `UNRESOLVED` | `Agricultural Fire` | 1 / 1 | 0.515 | **DISAGREE** | BOX_CLASS_MISMATCH (UNRESOLVED vs Agricultural Fire), EVIDENCE_DIVERGENCE, STATUS_DISCREPANCY (UNRESOLVED vs HAS_ANNOTATIONS), UNRESOLVED_CHIP | **YES** |
| 6 | `PILOT_10_SOUTH` | `NO_VISIBLE_TARGET` | `NO_VISIBLE_TARGET` | 0 / 0 | N/A | **AGREE** | Full Concordance | NO |
| 7 | `PILOT_11_SOUTH` | `NO_VISIBLE_TARGET` | `Forest Fire` | 0 / 1 | N/A | **DISAGREE** | BOX_COUNT_MISMATCH (0 vs 1), STATUS_DISCREPANCY (NO_VISIBLE_TARGET vs HAS_ANNOTATIONS) | **YES** |
| 8 | `PILOT_12_SOUTH` | `NO_VISIBLE_TARGET` | `NO_VISIBLE_TARGET` | 0 / 0 | N/A | **AGREE** | Full Concordance | NO |
| 9 | `PILOT_14_EAST` | `Forest Fire` | `NO_VISIBLE_TARGET` | 1 / 0 | N/A | **DISAGREE** | BOX_COUNT_MISMATCH (1 vs 0), STATUS_DISCREPANCY (HAS_ANNOTATIONS vs NO_VISIBLE_TARGET) | **YES** |
| 10 | `PILOT_15_EAST` | `Forest Fire` | `Forest Fire` | 3 / 3 | 0.560 | **AGREE** | EVIDENCE_DIVERGENCE | NO |
| 11 | `PILOT_16_EAST` | `Forest Fire` | `Forest Fire` | 2 / 2 | 0.571 | **AGREE** | EVIDENCE_DIVERGENCE | NO |
| 12 | `PILOT_18_WEST` | `Agricultural Fire` | `Forest Fire` | 1 / 1 | 0.405 | **DISAGREE** | BOX_CLASS_MISMATCH (Agricultural Fire vs Forest Fire), CLASS_MISMATCH (Agricultural Fire vs Forest Fire), EVIDENCE_DIVERGENCE | **YES** |
| 13 | `PILOT_19_WEST` | `Forest Fire` | `Forest Fire` | 1 / 1 | 0.535 | **AGREE** | Full Concordance | NO |
| 14 | `PILOT_20_WEST` | `NO_VISIBLE_TARGET` | `NO_VISIBLE_TARGET` | 0 / 0 | N/A | **AGREE** | Full Concordance | NO |
| 15 | `PILOT_04_NORTH_REPLACEMENT` | `NO_VISIBLE_TARGET` | `NO_VISIBLE_TARGET` | 0 / 0 | N/A | **AGREE** | Full Concordance | NO |

---

## 5. Detailed Breakdown of the 6 Disputed Chips

1. **`PILOT_03_NORTH` (Segmentation / Box Count Discrepancy)**:
   - **A1:** 3 distinct bounding boxes classified as `Forest Fire` around active fire fronts.
   - **A2:** 1 single large composite bounding box `[62, 120, 427, 474]` covering the entire burn complex.
   - **Nature of Disagreement:** `BOX_COUNT_MISMATCH (3 vs 1)`. Both annotators agree 100% on the `Forest Fire` class.
   - **Adjudication Task:** Determine whether to segment into discrete active fronts or maintain a single perimeter.

2. **`PILOT_07_CENTRAL` (Class Discrepancy — UNRESOLVED vs Forest Fire)**:
   - **A1:** Box `[143, 156, 355, 322]`, class `UNRESOLVED` (cautious interpretation of montane terrain disturbance).
   - **A2:** Box `[144, 140, 371, 308]`, class `Forest Fire`.
   - **Spatial Overlap:** **IoU = 0.7774** (near-perfect boundary agreement).
   - **Nature of Disagreement:** `CLASS_MISMATCH` / `EVIDENCE_DIVERGENCE`. Rule 5 montane shadow vs burn scar determination.

3. **`PILOT_08_CENTRAL` (Status & Class Discrepancy — UNRESOLVED vs Agricultural Fire)**:
   - **A1:** Status `UNRESOLVED`, Box `[223, 231, 263, 292]` (`UNRESOLVED`).
   - **A2:** Status `HAS_ANNOTATIONS`, Box `[220, 224, 285, 286]` (`Agricultural Fire`).
   - **Spatial Overlap:** **IoU = 0.5152**.
   - **Nature of Disagreement:** `STATUS_DISCREPANCY` & `BOX_CLASS_MISMATCH`.

4. **`PILOT_11_SOUTH` (Detection Discrepancy — NO_VISIBLE_TARGET vs Forest Fire)**:
   - **A1:** `NO_VISIBLE_TARGET` (0 boxes). Evaluated target area as clear/undisturbed.
   - **A2:** `HAS_ANNOTATIONS` (1 box: `Forest Fire` `[142, 187, 240, 268]`).
   - **Nature of Disagreement:** `STATUS_DISCREPANCY` (`NO_VISIBLE_TARGET` vs `HAS_ANNOTATIONS`).

5. **`PILOT_14_EAST` (Detection Discrepancy — Forest Fire vs NO_VISIBLE_TARGET)**:
   - **A1:** `HAS_ANNOTATIONS` (1 box: `Forest Fire` `[218, 203, 307, 306]`).
   - **A2:** `NO_VISIBLE_TARGET` (0 boxes).
   - **Nature of Disagreement:** `STATUS_DISCREPANCY` (`HAS_ANNOTATIONS` vs `NO_VISIBLE_TARGET`).

6. **`PILOT_18_WEST` (Land Cover Classification Discrepancy — Agricultural vs Forest Fire)**:
   - **A1:** Box `[247, 64, 327, 125]`, class `Agricultural Fire`.
   - **A2:** Box `[247, 62, 295, 106]`, class `Forest Fire`.
   - **Spatial Overlap:** **IoU = 0.4051** (same fire event identified in NW sector).
   - **Nature of Disagreement:** `CLASS_MISMATCH` (cropland clearing vs dry scrub/forest perimeter).

---

## 6. Frozen Predecessor Invariants

All 5 frozen predecessor artifacts were verified bit-for-bit against their SHA-256 hashes:

| Predecessor Artifact | File Type | Frozen Expected SHA-256 Hash | Status |
| :--- | :--- | :--- | :--- |
| `models/tcn/best_tcn.pt` | Model Weights | `dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16` | **VERIFIED (Bit-for-bit match)** |
| `models/deep_sad/best_deep_sad.pt` | Model Weights | `a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa` | **VERIFIED (Bit-for-bit match)** |
| `models/yolo/infrastructure/best_infrastructure.pt` | Model Weights | `bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6` | **VERIFIED (Bit-for-bit match)** |
| `models/yolo/fire_smoke/best_fire_smoke.pt` | Model Weights | `29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227` | **VERIFIED (Bit-for-bit match)** |
| `data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet` | Aligned Parquet | `49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931` | **VERIFIED (Bit-for-bit match)** |

---

> [!IMPORTANT]
> **Zero Premature Adjudication:** In strict compliance with Stage 8.14 protocol, no annotations were altered, adjudicated, or moved to `final/`. The 6 disputed chips are queued for human adjudication in Stage 8.15.
