# Stage 8.19G — Formal Decision Log

**Date:** 2026-10-03  
**Stage:** 8.19G — Spatial Metric Validation and Stage 8.20 Safety-Control Audit  
**Auditor / Reviewer Role:** Senior Geospatial Validation Engineer, Computational Geometry Specialist, Remote-Sensing Scientist & Software Safety Auditor  
**Workspace:** `d:/DATA PREPROCESSING`  

---

## Decision Record: DEC-U10 — Reference Footprint Polygon Metric Acceptance

### 1. Context and Problem Statement
Stage 8.19F reported a global minimum cross-fold separation of 50.101722 km. However, previous test implementations (`test_ds08_stage8_19e_audit.py` and `audit_stage8_19b_spatial_footprint.py`) relied on 4-corner-to-4-corner geodesic approximations. A mathematical audit was required to evaluate all 22,090 cross-fold pairs using true continuous polygon-to-polygon Euclidean distance on native UTM footprint geometries.

### 2. Independent Evaluation
A pair-specific Azimuthal Equidistant (AEQD) projection centered on the geographic midpoint of each candidate pair was implemented, preserving radial distance with less than 13 cm distortion across 50 km. The continuous infimum Euclidean distance between native UTM footprint polygons ($5120\text{ m} \times 5120\text{ m}$) was computed using `shapely.geometry.Polygon.distance()` across all 22,090 cross-fold pairs in Manifest v4.

**Findings:**
* **Total Pairs Evaluated:** 22,090
* **Violations $\le 50.000000\text{ km}$:** Exactly **0**
* **Global Minimum Separation:** **50.101722 km** ($50,101.72\text{ m}$)
* **Closest Pair:** `DS08_EXP_S3_004` (Fold 2) $\longleftrightarrow$ `DS08_EXP_S4_004` (Fold 4)
* **Margin Above 50.0 km Threshold:** **+101.72 meters**
* **Status:** **REFERENCE_METRIC_CONFIRMED (Case A — Equivalent)**

### 3. Formal Decision: DEC-U10
Approve the true continuous polygon-to-polygon AEQD distance metric as the official reference metric for DS08 spatial separation. Formally confirm that the reported 50.101722 km minimum separation is mathematically sound and that zero cross-fold footprint violations exist.

---

## Decision Record: DEC-U11 — Acquisition Script Safety Control Verification and Wording Resolution

### 1. Context and Problem Statement
The Stage 8.19F audit report contained an ambiguous phrase ("weakened zero safety checks") that could be misinterpreted as implying safety controls had been reduced. Furthermore, Stage 8.19G required an independent line-by-line audit of `scripts/stage8_20_pilot_acquisition.py` to confirm that no actual safety regressions occurred during the Stage 8.19E updates.

### 2. Independent Evaluation
Static and dynamic code audits confirmed that:
* Execution is hardcoded strictly to `PILOT_CHIP_IDS` (8 chips) with an explicit length assertion.
* `--confirm-acquisition` remains mandatory (default `False`).
* In dry-run mode, the script downloads **0 bytes**, writes **0 files**, and does not create the output directory.
* Credential loading from `.env` or environment logs only a boolean status check (`has_creds: True`); no secrets or tokens are printed or stored.
* The only change in Stage 8.19E was the addition of `MANIFEST_V4_PATH` fallback path selection.

### 3. Formal Decision: DEC-U11
1. **Wording Resolution:** Officially clarify and replace the ambiguous phrase with:
   > *"Zero safety checks were weakened; all pre-existing safeguards and confirmation gates remain strictly active and unaltered."*
2. **Safety Approval:** Formally confirm that `scripts/stage8_20_pilot_acquisition.py` has zero safety regressions and is verified safe for controlled human authorization.
