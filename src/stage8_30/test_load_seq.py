import pandas as pd
import numpy as np
from pathlib import Path

def test_load_seq():
    p_seq = Path("data/interim/ds08_stage8_30_historical_sequences.parquet")
    df_seq = pd.read_parquet(p_seq)
    print("Columns:", df_seq.columns.tolist())
    for idx, r in df_seq.head(5).iterrows():
        st = r["seq_tensor"]
        print(f"Row {idx} type: {type(st)}, len: {len(st)}")
        if len(st) > 0:
            arr = np.array([list(x) for x in st], dtype=np.float32)
            print("  arr shape:", arr.shape)
        else:
            arr = np.zeros((0, 11), dtype=np.float32)
            print("  arr shape:", arr.shape)

if __name__ == "__main__":
    test_load_seq()
