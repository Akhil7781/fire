# Stage 8.37 System Architecture Specification

## 1. Production Pipeline
The end-to-end operational pipeline consists of 8 interconnected stages:

1. **NASA FIRMS Sensor Ingestion:** Streams VIIRS (375m) and MODIS (1km) thermal anomalies across India.
2. **Data Sanitary Validation:** Filters coordinates, negative FRP, invalid timestamps, and duplicates (`validators.py`).
3. **Spatio-Temporal Event Clustering:** Clusters detections within $\le 3$ km and $\le 24$ hours into discrete thermal events (`event_builder.py`).
4. **Causal Feature Extraction:** Computes 41 clean features across Thermal, Industrial, Ecoregion, and Recurrence modalities (`feature_builder.py`).
5. **Frozen Neural Model Forward Pass:** Executes deterministic inference with `Architecture1_StaticMLP` (`predictor.py`).
6. **Persistence & Evidential Reasoning:** Calculates persistence level and produces human-readable explanations (`explainer.py`).
7. **Geospatial Storage:** Writes events, detections, and predictions into GIS-indexed tables (`db.py`).
8. **Visualization & Service:** Exposes REST endpoints, GeoJSON, and an interactive Leaflet web dashboard (`app.py`, `frontend/`).

---

## 2. Invariant Checklist
- **Model Checkpoint SHA-256:** `5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2` (Unchanged from Stage 8.36).
- **Preprocessing Scalers:** `models/stage8_36/preprocessing.pt` (Unchanged from Stage 8.36).
- **Feature Schema:** 41 features across 4 groups (Unchanged from Stage 8.36).
- **Registry Independence:** Verified 0 registry queries or flags.
- **Causality Invariant:** Verified 100% invariance under future observation injection.
