"""
Data integrity assertions and invariant validation checks.
"""

from __future__ import annotations

import math
from typing import List, Tuple
import pandas as pd
import numpy as np


class PreprocessingInvariantError(Exception):
    """Raised when a core preprocessing or research invariant is violated."""
    pass


def verify_raw_dataframe(df: pd.DataFrame, source_name: str, expected_columns: List[str]) -> None:
    """
    Validates that raw dataframe contains exact expected columns,
    0 missing values, and 0 exact duplicate rows across all original columns.
    """
    missing_cols = [c for c in expected_columns if c not in df.columns]
    if missing_cols:
        raise PreprocessingInvariantError(
            f"Source '{source_name}' missing expected columns: {missing_cols}"
        )

    null_counts = df[expected_columns].isnull().sum()
    total_nulls = int(null_counts.sum())
    if total_nulls > 0:
        bad_cols = null_counts[null_counts > 0].to_dict()
        raise PreprocessingInvariantError(
            f"Source '{source_name}' contains {total_nulls} null values. Columns: {bad_cols}"
        )

    duplicate_count = int(df.duplicated(subset=expected_columns).sum())
    if duplicate_count > 0:
        raise PreprocessingInvariantError(
            f"Source '{source_name}' contains {duplicate_count} exact duplicate rows."
        )


def verify_id_uniqueness(df: pd.DataFrame, id_col: str = "detection_id") -> None:
    """
    Asserts detection_id.nunique() == len(df).
    """
    row_count = len(df)
    unique_count = int(df[id_col].nunique())
    if unique_count != row_count:
        raise PreprocessingInvariantError(
            f"Uniqueness violation on '{id_col}': {unique_count} unique IDs for {row_count} rows."
        )


def verify_temporal_monotonicity(timestamps: np.ndarray) -> None:
    """
    Asserts that master table timestamps are non-decreasing.
    """
    if len(timestamps) <= 1:
        return
    diffs = np.diff(timestamps)
    if np.any(diffs < 0):
        violating_idx = int(np.where(diffs < 0)[0][0])
        raise PreprocessingInvariantError(
            f"Temporal monotonicity violated at index {violating_idx}: "
            f"{timestamps[violating_idx]} > {timestamps[violating_idx + 1]}"
        )


def verify_causal_history(target_time: int, history_times: List[int]) -> None:
    """
    Strictly asserts that for detection i at target_time, every historical observation j
    satisfies t_j < t_i.
    """
    for t_j in history_times:
        if t_j >= target_time:
            raise PreprocessingInvariantError(
                f"Causality violation: Historical observation time {t_j} >= target time {target_time}."
            )


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two points on the WGS-84 sphere in meters.
    """
    r = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def verify_spatial_partition_buffer(
    train_coords: np.ndarray,
    test_coords: np.ndarray,
    min_buffer_meters: float = 25000.0,
) -> Tuple[bool, float]:
    """
    Verifies that all test coordinates maintain >= min_buffer_meters (default 25 km)
    separation from all train coordinates.
    """
    from scipy.spatial import cKDTree

    # Convert lat/lon to 3D Cartesian coordinates on unit sphere for exact fast KD-Tree radius search
    def to_cartesian(coords: np.ndarray) -> np.ndarray:
        lats = np.radians(coords[:, 0])
        lons = np.radians(coords[:, 1])
        x = np.cos(lats) * np.cos(lons)
        y = np.cos(lats) * np.sin(lons)
        z = np.sin(lats)
        return np.column_stack((x, y, z))

    train_xyz = to_cartesian(train_coords)
    test_xyz = to_cartesian(test_coords)

    tree = cKDTree(train_xyz)
    # Chord distance corresponding to great-circle buffer distance
    chord_threshold = 2.0 * math.sin((min_buffer_meters / 6371000.0) / 2.0)

    distances, _ = tree.query(test_xyz, k=1)
    min_chord = float(np.min(distances))
    min_meters = 2.0 * 6371000.0 * math.asin(min_chord / 2.0)

    if min_chord < chord_threshold:
        raise PreprocessingInvariantError(
            f"Spatial buffer violation: Closest test coordinate is {min_meters / 1000.0:.2f} km from train "
            f"(required >= {min_buffer_meters / 1000.0:.2f} km)."
        )

    return True, min_meters
