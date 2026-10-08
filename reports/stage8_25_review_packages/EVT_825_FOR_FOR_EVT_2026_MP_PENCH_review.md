# Stage 8.25 Visual Review Package: EVT_825_FOR_FOR_EVT_2026_MP_PENCH

**Verdict:** `CORRECT`  
**True Class:** Forest Fire (Class ID 1)  
**Predicted Class:** Forest Fire (Class ID 1)  
**Model Confidence:** 73.4%  

---

## 1. Physical Event Properties
- **Centroid Coordinates:** 21.7862° N, 79.3257° E
- **Administrative Location:** N/A, Madhya Pradesh, India
- **Event Date:** 2026 Chronological Holdout Partition
- **Duration:** 36.0 hours
- **Peak Fire Radiative Power (FRP):** 23.1 MW
- **Mean Fire Radiative Power:** 23.1 MW
- **Associated Detections:** 1 VIIRS NOAA-20 SP observations

---

## 2. Predicted Class Probability Distribution
| Class | Probability | Visual Indicator |
|---|---|---|
| Industrial Fire | 0.1337 | ██ |
| Forest Fire | 0.7340 | ██████████████ |
| Agricultural Fire | 0.0798 | █ |
| Other Thermal / Persistent | 0.0525 | █ |

---

## 3. Ground Truth Verification & Evidence Trail
- **Statutory Evidence Source:** MP Forest Department Tiger Reserve Alert Register
- **Evidence Strength:** Statutory
- **Spatial Separation Audit:** Strictly > 50.0 km from all train/val events. Zero facility overlap.
- **Label Tier:** CONFIRMED (Authoritative Ground Truth)
