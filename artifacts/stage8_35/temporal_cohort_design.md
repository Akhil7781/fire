# Stage 8.35 - Temporal Cohort Design & Chronological Validation Specification

## 1. Executive Summary & Design Principles
In Stage 8.34, forensic reconciliation revealed that multi-period forward chaining prior to 2024 collapsed because the original dataset contained **zero persistent source records between 2016 and 2023**.

Stage 8.35 resolved this historical discontinuity by annotating **18 genuine historical persistent events** across 2018, 2020, and 2022 from documented public industrial/geological facilities using their active historical FIRMS detections.

---

## 2. Chronological Class Distribution After Historical Expansion ($N=165$)

| Calendar Year | Agricultural Fire | Forest Fire | Industrial Fire | Persistent / Other | Total Events | Multi-Class Feasibility |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 2016 | 1 | 2 | 1 | 0 | 4 | Incomplete (No Persistent) |
| 2017 | 1 | 0 | 1 | 0 | 2 | Incomplete (No Forest/Pers) |
| **2018** | 1 | 1 | 2 | **6** | **10** | **4 / 4 Classes Present** |
| 2019 | 2 | 2 | 3 | 0 | 7 | Incomplete |
| **2020** | 2 | 2 | 5 | **6** | **15** | **4 / 4 Classes Present** |
| 2021 | 3 | 3 | 5 | 0 | 11 | Incomplete |
| **2022** | 3 | 3 | 4 | **6** | **16** | **4 / 4 Classes Present** |
| 2023 | 3 | 3 | 5 | 0 | 11 | Incomplete |
| **2024** | 4 | 4 | 5 | **36** | **49** | **4 / 4 Classes Present** |
| **2025** | **23** | 7 | 4 | **6** | **40** | **4 / 4 Classes Present** |

---

## 3. Specification of Temporal Evaluation Protocols

### Protocol A: Canonical Forward Operational Holdout (Primary Temporal Protocol)
- **Train Partition:** Events with year $\le 2024$ ($N = 125$).
  * Industrial: 31, Forest: 20, Agricultural: 20, Persistent: 54.
- **Validation Partition:** Events with year $== 2025$ ($N = 40$).
  * Industrial: 4, Forest: 7, Agricultural: 23, Persistent: 6.
- **Validity:** **100% VALID & CANONICAL**. Both train and validation partitions have robust representation across all 4 classes.

### Protocol B: Chronological Multi-Era Chaining (Historical Feasibility)
- Because 2018, 2020, 2022, 2024, and 2025 all contain Class 3, historical multi-era evaluation is now mathematically possible for eras starting in 2018.
- Chaining Rule: Never evaluate a 4-class classifier on a period that introduces an unseen class without historical training support.
