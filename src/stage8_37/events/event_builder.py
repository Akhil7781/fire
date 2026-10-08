"""Stage 8.37 Thermal Event Builder.

Clusters individual spatio-temporal NASA FIRMS detections into discrete thermal events:
- Single-linkage / DBSCAN-style spatial radius clustering (<= 3.0 km)
- Temporal grouping window (<= 24 hours from initial onset)
- Centroid computation for latitude and longitude
- Preserves all underlying detection IDs for complete provenance
"""

import hashlib
import logging
from typing import List, Dict, Any
import numpy as np
import pandas as pd

from src.stage8_37.inference.schemas import FirmsDetectionRecord, ThermalEventInput
from src.stage8_37.inference.feature_builder import haversine_km

logger = logging.getLogger(__name__)

class EventBuilder:
    """Groups FIRMS point detections into discrete physical thermal events."""

    def __init__(self, spatial_radius_km: float = 3.0, temporal_window_hours: float = 24.0):
        self.spatial_radius_km = spatial_radius_km
        self.temporal_window_hours = temporal_window_hours

    def build_events(self, detections: List[FirmsDetectionRecord]) -> List[ThermalEventInput]:
        """Clusters detections into a list of ThermalEventInput objects."""
        if not detections:
            return []

        # Pre-parse timestamps
        det_parsed = []
        for d in detections:
            dt = pd.to_datetime(d.acq_datetime_utc)
            det_parsed.append((dt, d))
        det_parsed.sort(key=lambda x: x[0])

        clusters: List[Dict[str, Any]] = []

        for det_dt, det in det_parsed:
            assigned = False

            for c in clusters:
                hours_diff = (det_dt - c["start_dt"]).total_seconds() / 3600.0

                if hours_diff <= self.temporal_window_hours:
                    n = len(c["dets"])
                    c_lat = c["sum_lat"] / n
                    c_lon = c["sum_lon"] / n

                    dist_km = haversine_km(det.latitude, det.longitude, c_lat, c_lon)
                    if dist_km <= self.spatial_radius_km:
                        c["dets"].append(det)
                        c["sum_lat"] += det.latitude
                        c["sum_lon"] += det.longitude
                        assigned = True
                        break

            if not assigned:
                clusters.append({
                    "start_dt": det_dt,
                    "dets": [det],
                    "sum_lat": det.latitude,
                    "sum_lon": det.longitude
                })

        clusters_raw = [c["dets"] for c in clusters]

        events: List[ThermalEventInput] = []
        for idx, cluster in enumerate(clusters_raw):
            lats = [d.latitude for d in cluster]
            lons = [d.longitude for d in cluster]
            c_lat = float(np.mean(lats))
            c_lon = float(np.mean(lons))

            start_time = cluster[0].acq_datetime_utc
            date_str = start_time[:10].replace("-", "")

            # Deterministic event ID
            cluster_hash = hashlib.sha256(
                f"{c_lat:.4f}_{c_lon:.4f}_{start_time}".encode("utf-8")
            ).hexdigest()[:8].upper()
            event_id = f"EVT_{date_str}_{cluster_hash}"

            events.append(ThermalEventInput(
                event_id=event_id,
                centroid_lat=float(round(c_lat, 5)),
                centroid_lon=float(round(c_lon, 5)),
                event_start_time=start_time,
                event_detection_count=len(cluster),
                detections=cluster
            ))

        logger.info(f"Constructed {len(events)} thermal events from {len(detections)} detections.")
        return events
