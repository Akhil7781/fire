# Stage 8.25 Visual Review Package: EVT_825_AGR_AGR_EVT_2026_RJ_KOTA_RABI

**Verdict:** `CORRECT`  
**True Class:** Agricultural Fire (Class ID 2)  
**Predicted Class:** Agricultural Fire (Class ID 2)  
**Model Confidence:** 81.0%  

---

## 1. Physical Event Properties
- **Centroid Coordinates:** 25.1790° N, 75.8300° E
- **Administrative Location:** N/A, Rajasthan, India
- **Event Date:** 2026 Chronological Holdout Partition
- **Duration:** 8.0 hours
- **Peak Fire Radiative Power (FRP):** 24.8 MW
- **Mean Fire Radiative Power:** 24.8 MW
- **Associated Detections:** 1 VIIRS NOAA-20 SP observations

---

## 2. Predicted Class Probability Distribution
| Class | Probability | Visual Indicator |
|---|---|---|
| Industrial Fire | 0.0480 |  |
| Forest Fire | 0.0694 | █ |
| Agricultural Fire | 0.8105 | ████████████████ |
| Other Thermal / Persistent | 0.0721 | █ |

---

## 3. Ground Truth Verification & Evidence Trail
- **Statutory Evidence Source:** Rajasthan Agriculture Dept Kota Division Register
- **Evidence Strength:** High
- **Spatial Separation Audit:** Strictly > 50.0 km from all train/val events. Zero facility overlap.
- **Label Tier:** CONFIRMED (Authoritative Ground Truth)
