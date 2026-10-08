# STAGE 8.18 — PLANNING AUDIT REPORT: SAMPLING & ANNOTATION PROTOCOL
**Authoritative Architectural Review, Feasibility Assessment, and Sign-Off Readiness**

- **Audit Execution Timestamp:** `2026-10-02T12:38:00Z`
- **Stage:** Stage 8.18 — DS08 Dataset Expansion Planning
- **Status:** **COMPLETE — LOCKED FOR HUMAN REVIEW (STRICT STOP ENFORCED)**
- **Target Expansion Cohort:** $N = 250$ Real Level-2A Sentinel-2 Chips ($512 \times 512$ px, 10m GSD)
- **Operational Mode:** **PLANNING ONLY (ZERO BULK DOWNLOADS / ZERO MODEL TRAINING / ZERO SYNTHETIC LABELS)**

---

## 1. Executive Summary & Protocol Overview

Following the successful completion and certification of the 15-chip DS08 pilot package (`ds08_pilot_v1`, Stage 8.17), Stage 8.18 designs and locks a comprehensive, scientifically defensible sampling, acquisition, annotation, and data governance framework for expanding DS08 toward a target of approximately 250 real Sentinel-2 chips across India.

```text
========================================================================================
                          STAGE 8.18 PLANNING SUMMARY
========================================================================================
Total Target Chips:                           250 Sentinel-2 Level-2A Chips
  - Pilot Benchmark Calibration Cohort:       15 chips (FROZEN / HELD OUT)
  - New Expansion Acquisitions:               235 chips (PLANNED)
Sampling Strata Defined:                      7 distinct, physically grounded strata
Geographic Distribution:                      Pan-India (North 22%, Central 24%, South 18%, East 20%, West 16%)
Temporal Matching Policy:                     4 stratified tiers (Tier 1 <= 2h to Tier 4 <= 48h)
Annotation Methodology:                       Independent Double-Pass + Senior Adjudication
Visual Evidence Mutual Exclusion:             LOCKED (NO_CLEAR_VISUAL_EVIDENCE vs Positive Tags)
Split & Leakage Strategy:                     Spatial Tile Blocking (> 150 km buffer) & Spatial 5-Fold CV
Bulk Downloads Initiated:                     0 chips (STRICTLY PROHIBITED AT THIS STAGE)
Synthetic Labels Generated:                   0 (PROHIBITED)
Model Training Authorized:                    NO (STRICT BOUNDARY ENFORCED)
========================================================================================
```

---

## 2. Phase 1 Inspection Findings & Repository Inventory

An exhaustive inspection of the existing codebase, metadata, and data directories revealed:

### 2.1 Reusable Infrastructure
- **CDSE Sentinel Hub Processing Pipeline:** [`scripts/run_sentinel_pilot_acquisition.py`](file:///d:/DATA%20PREPROCESSING/scripts/run_sentinel_pilot_acquisition.py) provides a validated geometry and extraction engine (UTM zone selection, $5.12 \times 5.12\text{ km}$ AOI projection, FLOAT32 BOA reflectance, 17-point raster validation).
- **Double-Pass Annotation UI:** [`scripts/ds08_annotation_tool.py`](file:///d:/DATA%20PREPROCESSING/scripts/ds08_annotation_tool.py) and [`scripts/ds08_correction_tool.py`](file:///d:/DATA%20PREPROCESSING/scripts/ds08_correction_tool.py) provide robust double-pass human workflows with canvas-draw provenance tracking.
- **Packaging & Validation Engine:** [`scripts/package_ds08_pilot.py`](file:///d:/DATA%20PREPROCESSING/scripts/package_ds08_pilot.py) and [`scripts/validate_ds08_pilot_package.py`](file:///d:/DATA%20PREPROCESSING/scripts/validate_ds08_pilot_package.py) enforce 10-point cryptographic and logical verification.

### 2.2 Critical Discovery: The Reality of Acute Industrial Fire Scarcity
- In the 15-chip pilot cohort (`ds08_pilot_v1`): **ZERO Industrial Fire positive examples exist** (5 Forest Fire, 1 Agricultural Fire, 9 Negative).
- An empirical audit of official government disaster records and incident databases (`data/reference/industrial/india_industrial_incidents_2025_normalized.parquet` and `data/reference/ds05/industrial_incidents.parquet`) identified only **12 to 14 verified acute industrial fire events across all of India in 2025**.
- **Scientific Implication:** The historical placeholder in `ds08_sentinel2_manifest.parquet` proposing 100 Industrial Fire chips was physically ungrounded. Attempting to force 100 industrial fire chips would inevitably produce severe label noise (misclassifying normal flaring or nearby agricultural burning as industrial fires).
- Stage 8.18 corrects this by creating separate strata for **Confirmed Acute Industrial Disasters** ($n = 15$) and **Persistent Non-Biomass Thermal Sources** ($n = 30$, covering gas flaring, coal seam fires, and brick kilns).

---

## 3. The 7-Stratum Sampling Framework ($N = 250$)

| Stratum ID | Stratum Name | Target Class | Allocated Chips | Min. Required | Primary Data Source / Registry |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **STR-1** | **Confirmed Acute Industrial Fires** | `Industrial Fire` | **15 chips** | 10 chips | `india_industrial_incidents_2025_normalized.parquet` |
| **STR-2** | **Persistent Non-Biomass Thermal Sources** | `Other Thermal Source` | **30 chips** | 20 chips | `india_other_thermal_sources_2025_normalized.parquet`, World Bank GGFR, SentinelKilnDB |
| **STR-3** | **Active Forest Wildfires** | `Forest Fire` | **55 chips** | 45 chips | `fsi_van_agni_lff_2025_normalized.parquet`, Global Fire Atlas, MODIS MCD64A1 |
| **STR-4** | **Agricultural Crop Residue Burns** | `Agricultural Fire` | **55 chips** | 45 chips | `icar_iari_creams_2025_normalized.parquet`, CREAMS registries |
| **STR-5** | **Industrial Negative Controls** | `NO_VISIBLE_TARGET` | **40 chips** | 30 chips | OpenStreetMap industrial polygons, Central Electricity Authority database |
| **STR-6** | **Natural & Agricultural Negatives** | `NO_VISIBLE_TARGET` | **40 chips** | 30 chips | Low-confidence FIRMS detections, clear-sky background tiles |
| **STR-7** | **Pilot Benchmark Calibration Cohort** | Mixed (6 Pos / 9 Neg) | **15 chips** | 15 chips | `data/reference/ds08/packages/ds08_pilot_v1/manifest.json` |
| **TOTAL** | **Pan-India Expanded Dataset** | **All Categories** | **250 chips** | **195 chips** | **Multi-Source Ground Truth Pool** |

---

## 4. Key Protocol Specifications

1. **FIRMS-to-Sentinel-2 Temporal Matching:** Replaced flat 48h window with 4 stratified tiers (Tier 1 $\le 2\text{h}$, Tier 2 $\le 6\text{h}$, Tier 3 $\le 24\text{h}$, Tier 4 $\le 48\text{h}$).
2. **5-Band Sentinel-2 GeoTIFF:** B02, B03, B04, B11, B12 in FLOAT32 BOA reflectance; 20m SWIR bands upsampled to 10m via bilinear interpolation.
3. **Mutual Exclusion Invariant:** `NO_CLEAR_VISUAL_EVIDENCE` is strictly forbidden from co-occurring with `DIRECT_FIRE_VISIBLE` or `BURN_SCAR_VISIBLE`.
4. **Spatial Grouping Split Policy:** Random splitting prohibited. Enforced MGRS Tile ID blocking and $> 150\text{ km}$ spatial buffering. Pilot cohort held out permanently.

---

## 5. Deliverables Generated in Stage 8.18

All planning deliverables have been generated in an isolated, versioned directory ([`docs/stage8_18/`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18/)) without modifying any pilot data:

1. [`stage8_18_sampling_protocol.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18/stage8_18_sampling_protocol.md): Sampling objectives, 7 strata allocation, geographic quotas, and contingency rules.
2. [`stage8_18_acquisition_protocol.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18/stage8_18_acquisition_protocol.md): FIRMS matching tiers, chip geometry, band specs, and 3-gate cloud screening.
3. [`stage8_18_annotation_protocol.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18/stage8_18_annotation_protocol.md): Class definitions, evidence taxonomy, bounding box rules, and adjudication workflow.
4. [`stage8_18_quality_and_governance.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18/stage8_18_quality_and_governance.md): 10 automated quality gates, inter-annotator metrics, hashes, and quarantine isolation.
5. [`stage8_18_split_strategy.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18/stage8_18_split_strategy.md): Spatial block grouping, leakage prevention, and Spatial 5-Fold Cross-Validation.
6. [`stage8_18_decision_log.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18/stage8_18_decision_log.md): Formal log of 7 locked decisions, assumptions, and items requiring sign-off.
7. [`sampling_plan.json`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18/sampling_plan.json) / [`sampling_plan.csv`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18/sampling_plan.csv): Machine-readable allocation records.
8. [`STAGE8_18_PLANNING_AUDIT_REPORT.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_18/STAGE8_18_PLANNING_AUDIT_REPORT.md): This authoritative planning report.

---

## 6. Action Items Requiring Human Approval Before Stage 8.19

Per strict protocol instructions, execution is paused for human review. The following decisions require explicit sign-off:

1. **Approval of the 7-Stratum Allocation ($N = 250$):** Confirm the distribution (15 Acute Industrial, 30 Persistent Thermal, 55 Forest, 55 Agricultural, 40 Industrial Negatives, 40 Contextual Negatives, 15 Pilot Benchmark).
2. **Approval of the Acute Industrial Shortfall Contingency:** Authorize reallocating any shortfall in cloud-free 2025 acute industrial fire scenes to Stratum 2 (`Other Thermal Source`).
3. **Approval of Spatial 5-Fold Cross-Validation:** Confirm adoption of spatial tile blocking over static random splitting.
4. **Authorization for Candidate Discovery:** Authorize querying the CDSE STAC catalog to build candidate manifests without bulk downloading rasters.
