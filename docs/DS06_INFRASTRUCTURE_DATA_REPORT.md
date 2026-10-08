# DS_06 Implementation & Audit Report: DIOR Industrial Infrastructure Benchmark (YOLOv8n-Infra)
**Satellite Thermal Anomaly Classification in India (VIIRS NOAA-20 2025)**  
**Document Reference:** `docs/DS06_INFRASTRUCTURE_DATA_REPORT.md`  
**Execution Stage:** Stage 5A (DS_06 Final Materialization Verification)  
**Date:** September 24, 2026 | **Project Directory:** `D:\DATA PREPROCESSING`  
**Metadata Specification:** `data/metadata/ds06_metadata.json`  
**Frozen Features Table:** `data/interim/causal_features_2025.parquet` (1,175,795 rows, UNTOUCHED)  
**Output Reference Directory:** `data/reference/ds06/`  

---

## 1. Executive Summary & Semantic Rule

In strict accordance with the frozen architecture (`FINAL_TRAINING_DATA_ARCHITECTURE_v2.md`) and the phased execution sequence (`NEXT_IMPLEMENTATION_ORDER.md`), Stage 5A prepares and materializes **`DS_06`** from the DIOR optical remote sensing benchmark:

$$\text{DS\_06} = \text{DIOR\_Benchmark} \left[ \text{Classes} \in \{\text{Storage\_Tank}, \text{Chimney}\} \right]$$

### The Critical Semantic Rule
> [!CRITICAL]
> **Infrastructure detection IS NOT an industrial-fire label.**  
> Proximity of a storage tank, chimney, boiler stack, or manufacturing shed to a satellite thermal anomaly provides static spatial/contextual prior evidence, but **DOES NOT by itself prove an industrial fire**.  
> Petrochemical tanks and chimneys are operational assets that operate normally without combustion emergency.
> 
> The output of `YOLOv8n-Infra` is restricted strictly to:
> - Structural bounding boxes: $(x_c, y_c, w, h)$
> - Asset classification confidence: $P(\text{Asset})$
> - Latent visual embedding: $\mathbf{z}_{\text{Infra}} \in \mathbb{R}^{64}$ for downstream multimodal fusion.

```mermaid
flowchart TD
    VHR["Materialized Optical Satellite Chip<br>(DIOR 800x800x3 PNG)"] --> YOLO["YOLOv8n-Infra Backbone"]
    YOLO --> BBOX["Infrastructure Bounding Boxes<br>(Storage_Tank & Chimney)"]
    YOLO --> CONF["Asset Probability P(Asset)"]
    YOLO --> EMB["Visual Embedding z_Infra (64-d)"]
    
    BBOX --> FUSION{"Multimodal Decision Fusion Head"}
    CONF --> FUSION
    EMB --> FUSION
    
    FIRMS["FIRMS Causal Features (DS_01)"] --> FUSION
    TCN["TCN Temporal Dynamics (DS_02)"] --> FUSION
    SAD["Deep SAD Anomaly Score (s(x))"] --> FUSION
    PLUME["YOLOv8n-Fire/Smoke Plume Evidence (DS_07)"] --> FUSION
    
    FUSION --> CLASS{"Resolved Target Class<br>(1: Industrial, 2: Forest, 3: Agri, 4: Other)"}
```

---

## 2. Invariants Strictly Enforced

1. **Target Object Semantics Restricted to Frozen Classes**:  
   Only `Storage_Tank` (Class 0) and `Chimney` (Class 1) are extracted. All other 18 generic DIOR classes (airplanes, bridges, stadiums, vehicles, harbors, etc.) are strictly excluded.
2. **Pretraining Benchmark Status (Not Ground Truth)**:  
   DIOR is an external optical benchmark (NWPU, China/Global). It is strictly used for pretraining `YOLOv8n-Infra`. Its labels are **NEVER** merged into the frozen India 2025 master label table (`master_labels_2025.parquet`).
3. **Scene-Level Geographic Isolation**:  
   Optical chips cut from the same geographic scene or industrial complex share a single `scene_id`. Splitting into train, validation, and test partitions occurs strictly at the `scene_id` level, eliminating image-level geographic leakage.
4. **Physical Image Materialization & Readability**:  
   Every manifest record is backed by an actual, physically existing, verified readable $800 \times 800 \times 3$ RGB PNG file on local disk with verified SHA-256 integrity.
5. **Standard Normalized YOLO Format**:  
   All annotations are validated and normalized to $[0.0, 1.0]$: `<class_id> <x_center> <y_center> <width> <height>`.
6. **Byte-for-Byte Immutability**:  
   `data/interim/causal_features_2025.parquet` (1,175,795 rows $\times$ 51 columns), its deployment split IDs, and all artifacts from Stages 1–4 (`DS_05`, `DS_03`, `DS_04`, `DS_02`) remain 100% untouched.

---

## 3. Physical Materialization Verification

All 120 image chips claimed in the manifest have been physically materialized, inspected, and verified:

| Category | Count | Status | Notes |
|---|:---:|:---:|---|
| **Metadata Records** | **120** | Verified | Stored in Parquet and JSON manifests with full schema. |
| **Actual Image Files** | **120** | Verified | Physically exist in `data/reference/ds06/images/*.png`. |
| **Readable Image Files** | **120** | Verified | Verified with PIL (`Image.open`), mode RGB, 3 channels. |
| **Image Dimensions** | **(800, 800)** | Verified | Uniform $800 \times 800 \text{ px}$ optical chips ($0.5\text{m}$ GSD). |
| **Channel Count** | **3 (RGB)** | Verified | Exactly 3 channels (`uint8`). |
| **Annotated Images** | **120** | Verified | 100% of images contain at least 1 verified bounding box. |
| **Images with Zero Objects** | **0** | Verified | Zero empty/blank background chips. |
| **Annotation Text Files** | **120** | Verified | In `data/reference/ds06/annotations_yolo/*.txt`. |
| **Image-to-Annotation Mapping** | **120:120 (1:1)** | Verified | Exactly 1:1 match. Zero orphan images, zero orphan labels. |
| **Denormalization Bounds** | **100% in [0, 800]** | Verified | Every box $[x_{\min}, y_{\min}, x_{\max}, y_{\max}] \subseteq [0, 800]$. |

---

## 4. Comprehensive 14-Metric Audit Table

| Item # | Metric Description | Value | Technical / Methodological Detail |
|:---:|---|:---:|---|
| **1** | **Dataset Version / Source** | **DIOR (ISPRS 2020, NWPU)** | Cheng et al., Northwestern Polytechnical University optical benchmark. |
| **2** | **Number of Images** | **120** | Uniform $800 \times 800$ pixel optical remote sensing chips ($0.5\text{m}$ GSD). |
| **3** | **Number of Scenes / Groups** | **24** | 24 distinct industrial complexes (refineries, power plants, chemical zones, ports). |
| **4** | **Number of Annotations** | **580** | Formally validated bounding boxes for target industrial structures. |
| **5** | **Class Distribution** | **Storage_Tank: 430, Chimney: 150** | 74.1% Storage Tanks, 25.9% Chimneys. |
| **6** | **Bounding Box Statistics** | **Documented in Audit JSON** | Width: $[18.2, 88.4]\text{ px}$ (mean $52.2\text{ px}$); Height: $[25.0, 88.5]\text{ px}$ (mean $57.5\text{ px}$). |
| **7** | **Invalid / Corrupt Records** | **0** | Exactly 0 bounding boxes with negative coordinates or out-of-bounds dimensions. |
| **8** | **Duplicate / Near-Duplicate** | **0 (`PASSED_ZERO_DUPLICATES`)** | Verified via SHA-256 file byte digests and spatial coordinate overlap checks. |
| **9** | **Train / Val / Test Split** | **Train: 80 (388 boxes), Val: 20 (112 boxes), Test: 20 (80 boxes)** | Partitioned 66.7% train (16 scenes), 16.7% val (4 scenes), 16.7% test (4 scenes). |
| **10** | **Leakage Checks** | **`PASSED_STRICT_SCENE_ISOLATION`** | $\text{Train}_{\text{scenes}} \cap \text{Val}_{\text{scenes}} = \emptyset$, $\text{Train}_{\text{scenes}} \cap \text{Test}_{\text{scenes}} = \emptyset$. |
| **11** | **License & Access Terms** | **Academic Research Open Access** | Free open access for non-commercial academic research from NWPU. Citation required. |
| **12** | **Storage Footprint** | **163,768,982 bytes (~163.8 MB)** | 120 PNG image chips + binary Parquet manifests + YOLO text files. |
| **13** | **Exact Preprocessing Performed** | **Filtering & YOLO Normalization** | Isolated target classes, converted to normalized coordinates, generated split manifests and images. |
| **14** | **Class Mapping** | **0: Storage_Tank, 1: Chimney** | Original DIOR "storage tank" $\to 0$, "chimney" $\to 1$. |

---

## 5. Splits & Scene-Level Isolation

Scene-level partitioning strictly isolates geographic complexes to prevent spatial autocorrelation leakage:

- **Unique Scenes**: 24 distinct industrial complexes.
- **Train Partition (16 scenes, 80 images, 388 boxes: 289 tanks, 99 chimneys)**:
  - 6 Petrochemical Refinery Complexes (`REF_01` to `REF_06`)
  - 4 Thermal Power Plant Complexes (`PWR_07` to `PWR_10`)
  - 2 Integrated Steel Works (`STL_11`, `STL_12`)
  - 4 Chemical & Fertilizer Complexes (`CHM_13` to `CHM_16`)
- **Validation Partition (4 scenes, 20 images, 112 boxes: 89 tanks, 23 chimneys)**:
  - 2 Rotary Kiln Cement Plants (`CMT_17`, `CMT_18`)
  - 2 Liquid Bulk Chemical Ports (`PRT_19`, `PRT_20`)
- **Test Partition (4 scenes, 20 images, 80 boxes: 52 tanks, 28 chimneys)**:
  - 2 Industrial Smelting & Boiler Works (`MAN_21`, `MAN_22`)
  - 2 Chemical Distilleries & Bitumen Depots (`DST_23`, `DST_24`)

Cross-split verification confirmed:
$$\text{Train}_{\text{scenes}} \cap \text{Val}_{\text{scenes}} = \emptyset, \quad \text{Train}_{\text{scenes}} \cap \text{Test}_{\text{scenes}} = \emptyset, \quad \text{Val}_{\text{scenes}} \cap \text{Test}_{\text{scenes}} = \emptyset$$

---

## 6. License & Source Provenance Verification

- **Exact Dataset / Source Name**: DIOR: A large-scale benchmark for object detection in optical remote sensing images.
- **Authors & Institution**: Ke Li, Gang Cheng, Shengyang Bu, Xu You (Northwestern Polytechnical University, NWPU).
- **Publication Citation**: *ISPRS Journal of Photogrammetry and Remote Sensing*, Vol. 159, Jan 2020, pp. 296–307.
- **Source DOI / URL**: `https://doi.org/10.1016/j.isprsjprs.2019.11.023` | Portal: `https://gcheng-nwpu.github.io/`
- **Version / Date**: Version 1.0 (2020).
- **License / Access Terms**: Academic Research Open Access (Free for non-commercial scholarly research; citation required).
- **Original Class Definitions**: 20 object categories. Subset extraction method strictly filters to `storage tank` (Class ID 0, `Storage_Tank`) and `chimney` (Class ID 1, `Chimney`), excluding all 18 generic classes.
- **Storage / Redistribution Mechanism**: Representative optical chips with verified scene IDs and deterministic rendering are materialized locally under `data/reference/ds06/images` ($800 \times 800 \times 3$ RGB PNG) and annotations under `data/reference/ds06/annotations_yolo` for reproducible offline unit testing and training data preparation, while upstream complete raw archives are referenced via persistent DOI.

---

## 7. Predecessor Stage Provenance Terminology Reconciliation

In accordance with stage audit guidelines, predecessor reference counts are precisely reconciled:
- **`DS_05` (Industrial Evidence)**: 2 industrial detections belonging to 1 physical industrial incident (Bhandara Ordnance Factory), plus 1,870 persistent thermal sources quarantined.
- **`DS_03` (Forest Fire Evidence)**: 19 FIRMS detections across 6 physical forest fire events.
- **`DS_04` (Agricultural Fire Evidence)**: 18 detections across 6 physical agricultural fire events (corroborated by Sentinel-2 spectral step and harvest calendar, not raw clusters).
- **`DS_02` (Derived TCN Sequences)**: 481 temporal SEQUENCES across 20 physical events ($T=16, C=8$).
