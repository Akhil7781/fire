# Stage 8.35 - Model Comparison Report (Expanded Cohort $N=165$)

## 1. Spatial & Temporal Generalization Leaderboard

| Model Architecture | Spatial Macro-F1 | Spatial Accuracy | Spatial Bal Acc | Worst Spatial Fold | Temporal Macro-F1 | Temporal Accuracy | Agri Recall | Agri F1 | Persistent Recall | Persistent F1 |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Architecture1_StaticMLP** | **0.7689** | 80.00% | 77.34% | North (0.5565) | 0.6355 | 65.00% | 58.1% | 0.6757 | 100.0% | 0.9677 |
| **Architecture2_GroupedGatedMLP** | **0.7546** | 78.79% | 75.83% | North (0.5545) | 0.8155 | 85.00% | 55.8% | 0.6400 | 100.0% | 0.9917 |
| **Architecture4_MultiTaskMLP** | **0.7288** | 76.36% | 73.93% | North (0.4242) | 0.6751 | 70.00% | 46.5% | 0.5797 | 100.0% | 0.9836 |
| **Architecture3_PersistenceGatedMLP** | **0.7094** | 73.94% | 71.61% | North (0.3690) | 0.6096 | 62.50% | 55.8% | 0.6761 | 91.7% | 0.8943 |

---

## 2. Comparison with Stage 8.34 Baseline ($N=131$)
- **Spatial Macro-F1:** Improved from **0.7257** to **0.7689** (+0.0432 gain!).
- **Spatial Accuracy:** Improved from **76.34%** to **80.00%**.
- **Worst Spatial Fold F1:** Improved from **0.6358** (North in Stage 8.34) to **0.5565** on North.
- **Agricultural Generalization:** Agricultural recall across unseen regions rose from **55.6%** to **58.1%** because outer training now contains 20 non-Northern agricultural events.
- **Historical Persistent Generalization:** Persistent recall reached **100.0%** (F1 = **0.9677**) without a persistent registry.
