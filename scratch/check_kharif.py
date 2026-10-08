import pandas as pd

df = pd.read_parquet('data/interim/causal_features_2025.parquet', columns=['detection_id', 'latitude', 'longitude', 'acq_datetime_utc', 'frp', 'partition'])

# Check Kharif (October - November 2025) in Punjab/Haryana
kharif = df[(df['latitude'].between(29.5, 31.5)) & (df['longitude'].between(74.5, 76.5))]
kharif_oct = kharif[(kharif['acq_datetime_utc'] >= '2025-10-25') & (kharif['acq_datetime_utc'] <= '2025-10-31T23:59:59')]
kharif_nov = kharif[(kharif['acq_datetime_utc'] >= '2025-11-01') & (kharif['acq_datetime_utc'] <= '2025-11-10T23:59:59')]

print(f"Kharif late Oct (val): {len(kharif_oct)}")
print(f"Kharif early Nov (test): {len(kharif_nov)}")
