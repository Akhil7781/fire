# STAGE 8.7 — DS08 PILOT QUALITY & ANNOTATION READINESS AUDIT SUMMARY

**Audit Timestamp:** 2026-09-29T13:58:53.741649+00:00
**Total Chips Audited:** 20

## 1. Executive Summary & Readiness Breakdown

| Category | Count | Percentage | Description |
| :--- | :--- | :--- | :--- |
| **`ANNOTATION_READY`** | **18** | **90.0%** | 100% valid coverage, nominal reflectance, clear ground visibility, ready for human bounding-box annotation. |
| **`REQUIRES_REVIEW`** | **1** | **5.0%** | Valid raster but contains visible-band saturation (>1.0 in B02/B03/B04) or localized cloud/specular reflection requiring human review. |
| **`REJECT`** | **1** | **5.0%** | Unusable for annotation due to orbital swath-edge truncation (>50% unobserved zero-fill pixels). |

---

## 2. Chips Requiring Action

| Chip ID | Region | Status | Valid Px % | Cloud Concern | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `PILOT_04_NORTH` | NORTH | **`REJECT`** | 48.8% | LOW | Severe swath-edge truncation (51.2% unobserved zero-fill pixels). |
| `PILOT_05_CENTRAL` | CENTRAL | **`REQUIRES_REVIEW`** | 100.0% | MEDIUM | Visible bands (B02/B03/B04) saturated >1.0 (1568 px); localized cloud/specular reflection. |

---

## 3. Reflectance & Values > 1.0 Findings

- **SWIR-Exclusive Exceedance (>1.0):** 8 chips contain pixels exceeding 1.0 strictly in B11 or B12 (max 1.5778 in PILOT_06_CENTRAL), while all visible bands remain completely normal (<0.5). These occur in compact spatial clusters matching high-temperature thermal anomaly radiance emission.
- **Visible-Band Exceedance (>1.0):** Exactly 1 chip (`PILOT_05_CENTRAL`) exhibits values >1.0 in B02 (1.4365), B03 (1.3376), and B04 (1.2931). This corresponds to a localized dense cloud / cloud edge feature.
- **Nominal Reflection (0 pixels >1.0):** 11 chips have zero pixels exceeding 1.0 across all 5 bands.
- **Swath Edge Truncation:** Exactly 1 chip (`PILOT_04_NORTH`) fell on the Sentinel-2 orbital swath boundary, resulting in 51.2% unobserved zero-fill pixels. Classified as **`REJECT`**.

---

## 4. Scientific Limitation Notice

> [!IMPORTANT]
> The current DS08 authoritative chips contain five spectral bands: B02, B03, B04, B11, B12. Band B08 (Near-Infrared, 842 nm) was not included in the original DS08 specification. Consequently, standard NDVI ((B08 - B04)/(B08 + B04)) cannot be calculated from the current raster. Any future vegetation-index requirement must be addressed in subsequent dataset acquisition designs.

---

## 5. Per-Chip Audit Table

| Chip ID | Region | CRS | Valid % | Cloud | Shadow | Max B04 | Max B12 | B12 >1.0 % | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `PILOT_01_NORTH` | NORTH | `EPSG:32645` | 100.0% | LOW | LOW | 0.286 | 1.019 | 0.00% | **`ANNOTATION_READY`** |
| `PILOT_02_NORTH` | NORTH | `EPSG:32643` | 100.0% | LOW | LOW | 0.494 | 0.580 | 0.00% | **`ANNOTATION_READY`** |
| `PILOT_03_NORTH` | NORTH | `EPSG:32645` | 100.0% | MEDIUM | LOW | 0.423 | 1.474 | 0.02% | **`ANNOTATION_READY`** |
| `PILOT_04_NORTH` | NORTH | `EPSG:32642` | 48.8% | LOW | LOW | 0.319 | 0.376 | 0.00% | **`REJECT`** |
| `PILOT_05_CENTRAL` | CENTRAL | `EPSG:32644` | 100.0% | MEDIUM | LOW | 1.293 | 0.822 | 0.00% | **`REQUIRES_REVIEW`** |
| `PILOT_06_CENTRAL` | CENTRAL | `EPSG:32644` | 100.0% | LOW | LOW | 0.261 | 1.578 | 0.06% | **`ANNOTATION_READY`** |
| `PILOT_07_CENTRAL` | CENTRAL | `EPSG:32644` | 100.0% | LOW | LOW | 0.307 | 0.393 | 0.00% | **`ANNOTATION_READY`** |
| `PILOT_08_CENTRAL` | CENTRAL | `EPSG:32644` | 100.0% | LOW | LOW | 0.327 | 0.757 | 0.00% | **`ANNOTATION_READY`** |
| `PILOT_09_SOUTH` | SOUTH | `EPSG:32644` | 100.0% | LOW | LOW | 0.362 | 1.410 | 0.01% | **`ANNOTATION_READY`** |
| `PILOT_10_SOUTH` | SOUTH | `EPSG:32644` | 100.0% | LOW | LOW | 0.240 | 0.356 | 0.00% | **`ANNOTATION_READY`** |
| `PILOT_11_SOUTH` | SOUTH | `EPSG:32644` | 100.0% | MEDIUM | LOW | 0.342 | 0.721 | 0.00% | **`ANNOTATION_READY`** |
| `PILOT_12_SOUTH` | SOUTH | `EPSG:32643` | 100.0% | LOW | LOW | 0.331 | 0.631 | 0.00% | **`ANNOTATION_READY`** |
| `PILOT_13_EAST` | EAST | `EPSG:32646` | 100.0% | LOW | LOW | 0.247 | 0.448 | 0.00% | **`ANNOTATION_READY`** |
| `PILOT_14_EAST` | EAST | `EPSG:32646` | 100.0% | LOW | LOW | 0.252 | 0.374 | 0.00% | **`ANNOTATION_READY`** |
| `PILOT_15_EAST` | EAST | `EPSG:32647` | 100.0% | LOW | LOW | 0.281 | 1.490 | 0.02% | **`ANNOTATION_READY`** |
| `PILOT_16_EAST` | EAST | `EPSG:32647` | 100.0% | LOW | LOW | 0.252 | 1.488 | 0.08% | **`ANNOTATION_READY`** |
| `PILOT_17_WEST` | WEST | `EPSG:32642` | 100.0% | MEDIUM | LOW | 0.369 | 1.408 | 0.01% | **`ANNOTATION_READY`** |
| `PILOT_18_WEST` | WEST | `EPSG:32642` | 100.0% | MEDIUM | LOW | 0.389 | 1.397 | 0.05% | **`ANNOTATION_READY`** |
| `PILOT_19_WEST` | WEST | `EPSG:32643` | 100.0% | LOW | LOW | 0.300 | 0.453 | 0.00% | **`ANNOTATION_READY`** |
| `PILOT_20_WEST` | WEST | `EPSG:32643` | 100.0% | LOW | LOW | 0.288 | 0.319 | 0.00% | **`ANNOTATION_READY`** |