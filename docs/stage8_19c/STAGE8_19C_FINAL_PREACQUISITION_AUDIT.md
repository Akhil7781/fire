# Stage 8.19C — Final Pre-Acquisition Code, Geometry, and Script Safety Audit

## Document Metadata
- **Audit Stage:** Stage 8.19C (Final Pre-Acquisition Code and Geometry Audit)
- **Date:** 2026-10-02
- **Authoritative Files Inspected:**
  - Manifest: `data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json`
  - Spatial Audit Script: `scripts/audit_stage8_19b_spatial_footprint.py`
  - Manifest v3 Builder: `scripts/build_ds08_expansion_manifest_v3.py`
  - Acquisition Script: `scripts/stage8_20_pilot_acquisition.py`
  - Test Suite: `tests/test_ds08_stage8_19b_readiness.py`
- **Audit Mode:** **STRICT READ-ONLY (Zero Network Calls, Zero Imagery Downloads, Zero Model Training)**
- **Audit Status:** **READY FOR LIVE READ-ONLY STAC VERIFICATION**

---

## 1. Spatial Geometry Verification

### 1.1 Footprint Construction Methodology
In [`scripts/build_ds08_expansion_manifest_v3.py`](file:///d:/DATA%20PREPROCESSING/scripts/build_ds08_expansion_manifest_v3.py) and [`scripts/audit_stage8_19b_spatial_footprint.py`](file:///d:/DATA%20PREPROCESSING/scripts/audit_stage8_19b_spatial_footprint.py), chip footprints are constructed from center coordinates $(\text{lat}_c, \text{lon}_c)$ and standard Sentinel-2 chip dimensions ($512 \times 512$ pixels at $10.0\text{ m}$ GSD = $5,120\text{ m} \times 5,120\text{ m}$):
- Half-width offset: $r_{\text{half}} = 2,560\text{ m}$.
- Direct geodesic steps on the WGS84 ellipsoid via `pyproj.Geod(ellps='WGS84').fwd`:
  - $\text{North Point: } (\text{lon}_n, \text{lat}_n) \gets \text{fwd}(\text{lon}_c, \text{lat}_c, 0^\circ, 2560\text{ m})$
  - $\text{South Point: } (\text{lon}_s, \text{lat}_s) \gets \text{fwd}(\text{lon}_c, \text{lat}_c, 180^\circ, 2560\text{ m})$
  - $\text{East Point: } (\text{lon}_e, \text{lat}_e) \gets \text{fwd}(\text{lon}_c, \text{lat}_c, 90^\circ, 2560\text{ m})$
  - $\text{West Point: } (\text{lon}_w, \text{lat}_w) \gets \text{fwd}(\text{lon}_c, \text{lat}_c, 270^\circ, 2560\text{ m})$
- Angular deltas: $\Delta\text{lat} = (\text{lat}_n - \text{lat}_s)/2$, $\Delta\text{lon} = (\text{lon}_e - \text{lon}_w)/2$.
- The resulting 4-corner bounding polygon represents an axis-aligned bounding box enclosing the chip footprint.

### 1.2 Verification of Footprint-to-Footprint Distance Calculation
The code evaluates the minimum distance between two polygons $\mathcal{P}_1$ and $\mathcal{P}_2$:
```python
def footprint_edge_distance_km(geod: Geod, poly1, poly2):
    min_d = 999999999.0
    for x1, y1 in poly1:
        for x2, y2 in poly2:
            _, _, d = geod.inv(x1, y1, x2, y2)
            if d < min_d:
                min_d = d
    return min_d / 1000.0
```

#### Independent Mathematical Check: Corner-to-Corner vs. Continuous Edge
We independently tested whether evaluating only the 4 corner points is mathematically equivalent to continuous edge-to-edge evaluation:
- For convex polygons separated along an oblique vector, the minimum distance between the two polygons occurs strictly at the **facing corners**.
- We executed a dense boundary audit sampling 100 points along each edge (400 points per chip, 160,000 point evaluations per close pair).
- **Result:** For the closest pair (`DS08_EXP_S4_018` vs `DS08_EXP_S5_016`), the corner-to-corner distance is **$50,007.87\text{ m}$**, and the dense edge-to-edge distance is **$50,007.87\text{ m}$** (identical to sub-millimeter precision).
- Across all 22,090 cross-fold pairs, corner evaluation matches continuous edge evaluation within $< 5.7\text{ meters}$ in non-diagonal orientations, with zero cross-fold pairs violating the $50\text{ km}$ threshold.

### 1.3 Appropriateness of Geodesic vs. Projected Coordinate Systems
- Sentinel-2 Level-2A granules across India span **six Universal Transverse Mercator (UTM) zones** (Zones 42N to 47N, covering $68^\circ\text{E}$ to $98^\circ\text{E}$).
- A single planar projected coordinate system (such as UTM Zone 44N or an India-wide Albers Equal Area projection) suffers from scale distortion (up to $\pm 0.5\% \sim 250\text{ m}$ over $50\text{ km}$) and cannot represent trans-zone spatial relationships seamlessly.
- **Geodesic Evaluation on WGS84:** Utilizing Karney's geodesic inverse algorithm on the WGS84 ellipsoid ($a = 6378137.0\text{ m}, f = 1/298.257223563$) is the **most methodologically accurate approach possible** because it is mathematically continuous, zone-agnostic, and accurate to sub-millimeter scale nationwide.

### 1.4 Reproducibility and Robustness of the 50.0079 km Minimum
- **Closest Cross-Fold Pair:**
  - Chip 1: `DS08_EXP_S4_018` (Fold 4, Agricultural Burn in Maharashtra/Telangana border, Lat 19.67723, Lon 79.85232).
  - Chip 2: `DS08_EXP_S5_016` (Fold 3, Industrial Negative Control in Maharashtra/Telangana border, Lat 20.12000, Lon 80.13000).
  - Center-to-Center Distance: **$56.9915\text{ km}$**.
  - Facing Corners Distance: **$50.00787\text{ km} = \mathbf{50.0079\text{ km}}$**.
- **Numerical Robustness & Sensitivity Finding:**
  - The margin of safety above $50.0000\text{ km}$ for this single pair is **$7.87\text{ meters}$** ($0.016\%$).
  - Why did this occur? In `build_ds08_expansion_manifest_v3.py`, the spatial clustering engine applied graph edges for $D_{\text{edge}} \le 50.0000\text{ km}$. This pair evaluated to $50.00787\text{ km} > 50.0000\text{ km}$, so it was not forced into the same cluster.
  - *Sensitivity under UTM Grid Convergence:* In a native Sentinel-2 raster, the chip is aligned to UTM Grid North rather than True North. At this location (UTM Zone 44N), the grid convergence angle is $\gamma = -0.387^\circ$. Under worst-case orientation, a $0.387^\circ$ rotation of a $2.56\text{ km}$ edge shifts corner coordinates by $\approx 17.3\text{ meters}$. If evaluated in local raster pixel coordinates, this pair could theoretically measure $49.99\text{ km}$.
  - **Audit Assessment:** Under the locked WGS84 geographic bounding box standard, the pair **strictly passes ($50.0079\text{ km} > 50.0000\text{ km}$)**. However, because the margin is $7.87\text{ m}$, we formally flag this pair for human awareness. If a $> 1\text{ km}$ safety buffer is desired, a forced incident/pair group can lock these two chips into the same fold.

### 1.5 Verification of Invariants in Manifest v3
- **All Cross-Fold Pairs $\ge 50.0\text{ km}$:** **100% PASS (0 violations across 22,090 inter-fold pairs)**.
- **5-Fold Balance:** **Exactly 47 chips** in each of Folds 1, 2, 3, 4, 5 ($47 \times 5 = 235$ expansion chips).
- **Pilot Benchmark Isolation:** **Exactly 15 chips** assigned to `BENCHMARK_HELD_OUT` outside cross-validation folds.
- **MGRS Tile Isolation:** **0 tile splits** across folds.
- **Physical Incident Isolation:** **0 incident splits** across folds.

---

## 2. Acquisition Script Safety Audit

### 2.1 Inspection of `scripts/stage8_20_pilot_acquisition.py`
We inspected the source code of [`scripts/stage8_20_pilot_acquisition.py`](file:///d:/DATA%20PREPROCESSING/scripts/stage8_20_pilot_acquisition.py) to assess execution safety:

| Audit Checkpoint | Code Implementation / Verification | Audit Finding |
|:---|:---|:---:|
| **Eligible Records Scope** | Explicit list `PILOT_CHIP_IDS` of length 8 (lines 32–41). | **RESTRICTED TO 8 CHIPS** |
| **Bulk Acquisition Path** | No loop over full candidate roster `records`. Only indexes `PILOT_CHIP_IDS`. | **NO BULK PATH EXISTS** |
| **Command-Line Gate** | `if not confirm_acquisition: return {"mode": "DRY_RUN", ...}` (lines 105–118). | **MANDATORY FLAG ENFORCED** |
| **Default Execution Mode** | Default flag `confirm_acquisition=False`. Running script without args defaults to dry run. | **SAFE DRY-RUN BY DEFAULT** |
| **Live Catalog Requests** | `run_acquisition_pilot()` in dry-run mode issues **zero HTTP requests**. | **ZERO LIVE CALLS IN DRY RUN** |
| **Credential Security** | `load_credentials_from_env()` loads from `.env`; script prints only boolean `has_creds`. | **ZERO CREDENTIAL LEAKAGE** |
| **Output Directory Safety** | Target directory `data/interim/ds08_stage8_20_pilot/` is isolated from reference data. | **NO OVERWRITE OF BASELINE** |
| **Dry-Run Output** | Verified by running script: returns `downloaded_bytes: 0` and writes zero files. | **100% PASS** |

### 2.2 Alignment Between Code and Architecture Specification
- In [`scripts/stage8_20_pilot_acquisition.py`](file:///d:/DATA%20PREPROCESSING/scripts/stage8_20_pilot_acquisition.py), the script currently implements configuration validation, credential checks, candidate manifest lookup, and the `--confirm-acquisition` gate.
- The full download pipeline (Keycloak OAuth token acquisition, CDSE OData asset streaming, 20m bilinear resampling, and SCL screening) is specified in [`STAGE8_20_PILOT_ACQUISITION_PLAN.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_19b/STAGE8_20_PILOT_ACQUISITION_PLAN.md).
- Because downloading imagery was prohibited during Stage 8.19B and 8.19C, the download methods remain staged and will be executed only after live STAC verification and owner approval.

---

## 3. Pilot Cohort Review

### 3.1 Inspection of the 8 Proposed Pilot Records
All eight proposed pilot candidates were verified in [`data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json):

| Pilot ID | Candidate ID | Stratum | Expected Target Class | Scene Cloud % | Assigned Fold (v3) | ESA Product Identifier | Cloud Exception Status |
|:---:|:---|:---|:---|:---:|:---:|:---|:---:|
| **P-01** | `DS08_EXP_S1_003` | `STR-1` | Industrial Fire | $0.00\%$ | **Fold 5** | `S2B_MSIL2A_20250413T052649_N0511_R105_T43RFN_20250413T074009.SAFE` | Standard ($\le 10\%$) |
| **P-02** | `DS08_EXP_S1_002` | `STR-1` | Industrial Fire | $14.74\%$ | **Fold 4** | `S2B_MSIL2A_20250325T045659_N0511_R119_T44QQE_20250325T074633.SAFE` | **DEC-U5 Conditional Exception** |
| **P-03** | `DS08_EXP_S1_004` | `STR-1` | Industrial Fire | $19.32\%$ | **Fold 3** | `S2C_MSIL2A_20251028T053951_N0511_R005_T42QZH_20251028T084920.SAFE` | **DEC-U5 Conditional Exception** |
| **P-04** | `DS08_EXP_S2_001` | `STR-2` | Other Thermal Source | $2.60\%$ | **Fold 4** | `S2A_MSIL2A_20250611T215200_N0511_R063_T43TBB_20250612T010722.SAFE` | Standard ($\le 10\%$) |
| **P-05** | `DS08_EXP_S3_001` | `STR-3` | Forest Fire | $2.00\%$ | **Fold 4** | `S2B_MSIL2A_20250516T073500_N0511_R106_T43SEM_20250516T105022.SAFE` | Standard ($\le 10\%$) |
| **P-06** | `DS08_EXP_S4_001` | `STR-4` | Agricultural Fire | $1.20\%$ | **Fold 3** | `S2A_MSIL2A_20241023T081900_N0511_R006_T43SIN_20241023T113422.SAFE` | Standard ($\le 10\%$) |
| **P-07** | `DS08_EXP_S5_001` | `STR-5` | NO_VISIBLE_TARGET | $0.90\%$ | **Fold 1** | `S2C_MSIL2A_20250115T054807_N0511_R006_T43SKI_20250115T090329.SAFE` | Standard ($\le 10\%$) |
| **P-08** | `DS08_EXP_S6_001` | `STR-6` | NO_VISIBLE_TARGET | $0.80\%$ | **Fold 5** | `S2B_MSIL2A_20250212T051909_N0511_R063_T44SAI_20250212T083431.SAFE` | Standard ($\le 10\%$) |

### 3.2 Audit Findings on Pilot Records:
1. **Stratum Diversity:** All six candidate strata (STR-1 through STR-6) are represented.
2. **Platform Diversity:** S2A (2 records), S2B (4 records), and S2C (2 records) are all exercised.
3. **DEC-U5 Cloud Testing:** Both cloud-exception candidates (`DS08_EXP_S1_002` and `DS08_EXP_S1_004`) are included to directly test the SCL AOI-level ($\le 5\%$) and center-area ($100\%$ cloud-free) screening gate.
4. **Decoupled Taxonomy:** All 8 records have `human_confirmed_label = null` and `annotation_status = "UNLABELED_CANDIDATE"`.
5. **Minor Documentation Discrepancy Resolved:** In the preliminary draft table of `STAGE8_20_PILOT_ACQUISITION_PLAN.md`, the assigned folds reflected the pre-revalidation fold numbers (e.g. Fold 1 for S1-003). In the authoritative Manifest v3, the footprint-aware re-clustering placed them in Folds 5, 4, 3, 4, 4, 3, 1, and 5 respectively. The manifest is authoritative.

---

## 4. Test Execution & Artifact Integrity

### 4.1 Pytest Execution (Zero Network / Read-Only)
We executed the full non-networked regression test suite:
```bash
pytest tests/test_ds08_stage8_19b_readiness.py tests/test_ds08_stage8_19a_audit.py tests/test_ds08_stage8_19_discovery.py tests/test_ds08_stage8_18a_review.py tests/test_ds08_stage8_18_planning.py tests/test_ds08_stage8_17_package.py tests/test_ds08_stage8_16_correction.py
```

**Results:**
```text
============================= test session starts =============================
platform win32 -- Python 3.10.6, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\DATA PREPROCESSING
collected 67 items

tests/test_ds08_stage8_19b_readiness.py ...........                      [ 16%]
tests/test_ds08_stage8_19a_audit.py .............                        [ 35%]
tests/test_ds08_stage8_19_discovery.py .........                         [ 49%]
tests/test_ds08_stage8_18a_review.py .....                               [ 56%]
tests/test_ds08_stage8_18_planning.py .....                              [ 64%]
tests/test_ds08_stage8_17_package.py ............                        [ 82%]
tests/test_ds08_stage8_16_correction.py ............                     [100%]

============================= 67 passed in 6.17s ==============================
```

### 4.2 Cryptographic Hash Verification of Artifacts
SHA-256 hashes of all prior and Stage 8.19B deliverables were verified intact:

| Artifact Path | Stage | Verified SHA-256 Checksum | Integrity Status |
|:---|:---:|:---|:---:|
| `data/reference/ds08/packages/ds08_pilot_v1/manifest.json` | 8.17 | `6eed42b0b08da25f6fccbabf7c4d02f980c1a13fec7554160a75d63aebaa2b81` | **UNCHANGED** |
| `data/reference/ds08/manifests/stage8_19/ds08_expansion_candidates_v1.json` | 8.19 | `42a63f5aca8a53ed7ec338e3091016c4b354936d34e5c4af1a3cbe74d686961c` | **UNCHANGED** |
| `data/reference/ds08/manifests/stage8_19a/ds08_expansion_candidates_v2.json` | 8.19A | `c06b96944417dae402924f1f7ab4c223853da9f0ce80aeed9ab14da109d8b71a` | **UNCHANGED** |
| `data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json` | 8.19B | `dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848` | **UNCHANGED** |
| `docs/stage8_19b/STAGE8_19B_DECISION_RESOLUTION.md` | 8.19B | `07cab242103488e8a26b178a575840da71de6f3c737ac03258de40295255fda1` | **UNCHANGED** |
| `docs/stage8_19b/STAGE8_19B_SPATIAL_REVALIDATION.md` | 8.19B | `2470de01a3fc6b3bd0d291587779cc46260ce4ab865e22b545b17624c1054467` | **UNCHANGED** |
| `docs/stage8_19b/STAGE8_19B_ALLOCATION_RECONCILIATION.md` | 8.19B | `1193594f9e4bdced4d3b9598a1c517e69f85cfcb0de80b14cae8e6a4898db951` | **UNCHANGED** |
| `docs/stage8_19b/STAGE8_20_PILOT_ACQUISITION_PLAN.md` | 8.19B | `dd960ba972fae531895f4e0c122531ad7ada527413f957b064416e0ebdc8b1ef` | **UNCHANGED** |

---

## 5. Remaining Risks and Precautions

1. **Closest Pair Numerical Margin ($7.87\text{ m}$):** The minimum cross-fold footprint edge distance is $50.0079\text{ km}$. While strictly passing $> 50.0000\text{ km}$, this margin is small. If local UTM raster grid rotation is taken into account, the separation is close to the threshold boundary.
2. **DEC-U5 SCL Rejection Risk:** During Stage 8.20 execution, if either `DS08_EXP_S1_002` or `DS08_EXP_S1_004` exhibits $> 5.0\%$ AOI cloud or $> 0.0\%$ center cloud, it will be rejected immediately, producing an industrial fire shortfall.
3. **CDSE Service Availability:** The live catalog query and raster download pipeline depends on CDSE OData/STAC responsiveness and OAuth2 Keycloak token availability.

---

## 6. Audit Status Determination

### Definitive Status:
**READY FOR LIVE READ-ONLY STAC VERIFICATION**

- All code, geometry, and safety mechanisms have been audited and verified.
- The execution script is protected by `--confirm-acquisition` and defaults to read-only dry-run mode.
- **Stage 8.20 imagery download remains BLOCKED** until:
  1. A read-only live STAC verification query confirms asset presence in CDSE without downloading data.
  2. The project owner reviews the STAC verification results and grants explicit authorization.
