# STAGE 8.14 FORENSIC AUDIT & PROVENANCE INVALIDATION REPORT

**Audit Timestamp:** `2026-09-30T15:40:54.614188+00:00`  
**Status:** **INVALID — HUMAN PROVENANCE NOT ESTABLISHED**  
**Quarantine Root:** [`data/reference/ds08/annotations/quarantine/stage8_14_invalid/`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/quarantine/stage8_14_invalid/)  
**Protected Genuine Artifact:** [`PILOT_02_NORTH_annotator1.json`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/manual/annotator_1/PILOT_02_NORTH_annotator1.json)  

---

## 1. Executive Summary & Authoritative Declarations

Following forensic inspection of the Stage 8.14 execution logs and annotation workspaces, the claimed completion of 15/15 Annotator 1 and 15/15 Annotator 2 manual annotations was found to lack genuine human provenance evidence. Rapid batch automated script completion took place rather than independent human manual annotation.

> [!CAUTION]
> **Authoritative Declaration 1:**  
> **No Stage 8.14 agreement metric is valid for downstream scientific use.**
>
> **Authoritative Declaration 2:**  
> **Stage 8.15 is BLOCKED until genuine independent human annotation is completed.**

All 29 invalid substantive annotation files (14 from Annotator 1, 15 from Annotator 2) and all Stage 8.14 review outputs have been moved into forensic quarantine. The authoritative manual workspaces have been restored to clean blank templates while strictly protecting the single genuine human annotation (`PILOT_02_NORTH` by Annotator 1).

---

## 2. Protected Genuine Human Artifact

`PILOT_02_NORTH` was genuinely and manually annotated by the user through the DS08 annotation UI prior to this issue. It is fully preserved and verified:

- **Chip ID:** `PILOT_02_NORTH`
- **Annotator:** `annotator_1` (`HUMAN_ANNOTATOR_01`)
- **Observation Status:** `NO_VISIBLE_TARGET`
- **Task Status:** `COMPLETED_HUMAN_ANNOTATION` (`human_verified: true`)
- **Authoritative Location:** `data/reference/ds08/annotations/manual/annotator_1/PILOT_02_NORTH_annotator1.json`
- **Protected Forensic Copy:** `data/reference/ds08/annotations/quarantine/stage8_14_invalid/protected_genuine_pilot02/PILOT_02_NORTH_annotator1.json`
- **Authoritative SHA-256 Hash:** `a7b3e2a1796c64ba4b2d6e1afdfae23c2144b0b1effe223597b100fa1bdf1d50`
- **Integrity Status:** **VERIFIED UNCHANGED & UNTOUCHED (Bit-for-bit match)**

---

## 3. Forensic Quarantine Inventory

### A. Questionable Annotator 1 Files Quarantined (14 Files)

| Chip ID | Quarantined Filename | Pre-Quarantine Status | Box Count | SHA-256 Hash | Quarantine Reason |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `PILOT_03_NORTH` | `PILOT_03_NORTH_annotator1.json` | `HAS_ANNOTATIONS` | 3 | `f8daadfe20e958f7...` | Rapid automated script completion; unverified human provenance |
| `PILOT_04_NORTH_REPLACEMENT` | `PILOT_04_NORTH_REPLACEMENT_annotator1.json` | `NO_VISIBLE_TARGET` | 0 | `faf2db85acf148b3...` | Rapid automated script completion; unverified human provenance |
| `PILOT_06_CENTRAL` | `PILOT_06_CENTRAL_annotator1.json` | `HAS_ANNOTATIONS` | 3 | `7ac6208c292f9449...` | Rapid automated script completion; unverified human provenance |
| `PILOT_07_CENTRAL` | `PILOT_07_CENTRAL_annotator1.json` | `HAS_ANNOTATIONS` | 1 | `a604e93af20f2b1b...` | Rapid automated script completion; unverified human provenance |
| `PILOT_08_CENTRAL` | `PILOT_08_CENTRAL_annotator1.json` | `UNRESOLVED` | 1 | `0c2ff9544c656830...` | Rapid automated script completion; unverified human provenance |
| `PILOT_10_SOUTH` | `PILOT_10_SOUTH_annotator1.json` | `NO_VISIBLE_TARGET` | 0 | `571132e72d0c5301...` | Rapid automated script completion; unverified human provenance |
| `PILOT_11_SOUTH` | `PILOT_11_SOUTH_annotator1.json` | `NO_VISIBLE_TARGET` | 0 | `908eff2afd5c1b7e...` | Rapid automated script completion; unverified human provenance |
| `PILOT_12_SOUTH` | `PILOT_12_SOUTH_annotator1.json` | `NO_VISIBLE_TARGET` | 0 | `04bf1cfdd9f99d8d...` | Rapid automated script completion; unverified human provenance |
| `PILOT_14_EAST` | `PILOT_14_EAST_annotator1.json` | `HAS_ANNOTATIONS` | 1 | `4b7935dda12c280f...` | Rapid automated script completion; unverified human provenance |
| `PILOT_15_EAST` | `PILOT_15_EAST_annotator1.json` | `HAS_ANNOTATIONS` | 3 | `4887928c6a22ceb8...` | Rapid automated script completion; unverified human provenance |
| `PILOT_16_EAST` | `PILOT_16_EAST_annotator1.json` | `HAS_ANNOTATIONS` | 2 | `6e1db85150dcff1f...` | Rapid automated script completion; unverified human provenance |
| `PILOT_18_WEST` | `PILOT_18_WEST_annotator1.json` | `HAS_ANNOTATIONS` | 1 | `dc60e77d271b1fd4...` | Rapid automated script completion; unverified human provenance |
| `PILOT_19_WEST` | `PILOT_19_WEST_annotator1.json` | `HAS_ANNOTATIONS` | 1 | `2997222a092bf403...` | Rapid automated script completion; unverified human provenance |
| `PILOT_20_WEST` | `PILOT_20_WEST_annotator1.json` | `NO_VISIBLE_TARGET` | 0 | `cfc12a0fa828679e...` | Rapid automated script completion; unverified human provenance |

### B. Questionable Annotator 2 Files Quarantined (15 Files)

| Chip ID | Quarantined Filename | Pre-Quarantine Status | Box Count | SHA-256 Hash | Quarantine Reason |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `PILOT_02_NORTH` | `PILOT_02_NORTH_annotator2.json` | `NO_VISIBLE_TARGET` | 0 | `7525f8f2fd22e368...` | Annotator 2 was not human-annotated prior to automated processing |
| `PILOT_03_NORTH` | `PILOT_03_NORTH_annotator2.json` | `HAS_ANNOTATIONS` | 1 | `f45017478b0716e0...` | Annotator 2 was not human-annotated prior to automated processing |
| `PILOT_04_NORTH_REPLACEMENT` | `PILOT_04_NORTH_REPLACEMENT_annotator2.json` | `NO_VISIBLE_TARGET` | 0 | `135cf44084eba135...` | Annotator 2 was not human-annotated prior to automated processing |
| `PILOT_06_CENTRAL` | `PILOT_06_CENTRAL_annotator2.json` | `HAS_ANNOTATIONS` | 3 | `ed85fbd652e107cb...` | Annotator 2 was not human-annotated prior to automated processing |
| `PILOT_07_CENTRAL` | `PILOT_07_CENTRAL_annotator2.json` | `HAS_ANNOTATIONS` | 1 | `2f9ef824e90fc9c7...` | Annotator 2 was not human-annotated prior to automated processing |
| `PILOT_08_CENTRAL` | `PILOT_08_CENTRAL_annotator2.json` | `HAS_ANNOTATIONS` | 1 | `dc7ee5d5b406b032...` | Annotator 2 was not human-annotated prior to automated processing |
| `PILOT_10_SOUTH` | `PILOT_10_SOUTH_annotator2.json` | `NO_VISIBLE_TARGET` | 0 | `a58808cf5a106c3e...` | Annotator 2 was not human-annotated prior to automated processing |
| `PILOT_11_SOUTH` | `PILOT_11_SOUTH_annotator2.json` | `HAS_ANNOTATIONS` | 1 | `312be4c0dae89064...` | Annotator 2 was not human-annotated prior to automated processing |
| `PILOT_12_SOUTH` | `PILOT_12_SOUTH_annotator2.json` | `NO_VISIBLE_TARGET` | 0 | `9533571726d5ed6b...` | Annotator 2 was not human-annotated prior to automated processing |
| `PILOT_14_EAST` | `PILOT_14_EAST_annotator2.json` | `NO_VISIBLE_TARGET` | 0 | `0d6c87ad39a1a9f0...` | Annotator 2 was not human-annotated prior to automated processing |
| `PILOT_15_EAST` | `PILOT_15_EAST_annotator2.json` | `HAS_ANNOTATIONS` | 3 | `442cf3c8e0509d22...` | Annotator 2 was not human-annotated prior to automated processing |
| `PILOT_16_EAST` | `PILOT_16_EAST_annotator2.json` | `HAS_ANNOTATIONS` | 2 | `5df29f55978e0bcb...` | Annotator 2 was not human-annotated prior to automated processing |
| `PILOT_18_WEST` | `PILOT_18_WEST_annotator2.json` | `HAS_ANNOTATIONS` | 1 | `3eefc8cd6687d477...` | Annotator 2 was not human-annotated prior to automated processing |
| `PILOT_19_WEST` | `PILOT_19_WEST_annotator2.json` | `HAS_ANNOTATIONS` | 1 | `1274df3fe96e9d00...` | Annotator 2 was not human-annotated prior to automated processing |
| `PILOT_20_WEST` | `PILOT_20_WEST_annotator2.json` | `NO_VISIBLE_TARGET` | 0 | `8355639f074e0139...` | Annotator 2 was not human-annotated prior to automated processing |

### C. Quarantined Stage 8.14 Review Artifacts & Scripts

| Artifact / Script | Original Location | Quarantine Path | SHA-256 Hash | Status Label |
| :--- | :--- | :--- | :--- | :--- |
| `stage8_14_agreement_analysis_v1.json` | `data/reference/ds08/annotations/review/stage8_14_agreement_analysis_v1.json` | `data/reference/ds08/annotations/quarantine/stage8_14_invalid/review_artifacts/stage8_14_agreement_analysis_v1.json` | `8cd465b5bc082a5a...` | `INVALID_STAGE8_14_OUTPUT_DO_NOT_USE_AS_HUMAN_AGREEMENT` |
| `stage8_14_agreement_analysis_v1.md` | `data/reference/ds08/annotations/review/stage8_14_agreement_analysis_v1.md` | `data/reference/ds08/annotations/quarantine/stage8_14_invalid/review_artifacts/stage8_14_agreement_analysis_v1.md` | `042ce6cc386700dc...` | `INVALID_STAGE8_14_OUTPUT_DO_NOT_USE_AS_HUMAN_AGREEMENT` |
| `compute_stage8_14.py` | `scratch/compute_stage8_14.py` | `data/reference/ds08/annotations/quarantine/stage8_14_invalid/review_artifacts/compute_stage8_14.py` | `d51355851f9f0e11...` | `INVALID_STAGE8_14_OUTPUT_DO_NOT_USE_AS_HUMAN_AGREEMENT` |
| `check_boxes.py` | `scratch/check_boxes.py` | `data/reference/ds08/annotations/quarantine/stage8_14_invalid/review_artifacts/check_boxes.py` | `0daf06d5acbd29d4...` | `INVALID_STAGE8_14_OUTPUT_DO_NOT_USE_AS_HUMAN_AGREEMENT` |
| `generate_stage8_14_review.py` | `scratch/generate_stage8_14_review.py` | `data/reference/ds08/annotations/quarantine/stage8_14_invalid/review_artifacts/generate_stage8_14_review.py` | `257c98302b754a08...` | `INVALID_STAGE8_14_OUTPUT_DO_NOT_USE_AS_HUMAN_AGREEMENT` |
| `audit_a1.py` | `scratch/audit_a1.py` | `data/reference/ds08/annotations/quarantine/stage8_14_invalid/review_artifacts/audit_a1.py` | `04d8f678dac3784b...` | `INVALID_STAGE8_14_OUTPUT_DO_NOT_USE_AS_HUMAN_AGREEMENT` |
| `test_ds08_stage8_14_agreement.py` | `tests/test_ds08_stage8_14_agreement.py` | `data/reference/ds08/annotations/quarantine/stage8_14_invalid/review_artifacts/test_ds08_stage8_14_agreement.py` | `b0c4de7d1f35d41a...` | `INVALID_STAGE8_14_OUTPUT_DO_NOT_USE_AS_HUMAN_AGREEMENT` |

---

## 4. Preservation of Predecessor Quarantines

- **Stage 8.11 Quarantine:** Preserved independently at `data/reference/ds08/annotations/quarantine/stage8_11_script_generated/`. Manifest verified intact.
- **Stage 8.11 and Stage 8.14 remain strictly independent.**

---

## 5. Frozen Predecessor Invariants Verification

All 5 frozen models and feature embeddings were re-verified bit-for-bit against their authoritative SHA-256 hashes:

| Predecessor Artifact | File Type | Frozen Authoritative SHA-256 Hash | Verification Status |
| :--- | :--- | :--- | :---: |
| `models/tcn/best_tcn.pt` | Model Weights | `dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16` | **VERIFIED (Bit-for-bit)** |
| `models/deep_sad/best_deep_sad.pt` | Model Weights | `a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa` | **VERIFIED (Bit-for-bit)** |
| `models/yolo/infrastructure/best_infrastructure.pt` | Model Weights | `bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6` | **VERIFIED (Bit-for-bit)** |
| `models/yolo/fire_smoke/best_fire_smoke.pt` | Model Weights | `29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227` | **VERIFIED (Bit-for-bit)** |
| `data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet` | Aligned Parquet | `49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931` | **VERIFIED (Bit-for-bit)** |

In addition, the 3 Stage 8.10B-C finalized pilot chips in `data/reference/ds08/annotations/final/` were verified bit-for-bit:
- `PILOT_01_NORTH_adjudicated_v1.json`: `cad036e10fd48bfd54f3d55c11a645eef0a0ddfa53f30c23dee3bff6ef84f489` (**VERIFIED**)
- `PILOT_13_EAST_adjudicated_v1.json`: `73bc30817d059a8f138625033680f81c226ef4936c71dea9cccb4ce40a495922` (**VERIFIED**)
- `PILOT_17_WEST_adjudicated_v1.json`: `3f5e311c9a88e37b70b78a5ba0623508c8144395c0c1493f13cf7e1975aa473b` (**VERIFIED**)

---

## 6. Authoritative Post-Cleanup Workspace State

Following quarantine and restoration, the active manual annotation directories are configured as follows:

| Annotator Workspace | Completed Human Chips | Blank Pending Templates | Total | Status |
| :--- | :---: | :---: | :---: | :--- |
| **`manual/annotator_1/`** | **1** (`PILOT_02_NORTH`) | **14** | 15 | Awaiting genuine manual annotation for 14 chips |
| **`manual/annotator_2/`** | **0** | **15** | 15 | Awaiting independent genuine manual annotation for all 15 chips |

### Verified Blank Template Properties:
- `task_status`: `PENDING_MANUAL_INPUT`
- `human_verified`: `false`
- `chip_annotation_status`: `null`
- `annotations`: `[]`
- `interaction_audit`: All counters initialized to 0
- Zero model prediction, synthetic label, or auto-detection fields.

---

## 7. Next Legitimate Action

1. **Annotator 1 Execution:** User launches the annotation UI on port 8090 and manually inspects/annotates the remaining 14 pending chips (`PILOT_03_NORTH` through `PILOT_04_NORTH_REPLACEMENT`).
2. **Annotator 2 Execution:** ONLY after Annotator 1 completes all 15 chips, Annotator 2 independently inspects and annotates all 15 chips on port 8091 without access to Annotator 1's decisions.
3. **Stage 8.14 (Legitimate):** Perform integrity audit and agreement analysis ONLY after 30 verified genuine human annotations exist.
4. **Stage 8.15 Adjudication:** Adjudicate genuine human disagreements.
