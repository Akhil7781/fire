# Stage 8.19F — Formal Decision Log

**Date:** 2026-10-03  
**Stage:** 8.19F — Independent Evidence Reproduction, Acquisition-Script Audit, and Final Readiness Verification  
**Auditor / Reviewer Role:** Senior Remote-Sensing Researcher, Geospatial Validation Engineer, Reproducibility Auditor & Software Safety Reviewer  
**Workspace:** `d:/DATA PREPROCESSING`  

---

## Decision Record: DEC-U9 — Final Reproduction, Evidence Acceptance, and Acquisition-Pilot Readiness

### 1. Context and Problem Statement
In Stage 8.19E, two critical blockers from Stage 8.19D were claimed resolved:
1. Repair of the native UTM footprint separation violation (reassigning `DS08_EXP_S4_018` to Fold 3 and counter-swapping `DS08_EXP_S4_043` to Fold 4).
2. Live catalog reconciliation of 5 pilot candidates (`DS08_EXP_S2_001` to `DS08_EXP_S6_001`) from synthetic placeholders to verified Copernicus Level-2A SAFE products.

Stage 8.19F was commissioned to independently test, reproduce, and audit these claims as unproven hypotheses rather than accepting previous documentation.

---

### 2. Independent Audit Findings

1. **Spatial Geometry Reproduction:**
   * Recomputed all 22,090 cross-fold native UTM 5.12 km footprint distances using Karney's ellipsoidal geodesic method.
   * Confirmed zero ($\le 50.000000\text{ km}$) violations across all 5 folds.
   * Confirmed the global minimum separation is **50.101722 km** (closest pair: `DS08_EXP_S3_004` in Fold 2 vs `DS08_EXP_S4_004` in Fold 4), providing a robust positive margin of **+101.72 meters**.
   * Confirmed that `DS08_EXP_S4_018` and `DS08_EXP_S5_016` are both co-located in Fold 3 (zero cross-fold violation).
   * Confirmed 0 MGRS tile splits and 0 incident splits.
   * Confirmed exact fold balance: 47 expansion candidates in each of Folds 1–5, and 15 held-out chips in `BENCHMARK_HELD_OUT`.

2. **Live CDSE Catalog and Footprint Reproduction:**
   * Queried live Copernicus Data Space Ecosystem OData API for all 8 pilot products.
   * Confirmed 100% bidirectional UUID $\leftrightarrow$ Name matching for all products.
   * Confirmed all products are authentic Sentinel-2 Level-2A (`S2MSI2A`), online (`Online: True`), and possess daytime overpasses (~05:26 to ~05:46 UTC).
   * Verified candidate point-in-polygon containment using actual catalog `GeoFootprint` polygons. All 8 candidate coordinates are strictly contained within their respective product footprints.
   * Audited temporal consistency: Stratum 1, 3, and 4 products match exact fire events/seasons; Stratum 2 matches persistent gas flaring clusters; Strata 5 and 6 match documented clear-sky winter baseline rules (January/February 2025 dry season).
   * Clearly distinguished new evidence (the 5 reconciled products) from carried-forward evidence (the 3 STR-1 products inherited from Stage 8.19 / 8.19B with DEC-U5 cloud exceptions).

3. **Acquisition Script Safety Audit:**
   * Static and dynamic inspection of `scripts/stage8_20_pilot_acquisition.py` confirms that execution is strictly restricted to the 8 pilot chips (`PILOT_CHIP_IDS`).
   * The `--confirm-acquisition` gate is active and enforced.
   * Dry-run execution downloaded exactly 0 bytes, created 0 directories, and wrote 0 files.
   * Diff audit confirmed that Stage 8.19E only updated manifest path selection and did not weaken any safeguards.

4. **Test Suite Reproduction:**
   * Executed `pytest -q tests/test_ds08_stage8_19e_audit.py`: 12/12 passed (0.83s).
   * Executed all Stage 8.19 test suites: 53 passed (1.75s).
   * Executed combined regression suite: 87 passed (3.48s).
   * Identified and documented static-artifact reliance in Test 3, fully mitigated by live CDSE verification in Stage 8.19F.

5. **Artifact Immutability:**
   * Manifest v3 SHA-256 hash was verified before and after audit: `dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848` (100% byte-for-byte intact).

---

### 3. Formal Determination

All Stage 8.19E claims are **INDEPENDENTLY PROVEN**.

The final status of the DS08 expansion branch is formally recorded as:

**`PROVEN_READY_FOR_STAGE_8_20_REVIEW`**

Authorization is granted to submit this audit package for human review and approval prior to executing the controlled Stage 8.20 acquisition pilot.
