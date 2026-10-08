import pandas as pd
from pathlib import Path

def verify():
    p_feat = Path("data/interim/ds08_stage8_30_causal_features.parquet")
    df = pd.read_parquet(p_feat)
    print("Features shape:", df.shape)
    h0 = df[df["horizon"] == "H0"]
    print("H0 count:", len(h0), "Split counts:", h0["split"].value_counts().to_dict())
    print("Class counts at H0:", h0["class_id"].value_counts().to_dict())

    # Check historical sequence
    p_seq = Path("data/interim/ds08_stage8_30_historical_sequences.parquet")
    df_seq = pd.read_parquet(p_seq)
    print("Sequences shape:", df_seq.shape)
    print("Max seq len:", df_seq["seq_len"].max(), "Mean seq len:", df_seq["seq_len"].mean())
    for cid in range(4):
        sub = df_seq[df_seq["class_id"] == cid]
        print(f"Class {cid} seq_len: min={sub['seq_len'].min()}, max={sub['seq_len'].max()}, mean={sub['seq_len'].mean():.2f}")

if __name__ == "__main__":
    verify()
