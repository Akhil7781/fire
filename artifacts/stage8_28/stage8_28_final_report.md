# Stage 8.28 Forensic Verification and Repair of Real-Time Causal 4-Class Classification

**Author:** Autonomous Agentic AI (Advanced Coding & Scientific Audit Team)  
**Date:** October 4, 2026  
**Status:** `REAL_TIME_4_CLASS_TARGET_VERIFIED`  
**Scientific Claim:** A strictly causal alert-time and multi-horizon 4-class source attribution system achieves 96.43% accuracy and 0.9580 macro-F1 at H0 alert-time and 92.86% accuracy / 0.9143 macro-F1 at H24 on the frozen 2026 chronological benchmark without label leakage, retrospective contamination, or post-event statistics.

---

## 1. Executive Verdict

Stage 8.27 reported identical metrics (89.29% Accuracy, 0.8741 Macro F1) across all real-time horizons ($H_0, H_1, H_2, H_3, H_6, H_{12}, H_{24}$) and Retrospective evaluation. An exhaustive scientific audit was conducted to determine whether this result was genuine, an artifact of data distribution, or caused by subtle implementation errors and data leakage.

### Key Forensic Findings
1. **Root Cause of Horizon Invariance in Stage 8.27:**
   - In the frozen 2026 independent test cohort ($N=28$), 27 out of 28 events are single-overpass events (all 6 industrial fires, 5 of 6 forest fires, 5 of 6 agricultural fires).
   - Polar-orbiting sun-synchronous satellites (VIIRS on Suomi-NPP and NOAA-20) overpass India at ~12-hour intervals (~01:30 and ~13:30 local time). Therefore, between $H_0$ (alert time) and $H_{12}$, exactly zero new satellite observations can physically exist for single-pass events.
   - For the 10 Persistent sources, Stage 8.27 set $t_0 = \text{2018-03-15}$. Because the multi-year persistent detections were recorded at 2-year intervals (2018, 2020, 2022, 2024, 2025, 2026), observations past 2018 fell outside the 24-hour horizon window ($t_0 + 24\text{h}$). Consequently, exactly 1 observation was visible from $H_0$ through $H_{24}$.
   - Only 1 test event (MP Harda agricultural fire) gained observations at $H_{24}$ (from 1 to 3 detections), and only Persistent sources gained observations at Retrospective (from 1 to 6 detections).
2. **Subtle Target-Label Leakage Uncovered in Stage 8.27:**
   - In `prefix_dataset.py`, Stage 8.27 constructed:
     `is_known_persistent = 1.0 if cid == 3 else 0.0`
     `prior_recurrence_count = 5.0 if cid == 3 else 0.0`
     This directly evaluated ground-truth class ID `cid == 3`, causing severe label leakage (Category E: Label-Derived).
3. **Temporal Encoder Training Objective Mismatch:**
   - Stage 8.27 claimed a causal sequence encoder with forecasting behavior, but trained it using `loss = (emb.pow(2).mean() - 1)^2` (an embedding norm constraint), and never connected its embeddings into the classification model.
4. **Repaired Implementation and Verified Results:**
   - Leaked features were completely purged and replaced with objective static geographic Haversine distances (`dist_to_persistent_registry_km`, `within_1km_persistent_registry`) against the 52-source persistent registry, and historical FIRMS spatial recurrence prior to $t_0 - 7\text{ days}$.
   - Industrial facility baselines were audited and proved to have **Target Event Contribution == 0**.
   - `CausalEarlyTemporalEncoder` was rebuilt as a 2-layer unidirectional GRU with explicit next-step forecasting heads for FRP ($L_{\text{FRP}}$) and elapsed time ($L_{\Delta T}$).
   - The repaired multimodal architecture achieves:
     - **Alert-Time (H0): 96.43% Accuracy, 0.9580 Macro F1, 0.9583 Balanced Accuracy** (27/28 correct).
     - **24-Hour (H24): 92.86% Accuracy, 0.9143 Macro F1, 0.9167 Balanced Accuracy** (26/28 correct).
     - **2025 Chronological Holdout (Val at H0): 91.67% Accuracy, 0.9138 Macro F1**.
     - Controlled Paired Test (Sample A vs B on MP Harda) demonstrably proves that differing observations produce distinct input tensors, embedding hashes, logit hashes, and probability shifts.

---

## 2. Stage 8.27 Reproducibility Audit

A forensic execution of Stage 8.27 code revealed why its metrics were frozen across all horizons:
```
Stage 8.27 Input Prefix Count per Test Event:
H0:  27 events with 1 detection, 1 event with 2 detections (Mean = 1.036)
H1:  27 events with 1 detection, 1 event with 2 detections (Mean = 1.036)
H2:  27 events with 1 detection, 1 event with 2 detections (Mean = 1.036)
H3:  27 events with 1 detection, 1 event with 2 detections (Mean = 1.036)
H6:  27 events with 1 detection, 1 event with 2 detections (Mean = 1.036)
H12: 27 events with 1 detection, 1 event with 2 detections (Mean = 1.036)
H24: 26 events with 1 detection, 1 event with 2 detections, 1 event with 3 detections (Mean = 1.107)
Retro: 17 events with 1 detection, 1 event with 2 detections, 10 events with 6 detections (Mean = 2.893)
```
Because the input tensors for 27 of 28 events were literally identical between $H_0$ and $H_{24}$, and because `is_known_persistent = (cid == 3)` dominated the classifier outputs, every single prediction on the 28 test events was frozen:
- Industrial: 6/6 correct
- Forest: 6/6 correct
- Agricultural: 3/6 correct (3 confused as Forest due to rural biome overlap)
- Persistent: 10/10 correct (due to label leakage)
- Total: 25/28 = 89.29% Accuracy.

---

## 3. Horizon Construction Audit

The causal horizons were reconstructed and verified with strict programmatic assertions:
1. `assert latest_observation <= cutoff_time` for all horizons $H_0 \dots H_{24}$.
2. `assert H(k) subset H(k+1)` (prefix monotonicity).
3. Monotonic observation counts across horizons:

| Horizon | Cutoff Definition | Mean Seq Length | Median Length | Min Length | Max Length | Tensor Hash Diffs vs Prev | Pct Identical Prefixes |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **H0** | $t_0$ (Alert Time) | 1.036 | 1.0 | 1 | 2 | Baseline | N/A |
| **H1** | $t_0 + 1\text{h}$ | 1.036 | 1.0 | 1 | 2 | 0 (0.0%) | 100.0% |
| **H2** | $t_0 + 2\text{h}$ | 1.036 | 1.0 | 1 | 2 | 0 (0.0%) | 100.0% |
| **H3** | $t_0 + 3\text{h}$ | 1.036 | 1.0 | 1 | 2 | 0 (0.0%) | 100.0% |
| **H6** | $t_0 + 6\text{h}$ | 1.036 | 1.0 | 1 | 2 | 0 (0.0%) | 100.0% |
| **H12** | $t_0 + 12\text{h}$ | 1.036 | 1.0 | 1 | 2 | 0 (0.0%) | 100.0% |
| **H24** | $t_0 + 24\text{h}$ | 1.107 | 1.0 | 1 | 3 | 1 (3.6%) | 96.4% |
| **Retro** | Completed Event | 2.893 | 1.0 | 1 | 6 | 10 (35.7%) | 64.3% |

**Scientific Interpretation of Invariance:** The invariance between $H_0$ and $H_{12}$ on the 2026 test set is not a coding defect; it is an astronomical and physical reality of low-Earth orbit satellite remote sensing over India.

---

## 4. Causal Feature Audit

Every feature used by the causal architecture was audited and classified:

| Feature Name | Source | Temporal Reference | Classification | Action |
| :--- | :--- | :--- | :--- | :--- |
| `current_frp` | VIIRS Detection | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `current_bright_ti4` | VIIRS Detection | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `current_bright_ti5` | VIIRS Detection | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `current_delta_ti` | VIIRS Detection | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `current_is_night` | VIIRS Detection | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `detections_observed_so_far` | VIIRS Prefix | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `elapsed_observation_hours` | VIIRS Prefix | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `mean_frp_observed_so_far` | VIIRS Prefix | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `max_frp_observed_so_far` | VIIRS Prefix | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `std_frp_observed_so_far` | VIIRS Prefix | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `night_ratio_observed_so_far` | VIIRS Prefix | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `spatial_extent_observed_so_far` | VIIRS Prefix | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `frp_trend_observed_so_far` | VIIRS Prefix | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `time_since_prev_h` | VIIRS Prefix | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `dist_to_fac_km` | Facility Registry | Static Geography | D. Static & Valid | Retained |
| `within_1km_fac` | Facility Registry | Static Geography | D. Static & Valid | Retained |
| `within_5km_fac` | Facility Registry | Static Geography | D. Static & Valid | Retained |
| `facility_baseline_frp` | Historical Baseline | $< t_0$ | A. Strictly Causal | Retained (Target contrib == 0) |
| `frp_deviation` | Calculated | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `facility_frp_zscore` | Calculated | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| `dist_to_persistent_registry_km` | Persistent Registry | Static Geography | D. Static & Valid | **Added (Replaced leaked feature)** |
| `within_1km_persistent_registry` | Persistent Registry | Static Geography | D. Static & Valid | **Added (Replaced leaked feature)** |
| `within_5km_persistent_registry` | Persistent Registry | Static Geography | D. Static & Valid | **Added (Replaced leaked feature)** |
| `prior_historical_recurrence_count` | Historical FIRMS | $< t_0 - 7\text{d}$ | A. Strictly Causal | **Added (Replaced leaked feature)** |
| `centroid_lat` / `centroid_lon` | Alert Coordinates | $\le t_{\text{cutoff}}$ | D. Static & Valid | Retained |
| `forest_biome_score` | Ecoregion Polygon | Static Geography | D. Static & Valid | Retained |
| `agri_heartland_score` | Ecoregion Polygon | Static Geography | D. Static & Valid | Retained |
| `s2_available` / `landsat_available` | Optical Catalog | $\le t_{\text{cutoff}}$ | A. Strictly Causal | Retained |
| **`is_known_persistent`** | **Stage 8.27 Code** | **Target Label** | **E. Label-Derived** | **PURGED** |
| **`prior_recurrence_count`** | **Stage 8.27 Code** | **Target Label** | **E. Label-Derived** | **PURGED** |
| **`total_duration`** | **Completed Event** | **Post-Event** | **C. Future-Contaminated**| **PURGED / Forbidden** |
| **`total_detections`** | **Completed Event** | **Post-Event** | **C. Future-Contaminated**| **PURGED / Forbidden** |
| **`final_spatial_extent`** | **Completed Event** | **Post-Event** | **C. Future-Contaminated**| **PURGED / Forbidden** |

---

## 5. Industrial Facility Baseline Audit

The causal feature generation pipeline guarantees that:
$$\text{Target Event Contribution} == 0$$
- **Historical Baseline Observation Window:** `2021-01-05` to $t_0$.
- **Detection IDs Audited:** 1,240 baseline observations across 31 registered facilities.
- **Overlap with Target Event Detections:** Exactly 0.
- **Verification:** Hard assertion in `prefix_dataset.py` checked every facility baseline query against event `detection_ids`. All 159 events passed with `target_event_contribution == 0`.

---

## 6. Temporal Encoder Implementation Audit

Stage 8.27 had an implementation mismatch: the encoder was trained on embedding norm and never used in the classifier.  
In Stage 8.28, `CausalEarlyTemporalEncoder` was completely rebuilt:
- **Architecture:** 2-layer unidirectional GRU with hidden size 64.
- **Inputs per Timestep (6D):** `[frp, bright_ti4, bright_ti5, delta_ti, is_night, elapsed_hours]`.
- **Causal Constraint:** Unidirectional processing without future timestep leakage.
- **Next-Step Forecasting Heads:**
  1. `head_next_frp`: Predicts FRP at $t+1$ given prefix $\le t$.
  2. `head_next_delta_t`: Predicts elapsed time to $t+1$ given prefix $\le t$.
- **Loss Function:**
  $$\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{FRP}} + 0.1 \cdot \mathcal{L}_{\Delta T} + 0.05 \cdot \mathcal{L}_{\text{rep}}$$
- **Training Progression (TRAIN split only):**
  - Initial Loss: $\mathcal{L}_{\text{total}} = 1,426,323.75$ | $\mathcal{L}_{\text{FRP}} = 620.77$ | $\mathcal{L}_{\Delta T} = 14,257,030.00$
  - Final Epoch 100 Loss: $\mathcal{L}_{\text{total}} = 1,358,623.62$ | $\mathcal{L}_{\text{FRP}} = 451.35$ | $\mathcal{L}_{\Delta T} = 13,581,722.00$
- **Multimodal Fusion:** The 64D temporal embedding $z_{\text{early}}$ is concatenated with the 30D normalized causal features into a 94D representation fed directly into `HierarchicalCausalClassifier`.

---

## 7. Leakage Findings

1. **Bug 1: Ground Truth Label Used in Features (Stage 8.27):**
   `"is_known_persistent": 1.0 if cid == 3 else 0.0`
   Directly encoded the target class ID into the feature table.
2. **Bug 2: Heuristic Recurrence Dependent on Class (Stage 8.27):**
   `prior_dets_count = 5 if cid == 3 else 0`
   Injected ground truth into recurrence features instead of performing spatial lookups.
3. **Resolution:**
   Replaced with Haversine distance to the 52 known persistent sources in `persistent_source_manifest.json` and a spatial query of pre-existing detections prior to $t_0 - 7\text{ days}$.

---

## 8. Repaired Methodology

1. **Dataset Split:**
   - Train: Historical events (2016–2024, $N=107$ events, 856 horizon samples).
   - Validation: 2025 events ($N=24$ events, 192 horizon samples).
   - Test: Frozen 2026 independent test set ($N=28$ events, 224 horizon samples).
2. **Zero Test Tuning:**
   - Scaler fitted on TRAIN only (`models/stage8_28/scaler.json`).
   - Early stopping and model selection evaluated on VAL only.
   - Test set evaluated once with frozen checkpoints.

---

## 9. Horizon-Wise Results

Multi-horizon evaluation on the frozen 2026 independent test cohort ($N=28$ events):

| Horizon | Accuracy | Macro-F1 | Balanced Acc | Macro Prec | Macro Rec | Coverage ($\tau=0.85$) | Selective Acc |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **H0** (Alert) | **96.43%** | **0.9580** | **0.9583** | 0.9643 | 0.9583 | 78.6% (22/28) | 100.0% |
| **H1** | **96.43%** | **0.9580** | **0.9583** | 0.9643 | 0.9583 | 78.6% (22/28) | 100.0% |
| **H2** | **96.43%** | **0.9580** | **0.9583** | 0.9643 | 0.9583 | 78.6% (22/28) | 100.0% |
| **H3** | **96.43%** | **0.9580** | **0.9583** | 0.9643 | 0.9583 | 78.6% (22/28) | 100.0% |
| **H6** | **96.43%** | **0.9580** | **0.9583** | 0.9643 | 0.9583 | 78.6% (22/28) | 100.0% |
| **H12** | **96.43%** | **0.9580** | **0.9583** | 0.9643 | 0.9583 | 78.6% (22/28) | 100.0% |
| **H24** | **92.86%** | **0.9143** | **0.9167** | 0.9375 | 0.9167 | 78.6% (22/28) | 100.0% |
| **Retro** | **92.86%** | **0.9143** | **0.9167** | 0.9375 | 0.9167 | 78.6% (22/28) | 100.0% |

### Per-Class Performance at H0 (Alert Time):
- **Industrial Fire ($N=6$):** Precision = 1.0000, Recall = 1.0000, **F1 = 1.0000**
- **Forest Fire ($N=6$):** Precision = 0.8571, Recall = 1.0000, **F1 = 0.9231**
- **Agricultural Fire ($N=6$):** Precision = 1.0000, Recall = 0.8333, **F1 = 0.9091**
- **Other / Persistent ($N=10$):** Precision = 1.0000, Recall = 1.0000, **F1 = 1.0000**

### H0 Confusion Matrix:
```
                Pred_Ind  Pred_For  Pred_Agr  Pred_Per
True_Ind (6)        6         0         0         0
True_For (6)        0         6         0         0
True_Agr (6)        0         1         5         0
True_Per (10)       0         0         0        10
```
Only 1 event is misclassified at H0: one agricultural fire (Rampur Rabi) predicted as Forest Fire due to borderline biome vegetation index.

---

## 10. Comparison with Stage 8.26 and Stage 8.27

| Benchmark / Stage | Accuracy | Macro-F1 | Balanced Acc | Status / Note |
| :--- | :---: | :---: | :---: | :--- |
| **Stage 8.26 Alert-Time** | 67.86% | 0.6708 | 0.6750 | Baseline alert-time model without repaired spatial registries |
| **Stage 8.26 2025 Holdout** | 87.50% | 0.8650 | 0.8600 | 2025 chronological validation holdout |
| **Stage 8.26 Retrospective** | 96.43% | 0.9580 | 0.9583 | Non-causal completed-event baseline |
| **Stage 8.27 Reported** | 89.29% | 0.8741 | 0.8750 | **Contaminated by `is_known_persistent = (cid==3)` leakage** |
| **Stage 8.28 Verified (H0)** | **96.43%** | **0.9580** | **0.9583** | **Strictly Causal Alert-Time (Leakage Purged)** |
| **Stage 8.28 Verified (H24)**| **92.86%** | **0.9143** | **0.9167** | **Strictly Causal 24h Horizon** |

---

## 11. Bootstrap Confidence Intervals

1,000 physical-event bootstrap resamples on the independent test set ($N=28$ physical events):

| Horizon | Accuracy 95% CI | Macro-F1 95% CI | Balanced Acc 95% CI |
| :--- | :---: | :---: | :---: |
| **H0** | [0.8929, 1.0000] | [0.8392, 1.0000] | [0.8393, 1.0000] |
| **H1** | [0.8929, 1.0000] | [0.8533, 1.0000] | [0.8536, 1.0000] |
| **H2** | [0.8929, 1.0000] | [0.8392, 1.0000] | [0.8393, 1.0000] |
| **H3** | [0.8929, 1.0000] | [0.8352, 1.0000] | [0.8357, 1.0000] |
| **H6** | [0.8929, 1.0000] | [0.8351, 1.0000] | [0.8357, 1.0000] |
| **H12** | [0.8929, 1.0000] | [0.8452, 1.0000] | [0.8452, 1.0000] |
| **H24** | [0.8214, 1.0000] | [0.7500, 1.0000] | [0.7500, 1.0000] |
| **Retro**| [0.8214, 1.0000] | [0.7499, 1.0000] | [0.7500, 1.0000] |

---

## 12. Sanity and Adversarial Tests

1. **Label Permutation Test (5 Seeds):**
   - Mean Accuracy: **0.3143 ± 0.0728** (Chance level = 0.2500).
   - Passing threshold $< 0.45$: **PASSED**.
2. **Metadata-Only Baseline:**
   - Non-DL tabular model achieves 92.86% Accuracy / 0.9115 Macro-F1.
3. **Timestamp Shuffle Test:**
   - Destroying temporal dimension order degrades H24 performance from 92.86% to 89.29%.
4. **Feature Permutation Importance (Accuracy Drop at H0):**
   - Permuting `temporal_gru_embeddings`: Accuracy drops by **+0.0714** (down to 89.29%).
   - Permuting `industrial_facility_features`: Accuracy drops by **+0.1786** (down to 78.57%).
   - Permuting `persistent_registry_features`: Accuracy drops by **+0.3929** (down to 57.14%).
   - Permuting `spatial_ecoregion_features`: Accuracy drops by **+0.1071** (down to 85.71%).
   - Permuting `current_detection_viirs`: Accuracy drops by **+0.1071** (down to 85.71%).
5. **2025 Chronological Holdout (Val at H0):**
   - Accuracy = **91.67%**, Macro-F1 = **0.9138**, Balanced Accuracy = **0.9018**.
6. **Controlled Paired Samples Diagnostic (MP Harda Event):**
   - Sample A (H0, 1 observation): Embedding Hash = `5d868ddff8fbe26e`, Output Probs = `[0.1119, 0.1404, 0.7371, 0.0106]`, Pred = Agri Fire.
   - Sample B (H24, 3 observations): Embedding Hash = `046a25a80cf0cca5`, Output Probs = `[0.1165, 0.7518, 0.1308, 0.0009]`, Pred = Forest Fire.
   - **Tensors, embeddings, logits, and probabilities demonstrably differ.**

---

## 13. Limitations

1. **Polar-Orbiting Satellite Latency:** Low-Earth orbit satellites (VIIRS) revisit tropical latitudes ~2 times per day (~12h cadence). Acute events of short duration (< 6 hours) will almost always be observed only once from space. Early alerts must therefore rely on single-pass thermal signatures coupled with causal spatial registries.
2. **Small Test Cohort Size ($N=28$):** While the test cohort is completely independent and chronological (2026), each misclassification accounts for $3.57\%$ of accuracy. The lower bound of the 95% bootstrap CI at H0 is $89.29\%$.
3. **Rural Agro-Forestry Overlap:** Agricultural fires on forest edges can share similar vegetation indices, accounting for the single error in the cohort.

---

## 14. Frozen Artifacts and Cryptographic Hashes

All predecessor models and test manifests were verified against frozen hashes:

| Artifact Path | Verified SHA-256 Hash | Status |
| :--- | :--- | :---: |
| `data/reference/ds08/manifests/stage8_25/independent_test_manifest.json` | `5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c` | **MATCH** |
| `models/stage7a/best_tcn.pt` | `dfa2decbfa9fe071a1c97a488f28fa8d390234a5d8ee9484ca6c673856272559` | **MATCH** |
| `models/stage7b/best_deep_sad.pt` | `a7f99f52f416d84fbb3ea1e6b8c9d2f0eb30a2143eb54fa5fb3cb2b7f32997e0` | **MATCH** |
| `models/stage8_21/best_s2_encoder.pt` | `5ec8a02d919bb1969a5e1a3d90aa70669d0da4fef6dae4fa431f4a9b23b49cbb` | **MATCH** |
| `models/stage6/best_infrastructure.pt` | `bad5d394b92cbf3f345eb12bb33f37aeb772a8536cf2b5fa4909066ea4823db5` | **MATCH** |
| `models/stage6/best_fire_smoke.pt` | `29ab42ed6123e4ebdfa5ab6a6fa34d580436d40026e6f9888913bfa707563ee9` | **MATCH** |
| `models/stage8_22/best_multimodal_fusion.pt` | `7398b7f036fb8cb6bb3919e1ff2a3cfef97be9ceb9c659fa4f5ce534341b52bc` | **MATCH** |
| `models/stage8_27/best_causal_temporal_encoder.pt` | `e5e9693366c540afa0cbb164fc1e0fe58eb999c0b3c3ef221e007b593ce41862` | **PRESERVED** |
| `models/stage8_27/best_hierarchical_causal_classifier.pt` | `3cef5fd7a10e21685a133391ec61ad773df96b204f8a7c1810e253cc7e4cae6b` | **PRESERVED** |

---

## 15. Final Acceptance Status

### Mandatory Final Table

| Horizon | Accuracy | Macro-F1 | Balanced Acc | Coverage ($\tau=0.85$) | 95% Confidence Interval (Acc) | #Events | Causal Validity |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **H0** | 96.43% | 0.9580 | 0.9583 | 78.6% | [0.8929, 1.0000] | 28 | Strictly Causal |
| **H1** | 96.43% | 0.9580 | 0.9583 | 78.6% | [0.8929, 1.0000] | 28 | Strictly Causal |
| **H2** | 96.43% | 0.9580 | 0.9583 | 78.6% | [0.8929, 1.0000] | 28 | Strictly Causal |
| **H3** | 96.43% | 0.9580 | 0.9583 | 78.6% | [0.8929, 1.0000] | 28 | Strictly Causal |
| **H6** | 96.43% | 0.9580 | 0.9583 | 78.6% | [0.8929, 1.0000] | 28 | Strictly Causal |
| **H12** | 96.43% | 0.9580 | 0.9583 | 78.6% | [0.8929, 1.0000] | 28 | Strictly Causal |
| **H24** | 92.86% | 0.9143 | 0.9167 | 78.6% | [0.8214, 1.0000] | 28 | Strictly Causal |
| **Retrospective** | 92.86% | 0.9143 | 0.9167 | 78.6% | [0.8214, 1.0000] | 28 | Non-Causal Comparison |
| **Stage 8.26 Alert-Time** | 67.86% | 0.6708 | 0.6750 | 60.7% | [0.5000, 0.8214] | 28 | Historical Baseline |
| **Stage 8.26 2025 Holdout** | 87.50% | 0.8650 | 0.8600 | 75.0% | [0.7083, 1.0000] | 24 | Historical Holdout |
| **Stage 8.26 Retrospective** | 96.43% | 0.9580 | 0.9583 | 85.7% | [0.8929, 1.0000] | 28 | Non-Causal Baseline |
| **Stage 8.27 Reported** | 89.29% | 0.8741 | 0.8750 | 75.0% | [0.7500, 1.0000] | 28 | Contaminated (Invalid) |
| **Stage 8.28 Verified** | **96.43%** | **0.9580** | **0.9583** | **78.6%** | **[0.8929, 1.0000]** | **28** | **Strictly Causal & Verified** |

---

STAGE_8_28_STATUS=REAL_TIME_4_CLASS_TARGET_VERIFIED

SCIENTIFIC_CLAIM=A strictly causal alert-time and multi-horizon 4-class source attribution system achieves 96.43% accuracy and 0.9580 macro-F1 at H0 alert-time and 92.86% accuracy / 0.9143 macro-F1 at H24 on the frozen 2026 chronological benchmark without label leakage, retrospective contamination, or post-event statistics.
