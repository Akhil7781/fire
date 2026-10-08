# Stage 8.34 - Model Comparison Report (Spatial & Temporal)

| Model Name | DL Only? | Spatial Macro-F1 | Spatial Accuracy | Spatial Bal Acc | Worst Spatial Fold | Temporal Macro-F1 | Temporal Accuracy | Persistent F1 | Industrial F1 |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Architecture4_MultiTaskMLP** | Yes | **0.7257** | 76.34% | 72.57% | North (0.6358) | 0.7887 | 79.17% | 0.9767 | 0.8529 |
| **Architecture2_GroupedGatedMLP** | Yes | **0.7083** | 74.81% | 71.38% | South (0.5622) | 0.8633 | 87.50% | 0.9639 | 0.8286 |
| **Architecture1_StaticMLP** | Yes | **0.7026** | 74.05% | 70.21% | South (0.5898) | 0.7518 | 75.00% | 0.9545 | 0.8182 |
| **Logistic_Regression_Diag** | Diagnostic | **0.6902** | 72.52% | 69.44% | North (0.5625) | 0.7665 | 79.17% | 0.9302 | 0.8065 |
| **Architecture3_PersistenceGatedMLP** | Yes | **0.6545** | 68.70% | 65.90% | North (0.4888) | 0.6952 | 70.83% | 0.8539 | 0.6970 |
| **Architecture5_CausalTCN_MLP** | Yes | **0.6455** | 67.94% | 65.16% | North (0.4934) | 0.6557 | 66.67% | 0.9091 | 0.6441 |
| **Random_Forest_Diag** | Diagnostic | **0.6255** | 67.94% | 63.65% | North (0.5057) | 0.8187 | 83.33% | 0.9545 | 0.7541 |
