# Stage 8.35 - Data Sufficiency & Capacity Analysis

## 1. Sample Size vs Model Complexity Analysis
- **Total Development Samples ($N$):** **165 events** (expanded from 131)
- **Primary Neural Model:** `Architecture4_MultiTaskMLP`
- **Total Trainable Parameters:** **~11,200 parameters**
- **Effective Parameter-to-Sample Ratio:** ~68 parameters per event.

### Mitigation of Small-Sample Overfitting:
1. **Modality Group Encoders with Low Latent Dim ($D=32$):** Instead of a wide dense layer, inputs are projected into small 32-dimensional latent vectors with LayerNorm and Dropout (0.15).
2. **Auxiliary Multi-Task Supervision:** Shared representations are co-supervised by auxiliary binary persistence and 3-class acute classification tasks, multiplying effective gradient signals per sample.
3. **Weight Decay Regularization ($10^{-4}$) & Cosine Annealing:** Constrains weight norms and prevents memorization.
4. **Zero Coordinate Inputs:** The network is physically precluded from memorizing geographical coordinates.

---

## 2. Event Support per Class & per Split

| Class Name | Baseline Support | Expanded Support | % Increase | Min Outer Train Support |
|:---|:---:|:---:|:---:|:---:|
| **Industrial Fire** | 35 | 35 | +0.0% | 18 |
| **Forest Fire** | 27 | 27 | +0.0% | 18 |
| **Agricultural Fire** | 27 | **43** | **+59.3%** | **20** |
| **Persistent / Other** | 42 | **60** | **+42.9%** | **29** |
| **Total Events** | **131** | **165** | **+26.0%** | **117** |

### Verdict on Data Sufficiency:
The expanded cohort provides sufficient support ($\ge 18$ training events per class in every spatial fold) for small-capacity, heavily regularized neural architectures ($\le 20,000$ parameters). It is **not** sufficient for large transformers or deep ResNets, which would severely overfit. The current compact architecture is well-matched to dataset scale.
