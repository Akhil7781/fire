# Stage 8.32 Model Comparison Report

**Date:** October 4, 2026  
**Auditor:** Autonomous Agentic AI (Advanced Coding & Scientific Audit Team)  

---

## Benchmark Comparison Table

| Model | Neural-Only | Random Val F1 | Spatial Val F1 | Temporal Val F1 | Frozen Test Acc | Frozen Test F1 | Ind F1 | For F1 | Agr F1 | Per F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Stage 8.31 MLP + RF** | NO | 1.0 | 0.9139 | 0.9145 | **0.8571** | **0.8231** | 0.9231 | 0.7692 | 0.6 | 1.0 |
| **Stage 8.31 Static MLP** | YES | 0.9258 | 0.8699 | 0.8756 | **0.8214** | **0.7912** | 0.8889 | 0.7273 | 0.5455 | 1.0 |
| **Stage 8.32 Neural Direct 4-Class** | YES | 0.9583 | 0.8824 | 0.9093 | **N/A** | **N/A** | N/A | N/A | N/A | N/A |
| **Stage 8.32 Neural Hierarchical** | YES | 0.9182 | 0.8654 | 0.8707 | **N/A** | **N/A** | N/A | N/A | N/A | N/A |
| **Stage 8.32 Neural Multi-Task (FINAL)** | YES | 1.0 | 0.902 | 0.9476 | **0.7857** | **0.78** | 0.8 | 0.7692 | 0.7273 | 0.8235 |
