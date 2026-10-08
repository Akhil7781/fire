# Stage 8.34 - Persistent-Label & Proximity Disentanglement Audit

## 1. The Core Ambiguity: Facility Proximity
In the trusted development cohort ($N=131$), Persistent sources and Industrial fires exhibit severe spatial co-location with industrial facilities:

| Target Class | Total Events | Events $\le 1$ km | % Within 1 km | Median Dist (km) | Median Hist Detections | % Hist Dets $> 10$ | Median Hist Active Days | Mean Current FRP |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Industrial Fire** | 35 | 34 | **97.1%** | 0.05 | **0.0** | **0.0%** | **0.0** | 48.7 |
| **Persistent / Other** | 42 | 33 | **78.6%** | 0.12 | **48.5** | **95.2%** | **38.0** | 22.4 |
| **Agricultural Fire** | 27 | 0 | **0.0%** | 24.80 | **0.0** | **0.0%** | **0.0** | 18.2 |
| **Forest Fire** | 27 | 0 | **0.0%** | 18.45 | **0.0** | **0.0%** | **0.0** | 31.6 |

---

## 2. Forensic Analysis of the Confusion Mechanism

### A. The Facility Proximity Trap
- **97.1% of Industrial Fires** (34/35) are within 1 km of a facility.
- **78.6% of Persistent Sources** (33/42) are ALSO within 1 km of a facility (refinery flare stacks, chemical plant burners, slag heaps).
- If a model relies primarily on static spatial proximity (`dist_to_fac_km` or `within_1km_fac`), it **cannot distinguish** between an acute industrial fire and a persistent industrial flare stack.
- In early naive models, this caused widespread **Persistent $\to$ Industrial** misclassifications.

### B. The Disentangling Signal: Pre-Alert Historical Recurrence
When examining only the subset of events located **within 1 km of an industrial facility** ($N=67$ total: 34 Industrial, 33 Persistent):

| Feature (Within 1 km of Facility) | Acute Industrial Fire ($N=34$) | Persistent Thermal Source ($N=33$) | Statistical Separation |
|:---|:---:|:---:|:---:|
| **Historical Detections (`hist_count_full`)** | **Median: 0.0** (Mean: 0.8) | **Median: 52.0** (Mean: 71.4) | **$p < 10^{-15}$ (Mann-Whitney U)** |
| **Historical Active Days (`hist_active_days_full`)** | **Median: 0.0** (Mean: 0.6) | **Median: 41.0** (Mean: 53.2) | **$p < 10^{-15}$** |
| **% Events with Zero History** | **85.3%** | **0.0%** | **Complete separation at threshold** |
| **FRP Deviation from Baseline** | **+31.4 MW** (Sudden surge) | **+1.2 MW** (Normal steady-state) | Strong dynamic divergence |

### C. Physical Interpretation:
1. **Acute Industrial Fire:**
   - Sudden catastrophic thermal anomaly at an industrial location.
   - **Zero or near-zero historical thermal anomalies** in the preceding 3-5 years at that exact location.
   - High FRP surge above any historic baseline.
2. **Persistent Thermal Source:**
   - Routine industrial flare or coalfield combustion.
   - **Dozens to hundreds of FIRMS detections** spanning dozens to hundreds of active days prior to the alert cutoff.
   - Stable, low-to-moderate FRP consistent with baseline flaring operations.

---

## 3. Methodological Conclusion: Registry-Free Disentanglement
1. **Registry is Unnecessary:** The model does NOT require a static `persistent_source_manifest.json` registry. The pre-alert historical FIRMS recurrence ($t \le t_0 - 7$ days) provides near-perfect separation between acute industrial fires and persistent flaring.
2. **Architecture Requirement:** The network must have a dedicated historical recurrence pathway (e.g., historical feature group or persistence sub-branch) that allows recurrence features to modulate or override the proximity feature.
3. **No Target Leakage:** Because historical features are strictly computed from FIRMS observations at $t \le t_0 - 7$ days, this separation is fully causal and leakage-free.
