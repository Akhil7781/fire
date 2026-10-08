# Stage 8.19D — Native-Raster Geometry Verification and Live STAC Readiness Audit

**Audit Date:** 2026-10-02  
**Auditor Role:** Senior Geospatial ML Engineer & Remote-Sensing Pipeline Auditor  
**Workspace:** `d:/DATA PREPROCESSING`  
**Authoritative Manifest:** `data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json` (SHA-256: `dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848`)  
**Final Readiness Status:** **BLOCKED — RESOLUTION REQUIRED**

---

## 1. Executive Summary

This audit conducted an independent, rigorous, read-only verification of the Stage 8.19B/8.19C deliverables prior to any Sentinel-2 imagery acquisition for Stage 8.20. The evaluation examined:
1. Native UTM raster grid footprint geometry versus geographic bounding box approximations.
2. Cross-fold spatial separation, MGRS tile isolation, and incident grouping across all 235 expansion candidates and 15 held-out benchmark pilot chips.
3. Live CDSE STAC/OData catalog metadata for all 8 proposed pilot candidates.
4. DEC-U5 cloud-exception documentation and raster-screening conditionality.
5. Acquisition script safety guards in `scripts/stage8_20_pilot_acquisition.py`.
6. Full test suite execution and artifact hash preservation.

### Core Audit Outcomes:
* **Native Raster Footprint Geometry: FAIL (Shortfall: 6.01 meters below 50.0000 km threshold).**  
  Under the previously applied geographic axis-aligned bounding box approximation (Stage 8.19B/C), the closest cross-fold pair (`DS08_EXP_S4_018` in Fold 4 vs `DS08_EXP_S5_016` in Fold 3) evaluated to **50.0079 km** (+7.87 m margin). However, Sentinel-2 Level-2A imagery is natively gridded in the Universal Transverse Mercator (UTM) projection (UTM Zone 44N, EPSG:32644). Due to UTM grid convergence ($\gamma \approx +0.490^\circ$ and $+0.648^\circ$), the true native raster boundaries are slightly rotated relative to true geographic north. On the WGS84 ellipsoid, this rotation shifts the opposing corners toward each other by $\approx 13.89\text{ m}$, yielding a true polygon-to-polygon geodesic distance of **49.993988 km** ($49,993.99\text{ m}$). Under the non-negotiable rule that the 50.0 km separation must not be silently relaxed and the manifest cannot be modified during an audit, this constitutes an unresolved geometry violation.
* **Live STAC Catalog Verification: BLOCKED (5 of 8 pilot products missing from live catalog).**  
  A read-only query against the Copernicus Data Space Ecosystem (CDSE) OData catalog revealed that the 3 Stratum 1 products (`DS08_EXP_S1_003`, `DS08_EXP_S1_002`, `DS08_EXP_S1_004`) exist, are online, and exactly match the manifest. However, the remaining 5 pilot products (`DS08_EXP_S2_001`, `DS08_EXP_S3_001`, `DS08_EXP_S4_001`, `DS08_EXP_S5_001`, `DS08_EXP_S6_001`) return **0 matches** in CDSE. These candidate SAFE IDs were synthesized during candidate generation using standard ESA naming conventions (with placeholder nighttime sensing times like `21:52:00` UTC) rather than resolved from live CDSE STAC queries.
* **Acquisition Script Safety: PASS.**  
  `scripts/stage8_20_pilot_acquisition.py` is strictly gated by `--confirm-acquisition`, defaults to a 0-byte dry-run, restricts processing to the 8 pilot IDs, reads credentials securely from `.env` without printing secrets, and targets an isolated interim directory (`data/interim/ds08_stage8_20_pilot`).
* **Cloud Exceptions: CONDITIONAL.**  
  Both DEC-U5 cloud exceptions (`DS08_EXP_S1_002` at 14.74% and `DS08_EXP_S1_004` at 19.32%) are properly documented in manifest metadata. Because raster assets were not retrieved, AOI-level ($\le 5\%$) and center 1 km ($100\%$ clear) conditions cannot be evaluated at this stage and must be enforced by post-acquisition automated SCL screening.
* **Final Determination: BLOCKED — RESOLUTION REQUIRED.**  
  Imagery acquisition cannot proceed until the dataset owner resolves the 6.01-meter native geometry deficit and resolves live CDSE product IDs for Strata 2–6.

---

## 2. Scope and Restrictions Followed

This audit strictly adhered to all non-negotiable guidelines:
1. **Zero Imagery Downloads:** No Sentinel-2 raster files, JP2 bands, SAFE archives, or quicklooks were downloaded.
2. **Zero Model Operations:** No deep learning or machine learning models were trained, evaluated, or fine-tuned.
3. **Zero Synthetic Annotations:** No synthetic bounding boxes or labels were generated.
4. **Authoritative Manifest Frozen:** `data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json` was strictly read-only. Pre-audit and post-audit SHA-256 hashes are identical (`dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848`).
5. **Pilot Cohort Unchanged:** The 8 pilot candidate IDs were preserved exactly as defined.
6. **No Secret Leakage:** No API secrets, tokens, client credentials, or authorization headers were printed, logged, or written to reports.
7. **No Gated Script Execution:** `scripts/stage8_20_pilot_acquisition.py` was executed only in default dry-run mode without `--confirm-acquisition`.
8. **No Threshold Relaxation:** The 50 km cross-fold spatial separation rule and the 10% scene cloud cover threshold (with DEC-U5 exceptions) were evaluated without silent relaxation.
9. **Safe STAC Metadata Access:** Live catalog verification used read-only OData metadata endpoints without retrieving raster payload bytes.

---

## 3. Files and Artifacts Inspected

| Artifact / File | Path | Status | Pre-Audit SHA-256 | Post-Audit SHA-256 |
| :--- | :--- | :---: | :---: | :---: |
| Authoritative Manifest v3 | `data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json` | FROZEN | `dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848` | `dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848` |
| Frozen Benchmark Pilot Package | `data/reference/ds08/packages/ds08_pilot_v1/manifest.json` | FROZEN | `6eed42b0b08da25f6fccbabf7c4d02f980c1a13fec7554160a75d63aebaa2b81` | `6eed42b0b08da25f6fccbabf7c4d02f980c1a13fec7554160a75d63aebaa2b81` |
| Stage 8.19B Decision Resolution | `docs/stage8_19b/STAGE8_19B_DECISION_RESOLUTION.md` | VERIFIED | `07cab242103488e8a26b178a575840da71de6f3c737ac03258de40295255fda1` | `07cab242103488e8a26b178a575840da71de6f3c737ac03258de40295255fda1` |
| Stage 8.19B Spatial Revalidation | `docs/stage8_19b/STAGE8_19B_SPATIAL_REVALIDATION.md` | VERIFIED | `2470de01a3fc6b3bd0d291587779cc46260ce4ab865e22b545b17624c1054467` | `2470de01a3fc6b3bd0d291587779cc46260ce4ab865e22b545b17624c1054467` |
| Stage 8.19C Final Pre-Acquisition Audit | `docs/stage8_19c/STAGE8_19C_FINAL_PREACQUISITION_AUDIT.md` | VERIFIED | `ccba22bbe2ecd105a99452af2e4d905f47ee05d045e0684da4810df8ed71cc9a` | `ccba22bbe2ecd105a99452af2e4d905f47ee05d045e0684da4810df8ed71cc9a` |
| Stage 8.20 Pilot Acquisition Script | `scripts/stage8_20_pilot_acquisition.py` | VERIFIED | `ab5f9ba98d822ac4b70e3e0d760e2a053e21e4ffd368cceef558facbae83d5cd` | `ab5f9ba98d822ac4b70e3e0d760e2a053e21e4ffd368cceef558facbae83d5cd` |
| Spatial Footprint Audit Script | `scripts/audit_stage8_19b_spatial_footprint.py` | VERIFIED | `c174bf9ae143c7b37dbfb60cbeea5098ffb4f3b5eb497e0344d56d1a66270cb4` | `c174bf9ae143c7b37dbfb60cbeea5098ffb4f3b5eb497e0344d56d1a66270cb4` |

---

## 4. Native-Raster Geometry Verification

### 4.1 Specification and Native Grid Reconstruction
The repository contains complete and deterministic definitions of chip geometry:
* **Chip Dimension:** $512 \times 512$ pixels.
* **Ground Sample Distance (GSD):** $10.0\text{ meters}$ per pixel.
* **Chip Spatial Footprint:** $5,120\text{ m} \times 5,120\text{ m}$ ($2,560\text{ m}$ half-width from center).
* **Native Coordinate Reference System (CRS):** Universal Transverse Mercator (UTM), WGS84 ellipsoid.
  * Derived from MGRS tile prefix: `EPSG:32600 + int(mgrs_tile[1:3])` (e.g., tile `T44QLE` $\rightarrow$ UTM Zone 44N $\rightarrow$ `EPSG:32644`).
* **Chip Native Center:** Center latitude and longitude $(\phi, \lambda)$ projected to UTM Easting and Northing $(E_{\text{center}}, N_{\text{center}})$.
* **Native UTM Polygon:**
  $$\begin{aligned}
  P_{\text{SW}} &= (E_{\text{center}} - 2560\text{ m}, N_{\text{center}} - 2560\text{ m}) \\
  P_{\text{SE}} &= (E_{\text{center}} + 2560\text{ m}, N_{\text{center}} - 2560\text{ m}) \\
  P_{\text{NE}} &= (E_{\text{center}} + 2560\text{ m}, N_{\text{center}} + 2560\text{ m}) \\
  P_{\text{NW}} &= (E_{\text{center}} - 2560\text{ m}, N_{\text{center}} + 2560\text{ m})
  \end{aligned}$$
* **Transformation to WGS84 Ellipsoid:** The four corners are inverse-projected from `EPSG:32600+zone` to `EPSG:4326` $(\lambda_i, \phi_i)$.

### 4.2 Impact of Grid Convergence vs Geographic Approximation
In Stage 8.19B and 8.19C, footprint corners were approximated as an axis-aligned bounding box in geographic coordinates (WGS84 lat/lon) using geodesic offsets along the meridian ($d\phi = 2560 / 111320$) and parallel ($d\lambda = 2560 / (111320 \times \cos\phi)$).

In reality, Sentinel-2 rasters are gridded in UTM. The angle between UTM grid north and true geographic north is the **meridian convergence angle** $\gamma$:
$$\gamma \approx (\lambda - \lambda_0) \sin\phi$$
where $\lambda_0$ is the central meridian of the UTM zone ($81^\circ\text{E}$ for Zone 44).

For the closest cross-fold candidate pair:
* `DS08_EXP_S4_018` (Fold 4): Lat $22.37894^\circ\text{N}$, Lon $82.28821^\circ\text{E}$, MGRS `T44QLE` (UTM 44N).  
  Central meridian offset: $\Delta \lambda = +1.28821^\circ$. Grid convergence: $\gamma \approx +0.490^\circ$.
* `DS08_EXP_S5_016` (Fold 3): Lat $22.09630^\circ\text{N}$, Lon $82.72310^\circ\text{E}$, MGRS `T44QME` (UTM 44N).  
  Central meridian offset: $\Delta \lambda = +1.72310^\circ$. Grid convergence: $\gamma \approx +0.648^\circ$.

Because both chips lie east of the central meridian, their native UTM raster grids are rotated counter-clockwise with respect to true north by $\sim 0.5^\circ - 0.65^\circ$. This rotation tilts the eastern corners of `DS08_EXP_S4_018` southward and the western corners of `DS08_EXP_S5_016` northward—pointing directly along the azimuth separating the two chips!

### 4.3 Rigorous Distance Comparison
Using Karney's geodesic inverse algorithm on the WGS84 ellipsoid (`pyproj.Geod(ellps='WGS84')`):

| Method | Geometry Formulation | Distance | Separation Margin vs 50.0 km | Status |
| :--- | :--- | :---: | :---: | :---: |
| **Center-to-Center** | WGS84 Geodesic points | **56.9915 km** | +6,991.5 m | PASS |
| **Geographic Approx (8.19B/C)** | WGS84 Axis-aligned box | **50.0079 km** | +7.87 m | PASS (Nominal) |
| **Native UTM Raster Grid** | Projected UTM rotated box on WGS84 | **49.9940 km** | **-6.01 m** | **FAIL** |

### 4.4 Conclusion on Task 2
The repository does contain sufficient information to reconstruct the native-grid footprint geometry. The reconstruction is mathematically exact and reproducible. Under native UTM geometry, the minimum cross-fold footprint separation is **49.993988 km**, violating the strict 50.0000 km threshold by **6.01 meters**.

---

## 5. Independent Spatial Leakage Audit

### 5.1 Partition and Grouping Verification
* **Total Candidates:** 250 records.
* **Benchmark Pilot Cohort:** Exactly 15 chips held out (`assigned_fold == "BENCHMARK_HELD_OUT"`).
* **Expansion Cohort:** Exactly 235 chips divided into 5 cross-validation folds.
* **Fold Capacities:**
  * Fold 1: 47 chips
  * Fold 2: 47 chips
  * Fold 3: 47 chips
  * Fold 4: 47 chips
  * Fold 5: 47 chips
* **MGRS Tile Isolation:** 0 MGRS tiles split across folds. All candidates sharing an MGRS tile reside in the identical fold.
* **Incident Group Isolation:** 0 physical incident groups split across folds. All candidates originating from the same ground incident are assigned to the identical fold.

### 5.2 Nationwide Cross-Fold Distance Distribution
Total cross-fold candidate pairs evaluated:
$$\frac{47 \times 47 \times \binom{5}{2}}{1} = 22,090 \text{ candidate pairs}$$

| Metric | Geographic Approximation | Native UTM Raster Geometry |
| :--- | :---: | :---: |
| **Total cross-fold pairs** | 22,090 | 22,090 |
| **Violations ($\le 50.0000\text{ km}$)** | 0 | **1** |
| **Minimum separation** | 50.0079 km | 49.9940 km |
| **Pairs within $50.0 - 52.0\text{ km}$** | 4 | 4 |
| **Pairs within $52.0 - 55.0\text{ km}$** | 9 | 10 |
| **Total pairs $< 55.0000\text{ km}$** | 13 | 14 |

### 5.3 Nearest Cross-Fold Pairs (Native UTM Geometry)

| Rank | Chip 1 (Fold) | Chip 2 (Fold) | Stratum Pair | Center Dist (km) | Native Footprint Dist (km) | Status |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| 1 | `DS08_EXP_S4_018` (F4) | `DS08_EXP_S5_016` (F3) | STR-4 / STR-5 | 56.9915 | **49.9940** | **FAIL (-6.01 m)** |
| 2 | `DS08_EXP_S3_004` (F2) | `DS08_EXP_S4_004` (F4) | STR-3 / STR-4 | 57.2514 | 50.1017 | PASS (+101.7 m) |
| 3 | `DS08_EXP_S3_001` (F4) | `DS08_EXP_S6_004` (F3) | STR-3 / STR-6 | 58.3307 | 51.1768 | PASS (+1,176.8 m) |
| 4 | `DS08_EXP_S2_017` (F4) | `DS08_EXP_S6_019` (F1) | STR-2 / STR-6 | 58.7425 | 51.5083 | PASS (+1,508.3 m) |
| 5 | `DS08_EXP_S5_028` (F5) | `DS08_EXP_S6_026` (F1) | STR-5 / STR-6 | 58.7744 | 51.5727 | PASS (+1,572.7 m) |
| 6 | `DS08_EXP_S3_022` (F4) | `DS08_EXP_S6_010` (F3) | STR-3 / STR-6 | 59.5492 | 52.3943 | PASS (+2,394.3 m) |
| 7 | `DS08_EXP_S1_004` (F3) | `DS08_EXP_S3_053` (F4) | STR-1 / STR-3 | 59.8872 | 52.7138 | PASS (+2,713.8 m) |

### 5.4 Leakage Assessment Conclusion
Aside from the single 6.01-meter margin violation between `DS08_EXP_S4_018` and `DS08_EXP_S5_016`, the spatial blocking protocol provides strong spatial isolation across India. However, because strict scientific protocol prohibits unapproved relaxation of distance bounds, the spatial split cannot be certified as 100% compliant under native raster geometry without explicit protocol resolution.

---

## 6. Live STAC Verification Table for All Eight Pilot Products

Metadata queries were executed against the Copernicus Data Space Ecosystem (CDSE) OData catalog (`https://catalogue.dataspace.copernicus.eu/odata/v1/Products`). Zero raster assets were downloaded.

| Pilot Chip ID | Stratum | Expected Target Class | Manifest STAC Product ID | Catalog Status | CDSE Product UUID | Size (MB) | Sensing Timestamp Match | Required Bands Status | Overall Item Status |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `DS08_EXP_S1_003` | STR-1 | Industrial Fire | `S2B_MSIL2A_20250413T052649_N0511_R105_T43RFN_20250413T074009.SAFE` | **EXISTS_VERIFIED** | `34ce33d0-75a0-4c86-b3c8-d7904711640b` | 1,181.6 | MATCH (`2025-04-13T05:26:49Z`) | Online in SAFE | **PASS** |
| `DS08_EXP_S1_002` | STR-1 | Industrial Fire | `S2B_MSIL2A_20250325T045659_N0511_R119_T44QQE_20250325T074633.SAFE` | **EXISTS_VERIFIED** | `e7f0da0d-942d-48ba-a267-07b385c7ca80` | 325.2 | MATCH (`2025-03-25T04:56:59Z`) | Online in SAFE | **PASS** |
| `DS08_EXP_S1_004` | STR-1 | Industrial Fire | `S2C_MSIL2A_20251028T053951_N0511_R005_T42QZH_20251028T084920.SAFE` | **EXISTS_VERIFIED** | `80fd0f38-b426-4206-abc1-eaed217643f3` | 851.2 | MATCH (`2025-10-28T05:39:51Z`) | Online in SAFE | **PASS** |
| `DS08_EXP_S2_001` | STR-2 | Persistent Thermal Source | `S2A_MSIL2A_20250611T215200_N0511_R063_T43TBB_20250612T010722.SAFE` | **NOT FOUND (0 matches)** | None | None | MISMATCH | Missing | **FAIL / BLOCKED** |
| `DS08_EXP_S3_001` | STR-3 | Forest Fire | `S2B_MSIL2A_20250516T073500_N0511_R106_T43SEM_20250516T105022.SAFE` | **NOT FOUND (0 matches)** | None | None | MISMATCH | Missing | **FAIL / BLOCKED** |
| `DS08_EXP_S4_001` | STR-4 | Agricultural Fire | `S2A_MSIL2A_20241023T081900_N0511_R006_T43SIN_20241023T113422.SAFE` | **NOT FOUND (0 matches)** | None | None | MISMATCH | Missing | **FAIL / BLOCKED** |
| `DS08_EXP_S5_001` | STR-5 | No Fire / Industrial Background | `S2C_MSIL2A_20250115T054807_N0511_R006_T43SKI_20250115T090329.SAFE` | **NOT FOUND (0 matches)** | None | None | MISMATCH | Missing | **FAIL / BLOCKED** |
| `DS08_EXP_S6_001` | STR-6 | No Fire / Natural Background | `S2B_MSIL2A_20250212T051909_N0511_R063_T44SAI_20250212T083431.SAFE` | **NOT FOUND (0 matches)** | None | None | MISMATCH | Missing | **FAIL / BLOCKED** |

### 6.1 Root Cause Analysis of Catalog Discrepancy
* **Stratum 1 candidates** originated from live STAC searches conducted during Stage 8.19 over verified ground industrial incidents. Their product IDs correspond to real, indexed Copernicus granules available for download.
* **Strata 2–6 pilot candidates** originated from background thermal anomaly and land-use coordinate sampling. Their `stac_scene_id` values were synthesized using standard Sentinel-2 naming conventions (e.g., incorporating placeholder timestamps like `21:52:00` UTC, which is nighttime over India). These candidate names were never reconciled against the live CDSE catalog before being locked into the manifest.
* **Impact:** Attempting to download products 4 through 8 using `scripts/stage8_20_pilot_acquisition.py` would result in HTTP 404 / 0 search results from CDSE.

---

## 7. Cloud-Exception Review

The manifest records two explicit conditional cloud exceptions under DEC-U5:
1. `DS08_EXP_S1_002` (Vizag API Pharma fire): Reported scene cloud cover **14.74%** (`cloud_exception_applied: true`, `cloud_exception_id: "DEC-U5"`).
2. `DS08_EXP_S1_004` (Tarapur Chemical explosion): Reported scene cloud cover **19.32%** (`cloud_exception_applied: true`, `cloud_exception_id: "DEC-U5"`).

### Protocol Conditions:
* **Condition 1 (Scene-Level Exception): PASS.** The exception is explicitly recorded in Manifest v3, the decision log (`docs/stage8_19b/stage8_19b_decision_log.md`), and the Stage 8.19B report.
* **Condition 2 (AOI Cloud Contamination $\le 5\%$): CONDITIONAL.** SCL (Scene Classification Layer) pixel analysis over the $5.12\text{ km} \times 5.12\text{ km}$ bounding box cannot be computed prior to raster acquisition.
* **Condition 3 (Center 1 km Contamination $0\%$): CONDITIONAL.** Central $1\text{ km} \times 1\text{ km}$ ($100 \times 100$ pixels) cloud and shadow screening cannot be computed prior to raster acquisition.

### Operational Requirement for Stage 8.20:
Upon authorized retrieval of the SAFE archives for `DS08_EXP_S1_002` and `DS08_EXP_S1_004`, an automated raster screening gate must extract the SCL band jp2 and verify both Condition 2 and Condition 3. If either fails, the candidate must be rejected and replaced according to DEC-U5 fallback provisions.

---

## 8. Acquisition Script Safety Findings

An inspection of `scripts/stage8_20_pilot_acquisition.py` was conducted:

| Safety Requirement | Implementation in Script | Code Location | Status |
| :--- | :--- | :--- | :---: |
| **Strict Pilot Cohort Restriction** | Hardcoded `PILOT_CHIP_IDS` list containing exactly the 8 approved IDs. No iteration over full manifest. | Lines 32–41 | **PASS** |
| **Confirmation Gate** | Requires explicit CLI argument `--confirm-acquisition`. Absent flag terminates in dry run. | Lines 66–70, 104–118 | **PASS** |
| **Dry-Run Mode Zero Bytes** | Dry run returns `downloaded_bytes: 0` without initializing download workers or making network GET calls for rasters. | Lines 105–118 | **PASS** |
| **Protected Output Path** | Output targeted to `data/interim/ds08_stage8_20_pilot/`. Historical pilot packages (`data/reference/ds08/packages/`) cannot be overwritten. | Lines 29, 126 | **PASS** |
| **Credential Protection** | Reads from `.env` using `load_credentials_from_env()`. Never prints or logs `client_id`, `client_secret`, or authorization headers. | Lines 44–60, 100–102 | **PASS** |
| **Single-Candidate Integrity** | Manifest mapping validates existence of each pilot chip ID before execution. | Lines 88–92 | **PASS** |

### Dry-Run Execution Test:
Executing `python scripts/stage8_20_pilot_acquisition.py` confirmed clean execution with 0 bytes downloaded and safe output.

---

## 9. Test Results

### 9.1 Stage 8.19 Test Suites
All four test suites specifically covering candidate discovery, manifest reconciliation, decision resolution, and spatial auditing passed with zero failures:
```
tests/test_ds08_stage8_19_discovery.py .........                         [ 24%]
tests/test_ds08_stage8_19a_audit.py .............                        [ 59%]
tests/test_ds08_stage8_19b_readiness.py ...........                      [ 89%]
tests/test_ds08_stage8_19c_audit.py ....                                 [100%]
============================== 37 passed in 2.47s ==============================
```

### 9.2 Upstream Packages and Review Tests (Stages 8.16–8.18)
All 34 tests covering pilot correction, packaging, expansion planning, and review passed:
```
tests/test_ds08_stage8_16_correction.py ............                     [ 35%]
tests/test_ds08_stage8_17_package.py ............                        [ 70%]
tests/test_ds08_stage8_18_planning.py .....                              [ 85%]
tests/test_ds08_stage8_18a_review.py .....                               [100%]
============================== 34 passed in 3.66s ==============================
```
**Total Passing Tests:** 71 / 71 tests across relevant active suites.

### 9.3 Investigation of Historical Test Failures
A full-repository test run (`tests/test_ds08*.py`) reported 8 failures in older test modules (`test_ds08_stage8_12a_ui_validation.py`, `test_ds08_stage8_12_repair.py`, `test_ds08_stage8_14_cleanup_integrity.py`). Investigation confirmed these failures are due to assertions expecting pilot manual annotation templates to be in `PENDING_MANUAL_INPUT` status. When human annotation was completed in Stage 8.13 and adjudicated in Stage 8.15/8.16, the templates transitioned to `COMPLETED_HUMAN_ANNOTATION`. These failures represent historical stage progression invariants, not regressions in current expansion code.

---

## 10. Artifact Integrity and Hash Comparison

| Artifact File | Expected SHA-256 | Observed SHA-256 | Match |
| :--- | :--- | :--- | :---: |
| `data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json` | `dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848` | `dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848` | YES |
| `data/reference/ds08/packages/ds08_pilot_v1/manifest.json` | `6eed42b0b08da25f6fccbabf7c4d02f980c1a13fec7554160a75d63aebaa2b81` | `6eed42b0b08da25f6fccbabf7c4d02f980c1a13fec7554160a75d63aebaa2b81` | YES |
| `docs/stage8_19b/STAGE8_19B_DECISION_RESOLUTION.md` | `07cab242103488e8a26b178a575840da71de6f3c737ac03258de40295255fda1` | `07cab242103488e8a26b178a575840da71de6f3c737ac03258de40295255fda1` | YES |
| `docs/stage8_19b/STAGE8_19B_SPATIAL_REVALIDATION.md` | `2470de01a3fc6b3bd0d291587779cc46260ce4ab865e22b545b17624c1054467` | `2470de01a3fc6b3bd0d291587779cc46260ce4ab865e22b545b17624c1054467` | YES |
| `docs/stage8_19c/STAGE8_19C_FINAL_PREACQUISITION_AUDIT.md` | `ccba22bbe2ecd105a99452af2e4d905f47ee05d045e0684da4810df8ed71cc9a` | `ccba22bbe2ecd105a99452af2e4d905f47ee05d045e0684da4810df8ed71cc9a` | YES |
| `scripts/stage8_20_pilot_acquisition.py` | `ab5f9ba98d822ac4b70e3e0d760e2a053e21e4ffd368cceef558facbae83d5cd` | `ab5f9ba98d822ac4b70e3e0d760e2a053e21e4ffd368cceef558facbae83d5cd` | YES |

---

## 11. Issues, Blockers, and Unresolved Assumptions

### Blocker 1: Native-Raster Footprint Separation Margin Deficit (Critical Geometry Blocker)
* **Description:** Under the true projected native UTM grid of Sentinel-2 Level-2A imagery, grid convergence tilts the raster bounding boxes by $\sim 0.5^\circ - 0.65^\circ$. This reduces the minimum cross-fold footprint separation between `DS08_EXP_S4_018` (Fold 4) and `DS08_EXP_S5_016` (Fold 3) to **49.993988 km**, which is **6.01 meters below the mandatory 50.0000 km threshold**.
* **Impact:** The candidate partition does not strictly satisfy the 50.0 km footprint separation rule under true native raster geometry.
* **Resolution Requirement:** The project owner must either:
  1. Authorize swapping `DS08_EXP_S4_018` or `DS08_EXP_S5_016` with a compliant candidate from the same stratum, or
  2. Formally document and approve an engineering tolerance exception for differences $\le 10\text{ meters}$ arising from map projection convergence.

### Blocker 2: Synthetic Product IDs for Strata 2–6 (Critical Catalog Blocker)
* **Description:** Only the 3 Stratum 1 pilot products exist in the live CDSE catalog. The remaining 5 pilot products (`DS08_EXP_S2_001`, `DS08_EXP_S3_001`, `DS08_EXP_S4_001`, `DS08_EXP_S5_001`, `DS08_EXP_S6_001`) have synthesized SAFE product IDs that return 0 matches in CDSE.
* **Impact:** Stage 8.20 acquisition cannot acquire 5 of the 8 pilot chips.
* **Resolution Requirement:** A live CDSE STAC spatial query over the coordinates and sensing dates for candidates 4–8 must be executed to resolve actual, downloadable Copernicus SAFE product identifiers before acquisition is initiated.

---

## 12. Final Readiness Determination

### Decision: **BLOCKED — RESOLUTION REQUIRED**

```
+-------------------------------------------------------------------------+
|                      FINAL READINESS DETERMINATION                      |
|                                                                         |
|                     BLOCKED -- RESOLUTION REQUIRED                     |
+-------------------------------------------------------------------------+
| [FAIL]    Native UTM Footprint Separation: 49.9940 km (-6.01 m margin)  |
| [BLOCKED] Live STAC Verification: 5 of 8 pilot products missing in CDSE |
| [PASS]    Acquisition Script Safety Guards and Dry Run                  |
| [PASS]    Test Suites Passing (71/71 active tests)                      |
| [PASS]    Artifact Integrity and Hashes Frozen                          |
| [COND.]   Cloud Exceptions Pending Post-Acquisition SCL Raster Gate     |
+-------------------------------------------------------------------------+
```

### Justification:
While safety guards, artifact integrity, and test suites are fully compliant, imagery acquisition cannot be authorized because:
1. True native raster geometry fails the 50.0 km spatial separation rule by 6.01 meters.
2. Five of the eight pilot candidates do not resolve to real products in the Copernicus Data Space Ecosystem catalog.

Controlled pilot acquisition is held pending resolution of these two blockers by the dataset owner.
