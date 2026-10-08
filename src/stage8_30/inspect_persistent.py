import pandas as pd
from pathlib import Path

def inspect_persistent():
    p_ev = Path("data/interim/ds08_stage8_25_physical_events.parquet")
    df_ev = pd.read_parquet(p_ev)
    pers = df_ev[df_ev["class_id"] == 3]
    
    p_firms = Path("data/interim/ds08_stage8_25_multiyear_firms.parquet")
    df_firms = pd.read_parquet(p_firms)
    df_firms["acq_dt"] = pd.to_datetime(df_firms["acq_datetime_utc"])
    
    print(f"Total persistent events: {len(pers)}")
    for yr in [2024, 2025, 2026]:
        sub = pers[pers["year"] == yr]
        print(f"\nYear {yr} persistent events ({len(sub)} events):")
        for idx, row in sub.head(3).iterrows():
            dids = row["detection_ids"]
            dets = df_firms[df_firms["detection_id"].isin(dids)].sort_values("acq_dt")
            print(f"  {row['event_id']}: event_start={row['event_start']}, event_end={row['event_end']}")
            print(f"    dets dates: {dets['acq_dt'].tolist()}")

if __name__ == "__main__":
    inspect_persistent()
