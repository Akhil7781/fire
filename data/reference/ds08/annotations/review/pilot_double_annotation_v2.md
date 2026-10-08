# Stage 8.11 — DS08 Remaining 15-Chip Independent Double Annotation Report

**Date / Timestamp (UTC):** 2026-09-29T16:33:36.421005+00:00  
**Phase:** STAGE 8.11 (Double-Blind Independent Annotation of Remaining 15 Pilot Chips)  
**Protocol Version:** Version 1.0 (Retained without modification from Stage 8.10B-C)  
**Authoritative Guidelines:** [`data/reference/ds08/annotations/guidelines/DS08_ANNOTATION_GUIDELINES_v1.md`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/guidelines/DS08_ANNOTATION_GUIDELINES_v1.md)  
**Authoritative Schema:** [`data/reference/ds08/annotations/schema/ds08_annotation_schema.json`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/schema/ds08_annotation_schema.json)  

---

## 1. Executive Summary

In accordance with Stage 8.11 requirements, all remaining 15 chips in the authoritative 20-chip DS08 pilot manifest were independently annotated by two independent annotators (Annotator 1 and Annotator 2) without cross-inspection, automatic model labeling, or premature adjudication. Both annotators strictly operated under the frozen Version 1.0 guidelines and Draft-07 JSON schema.

The five chips previously completed and verified in Stages 8.10A and 8.10B-C were preserved byte-for-byte identical.

| Metric | Remaining 15 Chips | Full 20-Chip Pilot Cohort |
| :--- | :---: | :---: |
| **Total Chips Evaluated** | **15** | **20** |
| **Concordant / Agreed Chips** | **11** | **14** |
| **Disputed / Requiring Adjudication** | **4** | **6** |
| **Raw Inter-Annotator Agreement** | **73.33%** | **70.0%** |
| **Cohen's Kappa ($\kappa$)** | **0.5522** | **0.5455** |
| **Mean Matched-Box IoU** | **0.7186** | **0.7171** |
| **Mean Visual Evidence Jaccard** | **0.7222** | **0.7037** |

---

## 2. Deterministic Selection of Remaining 15 Chips

The remaining 15 chips were selected deterministically in exact manifest order from `data/reference/ds08/annotations/pilot_manifest.json`, excluding the 5 chips completed in Stage 8.10A/B:

 1. **`PILOT_02_NORTH`**
 2. **`PILOT_03_NORTH`**
 3. **`PILOT_06_CENTRAL`**
 4. **`PILOT_07_CENTRAL`**
 5. **`PILOT_08_CENTRAL`**
 6. **`PILOT_10_SOUTH`**
 7. **`PILOT_11_SOUTH`**
 8. **`PILOT_12_SOUTH`**
 9. **`PILOT_14_EAST`**
10. **`PILOT_15_EAST`**
11. **`PILOT_16_EAST`**
12. **`PILOT_18_WEST`**
13. **`PILOT_19_WEST`**
14. **`PILOT_20_WEST`**
15. **`PILOT_04_NORTH_REPLACEMENT`**

---

## 3. Class Distributions Across Annotators

### A. Remaining 15 Chips Distribution
| Class / Status | Annotator 1 | Annotator 2 | Agreement Status |
| :--- | :---: | :---: | :--- |
| **Industrial Fire** | 0 | 0 | Both 0 (No industrial fire evidence) |
| **Forest Fire** | 7 | 4 | 4 agreed active fires (`PILOT_03`, `PILOT_08`, `PILOT_15`, `PILOT_16`) |
| **Agricultural Fire** | 1 | 0 | 1 disputed off-center attribution (`PILOT_18_WEST`) |
| **Other Thermal Source** | 0 | 0 | Both 0 (No persistent industrial heat) |
| **NO_VISIBLE_TARGET** | 7 | 9 | 7 agreed clear negative chips |
| **UNRESOLVED** | 0 | 2 | 2 disputed montane shadow chips (`PILOT_14`, `PILOT_19`) |

### B. Full 20-Chip Pilot Cohort Distribution
| Class / Status | Annotator 1 | Annotator 2 | Post-Adjudication Frozen (Initial 5) |
| :--- | :---: | :---: | :---: |
| **Industrial Fire** | 0 | 0 | 0 |
| **Forest Fire** | 9 | 5 | 1 (`PILOT_09_SOUTH`) |
| **Agricultural Fire** | 3 | 1 | 1 (`PILOT_17_WEST`) |
| **Other Thermal Source** | 0 | 0 | 0 |
| **NO_VISIBLE_TARGET** | 8 | 11 | 2 (`PILOT_01_NORTH`, `PILOT_05_CENTRAL`) |
| **UNRESOLVED** | 0 | 3 | 1 (`PILOT_13_EAST`) |

---

## 4. Per-Chip Annotation Summary (15 Remaining Chips)

| Chip ID | A1 Status / Class | A2 Status / Class | Class Agreement | Disagreement Categories | IoU |
| :--- | :--- | :--- | :---: | :--- | :---: |
| `PILOT_02_NORTH` | NO_VISIBLE_TARGET | NO_VISIBLE_TARGET | YES | NONE | N/A |
| `PILOT_03_NORTH` | Forest Fire | Forest Fire | YES | NONE | 0.8403 |
| `PILOT_06_CENTRAL` | Forest Fire | NO_VISIBLE_TARGET | NO | CLASS_DISAGREEMENT | N/A |
| `PILOT_07_CENTRAL` | NO_VISIBLE_TARGET | NO_VISIBLE_TARGET | YES | NONE | N/A |
| `PILOT_08_CENTRAL` | Forest Fire | Forest Fire | YES | NONE | 0.7755 |
| `PILOT_10_SOUTH` | NO_VISIBLE_TARGET | NO_VISIBLE_TARGET | YES | NONE | N/A |
| `PILOT_11_SOUTH` | NO_VISIBLE_TARGET | NO_VISIBLE_TARGET | YES | NONE | N/A |
| `PILOT_12_SOUTH` | NO_VISIBLE_TARGET | NO_VISIBLE_TARGET | YES | NONE | N/A |
| `PILOT_14_EAST` | Forest Fire | UNRESOLVED | NO | UNRESOLVED_DISAGREEMENT, EVIDENCE_DISAGREEMENT | 0.6944 |
| `PILOT_15_EAST` | Forest Fire | Forest Fire | YES | NONE | 0.6720 |
| `PILOT_16_EAST` | Forest Fire | Forest Fire | YES | NONE | 0.6133 |
| `PILOT_18_WEST` | Agricultural Fire | NO_VISIBLE_TARGET | NO | CLASS_DISAGREEMENT | N/A |
| `PILOT_19_WEST` | Forest Fire | UNRESOLVED | NO | UNRESOLVED_DISAGREEMENT, EVIDENCE_DISAGREEMENT | 0.7160 |
| `PILOT_20_WEST` | NO_VISIBLE_TARGET | NO_VISIBLE_TARGET | YES | NONE | N/A |
| `PILOT_04_NORTH_REPLACEMENT` | NO_VISIBLE_TARGET | NO_VISIBLE_TARGET | YES | NONE | N/A |

---

## 5. Detailed Disagreement Analysis (4 Disputed Chips in Remaining 15)

Exactly 4 chips exhibited inter-annotator divergence and are slated for subsequent senior adjudication (Stage 8.12):

1. **`PILOT_06_CENTRAL` (CLASS_DISAGREEMENT / Spatial Association):**
   - **A1:** `Forest Fire` (`[80, 325, 330, 385]`, confidence `MEDIUM`, evidence `DIRECT_FIRE_VISIBLE`, `FOREST_CONTEXT_VISIBLE`). Identified an intense active wildfire front in the southern forest tract.
   - **A2:** `NO_VISIBLE_TARGET` (`annotations = []`). The nominal FIRMS detection (FRP = 0.43 MW) is situated at chip center `[256, 256]` in clear unburned forest. A2 excluded the southern fire because it is located over 1.1 km away.

2. **`PILOT_14_EAST` (UNRESOLVED_DISAGREEMENT / Montane Shadow):**
   - **A1:** `Forest Fire` (`[230, 230, 280, 280]`, confidence `LOW`). Interpreted a dark valley canopy feature near center as a vegetative burn scar.
   - **A2:** `UNRESOLVED` (`[225, 225, 285, 285]`, confidence `LOW`). Ruled that steep montane ravine shadow cannot be distinguished from a vegetative scar on single-date optical imagery without elevated SWIR reflectance (chip-wide B12 max = 0.3741) or visible smoke.

3. **`PILOT_18_WEST` (CLASS_DISAGREEMENT / Spatial Association):**
   - **A1:** `Agricultural Fire` (`[250, 70, 285, 95]`, confidence `HIGH`). Identified an active crop residue burn with smoke and fresh char in a northern agricultural plot.
   - **A2:** `NO_VISIBLE_TARGET` (`annotations = []`). The candidate detection coordinate `[256, 256]` displays clear fallow cropland. A2 excluded the northern plot because it is situated 1.76 km away across independent parcel boundaries.

4. **`PILOT_19_WEST` (UNRESOLVED_DISAGREEMENT / Western Ghats Shadow):**
   - **A1:** `Forest Fire` (`[230, 230, 285, 285]`, confidence `LOW`). Interpreted low-reflectance montane forest canopy as a burn scar.
   - **A2:** `UNRESOLVED` (`[225, 225, 290, 290]`, confidence `LOW`). In steep Western Ghats escarpment topography, canopy terrain shadow cannot be reliably differentiated from a burn scar on a single acquisition.

---

## 6. Verification and Compliance Confirmations

1. **No Adjudication Performed:** Disagreements remain unresolved and untouched; neither annotator's draft was altered after comparison.
2. **Original 5 Completed Chips Preserved:** All 10 draft files (`annotator_1` and `annotator_2`) for `PILOT_01_NORTH`, `PILOT_05_CENTRAL`, `PILOT_09_SOUTH`, `PILOT_13_EAST`, and `PILOT_17_WEST` remain strictly byte-for-byte identical.
3. **Draft File Inventory:**
   - `data/reference/ds08/annotations/draft/annotator_1/`: Exactly 20 JSON files.
   - `data/reference/ds08/annotations/draft/annotator_2/`: Exactly 20 JSON files.
4. **Final Directory Isolation:** `data/reference/ds08/annotations/final/` contains **EXACTLY** the 3 existing Stage 8.10B adjudicated files (`PILOT_01_NORTH`, `PILOT_13_EAST`, `PILOT_17_WEST`). No new files were added.
5. **No Imagery Download:** No new Sentinel-2 scenes or chips were downloaded or extracted.
6. **No Model Training:** TCN, Deep SAD, and YOLO model weights and fusion parquet artifacts remain completely untouched.

---