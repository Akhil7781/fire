# DS08 REST API Documentation

The DS08 Operational System exposes a RESTful API powered by FastAPI, compliant with OpenAPI 3.0 and RFC 7946 (GeoJSON).

---

## 1. Base URL & Service Information

- **Default Local URL:** `http://127.0.0.1:8000`
- **Interactive Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc UI:** `http://127.0.0.1:8000/redoc`

---

## 2. Endpoints Overview

| Method | Path | Summary | Description |
|:---|:---|:---|:---|
| `GET` | `/health` | Health Check | Service status, frozen model hash, active database |
| `POST` | `/predict` | Single Event Inference | Causal 4-class attribution for a single thermal event |
| `POST` | `/predict/batch` | Batch Inference | Attribution for multiple thermal events simultaneously |
| `GET` | `/events` | List Ingested Events | Query ingested events with optional limit and class filters |
| `GET` | `/events/{event_id}` | Event Details | Detailed event information, centroid, detection count |
| `GET` | `/events/{event_id}/history` | Event History | Underlying raw satellite detections for an event |
| `GET` | `/events/{event_id}/explanation` | Event Explanation | Structured 4-channel evidential explanation |
| `GET` | `/statistics` | Attribution Statistics | Total counts and percentage breakdown by predicted class |
| `GET` | `/api/geojson` | GeoJSON FeatureCollection | All events formatted for GIS mapping and Leaflet |

---

## 3. Endpoint Details

### 3.1 `GET /health`
Returns service operational health and model verification hash.

#### Response (`200 OK`)
```json
{
  "status": "HEALTHY",
  "service": "DS08 Operational Attribution System",
  "version": "8.37.0",
  "frozen_model_hash": "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2",
  "model_status": "LOADED_AND_VERIFIED",
  "timestamp": "2026-10-04T15:58:34.694224+00:00"
}
```

---

### 3.2 `POST /predict`
Executes causal feature construction and forward pass for a single thermal event.

#### Request Body
```json
{
  "event_id": "EVT_TEST_001",
  "centroid_lat": 22.312,
  "centroid_lon": 73.195,
  "event_start_time": "2025-06-25T14:00:00Z",
  "event_detection_count": 2,
  "detections": [
    {
      "latitude": 22.312,
      "longitude": 73.195,
      "acq_date": "2025-06-25",
      "acq_time": "1400",
      "acq_datetime_utc": "2025-06-25T14:00:00Z",
      "bright_ti4": 345.2,
      "bright_ti5": 298.1,
      "frp": 25.4,
      "confidence": "high",
      "daynight": "D"
    }
  ]
}
```

#### Response (`200 OK`)
```json
{
  "event_id": "EVT_TEST_001",
  "centroid_lat": 22.312,
  "centroid_lon": 73.195,
  "alert_time": "2025-06-25T14:00:00Z",
  "predicted_class": "Industrial Fire",
  "class_id": 0,
  "confidence": 0.8654,
  "probability_industrial": 0.8654,
  "probability_forest": 0.0521,
  "probability_agricultural": 0.0612,
  "probability_persistent": 0.0213,
  "explanation": {
    "prediction_summary": "Model classifies event as 'Industrial Fire' with 86.5% confidence.",
    "thermal_evidence": ["Elevated fire radiative power (25.4 MW) indicates intense active combustion."],
    "recurrence_evidence": ["Sparse or absent pre-alert recurrence supports acute event."],
    "ecological_evidence": ["Located in non-forest, non-prime-agricultural transitional terrain."],
    "industrial_evidence": ["Close proximity (0.42 km) to registered facility (Vadodara Petrochemical Hub) strongly contributes to industrial attribution."]
  },
  "industrial_context": {
    "nearest_facility_name": "Vadodara Petrochemical Hub",
    "nearest_facility_distance_km": 0.42,
    "within_1km_fac": 1.0,
    "within_5km_fac": 1.0,
    "facility_baseline_frp": 5.0,
    "facility_context_available": true
  },
  "model_version": "8.36_final",
  "model_checkpoint_hash": "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2",
  "feature_schema_version": "8.36_final",
  "prediction_timestamp": "2026-10-04T15:58:35.123456+00:00"
}
```

---

### 3.3 `GET /api/geojson`
Returns an RFC 7946 compliant GeoJSON `FeatureCollection` for direct rendering in GIS tools (QGIS, ArcGIS, Mapbox, Leaflet).

#### Response (`200 OK`)
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [73.195, 22.312]
      },
      "properties": {
        "event_id": "EVT_TEST_001",
        "predicted_class": "Industrial Fire",
        "class_id": 0,
        "confidence": 0.8654,
        "p_industrial": 0.8654,
        "p_forest": 0.0521,
        "p_agricultural": 0.0612,
        "p_persistent": 0.0213,
        "alert_time": "2025-06-25T14:00:00Z",
        "detection_count": 2,
        "nearest_facility": "Vadodara Petrochemical Hub",
        "distance_to_facility_km": 0.42
      }
    }
  ]
}
```

---

## 4. Error Codes & Diagnostics

| HTTP Status | Reason | Schema / Detail |
|:---|:---|:---|
| `400 Bad Request` | Missing required payload parameters | `{"detail": "Error description"}` |
| `404 Not Found` | Requested event ID does not exist | `{"detail": "Event EVT_XYZ not found"}` |
| `422 Unprocessable Entity` | Pydantic validation failure (e.g. Lat > 90, negative FRP) | Array of validation issues with field names |
| `500 Internal Error` | Unhandled server exception | Standard error diagnostic |
