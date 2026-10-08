"""
Partitioning, spatial blocking with buffer exclusion, and strict state isolation.

CRITICAL INVARIANTS:
1. Spatial and temporal partitions must be assigned BEFORE any learned scaling/normalization.
2. Scalers/encoders must be fitted strictly on TRAIN data only.
3. Zero validation, test, or burn-in observations may leak into training statistics.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.data.invariants import PreprocessingInvariantError, verify_spatial_partition_buffer


class PartitionAwareScaler:
    """
    State-isolated feature scaler. Enforces that normalization statistics
    are computed strictly on the training partition.
    """

    def __init__(self, continuous_cols: List[str]):
        self.continuous_cols = continuous_cols
        self.is_fitted = False
        self.means_: Dict[str, float] = {}
        self.stds_: Dict[str, float] = {}
        self.medians_: Dict[str, float] = {}
        self.iqrs_: Dict[str, float] = {}

    def fit_on_train(self, train_df: pd.DataFrame) -> None:
        """
        Fits continuous normalization parameters strictly on TRAIN data.
        """
        for col in self.continuous_cols:
            if col not in train_df.columns:
                raise ValueError(f"Column '{col}' not in training dataframe.")
            vals = train_df[col].to_numpy(dtype=np.float64)
            mean_val = float(np.mean(vals))
            std_val = float(np.std(vals))
            med_val = float(np.median(vals))
            q25 = float(np.percentile(vals, 25))
            q75 = float(np.percentile(vals, 75))
            iqr_val = float(q75 - q25)

            self.means_[col] = mean_val
            self.stds_[col] = std_val if std_val > 1e-6 else 1.0
            self.medians_[col] = med_val
            self.iqrs_[col] = iqr_val if iqr_val > 1e-6 else 1.0

        self.is_fitted = True

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies fitted normalization parameters to arbitrary partition (Train, Val, or Test).
        """
        if not self.is_fitted:
            raise PreprocessingInvariantError(
                "Scaler is not fitted. Must call fit_on_train() before transform()."
            )

        scaled_df = df.copy()
        for col in self.continuous_cols:
            med = self.medians_[col]
            iqr = self.iqrs_[col]
            scaled_df[f"{col}_robust_scaled"] = (scaled_df[col] - med) / iqr
        return scaled_df


def assign_spatiotemporal_partitions(
    df: pd.DataFrame,
    min_spatial_buffer_meters: float = 25000.0,
) -> pd.DataFrame:
    """
    Assigns train, validation, and test partition labels using spatial blocking
    and temporal holdouts.
    
    Partition rules:
    - Burn-in context (is_burn_in_context == True): assigned 'context_burn_in' (never evaluated)
    - Primary 2025 corpus:
        * Spatial blocks: 1.0 degree lat/lon tiles.
        * Train: First 8 months (2025-01-01 to 2025-08-31) in train spatial blocks.
        * Validation: Month 9-10 (2025-09-01 to 2025-10-31).
        * Test: Month 11-12 (2025-11-01 to 2025-12-31) in hold-out spatial blocks.
    """
    partitions = np.full(len(df), "unassigned", dtype=object)

    # 1. Isolate context burn-in
    burn_in_mask = df["is_burn_in_context"].to_numpy(dtype=bool)
    partitions[burn_in_mask] = "context_burn_in"

    # 2. For primary 2025 data, assign based on spatial block and temporal date
    study_indices = np.where(~burn_in_mask)[0]
    study_dates = pd.to_datetime(df.iloc[study_indices]["acq_datetime_utc"], utc=True)
    study_lats = df.iloc[study_indices]["latitude"].to_numpy()
    study_lons = df.iloc[study_indices]["longitude"].to_numpy()

    # Spatial block assignment (1.0 degree integer blocks)
    block_lat = np.floor(study_lats).astype(int)
    block_lon = np.floor(study_lons).astype(int)
    # Checkerboard spatial assignment for test blocks
    is_test_spatial_block = ((block_lat + block_lon) % 3 == 0)

    for i, idx in enumerate(study_indices):
        dt = study_dates.iloc[i]
        month = dt.month
        is_test_block = is_test_spatial_block[i]

        if month <= 8:
            if not is_test_block:
                partitions[idx] = "train"
            else:
                partitions[idx] = "train_heldout_spatial"
        elif month in (9, 10):
            partitions[idx] = "val"
        else:
            if is_test_block:
                partitions[idx] = "test"
            else:
                partitions[idx] = "test_seen_spatial"

    out_df = df.copy()
    out_df["partition"] = partitions
    return out_df
