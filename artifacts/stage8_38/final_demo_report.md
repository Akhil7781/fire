# Stage 8.38 — Final Real NASA FIRMS Demonstration Report

**Demonstration Timestamp:** 2026-10-04T15:57:47.234607+00:00  
**Sensor Platform:** NASA FIRMS VIIRS NOAA-20 Satellite  
**Input Data:** Real non-test satellite observations (June 25–29, 2025)  
**Total Detections Ingested:** 619 (0 deduplicated)  
**Total Thermal Events Clustered:** 428  
**Model Architecture:** `Architecture1_StaticMLP` (SHA-256: `5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2`)  

---

## 1. Class Attribution Distribution (MODEL PREDICTIONS)

*Note: The following counts reflect **MODEL ATTRIBUTION PREDICTIONS** produced by the frozen neural model, NOT confirmed ground truth.*

| Attribution Class | Predicted Event Count | Percentage of Total Events |
|:---|:---:|:---:|
| **Industrial Fire** | **50** | 11.7% |
| **Forest Fire** | **73** | 17.1% |
| **Agricultural Fire** | **305** | 71.3% |
| **Persistent / Other Thermal Source** | **0** | 0.0% |
| **Total Events** | **428** | 100.0% |

---

## 2. Representative Operational Inference Examples

### Event: `EVT_20250625_0E4094F5`
- **Attribution Label (MODEL PREDICTION):** **Industrial Fire** (Confidence: 39.4%)
- **Location:** Lat 26.959, Lon 93.693
- **Alert Timestamp (t0):** 2025-06-25 06:44:00+00:00
- **Probability Breakdown:**
  - Industrial: 39.4%
  - Forest: 36.2%
  - Agricultural: 18.6%
  - Persistent / Other: 5.8%
- **Historical Recurrence Evidence:**
  - Recurrence Level: **LOW**
  - Historical Pre-Alert Count: 0
  - Active Calendar Months: 0
  - Days Since Latest History: 9999.0 days
- **Contextual Signals:**
  - Nearest Registered Facility: IOCL Barauni Refinery (783.71 km)
  - Forest Biome Score: 1.0
  - Agricultural Heartland Score: 0.0
- **Attribution Explanation:**
  - *Summary:* Model classifies event as 'Industrial Fire' with 39.4% confidence (probabilities: Ind=39.4%, For=36.2%, Agr=18.6%, Pers=5.8%).
  - *Thermal Evidence:* Elevated fire radiative power (162.5 MW) indicates intense active combustion.; Daytime detection is consistent with diurnal burning schedules.; High channel brightness differential (ΔTI = 38.3 K) indicates strong sub-pixel thermal anomaly.
  - *Recurrence Evidence:* Sparse or absent pre-alert recurrence (0 historical detections) supports acute, non-persistent event.
  - *Ecological Evidence:* Located within recognized Indian forest biome (Western Ghats / Central Highlands / NE / Himalayas / Odisha).
  - *Industrial Evidence:* Distant from known industrial facilities (783.7 km to nearest facility), rendering industrial facility source unlikely.

### Event: `EVT_20250625_36FD93BE`
- **Attribution Label (MODEL PREDICTION):** **Forest Fire** (Confidence: 40.7%)
- **Location:** Lat 29.040, Lon 93.067
- **Alert Timestamp (t0):** 2025-06-25 06:44:00+00:00
- **Probability Breakdown:**
  - Industrial: 12.3%
  - Forest: 40.7%
  - Agricultural: 31.7%
  - Persistent / Other: 15.3%
- **Historical Recurrence Evidence:**
  - Recurrence Level: **LOW**
  - Historical Pre-Alert Count: 0
  - Active Calendar Months: 0
  - Days Since Latest History: 9999.0 days
- **Contextual Signals:**
  - Nearest Registered Facility: IOCL Barauni Refinery (802.17 km)
  - Forest Biome Score: 1.0
  - Agricultural Heartland Score: 0.0
- **Attribution Explanation:**
  - *Summary:* Model classifies event as 'Forest Fire' with 40.7% confidence (probabilities: Ind=12.3%, For=40.7%, Agr=31.7%, Pers=15.3%).
  - *Thermal Evidence:* Moderate fire radiative power (13.9 MW) observed at alert timestamp.; Daytime detection is consistent with diurnal burning schedules.; High channel brightness differential (ΔTI = 35.8 K) indicates strong sub-pixel thermal anomaly.
  - *Recurrence Evidence:* Sparse or absent pre-alert recurrence (0 historical detections) supports acute, non-persistent event.
  - *Ecological Evidence:* Located within recognized Indian forest biome (Western Ghats / Central Highlands / NE / Himalayas / Odisha).
  - *Industrial Evidence:* Distant from known industrial facilities (802.2 km to nearest facility), rendering industrial facility source unlikely.

### Event: `EVT_20250625_6AEF88BE`
- **Attribution Label (MODEL PREDICTION):** **Agricultural Fire** (Confidence: 41.4%)
- **Location:** Lat 22.369, Lon 91.379
- **Alert Timestamp (t0):** 2025-06-25 06:43:00+00:00
- **Probability Breakdown:**
  - Industrial: 15.0%
  - Forest: 22.7%
  - Agricultural: 41.4%
  - Persistent / Other: 20.9%
- **Historical Recurrence Evidence:**
  - Recurrence Level: **LOW**
  - Historical Pre-Alert Count: 0
  - Active Calendar Months: 0
  - Days Since Latest History: 9999.0 days
- **Contextual Signals:**
  - Nearest Registered Facility: Haldia Petrochemicals Complex (340.72 km)
  - Forest Biome Score: 0.0
  - Agricultural Heartland Score: 0.0
- **Attribution Explanation:**
  - *Summary:* Model classifies event as 'Agricultural Fire' with 41.4% confidence (probabilities: Ind=15.0%, For=22.7%, Agr=41.4%, Pers=20.9%).
  - *Thermal Evidence:* Low fire radiative power (4.2 MW) typical of localized or smoldering thermal source.; Daytime detection is consistent with diurnal burning schedules.; High channel brightness differential (ΔTI = 46.9 K) indicates strong sub-pixel thermal anomaly.
  - *Recurrence Evidence:* Sparse or absent pre-alert recurrence (0 historical detections) supports acute, non-persistent event.
  - *Ecological Evidence:* Located in non-forest, non-prime-agricultural transitional terrain.
  - *Industrial Evidence:* Distant from known industrial facilities (340.7 km to nearest facility), rendering industrial facility source unlikely.


---

## 3. Real-World Execution Pipeline Verification
1. **Raw FIRMS Ingestion:** Validated and parsed standard NASA VIIRS SP format without error.
2. **Causal Integrity:** Features extracted strictly at alert time t0. Multi-year recurrence queries respected t0 - 7 days cutoff.
3. **Inference Latency:** Average inference latency was < 10 ms per event.
4. **GIS Persistence:** All 619 detections and clustered events successfully stored in database with geometry.
