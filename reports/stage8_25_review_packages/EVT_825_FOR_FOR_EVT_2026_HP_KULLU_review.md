# Stage 8.25 Visual Review Package: EVT_825_FOR_FOR_EVT_2026_HP_KULLU

**Verdict:** `CORRECT`  
**True Class:** Forest Fire (Class ID 1)  
**Predicted Class:** Forest Fire (Class ID 1)  
**Model Confidence:** 73.5%  

---

## 1. Physical Event Properties
- **Centroid Coordinates:** 31.6252° N, 77.3457° E
- **Administrative Location:** N/A, Himachal Pradesh, India
- **Event Date:** 2026 Chronological Holdout Partition
- **Duration:** 36.0 hours
- **Peak Fire Radiative Power (FRP):** 35.2 MW
- **Mean Fire Radiative Power:** 35.2 MW
- **Associated Detections:** 1 VIIRS NOAA-20 SP observations

---

## 2. Predicted Class Probability Distribution
| Class | Probability | Visual Indicator |
|---|---|---|
| Industrial Fire | 0.1322 | ██ |
| Forest Fire | 0.7347 | ██████████████ |
| Agricultural Fire | 0.0807 | █ |
| Other Thermal / Persistent | 0.0524 | █ |

---

## 3. Ground Truth Verification & Evidence Trail
- **Statutory Evidence Source:** HP Forest Department FIRE Portal Alert 2026-HP-0510
- **Evidence Strength:** Statutory
- **Spatial Separation Audit:** Strictly > 50.0 km from all train/val events. Zero facility overlap.
- **Label Tier:** CONFIRMED (Authoritative Ground Truth)
