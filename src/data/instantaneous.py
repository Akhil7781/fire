"""
Deterministic, stateless instantaneous and cyclical feature computations.
All features in this module have explicit physical and mathematical formulations.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_instantaneous_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes deterministic instantaneous thermal and geometric features.
    
    Inputs:
        df: DataFrame containing bright_ti4, bright_ti5, scan, track, frp,
            acq_datetime_utc, longitude.
            
    Returns:
        DataFrame containing computed features:
        - delta_t (Kelvin)
        - temp_ratio (dimensionless)
        - pixel_area (km^2)
        - frp_density (MW/km^2)
        - frp_log1p (log(1 + FRP))
        - sin_diurnal, cos_diurnal
        - sin_lst, cos_lst
        - sin_annual, cos_annual
    """
    # 1. Thermal and Geometric Features
    ti4 = df["bright_ti4"].to_numpy(dtype=np.float32)
    ti5 = df["bright_ti5"].to_numpy(dtype=np.float32)
    scan = df["scan"].to_numpy(dtype=np.float32)
    track = df["track"].to_numpy(dtype=np.float32)
    frp = df["frp"].to_numpy(dtype=np.float32)

    delta_t = ti4 - ti5
    temp_ratio = ti4 / np.maximum(ti5, 1e-3)
    pixel_area = scan * track
    frp_density = frp / np.maximum(pixel_area, 1e-4)
    frp_log1p = np.log1p(np.maximum(frp, 0.0))

    # 2. Datetime Parsing for Cyclical Features
    datetimes = pd.to_datetime(df["acq_datetime_utc"], utc=True)
    hours = datetimes.dt.hour.to_numpy(dtype=np.float64)
    minutes = datetimes.dt.minute.to_numpy(dtype=np.float64)
    seconds = datetimes.dt.second.to_numpy(dtype=np.float64)
    hour_frac = hours + (minutes / 60.0) + (seconds / 3600.0)

    # Diurnal harmonics (UTC base)
    theta_diurnal = (2.0 * np.pi * hour_frac) / 24.0
    sin_diurnal = np.sin(theta_diurnal).astype(np.float32)
    cos_diurnal = np.cos(theta_diurnal).astype(np.float32)

    # Local Solar Time (LST)
    lons = df["longitude"].to_numpy(dtype=np.float64)
    solar_offset_hours = lons / 15.0
    lst = np.mod(hour_frac + solar_offset_hours, 24.0)
    theta_lst = (2.0 * np.pi * lst) / 24.0
    sin_lst = np.sin(theta_lst).astype(np.float32)
    cos_lst = np.cos(theta_lst).astype(np.float32)

    # Annual seasonal harmonics
    doy = datetimes.dt.dayofyear.to_numpy(dtype=np.float64)
    theta_annual = (2.0 * np.pi * (doy - 1.0)) / 365.25
    sin_annual = np.sin(theta_annual).astype(np.float32)
    cos_annual = np.cos(theta_annual).astype(np.float32)

    out = pd.DataFrame(
        {
            "delta_t": delta_t,
            "temp_ratio": temp_ratio,
            "pixel_area": pixel_area,
            "frp_density": frp_density,
            "frp_log1p": frp_log1p,
            "sin_diurnal": sin_diurnal,
            "cos_diurnal": cos_diurnal,
            "sin_lst": sin_lst,
            "cos_lst": cos_lst,
            "sin_annual": sin_annual,
            "cos_annual": cos_annual,
        },
        index=df.index,
    )
    return out
