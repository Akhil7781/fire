import math
import pandas as pd
from pathlib import Path

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0)**2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

def test_t0_definitions():
    p_ev = Path("data/interim/ds08_stage8_25_physical_events.parquet")
    df_ev = pd.read_parquet(p_ev)
    p_firms = Path("data/interim/ds08_stage8_25_multiyear_firms.parquet")
    df_firms = pd.read_parquet(p_firms)
    df_firms["acq_dt"] = pd.to_datetime(df_firms["acq_datetime_utc"])
    
    print("Testing Case B: Alert time based on event_date / year:")
    for cid in [0, 1, 2, 3]:
        sub_ev = df_ev[df_ev["class_id"] == cid]
        cname = sub_ev["target_class"].iloc[0]
        hist_counts = []
        for _, ev in sub_ev.iterrows():
            dids = ev["detection_ids"]
            if not isinstance(dids, list):
                dids = dids.tolist()
            ev_dets = df_firms[df_firms["detection_id"].isin(dids)].sort_values("acq_dt")
            
            # For persistent sources, the alert in its assigned year:
            ev_yr = int(ev["year"])
            if cid == 3:
                # Alert detection is the detection in ev_yr
                curr_dets = ev_dets[ev_dets["acq_dt"].dt.year == ev_yr]
                if len(curr_dets) > 0:
                    t0 = curr_dets.iloc[0]["acq_dt"]
                else:
                    t0 = ev_dets.iloc[-1]["acq_dt"]
            else:
                t0 = ev_dets.iloc[0]["acq_dt"]
                
            t_hist_end = t0 - pd.Timedelta(days=7)
            lat0 = float(ev["centroid_lat"])
            lon0 = float(ev["centroid_lon"])
            
            cand = df_firms[
                (df_firms["acq_dt"] <= t_hist_end) &
                (df_firms["latitude"].between(lat0 - 0.03, lat0 + 0.03)) &
                (df_firms["longitude"].between(lon0 - 0.03, lon0 + 0.03))
            ]
            dists = [haversine_km(lat0, lon0, r["latitude"], r["longitude"]) for _, r in cand.iterrows()]
            n_2km = sum(1 for d in dists if d <= 2.0)
            hist_counts.append(n_2km)
            
        print(f"Class {cid} ({cname}): min={min(hist_counts)}, max={max(hist_counts)}, mean={sum(hist_counts)/len(hist_counts):.2f}")
        
    print("\nTest set (2026) under Case B:")
    test_ev = df_ev[df_ev["year"] == 2026]
    for cid in [0, 1, 2, 3]:
        sub = test_ev[test_ev["class_id"] == cid]
        cname = sub["target_class"].iloc[0]
        test_counts = []
        for _, ev in sub.iterrows():
            dids = ev["detection_ids"]
            if not isinstance(dids, list):
                dids = dids.tolist()
            ev_dets = df_firms[df_firms["detection_id"].isin(dids)].sort_values("acq_dt")
            ev_yr = int(ev["year"])
            if cid == 3:
                curr_dets = ev_dets[ev_dets["acq_dt"].dt.year == ev_yr]
                t0 = curr_dets.iloc[0]["acq_dt"] if len(curr_dets) > 0 else ev_dets.iloc[-1]["acq_dt"]
            else:
                t0 = ev_dets.iloc[0]["acq_dt"]
            t_hist_end = t0 - pd.Timedelta(days=7)
            lat0 = float(ev["centroid_lat"])
            lon0 = float(ev["centroid_lon"])
            cand = df_firms[
                (df_firms["acq_dt"] <= t_hist_end) &
                (df_firms["latitude"].between(lat0 - 0.03, lat0 + 0.03)) &
                (df_firms["longitude"].between(lon0 - 0.03, lon0 + 0.03))
            ]
            dists = [haversine_km(lat0, lon0, r["latitude"], r["longitude"]) for _, r in cand.iterrows()]
            n_2km = sum(1 for d in dists if d <= 2.0)
            test_counts.append(n_2km)
        print(f"Test Class {cid} ({cname}): counts={test_counts}")

if __name__ == "__main__":
    test_t0_definitions()
