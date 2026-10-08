# Stage 8.25 Visual Review Package: EVT_825_PER_PER_SRC_06

**Verdict:** `CORRECT`  
**True Class:** Other Thermal Source/Persistent Non-Biomass Thermal Source (Class ID 3)  
**Predicted Class:** Other Thermal Source/Persistent Non-Biomass Thermal Source (Class ID 3)  
**Model Confidence:** 94.3%  

---

## 1. Physical Event Properties
- **Centroid Coordinates:** 16.7848° N, 82.2549° E
- **Administrative Location:** N/A, Andhra Pradesh, India
- **Event Date:** 2026 Chronological Holdout Partition
- **Duration:** 8760.0 hours
- **Peak Fire Radiative Power (FRP):** 8.9 MW
- **Mean Fire Radiative Power:** 6.3 MW
- **Associated Detections:** 6 VIIRS NOAA-20 SP observations

---

## 2. Predicted Class Probability Distribution
| Class | Probability | Visual Indicator |
|---|---|---|
| Industrial Fire | 0.0173 |  |
| Forest Fire | 0.0172 |  |
| Agricultural Fire | 0.0229 |  |
| Other Thermal / Persistent | 0.9426 | ██████████████████ |

---

## 3. Ground Truth Verification & Evidence Trail
- **Statutory Evidence Source:** VIIRS Nightfire (VNF) & World Bank GGFR
- **Evidence Strength:** Statutory
- **Spatial Separation Audit:** Strictly > 50.0 km from all train/val events. Zero facility overlap.
- **Label Tier:** CONFIRMED (Authoritative Ground Truth)
