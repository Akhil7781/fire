import pandas as pd
import json
import math

EARTH_RADIUS_KM = 6371.0

def geodesic_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return EARTH_RADIUS_KM * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

df = pd.read_parquet('data/interim/causal_features_2025.parquet', columns=['detection_id', 'latitude', 'longitude', 'acq_datetime_utc', 'frp', 'partition'])
df['acq_dt'] = pd.to_datetime(df['acq_datetime_utc'], utc=True)

with open('data/reference/agriculture/raw_agricultural_fires_2025.json', 'r', encoding='utf-8') as f:
    events = json.load(f)

print(f"Total IARI reference events: {len(events)}")

for ev in events:
    rec_id = ev['record_id']
    ev_lat = ev['latitude']
    ev_lon = ev['longitude']
    t_start = pd.to_datetime(ev['start_utc'], utc=True)
    t_end = pd.to_datetime(ev['end_utc'], utc=True)
    
    # 12h buffer
    t_min = t_start - pd.Timedelta(hours=12.0)
    t_max = t_end + pd.Timedelta(hours=12.0)
    
    sub = df[(df['latitude'].between(ev_lat - 0.1, ev_lat + 0.1)) & 
             (df['longitude'].between(ev_lon - 0.1, ev_lon + 0.1))]
    sub = sub[(sub['acq_dt'] >= t_min) & (sub['acq_dt'] <= t_max)]
    
    matches = []
    for _, r in sub.iterrows():
        d = geodesic_distance_km(r['latitude'], r['longitude'], ev_lat, ev_lon)
        if d <= 5.0:
            matches.append((r['detection_id'], d, r['frp'], r['partition'], r['acq_dt']))
            
    print(f"\n{rec_id} ({ev['district']}, {ev['state']} - {ev['crop_type']}):")
    print(f"   Matches within 5.0 km & +/-12h: {len(matches)}")
    for m in matches[:5]:
        print(f"      {m[0][:16]} | dist={m[1]:.2f}km | FRP={m[2]:.1f}MW | part={m[3]} | time={m[4]}")
