import pandas as pd
from pathlib import Path

def inspect_test_prefixes():
    p = Path("data/interim/ds08_stage8_28_causal_prefix_dataset.parquet")
    df = pd.read_parquet(p)
    h0 = df[(df["split"] == "test") & (df["horizon"] == "H0")]
    print(f"Test H0 count: {len(h0)}")
    for idx, r in h0.iterrows():
        print(f"{r['event_id']} (class {r['class_id']}, {r['target_class']}):")
        print(f"  first_detection_time={r['first_detection_time']}, prefix_cutoff_time={r['prefix_cutoff_time']}")
        print(f"  earliest_timestamp={r['earliest_timestamp']}, latest_timestamp={r['latest_timestamp']}")
        print(f"  n_seen={r['number_observations_seen']}, dids_seen={r['detection_ids_seen']}")

if __name__ == "__main__":
    inspect_test_prefixes()
