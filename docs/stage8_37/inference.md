# Inference Pipeline Specification: DS08 Causal Engine

## 1. Frozen Neural Model Details
- **Architecture:** `Architecture1_StaticMLP`
- **Framework:** PyTorch (TorchScript / CPU compatible)
- **Model Checkpoint Path:** `models/stage8_36/final_neural_model.pt`
- **Model Checkpoint SHA-256:** `5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2`
- **Parameters:** 3,244 weights and biases.

```python
net = nn.Sequential(
    nn.Linear(41, 48),
    nn.LayerNorm(48),
    nn.GELU(),
    nn.Dropout(0.15),
    nn.Linear(48, 24),
    nn.LayerNorm(24),
    nn.GELU(),
    nn.Dropout(0.15),
    nn.Linear(24, 4)
)
```

---

## 2. Preprocessing & Feature Normalization
- **File:** `models/stage8_36/preprocessing.pt`
- **Standardization Formula:**
  $$\hat{x}_{i, g} = \frac{x_{i, g} - \mu_{g}}{\sigma_{g}}$$
  where $\mu_g, \sigma_g$ are precomputed strictly on development events ($\le 2024$).
- Feature vectors are organized by 4 modality blocks:
  - `thermal_feats`: (N, 14)
  - `industrial_feats`: (N, 6)
  - `ecoregion_feats`: (N, 3)
  - `historical_feats`: (N, 18)

---

## 3. Strict Causal Constraints
1. **Observation Time Limit:** Only observations with timestamp $\le t_0$ (alert time) enter the acute thermal feature calculation.
2. **Historical Recurrence Buffer:** Pre-alert multiyear FIRMS observations must satisfy $\text{timestamp} \le t_0 - 7\text{ days}$.
3. **Registry-Free:** No access to `persistent_source_manifest.json`.
4. **Coordinate-Free:** Latitude and longitude are used solely for spatial distance calculations (facility proximity, ecoregion bounding checks, and historical neighborhood filtering), but never directly provided as neural network input features.
