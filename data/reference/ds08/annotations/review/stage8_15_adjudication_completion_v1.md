# Stage 8.15 — Final Human Adjudication Persistence Audit Report

**Audit Status:** `FAIL`  
**Execution Timestamp (UTC):** `2026-09-30T16:58:30Z`  
**Target Workspace:** `data/reference/ds08/annotations/adjudication/review/`  
**Adjudication Scope:** Exactly 6 Disputed Chips (`PILOT_03_NORTH`, `PILOT_06_CENTRAL`, `PILOT_08_CENTRAL`, `PILOT_15_EAST`, `PILOT_16_EAST`, `PILOT_18_WEST`)

---

## 1. Executive Summary & Audit Verdict

In strict accordance with **Stage 8.15 Human Adjudication Rules** (specifically Section 3 *Human Rationale Quality Check* and Section 12 *Final Status Determination*), this read-only persistence audit has evaluated the 6 consensus files submitted through the adjudication interface.

### Final Determination: **`STAGE 8.15 = FAIL`**

### Primary Reasons for Failure:
1. **Human Rationale Quality Check Failure (Section 3)**:
   - Every one of the 6 persisted adjudication files contains the **exact prohibited generic rationale**:
     - `PILOT_03_NORTH`: `"I saw the fire on the image"`
     - `PILOT_06_CENTRAL`: `"i saw the fire in the image"`
     - `PILOT_08_CENTRAL`: `"i saw the fire in the image"`
     - `PILOT_15_EAST`: `"i saw the fire in the image"`
     - `PILOT_16_EAST`: `"i saw the fire in the image"`
     - `PILOT_18_WEST`: `"i saw the fire in the image"`
   - Per Section 3 guidelines: *"Reject generic rationales such as: 'I saw the fire.' 'Looks like fire.' 'Agreed with A1.' 'Agreed with A2.' A rationale must explain the observable visual basis for the decision. DO NOT rewrite the rationale. If a rationale is insufficient: FLAG THE CHIP and STOP. Do not programmatically improve it."*

2. **Placeholder Geometry Contamination**:
   - All 6 files contain the default dummy placeholder bounding box coordinates `[200, 200, 300, 300]` repeated multiple times (e.g. 4x for PILOT_03, 1x for PILOT_06, 2x for PILOT_08, 4x for PILOT_15, 8x for PILOT_16, 4x for PILOT_18).
   - In `PILOT_08_CENTRAL` (an agricultural cropland scene where A1 identified `Agricultural Fire` and A2 identified `NO_VISIBLE_TARGET`), the adjudicated files assigned `Forest Fire` with dummy coordinates `[200, 200, 300, 300]`.
   - The bounding boxes do not reflect visual delineation of actual active fire or burn scar features on the Sentinel-2 imagery.

Per Section 11 (*Strict Prohibitions*), the AI/coding agent has **NOT** rewritten the rationales, modified annotations, or programmatically generated consensus labels. All 6 chips are flagged and Stage 8.15 remains **OPEN / FAILED** until genuine, substantive expert rationales and valid geometries are entered.

---

## 2. Six-Chip Adjudication Persistence & Quality Audit

| Chip ID | File Name | Adjudication Status | Obs Status | Box Count | Final Class | Recorded Rationale | Rationale Validation | Geometry Validation | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`PILOT_03_NORTH`** | `PILOT_03_NORTH_adjudicated_v1.json` | `COMPLETED_HUMAN_ADJUDICATION` | `HAS_ANNOTATIONS` | 4 | `Forest Fire` | `"I saw the fire on the image"` | **FAIL** (Prohibited generic phrase) | **FAIL** (Dummy `[200, 200, 300, 300]` x4) | **FLAGGED / REJECTED** |
| **`PILOT_06_CENTRAL`** | `PILOT_06_CENTRAL_adjudicated_v1.json` | `COMPLETED_HUMAN_ADJUDICATION` | `HAS_ANNOTATIONS` | 1 | `Forest Fire` | `"i saw the fire in the image"` | **FAIL** (Prohibited generic phrase) | **FAIL** (Dummy `[200, 200, 300, 300]`) | **FLAGGED / REJECTED** |
| **`PILOT_08_CENTRAL`** | `PILOT_08_CENTRAL_adjudicated_v1.json` | `COMPLETED_HUMAN_ADJUDICATION` | `HAS_ANNOTATIONS` | 2 | `Forest Fire` | `"i saw the fire in the image"` | **FAIL** (Prohibited generic phrase) | **FAIL** (Dummy `[200, 200, 300, 300]` x2; Cropland misclassified as Forest Fire) | **FLAGGED / REJECTED** |
| **`PILOT_15_EAST`** | `PILOT_15_EAST_adjudicated_v1.json` | `COMPLETED_HUMAN_ADJUDICATION` | `HAS_ANNOTATIONS` | 4 | `Forest Fire` | `"i saw the fire in the image"` | **FAIL** (Prohibited generic phrase) | **FAIL** (Dummy `[200, 200, 300, 300]` x4) | **FLAGGED / REJECTED** |
| **`PILOT_16_EAST`** | `PILOT_16_EAST_adjudicated_v1.json` | `COMPLETED_HUMAN_ADJUDICATION` | `HAS_ANNOTATIONS` | 8 | `Forest Fire` | `"i saw the fire in the image"` | **FAIL** (Prohibited generic phrase) | **FAIL** (Dummy `[200, 200, 300, 300]` x8) | **FLAGGED / REJECTED** |
| **`PILOT_18_WEST`** | `PILOT_18_WEST_adjudicated_v1.json` | `COMPLETED_HUMAN_ADJUDICATION` | `HAS_ANNOTATIONS` | 4 | `Forest Fire` | `"i saw the fire in the image"` | **FAIL** (Prohibited generic phrase) | **FAIL** (Dummy `[200, 200, 300, 300]` x4) | **FLAGGED / REJECTED** |

**Summary**: 6 / 6 files persisted to disk, but 0 / 6 pass substantive human rationale and geometry validation.

---

## 3. Immutable Source File Integrity (12 Disputed Records)

Recalculation of SHA-256 hashes against pre-adjudication baselines recorded at Stage 8.15 start:

| Chip ID | Annotator 1 Expected | Annotator 1 Actual | A1 Match | Annotator 2 Expected | Annotator 2 Actual | A2 Match |
| :--- | :--- | :--- | :---: | :--- | :--- | :---: |
| `PILOT_03_NORTH` | `4ea58e129deacc36660c26527cd4e235ccda250d0a0dcb344e3a5e82ea6a79dd` | `4ea58e129deacc36660c26527cd4e235ccda250d0a0dcb344e3a5e82ea6a79dd` | **PASS** | `d464b2f542071ea100ffedf73de863f12e1377c4fe300345af626d7ea1848f00` | `d464b2f542071ea100ffedf73de863f12e1377c4fe300345af626d7ea1848f00` | **PASS** |
| `PILOT_06_CENTRAL` | `88acb76ba6b4c1ee7805a476a07fea307bc1c5440208f5b94c8afc4ab2822615` | `88acb76ba6b4c1ee7805a476a07fea307bc1c5440208f5b94c8afc4ab2822615` | **PASS** | `46d6dc9efa99c94d43f4eaac5d8fccec06dfc081166d4f14e5436588032242d9` | `46d6dc9efa99c94d43f4eaac5d8fccec06dfc081166d4f14e5436588032242d9` | **PASS** |
| `PILOT_08_CENTRAL` | `643a579d93e4d2ce88ab03ad3d01790f9c322b8f12ebb1ca5ca7e0216eae69c7` | `643a579d93e4d2ce88ab03ad3d01790f9c322b8f12ebb1ca5ca7e0216eae69c7` | **PASS** | `b3acc39e10c4bdf760949066bd0b263bd78e226b803883d27cc4e0a2fffd844e` | `b3acc39e10c4bdf760949066bd0b263bd78e226b803883d27cc4e0a2fffd844e` | **PASS** |
| `PILOT_15_EAST` | `a68f9383dccecb93dbd9755e0d629be0ddc685da555d9132c7297e446eae5759` | `a68f9383dccecb93dbd9755e0d629be0ddc685da555d9132c7297e446eae5759` | **PASS** | `c21eb67c1b0b1852a4b4892fb0ce07d779918fd3ccf792c25543050cae6b029d` | `c21eb67c1b0b1852a4b4892fb0ce07d779918fd3ccf792c25543050cae6b029d` | **PASS** |
| `PILOT_16_EAST` | `7d7f079047c191a8ff315298554e7b56a2a5e065627349a5b8a8e9ff4b5c9939` | `7d7f079047c191a8ff315298554e7b56a2a5e065627349a5b8a8e9ff4b5c9939` | **PASS** | `eabd01e9dccb1ce0b0c46145b32d061c63e69fa2328d053066940cfe5d04d9fd` | `eabd01e9dccb1ce0b0c46145b32d061c63e69fa2328d053066940cfe5d04d9fd` | **PASS** |
| `PILOT_18_WEST` | `8714e286dbad7610e7a79b6ee6e1ef1cae30deef33ad04244fdc3aacf943c257` | `8714e286dbad7610e7a79b6ee6e1ef1cae30deef33ad04244fdc3aacf943c257` | **PASS** | `54ba4215c080fe79eae0a3200db971a7e4b04f7820fa2f2950d5c95e5988b4f6` | `54ba4215c080fe79eae0a3200db971a7e4b04f7820fa2f2950d5c95e5988b4f6` | **PASS** |

**Source Workspace Integrity:** 12 / 12 files remain 100% bit-for-bit identical to pre-adjudication state.

---

## 4. Protected Pilot File Verification

- **Path:** `data/reference/ds08/annotations/manual/annotator_1/PILOT_02_NORTH_annotator1.json`
- **Expected SHA-256:** `a7b3e2a1796c64ba4b2d6e1afdfae23c2144b0b1effe223597b100fa1bdf1d50`
- **Actual SHA-256:** `a7b3e2a1796c64ba4b2d6e1afdfae23c2144b0b1effe223597b100fa1bdf1d50`
- **Status:** **PASS** (Protected human benchmark unmodified)

---

## 5. Frozen Predecessor Model & Fusion Integrity

| Predecessor Artifact | Expected SHA-256 | Actual SHA-256 | Verification |
| :--- | :--- | :--- | :---: |
| `models/tcn/best_tcn.pt` | `dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16` | `dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16` | **PASS** |
| `models/deep_sad/best_deep_sad.pt` | `a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa` | `a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa` | **PASS** |
| `models/yolo/infrastructure/best_infrastructure.pt` | `bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6` | `bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6` | **PASS** |
| `models/yolo/fire_smoke/best_fire_smoke.pt` | `29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227` | `29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227` | **PASS** |
| `data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet` | `49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931` | `49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931` | **PASS** |

---

## 6. Directory Hygiene & Modification Audit

- **Adjudication Review Dir:** Contains exactly 6 `*_adjudicated_v1.json` files. No extra consensus files exist.
- **Model Files Modified:** 0
- **Embedding Files Modified:** 0
- **Fusion Parquets Modified:** 0
- **A1 Files Modified:** 0
- **A2 Files Modified:** 0
- **Quarantine Files Modified:** 0
- **Annotation Guidelines Modified:** 0

---

## 7. Relevant Test Execution Summary

- `tests/test_ds08_stage8_14_agreement_v2.py`: **5 / 5 passed**
- `tests/test_ds08_adjudication.py`: **12 / 12 passed**
- `tests/test_ds08_annotation_schema.py`: **14 / 14 passed**
- Total relevant tests: **31 passed, 0 failed**

---

## 8. Final Audit Determination and Action Required

```
======================================================================
STAGE 8.15 ADJUDICATION PERSISTENCE AUDIT: FAIL
======================================================================
```

**Required Corrective Action:**
1. The human adjudicator must provide genuine, chip-specific observable visual evidence rationales (explaining what was seen in RGB/SWIR imagery) for each of the 6 disputed chips.
2. The bounding box geometries must be visually delineated to correspond to the physical targets rather than the dummy placeholder `[200, 200, 300, 300]`.
3. The AI agent must remain stopped without modifying any annotations programmatically.
