"""Stage 8.42 NASA FIRMS Near-Real-Time (NRT) Poller.

Fetches satellite thermal anomaly observations from NASA FIRMS Area CSV API:
Source: VIIRS_NOAA20_NRT
Bounding Box (India): 68,6,98,37 (West=68, South=6, East=98, North=37)
"""

import io
import logging
import os
from typing import List, Optional
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

from src.stage8_37.inference.schemas import FirmsDetectionRecord

logger = logging.getLogger(__name__)

FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
INDIA_BBOX = "68,6,98,37"  # West, South, East, North

class FirmsPollerError(Exception):
    """Raised when FIRMS polling fails."""
    pass

class FirmsNrtPoller:
    """Poller for NASA FIRMS VIIRS NOAA-20 near-real-time observations."""

    def __init__(
        self,
        map_key: Optional[str] = None,
        source: str = "VIIRS_NOAA20_NRT",
        bbox: str = INDIA_BBOX,
        timeout_seconds: float = 25.0
    ):
        self.map_key = map_key if map_key is not None else os.getenv("FIRMS_MAP_KEY", "")
        self.source = source
        self.bbox = bbox
        self.timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        """Returns True if FIRMS_MAP_KEY is available."""
        return bool(self.map_key and len(self.map_key.strip()) > 0)

    @property
    def area_bbox(self) -> str:
        """Returns the geographic bounding box string."""
        return self.bbox

    def is_in_bounds(self, lat: float, lon: float) -> bool:
        """Validates if coordinates fall within the India area bounding box."""
        return 6.0 <= lat <= 37.0 and 68.0 <= lon <= 98.0

    def fetch_detections(self, days: int = 1, auto_fallback_days: bool = True) -> List[FirmsDetectionRecord]:
        """Polls NASA FIRMS NRT Area API for recent thermal anomaly soundings in India.

        Args:
            days: Day window to query (1 to 10).
            auto_fallback_days: If days=1 yields 0 detections (e.g. early morning before overpass),
                                queries days=2 to retrieve recent active observations.

        Returns:
            List of validated FirmsDetectionRecord instances.
        """
        if not self.is_configured:
            raise FirmsPollerError(
                "FIRMS_MAP_KEY is not configured in environment. Live NRT mode unavailable."
            )

        url = f"{FIRMS_BASE_URL}/{self.map_key.strip()}/{self.source}/{self.bbox}/{days}"
        logger.info(f"Querying NASA FIRMS NRT ({self.source}) for India BBOX over last {days} day(s)...")

        try:
            resp = requests.get(url, timeout=self.timeout_seconds)
        except requests.exceptions.Timeout:
            raise FirmsPollerError(f"NASA FIRMS API connection timed out after {self.timeout_seconds}s.")
        except Exception as e:
            raise FirmsPollerError(f"NASA FIRMS API network request failed: {str(e)}")

        if resp.status_code == 403 or resp.status_code == 401:
            raise FirmsPollerError(f"NASA FIRMS authorization failed (HTTP {resp.status_code}). Check FIRMS_MAP_KEY.")
        if resp.status_code != 200:
            raise FirmsPollerError(f"NASA FIRMS API returned error HTTP {resp.status_code}: {resp.text[:200]}")

        content = resp.text.strip()
        if not content:
            return []

        try:
            df = pd.read_csv(io.StringIO(content))
        except Exception as e:
            raise FirmsPollerError(f"Failed to parse CSV response from NASA FIRMS: {str(e)}")

        # Check required columns
        required_cols = {"latitude", "longitude", "bright_ti4", "bright_ti5", "frp", "acq_date", "acq_time"}
        missing = required_cols - set(df.columns)
        if missing:
            raise FirmsPollerError(f"NASA FIRMS CSV missing expected columns: {missing}")

        # If days=1 is empty and auto_fallback is enabled, try days=2
        if len(df) == 0 and days == 1 and auto_fallback_days:
            logger.info("FIRMS days=1 returned 0 records; trying days=2 for recent satellite overpasses...")
            return self.fetch_detections(days=2, auto_fallback_days=False)

        records: List[FirmsDetectionRecord] = []
        for idx, row in df.iterrows():
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])

                # Spatial validation
                if not (6.0 <= lat <= 37.0 and 68.0 <= lon <= 98.0):
                    continue

                acq_date = str(row["acq_date"]).strip()
                acq_time_raw = str(row["acq_time"]).strip().zfill(4)
                hh = acq_time_raw[:2]
                mm = acq_time_raw[2:4]
                acq_dt = f"{acq_date}T{hh}:{mm}:00Z"

                rec = FirmsDetectionRecord(
                    latitude=lat,
                    longitude=lon,
                    acq_date=acq_date,
                    acq_time=acq_time_raw,
                    acq_datetime_utc=acq_dt,
                    bright_ti4=float(row.get("bright_ti4", 300.0)),
                    bright_ti5=float(row.get("bright_ti5", 280.0)),
                    frp=float(row.get("frp", 1.0)),
                    confidence=str(row.get("confidence", "nominal")),
                    satellite=str(row.get("satellite", "N20")),
                    sensor=str(row.get("instrument", "VIIRS")),
                    daynight=str(row.get("daynight", "D"))
                )
                records.append(rec)
            except Exception as e:
                logger.debug(f"Skipping malformed FIRMS detection row {idx}: {e}")
                continue

        logger.info(f"NASA FIRMS poller successfully parsed {len(records)} valid thermal soundings.")
        return records
