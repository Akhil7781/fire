# Stage 8.33: Specialized Persistence Representation Analysis

**Evaluation Scope:** Development Cohort ($N=131$)  
**Protocol:** Strictly Causal ($t \le t_0 - 7$ days), Registry-Free  
**Objective:** Investigate why Persistent Recall dropped to 70% in Stage 8.32 and define a specialized neural persistence representation.

---

## 1. Root Cause of Stage 8.32 Persistent False Negatives

In Stage 8.32, persistent test events suffered false negative predictions classified as **Industrial Fire**.
Analyzing development data reveals the physical origin of this confusion:

- **14 out of 42 (33.3%)** of development persistent sources are located within **1 km** of an industrial facility (e.g. continuous flaring stacks at refineries, petrochemical complexes, and power plants).
- For true Industrial Fires, **13 out of 35 (37.1%)** are also within 1 km of an industrial facility.
- When an architecture fuses features through generic shared layers without a dedicated persistence branch, the strong spatial signal `within_1km_fac = 1` biases the network toward the acute Industrial class.
- However, their historical recurrence profiles are **diametrically opposed**:
  - Acute Industrial Fires have mean `hist_count_2km` = **7.31** (median 0), as industrial accidents are rare, acute episodes.
  - Persistent flares have mean `hist_count_2km` = **14.55** and mean `hist_active_months_full` = **7.74**.

---

## 2. Statistical Separation: Persistent vs. Acute Sources

| Feature | Persistent Mean | Industrial Mean | Forest Mean | Agricultural Mean | Cohen's $d$ (Per vs Ind) | Physical Diagnostic Meaning |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| `hist_count_2km` | 14.55 | 7.31 | 0.44 | 0.04 | **+0.47** | Multi-year thermal recurrence count |
| `hist_count_5km` | 15.02 | 9.57 | 2.3 | 0.11 | **+0.34** | Multi-year thermal recurrence count |
| `hist_active_days_full` | 12.26 | 7.29 | 0.22 | 0.04 | **+0.39** | Longitudinal operational duration |
| `hist_active_months_full` | 7.74 | 3.8 | 0.11 | 0.04 | **+0.61** | Longitudinal operational duration |
| `hist_distinct_calendar_months` | 2.4 | 1.43 | 0.11 | 0.04 | **+0.48** | Recurrence intensity distribution |
| `hist_days_since_latest` | 470.76 | 4628.82 | 8074.66 | 9380.15 | **-1.17** | Temporal recency of previous thermal detection |
| `hist_mean_frp_full` | 6.58 | 2.56 | 1.69 | 0.89 | **+1.28** | Recurrence intensity distribution |
| `hist_cv_frp_full` | 0.21 | 0.15 | 0.05 | 0.0 | **+0.23** | Recurrence intensity distribution |
| `dist_to_fac_km` | 160.02 | 59.79 | 169.86 | 135.34 | **+0.53** | Static proximity to registered industrial facility |
| `within_1km_fac` | 0.33 | 0.37 | 0.0 | 0.0 | **-0.08** | Static proximity to registered industrial facility |

---

## 3. Dedicated Neural Persistence Branch Formulation

To prevent industrial proximity features from overpowering recurrence evidence, **Model G** incorporates a dedicated persistence pathway:

```
Historical Recurrence Features (104-D)
             │
             ├───► [DedicatedPersistenceBranch] ───► Binary Logits (Acute vs Persistent)
             │                 │
             │                 └───► Latent Persistence Embedding (32-D)
             │                                   │
Current Thermal (14-D) ───► [ThermalEncoder] ───┤
Industrial Context (6-D) ─► [FacEncoder] ───────┼───► Concat & Residual MLP ───► 4-Class Logits
Ecoregion Context (3-D) ──► [EcoEncoder] ───────┤                               └───► Acute Subclass
```

### Key Architectural Advantages:
1. **Isolated Recurrence Gradient:** The persistence head enforces that the historical branch must predict persistence directly from multi-year thermal activity without contaminating from facility distance.
2. **Auxiliary Supervision:** The network learns a sharp distinction between continuous flaring stacks (`hist_count_2km > 5`) and acute structural factory fires (`hist_count_2km == 0`).
3. **Registry-Free Operation:** Derived strictly from causally available raw NASA FIRMS detections $\le t_0 - 7$ days.

---
*Generated autonomously under Stage 8.33 strict test-lock constraints.*
