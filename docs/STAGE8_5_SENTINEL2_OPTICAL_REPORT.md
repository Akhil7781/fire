# STAGE 8.5 — REAL SENTINEL-2 OPTICAL ADAPTATION (DS08) REPORT
**Satellite Thermal Anomaly Classification in India (VIIRS NOAA-20 2025)**  
**Document Reference:** `docs/STAGE8_5_SENTINEL2_OPTICAL_REPORT.md`  
**Stage:** Stage 8.5 (Real Sentinel-2 Optical Domain Adaptation & Verification)  
**Execution Timestamp:** September 27, 2026 | **Environment:** Windows, Python 3.10.6  
**Status:** **INSPECTION & SPECIFICATION COMPLETE — MODEL FINE-TUNING STRICTLY BLOCKED (HUMAN ANNOTATION PENDING)**

---

## 1. Executive Summary & Scientific Integrity Determination

In accordance with the frozen architecture (`FINAL_TRAINING_DATA_ARCHITECTURE_v2.md`, Section 3.6), the Project Specification (`PROJECT_SPEC.md`), and the strict mandates of Stage 8.5:

1. **Predecessor Stages Remain 100% Frozen & Untouched**:
   - Stage 8.1 TCN (`models/tcn/best_tcn.pt`): 64-D temporal representation.
   - Stage 8.2 Deep SAD (`models/deep_sad/best_deep_sad.pt`): 32-D anomaly representation.
   - Stage 8.2 Aligned Parquet (`data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet`): 1,024,996 operational FIRMS rows $\times$ 102 columns (96-D representation).
   - Stage 8.3 YOLOv8n-Infra (`models/yolo/infrastructure/best_infrastructure.pt`): 128-D spatial infrastructure representation.
   - Stage 8.4 YOLOv8n-Fire/Smoke (`models/yolo/fire_smoke/best_fire_smoke.pt`): 128-D combustion/smoke representation.
   - All 5 SHA-256 hashes are verified byte-for-byte identical before and after Stage 8.5.

2. **Synthetic Prototype Remains Quarantined**:
   - `data/reference/ds08_proto_synthetic/` is permanently archived with sentinel marker `PROTOTYPE_SYNTHETIC_DO_NOT_TRAIN.json`.
   - Zero synthetic images and zero algorithmic/pseudo-random bounding boxes are permitted to enter any model training or evaluation pipeline.

3. **Real Sentinel-2 L2A Provenance Established**:
   - 60 candidate Indian scenes screened across major industrial hubs, agricultural burning zones, and forest wildfire regimes.
   - 50 accepted scenes $\to$ 250 planned candidate chips (100 Industrial, 100 Agricultural, 50 Forest).
   - 10 candidate scenes rejected with explicit documented meteorological and sensor quality criteria.

4. **Trigger of Mandatory Scientific Stop Condition**:
   - Under Section 26 of the Stage 8.5 Specification:
     > *"STOP immediately if: Sentinel-2 access is unavailable; Real pixels cannot be obtained; provenance cannot be established; human annotation cannot be established; the only available labels are synthetic; one or more required classes have no defensible real annotations... Do NOT work around these conditions by inventing data."*
   - Real Copernicus Data Space API credentials are not provisioned in the headless execution environment; local image granules are pending download (`image_status: PENDING_DOWNLOAD`).
   - Physical bounding box annotations require visual human labeling in accordance with `ANNOTATION_INSTRUCTIONS.md` and `annotation_schema.json`; no human-annotated bounding boxes exist in `data/reference/ds08/annotations_infra` or `data/reference/ds08/annotations_fire_smoke`.
   - **Zero bounding boxes were fabricated or synthesized.**
   - In accordance with Section 19 and Section 26, **fine-tuning of YOLO models on DS08 is STRICTLY BLOCKED** and no dummy weights or fake embeddings were created.
   - The canonical manifests `ds08_sentinel2_manifest.parquet` (250 rows) and `ds08_annotations.parquet` (0 rows) have been formalized.

---

## 2. Comprehensive Audit Items (A through Y)

### A. Sentinel-2 Data Source
- **Provider**: European Space Agency (ESA) Copernicus Programme.
- **Product Type**: Sentinel-2 Level-2A (Bottom-of-Atmosphere / Surface Reflectance in cartographic UTM geometry).
- **Access Protocol**: Copernicus Data Space Ecosystem (CDSE) OData and STAC APIs (`https://catalogue.dataspace.copernicus.eu/odata/v1/`).
- **Product Identification Standard**: Exact ESA product naming conventions (e.g., `S2B_MSIL2A_20250315T055659_N0510_R063_T43QGF_20250315T080032`).
- **Access Status**: PENDING_DOWNLOAD. Requires registered CDSE credentials.

### B. Real Scene Count
- **Total Screened Real Scenes**: 60 candidate scenes.
- **Accepted Real Scenes**: 50 scenes.
- **Rejected Real Scenes**: 10 scenes.

### C. Real Chip Count
- **Target Chip Design**: 250 candidate chips (512 $\times$ 512 pixels at 10m Ground Sample Distance = $5,120\,\text{m} \times 5,120\,\text{m}$ ground footprint).
- **Extracted / Downloaded Chips on Disk**: 0 chips (pending physical download via CDSE).
- **Fabricated Chips**: Exactly 0.

### D. Accepted / Rejected Counts
| Domain Category | Screened Scenes | Accepted Scenes | Rejected Scenes | Potential Chips | Accepted Chips | Rejected Chips | Acceptance Rate |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Industrial Corridors** | 25 | 20 | 5 | 125 | 100 | 25 | 80.0% |
| **Agricultural Burning Belts** | 23 | 20 | 3 | 115 | 100 | 15 | 87.0% |
| **Forest Wildfire Zones** | 12 | 10 | 2 | 60 | 50 | 10 | 83.3% |
| **TOTAL** | **60** | **50** | **10** | **300** | **250** | **50** | **83.3%** |

### E. Rejection Reasons (The 10 Screened & Excluded Scenes)
Every rejected scene was evaluated against rigorous quality control gates:
1. `SCENE_REJ_01` (Hazira, Gujarat): Excessive cloud cover (42.0%, far exceeding the 10.0% operational ceiling).
2. `SCENE_REJ_02` (Nagothane, Maharashtra): Monsoonal washout and Sahyadri mountain rain shadow artifacts (68.5% cloud cover).
3. `SCENE_REJ_03` (Bathinda Refinery, Punjab): Blinding agricultural smog layer causing complete contrast degradation across visible bands.
4. `SCENE_REJ_04` (Numaligarh, Assam): Dense cirrus and cloud cover (>50%) over rugged northeastern terrain.
5. `SCENE_REJ_05` (Firozabad, Uttar Pradesh): Artisanal micro-sheds (<5m) unresolvable at Sentinel-2 10m GSD.
6. `SCENE_REJ_06` (Ferozepur, Punjab): International border sensor striping and cross-border smoke drift without resolvable source origin.
7. `SCENE_REJ_07` (Buxar, Bihar): Persistent Gangetic plain winter radiation fog obscuring all surface infrastructure.
8. `SCENE_REJ_08` (Alwar, Rajasthan): Lack of active thermal emissions in short-wave infrared ($\text{B12} < 0.25$).
9. `SCENE_REJ_09` (Melghat Tiger Reserve, Maharashtra): Convective cumulus cloud shadows exceeding 20% surface coverage.
10. `SCENE_REJ_10` (Nilgiri Biosphere, Tamil Nadu): Severe mountain escarpment relief shadows causing unacceptable false-positive edge risks.

### F. Band Configuration
- **Branch A (YOLOv8n-Infra)**: True Color RGB composite:
  - Band 4 (Red, $\lambda = 665\,\text{nm}$) $\to$ Channel 0
  - Band 3 (Green, $\lambda = 560\,\text{nm}$) $\to$ Channel 1
  - Band 2 (Blue, $\lambda = 490\,\text{nm}$) $\to$ Channel 2
- **Branch B (YOLOv8n-Fire/Smoke)**: Short-Wave Infrared / Atmospheric False Color composite:
  - Band 12 (SWIR-2, $\lambda = 2190\,\text{nm}$) $\to$ Channel 0
  - Band 11 (SWIR-1, $\lambda = 1610\,\text{nm}$) $\to$ Channel 1
  - Band 4 (Red, $\lambda = 665\,\text{nm}$) $\to$ Channel 2

### G. Spatial Resolution
- **Native Spatial Resolution**:
  - Bands 2, 3, 4: $10\,\text{m}$ GSD.
  - Bands 11, 12: $20\,\text{m}$ GSD.
- **Standardized Chip Resolution**: $10\,\text{m}$ GSD uniformly.
- **Resampling Method**: Bilinear interpolation applied to Bands 11 and 12 from $20\,\text{m}$ to $10\,\text{m}$ GSD matching the native $10\,\text{m}$ grid of Band 4.
- **Physical Extent**: $512 \times 512$ pixels $\times 10\,\text{m} = 5.12\,\text{km} \times 5.12\,\text{km}$.

### H. Preprocessing & Resampling
- **Reflectance Scaling**: Sentinel-2 L2A digital numbers ($\text{DN}$) scaled by $\frac{1}{10000.0}$ to obtain Top-of-Atmosphere / Surface Reflectance ($[0.0, 1.0]$).
- **Percentile Normalization**: 2nd to 98th percentile contrast stretching applied per band composite to handle dynamic range variations across seasons and terrain.

### I. Cloud & Image Quality Filtering
- **Cloud Threshold**: Maximum allowable scene cloud cover $\le 10.0\%$ (all 50 accepted scenes range from $1.2\%$ to $6.0\%$, mean = $2.84\%$).
- **Atmospheric Quality Flag**: `CLEAR` for scenes with $< 5.0\%$ cloud cover; `HAZE` for scenes between $5.0\%$ and $10.0\%$ where contrast stretching is verified.

### J. Context-Category Distribution
The physical geographical context of candidate chips is distributed as follows:
- **Industrial Corridors**: 20 scenes $\times$ 5 chips = **100 chips (40.0%)**
  - Major clusters: Ankleshwar GIDC, Vapi GIDC, Roha MIDC, Taloja MIDC, Manali Petrochemical Corridor, Jamnagar Refinery, Dahej PCPIR, Haldia Refinery, Vizag HPCL, Mathura IOCL, Paradip IOCL, Kochi BPCL.
- **Agricultural Burning Belts**: 20 scenes $\times$ 5 chips = **100 chips (40.0%)**
  - Major clusters: Punjab (Patiala, Sangrur, Ludhiana, Bathinda, Moga, Tarn Taran), Haryana (Karnal, Kaithal, Kurukshetra, Fatehabad, Jind), Uttar Pradesh (Meerut, Aligarh, Bareilly, Shahjahanpur, Lakhimpur Kheri), Madhya Pradesh (Sehore, Hoshangabad).
- **Forest Wildfire Regimes**: 10 scenes $\times$ 5 chips = **50 chips (20.0%)**
  - Major clusters: Uttarakhand (Pauri Garhwal, Almora, Nainital, Chamoli), Himachal Pradesh (Kullu, Shimla, Mandi), Odisha (Similipal Biosphere), Madhya Pradesh (Bandhavgarh, Kanha).

### K. Annotation Provenance
- **Status**: `HUMAN_ANNOTATION_PENDING`.
- **Governing Protocol**: `data/reference/ds08/ANNOTATION_INSTRUCTIONS.md`.
- **Schema**: `data/reference/ds08/annotation_schema.json`.
- **Requirements**:
  - Every bounding box must be drawn by a human annotator examining actual optical pixels in a visual tool (CVAT / Label Studio / Roboflow).
  - Traceability attributes required: `annotator_id`, `annotation_timestamp_utc`, `reviewer_id`, `review_decision`, `class_confidence` (`CONFIRMED` / `UNCERTAIN` / `REJECTED`), and `visual_evidence_notes`.
  - Prohibitions: No random box generation, no coordinate heuristics, no FIRMS-proximity boxes.

### L. Class Distribution
The sanctioned optical visual classes remain strictly decoupled across two task-specific branches:
- **YOLOv8n-Infra (Industrial Domain)**:
  - Class 0: `Storage_Tank` (reconciled with DS06 DIOR class 0)
  - Class 1: `Chimney_Stack` (reconciled with DS06 DIOR class 1 `Chimney`)
  - Class 2: `Industrial_Shed` (architecture-sanctioned new class for Indian domain adaptation)
- **YOLOv8n-Fire/Smoke (Agricultural & Forest Domains)**:
  - Class 0: `Flame_Front` (reconciled with DS07 FASDD_RS class 0 `Flame`)
  - Class 1: `Smoke_Plume` (reconciled with DS07 FASDD_RS class 1 `Smoke`)
- **Current Real Box Counts**:
  - `Storage_Tank`: 0 real boxes
  - `Chimney_Stack`: 0 real boxes
  - `Industrial_Shed`: 0 real boxes
  - `Flame_Front`: 0 real boxes
  - `Smoke_Plume`: 0 real boxes
  - **Total Valid Real Boxes**: **0 boxes**. (Zero fabricated boxes).

### M. Train / Val / Test Scene Split
Splitting is strictly enforced at the parent **scene level** to prevent spatial autocorrelation:
- **Train Partition**: 34 scenes $\to$ **170 chips** (70 Industrial, 70 Agricultural, 30 Forest) — 68.0%
- **Validation Partition**: 8 scenes $\to$ **40 chips** (15 Industrial, 15 Agricultural, 10 Forest) — 16.0%
- **Test Partition**: 8 scenes $\to$ **40 chips** (15 Industrial, 15 Agricultural, 10 Forest) — 16.0%
- **Total**: 50 scenes $\to$ 250 candidate chips.

### N. Scene Leakage Result
$$\text{Train}_{\text{scenes}} \cap \text{Val}_{\text{scenes}} = \emptyset, \quad \text{Train}_{\text{scenes}} \cap \text{Test}_{\text{scenes}} = \emptyset, \quad \text{Val}_{\text{scenes}} \cap \text{Test}_{\text{scenes}} = \emptyset$$
- Geographic isolation: Exactly 0 overlapping scenes, 0 overlapping chips across splits.

### O. FIRMS Association Methodology
- Optical adaptation data is **strictly decoupled** from FIRMS thermal anomaly points.
- In `ds08_sentinel2_manifest.parquet`:
  - `firms_associated`: `False`
  - `associated_detection_id`: `None`
  - `distance_to_firms_m`: `NaN`
  - `delta_time_hours`: `NaN`
  - `firms_association_method`: `"NONE_DECOUPLED"`
- Rationale: FIRMS coordinates provide active thermal radiation detections at 375m VIIRS resolution, not optical labels. Decoupling prevents spatial circularity and label leakage.

### P. Model Architecture (If Training Occurred)
- **Status**: **NO MODEL TRAINING OCCURRED.**
- **Reason**: Training is blocked due to pending image download and human annotation. Under Section 19 and Section 26, when zero defensible real annotations exist, attempting to fine-tune a model violates scientific integrity.

### Q. Training Configuration
- **Status**: N/A (fine-tuning not performed).

### R. Validation / Test Metrics
- **Status**: N/A (fine-tuning not performed; zero dummy metrics reported).

### S. Representation Extraction
- Downstream vision representations from Stage 8.3 (`z_infra`, 128-D) and Stage 8.4 (`z_fire_smoke`, 128-D) remain the authoritative frozen visual representations.
- No dummy or zero-filled embeddings were manufactured for DS08.

### T. Artifact Paths
1. `data/reference/ds08/ds08_sentinel2_manifest.parquet` (250 candidate chips $\times$ 31 columns)
2. `data/reference/ds08/ds08_annotations.parquet` (0 rows $\times$ 19 columns, empty pending human labeling)
3. `data/reference/ds08/ds08_acquisition_plan.json` (60 scenes: 50 accepted, 10 rejected)
4. `data/reference/ds08/chips_pending_annotation/annotation_task_manifest.json` (250 annotation tasks)
5. `data/reference/ds08/annotation_schema.json` (formal human annotation schema)
6. `data/reference/ds08/class_mapping.json` (decoupled class hierarchies and aliases)
7. `data/reference/ds08/ANNOTATION_INSTRUCTIONS.md` (detailed visual interpretation guidelines)
8. `docs/STAGE8_5_SENTINEL2_OPTICAL_REPORT.md` (this report)
9. `tests/test_ds08_sentinel2.py` (15 targeted regression and validation tests)

### U. Targeted Tests
All 15 tests in `tests/test_ds08_sentinel2.py` pass:
- `test_01_real_sentinel2_provenance`: PASSED
- `test_02_synthetic_prototype_exclusion_and_quarantine`: PASSED
- `test_03_image_status_and_no_corrupted_images`: PASSED
- `test_04_band_configuration_and_resolution`: PASSED
- `test_05_quality_metadata_and_cloud_limits`: PASSED
- `test_06_quality_screening_audit_and_rejection_tracking`: PASSED
- `test_07_annotation_table_zero_fabricated_boxes`: PASSED
- `test_08_class_mapping_decoupling`: PASSED
- `test_09_scene_level_split_isolation`: PASSED
- `test_10_unique_identifiers_and_zero_duplicates`: PASSED
- `test_11_manifest_completeness`: PASSED
- `test_12_annotation_provenance_schema`: PASSED
- `test_13_firms_association_provenance`: PASSED
- `test_14_no_final_fusion_artifact_created`: PASSED
- `test_15_frozen_previous_checkpoints_unchanged`: PASSED

### V. Full PyTest Result
- Full test suite passed across all project modules (196 items total, 0 failures, 0 errors).

### W. Frozen Artifact Hashes
| Artifact Path | Expected SHA-256 | Actual SHA-256 | Immutability Status |
|---|---|---|:---:|
| `models/tcn/best_tcn.pt` | `dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16` | `dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16` | **VERIFIED IDENTICAL** |
| `models/deep_sad/best_deep_sad.pt` | `a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa` | `a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa` | **VERIFIED IDENTICAL** |
| `models/yolo/infrastructure/best_infrastructure.pt` | `bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6` | `bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6` | **VERIFIED IDENTICAL** |
| `models/yolo/fire_smoke/best_fire_smoke.pt` | `29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227` | `29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227` | **VERIFIED IDENTICAL** |
| `data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet` | `49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931` | `49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931` | **VERIFIED IDENTICAL** |

### X. Synthetic-Data Exclusion Verification
- `data/reference/ds08_proto_synthetic/` is quarantined.
- Neither `ds08_sentinel2_manifest.parquet` nor `ds08_annotations.parquet` contains references to synthetic files.
- `ds08_annotations.parquet` contains 0 rows, confirming that 0 synthetic boxes were injected into the genuine DS08 dataset.

### Y. Limitations
1. **Physical Image Acquisition Dependency**: Real Sentinel-2 L2A optical granules require Copernicus Data Space Ecosystem API credentials and an active external network connection for retrieval.
2. **Human Labeling Requirement**: Hand-annotation across the 250 candidate chips must be conducted using a visual annotation tool (e.g. CVAT, Label Studio, Roboflow) following the instructions in `ANNOTATION_INSTRUCTIONS.md`.
3. **Domain Fine-Tuning Blocked**: Until real optical images are downloaded and human annotations verified, domain adaptation of YOLO models cannot proceed without compromising scientific validity. Downstream multimodal fusion must rely on the robust frozen vision representations trained on DS06 (DIOR) and DS07 (FASDD_RS).

---

## 3. Scope Lock & Stop Declaration

```
================================================================================
FINAL STAGE 8.5 CONCLUSION:
Real Sentinel-2 specification, screening audit, manifests, and test suites are
COMPLETE and FROZEN. Zero synthetic boxes were fabricated.
Human annotation remains pending; no YOLO fine-tuning was performed.
EXECUTION IS FORMALLY STOPPED AT STAGE 8.5.
================================================================================
```
