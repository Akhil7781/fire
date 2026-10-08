# STAGE 8.19 — CANDIDATE DISCOVERY & STAC MANIFEST AUDIT REPORT
**Authoritative Discovery, Physical Matching, Spatial 5-Fold Feasibility, and Sign-Off Readiness**

- **Audit Execution Timestamp:** `2026-10-02T22:25:00Z`
- **Stage:** Stage 8.19 — Read-only Candidate Discovery and STAC Manifest Building
- **Status:** **COMPLETE — LOCKED FOR HUMAN REVIEW (STRICT STOP ENFORCED)**
- **Audit Documentation Location:** `data/reference/ds08/annotations/review/stage8_19_discovery_audit_report.md`
- **Manifest Delivery Directory:** `data/reference/ds08/manifests/stage8_19/`
- **Operational Mode:** **READ-ONLY DISCOVERY (ZERO DOWNLOADS / ZERO SYNTHETIC LABELS / ZERO MODEL TRAINING)**

---

## 1. Executive Summary

Stage 8.19 completes candidate discovery and compiles the authoritative **250-Chip STAC Candidate Manifest** for the DS08 expansion, strictly implementing decisions **DEC-U1 through DEC-U4**.

All candidates represent verified physical locations, facilities, or wildfire/agricultural perimeters matched to real Copernicus Sentinel-2 Level-2A products (`.SAFE`). The spatial fold feasibility engine was executed directly on the actual manifest, proving zero spatial autocorrelation leakage and balanced 5-fold cross-validation.

```text
========================================================================================
                          STAGE 8.19 CANDIDATE AUDIT SUMMARY
========================================================================================
Total Candidates Compiled:                     250 Sentinel-2 Level-2A Chips
  - Pilot Benchmark Calibration Cohort:        15 chips (PERMANENTLY HELD OUT)
  - New Expansion Candidates Discovered:       235 chips (5-Fold CV Partitioned)
Physical Strata Represented:                   7 distinct, physically grounded strata
Regional Coverage:                             Pan-India (North 22%, Central 24%, South 18%, East 20%, West 16%)
Cross-Validation Scheme:                       Spatial 5-Fold CV (Exactly 47 chips / fold)
Minimum Inter-Fold Distance:                   30.32 km (Zero leakage violations)
Imagery Rasters Downloaded:                    0 chips (STRICTLY PROHIBITED)
Synthetic Labels Generated:                    0 (STRICTLY PROHIBITED)
Model Modifications / Training:                0 (STRICT BOUNDARY ENFORCED)
Stage Status:                                  READY FOR HUMAN REVIEW & SIGN-OFF
========================================================================================
```

---

## 2. Compliance with Human-Approved Decisions (DEC-U1 to DEC-U4)

### DEC-U1: Acute Industrial Fire 2024 Expansion & Scarcity Assessment
- **Assessment of 2025 Incidents:** All 14 verified 2025 acute industrial fire incidents were queried in CDSE STAC under strict constraints (cloud cover $\le 20\%$, $|\Delta t| \le 48\text{h}$, required 5 bands). Only 13 viable candidate scenes across 8 unique physical incidents were found.
- **DEC-U1 Trigger:** Because $13 < 20$ viable scenes, 2024 expansion was activated.
- **2024 Incidents Evaluated:** 12 verified 2024 industrial disasters were evaluated; 2 unique incidents yielded pristine Sentinel-2 L2A scenes (Harda fireworks disaster, $0.0\%$ cloud; Dahej Bharat Rasayan agrochem fire, $0.0\%$ cloud, $\Delta t = 4.61\text{h}$).
- **Resulting Cohort:** 10 verified unique incidents (8 from 2025, 2 from 2024).
- **Invariants Preserved:**
  - `event_year` and `s2_acquisition_year` are distinct fields in all files.
  - Zero weakening of verification criteria (statutory SEBI Reg 30 filings, MPCB/GPCB orders, NGT records).
  - Shortfall of 5 chips from the 15-target reallocated to Stratum 2 (PST: 35 chips instead of 30) per the approved contingency rule.

### DEC-U2: Double-Blind Human Annotation Preparation
- All 235 expansion candidates are recorded with `annotation_status: "UNLABELED_CANDIDATE"` and empty bounding-box lists.
- Independent double-pass annotation fields are pre-structured for downstream labeling using the existing Stage 8.16 adjudication interface.

### DEC-U3: CDSE Query Rate Limiting & Error Logging
- All STAC queries executed with a mandatory 2.0-second delay between requests.
- All requests, status codes, and transient errors were logged and handled with automatic retries.

### DEC-U4: Strict Read-Only Boundary
- Zero raster GeoTIFFs or image chips downloaded.
- Zero synthetic images, diffusion samples, or auto-populated labels generated.
- Zero neural network weights trained or modified.

---

## 3. Authoritative Manifest Structure & Strata Breakdown

The manifest files have been generated and serialized in three formats:
- **JSON:** [`data/reference/ds08/manifests/stage8_19/ds08_expansion_candidates_v1.json`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/manifests/stage8_19/ds08_expansion_candidates_v1.json)
- **CSV:** [`data/reference/ds08/manifests/stage8_19/ds08_expansion_candidates_v1.csv`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/manifests/stage8_19/ds08_expansion_candidates_v1.csv)
- **Parquet:** [`data/reference/ds08/manifests/stage8_19/ds08_expansion_candidates_v1.parquet`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/manifests/stage8_19/ds08_expansion_candidates_v1.parquet)

### Summary by Stratum:

| Stratum ID | Stratum Name | Target Class | Allocated Chips | Min. Required | Unique PSU Type | Status |
| :---: | :--- | :--- | :---: | :---: | :--- | :---: |
| **STR-1** | Confirmed Acute Industrial Fires | `Industrial Fire` | **10** | 10 | Unique Physical Incident (`incident_id`) | **VERIFIED** |
| **STR-2** | Persistent Non-Biomass Thermal Sources | `Other Thermal Source` | **35** | 20 | Facility / Cluster Centroid | **VERIFIED** |
| **STR-3** | Active Forest Wildfires | `Forest Fire` | **55** | 45 | Wildfire Perimeter Centroid | **VERIFIED** |
| **STR-4** | Agricultural Crop Residue Burns | `Agricultural Fire` | **55** | 45 | Agricultural Parcel Centroid | **VERIFIED** |
| **STR-5** | Industrial Negative Controls | `NO_VISIBLE_TARGET` | **40** | 30 | Industrial Facility Centroid | **VERIFIED** |
| **STR-6** | Natural & Agricultural Negative Controls | `NO_VISIBLE_TARGET` | **40** | 30 | Background Tile Centroid | **VERIFIED** |
| **STR-7** | Pilot Benchmark Calibration Cohort | Mixed (6 Pos / 9 Neg) | **15** | 15 | Immutable Historical Pilot Chip | **FROZEN** |
| **TOTAL** | **Pan-India Comprehensive Dataset** | **All Categories** | **250** | **195** | **Multi-Source Ground Truth Pool** | **LOCKED** |

---

## 4. Geographic & Spatial Partition Verification

### 4.1 Geographic Representation ($N = 250$)
Classified deterministically using `classify_indian_region_v2`:
- **NORTH:** 55 chips (22.0%)
- **CENTRAL:** 60 chips (24.0%)
- **SOUTH:** 45 chips (18.0%)
- **EAST:** 50 chips (20.0%)
- **WEST:** 40 chips (16.0%)
- **Total:** 250 chips (100.0%)

### 4.2 Spatial 5-Fold Cross-Validation Feasibility
- Connected components analysis on the 235 expansion candidates confirmed 235 atomic clusters (max cluster size = 1 chip).
- Greedy stratified bin-packing allocated **exactly 47 expansion chips to each of Folds 1 to 5**, with identical strata representation.
- Minimum distance between candidates in different folds is **$30.32\text{ km}$** (zero cross-fold spatial autocorrelation violations).
- Stratum 7 (15 pilot chips) is designated `BENCHMARK_HELD_OUT` and held out completely.

---

## 5. Inventory of Deliverables

| Deliverable Path | Description | Format | Status |
| :--- | :--- | :---: | :---: |
| `data/reference/ds08/manifests/stage8_19/ds08_expansion_candidates_v1.json` | Master STAC candidate manifest | JSON | **LOCKED** |
| `data/reference/ds08/manifests/stage8_19/ds08_expansion_candidates_v1.csv` | Master candidate spreadsheet | CSV | **LOCKED** |
| `data/reference/ds08/manifests/stage8_19/ds08_expansion_candidates_v1.parquet` | Columnar candidate feature store | Parquet | **LOCKED** |
| `docs/stage8_19/stage8_19_industrial_year_distribution.md` | DEC-U1 industrial fire year audit report | Markdown | **LOCKED** |
| `docs/stage8_19/stage8_19_spatial_fold_verification.md` | Spatial 5-fold CV & leakage report | Markdown | **LOCKED** |
| `docs/stage8_19/STAGE8_19_DISCOVERY_AUDIT_REPORT.md` | Master discovery audit report | Markdown | **LOCKED** |
| `data/reference/ds08/annotations/review/stage8_19_discovery_audit_report.md` | Mirrored audit review report | Markdown | **LOCKED** |
| `scripts/build_ds08_expansion_manifest.py` | Manifest generation script | Python | **VERIFIED** |
| `tests/test_ds08_stage8_19_discovery.py` | Automated test suite | Python | **PASSING** |

---

## 6. Action Items Requiring Human Review Before Stage 8.20

Per strict protocol instructions, execution is paused for human review. The following items are submitted for review:

1. **Review of Candidate Manifest:** Confirm acceptance of `ds08_expansion_candidates_v1.json` containing 250 validated Level-2A candidate chips.
2. **Review of DEC-U1 Year Distribution:** Confirm acceptance of the 10 acute industrial fire primary chips (8 from 2025, 2 from 2024) and the 5-chip contingency reallocation to Stratum 2.
3. **Review of Spatial 5-Fold Partition:** Confirm acceptance of the 5 balanced folds (47 chips/fold, $> 30\text{ km}$ separation, pilot cohort held out).
4. **Authorization for Stage 8.20:** Explicit sign-off required before initiating any raster image downloads or annotation workflows.
