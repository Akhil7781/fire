# Stage 8.25 Visual Review Package: EVT_825_AGR_AGR_EVT_2026_AP_GUNTUR_RABI

**Verdict:** `CORRECT`  
**True Class:** Agricultural Fire (Class ID 2)  
**Predicted Class:** Agricultural Fire (Class ID 2)  
**Model Confidence:** 81.0%  

---

## 1. Physical Event Properties
- **Centroid Coordinates:** 16.2992° N, 80.4502° E
- **Administrative Location:** N/A, Andhra Pradesh, India
- **Event Date:** 2026 Chronological Holdout Partition
- **Duration:** 8.0 hours
- **Peak Fire Radiative Power (FRP):** 13.4 MW
- **Mean Fire Radiative Power:** 13.4 MW
- **Associated Detections:** 1 VIIRS NOAA-20 SP observations

---

## 2. Predicted Class Probability Distribution
| Class | Probability | Visual Indicator |
|---|---|---|
| Industrial Fire | 0.0483 |  |
| Forest Fire | 0.0693 | █ |
| Agricultural Fire | 0.8101 | ████████████████ |
| Other Thermal / Persistent | 0.0723 | █ |

---

## 3. Ground Truth Verification & Evidence Trail
- **Statutory Evidence Source:** AP Agriculture Dept Field Burning Verification Log 2026
- **Evidence Strength:** High
- **Spatial Separation Audit:** Strictly > 50.0 km from all train/val events. Zero facility overlap.
- **Label Tier:** CONFIRMED (Authoritative Ground Truth)
