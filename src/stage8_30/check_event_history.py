import math
import numpy as np
import pandas as pd
from pathlib import Path

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0)**2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

def check_event_history():
    events_path = Path("data/interim/ds08_stage8_25_physical_events.parquet")
    firms_path = Path("data/interim/ds08_stage8_25_multiyear_firms.parquet")
    
    df_events = pd.read_parquet(events_path)
    df_firms = pd.read_parquet(firms_path)
    df_firms["acq_dt"] = pd.to_datetime(df_firms["acq_datetime_utc"])
    
    print(f"Total events: {len(df_events)}, Total FIRMS detections: {len(df_firms)}")
    
    results = []
    for _, ev in df_events.iterrows():
        eid = ev["event_id"]
        cid = int(ev["class_id"])
        cname = ev["target_class"]
        lat0 = float(ev["centroid_lat"])
        lon0 = float(ev["centroid_lon"])
        dids = ev["detection_ids"]
        if not isinstance(dids, list):
            dids = dids.tolist()
            
        ev_dets = df_firms[df_firms["detection_id"].isin(dids)].sort_values("acq_dt")
        if len(ev_dets) == 0:
            continue
            
        t0 = ev_dets.iloc[0]["acq_dt"]
        t_hist_end = t0 - pd.Timedelta(days=7)
        
        # Historical detections before t_hist_end
        # Spatial filter: within 5km bounding box first
        deg_buf = 5.0 / 111.0 # ~0.045 deg
        cand = df_firms[
            (df_firms["acq_dt"] <= t_hist_end) &
            (df_firms["latitude"].between(lat0 - deg_buf, lat0 + deg_buf)) &
            (df_firms["longitude"].between(lon0 - deg_buf, lon0 + deg_buf))
        ].copy()
        
        # Calculate exact distances
        dists = [haversine_km(lat0, lon0, r["latitude"], r["longitude"]) for _, r in cand.iterrows()]
        cand["dist_km"] = dists
        
        n_1km = (cand["dist_km"] <= 1.0).sum()
        n_2km = (cand["dist_km"] <= 2.0).sum()
        n_5km = (cand["dist_km"] <= 5.0).sum()
        
        # Check that no target event detection leaked
        target_overlap = set(cand["detection_id"]).intersection(set(dids))
        assert len(target_overlap) == 0, f"Leakage: {target_overlap}"
        
        results.append({
            "event_id": eid,
            "class_id": cid,
            "target_class": cname,
            "year": ev["year"],
            "t0": str(t0),
            "t_hist_end": str(t_hist_end),
            "n_1km": n_1km,
            "n_2km": n_2km,
            "n_5km": n_5km
        })
        
    df_res = pd.DataFrame(results)
    print("\nSummary by class of historical detections within 2km (before t0 - 7 days):")
    for cid, grp in df_res.groupby("class_id"):
        cname = grp["target_class"].iloc[0]
        print(f"Class {cid} ({cname}): count={len(grp)}, mean_n2km={grp['n_2km'].mean():.2f}, max_n2km={grp['n_2km'].max()}, sum_n2km={grp['n_2km'].sum()}")
        
    print("\nTest events (2026) breakdown:")
    test_res = df_res[df_res["year"] == 2026]
    for cid, grp in test_res.groupby("class_id"):
        cname = grp["target_class"].iloc[0]
        print(f"Test Class {cid} ({cname}): count={len(grp)}, mean_n2km={grp['n_2km'].mean():.2f}, sum_n2km={grp['n_2km'].sum()}, n2km_values={grp['n_2km'].tolist()}")

if __name__ == "__main__":
    check_event_history()
