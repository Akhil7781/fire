# Stage 8.25 Visual Review Package: EVT_825_AGR_AGR_EVT_2026_UP_RAMPUR_RABI

**Verdict:** `CORRECT`  
**True Class:** Agricultural Fire (Class ID 2)  
**Predicted Class:** Agricultural Fire (Class ID 2)  
**Model Confidence:** 81.0%  

---

## 1. Physical Event Properties
- **Centroid Coordinates:** 28.7527° N, 79.1852° E
- **Administrative Location:** N/A, Uttar Pradesh, India
- **Event Date:** 2026 Chronological Holdout Partition
- **Duration:** 8.0 hours
- **Peak Fire Radiative Power (FRP):** 15.1 MW
- **Mean Fire Radiative Power:** 15.1 MW
- **Associated Detections:** 1 VIIRS NOAA-20 SP observations

---

## 2. Predicted Class Probability Distribution
| Class | Probability | Visual Indicator |
|---|---|---|
| Industrial Fire | 0.0479 |  |
| Forest Fire | 0.0692 | █ |
| Agricultural Fire | 0.8103 | ████████████████ |
| Other Thermal / Persistent | 0.0726 | █ |

---

## 3. Ground Truth Verification & Evidence Trail
- **Statutory Evidence Source:** UP Agriculture Dept Stubble Verification Register 2026
- **Evidence Strength:** High
- **Spatial Separation Audit:** Strictly > 50.0 km from all train/val events. Zero facility overlap.
- **Label Tier:** CONFIRMED (Authoritative Ground Truth)
