import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from src.utils.config import get_firms_map_key

key = get_firms_map_key()
for sensor in ("VIIRS_NOAA20_SP", "VIIRS_NOAA21_SP", "VIIRS_SNPP_SP"):
    try:
        response = requests.get(
            "https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/"
            + key + "/" + sensor,
            timeout=20,
        )
        print(sensor, "HTTP", response.status_code)
        print(response.text[:2500].replace(key, "[REDACTED]"))
    except Exception as exc:
        print(sensor, "ERROR", type(exc).__name__)
