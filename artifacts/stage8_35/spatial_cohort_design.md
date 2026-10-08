# Stage 8.35 - Geographic Cohort Design & Spatial Validation Specification

## 1. Executive Summary & Design Principles
Following Stage 8.35 data expansion, the development cohort was increased from $N=131$ to **$N=165$ events**.

The primary objective of this redesign was to eliminate the catastrophic spatial void in Southern and Western India for Agricultural fires, while ensuring that all 4 outer spatial folds contain robust multi-class training and validation support.

---

## 2. Expanded Regional Class Representation ($N=165$)

| Geographic Macro-Region | Agricultural Fire | Forest Fire | Industrial Fire | Persistent / Other | Total Events | Class Completeness |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **North** (Lat $\ge 26^\circ$) | 23 | 9 | 6 | 10 | **48** | **4 / 4 Classes** |
| **Central_East** ($20^\circ-26^\circ$, Lon $\ge 78^\circ$) | 1 | 8 | 4 | 31 | **44** | **4 / 4 Classes** |
| **Central_West** ($20^\circ-26^\circ$, Lon $< 78^\circ$) | 10 | 2 | 8 | 12 | **32** | **4 / 4 Classes** |
| **South** (Lat $< 20^\circ$) | **9** | 8 | 17 | 7 | **41** | **4 / 4 Classes** |
| **Total Nationwide** | **43** | **27** | **35** | **60** | **165** | **All 4 Classes Robust** |

---

## 3. Impact on Outer Spatial Cross-Validation

### The Breakthrough on Fold 0 (Holdout: North)
- **Baseline Stage 8.34 Outer Train:** When North was held out, outer training had only **4 agricultural fires** across all of Central and South India. The model could not learn generalizable agricultural patterns, collapsing North Agricultural recall and making North the worst spatial fold (Macro-F1 = 0.6358).
- **Expanded Stage 8.35 Outer Train:** Outer training now contains **20 agricultural fires** ($10$ in Central_West, $9$ in South, $1$ in Central_East).
- **Benefit:** For the first time, a model evaluated on Northern India has been trained on a diverse corpus of 20 non-Northern agricultural events (paddy stubble, sugarcane trash, cotton stalks).

### The Breakthrough on Fold 3 (Holdout: South)
- **Baseline Stage 8.34 Outer Val:** South had **0 agricultural fires**, meaning Southern agricultural generalization was unmeasurable.
- **Expanded Stage 8.35 Outer Val:** South now contains **9 agricultural fires** (Cauvery delta, Krishna-Godavari delta, Tungabhadra basin, Kolhapur sugarcane), allowing rigorous cross-regional validation.

---

## 4. Minimum Support per Spatial Fold
In the expanded design:
- Every outer validation partition has $\ge 32$ events.
- Every outer training partition has $\ge 117$ events.
- Minimum training support for any class in any fold:
  * Industrial Fire: $\ge 18$ events
  * Forest Fire: $\ge 18$ events
  * Persistent Source: $\ge 29$ events
  * Agricultural Fire: $\ge 20$ events (even when North is held out!)
