import pandas as pd

df = pd.read_parquet('data/interim/causal_features_2025.parquet', columns=['detection_id', 'latitude', 'longitude', 'acq_datetime_utc', 'frp', 'partition'])

# Search in MP (lat 22.5 to 23.5, lon 76.5 to 78.0) in April 2025
mp = df[(df['latitude'].between(22.8, 23.5)) & (df['longitude'].between(76.5, 77.8))]
mp = mp[(mp['acq_datetime_utc'] >= '2025-04-01') & (mp['acq_datetime_utc'] <= '2025-04-15T23:59:59')]
print(f"MP agricultural detections: {len(mp)}")
for _, r in mp.head(10).iterrows():
    print(f"   {r['detection_id'][:16]} | lat={r['latitude']:.4f}, lon={r['longitude']:.4f} | {r['acq_datetime_utc']} | FRP={r['frp']:.1f} | part={r['partition']}")
