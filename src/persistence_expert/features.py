"""Compact persistence summaries computed only from pre-alert FIRMS records.

This module deliberately accepts no event labels, registries, or future records.
The caller supplies the alert cutoff and a detection table; any row after t0 is
rejected instead of silently discarded so a bad upstream join is visible.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd

FEATURE_SCHEMA: Mapping[str, tuple[str, ...]] = {
    "recurrence": (
        "detections_30d", "detections_90d", "detections_365d",
        "active_days_365d", "active_months_365d", "median_interarrival_days",
        "interarrival_cv",
    ),
    "spatial": (
        "radius_2km_ratio", "centroid_distance_mean_km", "spatial_dispersion_km",
    ),
    "thermal": (
        "historical_frp_mean", "historical_frp_cv", "historical_delta_ti_mean",
        "historical_delta_ti_std",
    ),
    "temporal": ("historical_night_ratio", "recurrence_month_count"),
    "quality": ("history_detection_count", "history_available"),
}

REQUIRED_COLUMNS = ("timestamp", "latitude", "longitude", "frp", "bright_ti4", "bright_ti5", "daynight")


def _haversine_km(lat: np.ndarray, lon: np.ndarray, lat0: float, lon0: float) -> np.ndarray:
    p1 = np.radians(lat0)
    p2 = np.radians(lat)
    dp = p2 - p1
    dl = np.radians(lon - lon0)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 6371.0088 * 2 * np.arctan2(np.sqrt(a), np.sqrt(np.maximum(0, 1 - a)))


def build_persistence_features(
    detections: pd.DataFrame,
    *,
    t0: object,
    latitude: float,
    longitude: float,
) -> dict[str, float]:
    """Summarize detections at/before t0; rejects future timestamps explicitly.

    Coordinates are supplied from the current alert. Detections are filtered to
    a 5 km neighborhood, then summaries are calculated over that local history.
    Missing histories produce zero-valued summaries plus history_available=0.
    """
    cutoff = pd.Timestamp(t0)
    if cutoff.tzinfo is None:
        cutoff = cutoff.tz_localize("UTC")
    else:
        cutoff = cutoff.tz_convert("UTC")
    missing = set(REQUIRED_COLUMNS).difference(detections.columns)
    if missing:
        raise ValueError(f"Missing FIRMS columns: {sorted(missing)}")

    ts = pd.to_datetime(detections["timestamp"], utc=True, errors="raise")
    if (ts > cutoff).any():
        raise ValueError("Causality violation: historical_timestamp > t0")
    d = detections.copy()
    d["_timestamp"] = ts
    lat = pd.to_numeric(d["latitude"], errors="coerce").to_numpy(float)
    lon = pd.to_numeric(d["longitude"], errors="coerce").to_numpy(float)
    d["_distance_km"] = _haversine_km(lat, lon, float(latitude), float(longitude))
    d = d.loc[d["_distance_km"] <= 5.0].sort_values("_timestamp").copy()

    names = [name for group in FEATURE_SCHEMA.values() for name in group]
    out = {name: 0.0 for name in names}
    n = len(d)
    out["history_detection_count"] = float(n)
    out["history_available"] = float(n > 0)
    if not n:
        return out

    age_days = (cutoff - d["_timestamp"]).dt.total_seconds() / 86400.0
    for window in (30, 90, 365):
        out[f"detections_{window}d"] = float((age_days <= window).sum())
    out["active_days_365d"] = float(d.loc[age_days <= 365, "_timestamp"].dt.floor("D").nunique())
    out["active_months_365d"] = float(d.loc[age_days <= 365, "_timestamp"].dt.strftime("%Y-%m").nunique())
    out["recurrence_month_count"] = float(d["_timestamp"].dt.month.nunique())

    times = d["_timestamp"].drop_duplicates().sort_values()
    gaps = times.diff().dropna().dt.total_seconds().to_numpy(float) / 86400.0
    if len(gaps):
        med = float(np.median(gaps))
        out["median_interarrival_days"] = med
        out["interarrival_cv"] = float(np.std(gaps) / max(np.mean(gaps), 1e-12))

    dist = d["_distance_km"].to_numpy(float)
    out["radius_2km_ratio"] = float(np.mean(dist <= 2.0))
    out["centroid_distance_mean_km"] = float(np.mean(dist))
    out["spatial_dispersion_km"] = float(np.sqrt(np.mean(dist ** 2)))

    frp = pd.to_numeric(d["frp"], errors="coerce").to_numpy(float)
    frp = frp[np.isfinite(frp)]
    if len(frp):
        out["historical_frp_mean"] = float(np.mean(frp))
        out["historical_frp_cv"] = float(np.std(frp) / max(abs(float(np.mean(frp))), 1e-12))
    delta = pd.to_numeric(d["bright_ti4"], errors="coerce") - pd.to_numeric(d["bright_ti5"], errors="coerce")
    delta = delta.to_numpy(float)
    delta = delta[np.isfinite(delta)]
    if len(delta):
        out["historical_delta_ti_mean"] = float(np.mean(delta))
        out["historical_delta_ti_std"] = float(np.std(delta))
    daynight = d["daynight"].astype(str).str.upper()
    valid = daynight.isin(("D", "N"))
    if valid.any():
        out["historical_night_ratio"] = float((daynight[valid] == "N").mean())
    return out
