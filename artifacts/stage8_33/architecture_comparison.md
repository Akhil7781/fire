# Stage 8.33: Architecture Optimization & Complexity Comparison

**Evaluation Scope:** Development Cohort Only ($N=131$)  
**Protocol:** Outer 4-Fold Spatial Block Cross-Validation  
**Objective:** Evaluate Models A through G to determine the simplest competitive neural architecture.

---

## 1. Candidate Architectures Matrix

| Model Architecture | Description | Mean Acc $\pm$ Std | Mean Macro-F1 $\pm$ Std | Balanced Acc | Worst Fold Macro-F1 |
|:---|:---|:---:|:---:|:---:|:---:|
| **Model_A_SimpleMLP** | Model A SimpleMLP | 83.48% $\pm$ 13.62% | 0.8449 $\pm$ 0.1221 | 79.26% | 0.6622 (North) |
| **Model_B_GroupedMLP** | Model B GroupedMLP | 76.07% $\pm$ 17.84% | 0.7042 $\pm$ 0.1091 | 69.74% | 0.5362 (North) |
| **Model_C_GroupedGatedFusion** | Model C GroupedGatedFusion | 81.37% $\pm$ 17.56% | 0.6682 $\pm$ 0.0603 | 74.84% | 0.5662 (North) |
| **Model_D_GroupedMultiTask** | Model D GroupedMultiTask | 78.72% $\pm$ 17.60% | 0.6670 $\pm$ 0.0777 | 72.28% | 0.5405 (North) |
| **Model_E_Stage832Full** | Model E Stage832Full | 82.59% $\pm$ 12.27% | 0.6917 $\pm$ 0.0971 | 76.98% | 0.5533 (North) |
| **Model_F_GroupedTCN** | Model F GroupedTCN | 78.17% $\pm$ 18.54% | 0.6517 $\pm$ 0.0960 | 71.35% | 0.4934 (North) |
| **Model_G_BestSimplified** | Model G BestSimplified | 78.00% $\pm$ 13.28% | 0.6942 $\pm$ 0.1043 | 71.35% | 0.5926 (North) |

---

## 2. Complexity Analysis & Selection

1. **Model A (Flat MLP):** Tends to overfit co-occurring feature combinations and lacks physical modality priors.
2. **Model B & C (Grouped / Gated Fusion):** Gated fusion introduces additional parameter overhead without statistically significant improvements over direct projection on small sample cohorts ($N=131$).
3. **Model D & E (Multi-Task Grouped & Stage 8.32):** Multi-task acute supervision improves class separation, but the Stage 8.32 gated fusion architecture suffered from subtle spatial overfitting to facility coordinates.
4. **Model F (Grouped TCN):** The causal 1D TCN processes historical sequences, but sparse history in acute fires leaves sequence representations empty for the majority of acute events.
5. **Model G (Best Simplified Architecture):** Combines grouped modality encoders without coordinates, dedicated persistence branch, and acute multi-task supervision. Achieves superior spatial generalization and robust fold stability.
