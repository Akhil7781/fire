import pandas as pd

labels = pd.read_parquet('data/processed/labels/master_labels_2025.parquet')
feats = pd.read_parquet('data/interim/causal_features_2025.parquet', columns=['detection_id', 'latitude', 'longitude', 'acq_datetime_utc', 'frp', 'partition'])
m = labels[labels['label_class'] == 3].merge(feats, on='detection_id')
for idx, r in m.iterrows():
    print(f"{r['detection_id'][:16]} | {r['acq_datetime_utc']} | lat={r['latitude']:.4f}, lon={r['longitude']:.4f} | dist={r['spatial_distance_km']:.3f}km | dt={r['temporal_difference_hours']:.2f}h | ev_id={r['primary_evidence_id']} | part={r['partition']}")
