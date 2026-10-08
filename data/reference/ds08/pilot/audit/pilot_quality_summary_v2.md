# STAGE 8.8 — DS08 PILOT QUALITY RESOLUTION AUDIT SUMMARY (v2)

**Audit Timestamp:** 2026-09-29T14:14:36.566834+00:00
**Total Rasters Audited:** 21 (20 original + 1 replacement)
**Active Pilot Cohort Size:** 20 chips

## 1. Executive Summary & Active Pilot Readiness

| Metric | Active Cohort (20 chips) | Total Audited (21 chips) | Note |
| :--- | :--- | :--- | :--- |
| **`ANNOTATION_READY`** | **20 (100.0%)** | **20** | 18 original + 1 replacement + 1 resolved PILOT_05 |
| **`REQUIRES_REVIEW`** | **0 (0.0%)** | **0** | All quality issues resolved with diagnostic evidence |
| **`REJECT`** | **0 (0.0%)** | **1** | Original `PILOT_04_NORTH` preserved as `ORIGINAL_REJECTED` |
| **Unique Products** | **20 / 20** | - | 0 duplicate scenes in active pilot |
| **Unique Tiles** | **20 / 20** | - | 0 duplicate MGRS tiles in active pilot |

---

## 2. Resolution of Stage 8.7 Quality Issues

### A. PILOT_04_NORTH (Orbital Swath-Edge Truncation)
- **Original Status:** `ORIGINAL_REJECTED` (51.20% zero-fill pixels). Kept intact in `data/reference/ds08/pilot/chips/` for provenance.
- **Replacement Candidate:** `PILOT_04_NORTH_REPLACEMENT` acquired via CDSE Processing API.
- **Replacement Product ID:** `S2C_MSIL2A_20250319T052711_N0511_R105_T43RGP_20250319T104817.SAFE` (Tile: `T43RGP`).
- **Replacement Acquisition:** 2025-03-19T05:40:58.075Z (Temporal Gap: **1.68h** to FIRMS detection).
- **Replacement Cloud Cover:** **0.23%**.
- **Replacement Zero-Fill:** **0.0%** (0 / 262,144 pixels). Completely untruncated.
- **Replacement Storage:** `data/reference/ds08/pilot/replacement/`.
- **Replacement Decision:** **`ANNOTATION_READY`**.

### B. PILOT_05_CENTRAL (Visible-Band Saturation Diagnostic)
- **Diagnostic Findings:** Localized values >1.0 occur in B02 (1,568 px / 0.60%), B03 (766 px / 0.29%), B04 (514 px / 0.20%). SWIR bands (B11/B12) are completely nominal (max 0.9991 and 0.8221).
- **Spatial Localization:** Clustered in 10 small components centered in southeast quadrant (row 268, col 364), **1086.6 meters** from center.
- **Center Target Clearance:** The FIRMS coordinate at center (256, 256) and a 500m radius around it are **100% cloud-free** with clear-sky ground reflectance (0.03 to 0.14).
- **Ground Usability:** **96.18%** of the chip surface is completely unobstructed.
- **Final Decision:** **`ANNOTATION_READY`** (with documented localized cloud flag in SE corner).

---

## 3. Strengthened Swath / Zero-Fill Quality Gate

To prevent swath-truncated acquisitions in future DS08 batches:
1. **Automatic Rejection:** Any chip with `zero_fill_pct > 1.0%` or a contiguous all-band-zero component > 1.0% is automatically classified as `REJECT_SWATH_TRUNCATION`.
2. **Review Flag:** Any chip with `0.0% < zero_fill_pct <= 1.0%` is flagged for manual review.
3. **Connected Component Analysis:** Evaluates zero-component sizes, bounding boxes, and raster edge proximity.

---

## 4. Scientific Limitation Notice (NDVI & B08)

> [!IMPORTANT]
> NDVI remains unavailable from the current DS08 five-band raster because B08 (Near-Infrared, 842 nm) is not included in the authoritative five-band set (B02, B03, B04, B11, B12). No artificial NDVI or external indices were generated.

---

## 5. Complete Per-Chip Audit Table (v2)

| Chip ID | Role | Region | CRS | Valid % | Zero-Fill % | Cloud | Shadow | Max B04 | Max B12 | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `PILOT_01_NORTH` | `ORIGINAL_VALID` | NORTH | `EPSG:32645` | 100.0% | 0.0% | LOW | LOW | 0.286 | 1.019 | **`ANNOTATION_READY`** |
| `PILOT_02_NORTH` | `ORIGINAL_VALID` | NORTH | `EPSG:32643` | 100.0% | 0.0% | LOW | LOW | 0.494 | 0.580 | **`ANNOTATION_READY`** |
| `PILOT_03_NORTH` | `ORIGINAL_VALID` | NORTH | `EPSG:32645` | 100.0% | 0.0% | MEDIUM | LOW | 0.423 | 1.474 | **`ANNOTATION_READY`** |
| `PILOT_04_NORTH` | `ORIGINAL_REJECTED` | NORTH | `EPSG:32642` | 48.7953% | 51.2047% | LOW | LOW | 0.319 | 0.376 | **`REJECT`** |
| `PILOT_05_CENTRAL` | `ORIGINAL_EVALUATED` | CENTRAL | `EPSG:32644` | 100.0% | 0.0% | MEDIUM | LOW | 1.293 | 0.822 | **`ANNOTATION_READY`** |
| `PILOT_06_CENTRAL` | `ORIGINAL_VALID` | CENTRAL | `EPSG:32644` | 100.0% | 0.0% | LOW | LOW | 0.261 | 1.578 | **`ANNOTATION_READY`** |
| `PILOT_07_CENTRAL` | `ORIGINAL_VALID` | CENTRAL | `EPSG:32644` | 100.0% | 0.0% | LOW | LOW | 0.307 | 0.393 | **`ANNOTATION_READY`** |
| `PILOT_08_CENTRAL` | `ORIGINAL_VALID` | CENTRAL | `EPSG:32644` | 100.0% | 0.0% | LOW | LOW | 0.327 | 0.757 | **`ANNOTATION_READY`** |
| `PILOT_09_SOUTH` | `ORIGINAL_VALID` | SOUTH | `EPSG:32644` | 100.0% | 0.0% | LOW | LOW | 0.362 | 1.410 | **`ANNOTATION_READY`** |
| `PILOT_10_SOUTH` | `ORIGINAL_VALID` | SOUTH | `EPSG:32644` | 100.0% | 0.0% | LOW | LOW | 0.240 | 0.356 | **`ANNOTATION_READY`** |
| `PILOT_11_SOUTH` | `ORIGINAL_VALID` | SOUTH | `EPSG:32644` | 100.0% | 0.0% | MEDIUM | LOW | 0.342 | 0.721 | **`ANNOTATION_READY`** |
| `PILOT_12_SOUTH` | `ORIGINAL_VALID` | SOUTH | `EPSG:32643` | 100.0% | 0.0% | LOW | LOW | 0.331 | 0.631 | **`ANNOTATION_READY`** |
| `PILOT_13_EAST` | `ORIGINAL_VALID` | EAST | `EPSG:32646` | 100.0% | 0.0% | LOW | LOW | 0.247 | 0.448 | **`ANNOTATION_READY`** |
| `PILOT_14_EAST` | `ORIGINAL_VALID` | EAST | `EPSG:32646` | 100.0% | 0.0% | LOW | LOW | 0.252 | 0.374 | **`ANNOTATION_READY`** |
| `PILOT_15_EAST` | `ORIGINAL_VALID` | EAST | `EPSG:32647` | 100.0% | 0.0% | LOW | LOW | 0.281 | 1.490 | **`ANNOTATION_READY`** |
| `PILOT_16_EAST` | `ORIGINAL_VALID` | EAST | `EPSG:32647` | 100.0% | 0.0% | LOW | LOW | 0.252 | 1.488 | **`ANNOTATION_READY`** |
| `PILOT_17_WEST` | `ORIGINAL_VALID` | WEST | `EPSG:32642` | 100.0% | 0.0% | MEDIUM | LOW | 0.369 | 1.408 | **`ANNOTATION_READY`** |
| `PILOT_18_WEST` | `ORIGINAL_VALID` | WEST | `EPSG:32642` | 100.0% | 0.0% | MEDIUM | LOW | 0.389 | 1.397 | **`ANNOTATION_READY`** |
| `PILOT_19_WEST` | `ORIGINAL_VALID` | WEST | `EPSG:32643` | 100.0% | 0.0% | LOW | LOW | 0.300 | 0.453 | **`ANNOTATION_READY`** |
| `PILOT_20_WEST` | `ORIGINAL_VALID` | WEST | `EPSG:32643` | 100.0% | 0.0% | LOW | LOW | 0.288 | 0.319 | **`ANNOTATION_READY`** |
| `PILOT_04_NORTH_REPLACEMENT` | `REPLACEMENT` | NORTH | `EPSG:32643` | 100.0% | 0.0% | LOW | LOW | 0.334 | 0.720 | **`ANNOTATION_READY`** |