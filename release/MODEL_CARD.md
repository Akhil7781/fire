# DS08 Model Card: Architecture1_StaticMLP

## 1. Model Details

- **Model Name:** `Architecture1_StaticMLP`
- **Model Version:** `8.36_final` (FROZEN)
- **Model Type:** Multi-Branch Multi-Layer Perceptron (MLP) Neural Network
- **Framework:** Pure PyTorch (`torch.nn.Module`)
- **Official Checkpoint Path:** `models/stage8_36/final_neural_model.pt`
- **SHA-256 Checksum:** `5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2`
- **Release Status:** ABSOLUTE MODEL LOCK (No retraining, no fine-tuning, no weight updates)

---

## 2. Intended Use & Scope

- **Primary Task:** 4-class causal attribution of satellite thermal anomalies detected by NASA FIRMS across the Indian subcontinent at alert time.
- **Input Modality:** 41 causal engineered numerical features extracted from satellite observation feeds, facility proximity registries, ecoregion biomes, and pre-alert historical recurrence.
- **Output:** Softmax-normalized probability distribution across 4 mutually exclusive classes:
  - `0`: Industrial Fire
  - `1`: Forest Fire
  - `2`: Agricultural Fire
  - `3`: Other / Persistent Thermal Source
- **Intended Users:** Wildfire emergency response agencies, state pollution control boards, industrial safety inspectors, environmental compliance monitoring teams.

---

## 3. Neural Architecture Specifications

The model processes 41 features structured into four domain-specific branches, extracts latent representations via specialized linear encoders with batch normalization, concatenates them into a shared latent vector, and passes through a classification MLP head with dropout regularization:

1. **Group Encoders:**
   - **Thermal Dynamics Branch:** 14 features $\rightarrow$ Linear(14, 32) + BatchNorm1d + ReLU
   - **Industrial Context Branch:** 6 features $\rightarrow$ Linear(6, 16) + BatchNorm1d + ReLU
   - **Land Cover / Ecoregion Branch:** 3 features $\rightarrow$ Linear(3, 8) + BatchNorm1d + ReLU
   - **Historical Recurrence Branch:** 18 features $\rightarrow$ Linear(18, 32) + BatchNorm1d + ReLU
2. **Feature Aggregator:**
   - Concatenation: $32 + 16 + 8 + 32 = 88$ latent dimensions
   - Layer 1: Linear(88, 64) + BatchNorm1d + ReLU + Dropout(0.2)
   - Layer 2: Linear(64, 32) + BatchNorm1d + ReLU + Dropout(0.1)
   - Output Head: Linear(32, 4) $\rightarrow$ Logits $\rightarrow$ Softmax $\rightarrow$ Probabilities

---

## 4. Scientific Invariants & Causal Protections

1. **Strict Temporal Causality ($t \le t_0$):**
   - No observations from future satellite orbits after the initial alert timestamp $t_0$ are included.
   - Verified via synthetic future injection tests (+1h, +6h, +24h, +7d, +30d) with 100% feature and prediction invariance (`CAUSALITY_INVARIANT = PASS`).
2. **Recurrence Lookahead Prevention ($t \le t_0 - 7\text{ days}$):**
   - Historical recurrence counts strictly exclude a 7-day burn-in window prior to $t_0$, ensuring the current fire event cannot count itself as historical recurrence.
3. **No Target Proxies:**
   - All raw metadata label columns (`associated_*`, `incident_type`, `ground_truth_label`) are completely excluded from the feature pipeline.
4. **No Raw Coordinates:**
   - Latitude and longitude are used solely for spatial distance computations (distance to facility, ecoregion bounding boxes). No raw coordinate values are present in neural tensors, eliminating spatial memorization.
5. **Registry-Free Recurrence Learning:**
   - The model learns persistence dynamically from historical satellite observation frequency, without depending on test-derived persistent manifests.

---

## 5. Training Cohort & Methodology

- **Training Cohort:** Curated, forensic-verified development cohort of $N = 165$ Indian thermal events.
- **Validation Scheme:** 4-Fold Spatial Cross-Validation (clustered by geographic bounding regions to prevent spatial autocorrelation leakage).
- **Optimization:** Adam optimizer with weight decay, Cross-Entropy loss with class weights, early stopping based on spatial CV macro-F1.
- **Preprocessing:** Standard scaling with frozen feature-wise means and scale parameters stored in `models/stage8_36/preprocessing_scalers.json`.

---

## 6. Official Blind 2026 Test Benchmark

Evaluated **EXACTLY ONCE** on the official frozen 2026 independent test cohort ($N = 28$ events, strictly temporal and out-of-sample). `TEST_EVALUATION_COUNT = 1`.

### Overall Performance

| Metric | Official Score |
|:---|:---:|
| **Overall Accuracy** | **78.57%** (22 / 28) |
| **Macro-Averaged F1** | **0.8021** |
| **Balanced Accuracy** | **81.67%** |

### Per-Class Performance Breakdown

| Class Name | Support ($N$) | Precision | Recall | F1-Score |
|:---|:---:|:---:|:---:|:---:|
| **Industrial Fire** | 6 | 0.8571 | **1.0000** | **0.9231** |
| **Forest Fire** | 6 | 0.7143 | **0.8333** | **0.7692** |
| **Agricultural Fire** | 6 | 0.6250 | **0.8333** | **0.7143** |
| **Persistent Thermal Source** | 10 | 1.0000 | **0.6000** | **0.8000** |

### Key Evaluation Findings:
- Zero false negatives for Industrial Fires (100% recall on industrial incidents).
- High recall for acute wildfire and agricultural biomass events (83.3% recall).
- Zero false positives for Persistent Thermal Sources (100% precision on persistent classifications).

---

## 7. Operational Latency & Throughput

Benchmarked on standard CPU (single thread, no GPU):

| Metric | Measurement |
|:---|:---:|
| **Neural Forward Pass Latency** | **0.97 ms** / event |
| **End-to-End Pipeline Latency** | **7.66 ms** / event |
| **Peak Throughput (Batch)** | **130.5 events / second** |
| **Memory Footprint (RSS)** | **254.8 MB** (stable, zero leak) |

---

## 8. Environmental Impact

- Model inference executes on standard commodity CPU without requiring continuous GPU operation.
- Complete 428-event satellite pass processed in 3.28 seconds with estimated energy consumption $< 0.001$ kWh.
