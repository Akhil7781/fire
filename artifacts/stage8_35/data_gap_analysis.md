# Stage 8.35 - Formal Data Acquisition Plan & Gap Analysis

## Executive Summary
Following the Stage 8.34 forensic reconciliation, model performance limitations were conclusively shown to stem from **dataset distribution pathologies** rather than neural network capacity. 

This document details the quantitative gap analysis across the $N=131$ development cohort and defines the formal acquisition and annotation targets for Stage 8.35.

---

## 1. Class Distribution Across Geographic Regions ($N=131$)

| Region | Agricultural Fire | Forest Fire | Industrial Fire | Persistent / Other | Total Events | % Agri | % Persistent |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **North** | **23** (85.2%) | 9 (33.3%) | 6 (17.1%) | 7 (16.7%) | 45 | **51.1%** | 15.6% |
| **Central_East** | 1 (3.7%) | 8 (29.6%) | 4 (11.4%) | **22** (52.4%) | 35 | 2.9% | **62.9%** |
| **Central_West** | 3 (11.1%) | 2 (7.4%) | 8 (22.9%) | 6 (14.3%) | 19 | 15.8% | 31.6% |
| **South** | **0** (0.0%) | 8 (29.6%) | **17** (48.6%) | 7 (16.7%) | 32 | **0.0%** | 21.9% |
| **Total** | **27** | **27** | **35** | **42** | **131** | - | - |

### Core Vulnerabilities Identified:
1. **The Southern Agricultural Void:** Southern India has **zero** agricultural fire records in the development dataset, despite extensive paddy stubble burning in the Cauvery delta (Tamil Nadu), Krishna-Godavari delta (Andhra Pradesh), and sugarcane residue burning in Karnataka/Maharashtra.
2. **The Central_East Persistent Sink:** 52.4% of persistent sources are clustered in Central_East (Jharia coalfields).
3. **Severe Spatial CV Degradation:** When North is held out in spatial CV, outer training has only 4 agricultural fires, collapsing North Agricultural recall and causing North to be the worst spatial fold (Macro-F1 = 0.6358).

---

## 2. Chronological Distribution Across Years

| Year | Agricultural Fire | Forest Fire | Industrial Fire | Persistent / Other | Total Events |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 2016–2023 | 16 | 16 | 26 | **0** | 58 |
| **2024** | 4 | 4 | 5 | **36** | 49 |
| **2025** | 7 | 7 | 4 | **6** | 24 |
| **Total** | 27 | 27 | 35 | **42** | **131** |

### Core Vulnerabilities Identified:
1. **The 2016–2023 Persistent Void:** Prior to 2024, the dataset contains **zero** persistent source records.
2. **Consequence:** Forward-chaining evaluation prior to 2024 collapsed because models trained on $\le 2023$ were evaluated on 2024 where 73.5% of labels were Class 3.
3. **Opportunity:** Physical persistent thermal sources (refinery flare stacks, coalfield smoldering, steel mills) were active continuously across 2018–2023. Historical FIRMS observations from 2018, 2020, and 2022 can be retrospectively annotated without any target leakage.

---

## 3. Formal Acquisition Targets for Stage 8.35

| Acquisition Dimension | Current Support | Target Additions | Post-Expansion Target | Target Regions / Years |
|:---|:---:|:---:|:---:|:---|
| **Agricultural Fire Expansion** | 27 events (0 in South) | **+16 events** | **43 events** | South (AP, TN, Karnataka: +8), West/Central (MH, GJ, MP: +8) |
| **Persistent Historical Expansion** | 42 events (0 pre-2024) | **+18 events** | **60 events** | 2018 (+6), 2020 (+6), 2022 (+6) from documented persistent sites |
| **Total Development Cohort** | **131 events** | **+34 events** | **165 events** | Nationwide balanced representation |

---

## 4. Key Questions Answered
1. **Which class is geographically underrepresented?** Agricultural Fire (0 in South, only 1 in Central_East).
2. **Which class is temporally underrepresented?** Persistent / Other Thermal Source (0 in 2016–2023).
3. **Which class is absent from important regions?** Agricultural Fire is completely absent from Southern India.
4. **Which year ranges lack Persistent examples?** Years 2016 through 2023 lack Persistent events.
5. **Which spatial regions require additional samples?** South (Agricultural) and Central_West (Agricultural, Forest).
6. **How many additional events would materially improve each gap?** +16 Agricultural events and +18 Historical Persistent events (+34 events total) will provide genuine 4-class representation across all 4 macro-regions and multiple chronological eras.
