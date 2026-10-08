"""Stage 8.37 NASA FIRMS Ingestion Validators.

Performs strict data quality and sanitary checks on ingested satellite observations:
- Latitude / Longitude valid ranges
- Non-negative Fire Radiative Power (FRP)
- Valid timestamp parsing
- Missing value imputation / rejection
- Detection deduplication
"""

from datetime import datetime
import logging
from typing import List, Dict, Tuple, Any
import numpy as np
import pandas as pd

from src.stage8_37.inference.schemas import FirmsDetectionRecord

logger = logging.getLogger(__name__)

def validate_detection_record(rec: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Validates a single detection record and normalizes values.

    Returns:
        (is_valid, error_msg, normalized_record)
    """
    try:
        lat = float(rec.get("latitude", rec.get("LATITUDE", np.nan)))
        lon = float(rec.get("longitude", rec.get("LONGITUDE", np.nan)))
        frp = float(rec.get("frp", rec.get("FRP", 0.0)))
        ti4 = float(rec.get("bright_ti4", rec.get("BRIGHT_TI4", 300.0)))
        ti5 = float(rec.get("bright_ti5", rec.get("BRIGHT_TI5", 290.0)))
    except (ValueError, TypeError) as e:
        return False, f"Non-numeric field in record: {e}", {}

    if np.isnan(lat) or not (-90.0 <= lat <= 90.0):
        return False, f"Invalid latitude: {lat}", {}
    if np.isnan(lon) or not (-180.0 <= lon <= 180.0):
        return False, f"Invalid longitude: {lon}", {}
    if np.isnan(frp) or frp < 0.0:
        return False, f"Negative or NaN FRP: {frp}", {}
    if np.isnan(ti4) or ti4 <= 0.0 or np.isnan(ti5) or ti5 <= 0.0:
        return False, f"Invalid brightness temperature: ti4={ti4}, ti5={ti5}", {}

    # Timestamp extraction
    acq_date = str(rec.get("acq_date", rec.get("ACQ_DATE", ""))).strip()
    acq_time = str(rec.get("acq_time", rec.get("ACQ_TIME", "0000"))).strip().zfill(4)
    dt_utc = rec.get("acq_datetime_utc", rec.get("ACQ_DATETIME_UTC", None))

    if not dt_utc:
        try:
            # Parse date YYYY-MM-DD and time HHMM
            clean_date = acq_date.split("T")[0]
            hh = int(acq_time[:2])
            mm = int(acq_time[2:])
            parsed_dt = datetime.strptime(f"{clean_date} {hh:02d}:{mm:02d}", "%Y-%m-%d %H:%M")
            dt_utc = parsed_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception as e:
            return False, f"Failed to parse timestamp ({acq_date}, {acq_time}): {e}", {}

    did = str(rec.get("detection_id", rec.get("DETECTION_ID", "")))
    if not did:
        did = f"DET_{lat:.4f}_{lon:.4f}_{acq_date}_{acq_time}"

    conf = str(rec.get("confidence", rec.get("CONFIDENCE", "nominal"))).lower()
    daynight = str(rec.get("daynight", rec.get("DAYNIGHT", "D"))).upper()
    if daynight not in ["D", "N"]:
        daynight = "D"

    sat = str(rec.get("satellite", rec.get("SATELLITE", "N")))
    sensor = str(rec.get("sensor", rec.get("SENSOR", "VIIRS")))

    normalized = {
        "detection_id": did,
        "latitude": float(lat),
        "longitude": float(lon),
        "acq_date": acq_date,
        "acq_time": acq_time,
        "acq_datetime_utc": str(dt_utc),
        "bright_ti4": float(ti4),
        "bright_ti5": float(ti5),
        "frp": float(frp),
        "confidence": conf,
        "satellite": sat,
        "sensor": sensor,
        "daynight": daynight
    }

    return True, "", normalized

def deduplicate_detections(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Removes exact duplicate detections based on spatial coordinates and acquisition time."""
    seen = set()
    deduped = []
    for r in records:
        key = (round(r["latitude"], 4), round(r["longitude"], 4), r["acq_datetime_utc"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped
