# Stage 8.25 Visual Review Package: EVT_825_AGR_AGR_EVT_2026_TN_THANJAVUR_KHARIF

**Verdict:** `CORRECT`  
**True Class:** Agricultural Fire (Class ID 2)  
**Predicted Class:** Agricultural Fire (Class ID 2)  
**Model Confidence:** 81.0%  

---

## 1. Physical Event Properties
- **Centroid Coordinates:** 10.7795° N, 79.1300° E
- **Administrative Location:** N/A, Tamil Nadu, India
- **Event Date:** 2026 Chronological Holdout Partition
- **Duration:** 8.0 hours
- **Peak Fire Radiative Power (FRP):** 13.7 MW
- **Mean Fire Radiative Power:** 13.7 MW
- **Associated Detections:** 1 VIIRS NOAA-20 SP observations

---

## 2. Predicted Class Probability Distribution
| Class | Probability | Visual Indicator |
|---|---|---|
| Industrial Fire | 0.0479 |  |
| Forest Fire | 0.0693 | █ |
| Agricultural Fire | 0.8099 | ████████████████ |
| Other Thermal / Persistent | 0.0728 | █ |

---

## 3. Ground Truth Verification & Evidence Trail
- **Statutory Evidence Source:** Tamil Nadu Agriculture Dept Delta Monitoring Division
- **Evidence Strength:** High
- **Spatial Separation Audit:** Strictly > 50.0 km from all train/val events. Zero facility overlap.
- **Label Tier:** CONFIRMED (Authoritative Ground Truth)
