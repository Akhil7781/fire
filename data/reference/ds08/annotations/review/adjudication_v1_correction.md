# Stage 8.10B-C — DS08 Adjudication Record Consistency Correction Report

**Date / Timestamp (UTC):** 2026-09-29T16:10:00Z  
**Phase:** STAGE 8.10B-C (QA & Adjudication Record Correction Addendum)  
**Scope:** Correction of Stage 8.10B reporting inconsistency, scientific wording calibration, and audit verification.

---

## 1. Inconsistencies Identified

During the post-execution audit of Stage 8.10B, two specific issues were identified:
1. **Reporting / Status Matrix Inconsistency (`PILOT_09_SOUTH`):**
   - In the textual summary and status table of the Stage 8.10B execution report, `PILOT_09_SOUTH` was inadvertently written as `Agricultural Fire` in one row, whereas it was established in Stage 8.10A as an agreed `Forest Fire` observation.
2. **Scientific Wording Calibration (`PILOT_17_WEST` & `PILOT_13_EAST`):**
   - The Stage 8.10B report referred to high Band 12 (SWIR) reflectance values as directly measured "thermal emission" or "active SWIR radiance". Because Sentinel-2 Level-2A products provide Bottom-of-Atmosphere (BOA) surface reflectance (unitless ratio $\in [0, 1+]$) rather than calibrated radiance ($W \cdot m^{-2} \cdot sr^{-1} \cdot \mu m^{-1}$) or brightness temperature ($K$), describing B12 directly as "thermal emission" is scientifically imprecise.

---

## 2. Confirmation of `PILOT_09_SOUTH` Status

`PILOT_09_SOUTH` was audited across all underlying records:
- **Annotator 1 Draft:** `HAS_ANNOTATIONS`, 1 bounding box (`[195, 230, 240, 275]`), `class_name: "Forest Fire"`, `class_id: 2`, `confidence: "HIGH"`.
- **Annotator 2 Draft:** `HAS_ANNOTATIONS`, 1 bounding box (`[190, 225, 245, 270]`), `class_name: "Forest Fire"`, `class_id: 2`, `confidence: "HIGH"`.
- **Pre-adjudication Review (`pilot_review_v1.json`):** `class_match: true`, `requires_adjudication: false`, `disagreement_categories: []`.
- **Pre-agreed Status:** `PILOT_09_SOUTH` was a **100% pre-agreed concordant Forest Fire observation** in Stage 8.10A. It was never in dispute, was never a candidate for Stage 8.10B adjudication, and was never adjudicated.

---

## 3. Machine-Readable Annotation File Investigation

Audit confirmed:
- In `data/reference/ds08/annotations/draft/annotator_1/PILOT_09_SOUTH_annotator1.json`, the class has remained `Forest Fire` without modification.
- In `data/reference/ds08/annotations/draft/annotator_2/PILOT_09_SOUTH_annotator2.json`, the class has remained `Forest Fire` without modification.
- In `data/reference/ds08/annotations/review/pilot_adjudication_summary_v1.md`, the record correctly stated: `PILOT_05_CENTRAL (NO_TARGET) & PILOT_09_SOUTH (Forest Fire)`.
- In `data/reference/ds08/annotations/review/adjudication_v1.json`, only the 3 disputed chips (`PILOT_01_NORTH`, `PILOT_13_EAST`, `PILOT_17_WEST`) were recorded.
- **Conclusion:** `PILOT_09_SOUTH` was **never modified on disk** and was never relabeled as Agricultural Fire in any machine-readable dataset file. The error was strictly confined to the conversational summary matrix of the Stage 8.10B completion report.

---

## 4. Files Corrected

1. **`scripts/adjudicate_pilot_chips.py`**:
   - Replaced imprecise phrases (`"lacks concurrent active SWIR thermal emission"`, `"active SWIR radiance"`, `"sharp SWIR hotspot"`) with scientifically conservative phrasing:
     - For `PILOT_13_EAST`: `"lacks elevated SWIR reflectance (chip-wide max B12 is 0.4484) and visible smoke"`.
     - For `PILOT_17_WEST`: `"Peak B12 reflectance reaches 1.4082, accompanied by visible smoke and a fresh charred field-stubble pattern embedded in structured cropland furrows"`.
2. **`data/reference/ds08/annotations/review/adjudication_v1.json`**:
   - Regenerated via updated script with the calibrated scientific wording.
3. **`data/reference/ds08/annotations/review/pilot_adjudication_summary_v1.md`**:
   - Regenerated via updated script with the calibrated scientific wording.
4. **`tests/test_ds08_adjudication.py`**:
   - Added automated tests verifying `PILOT_09_SOUTH` remains Forest Fire in drafts, is absent from `final/`, that the authoritative 5-chip distribution holds, and that no unscientific thermal emission wording exists.

---

## 5. Confirmation: Original A1/A2 Draft Annotations Intact

The 10 original draft files remain strictly unaltered:
- `data/reference/ds08/annotations/draft/annotator_1/` (5 JSON files)
- `data/reference/ds08/annotations/draft/annotator_2/` (5 JSON files)

---

## 6. Authoritative Five-Chip Post-Adjudication Status Matrix

| Chip ID | Pre-Adjudication A1 | Pre-Adjudication A2 | Stage 8.10B Status | Authoritative Label | Class ID | Confidence |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **`PILOT_01_NORTH`** | Agricultural Fire | NO_VISIBLE_TARGET | Disputed (Adjudicated) | **`NO_VISIBLE_TARGET`** | — | — |
| **`PILOT_05_CENTRAL`** | NO_VISIBLE_TARGET | NO_VISIBLE_TARGET | Pre-agreed (Concordant) | **`NO_VISIBLE_TARGET`** | — | — |
| **`PILOT_09_SOUTH`** | Forest Fire | Forest Fire | Pre-agreed (Concordant) | **`Forest Fire`** | 2 | HIGH |
| **`PILOT_13_EAST`** | Forest Fire | UNRESOLVED | Disputed (Adjudicated) | **`UNRESOLVED`** | 0 | LOW |
| **`PILOT_17_WEST`** | Agricultural Fire | Agricultural Fire | Disputed (Adjudicated) | **`Agricultural Fire`** | 3 | HIGH |

### Authoritative Five-Chip Cohort Class Distribution:
- **Forest Fire:** 1 (`PILOT_09_SOUTH`)
- **Agricultural Fire:** 1 (`PILOT_17_WEST`)
- **Industrial Fire:** 0
- **Other Thermal Source / Persistent Non-Biomass Thermal Source:** 0
- **NO_VISIBLE_TARGET:** 2 (`PILOT_01_NORTH`, `PILOT_05_CENTRAL`)
- **UNRESOLVED:** 1 (`PILOT_13_EAST`)

---

## 7. Confirmation of Protocol Decisions

1. **Proposal A (750 m maximum association radius):**
   - Status: **`DEFER`**
   - Policy Code: `ASSOCIATION_RADIUS_POLICY = NOT_YET_FROZEN`
   - No universal association radius is frozen. Spatial association remains context-driven.
2. **Proposal B (Mandatory montane B12 > 0.5 threshold):**
   - Status: **`REJECT`**
   - Policy Code: `MONTANE_B12_THRESHOLD_POLICY = REJECTED_AS_MANDATORY_CRITERION`
   - No mandatory radiometric threshold is introduced. Cool burns and sub-pixel fire scars are preserved without artificial filtering.
3. **Annotation Guidelines Versioning:**
   - Status: **`RETAIN AS VERSION 1.0`**
   - Baseline `DS08_ANNOTATION_GUIDELINES_v1.md` and `ds08_annotation_schema.json` remain fully authoritative. Guidelines v1.1 was NOT created.

---

## 8. Confirmation of Zero Additional Annotations

- Exactly 3 files exist in `data/reference/ds08/annotations/final/`:
  - `PILOT_01_NORTH_adjudicated_v1.json`
  - `PILOT_13_EAST_adjudicated_v1.json`
  - `PILOT_17_WEST_adjudicated_v1.json`
- The remaining 17 pilot chips have **ZERO** files in `final/`.
- No new chips were acquired, chip extraction was not rerun, and no additional annotations were generated.

---

## 9. Full Pytest Execution Results

The full project pytest suite passed with 100% compliance:
- `pytest tests/test_ds08_adjudication.py -v`: 12 passed in 1.12s.
- `pytest -q`: 301 passed in 62.33s.

---

## 10. Frozen Predecessor Artifact SHA-256 Hashes

| Artifact Path | Authoritative Frozen SHA-256 | Verified SHA-256 | Verification |
| :--- | :--- | :--- | :--- |
| `models/tcn/best_tcn.pt` | `dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16` | `dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16` | **MATCH** |
| `models/deep_sad/best_deep_sad.pt` | `a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa` | `a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa` | **MATCH** |
| `models/yolo/infrastructure/best_infrastructure.pt` | `bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6` | `bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6` | **MATCH** |
| `models/yolo/fire_smoke/best_fire_smoke.pt` | `29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227` | `29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227` | **MATCH** |
| `data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet` | `49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931` | `49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931` | **MATCH** |
