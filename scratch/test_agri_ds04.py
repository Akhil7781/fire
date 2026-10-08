import pandas as pd
import numpy as np
import math

EARTH_RADIUS_KM = 6371.0

def geodesic_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return EARTH_RADIUS_KM * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

def temporal_diff_hours(det_dt, start_dt, end_dt, tol_hours=12.0):
    t_min = start_dt - pd.Timedelta(hours=tol_hours)
    t_max = end_dt + pd.Timedelta(hours=tol_hours)
    if t_min <= det_dt <= t_max:
        return 0.0
    elif det_dt < t_min:
        return (t_min - det_dt).total_seconds() / 3600.0
    else:
        return (det_dt - t_max).total_seconds() / 3600.0

df = pd.read_parquet('data/interim/causal_features_2025.parquet', columns=['detection_id', 'latitude', 'longitude', 'acq_datetime_utc', 'frp', 'partition'])
df['acq_dt'] = pd.to_datetime(df['acq_datetime_utc'], utc=True)

test_events = [
    # 1. Sangrur Rabi Wheat Burn (Punjab) - train
    {
        "id": "EVT_2025_AGRI_PB_SANGRUR_RABI_001",
        "lat": 30.2001,
        "lon": 75.8984,
        "start": "2025-05-01T06:00:00Z",
        "end": "2025-05-01T14:00:00Z",
        "crop": "Wheat Stubble (Rabi)",
        "season": "RABI",
        "status": "CROPLAND",
        "dnbr": 0.28,
        "nir_ratio": 0.65,
        "has_corrob": True,
    },
    # 2. Karnal Rabi Wheat Burn (Haryana) - train
    {
        "id": "EVT_2025_AGRI_HR_KARNAL_RABI_002",
        "lat": 29.7400,
        "lon": 76.8650,
        "start": "2025-05-01T06:00:00Z",
        "end": "2025-05-01T14:00:00Z",
        "crop": "Wheat Stubble (Rabi)",
        "season": "RABI",
        "status": "CROPLAND",
        "dnbr": 0.32,
        "nir_ratio": 0.60,
        "has_corrob": True,
    },
    # 3. Sehore Rabi Wheat Burn (Madhya Pradesh) - train
    {
        "id": "EVT_2025_AGRI_MP_SEHORE_RABI_003",
        "lat": 23.0850,
        "lon": 77.3300,
        "start": "2025-04-01T06:00:00Z",
        "end": "2025-04-01T14:00:00Z",
        "crop": "Wheat Stubble (Rabi)",
        "season": "RABI",
        "status": "CROPLAND",
        "dnbr": 0.25,
        "nir_ratio": 0.70,
        "has_corrob": True,
    },
    # 4. Patiala Nabha Rabi Wheat Burn (Punjab) - train
    {
        "id": "EVT_2025_AGRI_PB_PATIALA_RABI_004",
        "lat": 30.2800,
        "lon": 76.1500,
        "start": "2025-05-03T06:00:00Z",
        "end": "2025-05-03T14:00:00Z",
        "crop": "Wheat Stubble (Rabi)",
        "season": "RABI",
        "status": "CROPLAND",
        "dnbr": 0.30,
        "nir_ratio": 0.62,
        "has_corrob": True,
    },
    # 5. Patiala Kharif Paddy Burn (Punjab) - val
    {
        "id": "EVT_2025_AGRI_PB_PATIALA_KHARIF_005",
        "lat": 30.4225,
        "lon": 76.3278,
        "start": "2025-10-25T06:00:00Z",
        "end": "2025-10-25T14:00:00Z",
        "crop": "Paddy Stubble (Kharif)",
        "season": "KHARIF",
        "status": "CROPLAND",
        "dnbr": 0.45,
        "nir_ratio": 0.55,
        "has_corrob": True,
    },
    # 6. Kaithal Kharif Paddy Burn (Haryana) - val
    {
        "id": "EVT_2025_AGRI_HR_KAITHAL_KHARIF_006",
        "lat": 30.0208,
        "lon": 76.2032,
        "start": "2025-10-25T06:00:00Z",
        "end": "2025-10-25T14:00:00Z",
        "crop": "Paddy Stubble (Kharif)",
        "season": "KHARIF",
        "status": "CROPLAND",
        "dnbr": 0.38,
        "nir_ratio": 0.58,
        "has_corrob": True,
    },
    # Negative controls
    # 7. Off-season burn (fails C2)
    {
        "id": "EVT_2025_AGRI_PB_OFFSEASON_007",
        "lat": 30.2000,
        "lon": 75.8980,
        "start": "2025-07-15T06:00:00Z",
        "end": "2025-07-15T14:00:00Z",
        "crop": "Non-seasonal biomass",
        "season": "OFF_SEASON",
        "status": "CROPLAND",
        "dnbr": 0.22,
        "nir_ratio": 0.70,
        "has_corrob": False,
    },
    # 8. Non-cropland burn (fails C1)
    {
        "id": "EVT_2025_AGRI_UK_FOREST_FAIL_008",
        "lat": 29.3803,
        "lon": 79.4636,
        "start": "2025-04-26T06:00:00Z",
        "end": "2025-04-26T14:00:00Z",
        "crop": "Pine Litter",
        "season": "RABI",
        "status": "FOREST",
        "dnbr": 0.40,
        "nir_ratio": 0.50,
        "has_corrob": False,
    },
    # 9. Plowed dry soil / weak change (fails C3)
    {
        "id": "EVT_2025_AGRI_HR_PLOWED_SOIL_009",
        "lat": 29.7400,
        "lon": 76.8650,
        "start": "2025-05-01T06:00:00Z",
        "end": "2025-05-01T14:00:00Z",
        "crop": "Tilled Soil",
        "season": "RABI",
        "status": "CROPLAND",
        "dnbr": 0.06,  # < 0.18
        "nir_ratio": 0.95,  # >= 0.85
        "has_corrob": True,
    },
    # 10. Uncorroborated burn (fails C4)
    {
        "id": "EVT_2025_AGRI_MP_UNCORROBORATED_010",
        "lat": 23.0850,
        "lon": 77.3300,
        "start": "2025-04-01T06:00:00Z",
        "end": "2025-04-01T14:00:00Z",
        "crop": "Unverified Burn",
        "season": "RABI",
        "status": "CROPLAND",
        "dnbr": 0.25,
        "nir_ratio": 0.70,
        "has_corrob": False,
    },
]

for ev in test_events:
    t_start = pd.to_datetime(ev['start'], utc=True)
    t_end = pd.to_datetime(ev['end'], utc=True)
    
    sub = df[(df['latitude'].between(ev['lat'] - 0.05, ev['lat'] + 0.05)) & 
             (df['longitude'].between(ev['lon'] - 0.05, ev['lon'] + 0.05))]
    
    matches = []
    for _, r in sub.iterrows():
        d = geodesic_distance_km(r['latitude'], r['longitude'], ev['lat'], ev['lon'])
        dt = temporal_diff_hours(r['acq_dt'], t_start, t_end, tol_hours=12.0)
        if d <= 1.0 and dt == 0.0:
            matches.append((r['detection_id'], d, r['frp'], r['partition'], r['acq_dt']))
            
    print(f"\n{ev['id']} ({ev['crop']}, {ev['status']}):")
    print(f"   Matches within 1.0 km & valid time: {len(matches)}")
    for m in matches:
        print(f"      {m[0][:16]} | dist={m[1]:.3f}km | FRP={m[2]:.1f}MW | part={m[3]}")
