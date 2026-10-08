# Stage 8.19E — Formal Decision Log

**Date:** 2026-10-03  
**Stage:** 8.19E — Candidate Catalog Reconciliation and Spatial Split Repair  
**Workspace:** `d:/DATA PREPROCESSING`  

---

## Decision Record: DEC-U7 — Pilot Catalog Product Reconciliation

### 1. Context and Problem Statement
In Stage 8.19D, live read-only verification against the Copernicus Data Space Ecosystem (CDSE) catalog confirmed that 3 of the 8 pilot candidates (Stratum 1) exist and match the manifest. However, the other 5 pilot candidates (`DS08_EXP_S2_001` through `DS08_EXP_S6_001`) returned 0 matches in CDSE. Detailed inspection revealed:
* Placeholder nighttime or arbitrary timestamps (e.g., `21:52:00` UTC over India where optical passes occur ~05:30 UTC).
* Synthetic MGRS tile identifiers containing the invalid letter 'I' (e.g., `T43SKI`, `T44SAI`), which does not exist in standard MGRS notation.

### 2. Evaluated Options
* **Option A: Reject candidates and reduce pilot size.** Reject the 5 missing strata and proceed with only Stratum 1.  
  *Verdict: REJECTED.* Violates core pilot requirement that all 6 expansion strata must be represented.
* **Option B: Synthesize new coordinates.** Pick arbitrary coordinates where scenes exist.  
  *Verdict: REJECTED.* Violates non-negotiable rule against fabricating candidates or moving ground locations.
* **Option C: Reconcile live CDSE products via spatial coordinate intersection (APPROVED).** Query CDSE using exact physical ground coordinates and nominal dates using `OData.CSC.Intersects`, retrieve real Level-2A products, verify real tiles, and select clear-sky daytime overpasses.

### 3. Formal Decision: DEC-U7
Approve the reconciliation of candidates `DS08_EXP_S2_001`, `DS08_EXP_S3_001`, `DS08_EXP_S4_001`, `DS08_EXP_S5_001`, and `DS08_EXP_S6_001` with verified CDSE Level-2A SAFE products:
1. `DS08_EXP_S2_001`: `S2B_MSIL2A_20250608T054639_N0511_R048_T43SBS_20250608T074909.SAFE` (UUID: `d217bf07-...`, 0.0% cloud, real tile `T43SBS`).
2. `DS08_EXP_S3_001`: `S2B_MSIL2A_20250516T053639_N0511_R005_T43RDP_20250516T074822.SAFE` (UUID: `ec7925b0-...`, 0.24% cloud, real tile `T43RDP`, exact calendar match 2025-05-16).
3. `DS08_EXP_S4_001`: `S2A_MSIL2A_20241023T053901_N0511_R005_T43RFP_20241023T090052.SAFE` (UUID: `df4ae3e0-...`, 0.08% cloud, real tile `T43RFP`, exact calendar match 2024-10-23).
4. `DS08_EXP_S5_001`: `S2C_MSIL2A_20250128T053131_N0511_R105_T43RGM_20250128T084454.SAFE` (UUID: `ffb53396-...`, 0.0% cloud, real tile `T43RGM`, January 2025 baseline).
5. `DS08_EXP_S6_001`: `S2B_MSIL2A_20250212T052839_N0511_R105_T44RKS_20250212T073606.SAFE` (UUID: `fede2b88-...`, 0.0% cloud, real tile `T44RKS`, exact calendar match 2025-02-12).

---

## Decision Record: DEC-U8 — Spatial Split Repair via Intra-Stratum Swap

### 1. Context and Problem Statement
In Stage 8.19D, native UTM raster grid convergence reduced the footprint-to-footprint distance between `DS08_EXP_S4_018` (Fold 4, Agricultural Fire) and `DS08_EXP_S5_016` (Fold 3, Industrial Negative Control) to **49.993988 km**, falling **6.01 meters below the 50.000000 km threshold**.
The user instructions strictly forbid weakening the 50 km rule, adding tolerances, rounding, or switching back to geographic approximations.

### 2. Evaluated Options
* **Option A: Add engineering tolerance (±10 m).**  
  *Verdict: REJECTED.* Explicitly forbidden by prompt instructions.
* **Option B: Intra-stratum fold swap between Fold 3 and Fold 4 (APPROVED).**  
  Reassign `DS08_EXP_S4_018` to Fold 3 so both candidates are co-located in Fold 3. Counter-swap an isolated STR-4 candidate from Fold 3 to Fold 4 to maintain exact fold sizes (47 chips each) and exact stratum allocations.

### 3. Formal Decision: DEC-U8
Approve the intra-stratum swap of:
* `DS08_EXP_S4_018` (STR-4, tile `T44RDH`) from **Fold 4 to Fold 3**.
* `DS08_EXP_S4_043` (STR-4, tile `T45RGM`) from **Fold 3 to Fold 4**.

**Verification:**
* Cross-fold pairs evaluated: 22,090 nationwide.
* Violations $\le 50.000000\text{ km}$: Exactly **0**.
* Global minimum separation: **50.1017 km** (Margin: **+101.72 meters**).
* Fold balance: Exactly 47 chips in each fold.
* MGRS tile isolation: 0 split tiles.
* Incident isolation: 0 split incidents.
