# Stage 8.25 Visual Review Package: EVT_825_FOR_FOR_EVT_2026_MH_CHANDRAPUR

**Verdict:** `CORRECT`  
**True Class:** Forest Fire (Class ID 1)  
**Predicted Class:** Forest Fire (Class ID 1)  
**Model Confidence:** 73.3%  

---

## 1. Physical Event Properties
- **Centroid Coordinates:** 20.2170° N, 79.2590° E
- **Administrative Location:** N/A, Maharashtra, India
- **Event Date:** 2026 Chronological Holdout Partition
- **Duration:** 36.0 hours
- **Peak Fire Radiative Power (FRP):** 8.5 MW
- **Mean Fire Radiative Power:** 8.5 MW
- **Associated Detections:** 1 VIIRS NOAA-20 SP observations

---

## 2. Predicted Class Probability Distribution
| Class | Probability | Visual Indicator |
|---|---|---|
| Industrial Fire | 0.1368 | ██ |
| Forest Fire | 0.7330 | ██████████████ |
| Agricultural Fire | 0.0774 | █ |
| Other Thermal / Persistent | 0.0528 | █ |

---

## 3. Ground Truth Verification & Evidence Trail
- **Statutory Evidence Source:** Maharashtra Forest Department TATR Buffer Zone Record
- **Evidence Strength:** Statutory
- **Spatial Separation Audit:** Strictly > 50.0 km from all train/val events. Zero facility overlap.
- **Label Tier:** CONFIRMED (Authoritative Ground Truth)
