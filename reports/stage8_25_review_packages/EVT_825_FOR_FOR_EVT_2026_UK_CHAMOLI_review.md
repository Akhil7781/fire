# Stage 8.25 Visual Review Package: EVT_825_FOR_FOR_EVT_2026_UK_CHAMOLI

**Verdict:** `CORRECT`  
**True Class:** Forest Fire (Class ID 1)  
**Predicted Class:** Forest Fire (Class ID 1)  
**Model Confidence:** 73.5%  

---

## 1. Physical Event Properties
- **Centroid Coordinates:** 30.5186° N, 79.4949° E
- **Administrative Location:** N/A, Uttarakhand, India
- **Event Date:** 2026 Chronological Holdout Partition
- **Duration:** 36.0 hours
- **Peak Fire Radiative Power (FRP):** 5.0 MW
- **Mean Fire Radiative Power:** 5.0 MW
- **Associated Detections:** 2 VIIRS NOAA-20 SP observations

---

## 2. Predicted Class Probability Distribution
| Class | Probability | Visual Indicator |
|---|---|---|
| Industrial Fire | 0.1346 | ██ |
| Forest Fire | 0.7350 | ██████████████ |
| Agricultural Fire | 0.0788 | █ |
| Other Thermal / Persistent | 0.0516 | █ |

---

## 3. Ground Truth Verification & Evidence Trail
- **Statutory Evidence Source:** FSI FAST 3.0 LFF Alert 2026-UK-0418 & Chamoli Forest Division
- **Evidence Strength:** Statutory
- **Spatial Separation Audit:** Strictly > 50.0 km from all train/val events. Zero facility overlap.
- **Label Tier:** CONFIRMED (Authoritative Ground Truth)
