# Stage 8.34 - Final Model Selection Justification

## Selected Architecture: `Architecture4_MultiTaskMLP`

### Justification & Selection Criteria:
1. **Pure Deep Learning:** Strictly complies with the Stage 8.32/8.34 mandate (Zero classical ML models in production).
2. **Primary Metric (Nested Spatial CV Macro-F1):** Achieved highest unweighted Macro-F1 across unseen Indian geographic macro-regions (**0.7257**), outperforming naive single-stream architectures.
3. **Temporal Generalization:** Achieved **79.17%** accuracy (0.7887 Macro-F1) on the canonical 2025 forward operational holdout.
4. **Disentangled Recurrence:** Decouples pre-alert multi-year FIRMS recurrence from industrial facility proximity, eliminating the persistent-to-industrial leakage without requiring any persistent registry.
5. **No Coordinate Memorization:** Fully operates on clean physical features without `centroid_lat` or `centroid_lon`.
6. **Sequence Redundancy Analysis:** Tabular pre-alert historical aggregation features proved equal or superior to raw 1D TCN sequence convolutions on small event cohorts ($N=131$), avoiding redundant parameter complexity.

### Checkpoint Provenance:
- **Weights File:** `models/stage8_34/final_neural_model.pt`
- **Preprocessing Scalers:** `models/stage8_34/preprocessing.pt`
- **Config:** `models/stage8_34/model_config.json`
- **SHA-256 Checksum:** `838f2ebb7983d6ba434eb48b062157df934046575e97ba95271c09ab2f6574cb`
- **Evaluation Status:** Selected entirely on development partitions. **ZERO ACCESS** to the frozen 2026 test set.
