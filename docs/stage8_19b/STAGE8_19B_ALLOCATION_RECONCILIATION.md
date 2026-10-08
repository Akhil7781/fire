# Stage 8.19B — Stratum Allocation Reconciliation & Industrial Sample Limitations

## Executive Summary

This document provides complete, transparent accounting of the 250-chip DS08 dataset roster across all design iterations (Stage 8.18, Stage 8.18A, Stage 8.19A, and Stage 8.19B). It reconciles initial planning quotas with empirical remote sensing realities, documents the exact shortfall reallocation, and establishes the formal scientific limitations of the acute industrial fire sample.

---

## 1. Full Multi-Stage Stratum Allocation Reconciliation

The table below reconciles the stratum allocations from initial planning to the authoritative Manifest v3:

| Stratum ID | Stratum Name / Description | Stage 8.18 Planning Target | Stage 8.18A Revised Target | Manifest v2 (8.19A) Count | Manifest v3 (8.19B) Count | Delta vs Original 8.18 Target | Reallocation Status & Rationale |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **STR-1** | Confirmed Acute Industrial Fires | 15 | 10 | 10 | **10** | **-5 chips** | **Empirical Shortfall (-5):** 2025 nationwide search yielded only 8 viable incidents with clear S2 overpasses; DEC-U1 added 2 verified 2024 incidents ($8 + 2 = 10$). Remaining 5 slots reallocated to STR-2 per Stage 8.18 Section 6 contingency. |
| **STR-2** | Persistent Non-Biomass Thermal Sources | 30 | 35 | 35 | **35** | **+5 chips** | **Reallocation Inflow (+5):** Absorbed the 5-chip shortfall from Stratum 1 to maintain $N=250$ dataset quota while preserving high-temperature industrial thermal modeling. |
| **STR-3** | Active Forest Wildfires | 55 | 55 | 55 | **55** | **0 chips** | **Target Achieved:** Fully sampled across diverse Indian forest biomes (Western Ghats, Central forests, Northeast). |
| **STR-4** | Agricultural Crop Residue Burns | 55 | 55 | 55 | **55** | **0 chips** | **Target Achieved:** Fully sampled across Rabi and Kharif agricultural cycles (Indo-Gangetic plain and Deccan plateau). |
| **STR-5** | Industrial Negative Controls | 40 | 40 | 40 | **40** | **0 chips** | **Target Achieved:** Sampled from major clear-sky non-burning industrial complexes and refineries across all 5 zones. |
| **STR-6** | Natural & Agri Negative Controls | 40 | 40 | 40 | **40** | **0 chips** | **Target Achieved:** Sampled from clear forest tracts, fallow agricultural lands, and invariant background tiles. |
| **STR-7** | Pilot Benchmark Cohort (Frozen) | 15 | 15 | 15 | **15** | **0 chips** | **Immutable Reference Set:** Unchanged, held-out reference calibration set (`ds08_pilot_v1`). |
| **Total** | **Comprehensive DS08 Dataset** | **250** | **250** | **250** | **250** | **0 chips** | **100% Mathematically Reconciled across all stages.** |

### Verification of Reallocation Implementation:
- The shortfall of 5 chips in Stratum 1 was formally anticipated in **Stage 8.18 Sampling Protocol Section 6** (*"Contingency for Stratum 1: If clear S2 imagery is available for only $k < 15$ events, DO NOT FABRICATE additional events... Reallocate remaining $15 - k$ slots to Stratum 2"*).
- The final manifest (v3) **actually and strictly implements** this reallocation: Stratum 1 contains exactly 10 candidate chips, and Stratum 2 contains exactly 35 candidate chips.
- Zero synthetic records, fabricated coordinates, or phantom scenes were introduced.

---

## 2. Decoupled Taxonomy: Candidate Stratum vs. Confirmed Label

To prevent circular reasoning, label leakage, and evaluation bias, the schema enforces absolute decoupling between the four data-level concepts:

```
+-------------------------------------------------------------------------------------------------------+
|                                    FOUR-LEVEL TAXONOMY SEPARATION                                     |
+-------------------------------------------------------------------------------------------------------+
| 1. CANDIDATE STRATUM       : Discovery source & sampling balance category (e.g. STR-1, STR-3).        |
| 2. EXPECTED TARGET CLASS   : Prior hypothesis based on external alerts/registries (e.g. "Forest Fire"). |
| 3. HUMAN-CONFIRMED LABEL   : Authoritative ground truth established ONLY via double-blind adjudication|
|                              (null for all 235 expansion candidates in v3).                           |
| 4. ANNOTATION STATUS       : Workflow lifecycle state ("UNLABELED_CANDIDATE" for all 235 expansion).  |
+-------------------------------------------------------------------------------------------------------+
```

### Invariants Certified in Manifest v3:
- For all 235 expansion candidates:
  - `human_confirmed_label = null`
  - `confirmed_bounding_boxes = []`
  - `annotation_status = "UNLABELED_CANDIDATE"`
- No candidate's stratum or expected class is ever presented as a verified ground-truth label.
- Machine learning models trained on DS08 are strictly prohibited from evaluating against `expected_target_class`.

---

## 3. Critical Limitations of the Industrial Sample (Stratum 1)

The industrial fire detection problem is the most challenging task in the project. The 10 candidate scenes in Stratum 1 have fundamental scientific limitations that must be explicitly acknowledged:

### 3.1 Small Number of Independent Physical Incidents
- The sample comprises **only 10 independent physical ground incidents** across the entire Indian subcontinent for the 2024–2025 observation window.
- In statistics and machine learning, an $N=10$ sample of rare events provides limited statistical power to estimate false-negative rates or high-confidence bounding box variance.
- **Strict Anti-Inflation Policy:** Each of the 10 candidates represents a distinct physical incident. We do **not** artificially inflate the sample count by extracting multiple overlapping chips from the same factory or multiple temporal passes from the same incident.

### 3.2 Severe Geographic and Sectoral Skew
- **Geographic Imbalance:**
  - Western Region (Maharashtra & Gujarat): **5 incidents** (50.0%) — heavily concentrated in coastal chemical clusters (Dombivli, Tarapur, Dahej, Halol, Roha).
  - Central Region (MP & AP): **3 incidents** (30.0%) — Harda fireworks, Vizag API pharma, Bhandara munitions.
  - Northern Region (Haryana & HP): **2 incidents** (20.0%) — Panipat polymer, Baddi formulation.
  - Southern & Eastern Regions: **0 incidents** (0.0%).
- **Sectoral Imbalance:** The sample is dominated by chemical synthesis, pharmaceutical manufacturing, and explosives storage. Heavy metallurgy, oil refining, and power generation acute fire disasters are not represented due to zero verified qualifying incidents with clear overpasses during the window.

### 3.3 Domain & Temporal Shift (2024 vs. 2025)
- Under **DEC-U1**, two incidents from 2024 (`NDMA_2024_HARDA_FIRECRACKERS` and `SEBI_2024_DAHEJ_BHARAT_RASAYAN`) were incorporated.
- **Potential Sensor Shift:** Sentinel-2C was launched on September 5, 2024, and operationalized in late 2024 / 2025. 2024 acquisitions originate exclusively from Sentinel-2A and Sentinel-2B, whereas 2025 scenes include Sentinel-2C overpasses.
- **Seasonal & Climatic Differences:** Harda occurred in winter (February 2024); Dahej occurred in pre-monsoon spring (March 2024). Variations in atmospheric aerosols, land surface temperature, and soil background may induce subtle domain shift.

### 3.4 Feasibility / Calibration Set vs. Broad Generalization
- **Scientific Conclusion:** Stratum 1 in DS08 constitutes a **feasibility proof-of-concept and benchmark calibration dataset**, **NOT** a broad-generalization training cohort.
- Results obtained on Stratum 1 cannot support claims of universal industrial fire detection across all global industrial archetypes without further external domain validation.
