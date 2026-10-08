import pandas as pd

df = pd.read_parquet('data/interim/causal_features_2025.parquet', columns=['detection_id', 'latitude', 'longitude', 'acq_datetime_utc', 'frp', 'partition'])

# Check training partition in April/May 2025
train_df = df[df['partition'] == 'train']
print(f"Total train partition rows: {len(train_df):,}")

rabi_train = train_df[(train_df['acq_datetime_utc'] >= '2025-04-01') & (train_df['acq_datetime_utc'] <= '2025-05-31T23:59:59')]
print(f"Rabi window in train partition: {len(rabi_train):,} detections")

# Check distribution in key agricultural states:
# Punjab (lat 29.5-32.5, lon 74.0-76.8)
# Haryana (lat 27.5-30.8, lon 74.5-77.5)
# MP Sehore/Malwa (lat 22.5-24.5, lon 75.5-77.5)
pb = rabi_train[(rabi_train['latitude'].between(29.8, 31.8)) & (rabi_train['longitude'].between(74.5, 76.5))]
print(f"Punjab agricultural detections in train (Rabi): {len(pb):,}")

hr = rabi_train[(rabi_train['latitude'].between(28.5, 30.5)) & (rabi_train['longitude'].between(76.0, 77.5))]
print(f"Haryana agricultural detections in train (Rabi): {len(hr):,}")

mp = rabi_train[(rabi_train['latitude'].between(22.5, 24.0)) & (rabi_train['longitude'].between(76.0, 77.5))]
print(f"MP agricultural detections in train (Rabi): {len(mp):,}")
