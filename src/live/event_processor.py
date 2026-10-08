"""Stage 8.42 Live Event Processor.

Orchestrates the live operational pipeline:
1. Deterministic FIRMS detection deduplication
2. Spatio-temporal thermal event clustering (EventBuilder: <= 3km, <= 24h)
3. Causal 41-feature extraction and frozen PyTorch MLP inference
4. Geodesic GIS proximity analysis (Industry, School, Hospital, Village)
5. Geospatial database persistence and real-time state tracking
"""

from datetime import datetime, timezone
import hashlib
import logging
import time
from typing import List, Dict, Any, Tuple, Set, Optional

from src.stage8_37.inference.schemas import FirmsDetectionRecord, ThermalEventInput, PredictionOutput
from src.stage8_37.events.event_builder import EventBuilder
from src.stage8_37.inference.predictor import OperationalPredictor
from src.stage8_37.database.db import DatabaseManager, get_db
from src.gis.proximity import ProximityEngine
from src.live.live_state import LiveStateTracker, get_live_state

logger = logging.getLogger(__name__)

class LiveEventProcessor:
    """Processes incoming real-time FIRMS soundings into attributed, GIS-enriched thermal events."""

    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        predictor: Optional[OperationalPredictor] = None,
        proximity_engine: Optional[ProximityEngine] = None,
        state: Optional[LiveStateTracker] = None
    ):
        self.db = db or get_db()
        self.predictor = predictor or OperationalPredictor()
        self.proximity_engine = proximity_engine or ProximityEngine()
        self.state = state or get_live_state()
        self.event_builder = EventBuilder(spatial_radius_km=3.0, temporal_window_hours=24.0)

        # In-memory detection cache for fast deduplication
        self._processed_detection_keys: Set[str] = set()
        self._load_existing_detection_signatures()

    def _load_existing_detection_signatures(self):
        """Pre-populates known detection keys from the database."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT latitude, longitude, acq_datetime_utc, satellite, sensor, daynight FROM event_detections")
                for row in cursor.fetchall():
                    lat, lon, dt, sat, sen, dn = row
                    key = f"{lat:.5f}_{lon:.5f}_{dt}_{sat}_{sen}_{dn}"
                    self._processed_detection_keys.add(key)
            logger.info(f"Loaded {len(self._processed_detection_keys)} existing detection signatures for deduplication.")
        except Exception as e:
            logger.warning(f"Could not pre-load detection signatures: {e}")

    def deduplicate(self, detections: List[FirmsDetectionRecord]) -> Tuple[List[FirmsDetectionRecord], int]:
        """Filters out duplicate detections using deterministic signatures."""
        unique: List[FirmsDetectionRecord] = []
        duplicates = 0

        for d in detections:
            key = f"{d.latitude:.5f}_{d.longitude:.5f}_{d.acq_datetime_utc}_{d.satellite}_{d.sensor}_{d.daynight}"
            if key in self._processed_detection_keys:
                duplicates += 1
            else:
                self._processed_detection_keys.add(key)
                unique.append(d)

        return unique, duplicates

    def _deduplicate_detections(self, df: Any) -> Any:
        """Deduplicates a pandas DataFrame of detections based on space, time, and sensor."""
        subset_cols = [c for c in ["latitude", "longitude", "acq_date", "acq_time"] if c in df.columns]
        if subset_cols:
            return df.drop_duplicates(subset=subset_cols).reset_index(drop=True)
        return df.drop_duplicates().reset_index(drop=True)

    def process_live_detections(
        self,
        raw_detections: List[FirmsDetectionRecord],
        download_time_s: float = 0.0
    ) -> Dict[str, Any]:
        """Runs the complete ingestion -> clustering -> inference -> GIS pipeline.

        Returns:
            Dict containing processing metrics and newly created events.
        """
        t0_total = time.perf_counter()
        received_count = len(raw_detections)

        # 1. Deduplication
        new_detections, dup_count = self.deduplicate(raw_detections)
        logger.info(f"FIRMS Ingestion: {received_count} received | {dup_count} duplicates ignored | {len(new_detections)} new")

        if not new_detections:
            # No new soundings to cluster
            timings = {
                "download_s": round(download_time_s, 3),
                "clustering_s": 0.0,
                "inference_s": 0.0,
                "gis_s": 0.0,
                "db_write_s": 0.0,
                "total_s": round(time.perf_counter() - t0_total, 3)
            }
            stats = self.db.get_statistics()
            self.state.record_poll_success(
                received=received_count,
                duplicates=dup_count,
                new_dets=0,
                active_evts=stats["total_events"],
                classified=stats["total_events"],
                last_det_time=None,
                gis_lookups=0,
                timings=timings
            )
            return {
                "status": "NO_NEW_DATA",
                "received": received_count,
                "duplicates_ignored": dup_count,
                "new_detections": 0,
                "events_created": 0,
                "timings": timings
            }

        # 2. Event Clustering
        t0_cluster = time.perf_counter()
        events = self.event_builder.build_events(new_detections)
        clustering_time_s = time.perf_counter() - t0_cluster

        # 3. Model Inference & 4. GIS Proximity
        t0_inf = time.perf_counter()
        predictions: List[PredictionOutput] = []
        for ev in events:
            pred = self.predictor.predict_event(ev)
            predictions.append(pred)
        inference_time_s = time.perf_counter() - t0_inf

        t0_gis = time.perf_counter()
        proximity_records: List[Tuple[str, Dict[str, Any]]] = []
        for ev in events:
            prox = self.proximity_engine.compute_event_proximity(ev.centroid_lat, ev.centroid_lon)
            proximity_records.append((ev.event_id, prox))
        gis_time_s = time.perf_counter() - t0_gis

        # 5. Database Persistence (Batch Single-Transaction)
        t0_db = time.perf_counter()
        self.db.save_batch(events, predictions)
        self.db.save_proximity_batch(proximity_records)
        db_time_s = time.perf_counter() - t0_db

        total_time_s = time.perf_counter() - t0_total

        timings = {
            "download_s": round(download_time_s, 3),
            "clustering_s": round(clustering_time_s, 3),
            "inference_s": round(inference_time_s, 3),
            "gis_s": round(gis_time_s, 3),
            "db_write_s": round(db_time_s, 3),
            "total_s": round(total_time_s, 3)
        }

        # Find newest acquisition timestamp
        last_det_time = max(d.acq_datetime_utc for d in new_detections) if new_detections else None
        db_stats = self.db.get_statistics()

        # Update Observable Live State
        self.state.record_poll_success(
            received=received_count,
            duplicates=dup_count,
            new_dets=len(new_detections),
            active_evts=db_stats["total_events"],
            classified=db_stats["total_events"],
            last_det_time=last_det_time,
            gis_lookups=len(events) * 4,
            timings=timings
        )

        logger.info(
            f"Live Pipeline Completed: {len(events)} events built & classified | "
            f"{len(events)*4} GIS lookups | Total time: {total_time_s:.2f}s"
        )

        return {
            "status": "SUCCESS",
            "received": received_count,
            "duplicates_ignored": dup_count,
            "new_detections": len(new_detections),
            "events_created": len(events),
            "events": [ev.event_id for ev in events],
            "timings": timings
        }
