import pandas as pd

df = pd.read_parquet('data/interim/causal_features_2025.parquet', columns=['detection_id', 'latitude', 'longitude', 'acq_datetime_utc', 'frp', 'partition'])

pb = df[(df['latitude'].between(30.1, 30.6)) & (df['longitude'].between(75.5, 76.5))]
pb = pb[(pb['acq_datetime_utc'] >= '2025-05-02') & (pb['acq_datetime_utc'] <= '2025-05-04T23:59:59')]
print(f"Punjab matches May 2-4: {len(pb)}")
for _, r in pb.head(10).iterrows():
    print(f"   {r['detection_id'][:16]} | lat={r['latitude']:.4f}, lon={r['longitude']:.4f} | {r['acq_datetime_utc']} | FRP={r['frp']:.1f} | part={r['partition']}")
