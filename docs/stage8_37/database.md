# Geospatial Database Specification: DS08 Storage Layer

## 1. Supported Database Engines
1. **SQLite (Embedded Default):** Located at `data/operational.db`. Embedded zero-dependency engine enabling standalone execution on developer workstations.
2. **PostgreSQL + PostGIS (Production Container):** Configured via `database/schema.sql` and `docker/docker-compose.yml`.

---

## 2. Table Schemas

### `thermal_events`
Stores clustered thermal event metadata and spatial geometry.
- `event_id`: VARCHAR(64) PRIMARY KEY
- `centroid_lat`: DOUBLE PRECISION
- `centroid_lon`: DOUBLE PRECISION
- `event_start_time`: TIMESTAMPTZ (t0)
- `detection_count`: INTEGER
- `geom`: GEOMETRY(Point, 4326) [PostGIS only]
- `created_at`: TIMESTAMPTZ

### `event_detections`
Stores constituent NASA FIRMS sensor detections for each event.
- `id`: SERIAL / INTEGER PRIMARY KEY
- `event_id`: VARCHAR(64) FOREIGN KEY
- `detection_id`: VARCHAR(64)
- `latitude`, `longitude`: DOUBLE PRECISION
- `acq_datetime_utc`: TIMESTAMPTZ
- `bright_ti4`, `bright_ti5`: DOUBLE PRECISION
- `frp`: DOUBLE PRECISION
- `confidence`: VARCHAR(32)
- `satellite`: VARCHAR(16)
- `sensor`: VARCHAR(16)
- `daynight`: CHAR(1)

### `event_predictions`
Stores model predictions, probability distribution, and contextual evidence.
- `prediction_id`: SERIAL / INTEGER PRIMARY KEY
- `event_id`: VARCHAR(64) UNIQUE FOREIGN KEY
- `predicted_class`: VARCHAR(64)
- `class_id`: SMALLINT
- `confidence`: DOUBLE PRECISION
- `prob_industrial`, `prob_forest`, `prob_agricultural`, `prob_persistent`: DOUBLE PRECISION
- `persistence_level`: VARCHAR(16) (LOW, MODERATE, STRONG)
- `hist_detection_count`: DOUBLE PRECISION
- `hist_active_days`: DOUBLE PRECISION
- `hist_distinct_calendar_months`: DOUBLE PRECISION
- `dist_to_facility_km`: DOUBLE PRECISION
- `nearest_facility_name`: VARCHAR(128)
- `forest_biome_score`, `agri_heartland_score`: DOUBLE PRECISION
- `explanation_json`: TEXT / JSONB
- `model_version`: VARCHAR(32)
- `checkpoint_hash`: VARCHAR(64)
- `prediction_timestamp`: TIMESTAMPTZ

---

## 3. Spatial Indexing
- PostGIS builds a GiST index on `geom` for sub-millisecond bounding box queries.
- SQLite builds B-Tree indexes on `(centroid_lat, centroid_lon)` and `event_start_time`.
