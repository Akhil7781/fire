-- Stage 8.37 Production Geospatial Schema
-- PostgreSQL + PostGIS DDL for Operational Thermal-Source Attribution

CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Table: thermal_events
CREATE TABLE IF NOT EXISTS thermal_events (
    event_id VARCHAR(64) PRIMARY KEY,
    centroid_lat DOUBLE PRECISION NOT NULL,
    centroid_lon DOUBLE PRECISION NOT NULL,
    event_start_time TIMESTAMPTZ NOT NULL,
    detection_count INTEGER NOT NULL DEFAULT 1,
    geom GEOMETRY(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(centroid_lon, centroid_lat), 4326)) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_thermal_events_geom ON thermal_events USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_thermal_events_start_time ON thermal_events(event_start_time);

-- 2. Table: event_detections
CREATE TABLE IF NOT EXISTS event_detections (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(64) REFERENCES thermal_events(event_id) ON DELETE CASCADE,
    detection_id VARCHAR(64) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    acq_datetime_utc TIMESTAMPTZ NOT NULL,
    bright_ti4 DOUBLE PRECISION NOT NULL,
    bright_ti5 DOUBLE PRECISION NOT NULL,
    frp DOUBLE PRECISION NOT NULL,
    confidence VARCHAR(32),
    satellite VARCHAR(16),
    sensor VARCHAR(16),
    daynight CHAR(1),
    geom GEOMETRY(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)) STORED
);

CREATE INDEX IF NOT EXISTS idx_event_detections_event_id ON event_detections(event_id);
CREATE INDEX IF NOT EXISTS idx_event_detections_geom ON event_detections USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_event_detections_acq_dt ON event_detections(acq_datetime_utc);

-- 3. Table: event_predictions
CREATE TABLE IF NOT EXISTS event_predictions (
    prediction_id SERIAL PRIMARY KEY,
    event_id VARCHAR(64) UNIQUE REFERENCES thermal_events(event_id) ON DELETE CASCADE,
    predicted_class VARCHAR(64) NOT NULL,
    class_id SMALLINT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    prob_industrial DOUBLE PRECISION NOT NULL,
    prob_forest DOUBLE PRECISION NOT NULL,
    prob_agricultural DOUBLE PRECISION NOT NULL,
    prob_persistent DOUBLE PRECISION NOT NULL,
    persistence_level VARCHAR(16) NOT NULL,
    hist_detection_count DOUBLE PRECISION NOT NULL,
    hist_active_days DOUBLE PRECISION NOT NULL,
    hist_distinct_calendar_months DOUBLE PRECISION NOT NULL,
    dist_to_facility_km DOUBLE PRECISION NOT NULL,
    nearest_facility_name VARCHAR(128),
    forest_biome_score DOUBLE PRECISION NOT NULL,
    agri_heartland_score DOUBLE PRECISION NOT NULL,
    explanation_json JSONB,
    model_version VARCHAR(32) NOT NULL,
    checkpoint_hash VARCHAR(64) NOT NULL,
    prediction_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_event_predictions_class ON event_predictions(predicted_class);
CREATE INDEX IF NOT EXISTS idx_event_predictions_confidence ON event_predictions(confidence);
CREATE INDEX IF NOT EXISTS idx_event_predictions_timestamp ON event_predictions(prediction_timestamp);

-- 4. View: v_operational_events_geojson
CREATE OR REPLACE VIEW v_operational_events AS
SELECT 
    e.event_id,
    e.centroid_lat,
    e.centroid_lon,
    e.event_start_time,
    e.detection_count,
    p.predicted_class,
    p.class_id,
    p.confidence,
    p.prob_industrial,
    p.prob_forest,
    p.prob_agricultural,
    p.prob_persistent,
    p.persistence_level,
    p.dist_to_facility_km,
    p.nearest_facility_name,
    p.model_version,
    e.geom
FROM thermal_events e
JOIN event_predictions p ON e.event_id = p.event_id;
