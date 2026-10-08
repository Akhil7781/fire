# Stage 8.19B — Comprehensive Project Decision Log

## Document Metadata
- **Stage:** Stage 8.19B
- **Date:** 2026-10-02
- **Scope:** Complete lineage of user decisions, methodological resolutions, and active decision gates for DS08 expansion.

---

## 1. Resolved Historical Decisions (Stages 8.18A – 8.19A)

### DEC-U1: Expansion to Verified 2024 Industrial Disasters
- **Original Proposal:** Restrict Stratum 1 strictly to 2025 calendar year events.
- **Empirical Trigger:** Nationwide STAC query across 14 verified 2025 industrial disasters produced only 13 viable Sentinel-2 scenes across 8 unique incidents ($< 20$ viable scenes threshold).
- **Approved Decision:** Approved expanding candidate discovery to verified 2024 industrial fire disasters without weakening verification criteria. Event year and Sentinel-2 acquisition year must be tracked as separate fields.
- **Implementation Status:** Verified and active. Manifest v3 incorporates 8 incidents from 2025 and 2 incidents from 2024 (`NDMA_2024_HARDA_FIRECRACKERS` and `SEBI_2024_DAHEJ_BHARAT_RASAYAN`).

### DEC-U2: Double-Blind Human Annotation Labor Allocation
- **Original Proposal:** Single-pass annotation with spot-check audits.
- **Approved Decision:** Internal double-blind independent annotation using the Stage 8.16 correction interface, followed by consensus adjudication.
- **Implementation Status:** Schema decoupled; expansion records initialized as `UNLABELED_CANDIDATE` with `human_confirmed_label = null`.

### DEC-U3: STAC Rate Limiting and Backoff
- **Approved Decision:** Batches of queries with minimum 2.0-second delay; exponential backoff on HTTP 429/503.
- **Implementation Status:** Enforced across all STAC harvesting scripts.

### DEC-U4: Read-Only Candidate Discovery Authorization
- **Approved Decision:** Stage 8.19 and 8.19A authorized strictly for candidate discovery and manifest building. Zero raster downloads, zero synthetic labels, zero model training.
- **Implementation Status:** 100% complied with across all audits.

---

## 2. Decisions Resolved in Stage 8.19B

### DEC-U5: Record-Specific Scene-Cloud Exception
- **Original Rule:** Gate 1 scene-level cloud cover $\le 10.0\%$ (Stage 8.18 Section 4).
- **Problem:** `DS08_EXP_S1_002` (Vizag Pharma, $14.74\%$) and `DS08_EXP_S1_004` (Tarapur Chemical, $19.32\%$) exceed $10.0\%$ scene cloud cover, but fall within the $\le 20.0\%$ discovery filter.
- **Resolved Decision:** Formally approve a **record-specific conditional exception** strictly limited to these two candidate records.
- **Mandatory SCL Conditions (Must Pass in Stage 8.20):**
  1. AOI-level cloud and cloud shadow fraction $\le 5.0\%$ over the $5.12\text{ km} \times 5.12\text{ km}$ footprint.
  2. Central $1.0\text{ km} \times 1.0\text{ km}$ target area must be $100\%$ cloud-free ($0.0\%$ cloud/shadow).
- **Shortfall Policy:** If either candidate fails either condition, it is rejected immediately. No automatic replacement is permitted; shortfalls must be recorded and require a documented decision before replacement.
- **General Threshold:** The 10.0% scene cloud threshold remains unchanged for all other 248 records.
- **Implementation Status:** Active in Manifest v3 metadata envelope.

### DEC-U6: Footprint-Aware 50 km Spatial Separation
- **Original Rule:** Center-to-center 50 km spatial buffer (Stage 8.18A).
- **Problem:** In Stage 8.19A, 9 cross-fold chip pairs had footprint edge-to-edge separation $< 50.0\text{ km}$ (minimum edge distance: $43.82\text{ km}$) due to the $3.62\text{ km}$ half-diagonal footprint radius.
- **Resolved Decision:** Enforce a **footprint-aware 50 km separation rule** on physical bounding box edges on the WGS84 reference ellipsoid via `pyproj.Geod`.
- **Implementation Status:** Re-clustered in Manifest v3:
  - Minimum edge-to-edge distance: **$50.0079\text{ km}$** (0 violations $\le 50.0\text{ km}$).
  - Minimum center-to-center distance: **$55.5971\text{ km}$**.
  - All 5 folds maintain **exactly 47 expansion chips** ($47 \times 5 = 235$).
  - 15 pilot chips remain strictly outside the expansion folds in Stratum 7 (`BENCHMARK_HELD_OUT`).
  - MGRS tile splits: **0**.
  - Physical incident splits: **0**.

---

## 3. Active Decisions Awaiting Project Owner Confirmation

### DEC-U7: Authorization of Stage 8.20 Controlled Acquisition Pilot
- **Scope:** Authorize the execution of the 8-chip controlled acquisition pilot specified in [`STAGE8_20_PILOT_ACQUISITION_PLAN.md`](file:///d:/DATA%20PREPROCESSING/docs/stage8_19b/STAGE8_20_PILOT_ACQUISITION_PLAN.md) using:
  ```bash
  python scripts/stage8_20_pilot_acquisition.py --confirm-acquisition
  ```
- **Prerequisites Satisfied:**
  - Manifest v3 locked and validated.
  - SCL cloud-screening procedure specified.
  - 20m band bilinear resampling specified.
  - Credential security verified (loaded from `.env`).
- **Owner Action Required:** Explicitly approve the 8-chip batch and authorize running the pilot acquisition script.
