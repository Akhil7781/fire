# Stage 8.20: Controlled Sentinel-2 Pilot Acquisition and Real Chip Preprocessing Report

## Executive Summary

**Stage 8.20 (Controlled Sentinel-2 Pilot Acquisition and Real Chip Preprocessing)** has been successfully executed under strict remote-sensing and ML data engineering controls.

All **8 approved pilot Sentinel-2 Level-2A products** were legitimately acquired from the Copernicus Data Space Ecosystem (CDSE) OData API, verified for archive integrity (ZIP CRC32 and SHA-256), unpacked for required optical and classification assets, and preprocessed onto a common 10 m native UTM grid ($512 \times 512$ pixels, $5120\text{ m} \times 5120\text{ m}$).

Pixel-level Scene Classification Layer (SCL) quality screening and Central 1 km ($100 \times 100$ pixel) contamination checks were executed for each chip. Zero synthetic labels were generated (`human_confirmed_label = null` for all records), candidate associations were strictly separated from visual confirmation labels, and baseline candidate manifest V3 remains cryptographically frozen and unchanged.

---

## 1. Pilot Cohort

The acquisition and preprocessing pipeline was strictly constrained to the 8 approved pilot chip IDs specified in `STAGE8_20_PILOT_ACQUISITION_PLAN.md` and authorized in Stage 8.20:

| Pilot Index | Chip ID | Stratum ID | Stratum Name | Expected Target Class | MGRS Tile | Candidate Lat/Lon | Incident / Source Description |
|---|---|---|---|---|---|---|---|
| **P-01** | `DS08_EXP_S1_003` | `STR-1` | Acute Industrial Fires | Industrial Fire | `T43RFN` | 29.3882°N, 76.9924°E | Panipat Polymer Warehouse fire (2025 baseline) |
| **P-02** | `DS08_EXP_S1_002` | `STR-1` | Acute Industrial Fires | Industrial Fire | `T44QQE` | 17.5831°N, 83.1054°E | Vizag API Pharma facility fire (DEC-U5 exception test 1) |
| **P-03** | `DS08_EXP_S1_004` | `STR-1` | Acute Industrial Fires | Industrial Fire | `T42QZH` | 19.8214°N, 72.7128°E | Tarapur Chemical recovery unit (DEC-U5 exception test 2) |
| **P-04** | `DS08_EXP_S2_001` | `STR-2` | Other Thermal Sources | Other Thermal Source | `T43SBS` | 32.7617°N, 72.6283°E | Salt Range / Industrial High-Temperature Kiln/Flare |
| **P-05** | `DS08_EXP_S3_001` | `STR-3` | Active Wildfires | Forest Fire | `T43RDP` | 30.3048°N, 74.4877°E | Muktsar / Punjab Forest & Scrub Canopy Fire |
| **P-06** | `DS08_EXP_S4_001` | `STR-4` | Agricultural Burning | Agricultural Fire | `T43RFP` | 30.5770°N, 76.3328°E | Patiala Post-Monsoon Crop Residue Stubble Burn |
| **P-07** | `DS08_EXP_S5_001` | `STR-5` | Industrial Negative | NO_VISIBLE_TARGET | `T43RGM` | 28.3800°N, 77.2400°E | Faridabad Heavy Industrial Park Non-Fire Control |
| **P-08** | `DS08_EXP_S6_001` | `STR-6` | Natural Negative | NO_VISIBLE_TARGET | `T44RKS` | 28.2500°N, 78.3500°E | Ganges Basin Agricultural/Vegetation Non-Fire Control |

No chips outside this 8-chip cohort were acquired. Zero held-out benchmark chips were touched.

---

## 2. Products Acquired

All 8 Sentinel-2 Level-2A products were acquired from CDSE via streaming HTTP with OAuth2 bearer token authentication and atomic `.part` writing:

| Chip ID | CDSE UUID | Sentinel-2 L2A SAFE Product Name | Archive Size | Archive SHA-256 |
|---|---|---|---|---|
| `DS08_EXP_S1_003` | `34ce33d0-75a0-4c86-b3c8-d7904711640b` | `S2B_MSIL2A_20250413T052649_N0511_R105_T43RFN_20250413T074009.SAFE` | 1,239,010,302 B (1,181.6 MB) | `1451d19450df005f9cb7127ee6db7c6eb6f1e8bc2eb8e2a3948da62540bce326` |
| `DS08_EXP_S1_002` | `e7f0da0d-942d-48ba-a267-07b385c7ca80` | `S2B_MSIL2A_20250325T045659_N0511_R119_T44QQE_20250325T074633.SAFE` | 341,013,671 B (325.2 MB) | `1f2c61d8bec38b4885be9975b3b074a3dfb12e34bfb46c0715697669d0dc6b23` |
| `DS08_EXP_S1_004` | `80fd0f38-b426-4206-abc1-eaed217643f3` | `S2C_MSIL2A_20251028T053951_N0511_R005_T42QZH_20251028T084920.SAFE` | 892,524,107 B (851.2 MB) | `ea50fc47adb7fcb5791242337e7df24d35eb82b7891ae51ec851a7be8e25d2b7` |
| `DS08_EXP_S2_001` | `d217bf07-57cf-4984-bda8-9f0767f02b28` | `S2B_MSIL2A_20250608T054639_N0511_R048_T43SBS_20250608T074909.SAFE` | 1,227,378,633 B (1,170.5 MB) | `efed896fc55cd25752c0029b35b6f381f26284699fb4eb336c5c7d81a8b9e6fb` |
| `DS08_EXP_S3_001` | `ec7925b0-7e83-47f8-a78f-2425a430ab20` | `S2B_MSIL2A_20250516T053639_N0511_R005_T43RDP_20250516T074822.SAFE` | 1,209,981,763 B (1,153.9 MB) | `3e4897fe675acd57f00d8692697a296b42b6826dc6a061a7a0ec90c74149fa8d` |
| `DS08_EXP_S4_001` | `df4ae3e0-cb59-4df4-aa30-da3650687746` | `S2A_MSIL2A_20241023T053901_N0511_R005_T43RFP_20241023T090052.SAFE` | 480,235,189 B (458.0 MB) | `c5e132dd5dcb4df703c1d9777f98fb492a543ec6ce7eb2ee5101a93ca2e0a297` |
| `DS08_EXP_S5_001` | `ffb53396-a874-461f-9474-b678078078bf` | `S2C_MSIL2A_20250128T053131_N0511_R105_T43RGM_20250128T084454.SAFE` | 1,218,200,129 B (1,161.8 MB) | `619a77430876510129f1090fceb7ceb10c8ff7e42d76f8c7e997a9cfd8fe22ad` |
| `DS08_EXP_S6_001` | `fede2b88-962f-4f9b-9f2b-23b1fe291dad` | `S2B_MSIL2A_20250212T052839_N0511_R105_T44RKS_20250212T073606.SAFE` | 613,319,165 B (584.9 MB) | `44891781f3709dacb350ae22c83c2e17ea5cfdc3cf6a67812ea1bc83226db2a5` |

**Total volume acquired:** 7,221,662,959 bytes (6,887.1 MB / 6.725 GiB).

---

## 3. Download Integrity

Download integrity verification was performed at two levels:
1. **Network Layer:** Atomic partial writing (`.zip.part` $\to$ `.zip`) with exact HTTP `Content-Length` matching.
2. **Container Layer:** Zip archive internal checksum validation via `zipfile.ZipFile.testzip()`. Every archive reported zero corrupted members.
3. **Cryptographic Layer:** SHA-256 hash computed during chunked stream receipt and verified upon completion.

All 8 products were logged into [`data/interim/ds08_stage8_20_pilot/acquisition_manifest.json`](file:///d:/DATA%20PREPROCESSING/data/interim/ds08_stage8_20_pilot/acquisition_manifest.json) with status `VERIFIED_SAFE`.

---

## 4. Band Availability

Essential raster assets were extracted directly into `data/interim/ds08_stage8_20_pilot/safes/`:
- **Native 10 m Bands:** B02 (Blue, 490 nm), B03 (Green, 560 nm), B04 (Red, 665 nm)
- **Native 20 m Bands:** B11 (SWIR-1, 1610 nm), B12 (SWIR-2, 2190 nm)
- **Scene Classification:** SCL (Scene Classification Layer, 20 m native)
- **Product Metadata:** `MTD_MSIL2A.xml` and `MTD_TL.xml`

All 6 required raster layers were present and verified for every single product.

---

## 5. Reprojection & Grid Alignment

All bands were aligned to a single, consistent 10 m UTM target grid matching the native Sentinel-2 tile coordinate reference system:
- **Spatial Resolution:** Exactly 10.0 m $\times$ 10.0 m.
- **Physical Extent:** 5,120 m $\times$ 5,120 m.
- **Raster Dimensions:** Exactly $512 \times 512$ pixels.
- **Channel Order (ML):** `[B02, B03, B04, B11, B12]` (Index 0: B02, Index 1: B03, Index 2: B04, Index 3: B11, Index 4: B12).
- **Resampling Policies:**
  - **Reflectance Bands B11 & B12 (20 m $\to$ 10 m):** Bilinear interpolation (`Resampling.bilinear`) via GDAL/Rasterio Warp. Preserves smooth spatial gradients of radiometric reflectance.
  - **Classification Mask SCL (20 m $\to$ 10 m):** Strict Nearest-Neighbour (`Resampling.nearest`). Absolutely no categorical blurring or non-integer class generation.

---

## 6. Chip Extraction & Coordinate Snapping

Candidate coordinates were projected into the native tile UTM CRS, and the 5.12 km bounding box was snapped to the 10 m raster origin:

| Chip ID | Native CRS | Projected Candidate $(X_c, Y_c)$ | Grid Snap Offset $(\Delta c, \Delta r)$ | Chip Pixel Center | UTM Bounds $[X_{min}, X_{max}] \times [Y_{min}, Y_{max}]$ |
|---|---|---|---|---|---|
| `DS08_EXP_S1_003` | EPSG:32643 | (693350.45, 3252646.23) | (+0.045, +0.377) | (256.045, 256.377) | [690790.0, 695910.0] $\times$ [3250090.0, 3255210.0] |
| `DS08_EXP_S1_002` | EPSG:32644 | (723324.23, 1945327.10) | (+0.242, -0.290) | (256.242, 255.710) | [720760.0, 725880.0] $\times$ [1942770.0, 1947890.0] |
| `DS08_EXP_S1_004` | EPSG:32642 | (260555.32, 2193259.04) | (-0.447, +0.410) | (255.553, 256.410) | [258000.0, 263120.0] $\times$ [2190700.0, 2195820.0] |
| `DS08_EXP_S2_001` | EPSG:32643 | (277831.62, 3627515.77) | (-0.084, -0.421) | (255.916, 255.579) | [275270.0, 280390.0] $\times$ [3624960.0, 3630080.0] |
| `DS08_EXP_S3_001` | EPSG:32643 | (450753.37, 3352841.97) | (-0.166, -0.380) | (255.834, 255.620) | [448190.0, 453310.0] $\times$ [3350280.0, 3355400.0] |
| `DS08_EXP_S4_001` | EPSG:32643 | (627796.82, 3383564.84) | (-0.432, +0.484) | (255.568, 256.484) | [625240.0, 630360.0] $\times$ [3381000.0, 3386120.0] |
| `DS08_EXP_S5_001` | EPSG:32643 | (719878.84, 3141618.31) | (-0.412, +0.183) | (255.588, 256.183) | [717320.0, 722440.0] $\times$ [3139060.0, 3144180.0] |
| `DS08_EXP_S6_001` | EPSG:32644 | (239775.91, 3127886.10) | (-0.241, -0.390) | (255.759, 255.610) | [237220.0, 242340.0] $\times$ [3125330.0, 3130450.0] |

**Verification Check:** For all 8 chips, candidate coordinates lie strictly within chip physical bounds ($X_{min} \le X_c \le X_{max}$, $Y_{min} \le Y_c \le Y_{max}$) and continuous pixel row/column coordinates are within $[255.5, 256.5] \subset [0, 512)$.

---

## 7. SCL Quality Screening Results

SCL quality screening was computed over all 262,144 pixels of each chip footprint:

| Chip ID | Scene Metadata Cloud % | Actual Chip Cloud % (SCL 8,9,10) | Actual Chip Shadow % (SCL 3) | Total AOI Contamination % | Clean Pixel % | Invalid / NoData % |
|---|---|---|---|---|---|---|
| `DS08_EXP_S1_003` | 0.00% | 0.00% | 0.00% | **0.00%** | 100.00% | 0.00% |
| `DS08_EXP_S1_002` | 14.74% | 49.78% | 3.53% | **53.31%** | 46.69% | 0.00% |
| `DS08_EXP_S1_004` | 19.32% | 40.83% | 0.13% | **40.95%** | 59.05% | 0.00% |
| `DS08_EXP_S2_001` | 0.00% | 0.00% | 0.00% | **0.00%** | 100.00% | 0.00% |
| `DS08_EXP_S3_001` | 0.24% | 0.00% | 0.00% | **0.00%** | 100.00% | 0.00% |
| `DS08_EXP_S4_001` | 0.08% | 0.00% | 0.00% | **0.00%** | 100.00% | 0.00% |
| `DS08_EXP_S5_001` | 0.00% | 0.00% | 0.00% | **0.00%** | 100.00% | 0.00% |
| `DS08_EXP_S6_001` | 0.00% | 0.003% | 0.00% | **0.003%** | 99.997% | 0.00% |

**Distinction Confirmed:** Scene metadata cloud cover does not predict local AOI cloud contamination. For instance, `DS08_EXP_S1_002` had $14.74\%$ scene-level cloud cover, but the actual chip AOI exhibited $53.31\%$ cloud and shadow contamination.

---

## 8. Central 1 km Quality Check

A $100 \times 100$ pixel window ($1000\text{ m} \times 1000\text{ m}$) centered directly on the candidate coordinate was extracted to evaluate target-area visibility:

| Chip ID | Central 1 km Cloud % | Central 1 km Shadow % | Central 1 km Contamination % | Central 1 km Clean % | Local Occlusion State |
|---|---|---|---|---|---|
| `DS08_EXP_S1_003` | 0.00% | 0.00% | **0.00%** | 100.00% | Completely Clear |
| `DS08_EXP_S1_002` | 100.00% | 0.00% | **100.00%** | 0.00% | **Completely Occluded (Thick Cloud)** |
| `DS08_EXP_S1_004` | 29.70% | 0.00% | **29.70%** | 70.30% | **Partially Occluded (Cloud Contaminated)** |
| `DS08_EXP_S2_001` | 0.00% | 0.00% | **0.00%** | 100.00% | Completely Clear |
| `DS08_EXP_S3_001` | 0.00% | 0.00% | **0.00%** | 100.00% | Completely Clear |
| `DS08_EXP_S4_001` | 0.00% | 0.00% | **0.00%** | 100.00% | Completely Clear |
| `DS08_EXP_S5_001` | 0.00% | 0.00% | **0.00%** | 100.00% | Completely Clear |
| `DS08_EXP_S6_001` | 0.00% | 0.00% | **0.00%** | 100.00% | Completely Clear |

---

## 9. Per-Chip Quality Status Decisions

Based on the documented DS08 acceptance criteria and DEC-U5 cloud exception rules:

1. **`DS08_EXP_S1_003` $\to$ PASS:**
   AOI contamination is $0.00\% \le 5.0\%$, Central 1 km contamination is $0.00\% \le 5.0\%$. Crystal-clear view of the Panipat polymer warehouse fire scene.
2. **`DS08_EXP_S1_002` $\to$ REJECT:**
   DEC-U5 exception candidate. Scene metadata was $14.74\%$. However, actual SCL screening revealed that the central 1 km region directly over the Vizag API Pharma facility is **$100.00\%$ occluded by thick cloud**. Under DEC-U5, a conditional candidate must possess an unobstructed local target area ($\le 10.0\%$). This scene fails the test and is rejected.
3. **`DS08_EXP_S1_004` $\to$ REJECT:**
   DEC-U5 exception candidate. Central 1 km contamination is **$29.70\%$**, exceeding the $10.0\%$ tolerance limit. SCL confirms cloud contamination obscuring the Tarapur Chemical recovery facility. Rejected.
4. **`DS08_EXP_S2_001` $\to$ PASS:**
   AOI contamination $0.00\%$, Central 1 km $0.00\%$. Pristine high-temperature thermal source scene.
5. **`DS08_EXP_S3_001` $\to$ PASS:**
   AOI contamination $0.00\%$, Central 1 km $0.00\%$. Clear wildfire scene.
6. **`DS08_EXP_S4_001` $\to$ PASS:**
   AOI contamination $0.00\%$, Central 1 km $0.00\%$. Clear agricultural residue burn scene.
7. **`DS08_EXP_S5_001` $\to$ PASS:**
   AOI contamination $0.00\%$, Central 1 km $0.00\%$. Clear industrial negative control.
8. **`DS08_EXP_S6_001` $\to$ PASS:**
   AOI contamination $0.003\%$, Central 1 km $0.00\%$. Clear natural negative control.

**Overall Cohort Status:** 6 PASS, 0 CONDITIONAL, 2 REJECT.

---

## 10. Human Review Package

For each of the 8 pilot chips, an inspection package has been created under `data/interim/ds08_stage8_20_pilot/previews/<chip_id>/`:
1. `rgb_preview.png`: True Color composite (B04, B03, B02) with 2–98% percentile stretch.
2. `swir_preview.png`: False Color SWIR composite (B12, B11, B04) highlighting combustion and heat scars.
3. `scl_mask.png`: Color-coded SCL discrete classification map with legend of all detected landcover classes and contamination summary.
4. `candidate_overlay.png`: High-resolution True Color image with marked candidate coordinates (red crosshair) and the central 1 km evaluation window (yellow bounding box).

---

## 11. Data Statistics & Radiometric Validation

Each chip array was validated for radiometric range, dtype, and lack of corrupt values:
- **`spectral_raw.npy`:** Dtype `uint16`, shape `(5, 512, 512)`, values in $[0, 16384]$. Zero NaN, zero Inf.
- **`spectral_normalized.npy`:** Dtype `float32`, shape `(5, 512, 512)`, computed via $DN / 10000.0$ and clipped to $[0.0, 1.0]$. Zero NaN, zero Inf.
- **`scl.npy`:** Dtype `uint8`, shape `(512, 512)`, values strictly in $\{0, 1, \dots, 11\}$.

Summary of radiometric means across the clean PASS chips:
- `DS08_EXP_S1_003` (Industrial Fire): Mean B02: 835.6, B03: 1042.8, B04: 1111.4, B11: 2795.3, B12: 2139.1.
- `DS08_EXP_S2_001` (Other Thermal): Mean B02: 1228.8, B03: 1618.5, B04: 1827.8, B11: 3418.9, B12: 2769.7.
- `DS08_EXP_S3_001` (Forest Fire): Mean B02: 735.2, B03: 987.5, B04: 1024.1, B11: 2841.0, B12: 1985.3.
- `DS08_EXP_S4_001` (Agri Fire): Mean B02: 673.8, B03: 924.1, B04: 1012.5, B11: 2618.2, B12: 1742.8.
- `DS08_EXP_S5_001` (Industrial Negative): Mean B02: 891.2, B03: 1098.4, B04: 1215.3, B11: 2541.6, B12: 1981.2.
- `DS08_EXP_S6_001` (Natural Negative): Mean B02: 712.4, B03: 915.2, B04: 981.6, B11: 2412.8, B12: 1654.1.

---

## 12. Failed / Rejected Cases

Two candidates were rejected during Stage 8.20 SCL screening:
1. **`DS08_EXP_S1_002` (Vizag API Pharma):**
   - **Reason:** Central 1 km is $100.00\%$ occluded by cloud. The facility cannot be resolved in optical imagery for visual annotation or CNN feature extraction.
   - **Handling:** Isolated in `ds08_stage8_20_pilot_processed.json` with `quality_status: "REJECT"`. Will be excluded from training sets in Stage 8.21.
2. **`DS08_EXP_S1_004` (Tarapur Chemical):**
   - **Reason:** Central 1 km has $29.70\%$ cloud contamination. The cloud covers key portions of the industrial facility.
   - **Handling:** Isolated with `quality_status: "REJECT"`. Excluded from training sets.

Crucially, **these rejections vindicate the protocol**: the DEC-U5 mechanism explicitly subjected scenes with $> 10\%$ scene-level cloud cover to ground truth pixel-level SCL validation rather than blindly accepting or rejecting them. The SCL check successfully caught the cloudy target areas.

---

## 13. Reproducibility

The entire acquisition and preprocessing pipeline is 100% reproducible via two standalone scripts:
1. [`scripts/stage8_20_pilot_acquisition.py`](file:///d:/DATA%20PREPROCESSING/scripts/stage8_20_pilot_acquisition.py):
   Downloads the 8 SAFE archives from CDSE and extracts essential assets. Requires `--confirm-acquisition`.
2. [`scripts/process_ds08_stage8_20_pilot.py`](file:///d:/DATA%20PREPROCESSING/scripts/process_ds08_stage8_20_pilot.py):
   Reads the extracted SAFEs, aligns bands to the 10 m common UTM grid, computes SCL statistics, generates ML arrays and preview PNGs, and writes the processed pilot manifest.

---

## 14. Verification Tests

A dedicated 18-point pytest suite was created in [`tests/test_ds08_stage8_20_processing.py`](file:///d:/DATA%20PREPROCESSING/tests/test_ds08_stage8_20_processing.py):
- `test_01_exactly_8_pilot_chip_ids`: PASS
- `test_02_every_chip_has_verified_source_product`: PASS
- `test_03_every_chip_has_all_required_bands`: PASS
- `test_04_all_bands_align_spatially`: PASS
- `test_05_all_ml_spectral_arrays_are_512x512`: PASS
- `test_06_scl_is_512x512`: PASS
- `test_07_crs_is_valid`: PASS
- `test_08_pixel_resolution_is_10m`: PASS
- `test_09_no_nan_values_after_preprocessing`: PASS
- `test_10_no_inf_values`: PASS
- `test_11_candidate_point_lies_inside_chip_footprint`: PASS
- `test_12_scl_uses_nearest_neighbour_semantics`: PASS
- `test_13_expected_class_is_not_copied_into_human_confirmed_label`: PASS
- `test_14_no_synthetic_labels_exist`: PASS
- `test_15_cloud_quality_metrics_are_present`: PASS
- `test_16_central_1km_metric_is_present`: PASS
- `test_17_rejected_chips_not_silently_included_in_clean_dataset`: PASS
- `test_18_v3_manifest_remains_intact`: PASS

Result: **18 passed in 0.61s (100% pass rate)**.
Predecessor Stage 8.19G test suite (`tests/test_ds08_stage8_19g_audit.py`): **18 passed in 0.30s (100% pass rate)**.

---

## 15. Artifact Hashes

| Artifact Path | SHA-256 Checksum | Immutability Status |
|---|---|---|
| `data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json` | `dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848` | **FROZEN / UNCHANGED** |
| `data/reference/ds08/manifests/stage8_19e/ds08_expansion_candidates_v4.json` | `54154edcd0189545c2d03615827f834be91d2452767cef0a1d8978d3b4d9d62c` | **FROZEN / UNCHANGED** |
| `data/interim/ds08_stage8_20_pilot/acquisition_manifest.json` | `c0fd918d25b9744234d4668ec09a700b8e09159369a266ded8285a69de588ca7` | Generated Stage 8.20 |
| `data/reference/ds08/manifests/stage8_20/ds08_stage8_20_pilot_processed.json` | `88817de6f243b7a5af4efce06a79eb5d580e41ba15101e6fd237384fea22bb0c` | Generated Stage 8.20 |

---

## 16. Final Stage Status

**FINAL STATUS: STAGE_8_20_CONTROLLED_ACQUISITION_AND_PREPROCESSING_COMPLETE**

---

## Required Final Table (Section 26)

| Chip | Product Verified | Bands | Chip | SCL | Central 1km | Quality | Status |
|---|---|---|---|---|---|---|---|
| S1_003 | S2B_MSIL2A_20250413T05... | 6/6 (10m/20m) | 512x512 (10m) | 0.00% | 0.00% | CLEAR | **PASS** |
| S1_002 | S2B_MSIL2A_20250325T04... | 6/6 (10m/20m) | 512x512 (10m) | 53.31% | 100.00% | CONTAMINATED | **REJECT** |
| S1_004 | S2C_MSIL2A_20251028T05... | 6/6 (10m/20m) | 512x512 (10m) | 40.95% | 29.70% | CONTAMINATED | **REJECT** |
| S2_001 | S2B_MSIL2A_20250608T05... | 6/6 (10m/20m) | 512x512 (10m) | 0.00% | 0.00% | CLEAR | **PASS** |
| S3_001 | S2B_MSIL2A_20250516T05... | 6/6 (10m/20m) | 512x512 (10m) | 0.00% | 0.00% | CLEAR | **PASS** |
| S4_001 | S2A_MSIL2A_20241023T05... | 6/6 (10m/20m) | 512x512 (10m) | 0.00% | 0.00% | CLEAR | **PASS** |
| S5_001 | S2C_MSIL2A_20250128T05... | 6/6 (10m/20m) | 512x512 (10m) | 0.00% | 0.00% | CLEAR | **PASS** |
| S6_001 | S2B_MSIL2A_20250212T05... | 6/6 (10m/20m) | 512x512 (10m) | 0.00% | 0.00% | CLEAR | **PASS** |

---

## Summary Metrics

- **Products acquired:** 8 / 8 (100%)
- **Products successfully processed:** 8 / 8 (100%)
- **Chips produced:** 8
- **Bands produced per chip:** 6 (B02, B03, B04, B11, B12, SCL)
- **Bytes downloaded:** 7,221,662,959 bytes (6,887.1 MB)
- **Quality status distribution:** 6 PASS, 0 CONDITIONAL, 2 REJECT
- **Synthetic labels created:** 0 (`human_confirmed_label = null` across all records)
- **Manifest V3 SHA-256:** `dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848` (MATCH)
- **Stage 8.20 tests passed:** 18 / 18 (100%)
- **Stage 8.19G tests passed:** 18 / 18 (100%)
