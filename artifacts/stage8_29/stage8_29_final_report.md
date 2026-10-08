# Stage 8.29 Independent-Registry and Target-Proxy Robustness Audit

**Date:** October 4, 2026  
**Auditor:** Autonomous Agentic AI (Advanced Coding & Scientific Audit Team)  
**Status:** `REAL_TIME_4_CLASS_TARGET_NOT_REGISTRY_INDEPENDENT`  
**Registry Provenance:** `PROJECT_DERIVED / TEST_DERIVED (10 of 52 sources are test entities)`  
**NO_REGISTRY_H0_ACCURACY:** `78.57%`  
**FULL_H0_ACCURACY:** `96.43%`  
**Final Scientific Claim:** While the causal multimodal architecture is structurally sound and achieves 100% precision on industrial fires, 4-class real-time attribution accuracy at H0 alert-time falls from 96.43% to 78.57% (macro-F1 0.7820) when the project-derived persistent source registry is removed, demonstrating that distinguishing acute biomass fires from persistent rural thermal anomalies without an independent external registry remains below the 85% operational benchmark.

---

## 1. Executive Verdict

Stage 8.28 successfully removed explicit label leakage (`is_known_persistent = (cid == 3)`) and verified strict causal prefix construction. However, adversarial auditing revealed a critical structural vulnerability:

1. **The Persistent Source Registry is a Direct Target Proxy:**
   - 10 of the 52 entries in `persistent_source_manifest.json` are literally the exact same physical entities as the 10 persistent events evaluated in the frozen 2026 test set.
   - For all 10 test persistent events, the distance to the registry is $< 62\text{ meters}$ (mean $= 34.4\text{ m}$).
   - For all 18 acute fire events (Industrial, Forest, Agricultural), the distance is $> 79.4\text{ km}$ (mean $= 216.2\text{ km}$).
   - Therefore, the binary feature `within_1km_persistent_registry` has a **perfect Pearson correlation ($r = 1.0000$)** with ground-truth class 3.

2. **Ablation Reveals True Model Capability Without Registry:**
   - When the persistent registry feature group is removed (`NO_PERSISTENT_REGISTRY`), model performance at alert time ($H_0$) drops from **96.43% (27/28)** to **78.57% (22/28)**, and Macro-F1 drops from **0.9580** to **0.7820**.
   - **Industrial Fire attribution is completely unaffected:** All 6 industrial fires remain **100% correct (6/6, F1 = 1.0000)** because industrial fires are discriminated by physical facility proximity, thermal baseline anomalies, and infrastructure context.
   - **The collapse occurs in separating Persistent Thermal Sources from Biomass Fires:** Without the registry coordinates, 3 agricultural fires and 1 forest fire are misclassified as Persistent thermal sources (and 1 persistent source is misclassified as Agricultural).
   - This proves that the previous 96.43% score was not genuine 4-class thermal signature learning; it was identifying persistent sources via an encoded target proxy.

3. **Temporal Encoder Loss Diagnostic & Repair:**
   - In Stage 8.28, the unnormalized $\Delta T$ target had a mean squared scale of $1.34 \times 10^7$ (due to multi-year intervals up to 17,544 hours), which was **29,380 times larger** than the FRP loss ($455.8$).
   - $\Delta T$ was driving $99.97\%$ of the gradient magnitude.
   - In Stage 8.29, log1p target normalization was implemented, balancing FRP loss ($0.8785$) and $\Delta T$ loss ($1.2826$), reducing total loss from $1.36\text{M}$ to $1.0068$.

---

## 2. Persistent Source Registry Provenance

Audit of `data/reference/ds08/manifests/stage8_25/persistent_source_manifest.json` across all 52 sources:

- **Manifest Metadata:** `"version": "1.0.0", "stage": "8.25", "count": 52`.
- **Relationship to Dataset:** Exactly 52 physical events in `ds08_stage8_25_physical_events.parquet` share identical names (`EVT_825_PER_PER_SRC_01` to `52`) and coordinates.
- **Classification of Sources:**
  - **TRAIN_DERIVED:** 36 sources (69.2%) corresponding to 2016–2024 training events.
  - **VAL_DERIVED:** 6 sources (11.5%) corresponding to 2025 validation events.
  - **TEST_DERIVED:** 10 sources (19.2%) corresponding to 2026 test events (`PER_SRC_01`, `02`, `03`, `06`, `21`, `25`, `26`, `47`, `49`, `52`).
  - **INDEPENDENT_EXTERNAL:** **0 sources (0.0%)**.
- **Conclusion:** The manifest is a project-derived label artifact created concurrently with the event dataset in Stage 8.25. It cannot be used to prove generalizable 4-class attribution.

---

## 3. Target-Proxy Audit

Documented in [`registry_target_proxy_audit.csv`](file:///d:/DATA%20PREPROCESSING/artifacts/stage8_29/registry_target_proxy_audit.csv):

| Class | Count | Mean Distance to Registry | Within 1 km | Within 5 km | Spatially Associated with Test Event |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Industrial Fire** | 6 | 198.43 km | 0.0% (0/6) | 0.0% (0/6) | 0.0% (0/6) |
| **Forest Fire** | 6 | 210.68 km | 0.0% (0/6) | 0.0% (0/6) | 0.0% (0/6) |
| **Agricultural Fire** | 6 | 239.59 km | 0.0% (0/6) | 0.0% (0/6) | 0.0% (0/6) |
| **Other / Persistent** | 10 | **0.034 km (34.4 m)** | **100.0% (10/10)** | **100.0% (10/10)** | **100.0% (10/10)** |

**Mathematical Proof of Proxy:** Because `within_1km` is true if and only if `class == 3`, the feature acts as a deterministic 1-bit proxy for the target class.

---

## 4. Controlled Ablation Results at H0 Alert Time

Trained on TRAIN split only ($N=856$), validated on VAL split ($N=192$), evaluated once on the frozen 2026 independent test cohort ($N=28$):

| Model / Ablation | Input Dim | H0 Accuracy | Macro-F1 | Balanced Acc | Ind F1 | For F1 | Agr F1 | Per F1 | 95% Confidence Interval (Acc) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Stage 8.28 FULL** | 94 | **96.43%** | **0.9580** | **0.9583** | 1.0000 | 0.9231 | 0.9091 | 1.0000 | [0.8929, 1.0000] |
| **NO_PERSISTENT_REGISTRY** | 91 | **78.57%** | **0.7820** | **0.7667** | **1.0000** | **0.8000** | **0.5455** | **0.7826** | **[0.6071, 0.9286]** |
| **NO_FACILITY_REGISTRY** | 88 | 89.29% | 0.8741 | 0.8750 | 1.0000 | 0.7692 | 0.7273 | 1.0000 | [0.7848, 1.0000] |
| **NO_STATIC_REGISTRIES** | 85 | 78.57% | 0.7428 | 0.7500 | 0.8571 | 0.8000 | 0.4444 | 0.8696 | [0.6071, 0.9286] |
| **CURRENT_THERMAL_ONLY** | 5 | 82.14% | 0.7869 | 0.7917 | 0.8333 | 0.6000 | 0.7143 | 1.0000 | [0.6786, 0.9643] |
| **TEMPORAL_ONLY** | 64 | 35.71% | 0.1351 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.5405 | [0.1786, 0.5357] |
| **GEOGRAPHIC_ONLY** | 4 | 46.43% | 0.4492 | 0.4417 | 0.4000 | 0.2857 | 0.4444 | 0.6667 | [0.2857, 0.6429] |
| **NON_REGISTRY_MULTIMODAL** | 85 | 78.57% | 0.7428 | 0.7500 | 0.8571 | 0.8000 | 0.4444 | 0.8696 | [0.6071, 0.9286] |

### Key Scientific Observations:
1. **The Persistent Registry is Responsible for +17.86% Accuracy:** Removing it drops accuracy from 96.43% to 78.57%.
2. **Industrial Attribution is Robust Without Registries:** Industrial F1 remains **1.0000** in both FULL, NO_PERSISTENT_REGISTRY, and NO_FACILITY_REGISTRY (and 0.8571 when both registries are stripped).
3. **Temporal Embeddings Alone Cannot Distinguish Classes at H0:** TEMPORAL_ONLY achieves only 35.71% because at alert time $H_0$, only 1 observation is visible for 27/28 events. The GRU requires multimodal context.

---

## 5. Multi-Horizon Results Without Persistent Registry

Documented in [`no_registry_horizon_results.csv`](file:///d:/DATA%20PREPROCESSING/artifacts/stage8_29/no_registry_horizon_results.csv):

| Horizon | Accuracy | Macro-F1 | Balanced Acc | Industrial F1 | Forest F1 | Agricultural F1 | Persistent F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **H0** | 78.57% | 0.7820 | 0.7667 | 1.0000 | 0.8000 | 0.5455 | 0.7826 |
| **H1** | 78.57% | 0.7820 | 0.7667 | 1.0000 | 0.8000 | 0.5455 | 0.7826 |
| **H2** | 78.57% | 0.7820 | 0.7667 | 1.0000 | 0.8000 | 0.5455 | 0.7826 |
| **H3** | 78.57% | 0.7820 | 0.7667 | 1.0000 | 0.8000 | 0.5455 | 0.7826 |
| **H6** | 78.57% | 0.7820 | 0.7667 | 1.0000 | 0.8000 | 0.5455 | 0.7826 |
| **H12** | 78.57% | 0.7820 | 0.7667 | 1.0000 | 0.8000 | 0.5455 | 0.7826 |
| **H24** | 75.00% | 0.7275 | 0.7250 | 1.0000 | 0.7500 | 0.4444 | 0.7143 |
| **Retro** | 78.57% | 0.7513 | 0.7500 | 1.0000 | 0.8000 | 0.4444 | 0.7619 |

Across all horizons, causal performance without the persistent registry ranges between **75.00% and 78.57%**.

---

## 6. Temporal Model Diagnostic & Loss Audit

Documented in [`temporal_loss_audit.csv`](file:///d:/DATA%20PREPROCESSING/artifacts/stage8_29/temporal_loss_audit.csv):

- **Target Disparity in Stage 8.28:**
  - FRP Target: Mean $= 12.92\text{ MW}$, Std $= 21.35\text{ MW}$, MSE scale $\approx 455.85$.
  - $\Delta T$ Target (Raw Hours): Mean $= 929.64\text{ h}$, Std $= 3659.62\text{ h}$, Max $= 17,544.0\text{ h}$, MSE scale $\approx 13,392,812.29$.
  - Gradient contribution: $\Delta T$ drove **99.967%** of the loss gradient.
- **Repaired Target Normalization in Stage 8.29:**
  - Target $\Delta T_{\text{norm}} = \log(1 + \Delta T_{\text{hours}})$ (MSE scale $\approx 5.69$).
  - Target $\text{FRP}_{\text{norm}} = \log(1 + \text{FRP})$ (MSE scale $\approx 0.88$).
  - Repaired Loss: $\mathcal{L}_{\text{total}} = 1.0068$ ($\mathcal{L}_{\text{FRP}} = 0.8785$, $\mathcal{L}_{\Delta T} = 1.2826$, $\mathcal{L}_{\text{rep}} = 0.00$).
  - **Verdict:** Log-normalization resolves the numerical gradient imbalance cleanly.

---

## 7. Temporal Representation Value Test

Evaluating the incremental value of the 64D temporal GRU embedding:

- **At H0 (Alert Time):**
  - With Temporal Embedding: **96.43% Accuracy**
  - Without Temporal Embedding (Tabular Only): **89.29% Accuracy**
  - **Incremental Value at H0:** **$+7.14\%$ Accuracy** ($+2$ events classified correctly).
- **At H24 (24-Hour Horizon):**
  - With Temporal Embedding: **92.86% Accuracy**
  - Without Temporal Embedding: **89.29% Accuracy**
  - **Incremental Value at H24:** **$+3.57\%$ Accuracy** ($+1$ event classified correctly).
- **Verdict:** The temporal embedding provides a positive, measurable contribution ($+3.5\%$ to $+7.1\%$), but tabular spatial/context features remain the primary drivers.

---

## 8. Spatial Memorization & Registry Permutation Tests

1. **Test-to-Train Geographic Separation:**
   - Minimum separation: $53.2\text{ km}$.
   - Mean separation: $180.4\text{ km}$.
   - Maximum separation: $1,176.0\text{ km}$.
   - Confirms test events are not collocated with training events.
2. **Coordinate Perturbation Test:**
   - Jitter $\pm 0.02^\circ$ ($\approx 2.2\text{ km}$): Mean probability change $= 0.0001$, **0 flips out of 28**.
   - Jitter $\pm 0.05^\circ$ ($\approx 5.6\text{ km}$): Mean probability change $= 0.0002$, **0 flips out of 28**.
   - Confirms model predictions are robust to GPS/satellite georeferencing jitter.
3. **Random Registry Control:**
   - Real Registry (FULL): **96.43%**
   - NO_REGISTRY: **78.57%**
   - RANDOM_REGISTRY (52 relocated coordinates): **75.00%** (Macro-F1 = 0.7035).
   - Confirms that randomly distributed registry coordinates provide zero utility, reinforcing that the FULL model's boost was due specifically to the real registry containing the test locations.

---

## 9. Prediction Flip Analysis (FULL vs NO_REGISTRY)

Documented in [`prediction_flip_analysis.csv`](file:///d:/DATA%20PREPROCESSING/artifacts/stage8_29/prediction_flip_analysis.csv):

Exactly 6 test events (21.4%) flip prediction when the persistent registry is removed:
1. `EVT_825_FOR_FOR_EVT_2026_UK_CHAMOLI`: True Forest Fire $\rightarrow$ Flipped to Agricultural Fire.
2. `EVT_825_FOR_FOR_EVT_2026_OD_KOTGARH`: True Forest Fire $\rightarrow$ Flipped to Persistent Thermal Source.
3. `EVT_825_AGR_AGR_EVT_2026_AP_GUNTUR_RABI`: True Agricultural Fire $\rightarrow$ Flipped to Persistent Thermal Source.
4. `EVT_825_AGR_AGR_EVT_2026_BR_BUXAR_RABI`: True Agricultural Fire $\rightarrow$ Flipped to Persistent Thermal Source.
5. `EVT_825_AGR_AGR_EVT_2026_TN_THANJAVUR_KHARIF`: True Agricultural Fire $\rightarrow$ Flipped to Persistent Thermal Source.
6. `EVT_825_PER_PER_SRC_49` (Vedanta Jharsuguda): True Persistent Thermal Source $\rightarrow$ Flipped to Agricultural Fire.

### Critical Insight:
**Industrial Fires had ZERO flips (0/6).** All 6 industrial fires remained 100% correct in both models. The confusion introduced by removing the registry is strictly between rural persistent emitters (smoldering slag, small kilns) and biomass fires (crop burning, forest fires).

---

## 10. Small-Sample Uncertainty Quantification

With $N=28$ independent physical test events, every event represents $3.5714\%$ of accuracy:

| Correct Events | Total Events | Accuracy | Context / Stage |
| :---: | :---: | :---: | :--- |
| **28** | 28 | **100.00%** | Theoretical perfect score |
| **27** | 28 | **96.43%** | Stage 8.28 Verified FULL (with target proxy registry) |
| **26** | 28 | **92.86%** | Stage 8.28 H24 / Without Temporal |
| **25** | 28 | **89.29%** | Stage 8.27 reported (contaminated) / NO_FACILITY |
| **24** | 28 | **85.71%** | **Lowest integer passing the 85% benchmark** |
| **23** | 28 | **82.14%** | First failing integer below 85% |
| **22** | 28 | **78.57%** | **Stage 8.29 NO_PERSISTENT_REGISTRY (True causal baseline)** |

A shift of just 2 events moves the model from passing ($85.71\%$) to failing ($78.57\%$).

---

## 11. Comparison Across All Historical Stages

| Stage / Variant | Accuracy | Macro-F1 | Balanced Acc | Status & Scientific Validity |
| :--- | :---: | :---: | :---: | :--- |
| **Stage 8.26 Alert-Time** | 67.86% | 0.6708 | 0.6750 | Clean baseline alert-time |
| **Stage 8.26 Retrospective** | 96.43% | 0.9580 | 0.9583 | Non-causal completed-event baseline |
| **Stage 8.27 Reported** | 89.29% | 0.8741 | 0.8750 | Contaminated by `is_known_persistent = (cid==3)` |
| **Stage 8.28 Verified (FULL)** | 96.43% | 0.9580 | 0.9583 | Structurally causal, but dependent on project-derived registry |
| **Stage 8.29 NO_REGISTRY** | **78.57%** | **0.7820** | **0.7667** | **True Causal Baseline Without Target Proxy** |

---

## 12. Externalized Persistent Source Reality

In operational remote sensing, an attribution system cannot assume that every persistent source is pre-registered in an internal catalog. If an alert occurs at an uncataloged thermal anomaly, the system must rely on:
1. Multi-overpass persistence (e.g. thermal detections across days/weeks).
2. Diurnal cycle signature (day/night brightness ratio).
3. Coincident high-resolution optical imagery (Sentinel-2 chips).

Because at $H_0$ alert time only 1 observation is visible, a single-pass thermal detection without a spatial registry or optical chip is fundamentally ambiguous between a small persistent industrial emission and an acute agricultural fire.

---

## 13. Scientific Limitations

1. **Absence of Truly Independent External Registry:** India lacks an open, comprehensive, public GIS polygon database of all brick kilns, gas flares, and coal fires. The 52 sources in `persistent_source_manifest.json` were manually assembled for this project.
2. **Gated Optical Coverage at Alert Time:** Sentinel-2 L2A chips have a 5-day revisit latency. At $H_0$ alert time, optical chips are available for $< 1\%$ of acute detections.
3. **Discrete Metric Granularity:** With $N=28$, statistical power is limited. Confidence interval at $78.57\%$ spans $[60.71\%, 92.86\%]$.

---

## 14. Final Acceptance Decision

According to Section 14 acceptance rules:
- Rule A (`REAL_TIME_4_CLASS_TARGET_VERIFIED`) requires that registry provenance is independent and no target proxy remains. **FAILED.**
- Rule B (`REAL_TIME_4_CLASS_TARGET_VERIFIED_WITH_EXTERNAL_REGISTRY_DEPENDENCY`) requires an independently sourced external registry. **FAILED.**
- Rule C (`REAL_TIME_4_CLASS_TARGET_NOT_REGISTRY_INDEPENDENT`) applies when:
  *"the persistent registry is derived from target labels or target events AND removing it causes major performance collapse."*
  **SATISFIED.** (10 of 52 sources are test events; removing it drops performance from 96.43% to 78.57%, falling below the 85% threshold).
- Rule D (`CAUSAL_MODEL_VALID_BUT_TARGET_NOT_MET`) applies when:
  *"causal/no-registry performance falls below 85%."*
  **SATISFIED.** (True causal accuracy = 78.57% < 85.00%).

Therefore, the primary scientific status is:
**`REAL_TIME_4_CLASS_TARGET_NOT_REGISTRY_INDEPENDENT`**

---

STAGE_8_29_STATUS=REAL_TIME_4_CLASS_TARGET_NOT_REGISTRY_INDEPENDENT

REGISTRY_PROVENANCE=PROJECT_DERIVED / TEST_DERIVED (10 of 52 sources are test entities)

NO_REGISTRY_H0_ACCURACY=78.57%

FULL_H0_ACCURACY=96.43%

FINAL_SCIENTIFIC_CLAIM=While the causal multimodal architecture is structurally sound and achieves 100% precision on industrial fires, 4-class real-time attribution accuracy at H0 alert-time falls from 96.43% to 78.57% (macro-F1 0.7820) when the project-derived persistent source registry is removed, demonstrating that distinguishing acute biomass fires from persistent rural thermal anomalies without an independent external registry remains below the 85% operational benchmark.
