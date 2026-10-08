"""
Stage 8.30 Data Builder & Causal History Extractor.
Extracts:
1. Historical detection sequences (within 2 km, strictly <= t0 - 7 days).
2. Multi-scale causal historical summary features.
3. Current alert observations (within horizon H).
4. Causal geospatial/context features (NO persistent registry).
"""

import math
import numpy as np
import pandas as pd
from pathlib import Path

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0)**2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

def compute_pairwise_max_distance(lats: np.ndarray, lons: np.ndarray) -> float:
    if len(lats) <= 1:
        return 0.0
    max_d = 0.0
    for i in range(len(lats)):
        for j in range(i + 1, len(lats)):
            d = haversine_km(lats[i], lons[i], lats[j], lons[j])
            if d > max_d:
                max_d = d
    return float(max_d)

def compute_ecoregion_scores(lat: float, lon: float):
    is_wg = (8.0 <= lat <= 16.0) and (73.0 <= lon <= 77.5)
    is_him = (lat >= 29.0) and (75.0 <= lon <= 89.0)
    is_ch = (20.0 <= lat <= 24.5) and (78.0 <= lon <= 85.0)
    is_ne = (lat >= 24.0) and (lon >= 90.0)
    is_od = (18.5 <= lat <= 22.0) and (83.0 <= lon <= 86.5)
    forest_score = 1.0 if (is_wg or is_him or is_ch or is_ne or is_od) else 0.0

    is_igp = (24.0 <= lat <= 31.5) and (74.0 <= lon <= 88.0) and not is_him
    is_kd = (15.5 <= lat <= 17.5) and (80.0 <= lon <= 82.5)
    is_cav = (10.5 <= lat <= 12.0) and (78.5 <= lon <= 80.0)
    is_mal = (21.5 <= lat <= 24.5) and (75.0 <= lon <= 78.0)
    agri_score = 1.0 if (is_igp or is_kd or is_cav or is_mal) else 0.0

    return forest_score, agri_score

def test_feature_extraction():
    events_path = Path("data/interim/ds08_stage8_25_physical_events.parquet")
    firms_path = Path("data/interim/ds08_stage8_25_multiyear_firms.parquet")
    
    df_events = pd.read_parquet(events_path)
    df_firms = pd.read_parquet(firms_path)
    df_firms["acq_dt"] = pd.to_datetime(df_firms["acq_datetime_utc"])
    
    print(f"Loaded {len(df_events)} events and {len(df_firms)} FIRMS detections.")

if __name__ == "__main__":
    test_feature_extraction()
