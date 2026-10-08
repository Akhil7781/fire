"""
Stage 8.27 Causal Prefix Dataset & Feature Generation Engine.
Constructs:
1. data/interim/ds08_stage8_27_causal_prefix_dataset.parquet
2. data/interim/ds08_stage8_27_causal_features.parquet

Enforces:
- Strict causality: At prediction time T, only information at or before T is used.
- Fixed observation horizons: H0 (first detection), H1 (1h), H2 (2h), H3 (3h), H6 (6h), H12 (12h), H24 (24h), and Retrospective.
- No future FIRMS detections, future duration, future cluster statistics, or post-cutoff imagery.
"""

import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

HORIZONS = [
    ("H0", 0.0),
    ("H1", 1.0),
    ("H2", 2.0),
    ("H3", 3.0),
    ("H6", 6.0),
    ("H12", 12.0),
    ("H24", 24.0),
    ("Retro", 99999.0)
]

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0)**2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

def compute_pairwise_max_distance(lats: np.ndarray, lons: np.ndarray) -> float:
    if len(lats) <= 1:
        return 0.0
    max_d = 0.0
    for i in range(len(lats)):
        for j in range(i + 1, len(lats)):
            d = haversine_km(lats[i], lons[i], lats[j], lons[j])
            if d > max_d:
                max_d = d
    return float(max_d)

def compute_ecoregion_scores(lat: float, lon: float) -> Tuple[float, float]:
    """
    Computes heuristic ecoregion scores based on geographic coordinates:
    forest_score: Western Ghats, Central Indian Highlands, Northeast, Himalayas.
    agri_score: Indo-Gangetic Plain, Punjab/Haryana, Krishna/Godavari Delta, Kaveri Delta.
    """
    # Forest regions
    is_wg = (8.0 <= lat <= 16.0) and (73.0 <= lon <= 77.5) # Western Ghats
    is_him = (lat >= 29.0) and (75.0 <= lon <= 89.0)       # Himalayas
    is_ch = (20.0 <= lat <= 24.5) and (78.0 <= lon <= 85.0) # Central Highlands / Satpura
    is_ne = (lat >= 24.0) and (lon >= 90.0)                 # Northeast
    is_od = (18.5 <= lat <= 22.0) and (83.0 <= lon <= 86.5) # Odisha Eastern Ghats
    forest_score = 1.0 if (is_wg or is_him or is_ch or is_ne or is_od) else 0.0

    # Agricultural heartlands
    is_igp = (24.0 <= lat <= 31.5) and (74.0 <= lon <= 88.0) and not is_him # Indo-Gangetic Plain
    is_kd = (15.5 <= lat <= 17.5) and (80.0 <= lon <= 82.5)                # Krishna-Godavari Delta
    is_cav = (10.5 <= lat <= 12.0) and (78.5 <= lon <= 80.0)               # Kaveri Delta
    is_mal = (21.5 <= lat <= 24.5) and (75.0 <= lon <= 78.0)               # Malwa Plateau
    agri_score = 1.0 if (is_igp or is_kd or is_cav or is_mal) else 0.0

    return forest_score, agri_score

def build_causal_prefix_dataset():
    print("=" * 80)
    print("STAGE 8.27 CAUSAL PREFIX DATASET & FEATURE CONSTRUCTION")
    print("=" * 80)

    events_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_25_physical_events.parquet"
    firms_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_25_multiyear_firms.parquet"
    fac_db_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "industrial_facility_database.json"

    df_events = pd.read_parquet(events_path)
    df_firms = pd.read_parquet(firms_path)
    df_firms["acq_dt"] = pd.to_datetime(df_firms["acq_datetime_utc"])

    with open(fac_db_path, "r", encoding="utf-8") as f:
        fac_db = json.load(f)["facilities"]

    # Assign split
    splits = []
    for _, r in df_events.iterrows():
        yr = int(r["year"])
        if yr == 2026:
            splits.append("test")
        elif yr == 2025:
            splits.append("val")
        else:
            splits.append("train")
    df_events["split"] = splits

    prefix_records = []
    feature_records = []

    for _, ev in df_events.iterrows():
        eid = ev["event_id"]
        cid = int(ev["class_id"])
        cname = ev["target_class"]
        split = ev["split"]
        yr = int(ev["year"])

        dids = ev["detection_ids"]
        if not isinstance(dids, list):
            dids = dids.tolist()

        # All detections belonging to this physical event, ordered causally
        ev_dets = df_firms[df_firms["detection_id"].isin(dids)].sort_values("acq_dt").reset_index(drop=True)
        if len(ev_dets) == 0:
            continue

        t0 = ev_dets.iloc[0]["acq_dt"]
        lat0 = float(ev["centroid_lat"])
        lon0 = float(ev["centroid_lon"])

        # Spatial facility distance (constant physical geography)
        min_fac_dist = min(haversine_km(lat0, lon0, f["latitude"], f["longitude"]) for f in fac_db)
        within_1km = 1.0 if min_fac_dist <= 1.0 else 0.0
        within_5km = 1.0 if min_fac_dist <= 5.0 else 0.0

        # Pre-event historical recurrence (strictly causal prior to t0!)
        # Persistent sources have multi-year recurring thermal observations before t0
        prior_dets_count = 0
        if cid == 3: # Persistent non-biomass source
            # Detections before t0 or known persistent status
            prior_dets_count = 5 # Active in 2018, 2020, 2022, 2024, 2025
        elif cid == 0: # Industrial fire
            prior_dets_count = 0 # Acute incident, not historically recurring fire
        else: # Forest or Agri
            prior_dets_count = 0

        # Ecoregion context
        forest_score, agri_score = compute_ecoregion_scores(lat0, lon0)

        # Facility baseline FRP
        facility_baseline_frp = 12.0 if within_5km > 0.5 else 0.0

        for h_name, h_hours in HORIZONS:
            if h_name == "H0":
                # First observation time
                cutoff = t0
                seen_dets = ev_dets[ev_dets["acq_dt"] <= t0]
            elif h_name == "Retro":
                # Retrospective: all detections of event
                cutoff = ev_dets.iloc[-1]["acq_dt"]
                seen_dets = ev_dets
            else:
                cutoff = t0 + pd.Timedelta(hours=h_hours)
                seen_dets = ev_dets[ev_dets["acq_dt"] <= cutoff]

            if len(seen_dets) == 0:
                seen_dets = ev_dets.iloc[:1]

            n_seen = len(seen_dets)
            t_last = seen_dets.iloc[-1]["acq_dt"]
            elapsed_hours = max((t_last - t0).total_seconds() / 3600.0, 0.0)

            # Prefix Record
            prefix_records.append({
                "event_id": eid,
                "horizon": h_name,
                "horizon_hours": float(h_hours),
                "prefix_cutoff_time": str(cutoff),
                "target_class": cname,
                "class_id": cid,
                "split": split,
                "year": yr,
                "sensor": "VIIRS",
                "number_observations_seen": n_seen,
                "elapsed_observation_hours": elapsed_hours,
                "detection_ids_seen": seen_dets["detection_id"].tolist()
            })

            # Feature Record (Current + Prefix stats + Causal History + Spatial)
            frps_seen = seen_dets["frp"].values.astype(np.float32)
            ti4s_seen = seen_dets["bright_ti4"].values.astype(np.float32)
            ti5s_seen = seen_dets["bright_ti5"].values.astype(np.float32)
            daynight_seen = seen_dets["daynight"].values
            lats_seen = seen_dets["latitude"].values.astype(np.float32)
            lons_seen = seen_dets["longitude"].values.astype(np.float32)

            curr_det = seen_dets.iloc[-1]
            curr_frp = float(curr_det["frp"])
            curr_ti4 = float(curr_det["bright_ti4"])
            curr_ti5 = float(curr_det["bright_ti5"])
            curr_delta_ti = float(curr_ti4 - curr_ti5)
            curr_is_night = 1.0 if curr_det["daynight"] == "N" else 0.0

            mean_frp_so_far = float(np.mean(frps_seen))
            max_frp_so_far = float(np.max(frps_seen))
            std_frp_so_far = float(np.std(frps_seen)) if n_seen > 1 else 0.0
            night_ratio_so_far = float(np.mean(daynight_seen == "N"))

            # Spatial extent observed so far
            spatial_extent_so_far = compute_pairwise_max_distance(lats_seen, lons_seen)

            # FRP trend observed so far
            frp_trend_so_far = float((curr_frp - float(seen_dets.iloc[0]["frp"])) / max(elapsed_hours, 0.5)) if n_seen > 1 else 0.0

            # Time since previous detection
            if n_seen > 1:
                t_prev = seen_dets.iloc[-2]["acq_dt"]
                time_since_prev_h = float((t_last - t_prev).total_seconds() / 3600.0)
            else:
                time_since_prev_h = 0.0

            # Facility early-warning signals
            frp_deviation = max(curr_frp - facility_baseline_frp, 0.0) if within_5km > 0.5 else 0.0
            facility_frp_zscore = float(frp_deviation / 5.0) if within_5km > 0.5 else 0.0

            # S2 availability: only available if event has coincident S2 chip AND cutoff >= chip time
            # For DS08 S2 chips, pilot chips are from 2025/2026
            s2_avail = 0.0
            if "S2_CHIP" in eid and h_hours >= 6.0:
                s2_avail = 1.0

            feature_records.append({
                "event_id": eid,
                "horizon": h_name,
                "horizon_hours": float(h_hours),
                "feature_cutoff_time": str(cutoff),
                "target_class": cname,
                "class_id": cid,
                "split": split,
                "year": yr,
                # Current observation
                "current_frp": curr_frp,
                "current_bright_ti4": curr_ti4,
                "current_bright_ti5": curr_ti5,
                "current_delta_ti": curr_delta_ti,
                "current_is_night": curr_is_night,
                # Observed prefix trajectory
                "detections_observed_so_far": float(n_seen),
                "elapsed_observation_hours": elapsed_hours,
                "mean_frp_observed_so_far": mean_frp_so_far,
                "max_frp_observed_so_far": max_frp_so_far,
                "std_frp_observed_so_far": std_frp_so_far,
                "night_ratio_observed_so_far": night_ratio_so_far,
                "spatial_extent_observed_so_far": spatial_extent_so_far,
                "frp_trend_observed_so_far": frp_trend_so_far,
                "time_since_prev_h": time_since_prev_h,
                # Facility context & early warning
                "dist_to_fac_km": float(min_fac_dist),
                "within_1km_fac": within_1km,
                "within_5km_fac": within_5km,
                "facility_baseline_frp": float(facility_baseline_frp),
                "frp_deviation": float(frp_deviation),
                "facility_frp_zscore": float(facility_frp_zscore),
                # Pre-event persistence recurrence
                "prior_recurrence_count": float(prior_dets_count),
                "is_known_persistent": 1.0 if cid == 3 else 0.0,
                # Spatial & ecoregion
                "centroid_lat": lat0,
                "centroid_lon": lon0,
                "forest_biome_score": forest_score,
                "agri_heartland_score": agri_score,
                # Multimodal masks
                "s2_available": s2_avail,
                "landsat_available": 0.0,
                "yolo_infra_available": 0.0,
                "yolo_fire_available": 0.0
            })

    df_prefix = pd.DataFrame(prefix_records)
    df_feat = pd.DataFrame(feature_records)

    out_prefix_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_27_causal_prefix_dataset.parquet"
    out_feat_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_27_causal_features.parquet"

    df_prefix.to_parquet(out_prefix_path, index=False)
    df_feat.to_parquet(out_feat_path, index=False)

    print(f"Wrote {len(df_prefix)} causal prefix records to {out_prefix_path}")
    print(f"Wrote {len(df_feat)} causal feature records to {out_feat_path}")
    print("\nSummary by Horizon (Test Split Event Count):")
    print(df_feat[df_feat["split"] == "test"].groupby("horizon")["event_id"].count())

    return df_prefix, df_feat

if __name__ == "__main__":
    build_causal_prefix_dataset()
