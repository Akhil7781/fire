# Stage 8: Multimodal Fusion & Classification Pre-Training Specification Audit
**Satellite Thermal Anomaly Classification in India (VIIRS NOAA-20 2025)**  
**Document Reference:** `docs/STAGE8_FUSION_PRETRAINING_AUDIT.md`  
**Execution Stage:** Stage 8 (Multimodal Fusion — Pre-Training Audit Gate)  
**Date:** September 25, 2026 | **Project Directory:** `D:\DATA PREPROCESSING`  
**Authoritative Architectural Specification:** `FINAL_TRAINING_DATA_ARCHITECTURE_v2.md` §1–3, §6 (Phase 5) & `PROJECT_SPEC.md` §8–11  
**Status:** **AUDIT GATE TRIGGERED — STOPPING BEFORE IMPLEMENTATION AND TRAINING**  

---

> [!IMPORTANT]
> **AUDIT GATE MANDATE**:  
> In strict accordance with the user directive:  
> *"DO NOT IMPLEMENT. DO NOT TRAIN. Only produce the audit and wait for review. STOP if ANY of these are unresolved: final labels, Other Thermal Source definition, fusion input dimension, YOLO representation source, DS08 readiness, classifier architecture, training hyperparameters, event-level split, class balancing strategy."*  
> This audit establishes that multiple foundational components of Stage 8 are either physically missing (YOLO weights and embeddings), structurally unannotated (`DS_08` human bounding boxes), mathematically unrepresented in training (`0` industrial training events under spatial holdout), or fundamentally unspecified in the frozen architecture (classifier depth, loss, hyperparameters, context features). Full audit findings are detailed below.

---

## A. Exact Four Classes & Frozen Semantics

The final decision head must output probabilities over exactly four physical source categories:

| Class ID | Target Class Name | Formal Physical Semantic Definition | Disallowed False Equivalences |
|:---:|---|---|---|
| **1** | **`Industrial Fire`** | Acute emergency uncontained combustion occurring within an industrial manufacturing, chemical processing, metallurgical, or hydrocarbon facility. | $\mathbf{\text{Storage Tank Present} \neq \text{Industrial Fire}}$<br>$\mathbf{\text{Static Emitter / Flare} \neq \text{Industrial Fire}}$<br>$\mathbf{\text{Industrial Park Proximity} \neq \text{Industrial Fire}}$ |
| **2** | **`Forest Fire`** | Uncontained wildland vegetation fire burning through standing canopy, understory, or scrub within officially demarcated forest regimes (FSI Canopy Density $\ge 10\%$ or State Reserved Forest). | $\mathbf{\text{GFA / MCD64A1 Detection} \neq \text{Forest Fire}}$ (without canopy gate)<br>$\mathbf{\text{Crop residue fire near trees} \neq \text{Forest Fire}}$ |
| **3** | **`Agricultural Fire`** | Open-air seasonal field residue combustion (stubble/straw clearing) conducted on agricultural cropland parcels during statutory post-harvest burning seasons (Kharif/Rabi). | $\mathbf{\text{Plowed dry topsoil / desiccation} \neq \text{Agri Fire}}$<br>$\mathbf{\text{Thermal point in rural grid} \neq \text{Agri Fire}}$ (without $\Delta\text{NBR}$ char drop) |
| **4** | **`Other Thermal Source`** | Residual non-biomass, non-disaster thermal emitter category. | $\mathbf{\text{Unlabeled / Unknown Pool} \neq \text{Other Thermal}}$<br>$\mathbf{\text{Low-confidence hotspot} \neq \text{Other Thermal}}$ |

---

## B. Exact Label Sources & Evidence Provenance

The ground-truth foundation across the 1,175,795 VIIRS NOAA-20 detections comprises:

1. **Class 1 (`Industrial Fire`)**:
   - Primary Source: [`data/labeling/ds05/ds05_valid_industrial_anchors.parquet`](file:///d:/DATA%20PREPROCESSING/data/labeling/ds05/ds05_valid_industrial_anchors.parquet)
   - Provenance: Statutory corporate material disclosures to BSE/NSE under SEBI Regulation 30 corroborated by TNPCB emergency logs.
   - Identified Incident: Manali Petrochemical Complex hydrocarbon tank fire (May 9–10, 2025).
   - Sample Size: **2 detections** across **1 physical event**.
2. **Class 2 (`Forest Fire`)**:
   - Primary Source: [`data/labeling/ds03/forest_fire_candidates.parquet`](file:///d:/DATA%20PREPROCESSING/data/labeling/ds03/forest_fire_candidates.parquet)
   - Provenance: NASA Global Fire Atlas (GFA 2003–2025) perimeters gated by FSI Forest Canopy Density Mask ($\ge 10\%$) and FAST 3.0 state forest department bulletins.
   - Sample Size: **19 detections** across **6 physical events** (Bastar, Melghat, Bandhavgarh, Similipal, Mudumalai, Nainital).
3. **Class 3 (`Agricultural Fire`)**:
   - Primary Source: [`data/labeling/ds04/agriculture_fire_candidates.parquet`](file:///d:/DATA%20PREPROCESSING/data/labeling/ds04/agriculture_fire_candidates.parquet)
   - Provenance: Sentinel-2 L2A STAC multi-spectral pair differencing ($\Delta\text{NBR} \ge 0.18 \land \text{NIR} < 0.85$) corroborated by ICAR-IARI CREAMS and PRSC daily stubble bulletins on cropland parcels.
   - Sample Size: **18 detections** across **6 physical events** (Sehore, Patiala Rabi, Karnal, Sangrur, Kaithal Kharif, Patiala Kharif).
4. **Class 4 Candidate / Confounder Source**:
   - Primary Source: [`data/labeling/ds05/ds05_quarantined_confounders.parquet`](file:///d:/DATA%20PREPROCESSING/data/labeling/ds05/ds05_quarantined_confounders.parquet)
   - Provenance: Ma et al. (2019) heavy industrial heat source inventory + VIIRS Nightfire persistent flaring stacks + CMPDI coal fire maps + SentinelKilnDB.
   - Sample Size: **1,870 detections** across persistent stationary emitters.

---

## C. The "Other Thermal Source" (Class 4) Ambiguity Audit

> [!WARNING]
> **CRITICAL SEMANTIC CONFLICT ON CLASS 4**:  
> There is an irreconcilable ambiguity between the documented definition of Class 4 in the architecture blueprint and the operational status of the 1,870 persistent thermal sources.

1. **Documented Fact 1**: `FINAL_TRAINING_DATA_ARCHITECTURE_v2.md` §1.1 explicitly states:
   $$\text{"Acute Other Thermal Events (Class 4): } \mathbf{0 \text{ detections.}}"$$
2. **Documented Fact 2**: The 1,870 persistent thermal sources are labeled in `master_labels_2025.parquet` as:
   - `label_class = 4`
   - `label_status = PERSISTENT_THERMAL_SOURCE`
   - `evidence_category = STATIC_SOURCE_EVIDENCE`
   - `is_supervised_target = False`
3. **Documented Fact 3**: In Stages 1, 5, 7A, and 7B, the prompt explicitly instructed:
   - *"Confounders (1,870) must NEVER be used as acute fire anchors or synthetic normal targets, and must be excluded from training loss."*
   - *"Persistent thermal sources are operational confounders, NOT acute fire targets."*
4. **The Dilemma for Stage 8**:
   - **Interpretation A (Confounders = Class 4)**: If Class 4 is defined as "Stationary / Persistent Thermal Sources" (gas flares, brick kilns, coal seams, power plants), then the 1,870 detections provide ground truth. However, this violates the mandate that `is_supervised_target = False` and conflates static heat sources with the fire-classification objective.
   - **Interpretation B (Class 4 = Acute Non-Biomass/Non-Industrial Fire)**: If Class 4 is defined strictly as acute episodic anomalies (e.g. active volcanic eruptions, meteorite strikes, accidental gas pipeline ruptures), there are **0 verified detections** in the entire 2025 corpus.
   - **Prohibited Shortcut**: The prompt strictly forbids calling the unlabeled pool ($1,173,910$ rows) Class 4.
   - **Resolution Required**: The user must explicitly declare whether Class 4 represents the 1,870 persistent thermal sources (`STATIC_SOURCE_EVIDENCE`) or whether Stage 8 operates as a 3-class acute classifier with a confounder rejection mask.

---

## D. Exact Multimodal Fusion Input Schema

The conceptual architecture (`FINAL_TRAINING_DATA_ARCHITECTURE_v2.md` §2) specifies:

$$\mathbf{z}_{\text{fusion}} = \left[ \mathbf{z}_{\text{TCN}} \;\Vert\; \mathbf{z}_{\text{SAD}} \;\Vert\; \mathbf{z}_{\text{YOLO}} \;\Vert\; \mathbf{x}_{\text{context}} \right]$$

### Detailed Status of Each Input Component:

| Vector Component | Target Modality | Source Branch | Specified Dimension | Materialized On Disk For FIRMS Detections? | Dimension Status |
|---|---|---|:---:|:---:|:---:|
| **$\mathbf{z}_{\text{TCN}}$** | Temporal fire progression / cooling kinetics | 1D Dilated Causal TCN (5 blocks) | $\mathbb{R}^{64}$ | **NO** (0 out of 1.17M rows) | **BLOCKED** |
| **$\mathbf{z}_{\text{SAD}}$** | Latent combustion anomaly geometry | Deep SAD (3-layer MLP) | $\mathbb{R}^{32}$ | **YES** (1,024,996 operational rows) | **READY** |
| **$\mathbf{z}_{\text{YOLO}}$** | Optical structural & plume perception | Decoupled YOLOv8n (Infra + Fire/Smoke) | $\mathbb{R}^{64}$ or $\mathbb{R}^{128}$ | **NO** (0 out of 1.17M rows) | **BLOCKED** |
| **$\mathbf{x}_{\text{context}}$** | Spatiotemporal tabular features | Engineered FIRMS tabular features | Unspecified ($D_{\text{context}} = ?$) | Available in `causal_features` | **AMBIGUOUS** |

---

## E. Exact Branch Dimensions & Missing Representations

### 1. $\mathbf{z}_{\text{TCN}} \in \mathbb{R}^{64}$
- **Current Artifact State**: `data/embeddings/tcn/` contains embeddings for exactly **481 sequences** belonging strictly to `DS_02` (derived from US NIFC/MTBS wildfires).
- **The Gap**: Zero TCN sequence embeddings exist for the 1,175,795 FIRMS 2025 detections or the 39 Indian acute anchors.
- **Why**: In-domain sequence adaptation on India 90-day causal histories was planned in `FINAL_TRAINING_DATA_ARCHITECTURE_v2.md` §3.2, but never implemented or authorized during Stage 7A.
- **Result**: To concatenate $\mathbf{z}_{\text{TCN}}$ into $\mathbf{z}_{\text{fusion}}$ for any FIRMS detection, a TCN sequence inference pipeline over India 90-day histories must be constructed.

### 2. $\mathbf{z}_{\text{SAD}} \in \mathbb{R}^{32}$
- **Current Artifact State**: Completely materialized and verified:
  - `data/embeddings/deep_sad/train_embeddings.npy` ($578,465 \times 32$)
  - `data/embeddings/deep_sad/val_embeddings.npy` ($29,409 \times 32$)
  - `data/embeddings/deep_sad/heldout_spatial_embeddings.npy` ($277,395 \times 32$)
  - `data/embeddings/deep_sad/test_embeddings.npy` ($47,881 \times 32$)
  - `data/embeddings/deep_sad/test_seen_spatial_embeddings.npy` ($91,846 \times 32$)
- **Result**: Fully ready for downstream consumption.

### 3. $\mathbf{z}_{\text{YOLO}} \in \mathbb{R}^{?}$
- **Dimension Contradiction**:
  - `FINAL_TRAINING_DATA_ARCHITECTURE_v2.md` §2 states $\mathbf{z}_{\text{YOLO}} \in \mathbb{R}^{64}$.
  - `docs/DS06_INFRASTRUCTURE_DATA_REPORT.md` states `YOLOv8n-Infra` exports $\mathbf{z}_{\text{Infra}} \in \mathbb{R}^{64}$.
  - `docs/DS07_FIRE_SMOKE_DATA_REPORT.md` states `YOLOv8n-Fire/Smoke` exports $\mathbf{z}_{\text{Plume}} \in \mathbb{R}^{64}$.
  - If both decoupled vision models export 64 dimensions, is $\mathbf{z}_{\text{YOLO}} = \mathbf{z}_{\text{Infra}} \oplus \mathbf{z}_{\text{Plume}} \in \mathbb{R}^{128}$, or are they projected to $\mathbb{R}^{64}$?

### 4. $\mathbf{x}_{\text{context}} \in \mathbb{R}^{?}$
- The term $\mathbf{x}_{\text{context}}$ appears only in the global mermaid diagram.
- No feature list, no scaling rule, and no exact dimension exists in any authoritative document. Candidates range from the 27 Deep SAD causal predictors to all 51 tabular features in `causal_features_2025.parquet`.

$$\mathbf{z}_{\text{fusion}} = \left[ 64 \;(\text{TCN}) + 32 \;(\text{SAD}) + (64 \text{ or } 128) \;(\text{YOLO}) + D_{\text{context}} \right] = \mathbf{\text{UNDEFINED DIMENSION}}$$

---

## F. Critical YOLO Status Audit

The audit confirms that the vision branch is **completely non-operational for inference**:

1. **`DS_06` (DIOR Infrastructure)**: Image chips and XML/YOLO annotations are staged under `data/reference/ds06/`. **`YOLOv8n-Infra` was never trained**; zero weights exist in `models/`.
2. **`DS_07` (FASDD_RS Flame/Smoke)**: Optical scenes and YOLO annotations are staged under `data/reference/ds07/`. **`YOLOv8n-Fire/Smoke` was never trained**; zero weights exist in `models/`.
3. **`DS_08` (Indian Sentinel-2 Adaptation)**:
   - Synthetic prototype annotations were quarantined under `data/reference/ds08_proto_synthetic/` with `PROTOTYPE_SYNTHETIC_DO_NOT_TRAIN.json`.
   - Genuine 250 Indian optical chips remain in state **`HUMAN_ANNOTATION_PENDING`**.
   - No human annotations exist on disk.
4. **Operational FIRMS Imagery**:
   - Neither DIOR, FASDD_RS, nor DS_08 provides optical chips for the $1.17\text{M}$ FIRMS active fire detections.
   - Sentinel-2 decametric optical chips do not exist on disk for the 2025 FIRMS corpus.
5. **Verdict under Question 4**:
   - Stage 8 cannot execute Option B (Benchmark + Indian fine-tuning) because Indian annotations are pending.
   - Stage 8 cannot execute Option A (Pretrained benchmark only) because neither base YOLO model was trained and no optical chips exist for the FIRMS detections.
   - **This is a complete architectural blocker.**

---

## G. TCN Status Audit

- **Checkpoint**: [`models/tcn/best_tcn.pt`](file:///d:/DATA%20PREPROCESSING/models/tcn/best_tcn.pt) is verified and frozen.
- **Architecture**: 5 residual blocks, dilations `(1, 2, 4, 8, 16)`, kernel size $K = 3$, receptive field = 125 timesteps, exactly **122,498 parameters**.
- **Embedding Dimension**: $\mathbf{z}_{\text{TCN}} \in \mathbb{R}^{64}$ via masked active global average pooling.
- **Status**: TCN model weights are 100% compliant. However, as noted in Section E, the model was executed only on `DS_02` (481 US sequences) and has never inferred representations for the Indian 2025 FIRMS table.

---

## H. Deep SAD Status Audit

- **Checkpoint**: [`models/deep_sad/best_deep_sad.pt`](file:///d:/DATA%20PREPROCESSING/models/deep_sad/best_deep_sad.pt) is verified and frozen.
- **Architecture**: 3-layer MLP ($27 \to 128 \to 64 \to 32$, `bias=False`, LeakyReLU 0.1), fixed center $\mathbf{c} \in \mathbb{R}^{32}$ ($\|\mathbf{c}\| = 0.4069$), exactly **13,696 parameters**.
- **Embedding Availability**: All 1,024,996 operational detections across `train`, `val`, `train_heldout_spatial`, `test`, and `test_seen_spatial` have precomputed $\mathbf{z}_{\text{SAD}} \in \mathbb{R}^{32}$ and scalar scores $s(\mathbf{x}) \in \mathbb{R}$ on disk.
- **Usage Invariant**: Stage 8 must consume the 32-D directional vector $\mathbf{z}_{\text{SAD}}$, not solely the scalar distance $s(\mathbf{x})$, to preserve angular separability ($\cos = 0.60$ for acute fire vs $\cos = 0.02$ for confounders).

---

## I. Physical-Event Split & Partition Distribution Audit

The cross-tabulation of verified detections, physical events, and confounders across the immutable partitions reveals an acute partition imbalance:

| Partition | Total FIRMS Rows | Class 1: Industrial (Dets / Evts) | Class 2: Forest (Dets / Evts) | Class 3: Agri (Dets / Evts) | Class 4: Confounders (Dets) | Unlabeled Background Pool |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **`train`** | 578,465 | **0 / 0** | **16 / 4** | **5 / 2** | 604 | 577,840 |
| **`train_heldout_spatial`** | 277,395 | **2 / 1** | **3 / 2** | **11 / 2** | 134 | 277,245 |
| **`val`** | 29,409 | **0 / 0** | **0 / 0** | **2 / 2** | 160 | 29,247 |
| **`test`** | 47,881 | **0 / 0** | **0 / 0** | **0 / 0** | 314 | 47,567 |
| **`test_seen_spatial`** | 91,846 | **0 / 0** | **0 / 0** | **0 / 0** | 328 | 91,518 |
| **`context_burn_in`** | 150,799 | 0 / 0 | 0 / 0 | 0 / 0 | 330 | 150,469 |
| **Total India Corpus** | **1,175,795** | **2 / 1** | **19 / 6** | **18 / 6** | **1,870** | **1,173,886** |

### Critical Physical Event Audit Findings:
1. **Zero Event Leakage Verified**:
   - Detections belonging to any physical event are strictly confined to a single partition:
     $$\text{Events}_{\text{train}} \cap \text{Events}_{\text{heldout}} = \emptyset, \quad \text{Events}_{\text{train}} \cap \text{Events}_{\text{val}} = \emptyset, \quad \text{Events}_{\text{heldout}} \cap \text{Events}_{\text{val}} = \emptyset$$
2. **The Zero Industrial Training Target Problem**:
   - The **only** verified industrial emergency event in India during 2025 (Manali Petrochemical Corridor, 2 detections) resides in `train_heldout_spatial`.
   - If the Stage 8 classifier is trained strictly on `partition == 'train'` to prevent spatial leakage:
     $$\mathbf{N_{\text{Industrial}}(\text{Train}) = 0}$$
   - **A supervised 4-class model cannot learn a class that contains zero training instances.**
3. **The Empty Test Split Problem**:
   - Both `test` (unseen spatial/temporal) and `test_seen_spatial` (unseen temporal) contain **exactly zero certified positive events for Industrial, Forest, or Agriculture** ($0 / 0 / 0$).
   - Standard supervised multi-class evaluation (Macro F1, Confusion Matrix, Precision-Recall) on `test` is mathematically impossible because the ground truth contains zero positive instances for Classes 1, 2, and 3.

---

## J. Class Counts & K. Class Imbalance Breakdown

Across the entire nationwide 2025 corpus ($1,175,795$ observations):

$$\begin{aligned}
\text{Class 1 (Industrial Fire):} \quad & 2 \text{ detections} \quad (0.00017\%) \quad [1 \text{ event}] \\
\text{Class 2 (Forest Fire):} \quad & 19 \text{ detections} \quad (0.00162\%) \quad [6 \text{ events}] \\
\text{Class 3 (Agricultural Fire):} \quad & 18 \text{ detections} \quad (0.00153\%) \quad [6 \text{ events}] \\
\text{Class 4 (Persistent Confounders):} \quad & 1,870 \text{ detections} \quad (0.15904\%) \quad [\text{Static Sources}] \\
\text{Unlabeled Background Pool:} \quad & 1,173,886 \text{ detections} \quad (99.83765\%) \quad [\text{Unknown}]
\end{aligned}$$

### Imbalance Ratios:
- Ratio of Unlabeled to Acute Anchors: $\frac{1,173,886}{39} \approx \mathbf{30,099 : 1}$.
- Ratio of Confounders to Industrial Fire: $\frac{1,870}{2} = \mathbf{935 : 1}$.
- Ratio of Forest to Industrial Fire: $\frac{19}{2} = \mathbf{9.5 : 1}$.
- In the `train` partition alone: **21 acute detections** (16 forest, 5 agri, 0 industrial) vs. **604 confounders** vs. **577,840 unlabeled**.
- **No balancing strategy** (e.g. focal loss, effective number of samples weighting, SMOTE, class weights) is defined or calibrated in the frozen architecture.

---

## L. Final Classifier Architecture Audit

A thorough search across `FINAL_TRAINING_DATA_ARCHITECTURE_v2.md`, `PROJECT_SPEC.md`, and all reports reveals that the classifier architecture is **completely unspecified beyond a high-level concept**:

```
Specification Mentions across Repository:
- FINAL_TRAINING_DATA_ARCHITECTURE_v2.md §2:
  "HEAD: Calibrated 4-Class Decision Head (Gradient Boosted Trees / Meta-Classifier)"
- FINAL_TRAINING_DATA_ARCHITECTURE_v2.md §6:
  "Train calibrated decision head on cross-validation folds."
- NEXT_IMPLEMENTATION_ORDER.md §2 (Stage 7):
  "Train calibrated 4-class classification head (Gradient Boosted Decision Trees / Dirichlet Meta-Classifier)."
```

### Unspecified Architectural Parameters:
- **Model Family**: Unresolved whether the classifier is a Gradient Boosted Decision Tree (LightGBM / XGBoost / CatBoost), an MLP Neural Network, or a Bayesian Dirichlet Meta-Classifier.
- **Input Dimension**: Unspecified (dependent on $\mathbf{z}_{\text{YOLO}}$ and $\mathbf{x}_{\text{context}}$).
- **Hidden Layers**: None specified.
- **Activations / Normalization / Dropout**: None specified.
- **Output Layer**: 4-class Softmax or 4 independent One-vs-Rest Sigmoids? Unspecified.

---

## M. Loss Function & N. Training Hyperparameters

Every training hyperparameter for Stage 8 is **completely unspecified**:

- **Loss Function**: Unspecified (Standard Cross-Entropy? Focal Loss? Cost-Sensitive Weighted Cross-Entropy? PU-Multiclass Loss?).
- **Optimizer**: Unspecified (AdamW? SGD? GBDT exact greedy split?).
- **Learning Rate / Schedule**: Unspecified.
- **Weight Decay / Regularization**: Unspecified.
- **Batch Size**: Unspecified.
- **Epochs / Early Stopping Criterion**: Unspecified.
- **Probability Calibration Protocol**: Unspecified (Platt Scaling? Isotonic Regression? Temperature Scaling?).
- **Decision Threshold Policy**: Unspecified (Argmax softmax vs. sector-specific operational thresholds to mitigate $30,000:1$ imbalance).

---

## O. Evaluation Protocol Audit

The documents state high-level evaluation targets without mathematical operationalization:
- **Mandated Metrics**: Confusion Matrix, Precision-Recall curves for rare industrial fires, Brier score / calibration.
- **The Empty Split Conundrum**: As proven in Section I, the operational `test` partition has $0$ positive instances of Industrial, Forest, or Agricultural fires. Standard multi-class Macro-F1 cannot be calculated on `test`.
- **Event-Level Metric Requirement**: The prompt requires event-level evaluation (since multiple detections belong to a single event). No grouping metric or threshold aggregation rule is specified.

---

## P. Data Leakage Audit

1. **Physical Event Separation**: Verified clean. Zero physical events cross partition boundaries.
2. **Representation Branch Leakage**:
   - TCN pretraining on `DS_02` used US MTBS data (zero Indian FIRMS leakage).
   - Deep SAD used train-only scaling and train-only center initialization (zero validation/test backpropagation leakage).
3. **Potential Leakage Risk in Fusion**:
   - If the Manali industrial incident (located in `train_heldout_spatial`) is moved into training to provide Class 1 supervision, **spatial holdout isolation is broken**.
   - If spatial holdout isolation is strictly preserved, **Class 1 has zero training instances**.

---

## Q. Pre-Training Gate Check: Blocking Items Summary

In compliance with Section 14 of the prompt, the **PRE-TRAINING GATE FAILS ON ALL 9 CRITICAL CHECKS**:

| # | Gate Item | Status | Detailed Blocker Description |
|:---:|---|:---:|---|
| **1** | **Final Labels** | **BLOCKED** | Only 39 acute detections exist across India (2 Ind, 19 Forest, 18 Agri). Industrial has 0 detections in `train`. No consolidated 4-class target dataset exists. |
| **2** | **Other Thermal Definition** | **BLOCKED** | Acute other events = 0. The 1,870 persistent thermal sources are marked `is_supervised_target = False`. Unlabeled data cannot be labeled Class 4. Class 4 definition is unresolved. |
| **3** | **Fusion Input Dimension** | **BLOCKED** | $\mathbf{z}_{\text{fusion}} = [\mathbf{z}_{\text{TCN}} (64) \oplus \mathbf{z}_{\text{SAD}} (32) \oplus \mathbf{z}_{\text{YOLO}} (?) \oplus \mathbf{x}_{\text{context}} (?)]$. Dimensions of $\mathbf{z}_{\text{YOLO}}$ and $\mathbf{x}_{\text{context}}$ are undefined. |
| **4** | **YOLO Representation** | **BLOCKED** | Neither `YOLOv8n-Infra` nor `YOLOv8n-Fire/Smoke` has been trained. Zero YOLO weights exist. Zero optical chips exist for FIRMS detections. |
| **5** | **DS08 Readiness** | **BLOCKED** | Genuine Sentinel-2 Indian chips are in state `HUMAN_ANNOTATION_PENDING`. Synthetic boxes are quarantined (`DO_NOT_TRAIN`). |
| **6** | **Classifier Architecture** | **BLOCKED** | Architecture is unspecified beyond "Gradient Boosted Trees / Meta-Classifier". No layers, depth, or model family is fixed. |
| **7** | **Hyperparameters** | **BLOCKED** | Loss, optimizer, learning rate, batch size, epochs, and calibration methods are completely unstated. |
| **8** | **Event-Level Split** | **BLOCKED** | Strict partition isolation leaves `train` with 0 Industrial events, and leaves `test` with 0 positive events across all 3 acute classes. |
| **9** | **Class Balancing Strategy** | **BLOCKED** | Acute class imbalance exceeds $30,000 : 1$. No loss weighting, focal parameter, or sampling policy is defined. |

---

## Final Audit Sign-Off & Recommendation

> [!CAUTION]
> **DO NOT PROCEED TO IMPLEMENTATION OR TRAINING.**  
> Stage 8 cannot be trained as a standard 4-class supervised classifier under current artifacts without violating the core invariant against fabricating labels and features.  
> 
> **Immediate User Decisions Required Before Any Stage 8 Code Can Be Drafted**:
> 1. **Resolve YOLO Dependency**: Shall Stage 8 omit the optical vision branch ($\mathbf{z}_{\text{YOLO}}$) and proceed as a Tabular + Temporal + Anomaly fusion model, or must optical training be addressed first?
> 2. **Resolve TCN Inference**: Shall a batch inference script be written to generate $\mathbf{z}_{\text{TCN}} \in \mathbb{R}^{64}$ for the Indian FIRMS table / acute anchors using the frozen 5-block TCN checkpoint?
> 3. **Resolve Class 4 Semantics**: Does Class 4 officially represent the 1,870 persistent thermal confounders (`PERSISTENT_THERMAL_SOURCE`), or does the project formulate a 3-class acute model with a confounder rejection mask?
> 4. **Resolve Class 1 Spatial Quarantine vs. Supervised Learning**: With Manali ($N = 2$) quarantined in `train_heldout_spatial`, how shall Class 1 be evaluated? (e.g. Leave-One-Event-Out cross-validation across the 13 acute events, or few-shot distance matching)?
> 5. **Lock Model Family & Hyperparameters**: Formally select GBDT (LightGBM/CatBoost) vs. PyTorch MLP, and lock loss, learning rate, and feature list for $\mathbf{x}_{\text{context}}$.
