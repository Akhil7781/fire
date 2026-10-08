import pandas as pd
from pathlib import Path

def check_pre_2018():
    p_firms = Path("data/interim/ds08_stage8_25_multiyear_firms.parquet")
    df = pd.read_parquet(p_firms)
    df["acq_dt"] = pd.to_datetime(df["acq_datetime_utc"])
    pre = df[df["acq_dt"] < "2018-03-08"]
    print("Detections before 2018-03-08:", len(pre))
    print(pre[["detection_id", "acq_dt", "latitude", "longitude", "source_product"]])

if __name__ == "__main__":
    check_pre_2018()
