# Stage 8.25 Visual Review Package: EVT_825_AGR_AGR_EVT_2026_BR_BUXAR_RABI

**Verdict:** `CORRECT`  
**True Class:** Agricultural Fire (Class ID 2)  
**Predicted Class:** Agricultural Fire (Class ID 2)  
**Model Confidence:** 81.0%  

---

## 1. Physical Event Properties
- **Centroid Coordinates:** 25.5595° N, 84.0091° E
- **Administrative Location:** N/A, Bihar, India
- **Event Date:** 2026 Chronological Holdout Partition
- **Duration:** 8.0 hours
- **Peak Fire Radiative Power (FRP):** 17.7 MW
- **Mean Fire Radiative Power:** 17.7 MW
- **Associated Detections:** 1 VIIRS NOAA-20 SP observations

---

## 2. Predicted Class Probability Distribution
| Class | Probability | Visual Indicator |
|---|---|---|
| Industrial Fire | 0.0483 |  |
| Forest Fire | 0.0691 | █ |
| Agricultural Fire | 0.8103 | ████████████████ |
| Other Thermal / Persistent | 0.0723 | █ |

---

## 3. Ground Truth Verification & Evidence Trail
- **Statutory Evidence Source:** Bihar Agriculture Department Stubble Monitoring Cell
- **Evidence Strength:** High
- **Spatial Separation Audit:** Strictly > 50.0 km from all train/val events. Zero facility overlap.
- **Label Tier:** CONFIRMED (Authoritative Ground Truth)
