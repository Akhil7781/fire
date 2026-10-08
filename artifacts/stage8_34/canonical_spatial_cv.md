# Stage 8.34 - Canonical Spatial Cross-Validation Report

## Protocol
- **Dataset:** Trusted Development Cohort ($N=131$)
- **Validation:** Outer 4-Fold Macro-Region Holdouts (North, Central_East, Central_West, South)
- **Primary Selection Metric:** Nested Spatial CV Macro-F1
- **Test Lock:** FROZEN 2026 TEST COHORT UNTOUCHED ($N=28$, Eval Count = 0)

## Performance Leaderboard

| Model Architecture | DL Only? | Mean Spatial Macro-F1 | Overall Spatial Macro-F1 | Overall Accuracy | Balanced Acc | Worst Fold | Worst Fold F1 | Ind F1 | For F1 | Agr F1 | Per F1 |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Architecture4_MultiTaskMLP** | Yes | 0.7089 $\pm$ 0.0872 | **0.7257** | 76.34% | 72.57% | North | 0.6358 | 0.8529 | 0.5397 | 0.5333 | 0.9767 |
| **Architecture2_GroupedGatedMLP** | Yes | 0.7397 $\pm$ 0.1665 | **0.7083** | 74.81% | 71.38% | South | 0.5622 | 0.8286 | 0.5758 | 0.4651 | 0.9639 |
| **Architecture1_StaticMLP** | Yes | 0.7121 $\pm$ 0.1358 | **0.7026** | 74.05% | 70.21% | South | 0.5898 | 0.8182 | 0.5161 | 0.5217 | 0.9545 |
| **Logistic_Regression_Diag** | Diagnostic | 0.6972 $\pm$ 0.1145 | **0.6902** | 72.52% | 69.44% | North | 0.5625 | 0.8065 | 0.5797 | 0.4444 | 0.9302 |
| **Architecture3_PersistenceGatedMLP** | Yes | 0.6649 $\pm$ 0.1729 | **0.6545** | 68.70% | 65.90% | North | 0.4888 | 0.6970 | 0.5672 | 0.5000 | 0.8539 |
| **Architecture5_CausalTCN_MLP** | Yes | 0.6172 $\pm$ 0.1125 | **0.6455** | 67.94% | 65.16% | North | 0.4934 | 0.6441 | 0.5507 | 0.4783 | 0.9091 |
| **Random_Forest_Diag** | Diagnostic | 0.6332 $\pm$ 0.0994 | **0.6255** | 67.94% | 63.65% | North | 0.5057 | 0.7541 | 0.5143 | 0.2791 | 0.9545 |
