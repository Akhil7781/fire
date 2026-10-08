import os
import glob
import pandas as pd
from pathlib import Path

def explore():
    print("=== Exploring FIRMS Sources ===")
    p_multi = Path("data/interim/ds08_stage8_25_multiyear_firms.parquet")
    if p_multi.exists():
        df_multi = pd.read_parquet(p_multi)
        print(f"multiyear_firms.parquet: {len(df_multi)} rows, columns: {df_multi.columns.tolist()}")
        print(f"multiyear dates: {df_multi['acq_datetime_utc'].min()} to {df_multi['acq_datetime_utc'].max()}")

    p_events = Path("data/interim/ds08_stage8_25_physical_events.parquet")
    if p_events.exists():
        df_events = pd.read_parquet(p_events)
        print(f"physical_events.parquet: {len(df_events)} rows")
        print(df_events["target_class"].value_counts())
        print("Years:", df_events["year"].value_counts())

    # Check 2025 FIRMS
    p_2025 = Path("causal_features_2025.parquet")
    if p_2025.exists():
        print(f"causal_features_2025.parquet exists: {os.path.getsize(p_2025):,} bytes")

    # Check raw_multiyear folder
    raw_files = list(Path("data/raw_multiyear").glob("*.csv"))
    print(f"raw_multiyear CSV count: {len(raw_files)}")

if __name__ == "__main__":
    explore()
