"""
Causal historical and contemporaneous snapshot feature generation.

CRITICAL INVARIANTS:
1. Group A (Causal Historical): For every detection i, historical features may use
   ONLY observations that satisfy t_j < t_i. Future observations (t_j >= t_i) are strictly forbidden.
2. Group B (Contemporaneous Snapshot): |t_j - t_i| <= 15 minutes. Explicitly NON-CAUSAL.
   Must be documented as same-overpass snapshot context and barred from causal TCN sequence models.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from src.data.invariants import PreprocessingInvariantError, haversine_distance_meters
from src.data.spatial_index import LocalSpatialIndex


def compute_causal_and_snapshot_features(
    df: pd.DataFrame,
    spatial_index: LocalSpatialIndex,
    radius_meters: float = 2000.0,
    enforce_strict_causality: bool = True,
) -> pd.DataFrame:
    """
    Computes causal historical features (6h, 24h) and contemporaneous snapshot features (15m)
    for detections within a local causal context radius of 2 km.
    
    Inputs:
        df: DataFrame sorted chronologically containing:
            - latitude, longitude, timestamp_utc, frp, daynight, h3_res8
        spatial_index: Populated LocalSpatialIndex built over candidate detections
        radius_meters: Local causal context radius (default 2000.0 meters)
        enforce_strict_causality: When True, raises PreprocessingInvariantError if any t_j >= t_i
    """
    n_records = len(df)
    lats = df["latitude"].to_numpy(dtype=np.float64)
    lons = df["longitude"].to_numpy(dtype=np.float64)
    timestamps = df["timestamp_utc"].to_numpy(dtype=np.int64)
    frps = df["frp"].to_numpy(dtype=np.float32)
    daynights = df["daynight"].to_numpy()
    h3_cells = df["h3_res8"].tolist()

    # Pre-allocate output arrays
    # Group A: Causal Historical Features
    hist_count_6h = np.zeros(n_records, dtype=np.int32)
    hist_count_24h = np.zeros(n_records, dtype=np.int32)
    time_since_last_det = np.full(n_records, 86400.0, dtype=np.float32)  # 24h sentinel
    has_prior_24h = np.zeros(n_records, dtype=bool)
    mean_frp_6h = np.zeros(n_records, dtype=np.float32)
    max_frp_6h = np.zeros(n_records, dtype=np.float32)
    mean_frp_24h = np.zeros(n_records, dtype=np.float32)
    max_frp_24h = np.zeros(n_records, dtype=np.float32)
    day_ratio_24h = np.zeros(n_records, dtype=np.float32)
    spatial_dispersion_24h = np.zeros(n_records, dtype=np.float32)

    # Group B: Contemporaneous Snapshot Features (Non-causal overpass context)
    snapshot_co_detect_count = np.zeros(n_records, dtype=np.int32)

    window_6h_sec = 6 * 3600      # 21,600 s
    window_24h_sec = 24 * 3600    # 86,400 s
    snapshot_sec = 15 * 60        # 900 s

    for i in range(n_records):
        t_i = timestamps[i]
        lat_i = lats[i]
        lon_i = lons[i]
        cell_i = h3_cells[i]

        candidate_indices = spatial_index.query_candidates(cell_i)
        if not candidate_indices:
            continue

        # Accumulators for 6h and 24h causal history
        c_6h = 0
        c_24h = 0
        sum_frp_6h = 0.0
        peak_frp_6h = 0.0
        sum_frp_24h = 0.0
        peak_frp_24h = 0.0
        day_count_24h = 0
        sq_dist_sum_24h = 0.0
        latest_prior_time = -1

        # Accumulator for contemporaneous snapshot
        c_snapshot = 0

        for j in candidate_indices:
            t_j = timestamps[j]
            delta_t = t_i - t_j  # positive when j is in the past

            # 1. Contemporaneous Snapshot Check (|delta_t| <= 900 s, j != i)
            if j != i and abs(delta_t) <= snapshot_sec:
                dist = haversine_distance_meters(lat_i, lon_i, lats[j], lons[j])
                if dist <= radius_meters:
                    c_snapshot += 1

            # 2. Causal Historical Checks (Strictly delta_t > 0 <=> t_j < t_i)
            if delta_t <= 0:
                # Contemporaneous or future record: strictly barred from causal history
                continue

            if delta_t > window_24h_sec:
                # Beyond 24h historical window
                continue

            # Within 24-hour causal window; verify spatial distance
            dist = haversine_distance_meters(lat_i, lon_i, lats[j], lons[j])
            if dist > radius_meters:
                continue

            # Passed spatial and temporal causal filter for 24h
            if enforce_strict_causality and t_j >= t_i:
                raise PreprocessingInvariantError(
                    f"Causality violation detected at record {i}: historical record {j} has "
                    f"t_j ({t_j}) >= t_i ({t_i})."
                )

            c_24h += 1
            frp_j = frps[j]
            sum_frp_24h += frp_j
            if frp_j > peak_frp_24h:
                peak_frp_24h = frp_j

            if daynights[j] == "D":
                day_count_24h += 1

            sq_dist_sum_24h += dist * dist

            if t_j > latest_prior_time:
                latest_prior_time = t_j

            # Check 6h sub-window
            if delta_t <= window_6h_sec:
                c_6h += 1
                sum_frp_6h += frp_j
                if frp_j > peak_frp_6h:
                    peak_frp_6h = frp_j

        # Assign computed causal statistics
        hist_count_6h[i] = c_6h
        hist_count_24h[i] = c_24h

        if c_6h > 0:
            mean_frp_6h[i] = sum_frp_6h / c_6h
            max_frp_6h[i] = peak_frp_6h

        if c_24h > 0:
            has_prior_24h[i] = True
            time_since_last_det[i] = float(t_i - latest_prior_time)
            mean_frp_24h[i] = sum_frp_24h / c_24h
            max_frp_24h[i] = peak_frp_24h
            day_ratio_24h[i] = float(day_count_24h) / float(c_24h)
            spatial_dispersion_24h[i] = math.sqrt(sq_dist_sum_24h / float(c_24h))

        # Assign snapshot statistic
        snapshot_co_detect_count[i] = c_snapshot

    out = pd.DataFrame(
        {
            # Group A: Causal Historical Features (strictly t_j < t_i)
            "hist_count_6h_2km": hist_count_6h,
            "hist_count_24h_2km": hist_count_24h,
            "time_since_last_det_2km": time_since_last_det,
            "has_prior_24h_2km": has_prior_24h,
            "mean_frp_6h_2km": mean_frp_6h,
            "max_frp_6h_2km": max_frp_6h,
            "mean_frp_24h_2km": mean_frp_24h,
            "max_frp_24h_2km": max_frp_24h,
            "day_ratio_24h_2km": day_ratio_24h,
            "spatial_dispersion_24h_2km": spatial_dispersion_24h,
            # Group B: Contemporaneous Snapshot Features (explicitly non-causal overpass context)
            "snapshot_co_detect_count_2km": snapshot_co_detect_count,
        },
        index=df.index,
    )
    return out
