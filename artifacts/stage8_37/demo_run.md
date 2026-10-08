# Stage 8.37 — End-to-End Operational Demonstration Run

**Run Date:** 2026-10-04T15:41:41.533108+00:00  
**System Status:** OPERATIONAL INTEGRATION VERIFIED  
**Model Architecture:** `Architecture1_StaticMLP` (SHA-256: `5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2`)

---

## 1. Execution Steps

- 1. Ingested 6 NASA FIRMS thermal anomaly observations.
- 2. Validated spatial coordinates, positive FRP, channel brightness temperatures, and timestamps.
- 3. Spatiotemporal clustering constructed 4 discrete thermal events.
- 4 & 5. Extracted 41 clean causal features and executed frozen neural inference for 4 events.
- 6. Persisted events, detections, and probabilities to geospatial database.
- 7. Generated GeoJSON FeatureCollection with 54 features.
- 8. Selected event 'EVT_20260601_89E8E7A0' for detailed operational inspection.
- 9. Class Attribution: Other / Persistent Thermal Source (Confidence: 40.8%) [Ind: 22.2%, For: 17.7%, Agr: 19.3%, Pers: 40.8%]
- 10. Historical Recurrence Evidence: Level=STRONG, Historical Count=41.0, Active Months=5.0
- 11. Contextual Evidence: Nearest Facility='Chincholi MIDC Industrial Park, Solapur' at 0.12 km. Forest Score=0.0, Agri Score=0.0
- 12. Explanation Summary: Model classifies event as 'Other / Persistent Thermal Source' with 40.8% confidence (probabilities: Ind=22.2%, For=17.7%, Agr=19.3%, Pers=40.8%).

---

## 2. Event Prediction Summary Table

| Event ID | Centroid (Lat, Lon) | Predicted Class | Confidence | Industrial % | Forest % | Agricultural % | Persistent % | Persistence Evidence | Nearest Facility Dist |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `EVT_20260601_89E8E7A0` | (17.659, 75.907) | **Other / Persistent Thermal Source** | 40.8% | 22.2% | 17.7% | 19.3% | 40.8% | STRONG | 0.12 km |
| `EVT_20260601_3E26A6C1` | (30.451, 78.101) | **Agricultural Fire** | 40.6% | 11.7% | 31.1% | 40.6% | 16.6% | LOW | 115.35 km |
| `EVT_20260601_51AC9519` | (29.850, 75.950) | **Forest Fire** | 39.3% | 13.1% | 39.3% | 35.7% | 11.8% | LOW | 99.55 km |
| `EVT_20260601_E5174174` | (22.450, 82.750) | **Forest Fire** | 45.1% | 15.4% | 45.1% | 30.5% | 9.0% | LOW | 294.77 km |

---

## 3. Sample Event Deep-Dive (`EVT_20260601_89E8E7A0`)

### Attribution: **Other / Persistent Thermal Source** (Confidence: 40.8%)

#### Feature-Grounded Evidential Statements:
- **Thermal:** Elevated fire radiative power (38.1 MW) indicates intense active combustion.
- **Thermal:** Daytime detection is consistent with diurnal burning schedules.
- **Thermal:** High channel brightness differential (ΔTI = 48.5 K) indicates strong sub-pixel thermal anomaly.
- **Recurrence:** Strong multi-year recurrence (41 pre-alert detections across 5 distinct calendar months) strongly supports persistent/industrial thermal anomaly.
- **Recurrence:** Last pre-alert detection occurred 71 days prior to alert cutoff.
- **Ecological:** Located in non-forest, non-prime-agricultural transitional terrain.
- **Industrial:** Close proximity (0.12 km) to registered facility (Chincholi MIDC Industrial Park, Solapur) strongly contributes to industrial attribution.

---

## 4. Operational Invariant Verification
- Model loaded from frozen Stage 8.36 package without modification or retraining.
- Features strictly causality-constrained (t <= t0 for acute, t <= t0 - 7d for historical).
- Output probabilities strictly sum to 1.0.
- Full GeoJSON and REST endpoints verified.
