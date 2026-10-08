import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.persistence_expert.features import FEATURE_SCHEMA, build_persistence_features


def rows(times, *, lats=None, frps=None):
    n = len(times)
    return pd.DataFrame({
        "timestamp": times,
        "latitude": lats or [20.0] * n,
        "longitude": [78.0] * n,
        "frp": frps or [10.0] * n,
        "bright_ti4": [340.0 + i for i in range(n)],
        "bright_ti5": [300.0] * n,
        "daynight": ["N" if i % 2 else "D" for i in range(n)],
    })


def build(df):
    return build_persistence_features(df, t0="2025-01-01T00:00:00Z", latitude=20, longitude=78)


def test_rejects_any_future_timestamp():
    with pytest.raises(ValueError, match="historical_timestamp > t0"):
        build(rows(["2024-12-31T00:00:00Z", "2025-01-01T00:01:00Z"]))


def test_empty_history_is_finite_and_marked_unavailable():
    out = build(rows([]))
    assert out["history_detection_count"] == 0
    assert out["history_available"] == 0
    assert all(value == 0 for value in out.values())


def test_single_detection_has_no_interarrival():
    out = build(rows(["2024-12-01T00:00:00Z"]))
    assert out["history_available"] == 1
    assert out["median_interarrival_days"] == 0
    assert out["detections_30d"] == 0


def test_counts_active_days_and_irregular_interarrival():
    out = build(rows(["2024-12-01T00:00:00Z", "2024-12-02T00:00:00Z", "2024-12-10T00:00:00Z"]))
    assert out["history_detection_count"] == 3
    assert out["active_days_365d"] == 3
    assert out["median_interarrival_days"] == 4.5
    assert out["interarrival_cv"] > 0


def test_spatial_stability_and_thermal_summaries():
    out = build(rows(["2024-12-01T00:00:00Z", "2024-12-02T00:00:00Z"], frps=[10, 20]))
    assert out["radius_2km_ratio"] == 1
    assert out["spatial_dispersion_km"] == 0
    assert out["historical_frp_mean"] == 15
    assert out["historical_delta_ti_mean"] == 40.5
    assert out["historical_night_ratio"] == 0.5


def test_missing_measurements_do_not_produce_nonfinite_features():
    df = rows(["2024-12-01T00:00:00Z"])
    df.loc[0, ["frp", "bright_ti4", "bright_ti5", "daynight"]] = [None, None, None, None]
    out = build(df)
    assert all(pd.notna(value) for value in out.values())
    assert out["history_detection_count"] == 1
    assert out["historical_frp_mean"] == 0


def test_schema_is_compact_and_grouped():
    assert set(FEATURE_SCHEMA) == {"recurrence", "spatial", "thermal", "temporal", "quality"}
    assert len({name for group in FEATURE_SCHEMA.values() for name in group}) == 18
