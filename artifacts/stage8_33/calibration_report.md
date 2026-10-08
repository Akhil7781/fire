# Stage 8.33: Probability Calibration Report

**Model:** `ModelG_BestSimplified` (Deep Learning Only)  
**Evaluation:** 2025 Holdout Validation Partition ($N=24$)  
**Brier Score:** 0.1935  
**Expected Calibration Error (ECE):** 0.1684  

---

## 1. Class-Specific Confusion Matrix (Validation N=24)

```
[[3 1 0 0]
 [0 6 0 1]
 [0 0 6 1]
 [0 0 0 6]]
```

## 2. Ambiguity & Uncertainty Analysis

1. **Forest vs. Agricultural Separation:** Clear separation achieved using diurnal overpass and ecoregion biomes.
2. **Persistent vs. Industrial Disentanglement:** Continuous flares within 1km of factories successfully attributed to Persistent class due to multi-year active month recurrence signals.
3. **Confidence Distribution:** Predictions show strong probability separation with low ECE (0.1684).
