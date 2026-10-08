# Stage 7A: 1D Dilated Causal TCN Self-Supervised Pretraining & Representation Learning Report
**Satellite Thermal Anomaly Classification in India (VIIRS NOAA-20 2025)**  
**Document Reference:** `docs/DS02_TCN_PRETRAINING_REPORT.md`  
**Execution Stage:** Stage 7A (TCN Self-Supervised Sequence Pretraining — 5-Block Clean Retrain)  
**Date:** September 25, 2026 | **Project Directory:** `D:\DATA PREPROCESSING`  
**Authoritative Architectural Specification:** `FINAL_TRAINING_DATA_ARCHITECTURE_v2.md` §3.2  
**Active Model Artifacts:** `models/tcn/` (122,498 parameters, 5 residual blocks)  
**Active Embeddings:** `data/embeddings/tcn/` (64-D latent vectors)  
**Quarantined Superseded Artifacts:** `models/tcn/superseded_4block/`, `data/embeddings/tcn/superseded_4block/`  
**Hardware / Framework:** CPU | PyTorch 2.14.0+cpu  

---

## 1. Executive Summary & Architecture Compliance Audit

Following a rigorous source-level architecture consistency audit against `FINAL_TRAINING_DATA_ARCHITECTURE_v2.md` §3.2, the 1D Dilated Causal Temporal Convolutional Network (TCN) was corrected from a non-compliant 4-block implementation to the authoritative **5-block, 5-dilation architecture**, followed by a complete clean retrain from scratch.

$$\mathcal{F}_{\text{TCN}}: \mathbb{R}^{B \times 16 \times 8} \longrightarrow \mathbb{R}^{B \times 64} \quad (\mathbf{z}_{\text{TCN}})$$

### Architectural Compliance & Audit Status:
- **Superseded Implementation (Quarantined)**: 4 residual blocks, dilations `(1, 2, 4, 8)`, 97,666 parameters. Identified as non-compliant with §3.2; all weights and embeddings moved to `superseded_4block/` and quarantined.
- **Corrected Authoritative Implementation**: 5 residual blocks, dilations `(1, 2, 4, 8, 16)`, exactly **122,498 parameters**.
- **Confirmed Data Flow Paradigm (Pattern A)**:
  - Causal hidden states $H \in \mathbb{R}^{B \times 64 \times 16} \to$ per-timestep $\text{FRP}$ and $\Delta T$ reconstruction heads.
  - Causal hidden states $H \in \mathbb{R}^{B \times 64 \times 16} \xrightarrow{\text{Active Pooling}} \mathbf{z}_{\text{TCN}} \in \mathbb{R}^{64}$ for downstream multimodal fusion.
  - $\mathbf{z}_{\text{TCN}}$ is **not** a sequence reconstruction bottleneck; no temporal decoder exists.

---

## 2. Corrected Model Architecture & Mathematical Receptive Field

```
1D Dilated Causal TCN Architecture (5 Residual Blocks, K=3):
├── Input Layer: (Batch, Timesteps=16, Channels=8)
├── Causal Temporal Blocks (Dilations d in {1, 2, 4, 8, 16}, Kernel k=3):
│   ├── Block 1 (d=1,  pad=2):  CausalConv1d(8 -> 64)  + ReLU + Dropout(0.2) + CausalConv1d(64 -> 64) + Residual(1x1 Conv)
│   ├── Block 2 (d=2,  pad=4):  CausalConv1d(64 -> 64) + ReLU + Dropout(0.2) + CausalConv1d(64 -> 64) + Residual(Identity)
│   ├── Block 3 (d=4,  pad=8):  CausalConv1d(64 -> 64) + ReLU + Dropout(0.2) + CausalConv1d(64 -> 64) + Residual(Identity)
│   ├── Block 4 (d=8,  pad=16): CausalConv1d(64 -> 64) + ReLU + Dropout(0.2) + CausalConv1d(64 -> 64) + Residual(Identity)
│   └── Block 5 (d=16, pad=32): CausalConv1d(64 -> 64) + ReLU + Dropout(0.2) + CausalConv1d(64 -> 64) + Residual(Identity)
├── Latent Bottleneck Projection:
│   └── Masked Active Global Average Pooling -> Linear(64, 64) -> LayerNorm(64) -> z_TCN in R^64
└── Reconstruction Heads:
    ├── FRP Head: Linear(64, 32) -> ReLU -> Linear(32, 1) -> Predicted FRP (Normalized)
    └── Thermal Contrast Head: Linear(64, 32) -> ReLU -> Linear(32, 1) -> Predicted Delta-T (Normalized)
```

### Exact Mathematical Receptive Field ($K=3$):
Each residual block (`TemporalBlock`) contains two causal convolutions of kernel size $K=3$ with left-only padding $(K-1) \times d = 2d$:
$$\text{RF} = 1 + 2 \sum_{l=1}^5 (K - 1) \cdot d_l = 1 + 4 \times (1 + 2 + 4 + 8 + 16) = 1 + 4 \times 31 = \mathbf{125} \text{ timesteps}$$
*(Or $\text{RF} = 1 + 2 \times 31 = \mathbf{63} \text{ timesteps}$ if calculated per dilation stage).*  
Both formulations strictly and comprehensively cover the uniform sequence window of $T=16$ historical observations with zero future leakage.

### Hyperparameter Specification:
- **Input Channels ($C=8$)**:
  0: `elapsed_time_hours`  
  1: `geodesic_distance_km`  
  2: `thermal_contrast_k` (Reconstruction Target)  
  3: `frp_mw` (Reconstruction Target)  
  4: `log1p_frp`  
  5: `pixel_footprint_km2`  
  6: `solar_zenith_deg`  
  7: `daynight_flag`  
- **Sequence Length ($T$)**: 16 timesteps (left-padded with zeros)
- **Hidden Channels**: 64
- **Dilations**: `(1, 2, 4, 8, 16)`
- **Residual Blocks**: 5
- **Latent Dimension**: 64
- **Total Trainable Parameters**: **122,498** (+24,832 from the corrected 5th residual block)
- **Optimizer**: AdamW ($\beta_1=0.9, \beta_2=0.999$, weight decay $= 10^{-4}$)
- **Learning Rate**: $10^{-3}$ with `ReduceLROnPlateau(factor=0.5, patience=5, min_lr=1e-5)`
- **Batch Size**: 32
- **Mask Ratio**: 15% of active timesteps per sequence ($k = \max(1, \text{round}(0.15 \times N_{\text{active}}))$)
- **Loss Function**: Smooth L1 (Huber, $\beta=1.0$) computed strictly on masked active positions

---

## 3. Dataset Composition & Data Isolation Audit

| Partition | Sequence Count | Physical Event Count | Active Timesteps | Pretraining Role in Stage 7A |
|---|:---:|:---:|:---:|---|
| **`derived_ds02_train`** | **339** | **14** | **3,479** | **Active Gradient Updates & Scaler Fitting** |
| **`derived_ds02_val`** | **71** | **3** | **621** | **Validation Loss & Checkpoint Selection** |
| **`derived_ds02_test`** | **71** | **3** | **776** | **Inference-Only Representation Extraction** |
| **TOTAL** | **481** | **20** | **4,876** | **Full DS_02 Corpus** |

> [!IMPORTANT]
> **Data Isolation Guarantees**:
> 1. Feature scaler (`models/tcn/scaler_params.json`) fitted exclusively on the 3,479 active timesteps of `derived_ds02_train`. Zero validation or test samples contributed to normalizer state.
> 2. Validation partition used solely for checkpoint tracking and early stopping.
> 3. Test partition strictly quarantined from optimizer and hyperparameter tuning.
> 4. Physical event boundaries strictly disjoint across train, val, and test.

---

## 4. Pretraining Results & Metrics (Clean Retrain)

Training converged smoothly and triggered early stopping at Epoch 30 (patience = 12 epochs without validation loss improvement):

- **Best Epoch**: **Epoch 18**
- **Best Validation Loss**: **0.2039** (Smooth L1) — *improved from 0.2526 in 4-block prototype*
- **Final Training Loss**: **0.1570** (Smooth L1)
- **Training Runtime**: **17.07 seconds** on CPU

### Masked Reconstruction Physical Error Metrics (Best Epoch 18 Checkpoint):
- **FRP Reconstruction MAE**: **7.355 MW** (RMSE: **9.939 MW**) on physical radiant energy
- **$\Delta T$ Reconstruction MAE**: **2.124 K** (RMSE: **2.650 K**) on brightness temperature contrast

### Training Loss Trajectory (Sampled Epochs):
| Epoch | Train Loss | Val Loss | Val FRP MAE (MW) | Val $\Delta T$ MAE (K) | Learning Rate | Status |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 0.7449 | 0.3673 | 15.28 | 3.42 | $1.0 \times 10^{-3}$ | Checkpoint Saved |
| 2 | 0.4204 | 0.3042 | 11.82 | 2.76 | $1.0 \times 10^{-3}$ | Checkpoint Saved |
| 3 | 0.2850 | 0.3105 | 10.13 | 2.53 | $1.0 \times 10^{-3}$ | - |
| 4 | 0.2333 | 0.2610 | 8.83 | 2.32 | $1.0 \times 10^{-3}$ | Checkpoint Saved |
| 5 | 0.2271 | 0.2727 | 8.46 | 2.30 | $1.0 \times 10^{-3}$ | - |
| 10 | 0.1812 | 0.2690 | 8.22 | 2.28 | $1.0 \times 10^{-3}$ | - |
| 15 | 0.1649 | 0.2384 | 7.66 | 2.19 | $5.0 \times 10^{-4}$ | Checkpoint Saved |
| **18** | **0.1581** | **0.2039** | **7.36** | **2.12** | **$5.0 \times 10^{-4}$** | **BEST CHECKPOINT** |
| 20 | 0.1703 | 0.2103 | 7.59 | 2.13 | $5.0 \times 10^{-4}$ | - |
| 25 | 0.1699 | 0.2103 | 7.56 | 2.15 | $2.5 \times 10^{-4}$ | - |
| 30 | 0.1570 | 0.2110 | 7.51 | 2.18 | $2.5 \times 10^{-4}$ | Early Stopping (Patience 12) |

---

## 5. Artifact Inventory

### Active 5-Block Model Artifacts (`models/tcn/`):
- `models/tcn/best_tcn.pt`: Best model weights, optimizer state, config, and scaler parameters (Epoch 18, 122,498 parameters).
- `models/tcn/final_tcn.pt`: Final model checkpoint (Epoch 30).
- `models/tcn/config.json`: Hyperparameters (`"dilations": [1, 2, 4, 8, 16]`).
- `models/tcn/training_history.json`: Complete 30-epoch trajectory.
- `models/tcn/scaler_params.json`: Train-fitted channel means and standard deviations.
- `models/tcn/tcn_training_summary.json`: Executive JSON execution summary.

### Active 5-Block Latent Embeddings (`data/embeddings/tcn/`):
- `data/embeddings/tcn/train_embeddings.npy`: $(339, 64)$ float32 array
- `data/embeddings/tcn/val_embeddings.npy`: $(71, 64)$ float32 array
- `data/embeddings/tcn/test_embeddings.npy`: $(71, 64)$ float32 array
- `data/embeddings/tcn/embedding_manifest.parquet`: 481 records mapping each sequence ID to its physical event ID, target detection ID, split partition, and embedding index.

### Quarantined Superseded 4-Block Artifacts:
- `models/tcn/superseded_4block/`: Contains superseded 4-block weights, config, and logs with `QUARANTINE_NOTE.txt`.
- `data/embeddings/tcn/superseded_4block/`: Contains superseded 4-block embeddings with `QUARANTINE_NOTE.txt`.

---

## 6. Verification Test Suite Status

The scientific and regression test suite was executed:
- **`tests/test_tcn_pretraining.py`**: **15 / 15 passed** in 3.81s.
  - Verifies causality (diff = 0.0 at past timesteps), 5 residual blocks, dilations `(1, 2, 4, 8, 16)`, parameter count == 122,498, 15% masking, train-only scaler, event isolation, and bit-for-bit inference reproduction.
- **Full Project Test Suite (`tests/`)**: **129 / 129 passed** in 40.07s. Zero regressions.
