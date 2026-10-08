"""Stage 8.37 Production Causal Feature Generator.

Extracts the exact 41 clean causal features matching the Stage 8.36 frozen schema:
1. Thermal Anomaly Dynamics (14 features, t <= t0)
2. Industrial Context & Facility Geometry (6 features)
3. Land Cover / Ecoregion Context (3 features)
4. Multi-Scale Historical FIRMS Recurrence (18 features, t <= t0 - 7 days)

STRICT INVARIANTS:
- No future observations (strict t <= t0 cutoff).
- No lookahead into history (strict t <= t0 - 7 days cutoff).
- No target proxies (associated_* columns excluded).
- No raw geographic coordinates in feature tensors.
- No persistent registry lookup.
"""

import json
import logging
import math
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd

from src.stage8_37.inference.schemas import (
    ThermalEventInput,
    FirmsDetectionRecord,
    IndustrialContext,
    EcoregionContext,
    PersistenceEvidence
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
SCHEMA_PATH = PROJECT_ROOT / "models" / "stage8_36" / "feature_schema.json"
FACILITY_DB_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "industrial_facility_database.json"
HISTORICAL_FIRMS_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_25_multiyear_firms.parquet"

_CACHED_SCHEMA: Optional[dict] = None
_CACHED_FACILITIES: Optional[List[dict]] = None
_CACHED_HISTORICAL_DF: Optional[pd.DataFrame] = None

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two coordinates in kilometers."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

def compute_pairwise_max_distance(lats: np.ndarray, lons: np.ndarray) -> float:
    """Computes the maximum pairwise spatial distance in kilometers among points."""
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
    """Calculates forest biome score and agricultural heartland score for India."""
    # Forest biomes: Western Ghats, Himalayas, Central Highlands, Northeast, Odisha Highlands
    is_wg = (8.0 <= lat <= 16.0) and (73.0 <= lon <= 77.5)
    is_him = (lat >= 29.0) and (75.0 <= lon <= 89.0)
    is_ch = (20.0 <= lat <= 24.5) and (78.0 <= lon <= 85.0)
    is_ne = (lat >= 24.0) and (lon >= 90.0)
    is_od = (18.5 <= lat <= 22.0) and (83.0 <= lon <= 86.5)
    forest_score = 1.0 if (is_wg or is_him or is_ch or is_ne or is_od) else 0.0

    # Agricultural heartlands: Indo-Gangetic Plain, Krishna-Godavari, Cauvery, Malwa
    is_igp = (24.0 <= lat <= 31.5) and (74.0 <= lon <= 88.0) and not is_him
    is_kd = (15.5 <= lat <= 17.5) and (80.0 <= lon <= 82.5)
    is_cav = (10.5 <= lat <= 12.0) and (78.5 <= lon <= 80.0)
    is_mal = (21.5 <= lat <= 24.5) and (75.0 <= lon <= 78.0)
    agri_score = 1.0 if (is_igp or is_kd or is_cav or is_mal) else 0.0

    return forest_score, agri_score

def get_feature_schema() -> dict:
    """Loads and caches the frozen feature schema."""
    global _CACHED_SCHEMA
    if _CACHED_SCHEMA is not None:
        return _CACHED_SCHEMA
    assert SCHEMA_PATH.exists(), f"Schema file not found at {SCHEMA_PATH}"
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        _CACHED_SCHEMA = json.load(f)
    return _CACHED_SCHEMA

def get_industrial_facilities() -> List[dict]:
    """Loads and caches industrial facility database."""
    global _CACHED_FACILITIES
    if _CACHED_FACILITIES is not None:
        return _CACHED_FACILITIES
    assert FACILITY_DB_PATH.exists(), f"Facility DB missing at {FACILITY_DB_PATH}"
    with open(FACILITY_DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    _CACHED_FACILITIES = data.get("facilities", data)
    return _CACHED_FACILITIES

def get_historical_firms_archive() -> pd.DataFrame:
    """Loads and caches the historical multiyear FIRMS observations."""
    global _CACHED_HISTORICAL_DF
    if _CACHED_HISTORICAL_DF is not None:
        return _CACHED_HISTORICAL_DF
    if HISTORICAL_FIRMS_PATH.exists():
        df = pd.read_parquet(HISTORICAL_FIRMS_PATH)
        df["acq_dt"] = pd.to_datetime(df["acq_datetime_utc"])
        _CACHED_HISTORICAL_DF = df
    else:
        logger.warning(f"Historical FIRMS archive not found at {HISTORICAL_FIRMS_PATH}. Using empty fallback.")
        _CACHED_HISTORICAL_DF = pd.DataFrame(columns=[
            "detection_id", "latitude", "longitude", "acq_dt", "bright_ti4", "bright_ti5",
            "frp", "confidence", "daynight", "is_facility_baseline"
        ])
    return _CACHED_HISTORICAL_DF

class CausalFeatureBuilder:
    """Extracts the 41 clean causal features for an event."""

    def __init__(self):
        self.schema = get_feature_schema()
        self.facilities = get_industrial_facilities()
        self.historical_firms = get_historical_firms_archive()

    def build_features_for_event(
        self, event: ThermalEventInput
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """Constructs the 41 features for a single thermal event.

        Returns:
            Tuple of:
            - grouped_features: Dict[group_name -> np.ndarray of shape (1, D_group)]
            - metadata: Dict with contextual evidence, alert time, cutoffs
        """
        lat0 = event.centroid_lat
        lon0 = event.centroid_lon
        t0 = pd.to_datetime(event.event_start_time)
        t_hist_end = t0 - pd.Timedelta(days=7)

        # -------------------------------------------------------------
        # 1. Thermal Anomaly Dynamics (t <= t0)
        # -------------------------------------------------------------
        # Sort current event detections up to alert time t0
        dets = [d for d in event.detections if pd.to_datetime(d.acq_datetime_utc) <= t0]
        if len(dets) == 0 and len(event.detections) > 0:
            dets = [event.detections[0]]  # Fallback to initial detection
        elif len(dets) == 0:
            # Minimal synthetic fallback detection
            dets = [FirmsDetectionRecord(
                latitude=lat0, longitude=lon0, acq_date=str(t0.date()),
                acq_time=t0.strftime("%H%M"), acq_datetime_utc=t0.isoformat(),
                bright_ti4=330.0, bright_ti5=295.0, frp=15.0, confidence="nominal", daynight="D"
            )]

        dets.sort(key=lambda d: pd.to_datetime(d.acq_datetime_utc))
        curr_det = dets[-1]
        first_det = dets[0]

        curr_frp = float(curr_det.frp)
        curr_ti4 = float(curr_det.bright_ti4)
        curr_ti5 = float(curr_det.bright_ti5)
        curr_delta_ti = float(curr_ti4 - curr_ti5)
        curr_is_night = 1.0 if curr_det.daynight == "N" else 0.0

        n_seen = len(dets)
        t_last = pd.to_datetime(curr_det.acq_datetime_utc)
        elapsed_hours = max((t_last - t0).total_seconds() / 3600.0, 0.0)

        frps_seen = [d.frp for d in dets]
        mean_frp_so_far = float(np.mean(frps_seen))
        max_frp_so_far = float(np.max(frps_seen))
        std_frp_so_far = float(np.std(frps_seen)) if n_seen > 1 else 0.0
        night_ratio_so_far = float(np.mean([1.0 if d.daynight == "N" else 0.0 for d in dets]))

        lats_seen = np.array([d.latitude for d in dets])
        lons_seen = np.array([d.longitude for d in dets])
        spatial_extent_so_far = compute_pairwise_max_distance(lats_seen, lons_seen)

        frp_trend_so_far = (
            float((curr_frp - float(first_det.frp)) / max(elapsed_hours, 0.5))
            if n_seen > 1 else 0.0
        )

        if n_seen > 1:
            t_prev = pd.to_datetime(dets[-2].acq_datetime_utc)
            time_since_prev_h = float((t_last - t_prev).total_seconds() / 3600.0)
        else:
            time_since_prev_h = 0.0

        thermal_dict = {
            "current_frp": curr_frp,
            "current_bright_ti4": curr_ti4,
            "current_bright_ti5": curr_ti5,
            "current_delta_ti": curr_delta_ti,
            "current_is_night": curr_is_night,
            "detections_observed_so_far": float(n_seen),
            "elapsed_observation_hours": elapsed_hours,
            "mean_frp_observed_so_far": mean_frp_so_far,
            "max_frp_observed_so_far": max_frp_so_far,
            "std_frp_observed_so_far": std_frp_so_far,
            "night_ratio_observed_so_far": night_ratio_so_far,
            "spatial_extent_observed_so_far": spatial_extent_so_far,
            "frp_trend_observed_so_far": frp_trend_so_far,
            "time_since_prev_h": time_since_prev_h
        }

        # -------------------------------------------------------------
        # 2. Industrial Context & Facility Geometry
        # -------------------------------------------------------------
        min_fac_dist = float("inf")
        nearest_fac_name = None
        for fac in self.facilities:
            d = haversine_km(lat0, lon0, float(fac["latitude"]), float(fac["longitude"]))
            if d < min_fac_dist:
                min_fac_dist = d
                nearest_fac_name = fac.get("facility_name", fac.get("name", "Unknown Facility"))

        within_1km_fac = 1.0 if min_fac_dist <= 1.0 else 0.0
        within_5km_fac = 1.0 if min_fac_dist <= 5.0 else 0.0

        facility_baseline_frp = 5.0 if within_5km_fac > 0.5 else 0.0
        facility_baseline_std = 1.0
        frp_deviation = max(curr_frp - facility_baseline_frp, 0.0) if within_5km_fac > 0.5 else 0.0
        facility_frp_zscore = float(frp_deviation / max(facility_baseline_std, 1.0)) if within_5km_fac > 0.5 else 0.0

        industrial_dict = {
            "dist_to_fac_km": float(min_fac_dist),
            "within_1km_fac": within_1km_fac,
            "within_5km_fac": within_5km_fac,
            "facility_baseline_frp": facility_baseline_frp,
            "frp_deviation": frp_deviation,
            "facility_frp_zscore": facility_frp_zscore
        }

        industrial_context = IndustrialContext(
            nearest_facility_name=nearest_fac_name,
            nearest_facility_distance_km=float(round(min_fac_dist, 2)),
            within_1km_fac=within_1km_fac,
            within_5km_fac=within_5km_fac,
            facility_baseline_frp=facility_baseline_frp,
            facility_context_available=True
        )

        # -------------------------------------------------------------
        # 3. Land Cover / Ecoregion Context
        # -------------------------------------------------------------
        forest_score, agri_score = compute_ecoregion_scores(lat0, lon0)
        s2_avail = 0.0

        ecoregion_dict = {
            "forest_biome_score": forest_score,
            "agri_heartland_score": agri_score,
            "s2_available": s2_avail
        }

        ecoregion_context = EcoregionContext(
            forest_biome_score=forest_score,
            agri_heartland_score=agri_score,
            s2_available=s2_avail,
            ecoregion_context_available=True
        )

        # -------------------------------------------------------------
        # 4. Multi-Scale Historical Recurrence (t <= t0 - 7 days)
        # -------------------------------------------------------------
        df_hist = self.historical_firms
        # Filter strictly by causal cutoff and 5km bounding box
        deg_buf = 5.0 / 111.0
        cand_hist = df_hist[
            (df_hist["acq_dt"] <= t_hist_end) &
            (df_hist["latitude"].between(lat0 - deg_buf, lat0 + deg_buf)) &
            (df_hist["longitude"].between(lon0 - deg_buf, lon0 + deg_buf))
        ].copy()

        # Exclude any detection from current event
        ev_did_set = {d.detection_id for d in event.detections if d.detection_id}
        if len(cand_hist) > 0 and len(ev_did_set) > 0:
            cand_hist = cand_hist[~cand_hist["detection_id"].isin(ev_did_set)].copy()

        if len(cand_hist) > 0:
            dists = [haversine_km(lat0, lon0, r["latitude"], r["longitude"]) for _, r in cand_hist.iterrows()]
            cand_hist["dist_km"] = dists
            hist_2km = cand_hist[cand_hist["dist_km"] <= 2.0].sort_values("acq_dt").reset_index(drop=True)
            hist_1km = cand_hist[cand_hist["dist_km"] <= 1.0]
            hist_5km = cand_hist[cand_hist["dist_km"] <= 5.0]
            latest_hist_ts = hist_2km["acq_dt"].max() if len(hist_2km) > 0 else None
        else:
            hist_2km = pd.DataFrame()
            hist_1km = pd.DataFrame()
            hist_5km = pd.DataFrame()
            latest_hist_ts = None

        n_hist = len(hist_2km)
        hist_count_full = float(n_hist)
        hist_count_1km = float(len(hist_1km))
        hist_count_2km = float(n_hist)
        hist_count_5km = float(len(hist_5km))

        if n_hist > 0:
            frps_h = hist_2km["frp"].values.astype(np.float32)
            ti4s_h = hist_2km["bright_ti4"].values.astype(np.float32)
            ti5s_h = hist_2km["bright_ti5"].values.astype(np.float32)
            dts_h = hist_2km["acq_dt"]

            hist_mean_frp_full = float(np.mean(frps_h))
            hist_max_frp_full = float(np.max(frps_h))
            hist_std_frp_full = float(np.std(frps_h)) if n_hist > 1 else 0.0
            hist_cv_frp_full = float(hist_std_frp_full / max(hist_mean_frp_full, 1e-3))
            hist_active_days_full = float(dts_h.dt.date.nunique())
            hist_active_months_full = float(dts_h.dt.tz_localize(None).dt.to_period("M").nunique())
            hist_night_ratio_full = float(np.mean(hist_2km["daynight"] == "N"))
            hist_mean_delta_ti_full = float(np.mean(ti4s_h - ti5s_h))
            hist_distinct_calendar_months = float(dts_h.dt.month.nunique())
            hist_dispersion = compute_pairwise_max_distance(hist_2km["latitude"].values, hist_2km["longitude"].values) if n_hist > 1 else 0.0
            hist_days_since_latest = float((t0 - latest_hist_ts).total_seconds() / 86400.0) if latest_hist_ts else 9999.0

            # Window counts
            t_365 = t0 - pd.Timedelta(days=365)
            t_90 = t0 - pd.Timedelta(days=90)
            t_30 = t0 - pd.Timedelta(days=30)
            hist_count_365d = float(len(hist_2km[hist_2km["acq_dt"] >= t_365]))
            hist_count_90d = float(len(hist_2km[hist_2km["acq_dt"] >= t_90]))
            hist_count_30d = float(len(hist_2km[hist_2km["acq_dt"] >= t_30]))
        else:
            hist_mean_frp_full = 0.0
            hist_max_frp_full = 0.0
            hist_std_frp_full = 0.0
            hist_cv_frp_full = 0.0
            hist_active_days_full = 0.0
            hist_active_months_full = 0.0
            hist_night_ratio_full = 0.0
            hist_mean_delta_ti_full = 0.0
            hist_distinct_calendar_months = 0.0
            hist_dispersion = 0.0
            hist_days_since_latest = 9999.0
            hist_count_365d = 0.0
            hist_count_90d = 0.0
            hist_count_30d = 0.0

        historical_dict = {
            "hist_count_full": hist_count_full,
            "hist_active_days_full": hist_active_days_full,
            "hist_active_months_full": hist_active_months_full,
            "hist_mean_frp_full": hist_mean_frp_full,
            "hist_max_frp_full": hist_max_frp_full,
            "hist_std_frp_full": hist_std_frp_full,
            "hist_cv_frp_full": hist_cv_frp_full,
            "hist_count_1km": hist_count_1km,
            "hist_count_2km": hist_count_2km,
            "hist_count_5km": hist_count_5km,
            "hist_dispersion": hist_dispersion,
            "hist_distinct_calendar_months": hist_distinct_calendar_months,
            "hist_days_since_latest": hist_days_since_latest,
            "hist_count_365d": hist_count_365d,
            "hist_count_90d": hist_count_90d,
            "hist_count_30d": hist_count_30d,
            "hist_night_ratio_full": hist_night_ratio_full,
            "hist_mean_delta_ti_full": hist_mean_delta_ti_full
        }

        # Determine human-readable persistence evidence level
        if hist_distinct_calendar_months >= 3 and hist_count_full >= 8:
            pers_level = "STRONG"
        elif hist_distinct_calendar_months >= 2 or hist_count_full >= 4:
            pers_level = "MODERATE"
        else:
            pers_level = "LOW"

        persistence_evidence = PersistenceEvidence(
            level=pers_level,
            historical_detection_count=hist_count_full,
            historical_active_days=hist_active_days_full,
            historical_active_months=hist_active_months_full,
            time_since_previous_detection_days=float(round(hist_days_since_latest, 1)),
            historical_mean_frp=float(round(hist_mean_frp_full, 2)),
            historical_night_ratio=float(round(hist_night_ratio_full, 3)),
            distinct_calendar_months=hist_distinct_calendar_months
        )

        # -------------------------------------------------------------
        # 5. Format arrays matching exact schema order
        # -------------------------------------------------------------
        schema_groups = self.schema["feature_groups"]
        raw_grouped_arrays = {
            "thermal": np.array([[thermal_dict[c] for c in schema_groups["thermal"]]], dtype=np.float32),
            "industrial": np.array([[industrial_dict[c] for c in schema_groups["industrial"]]], dtype=np.float32),
            "ecoregion": np.array([[ecoregion_dict[c] for c in schema_groups["ecoregion"]]], dtype=np.float32),
            "historical": np.array([[historical_dict[c] for c in schema_groups["historical"]]], dtype=np.float32)
        }

        metadata = {
            "alert_time": str(t0),
            "historical_cutoff": str(t_hist_end),
            "industrial_context": industrial_context,
            "ecoregion_context": ecoregion_context,
            "persistence_evidence": persistence_evidence,
            "thermal_dict": thermal_dict,
            "industrial_dict": industrial_dict,
            "ecoregion_dict": ecoregion_dict,
            "historical_dict": historical_dict
        }

        return raw_grouped_arrays, metadata
