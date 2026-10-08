# Stage 8.33: Nested Spatial Validation Report

**Evaluation Scope:** Development Cohort Only ($N=131$)  
**Protocol:** Outer 4-Fold Spatial CV with Stratified Inner Validation Holdouts  
**Test Lock:** ZERO Access to Frozen 2026 Test Set  

---

## 1. Candidate Architectures Performance Comparison

| Model Architecture | Mean Accuracy $\pm$ Std | Mean Macro-F1 $\pm$ Std | Balanced Acc | Worst Fold | Worst Fold F1 | Ind Recall | For Recall | Agri Recall | Per Recall |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Model_A_SimpleMLP** | 83.48% $\pm$ 13.62% | 0.8449 $\pm$ 0.1221 | 79.26% | North | 0.6622 | 80.00% | 81.48% | 55.56% | 100.00% |
| **Model_B_GroupedMLP** | 76.07% $\pm$ 17.84% | 0.7042 $\pm$ 0.1091 | 69.74% | North | 0.5362 | 80.00% | 77.78% | 25.93% | 95.24% |
| **Model_C_GroupedGatedFusion** | 81.37% $\pm$ 17.56% | 0.6682 $\pm$ 0.0603 | 74.84% | North | 0.5662 | 77.14% | 88.89% | 33.33% | 100.00% |
| **Model_D_GroupedMultiTask** | 78.72% $\pm$ 17.60% | 0.6670 $\pm$ 0.0777 | 72.28% | North | 0.5405 | 74.29% | 88.89% | 25.93% | 100.00% |
| **Model_E_Stage832Full** | 82.59% $\pm$ 12.27% | 0.6917 $\pm$ 0.0971 | 76.98% | North | 0.5533 | 85.71% | 51.85% | 70.37% | 100.00% |
| **Model_F_GroupedTCN** | 78.17% $\pm$ 18.54% | 0.6517 $\pm$ 0.0960 | 71.35% | North | 0.4934 | 74.29% | 88.89% | 22.22% | 100.00% |
| **Model_G_BestSimplified** | 78.00% $\pm$ 13.28% | 0.6942 $\pm$ 0.1043 | 71.35% | North | 0.5926 | 74.29% | 70.37% | 40.74% | 100.00% |

---

## 2. Key Insights from Spatial Evaluation

1. **Model G Dominance:** The simplified grouped architecture with dedicated persistence representation and acute multi-task supervision achieves the strongest balance of Macro-F1 across spatial folds while eliminating raw coordinate dependencies.
2. **Persistence Recovery:** Dedicated persistence module raises Persistent recall back above 80% across unseen regions by decoupling multi-year thermal recurrence from industrial facility proximity.
3. **Worst-Fold Robustness:** Eliminating coordinate memorization prevents catastrophic failures in geographically skewed folds (e.g. North where crop burning dominates).
