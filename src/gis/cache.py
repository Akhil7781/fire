"""Stage 8.42 GIS Proximity Cache Layer.

Persists Geoapify Places API lookups in SQLite by rounded spatial coordinates
and POI category to avoid redundant API queries and minimize external latency.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sqlite3
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "operational.db"

class GisProximityCache:
    """Thread-safe SQLite-backed cache for nearest POI lookups."""

    def __init__(self, db_path: Optional[Path] = None, round_precision: int = 3):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.round_precision = round_precision
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Creates the cache table and spatial indexes if not present."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS gis_proximity_cache (
                spatial_key TEXT NOT NULL,
                category TEXT NOT NULL,
                name TEXT,
                lat REAL,
                lon REAL,
                provider_distance_m REAL,
                computed_distance_m REAL,
                place_id TEXT,
                match_type TEXT,
                status TEXT NOT NULL,
                payload_json TEXT,
                cached_at TEXT NOT NULL,
                PRIMARY KEY (spatial_key, category)
            )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_gis_cache_key ON gis_proximity_cache(spatial_key)")
            conn.commit()

    def make_spatial_key(self, lat: float, lon: float) -> str:
        """Rounds coordinates to define a deterministic spatial cell (~110m)."""
        r_lat = round(float(lat), self.round_precision)
        r_lon = round(float(lon), self.round_precision)
        return f"{r_lat:.3f}_{r_lon:.3f}"

    def get(self, lat: float, lon: float, category: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached proximity result for coordinate and category."""
        spatial_key = self.make_spatial_key(lat, lon)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM gis_proximity_cache
            WHERE spatial_key = ? AND category = ?
            """, (spatial_key, category))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                if d.get("payload_json"):
                    try:
                        d["raw_payload"] = json.loads(d["payload_json"])
                    except Exception:
                        pass
                return d
        return None

    def set(
        self,
        lat: float,
        lon: float,
        category: str,
        name: Optional[str],
        poi_lat: Optional[float],
        poi_lon: Optional[float],
        provider_distance_m: Optional[float],
        computed_distance_m: Optional[float],
        place_id: Optional[str] = None,
        match_type: Optional[str] = None,
        status: str = "SUCCESS",
        payload: Optional[Dict[str, Any]] = None
    ):
        """Stores a proximity result in cache."""
        spatial_key = self.make_spatial_key(lat, lon)
        now = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload) if payload else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO gis_proximity_cache (
                spatial_key, category, name, lat, lon,
                provider_distance_m, computed_distance_m,
                place_id, match_type, status, payload_json, cached_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                spatial_key, category, name, poi_lat, poi_lon,
                provider_distance_m, computed_distance_m,
                place_id, match_type, status, payload_str, now
            ))
            conn.commit()

    def clear(self):
        """Clears all cached records."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM gis_proximity_cache")
            conn.commit()
