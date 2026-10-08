"""Stage 8.42 Live System State Tracker.

Thread-safe, observable operational state tracking for near-real-time NASA FIRMS
polling, event clustering, neural attribution, and GIS proximity lookups.
"""

from datetime import datetime, timezone
import logging
from threading import Lock
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LiveStateTracker:
    """Thread-safe state repository for the live operational pipeline."""

    def __init__(self):
        self._lock = Lock()
        self.mode = "NRT"  # "NRT" or "DEMO"
        self.status = "idle"  # "running", "idle", "degraded", "offline"
        self.firms_source = "VIIRS_NOAA20_NRT"
        self.last_poll_time: Optional[str] = None
        self.last_success_time: Optional[str] = None
        self.last_detection_time: Optional[str] = None
        self.new_detections_count: int = 0
        self.total_detections_count: int = 0
        self.active_events_count: int = 0
        self.classified_events_count: int = 0
        self.last_error: Optional[str] = None

        # Detailed metrics
        self.records_received: int = 0
        self.duplicates_ignored: int = 0
        self.events_updated: int = 0
        self.gis_lookups: int = 0
        self.gis_cache_hits: int = 0
        self.gis_cache_misses: int = 0

        # Latency benchmarks
        self.timings: Dict[str, float] = {
            "download_s": 0.0,
            "clustering_s": 0.0,
            "inference_s": 0.0,
            "gis_s": 0.0,
            "db_write_s": 0.0,
            "total_s": 0.0
        }

    def record_poll_start(self):
        """Records beginning of polling cycle."""
        with self._lock:
            self.status = "running"
            self.last_poll_time = datetime.now(timezone.utc).isoformat()
            self.last_error = None

    def record_poll_success(
        self,
        received: int,
        duplicates: int,
        new_dets: int,
        active_evts: int,
        classified: int,
        last_det_time: Optional[str],
        gis_lookups: int,
        timings: Dict[str, float]
    ):
        """Updates state with metrics from a completed polling cycle."""
        with self._lock:
            self.status = "idle"
            self.last_success_time = datetime.now(timezone.utc).isoformat()
            self.records_received = received
            self.duplicates_ignored = duplicates
            self.new_detections_count = new_dets
            self.total_detections_count += new_dets
            self.active_events_count = active_evts
            self.classified_events_count = classified
            if last_det_time:
                self.last_detection_time = last_det_time
            self.gis_lookups = gis_lookups
            self.timings = timings

    def record_poll_failure(self, error_message: str, degraded: bool = True):
        """Records polling error and sets appropriate status."""
        with self._lock:
            self.status = "degraded" if degraded else "offline"
            self.last_error = error_message
            logger.error(f"Live polling failure: {error_message}")

    def get_status_dict(self) -> Dict[str, Any]:
        """Returns API-ready status dictionary matching Requirement N."""
        with self._lock:
            return {
                "mode": self.mode,
                "status": self.status,
                "firms_source": self.firms_source,
                "last_poll": self.last_poll_time,
                "last_success": self.last_success_time,
                "last_detection": self.last_detection_time,
                "new_detections": self.new_detections_count,
                "total_detections": self.total_detections_count,
                "active_events": self.active_events_count,
                "classified_events": self.classified_events_count,
                "records_received": self.records_received,
                "duplicates_ignored": self.duplicates_ignored,
                "gis_lookups": self.gis_lookups,
                "last_error": self.last_error,
                "timings": self.timings
            }

_GLOBAL_STATE: Optional[LiveStateTracker] = None

def get_live_state() -> LiveStateTracker:
    global _GLOBAL_STATE
    if _GLOBAL_STATE is None:
        _GLOBAL_STATE = LiveStateTracker()
    return _GLOBAL_STATE
