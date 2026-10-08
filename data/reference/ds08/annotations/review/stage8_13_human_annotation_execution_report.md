# STAGE 8.13 — GENUINE HUMAN DOUBLE ANNOTATION EXECUTION REPORT

**Stage:** Stage 8.13 — Genuine Human Double Annotation Execution  
**Date:** 2026-09-29  
**Status:** **AWAITING GENUINE HUMAN VISUAL ANNOTATION (STRICT STOP ENFORCED — NO FABRICATION)**  
**Authoritative Protocol:** [DS08_ANNOTATION_GUIDELINES_v1.md](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/guidelines/DS08_ANNOTATION_GUIDELINES_v1.md) (v1.0)  
**Machine-Readable Review Record:** [stage8_13_human_annotation_execution_report.json](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/review/stage8_13_human_annotation_execution_report.json)  

---

## 1. Executive Summary

Stage 8.13 is strictly defined as a **genuine manual human annotation execution stage**, not a code generation or data synthesis task.

The prompt imposes an absolute, non-negotiable instruction:
> **DO NOT FABRICATE HUMAN INPUT**  
> The agent must not populate annotation values programmatically, simulate mouse clicks to manufacture annotations, generate labels from code, generate boxes from algorithms, copy labels between annotators, write substantive annotation content into templates, or create fake interaction histories.  
> **If no human is available to perform the annotation, STOP and report that annotation cannot proceed. Do not substitute synthetic annotations.**

In strict adherence to this mandate:
- The AI agent has **NOT** populated any substantive labels, bounding boxes, or evidence into any template.
- All 15 templates for Annotator 1 and all 15 templates for Annotator 2 remain in their pristine, blank state: `task_status: "PENDING_MANUAL_INPUT"`, `annotations: []`, `human_verified: false`.
- The manual annotation UI has been validated and verified.
- Execution is stopped to await genuine manual visual inspection by human Annotator 1 and Annotator 2.

---

## 2. Chip Inventory & Current Annotation Status

The 15 active chips to be annotated are:
1. `PILOT_02_NORTH` (Delhi/Haryana agricultural-urban perimeter)
2. `PILOT_03_NORTH` (Punjab/Haryana intensive agricultural parcel)
3. `PILOT_06_CENTRAL` (Madhya Pradesh forest/scrubland parcel)
4. `PILOT_07_CENTRAL` (Chhattisgarh coal mining/industrial basin parcel)
5. `PILOT_08_CENTRAL` (Odisha dense forest reserve parcel)
6. `PILOT_10_SOUTH` (Karnataka Western Ghats agricultural-forest boundary)
7. `PILOT_11_SOUTH` (Tamil Nadu agricultural parcel)
8. `PILOT_12_SOUTH` (Andhra Pradesh scrub/cropland parcel)
9. `PILOT_14_EAST` (Jharkhand coal basin industrial corridor parcel)
10. `PILOT_15_EAST` (Assam tea garden/wetland agricultural parcel)
11. `PILOT_16_EAST` (West Bengal cropland parcel)
12. `PILOT_18_WEST` (Rajasthan arid agricultural plain)
13. `PILOT_19_WEST` (Gujarat industrial corridor parcel)
14. `PILOT_20_WEST` (Maharashtra agricultural parcel)
15. `PILOT_04_NORTH_REPLACEMENT` (Validated cloud-free replacement chip for original swath-edge chip)

### Annotator 1 Cohort Status (`data/reference/ds08/annotations/manual/annotator_1/`)
- Total Chips: 15
- Completed: **0**
- Pending: **15** (`task_status = "PENDING_MANUAL_INPUT"`)
- `human_verified`: `false` (15 / 15)
- Pre-populated labels / bounding boxes: **0** (100% clean)

### Annotator 2 Cohort Status (`data/reference/ds08/annotations/manual/annotator_2/`)
- Total Chips: 15
- Completed: **0**
- Pending: **15** (`task_status = "PENDING_MANUAL_INPUT"`)
- `human_verified`: `false` (15 / 15)
- Pre-populated labels / bounding boxes: **0** (100% clean)

---

## 3. Human Annotator Workflow & UI Launch Instructions

Because Windows background system processes are currently utilizing ports 8080 (`ApplicationWebServer`) and 8081 (Oracle `TNSLSNR`), free ports **8090** and **8091** should be used.

### Phase 1: Annotator 1 Execution
Annotator 1 opens a terminal and runs:
```bash
python scripts/ds08_annotation_tool.py --ui --annotator annotator_1 --port 8090
```
Then opens `http://localhost:8090` in a web browser.

**Annotator 1 Action Checklist for each of the 15 chips:**
1. Select chip from dropdown.
2. Inspect True-Color RGB and False-Color SWIR imagery (`B12-B11-B04`).
3. Note FIRMS contextual location (`FIRMS CONTEXT — NOT GROUND TRUTH`).
4. Manually determine observation status:
   - If visible fire, smoke, burn scar, or facility: choose `HAS_ANNOTATIONS`.
   - If imagery is clear but no thermal target or fire feature exists: choose `NO_VISIBLE_TARGET`.
   - If ambiguous or obscured: choose `UNRESOLVED`.
5. If `HAS_ANNOTATIONS`:
   - Click and drag on the 512×512 imagery canvas to define bounding box `[x_min, y_min, x_max, y_max]`.
   - Select target class manually (`Industrial Fire`, `Forest Fire`, `Agricultural Fire`, `Other Thermal Source`, `UNRESOLVED`).
   - Check all observed optical evidence (`DIRECT_FIRE_VISIBLE`, `SMOKE_VISIBLE`, `BURN_SCAR_VISIBLE`, etc.).
   - Select visibility status (`CLEAR`, `PARTIALLY_OBSCURED`, `HEAVILY_OBSCURED`).
   - Select geometry confidence and source-class confidence (`HIGH`, `MEDIUM`, `LOW`).
   - Select spatial relationship to FIRMS point.
   - Enter explanatory notes.
6. Click **`Validate & Save Human Annotation`**.
7. Confirm status changes to `COMPLETED_HUMAN_ANNOTATION`.

### Phase 2: Annotator 2 Execution
**Only after Annotator 1 has completed all 15 chips**, Annotator 2 runs:
```bash
python scripts/ds08_annotation_tool.py --ui --annotator annotator_2 --port 8091
```
Then opens `http://localhost:8091` in a separate browser window and annotates the exact same 15 chips completely independently, with zero knowledge of Annotator 1's decisions.

---

## 4. Provenance & File Integrity Verification

- **Quarantine Isolation:** Quarantined Stage 8.11 draft files in `data/reference/ds08/annotations/quarantine/stage8_11_script_generated/` remain untouched and excluded.
- **Genuine Draft Integrity:** The 5 genuine Stage 8.10A draft files in `data/reference/ds08/annotations/draft/` remain byte-for-byte identical.
- **Adjudicated Cohort Integrity:** The 3 final adjudicated files in `data/reference/ds08/annotations/final/` remain byte-for-byte identical.
- **Zero Model Modification:** No model checkpoints were altered; no embeddings were regenerated; fusion data was not modified.

---

## 5. Frozen Predecessor Invariants

All 5 frozen predecessor artifacts match their SHA-256 hashes bit-for-bit:

| Predecessor Artifact | File Type | Frozen Expected SHA-256 Hash | Verification Status |
| :--- | :--- | :--- | :--- |
| `models/tcn/best_tcn.pt` | Model Weights | `dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16` | **VERIFIED (Bit-for-bit match)** |
| `models/deep_sad/best_deep_sad.pt` | Model Weights | `a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa` | **VERIFIED (Bit-for-bit match)** |
| `models/yolo/infrastructure/best_infrastructure.pt` | Model Weights | `bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6` | **VERIFIED (Bit-for-bit match)** |
| `models/yolo/fire_smoke/best_fire_smoke.pt` | Model Weights | `29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227` | **VERIFIED (Bit-for-bit match)** |
| `data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet` | Aligned Parquet | `49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931` | **VERIFIED (Bit-for-bit match)** |

---

## 6. Strict Stop Enforced

In full compliance with the Stage 8.13 prompt:
- **No synthetic annotations were substituted.**
- **No automated labeling was performed.**
- **No agreement metrics (Cohen's kappa, IoU, Jaccard) were computed.**
- **No adjudication was performed.**
- **No models were trained.**

Execution is stopped to allow genuine human annotators to complete visual inspection and annotation via the UI.
