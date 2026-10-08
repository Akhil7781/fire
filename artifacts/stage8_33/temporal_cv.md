# Stage 8.33: Chronological Validation Report

**Evaluation Scope:** Development Cohort ($N=131$)  
**Protocol:** Strict Forward-Chaining Chronological Partitions ($t_{\text{train}} < t_{\text{val}}$)  
**Overall Temporal Accuracy:** 47.62%  
**Overall Temporal Macro-F1:** 0.4840  
**Overall Temporal Balanced Accuracy:** 64.29%  

---

## Chronological Split Results

| Split | Target Year | Train Size | Val Size | Accuracy | Macro-F1 | Balanced Acc |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `2022_to_2023` | 2023 | 47 | 11 | 72.73% | 0.5897 | 66.67% |
| `2023_to_2024` | 2024 | 58 | 49 | 24.49% | 0.2890 | 68.75% |
| `2024_to_2025` | 2025 | 107 | 24 | 83.33% | 0.8183 | 83.04% |

---
*Temporal causality strictly verified: no future data permitted in training.*
