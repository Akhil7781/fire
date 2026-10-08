"""Stage 8.37 Geospatial Database Layer.

Provides local SQLite and PostgreSQL/PostGIS persistence for thermal events,
detections, and official 4-class attribution predictions.
Generates valid GeoJSON FeatureCollections for map visualization.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sqlite3
from typing import List, Dict, Any, Optional, Tuple

from src.stage8_37.inference.schemas import ThermalEventInput, PredictionOutput

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
DB_DIR = PROJECT_ROOT / "data"
SQLITE_DB_PATH = DB_DIR / "operational.db"

class DatabaseManager:
    """Geospatial persistence manager."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or SQLITE_DB_PATH
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes database tables and indexes."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 1. thermal_events
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS thermal_events (
                event_id TEXT PRIMARY KEY,
                centroid_lat REAL NOT NULL,
                centroid_lon REAL NOT NULL,
                event_start_time TEXT NOT NULL,
                detection_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_start_time ON thermal_events(event_start_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_coords ON thermal_events(centroid_lat, centroid_lon)")

            # 2. event_detections
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                detection_id TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                acq_datetime_utc TEXT NOT NULL,
                bright_ti4 REAL NOT NULL,
                bright_ti5 REAL NOT NULL,
                frp REAL NOT NULL,
                confidence TEXT,
                satellite TEXT,
                sensor TEXT,
                daynight TEXT,
                FOREIGN KEY(event_id) REFERENCES thermal_events(event_id) ON DELETE CASCADE
            )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dets_event_id ON event_detections(event_id)")

            # 3. event_predictions
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_predictions (
                prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                predicted_class TEXT NOT NULL,
                class_id INTEGER NOT NULL,
                confidence REAL NOT NULL,
                prob_industrial REAL NOT NULL,
                prob_forest REAL NOT NULL,
                prob_agricultural REAL NOT NULL,
                prob_persistent REAL NOT NULL,
                persistence_level TEXT NOT NULL,
                hist_detection_count REAL NOT NULL,
                hist_active_days REAL NOT NULL,
                hist_distinct_calendar_months REAL NOT NULL,
                dist_to_facility_km REAL NOT NULL,
                nearest_facility_name TEXT,
                forest_biome_score REAL NOT NULL,
                agri_heartland_score REAL NOT NULL,
                explanation_json TEXT,
                model_version TEXT NOT NULL,
                checkpoint_hash TEXT NOT NULL,
                prediction_timestamp TEXT NOT NULL,
                FOREIGN KEY(event_id) REFERENCES thermal_events(event_id) ON DELETE CASCADE
            )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_preds_class ON event_predictions(predicted_class)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_preds_conf ON event_predictions(confidence)")

            # 4. event_proximity (Stage 8.42)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_proximity (
                event_id TEXT PRIMARY KEY,
                nearest_industry_name TEXT,
                nearest_industry_lat REAL,
                nearest_industry_lon REAL,
                distance_to_industry_m REAL,
                distance_to_industry_km REAL,
                nearest_school_name TEXT,
                nearest_school_lat REAL,
                nearest_school_lon REAL,
                distance_to_school_m REAL,
                distance_to_school_km REAL,
                school_place_id TEXT,
                nearest_hospital_name TEXT,
                nearest_hospital_lat REAL,
                nearest_hospital_lon REAL,
                distance_to_hospital_m REAL,
                distance_to_hospital_km REAL,
                hospital_place_id TEXT,
                nearest_village_name TEXT,
                nearest_village_lat REAL,
                nearest_village_lon REAL,
                distance_to_village_m REAL,
                distance_to_village_km REAL,
                village_place_id TEXT,
                village_match_type TEXT,
                village_status TEXT,
                proximity_provider TEXT,
                proximity_calculated_at TEXT,
                proximity_status TEXT,
                FOREIGN KEY(event_id) REFERENCES thermal_events(event_id) ON DELETE CASCADE
            )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prox_event_id ON event_proximity(event_id)")

            conn.commit()
            logger.info("Database tables initialized successfully.")

    def save_event(self, event: Any):
        """Persists a thermal event and its underlying detections."""
        now = datetime.now(timezone.utc).isoformat()
        if isinstance(event, dict):
            ev_id = event["event_id"]
            lat = event["centroid_lat"]
            lon = event["centroid_lon"]
            start_time = event["event_start_time"]
            count = event.get("event_detection_count") or event.get("detection_count", 1)
            dets = event.get("detections", [])
        else:
            ev_id = event.event_id
            lat = event.centroid_lat
            lon = event.centroid_lon
            start_time = event.event_start_time
            count = event.event_detection_count
            dets = getattr(event, "detections", [])

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO thermal_events (
                event_id, centroid_lat, centroid_lon, event_start_time, detection_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (ev_id, lat, lon, start_time, count, now))

            for det in dets:
                if isinstance(det, dict):
                    d_id = det.get("detection_id") or f"D_{det.get('latitude')}_{det.get('longitude')}"
                    d_lat = det.get("latitude")
                    d_lon = det.get("longitude")
                    d_dt = det.get("acq_datetime_utc")
                    d_ti4 = det.get("bright_ti4")
                    d_ti5 = det.get("bright_ti5")
                    d_frp = det.get("frp")
                    d_conf = det.get("confidence")
                    d_sat = det.get("satellite")
                    d_sen = det.get("sensor")
                    d_dn = det.get("daynight")
                else:
                    d_id = det.detection_id or f"D_{det.latitude}_{det.longitude}"
                    d_lat = det.latitude
                    d_lon = det.longitude
                    d_dt = det.acq_datetime_utc
                    d_ti4 = det.bright_ti4
                    d_ti5 = det.bright_ti5
                    d_frp = det.frp
                    d_conf = det.confidence
                    d_sat = det.satellite
                    d_sen = det.sensor
                    d_dn = det.daynight

                cursor.execute("""
                INSERT OR IGNORE INTO event_detections (
                    event_id, detection_id, latitude, longitude, acq_datetime_utc,
                    bright_ti4, bright_ti5, frp, confidence, satellite, sensor, daynight
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (ev_id, d_id, d_lat, d_lon, d_dt, d_ti4, d_ti5, d_frp, d_conf, d_sat, d_sen, d_dn))
            conn.commit()

    def save_prediction(self, pred: Any):
        """Persists a prediction record."""
        if isinstance(pred, dict):
            ev_id = pred["event_id"]
            pred_cls = pred["predicted_class"]
            cls_id = pred.get("class_id", 0)
            conf = pred.get("confidence", 0.0)
            p_ind = pred.get("prob_industrial", 0.0)
            p_for = pred.get("prob_forest", 0.0)
            p_agr = pred.get("prob_agricultural", 0.0)
            p_per = pred.get("prob_persistent", 0.0)
            p_lvl = pred.get("persistence_level", "LOW")
            h_cnt = pred.get("hist_detection_count", 0)
            h_days = pred.get("hist_active_days", 0)
            h_m = pred.get("hist_distinct_calendar_months", 0)
            d_fac = pred.get("dist_to_facility_km")
            n_fac = pred.get("nearest_facility_name")
            f_bio = pred.get("forest_biome_score", 0.0)
            a_hrt = pred.get("agri_heartland_score", 0.0)
            expl = json.dumps(pred.get("explanation", {}))
            m_ver = pred.get("model_version", "1.0")
            c_hash = pred.get("checkpoint_hash", "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2")
            p_time = pred.get("prediction_timestamp", datetime.now(timezone.utc).isoformat())
        else:
            ev_id = pred.event_id
            pred_cls = pred.predicted_class
            cls_id = pred.class_id
            conf = pred.confidence
            p_ind = pred.probability_industrial
            p_for = pred.probability_forest
            p_agr = pred.probability_agricultural
            p_per = pred.probability_persistent
            p_lvl = pred.persistence_evidence.level
            h_cnt = pred.persistence_evidence.historical_detection_count
            h_days = pred.persistence_evidence.historical_active_days
            h_m = pred.persistence_evidence.distinct_calendar_months
            d_fac = pred.industrial_context.nearest_facility_distance_km
            n_fac = pred.industrial_context.nearest_facility_name
            f_bio = pred.ecoregion_context.forest_biome_score
            a_hrt = pred.ecoregion_context.agri_heartland_score
            expl = json.dumps(pred.explanation.model_dump())
            m_ver = pred.model_version
            c_hash = pred.model_checkpoint_hash
            p_time = pred.prediction_timestamp

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO event_predictions (
                event_id, predicted_class, class_id, confidence,
                prob_industrial, prob_forest, prob_agricultural, prob_persistent,
                persistence_level, hist_detection_count, hist_active_days,
                hist_distinct_calendar_months, dist_to_facility_km, nearest_facility_name,
                forest_biome_score, agri_heartland_score, explanation_json,
                model_version, checkpoint_hash, prediction_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ev_id, pred_cls, cls_id, conf,
                p_ind, p_for, p_agr, p_per,
                p_lvl, h_cnt, h_days, h_m, d_fac, n_fac,
                f_bio, a_hrt, expl, m_ver, c_hash, p_time
            ))
            conn.commit()

    def save_batch(self, events: List[ThermalEventInput], predictions: List[PredictionOutput]):
        """Persists multiple events and predictions inside a single SQLite transaction."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for event in events:
                cursor.execute("""
                INSERT OR REPLACE INTO thermal_events (
                    event_id, centroid_lat, centroid_lon, event_start_time, detection_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id, event.centroid_lat, event.centroid_lon,
                    event.event_start_time, event.event_detection_count, now
                ))
                for det in event.detections:
                    cursor.execute("""
                    INSERT OR IGNORE INTO event_detections (
                        event_id, detection_id, latitude, longitude, acq_datetime_utc,
                        bright_ti4, bright_ti5, frp, confidence, satellite, sensor, daynight
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.event_id, det.detection_id or f"D_{det.latitude}_{det.longitude}",
                        det.latitude, det.longitude, det.acq_datetime_utc,
                        det.bright_ti4, det.bright_ti5, det.frp, det.confidence,
                        det.satellite, det.sensor, det.daynight
                    ))

            for pred in predictions:
                explanation_json = json.dumps(pred.explanation.model_dump())
                cursor.execute("""
                INSERT OR REPLACE INTO event_predictions (
                    event_id, predicted_class, class_id, confidence,
                    prob_industrial, prob_forest, prob_agricultural, prob_persistent,
                    persistence_level, hist_detection_count, hist_active_days,
                    hist_distinct_calendar_months, dist_to_facility_km, nearest_facility_name,
                    forest_biome_score, agri_heartland_score, explanation_json,
                    model_version, checkpoint_hash, prediction_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pred.event_id, pred.predicted_class, pred.class_id, pred.confidence,
                    pred.probability_industrial, pred.probability_forest,
                    pred.probability_agricultural, pred.probability_persistent,
                    pred.persistence_evidence.level,
                    pred.persistence_evidence.historical_detection_count,
                    pred.persistence_evidence.historical_active_days,
                    pred.persistence_evidence.distinct_calendar_months,
                    pred.industrial_context.nearest_facility_distance_km,
                    pred.industrial_context.nearest_facility_name,
                    pred.ecoregion_context.forest_biome_score,
                    pred.ecoregion_context.agri_heartland_score,
                    explanation_json,
                    pred.model_version, pred.model_checkpoint_hash,
                    pred.prediction_timestamp
                ))
            conn.commit()
            logger.info(f"Batch saved {len(events)} events and {len(predictions)} predictions in single transaction.")

    def save_proximity_batch(self, records: List[Tuple[str, Dict[str, Any]]]):
        """Persists multiple proximity analysis records inside a single SQLite transaction."""
        if not records:
            return
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for event_id, prox in records:
                cursor.execute("""
                INSERT OR REPLACE INTO event_proximity (
                    event_id,
                    nearest_industry_name, nearest_industry_lat, nearest_industry_lon,
                    distance_to_industry_m, distance_to_industry_km,
                    nearest_school_name, nearest_school_lat, nearest_school_lon,
                    distance_to_school_m, distance_to_school_km, school_place_id,
                    nearest_hospital_name, nearest_hospital_lat, nearest_hospital_lon,
                    distance_to_hospital_m, distance_to_hospital_km, hospital_place_id,
                    nearest_village_name, nearest_village_lat, nearest_village_lon,
                    distance_to_village_m, distance_to_village_km, village_place_id,
                    village_match_type, village_status,
                    proximity_provider, proximity_calculated_at, proximity_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id,
                    prox.get("nearest_industry_name"), prox.get("nearest_industry_lat"), prox.get("nearest_industry_lon"),
                    prox.get("distance_to_industry_m"), prox.get("distance_to_industry_km"),
                    prox.get("nearest_school_name"), prox.get("nearest_school_lat"), prox.get("nearest_school_lon"),
                    prox.get("distance_to_school_m"), prox.get("distance_to_school_km"), prox.get("school_place_id"),
                    prox.get("nearest_hospital_name"), prox.get("nearest_hospital_lat"), prox.get("nearest_hospital_lon"),
                    prox.get("distance_to_hospital_m"), prox.get("distance_to_hospital_km"), prox.get("hospital_place_id"),
                    prox.get("nearest_village_name"), prox.get("nearest_village_lat"), prox.get("nearest_village_lon"),
                    prox.get("distance_to_village_m"), prox.get("distance_to_village_km"), prox.get("village_place_id"),
                    prox.get("village_match_type"), prox.get("village_status"),
                    prox.get("proximity_provider"), prox.get("proximity_calculated_at"), prox.get("proximity_status")
                ))
            conn.commit()

    def save_proximity(self, event_id: str, prox: Dict[str, Any]):
        """Persists or updates infrastructure and settlement proximity analysis for an event."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO event_proximity (
                event_id,
                nearest_industry_name, nearest_industry_lat, nearest_industry_lon,
                distance_to_industry_m, distance_to_industry_km,
                nearest_school_name, nearest_school_lat, nearest_school_lon,
                distance_to_school_m, distance_to_school_km, school_place_id,
                nearest_hospital_name, nearest_hospital_lat, nearest_hospital_lon,
                distance_to_hospital_m, distance_to_hospital_km, hospital_place_id,
                nearest_village_name, nearest_village_lat, nearest_village_lon,
                distance_to_village_m, distance_to_village_km, village_place_id,
                village_match_type, village_status,
                proximity_provider, proximity_calculated_at, proximity_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                prox.get("nearest_industry_name"), prox.get("nearest_industry_lat"), prox.get("nearest_industry_lon"),
                prox.get("distance_to_industry_m"), prox.get("distance_to_industry_km"),
                prox.get("nearest_school_name"), prox.get("nearest_school_lat"), prox.get("nearest_school_lon"),
                prox.get("distance_to_school_m"), prox.get("distance_to_school_km"), prox.get("school_place_id"),
                prox.get("nearest_hospital_name"), prox.get("nearest_hospital_lat"), prox.get("nearest_hospital_lon"),
                prox.get("distance_to_hospital_m"), prox.get("distance_to_hospital_km"), prox.get("hospital_place_id"),
                prox.get("nearest_village_name"), prox.get("nearest_village_lat"), prox.get("nearest_village_lon"),
                prox.get("distance_to_village_m"), prox.get("distance_to_village_km"), prox.get("village_place_id"),
                prox.get("village_match_type"), prox.get("village_status"),
                prox.get("proximity_provider"), prox.get("proximity_calculated_at"), prox.get("proximity_status")
            ))
            conn.commit()

    def get_proximity(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves proximity analysis record for an event."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM event_proximity WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def clear_database(self):
        """Clears all operational events, detections, predictions, and proximity records."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM event_proximity")
            cursor.execute("DELETE FROM event_detections")
            cursor.execute("DELETE FROM event_predictions")
            cursor.execute("DELETE FROM thermal_events")
            conn.commit()
            logger.info("Operational database cleared successfully.")

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single event with its prediction, detections, and proximity context."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT e.*, p.predicted_class, p.class_id, p.confidence,
                   p.prob_industrial, p.prob_forest, p.prob_agricultural, p.prob_persistent,
                   p.persistence_level, p.hist_detection_count, p.hist_active_days, p.hist_distinct_calendar_months,
                   p.dist_to_facility_km, p.nearest_facility_name,
                   p.forest_biome_score, p.agri_heartland_score, p.explanation_json,
                   p.model_version, p.checkpoint_hash, p.prediction_timestamp,
                   pr.nearest_industry_name, pr.nearest_industry_lat, pr.nearest_industry_lon,
                   pr.distance_to_industry_m, pr.distance_to_industry_km,
                   pr.nearest_school_name, pr.nearest_school_lat, pr.nearest_school_lon,
                   pr.distance_to_school_m, pr.distance_to_school_km, pr.school_place_id,
                   pr.nearest_hospital_name, pr.nearest_hospital_lat, pr.nearest_hospital_lon,
                   pr.distance_to_hospital_m, pr.distance_to_hospital_km, pr.hospital_place_id,
                   pr.nearest_village_name, pr.nearest_village_lat, pr.nearest_village_lon,
                   pr.distance_to_village_m, pr.distance_to_village_km, pr.village_place_id,
                   pr.village_match_type, pr.village_status,
                   pr.proximity_provider, pr.proximity_calculated_at, pr.proximity_status
            FROM thermal_events e
            LEFT JOIN event_predictions p ON e.event_id = p.event_id
            LEFT JOIN event_proximity pr ON e.event_id = pr.event_id
            WHERE e.event_id = ?
            """, (event_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)

            # Fetch detections
            cursor.execute("SELECT * FROM event_detections WHERE event_id = ? ORDER BY acq_datetime_utc", (event_id,))
            dets = [dict(d) for d in cursor.fetchall()]
            res["detections"] = dets
            if res.get("explanation_json"):
                res["explanation"] = json.loads(res["explanation_json"])

            # Structure proximity sub-dict
            res["proximity"] = {
                "nearest_industry_name": res.get("nearest_industry_name"),
                "nearest_industry_lat": res.get("nearest_industry_lat"),
                "nearest_industry_lon": res.get("nearest_industry_lon"),
                "distance_to_industry_m": res.get("distance_to_industry_m"),
                "distance_to_industry_km": res.get("distance_to_industry_km"),
                "nearest_school_name": res.get("nearest_school_name"),
                "nearest_school_lat": res.get("nearest_school_lat"),
                "nearest_school_lon": res.get("nearest_school_lon"),
                "distance_to_school_m": res.get("distance_to_school_m"),
                "distance_to_school_km": res.get("distance_to_school_km"),
                "school_place_id": res.get("school_place_id"),
                "nearest_hospital_name": res.get("nearest_hospital_name"),
                "nearest_hospital_lat": res.get("nearest_hospital_lat"),
                "nearest_hospital_lon": res.get("nearest_hospital_lon"),
                "distance_to_hospital_m": res.get("distance_to_hospital_m"),
                "distance_to_hospital_km": res.get("distance_to_hospital_km"),
                "hospital_place_id": res.get("hospital_place_id"),
                "nearest_village_name": res.get("nearest_village_name"),
                "nearest_village_lat": res.get("nearest_village_lat"),
                "nearest_village_lon": res.get("nearest_village_lon"),
                "distance_to_village_m": res.get("distance_to_village_m"),
                "distance_to_village_km": res.get("distance_to_village_km"),
                "village_place_id": res.get("village_place_id"),
                "village_match_type": res.get("village_match_type"),
                "village_status": res.get("village_status"),
                "proximity_provider": res.get("proximity_provider"),
                "proximity_calculated_at": res.get("proximity_calculated_at"),
                "proximity_status": res.get("proximity_status") or "NOT_CALCULATED"
            }
            return res

    def list_events(
        self,
        limit: int = 100,
        offset: int = 0,
        class_filter: Optional[str] = None,
        min_confidence: float = 0.0,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lists events with optional filtering including proximity summary."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
            SELECT e.*, p.predicted_class, p.class_id, p.confidence,
                   p.prob_industrial, p.prob_forest, p.prob_agricultural, p.prob_persistent,
                   p.persistence_level, p.dist_to_facility_km, p.nearest_facility_name,
                   pr.nearest_school_name, pr.distance_to_school_km, pr.nearest_school_lat, pr.nearest_school_lon,
                   pr.nearest_hospital_name, pr.distance_to_hospital_km, pr.nearest_hospital_lat, pr.nearest_hospital_lon,
                   pr.nearest_village_name, pr.distance_to_village_km, pr.nearest_village_lat, pr.nearest_village_lon,
                   pr.nearest_industry_name, pr.distance_to_industry_km, pr.nearest_industry_lat, pr.nearest_industry_lon,
                   pr.proximity_status
            FROM thermal_events e
            LEFT JOIN event_predictions p ON e.event_id = p.event_id
            LEFT JOIN event_proximity pr ON e.event_id = pr.event_id
            WHERE 1=1
            """
            params: List[Any] = []
            if class_filter:
                query += " AND p.predicted_class = ?"
                params.append(class_filter)
            if min_confidence > 0.0:
                query += " AND p.confidence >= ?"
                params.append(min_confidence)
            if since:
                query += " AND (e.created_at > ? OR e.event_start_time > ?)"
                params.extend([since, since])

            query += " ORDER BY e.event_start_time DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """Calculates operational database statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM thermal_events")
            total_events = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM event_detections")
            total_detections = cursor.fetchone()[0]

            cursor.execute("""
            SELECT predicted_class, COUNT(*), AVG(confidence)
            FROM event_predictions
            GROUP BY predicted_class
            """)
            class_breakdown = {}
            for r in cursor.fetchall():
                class_breakdown[r[0]] = {
                    "count": r[1],
                    "mean_confidence": round(float(r[2]), 4) if r[2] else 0.0
                }

            cursor.execute("SELECT COUNT(*) FROM event_proximity WHERE distance_to_school_km IS NOT NULL")
            schools_mapped = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM event_proximity WHERE distance_to_hospital_km IS NOT NULL")
            hospitals_mapped = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM event_proximity WHERE distance_to_village_km IS NOT NULL")
            villages_mapped = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM event_proximity WHERE distance_to_industry_km IS NOT NULL")
            industries_mapped = cursor.fetchone()[0]

            return {
                "total_events": total_events,
                "total_detections": total_detections,
                "class_breakdown": class_breakdown,
                "proximity_stats": {
                    "schools_mapped": schools_mapped,
                    "hospitals_mapped": hospitals_mapped,
                    "villages_mapped": villages_mapped,
                    "industries_mapped": industries_mapped
                }
            }

    def get_geojson(
        self,
        class_filter: Optional[str] = None,
        min_confidence: float = 0.0,
        since: Optional[str] = None
    ) -> Dict[str, Any]:
        """Returns standard GeoJSON FeatureCollection with proximity lines metadata."""
        events = self.list_events(limit=1000, offset=0, class_filter=class_filter, min_confidence=min_confidence, since=since)
        features = []
        for ev in events:
            feat = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [ev["centroid_lon"], ev["centroid_lat"]]
                },
                "properties": {
                    "event_id": ev["event_id"],
                    "event_start_time": ev["event_start_time"],
                    "detection_count": ev["detection_count"],
                    "predicted_class": ev.get("predicted_class", "Unclassified"),
                    "class_id": ev.get("class_id"),
                    "confidence": ev.get("confidence", 0.0),
                    "persistence_level": ev.get("persistence_level", "UNKNOWN"),
                    "nearest_facility_distance_km": ev.get("dist_to_facility_km", 999.0),
                    "nearest_facility_name": ev.get("nearest_facility_name", "None"),
                    # Proximity context (Stage 8.42)
                    "nearest_industry_name": ev.get("nearest_industry_name") or ev.get("nearest_facility_name"),
                    "distance_to_industry_km": ev.get("distance_to_industry_km") if ev.get("distance_to_industry_km") is not None else ev.get("dist_to_facility_km"),
                    "nearest_industry_lat": ev.get("nearest_industry_lat"),
                    "nearest_industry_lon": ev.get("nearest_industry_lon"),
                    "nearest_school_name": ev.get("nearest_school_name"),
                    "distance_to_school_km": ev.get("distance_to_school_km"),
                    "nearest_school_lat": ev.get("nearest_school_lat"),
                    "nearest_school_lon": ev.get("nearest_school_lon"),
                    "nearest_hospital_name": ev.get("nearest_hospital_name"),
                    "distance_to_hospital_km": ev.get("distance_to_hospital_km"),
                    "nearest_hospital_lat": ev.get("nearest_hospital_lat"),
                    "nearest_hospital_lon": ev.get("nearest_hospital_lon"),
                    "nearest_village_name": ev.get("nearest_village_name"),
                    "distance_to_village_km": ev.get("distance_to_village_km"),
                    "nearest_village_lat": ev.get("nearest_village_lat"),
                    "nearest_village_lon": ev.get("nearest_village_lon"),
                    "proximity_status": ev.get("proximity_status") or "NOT_CALCULATED"
                }
            }
            features.append(feat)

        return {
            "type": "FeatureCollection",
            "features": features
        }

_GLOBAL_DB: Optional[DatabaseManager] = None

def get_db() -> DatabaseManager:
    global _GLOBAL_DB
    if _GLOBAL_DB is None:
        _GLOBAL_DB = DatabaseManager()
    return _GLOBAL_DB
