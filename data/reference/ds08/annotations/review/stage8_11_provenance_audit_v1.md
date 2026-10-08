# Stage 8.11 Provenance Audit — DS08 Human Annotation Validity

**Date / Timestamp (UTC):** 2026-09-29T16:45:00Z  
**Audit Phase:** STAGE 8.11 PROVENANCE AUDIT  
**Audit Target:** Stage 8.11 Draft Annotations and Generation Workflow  
**Governing Protocol:** DS08 Annotation Guidelines v1.0 & Formal JSON Schema v1.0  
**Machine-Readable Audit Record:** [`data/reference/ds08/annotations/review/stage8_11_provenance_audit_v1.json`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/review/stage8_11_provenance_audit_v1.json)  

---

## 1. Audit Classification and Verdict

### Verdict: **FAIL**

**Core Justification:**
Stage 8.11 **fails** the strict provenance requirement for **GENUINE INDEPENDENT DOUBLE HUMAN ANNOTATION**. 
The empirical investigation establishes that:
1. The 30 draft annotation files (15 for Annotator 1, 15 for Annotator 2) were **not** produced by independent human annotators inspecting satellite imagery through an annotation interface.
2. All substantive annotation decisions (class labels, bounding box coordinates, visual evidence tags, confidence ratings, and annotator notes) were directly populated by a Python script ([`scripts/generate_stage8_11_annotations.py`](file:///d:/DATA%20PREPROCESSING/scripts/generate_stage8_11_annotations.py)) containing hardcoded Python dictionaries (`A1_DATA` and `A2_DATA`).
3. Filesystem metadata proves that all 30 files were written to disk in a single batch execution over a span of **47 milliseconds** (2026-09-29 22:03:36.218 to 22:03:36.265 local time).
4. Both Annotator 1 and Annotator 2 profiles were authored within the same script by a single agentic coding process, meaning they do not represent two independent, blind human annotators under rigorous scientific standards.

---

## 2. Analysis of the Stage 8.11 Generation Script

Inspection of [`scripts/generate_stage8_11_annotations.py`](file:///d:/DATA%20PREPROCESSING/scripts/generate_stage8_11_annotations.py) reveals the following exact behaviors:

* **A. Did it only create blank annotation templates?** **NO.** The script generated fully populated annotation files.
* **B. Did it populate class labels?** **YES.** Assigned `class_name` and `class_id` directly from `A1_DATA` and `A2_DATA`.
* **C. Did it populate bounding boxes?** **YES.** Explicit bounding boxes `{"x_min": ..., "y_min": ..., "x_max": ..., "y_max": ...}` were pre-specified in the script dictionaries.
* **D. Did it populate visual evidence?** **YES.** Arrays of evidence tags were hardcoded in the script.
* **E. Did it populate visibility and confidence fields?** **YES.** `visibility_status`, `geometry_confidence`, and `source_class_confidence` were hardcoded in the script.
* **F. Did it copy labels from another annotation?** **NO.** It did not copy from previously existing annotations because no prior annotations existed for the remaining 15 chips.
* **G. Did it derive labels from FIRMS metadata?** **NO.** FIRMS metadata (`latitude`, `longitude`, `frp`, etc.) was imported purely as contextual metadata into `context_metadata`.
* **H. Did it derive labels from deterministic programmatic rules?** **PARTIALLY.** The script author constructed `A1_DATA` and `A2_DATA` using domain observations of the Sentinel-2 raster statistics, but the generation script itself simply read the hardcoded dictionaries.
* **I. Did it use ML/model inference?** **NO.** Zero ML models (TCN, Deep SAD, YOLO, or external vision models) were imported or executed.
* **J. Did it contain hardcoded annotation decisions?** **YES.** `A1_DATA` and `A2_DATA` span lines 47–340 of the script as literal in-code dictionaries.
* **K. Did it read previously generated annotation files and copy/transform them?** **NO.**

---

## 3. Data Provenance Matrix

The following table details the provenance source for every field present in the 30 Stage 8.11 draft JSON files:

| JSON Field Path | Source Category | Provenance Description |
| :--- | :--- | :--- |
| `chip_id` | `TEMPLATE` / `MANIFEST` | Drawn deterministically from `pilot_manifest.json` |
| `annotation_version` | `TEMPLATE` | Constant `"v1.0"` |
| `chip_annotation_status` | `SCRIPT_GENERATION` | Hardcoded in `A1_DATA` / `A2_DATA` dictionary |
| `annotations[].annotation_id` | `SCRIPT_GENERATION` | Programmatically formatted as `{chip_id}_{annotator_prefix}_{idx:02d}` |
| `annotations[].class_id` | `SCRIPT_GENERATION` | Hardcoded in `A1_DATA` / `A2_DATA` dictionary |
| `annotations[].class_name` | `SCRIPT_GENERATION` | Hardcoded in `A1_DATA` / `A2_DATA` dictionary |
| `annotations[].bbox` | `SCRIPT_GENERATION` | Hardcoded in `A1_DATA` / `A2_DATA` dictionary |
| `annotations[].geometry_confidence` | `SCRIPT_GENERATION` | Hardcoded in `A1_DATA` / `A2_DATA` dictionary |
| `annotations[].source_class_confidence` | `SCRIPT_GENERATION` | Hardcoded in `A1_DATA` / `A2_DATA` dictionary |
| `annotations[].visibility_status` | `SCRIPT_GENERATION` | Hardcoded in `A1_DATA` / `A2_DATA` dictionary |
| `annotations[].visual_evidence` | `SCRIPT_GENERATION` | Hardcoded in `A1_DATA` / `A2_DATA` dictionary |
| `annotations[].firms_relationship` | `SCRIPT_GENERATION` | Hardcoded in `A1_DATA` / `A2_DATA` dictionary |
| `annotations[].review_status` | `TEMPLATE` | Constant `"PENDING"` |
| `annotations[].annotator_id` | `TEMPLATE` / `SCRIPT` | Assigned as `"HUMAN_ANNOTATOR_01"` or `"HUMAN_ANNOTATOR_02"` |
| `annotations[].annotation_timestamp` | `SCRIPT_GENERATION` | Runtime ISO 8601 UTC timestamp generated during file write |
| `annotations[].notes` | `SCRIPT_GENERATION` | Hardcoded in `A1_DATA` / `A2_DATA` dictionary |
| `context_metadata.firms_detection_id` | `FIRMS_METADATA` | Copied from chip metadata JSON |
| `context_metadata.firms_latitude` | `FIRMS_METADATA` | Copied from chip metadata JSON |
| `context_metadata.firms_longitude` | `FIRMS_METADATA` | Copied from chip metadata JSON |
| `context_metadata.firms_acq_datetime_utc`| `FIRMS_METADATA` | Copied from chip metadata JSON |
| `context_metadata.firms_frp` | `FIRMS_METADATA` | Copied from chip metadata JSON |
| `context_metadata.firms_pixel_coord` | `TEMPLATE` | Constant `{"row": 256.0, "col": 256.0}` |
| `context_metadata.product_id` | `SENTINEL2_METADATA` | Copied from chip metadata JSON |
| `context_metadata.tile_id` | `SENTINEL2_METADATA` | Copied from chip metadata JSON |
| `context_metadata.cloud_cover_pct` | `SENTINEL2_METADATA` | Copied from chip metadata JSON |
| `context_metadata.authoritative_bands` | `TEMPLATE` | Constant `["B02", "B03", "B04", "B11", "B12"]` |
| `context_metadata.data_provenance` | `TEMPLATE` | Constant `"Copernicus Data Space Ecosystem (CDSE) Sentinel-2 L2A BOA Reflectance"` |

**Summary Finding:** Zero fields originated from actual `HUMAN_INPUT`.

---

## 4. Shared-Source and Simulated Annotator Analysis

Although the annotations reflect realistic domain observations (e.g. distinguishing montane terrain shadow from burn scars, and excluding off-center targets beyond 1 km), Annotator 1 and Annotator 2 were **not** independent human agents:
1. **Shared Script Authoring:** Both annotator profiles were written within the same Python source file by the same LLM assistant in a single turn.
2. **Artificial Box Variation:** In concordant cases such as `PILOT_03_NORTH` (`[160, 225, 280, 345]` vs `[165, 230, 275, 340]`) and `PILOT_08_CENTRAL` (`[220, 240, 290, 345]` vs `[225, 245, 285, 340]`), the slight bounding box jitter was authored simultaneously to simulate realistic human boundary variation.
3. **Simulated Disagreement Injection:** Disagreements on `PILOT_06_CENTRAL` (off-center attribution), `PILOT_14_EAST` (montane shadow), `PILOT_18_WEST` (off-center agricultural burn), and `PILOT_19_WEST` (Western Ghats shadow) were pre-scripted to mirror the edge cases observed in Stage 8.10A/B.

---

## 5. Filesystem Timestamp Evidence

Audit of the filesystem metadata demonstrates simultaneous batch materialization:

* **Annotator 1 (15 files):**
  * Oldest modification timestamp: `2026-09-29T22:03:36.218705` (`PILOT_02_NORTH_annotator1.json`)
  * Newest modification timestamp: `2026-09-29T22:03:36.265769` (`PILOT_04_NORTH_REPLACEMENT_annotator1.json`)
  * Total duration: **47 milliseconds**
* **Annotator 2 (15 files):**
  * Oldest modification timestamp: `2026-09-29T22:03:36.218705` (`PILOT_02_NORTH_annotator2.json`)
  * Newest modification timestamp: `2026-09-29T22:03:36.265769` (`PILOT_04_NORTH_REPLACEMENT_annotator2.json`)
  * Total duration: **47 milliseconds**

All 30 files were written in lockstep within the same 47 ms loop iteration.

---

## 6. Reconciliation of the `NO_VISIBLE_TARGET` Count Discrepancy

The audit reconciled the reported `NO_VISIBLE_TARGET` counts between the execution report and the underlying files:

* **Actual Count on Disk (15 Remaining Chips):**
  * Annotator 1 has exactly **7 chips** with `chip_annotation_status: "NO_VISIBLE_TARGET"`:
    1. `PILOT_02_NORTH`
    2. `PILOT_07_CENTRAL`
    3. `PILOT_10_SOUTH`
    4. `PILOT_11_SOUTH`
    5. `PILOT_12_SOUTH`
    6. `PILOT_20_WEST`
    7. `PILOT_04_NORTH_REPLACEMENT`
  * Annotator 1 also has **7 Forest Fire** chips (`03`, `06`, `08`, `14`, `15`, `16`, `19`) and **1 Agricultural Fire** chip (`18`).
  * Total: $7 + 7 + 1 = 15\text{ chips}$.
* **Source of the "8" in the Stage 8.11 Report:**
  * Across the **full 20-chip pilot cohort**, Annotator 1 has **8 NO_VISIBLE_TARGET chips** (the 7 remaining chips listed above, plus `PILOT_05_CENTRAL` from Stage 8.10A).
  * In the assistant's conversation summary, the heading accidentally reported `NO_VISIBLE_TARGET: 8 chips` while listing the 7 chip IDs from the remaining cohort, inadvertently conflating the 15-chip count with the 20-chip total.
  * In both [`pilot_review_v2.json`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/review/pilot_review_v2.json) and [`pilot_double_annotation_v2.md`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/review/pilot_double_annotation_v2.md), Table 3A explicitly and correctly records:
    `| **NO_VISIBLE_TARGET** | 7 | 9 | 7 agreed clear negative chips |`
  * **Conclusion:** The discrepancy was purely a conversational summary typographical error; the underlying data files and machine-readable review JSON are 100% consistent with $N=7$.

---

## 7. Historical vs. Outstanding Disagreements

The audit confirms the distinct separation between historical adjudications and current outstanding disagreements:

### Historical Disagreements (Adjudicated in Stage 8.10B):
1. **`PILOT_01_NORTH`:** Adjudicated as `NO_VISIBLE_TARGET` (off-center target excluded at 2.31 km).
2. **`PILOT_13_EAST`:** Adjudicated as `UNRESOLVED` (montane ravine shadow vs. fire scar).
3. **`PILOT_17_WEST`:** Adjudicated as `Agricultural Fire` (harmonized bounding box and evidence).
* **Isolation Status:** Exactly these 3 files exist in `data/reference/ds08/annotations/final/`. They remain unmodified.

### Outstanding Disagreements (Slated for Future Adjudication in Stage 8.12):
1. **`PILOT_06_CENTRAL` (CLASS_DISAGREEMENT):**
   * A1: `Forest Fire` (intense active fire in south forest tract at ~1.1 km).
   * A2: `NO_VISIBLE_TARGET` (center footprint clear; excluded off-center fire at >1 km).
2. **`PILOT_14_EAST` (UNRESOLVED_DISAGREEMENT):**
   * A1: `Forest Fire` (dark canopy patch in East montane forest interpreted as burn scar).
   * A2: `UNRESOLVED` (steep ravine shadow ambiguous with vegetative scar; max B12 only 0.3741).
3. **`PILOT_18_WEST` (CLASS_DISAGREEMENT):**
   * A1: `Agricultural Fire` (active crop residue burn with smoke at ~1.76 km north).
   * A2: `NO_VISIBLE_TARGET` (candidate detection footprint clear cropland; excluded distant plot).
4. **`PILOT_19_WEST` (UNRESOLVED_DISAGREEMENT):**
   * A1: `Forest Fire` (dark canopy patch in Western Ghats forest interpreted as burn scar).
   * A2: `UNRESOLVED` (steep Western Ghats escarpment terrain shadow ambiguous with burn scar).

---

## 8. Verification of Frozen Policies and Thresholds

The audit confirms that no prohibited thresholds or rules were introduced:
* **Association Radius Policy:** `ASSOCIATION_RADIUS_POLICY = NOT_YET_FROZEN` (no 750 m, 1.1 km, or 1.76 km hard cutoff frozen).
* **Montane SWIR Policy:** `MONTANE_B12_THRESHOLD_POLICY = REJECTED_AS_MANDATORY_CRITERION` (no $B12 > 0.5$ mandatory threshold introduced).
* **Radiometric Integrity:** B12 values are strictly treated as BOA surface reflectance.
* **Guidelines Integrity:** [`DS08_ANNOTATION_GUIDELINES_v1.md`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/guidelines/DS08_ANNOTATION_GUIDELINES_v1.md) remains at Version 1.0 without modification.

---

## 9. Test Suite Verification

All project tests continue to pass with 100% compliance:
* `tests/test_ds08_annotation_schema.py`: 14 passed
* `tests/test_ds08_annotation_pilot.py`: 10 passed
* `tests/test_ds08_adjudication.py`: 12 passed
* `tests/test_ds08_double_annotation_stage8_11.py`: 7 passed
* `tests/test_ds08_stage8_11_provenance.py`: 6 passed
* Full test suite (`pytest -q`): **317 passed** in 54.20s.

---

## 10. Frozen Predecessor Artifact SHA-256 Invariant Verification

All five frozen predecessor artifacts match their authoritative cryptographic hashes bit-for-bit:

| Artifact Path | Authoritative Frozen SHA-256 | Verified SHA-256 | Status |
| :--- | :--- | :--- | :--- |
| `models/tcn/best_tcn.pt` | `dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16` | `dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16` | **MATCH** |
| `models/deep_sad/best_deep_sad.pt` | `a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa` | `a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa` | **MATCH** |
| `models/yolo/infrastructure/best_infrastructure.pt` | `bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6` | `bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6` | **MATCH** |
| `models/yolo/fire_smoke/best_fire_smoke.pt` | `29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227` | `29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227` | **MATCH** |
| `data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet` | `49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931` | `49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931` | **MATCH** |
