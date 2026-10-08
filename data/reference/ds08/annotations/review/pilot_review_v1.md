# STAGE 8.10A — DS08 HUMAN ANNOTATION PILOT REVIEW REPORT

**Review Timestamp:** 2026-09-29T15:38:38.083805+00:00  
**Chips Evaluated:** 5 (Independent Double-Pass)  
**Adjudication Status:** **PENDING (NO FINAL ADJUDICATION IN THIS STAGE)**  

## 1. Executive Summary & Pilot QA Metrics

| Metric | Result | Description / Target |
| :--- | :--- | :--- |
| **Class Agreement Rate** | **60.0%** (3/5) | 3 out of 5 chips achieved identical class/target determination. |
| **Cohen's Kappa ($\kappa$)** | **0.4737** | Calculated over n=5 samples across 4 categories. |
| **Mean Matched-Box IoU** | **0.7141** | High spatial boundary consistency for matched boxes (target $\ge 0.70$). |
| **Evidence Jaccard Similarity** | **0.6667** | Substantial overlap in selected optical evidence tags. |
| **Visibility Agreement** | **100.0%** | 100% agreement on atmospheric/cloud visibility over target regions. |
| **Disagreement Rate** | **60.0%** | 2 of 5 chips exhibited authentic inter-annotator friction. |
| **Adjudication Queue** | **3 chips** | `PILOT_01_NORTH, PILOT_13_EAST, PILOT_17_WEST` queued for Stage 8.10B review. |

---

## 2. Class Distribution Across Annotators

| Class / Status | Annotator 1 | Annotator 2 | Notes |
| :--- | :---: | :---: | :--- |
| **Agricultural Fire** | 2 | 1 | Full agreement on PILOT_17; divergence on PILOT_01 off-center target. |
| **Forest Fire** | 2 | 1 | Full agreement on PILOT_09 ridge wildfire; divergence on PILOT_13 scar vs UNRESOLVED. |
| **Industrial Fire** | 0 | 0 | 0 chips classified as Industrial Fire (strictly adherence to Rule 2). |
| **Other Thermal Source** | 0 | 0 | 0 chips classified as Other Thermal Source. |
| **NO_VISIBLE_TARGET** | 1 | 2 | Full agreement on PILOT_05 clear-sky center; PILOT_01 center empty. |
| **UNRESOLVED** | 0 | 1 | PILOT_13 assigned UNRESOLVED by Annotator 2 (Rule 5 compliance). |

---

## 3. Per-Chip Comparison & Disagreement Analysis

| Chip ID | A1 Status / Class | A2 Status / Class | Matched IoU | Disagreements | Requires Adjudication |
| :--- | :--- | :--- | :---: | :--- | :---: |
| `PILOT_01_NORTH` | `HAS_ANNOTATIONS` | `NO_VISIBLE_TARGET` | N/A | CLASS_DISAGREEMENT | **YES** |
| `PILOT_05_CENTRAL` | `NO_VISIBLE_TARGET` | `NO_VISIBLE_TARGET` | N/A | NONE (Full Agreement) | NO |
| `PILOT_09_SOUTH` | `HAS_ANNOTATIONS` | `HAS_ANNOTATIONS` | 0.722 | NONE (Full Agreement) | NO |
| `PILOT_13_EAST` | `HAS_ANNOTATIONS` | `UNRESOLVED` | 0.716 | EVIDENCE_DISAGREEMENT, UNRESOLVED_DISAGREEMENT | **YES** |
| `PILOT_17_WEST` | `HAS_ANNOTATIONS` | `HAS_ANNOTATIONS` | 0.704 | EVIDENCE_DISAGREEMENT | **YES** |

### Detailed Chip Breakdown:

1. **`PILOT_01_NORTH`:**
   - **Annotator 1:** `HAS_ANNOTATIONS` (`Agricultural Fire`, box `[445, 320, 495, 365]`, near SE boundary).
   - **Annotator 2:** `NO_VISIBLE_TARGET` (focused on center `[256, 256]` where field is fallow with no fire).
   - **Disagreement:** `CLASS_DISAGREEMENT` / Status discrepancy (`HAS_ANNOTATIONS` vs `NO_VISIBLE_TARGET`).
   - **Friction Cause:** Ambiguity regarding whether an active burn plot $\approx 1\text{ km}$ away from the FIRMS point should be bound.

2. **`PILOT_05_CENTRAL`:**
   - **Annotator 1:** `NO_VISIBLE_TARGET` (clear ground surface at center `[256, 256]`, zero fire/smoke).
   - **Annotator 2:** `NO_VISIBLE_TARGET` (agreed that peripheral cloud in SE corner is non-target; center is clear).
   - **Disagreement:** **NONE**. Full concordance.

3. **`PILOT_09_SOUTH`:**
   - **Annotator 1:** `Forest Fire` (box `[210, 50, 290, 115]`, active ridge wildfire).
   - **Annotator 2:** `Forest Fire` (box `[205, 45, 295, 125]`, active ridge wildfire).
   - **Spatial Overlap:** **IoU = 0.722**. Class match = **TRUE**.
   - **Evidence Overlap:** Jaccard = **1.000** (`DIRECT_FIRE_VISIBLE`, `BURN_SCAR_VISIBLE`, `FOREST_CONTEXT_VISIBLE`).
   - **Disagreement:** **NONE**. Full concordance.

4. **`PILOT_13_EAST`:**
   - **Annotator 1:** `Forest Fire` (box `[230, 230, 285, 285]`, dark canopy patch interpreted as forest scar).
   - **Annotator 2:** `UNRESOLVED` (box `[225, 225, 290, 290]`, dark patch cannot be distinguished from terrain shadow without active SWIR emission).
   - **Disagreement:** `UNRESOLVED_DISAGREEMENT` / `EVIDENCE_DISAGREEMENT`.
   - **Friction Cause:** Strict adherence to Rule 5 ('Unknown evidence $\ne$ forced class') by Annotator 2.

5. **`PILOT_17_WEST`:**
   - **Annotator 1:** `Agricultural Fire` (box `[168, 245, 198, 268]`, active crop burning).
   - **Annotator 2:** `Agricultural Fire` (box `[165, 242, 200, 270]`, active crop burning).
   - **Spatial Overlap:** **IoU = 0.704**. Class match = **TRUE**.
   - **Evidence Overlap:** Jaccard = **0.667** (`DIRECT_FIRE_VISIBLE`, `CROPLAND_CONTEXT_VISIBLE`).
   - **Disagreement:** Minor `EVIDENCE_DISAGREEMENT` (A1 included `BURN_SCAR_VISIBLE`, A2 omitted). Class and geometry fully agree.

---

## 4. Proposed Protocol Changes (`PROPOSED_PROTOCOL_CHANGE`)

Based on authentic friction observed during this 5-chip pilot, the following two protocol refinements are submitted for user review prior to Stage 8.10B:

### `PROPOSED_PROTOCOL_CHANGE_01`: Standardize Search Association Radius
- **Issue:** In `PILOT_01_NORTH`, annotators disagreed on whether a visual target $1\text{ km}$ away from the FIRMS detection should be annotated.
- **Proposed Rule:** Define an explicit maximum association distance of **$750\text{ m}$ (75 pixels)** from the FIRMS coordinate. Targets $>750\text{ m}$ away must not be associated; the chip should be designated `NO_VISIBLE_TARGET` if the central $750\text{ m}$ is clear.

### `PROPOSED_PROTOCOL_CHANGE_02`: Cold Vegetative Scars Without Thermal Confirmation
- **Issue:** In `PILOT_13_EAST`, montane shadow vs burn scar ambiguity led to divergence between `Forest Fire` and `UNRESOLVED`.
- **Proposed Rule:** In dense montane/hilly terrain, if a vegetative disturbance lacks concurrent SWIR hotspot radiance ($B12 > 0.5$) or visible smoke plume, annotators must require secondary temporal contrast or designate `UNRESOLVED` to prevent terrain shadow false positives.

---

> [!IMPORTANT]
> **Zero Premature Adjudication:** All 5 chips remain in draft review status. No files have been moved to `data/reference/ds08/annotations/final/`.