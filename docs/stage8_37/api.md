# REST API Specification: DS08 Attribution Service

The operational service runs via FastAPI on port 8000. Interactive Swagger documentation is available at `http://localhost:8000/docs`.

---

## Endpoints Summary

### 1. `GET /health`
Returns system status, active model version, checkpoint hash, and architecture.
- **Response `200 OK`**:
```json
{
  "status": "HEALTHY",
  "service": "DS08 Operational Attribution API",
  "model_version": "8.36_final",
  "architecture": "Architecture1_StaticMLP",
  "checkpoint_sha256": "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2",
  "pure_deep_learning": true,
  "total_tabular_features": 41,
  "timestamp": "2026-10-04T15:38:36.720271+00:00"
}
```

---

### 2. `POST /predict`
Performs real-time causal 4-class attribution on an input thermal event.
- **Request Body:** `ThermalEventInput`
```json
{
  "event_id": "EVT_SAMPLE_001",
  "centroid_lat": 18.5204,
  "centroid_lon": 73.8567,
  "event_start_time": "2026-06-01T10:30:00Z",
  "event_detection_count": 1,
  "detections": [
    {
      "detection_id": "DET_001",
      "latitude": 18.5204,
      "longitude": 73.8567,
      "acq_date": "2026-06-01",
      "acq_time": "1030",
      "acq_datetime_utc": "2026-06-01T10:30:00Z",
      "bright_ti4": 345.2,
      "bright_ti5": 298.1,
      "frp": 25.4,
      "confidence": "high",
      "satellite": "N",
      "sensor": "VIIRS",
      "daynight": "D"
    }
  ]
}
```
- **Response `200 OK`:** `PredictionOutput`

---

### 3. `POST /predict/batch`
Batch inference over a list of `ThermalEventInput` objects.
- **Response `200 OK`:** `BatchPredictionResponse` containing predictions and `processing_time_ms`.

---

### 4. `GET /events`
Lists persisted events with pagination and filters.
- **Query Parameters:**
  - `limit` (default: 50, max: 1000)
  - `offset` (default: 0)
  - `class_filter` (optional string, e.g. "Industrial Fire")
  - `min_confidence` (optional float, 0.0 to 1.0)

---

### 5. `GET /events/{event_id}`
Returns full record of a single event including predicted class, probabilities, context metrics, and constituent detections.

---

### 6. `GET /events/{event_id}/explanation`
Returns feature-grounded evidential statements explaining why the model predicted the given class.

---

### 7. `GET /events/{event_id}/history`
Returns chronological timeline of all detections associated with the event.

---

### 8. `GET /statistics`
Returns operational breakdown: total events, total detections, and counts per predicted class with mean confidence.

---

### 9. `GET /api/geojson`
Returns standard RFC 7946 GeoJSON `FeatureCollection` for map rendering.
- **Query Parameters:** `class_filter`, `min_confidence`.

---

### 10. `POST /ingest/csv`
Uploads a raw NASA FIRMS CSV file, validates detections, clusters events, runs neural inference, and updates the database.
