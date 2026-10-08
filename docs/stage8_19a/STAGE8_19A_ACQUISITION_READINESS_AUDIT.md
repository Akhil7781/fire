# Stage 8.19A — Pre-Acquisition Readiness & Integrity Audit Report
**Read-Only Assessment of DS08 Expansion Candidate Manifest v2 Prior to Stage 8.20**

## Document Metadata
- **Audit Stage:** Stage 8.19A Final Pre-Acquisition Review
- **Date:** 2026-10-02
- **Authoritative Manifest Audited:** `data/reference/ds08/manifests/stage8_19a/ds08_expansion_candidates_v2.json`
- **Total Records Evaluated:** 250 records (235 Expansion Candidates, 15 Frozen Pilot Benchmark Chips)
- **Operational Constraint Status:**
  - CDSE live catalog queries: **0 executed**
  - Raster imagery downloads: **0 executed**
  - Annotation labels assigned: **0 generated**
  - Model training/inference: **0 executed**
- **Existing Artifacts Preserved:** 100% of Stage 8.19 and prior stage files remain unmodified.

---

## 1. Executive Summary & Readiness Scorecard

| # | Readiness Dimension | Evaluation Standard | Stored Value / Result | Audit Status | Required Action / Decision |
|:---:|:---|:---|:---:|:---:|:---|
| **1** | **Scene Cloud Cover (Gate 1)** | $\le 10.0\%$ (Original Stage 8.18) | 248 / 250 records $\le 10.0\%$ (mean = $2.63\%$) | **FAIL / HUMAN DECISION** | 2 records exceed 10.0%: requires **DEC-U5** |
| **2** | **AOI Cloud Cover (Gate 2)** | $\le 5.0\%$ over $5.12 \times 5.12\text{ km}$ AOI | Not present in STAC catalog metadata | **PENDING SCL IN STAGE 8.20** | Execute SCL pixel mask upon raster retrieval |
| **3** | **Center-Area Cloud (Gate 2b)** | $100\%$ cloud-free over central $1\text{ km}$ | Not present in STAC catalog metadata | **PENDING SCL IN STAGE 8.20** | Enforce zero SCL cloud in central $1\text{ km}$ |
| **4** | **Geodesic Distances (Center)** | $\Delta_{\text{min}} > 50.0\text{ km}$ (WGS84 Ellipsoid) | $\Delta_{\text{min}} = \mathbf{50.1595\text{ km}}$ (0 pairs $\le 50.0\text{ km}$) | **PASS** | Center-to-center spatial buffer 100% compliant |
| **5** | **Geodesic Distances (Footprint)** | $\Delta_{\text{min}} > 50.0\text{ km}$ (Edge-to-Edge) | $\Delta_{\text{min}} = \mathbf{43.8213\text{ km}}$ (9 pairs $\le 50.0\text{ km}$) | **HUMAN CLARIFICATION** | Clarify center vs footprint rule (**DEC-U6**) |
| **6** | **MGRS Tile Grouping** | Same MGRS tile hard-locked to same fold | 0 tiles split across folds | **PASS** | MGRS tile blocking 100% compliant |
| **7** | **Incident Grouping** | Same incident hard-locked to same fold | 0 incidents split across folds | **PASS** | Incident blocking 100% compliant |
| **8** | **Saved STAC Evidence Validation** | Matching product IDs, times, clouds on disk | 15/15 pilot match; 10/10 industrial match | **PASS (Offline)** | Validated against stored discovery files |
| **9** | **Live Catalog Verification** | CDSE live API search confirmation | 0 live queries performed | **PENDING STAGE 8.20** | Read-only constraint preserved |
| **10** | **2024 Industrial Fire Evidence** | Statutory / regulatory corroboration | 2 incidents: Harda (SDMA) & Dahej (SEBI) | **PASS** | High-evidence standard strictly preserved |

---

## 2. Cloud Cover Audit: Scene-Level vs. AOI-Level vs. Center-Area

### 2.1 The Three Cloud Evaluation Tiers
A core principle of optical remote sensing is that **scene-level cloud cover does not prove that the event target area is clear**:
- A Sentinel-2 MGRS granule spans **$100\text{ km} \times 100\text{ km} = 10,000\text{ km}^2$**.
- A candidate chip AOI spans **$5.12\text{ km} \times 5.12\text{ km} = 26.21\text{ km}^2$** ($0.26\%$ of the scene).
- The event center target spans **$1.0\text{ km} \times 1.0\text{ km} = 1.00\text{ km}^2$** ($0.01\%$ of the scene).

Consequently:
1. A scene with only $1.5\%$ overall cloud cover may have an isolated cumulus cloud sitting directly on the burning plant, obscuring the smoke plume.
2. Conversely, a scene with $15\%$ cloud cover across the $10,000\text{ km}^2$ tile may be completely clear-sky over the specific facility.

### 2.2 Status in Candidate Manifest v2
| Cloud Evaluation Tier | Geographic Scale | Data Source in Manifest v2 | Current Audit Result | Acquisition Gate Status |
|:---|:---|:---|:---|:---|
| **Tier 1: Scene-Level** | $100\text{ km} \times 100\text{ km}$ ($10,000\text{ km}^2$) | STAC metadata property `cloud_cover_pct` | Mean: **$2.63\%$**, Median: **$2.00\%$**, Range: $[0.00\%, 19.32\%]$ | **AUDITED**: 248 records pass original $\le 10\%$; 2 records exceed $\le 10\%$ |
| **Tier 2: AOI-Level** | $5.12\text{ km} \times 5.12\text{ km}$ ($26.21\text{ km}^2$) | Level-2A Scene Classification Layer (SCL) | **Not available in STAC metadata prior to raster download** | **PENDING STAGE 8.20**: Must be evaluated when downloading SCL band |
| **Tier 3: Center-Area** | $1.00\text{ km} \times 1.00\text{ km}$ ($1.00\text{ km}^2$) | Level-2A Scene Classification Layer (SCL) | **Not available in STAC metadata prior to raster download** | **PENDING STAGE 8.20**: Must enforce 0% cloud over central 1 km |

---

## 3. Identification of Records Violating Original Cloud Thresholds

### 3.1 Policy Comparison: Original vs. Discovery Query Thresholds
- **Original Stage 8.18 Gate 1 Protocol:** `cloud_cover_pct <= 10.0%`.
- **Stage 8.19 Candidate Discovery Filter:** In Stage 8.19, STAC search filters for acute industrial fires were widened to $\le 20.0\%$ because 2025 acute industrial disasters were so scarce (only 8 unique incidents with overpasses within 48h existed in all of India).

### 3.2 List of Affected Records Exceeding Original 10.0% Threshold
Under the strict original Stage 8.18 Gate 1 requirement ($\le 10.0\%$), exactly **2 candidate records** violate the threshold:

| Chip ID | Stratum | Incident ID | Facility Name & Location | Assigned Fold | Scene Cloud Cover | Temporal Delta ($\Delta t$) | ESA Product ID |
|:---|:---:|:---|:---|:---:|:---:|:---:|:---|
| **`DS08_EXP_S1_002`** | `STR-1` | `NGT_2025_VIZAG_PHARMA_03` | Active Pharmaceutical Ingredient (API) Bulk Drug Unit, Jawaharlal Nehru Pharma City, Visakhapatnam, Andhra Pradesh | **Fold 5** | **$14.74\%$** | $19.23\text{ h}$ (Tier 3) | `S2B_MSIL2A_20250325T045659_N0511_R119_T44QQE_20250325T074633.SAFE` |
| **`DS08_EXP_S1_004`** | `STR-1` | `SPCB_2025_TARAPUR_CHEM_10` | Industrial Solvents and Hazardous Waste Recovery Unit, MIDC Tarapur, Maharashtra | **Fold 5** | **$19.32\%$** | $3.11\text{ h}$ (Tier 2) | `S2C_MSIL2A_20251028T053951_N0511_R005_T42QZH_20251028T084920.SAFE` |

Neither record was silently modified, replaced, or normalized.

### 3.3 Human Decision Required: DEC-U5
A human decision is required on how to treat these two candidates before Stage 8.20:
- **Decision Option A (Recommended — Grant Rare-Class Gate 1 Exemption):**
  Approve an explicit protocol exemption allowing scene-level cloud cover up to $20.0\%$ exclusively for verified Stratum 1 acute industrial fires, **contingent upon Gate 2 (AOI SCL $\le 5.0\%$) and Gate 2b (Center 1 km $100\%$ cloud-free) passing upon raster retrieval**. 
  *Rationale:* Rejecting these two drops 2025 verified acute industrial incidents from 8 to 6, further impoverishing the rarest class in DS08.
- **Decision Option B (Enforce Strict $\le 10.0\%$ Gate 1 Rejection):**
  Strictly reject `DS08_EXP_S1_002` and `DS08_EXP_S1_004`. Stratum 1 would drop to 8 primary chips (6 from 2025, 2 from 2024). The deficit of 2 chips would be reallocated to Stratum 2 (Persistent Thermal Sources, increasing it from 35 to 37 chips).

---

## 4. Recomputation of Geodesic Spatial Distances (WGS84 Ellipsoid)

The spatial split feasibility was recomputed using rigorous geodesic calculations on the WGS84 reference ellipsoid ($a = 6,378,137.0\text{ m}, f = 1/298.257223563$) via `pyproj.Geod(ellps='WGS84')`.

### 4.1 Chip Center vs. Chip Footprint Analysis
- **Chip Center Point:** Coordinates $(\text{Lat}, \text{Lon})$.
- **Chip Footprint:** $512 \times 512$ pixels at $10\text{ m}$ GSD = $5,120\text{ m} \times 5,120\text{ m}$ square bounding box.
- Half-width $= 2,560\text{ m}$; Half-diagonal $= \sqrt{2560^2 + 2560^2} = 3,620.4\text{ m}$ ($3.62\text{ km}$).

```
          [ Chip A Footprint ]                      [ Chip B Footprint ]
       +-----------------------+                 +-----------------------+
       |           |           |                 |           |           |
       |     <- 2.56 km ->     |                 |     <- 2.56 km ->     |
       |           * (Center A)|                 |*(Center B)|           |
       |                       |                 |                       |
       +-----------------------+                 +-----------------------+
                   |<------- Edge-to-Edge Distance --------->|
                   |<============ Center-to-Center Distance ================>|
```

### 4.2 Geodesic Recomputation Results

#### A. Center-to-Center Geodesic Distance:
$$\Delta_{\text{center}}^{\text{min}} = \min_{\substack{i, j \in [1, 235] \\ \text{Fold}(i) \neq \text{Fold}(j)}} \text{GeodesicWGS84}\left(\text{Center}_i, \text{Center}_j\right)$$
- **Minimum Geodesic Distance:** **$\mathbf{50.1595\text{ km}}$**
- **Closest Chip Pair:** `DS08_EXP_S2_024` (Fold 5, Lat 19.20432, Lon 96.02615) vs `DS08_EXP_S3_049` (Fold 1, Lat 19.16421, Lon 95.55111).
- **Violations ($\le 50.000\text{ km}$):** **0 pairs (100% COMPLIANT / PASS)**.

#### B. Footprint-to-Footprint (Edge-to-Edge) Geodesic Distance:
$$\Delta_{\text{footprint}}^{\text{min}} = \min_{\substack{i, j \in [1, 235] \\ \text{Fold}(i) \neq \text{Fold}(j)}} \text{GeodesicWGS84}\left(\text{PolyEdge}_i, \text{PolyEdge}_j\right)$$
- **Minimum Footprint Distance:** **$\mathbf{43.8213\text{ km}}$**
- **Closest Chip Pair:** `DS08_EXP_S2_031` (Fold 3) vs `DS08_EXP_S3_055` (Fold 5).
- **Pairs with Edge Separation $\le 50.000\text{ km}$:** **9 pairs** (all have center distances between $50.16\text{ km}$ and $54.80\text{ km}$, but edge distances between $43.82\text{ km}$ and $49.99\text{ km}$).

### 4.3 Methodological Clarification Required: DEC-U6
- In remote sensing machine learning literature, spatial buffers for cross-validation blocking are standardly defined **point-to-point (center-to-center)** because the receptive field and visual footprint ($5.12\text{ km}$) is negligible compared to the $50\text{ km}$ buffer ($5.12\text{ km} \ll 50\text{ km}$, leaving $\ge 43.8\text{ km}$ of buffer space between bounding box edges).
- **Decision Required:** Formal confirmation that the approved 50 km spatial blocking rule is measured **center-to-center** (yielding **PASS** with minimum distance $50.16\text{ km}$ and 0 violations). If footprint edge-to-edge isolation is required, the spatial clustering engine buffer radius must be expanded to $57.24\text{ km}$ ($50\text{ km} + 2 \times 3.62\text{ km}$).

### 4.4 MGRS Tile and Incident Grouping Verification
- **MGRS Tile Splits Across Folds:** **0 (PASS)**.
- **Incident Splits Across Folds:** **0 (PASS)**.

---

## 5. Independent Validation of STAC Product IDs & Timestamps

### 5.1 Validation Against Saved Discovery Evidence (Offline)
All product IDs and timestamps in `ds08_expansion_candidates_v2.json` were cross-checked against authoritative source files on disk:
1. **Stratum 7 (15 Pilot Chips):**
   - Source: `data/reference/ds08/packages/ds08_pilot_v1/manifest.json`.
   - Matching Product IDs: **15 / 15 (100% Match)**.
   - Matching Acquisition Timestamps: **15 / 15 (100% Match)**.
2. **Stratum 1 (10 Acute Industrial Chips):**
   - Source: `scratch/industrial_2025_verified_stac.json` and `scratch/industrial_2024_verified_stac.json`.
   - Matching Product IDs: **10 / 10 (100% Match)**.
   - Matching Acquisition Timestamps: **10 / 10 (100% Match)**.
   - Matching Cloud Cover Percentages: **10 / 10 (100% Match)**.
3. **Strata 2–6 (225 Chips):**
   - Source: `data/interim/causal_features_2025.parquet` and verified baseline coordinate registries.
   - All product IDs conform strictly to ESA SAFE naming regex (`^S2[ABC]_MSIL2A_\d{8}T\d{6}_N\d{4}_R\d{3}_T[0-9A-Z]{5}_\d{8}T\d{6}\.SAFE$`).

### 5.2 Distinction from Live Catalog Verification (Online)
- **Live Catalog Check Status:** **NOT PERFORMED / PENDING STAGE 8.20**.
- In strict adherence to your instructions (*"Do not query CDSE, download imagery, annotate, or train models"*), no live HTTP/REST queries were dispatched to `catalogue.dataspace.copernicus.eu`.
- All checks in this audit represent static, offline validation against stored discovery metadata.

---

## 6. Industrial Incident Distribution & Statutory Evidence Verification

### 6.1 Distribution Across the 10 Primary Candidates
Stratum 1 contains exactly 10 candidate chips originating from 10 distinct physical ground incidents (8 in 2025, 2 in 2024):

| Chip ID | Incident ID | Incident Name & Facility | State | Region | Event Year | S2 Year | $\Delta t$ | Cloud | Corroborating Statutory Source |
|:---|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---|
| `DS08_EXP_S1_001` | `SPCB_2025_MPCB_DOMBIVLI_02` | MIDC Phase II Chemical Plant | Maharashtra | WEST | 2025 | 2025 | $45.65\text{ h}$ | $6.65\%$ | MPCB Formal Closure Direction under Sec 31A |
| `DS08_EXP_S1_002` | `NGT_2025_VIZAG_PHARMA_03` | J.N. Pharma City API Bulk Drug Unit | Andhra Pradesh | CENTRAL | 2025 | 2025 | $19.23\text{ h}$ | $14.74\%$ | NGT Principal Bench Inspection Report |
| `DS08_EXP_S1_003` | `SEBI_2025_PANIPAT_POLYMER_04` | Panipat Textile Synthetic Yarn Warehouse | Haryana | NORTH | 2025 | 2025 | $15.18\text{ h}$ | $0.00\%$ | Statutory Exchange Filing & Fire Tender Log |
| `DS08_EXP_S1_004` | `SPCB_2025_TARAPUR_CHEM_10` | MIDC Tarapur Hazardous Waste Recovery | Maharashtra | WEST | 2025 | 2025 | $3.11\text{ h}$ | $19.32\%$ | MPCB Emergency Closure Direction |
| `DS08_EXP_S1_005` | `NEWS_2025_BADDI_PHARMA_11` | Baddi Pharma Formulation Plant | Himachal Pradesh | NORTH | 2025 | 2025 | $3.68\text{ h}$ | $0.00\%$ | Himachal Fire Service Official Accident Report |
| `DS08_EXP_S1_006` | `SEBI_2025_HALOL_AUTO_PARTS_12` | GIDC Halol Automotive Sheet Metal Unit | Gujarat | WEST | 2025 | 2025 | $40.88\text{ h}$ | $0.65\%$ | BSE/NSE Material Disclosure / Insurance Survey |
| `DS08_EXP_S1_007` | `SEBI_2025_HEUBACH_ROHA_13` | Heubach Colorants Chemical Complex | Maharashtra | WEST | 2025 | 2025 | $14.60\text{ h}$ | $0.00\%$ | SEBI Regulation 30 Material Disclosure |
| `DS08_EXP_S1_008` | `MOD_2025_BHANDARA_ORDNANCE_14` | Bhandara Ordnance Factory / Munitions India | Maharashtra | CENTRAL | 2025 | 2025 | $47.61\text{ h}$ | $0.00\%$ | Ministry of Defence Release / NGT Docket |
| `DS08_EXP_S1_009` | `NDMA_2024_HARDA_FIRECRACKERS` | Bairagarh Fireworks Factory & Explosives | Madhya Pradesh | CENTRAL | 2024 | 2024 | $23.95\text{ h}$ | $0.00\%$ | MP State Disaster Authority / MHA Inquiry |
| `DS08_EXP_S1_010` | `SEBI_2024_DAHEJ_BHARAT_RASAYAN` | Dahej GIDC Phase I Agrochemicals Plant | Gujarat | WEST | 2024 | 2024 | $4.61\text{ h}$ | $0.00\%$ | SEBI Reg 30 Statutory Disclosure / GPCB Order |

### 6.2 Confirmation of Evidence Rigor
- **Zero Weakened Criteria:** No incident was accepted based on social media rumor, generic news scrapers, or unverified single-pixel VIIRS hotspots near factories. Every incident has an identified facility name, verified coordinates, known event start timestamp, and an official regulatory, statutory, or judicial source.
- **Evidence Integrity on 2024 Incidents:**
  - `NDMA_2024_HARDA_FIRECRACKERS` represents one of the largest industrial explosion disasters in India in 2024 (13 fatalities, 100+ injured), extensively documented by the Madhya Pradesh State Disaster Management Authority and Ministry of Home Affairs.
  - `SEBI_2024_DAHEJ_BHARAT_RASAYAN` was formally disclosed by Bharat Rasayan Limited to the National Stock Exchange of India (NSE) and Bombay Stock Exchange (BSE) under SEBI Regulation 30 statutory reporting, corroborated by Gujarat Pollution Control Board emergency orders.
- **Quota Discipline:** Rather than loosening evidence requirements to artificially reach the initial 35-scene target for Stratum 1, the shortfall was transparently reallocated to Stratum 2 (Persistent Non-Biomass Thermal Sources), preserving scientific defensibility.

---

## 7. Action Items & Human Decisions Required

Stage 8.19A pre-acquisition readiness audit is complete. To proceed to Stage 8.20, human confirmation is required on two specific decision items:

### DEC-U5 (Cloud Exemption Decision for 2 Rare Industrial Incidents)
- **Context:** `DS08_EXP_S1_002` (Vizag Pharma, $14.74\%$ scene cloud) and `DS08_EXP_S1_004` (Tarapur Chemical, $19.32\%$ scene cloud) violate the original Stage 8.18 Gate 1 rule ($\le 10.0\%$), but pass the Stage 8.19 query ceiling ($\le 20.0\%$).
- **Select Option:**
  - **Option A (Recommended):** Approve Gate 1 exemption allowing scene cloud up to $20.0\%$ for these two rare acute industrial incidents, contingent on Gate 2 (AOI SCL $\le 5\%$) and Gate 2b (Center 1 km $100\%$ cloud-free) passing upon raster retrieval.
  - **Option B:** Reject both scenes. Stratum 1 decreases to 8 candidates; 2 chips reallocated to Stratum 2.

### DEC-U6 (Spatial Buffer Metric Confirmation)
- **Context:** The minimum inter-fold geodesic distance on the WGS84 ellipsoid is **$50.16\text{ km}$** measured **center-to-center** (0 violations), but **$43.82\text{ km}$** measured **footprint edge-to-edge** (9 pairs within $43.8\text{--}50\text{ km}$).
- **Select Option:**
  - **Option A (Recommended):** Confirm that the approved 50 km spatial buffer rule applies **center-to-center** (standard remote sensing ML practice, certified PASS).
  - **Option B:** Require 50 km edge-to-edge buffer (requires re-running spatial clustering bin-packing with $R = 57.24\text{ km}$).
