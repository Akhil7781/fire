"""
Stage 8.32 Spatial and Temporal Partition Generator.
Strictly operates on Train (2018-2024, N=107) and Validation (2025, N=24) cohorts.
FROZEN 2026 TEST SET IS NEVER ACCESSED HERE.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")

def load_development_events() -> pd.DataFrame:
    df_feat = pd.read_parquet(PROJECT_ROOT / "data" / "interim" / "ds08_stage8_30_causal_features.parquet")
    dev_df = df_feat[(df_feat["horizon"] == "H0") & (df_feat["split"].isin(["train", "val"]))].copy()
    dev_df = dev_df.reset_index(drop=True)
    return dev_df

def assign_spatial_regions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assigns contiguous geographic macro-regions to each event:
    1. North: lat >= 26.0 (Punjab, Haryana, Uttarakhand, UP, North Rajasthan)
    2. Central_West: 20.0 <= lat < 26.0 and lon < 78.0 (Gujarat, West MP, West MH)
    3. Central_East: 20.0 <= lat < 26.0 and lon >= 78.0 (East MP, CG, Odisha, Jharkhand)
    4. South: lat < 20.0 (Maharashtra, Karnataka, AP, Tamil Nadu, Kerala)
    """
    regions = []
    for _, r in df.iterrows():
        lat = float(r["centroid_lat"])
        lon = float(r["centroid_lon"])
        if lat >= 26.0:
            regions.append("North")
        elif lat >= 20.0 and lon < 78.0:
            regions.append("Central_West")
        elif lat >= 20.0 and lon >= 78.0:
            regions.append("Central_East")
        else:
            regions.append("South")
    df = df.copy()
    df["spatial_region"] = regions
    return df

def get_splits(df: pd.DataFrame, seed: int = 42) -> Dict[str, Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Returns dataframes for:
    - 'random': 80/20 stratified split
    - 'temporal': 2018-2024 train (N=107) vs 2025 val (N=24)
    - 'spatial_block': Spatial holdout block (Central_West holdout, N=19 vs remaining N=112)
    """
    df = assign_spatial_regions(df)

    # 1. Temporal split
    train_temporal = df[df["split"] == "train"].copy().reset_index(drop=True)
    val_temporal = df[df["split"] == "val"].copy().reset_index(drop=True)

    # 2. Random split (stratified by class_id)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    train_idx, val_idx = next(skf.split(df, df["class_id"]))
    train_random = df.iloc[train_idx].copy().reset_index(drop=True)
    val_random = df.iloc[val_idx].copy().reset_index(drop=True)

    # 3. Spatial Block Split (Holdout: Central_West)
    train_spatial = df[df["spatial_region"] != "Central_West"].copy().reset_index(drop=True)
    val_spatial = df[df["spatial_region"] == "Central_West"].copy().reset_index(drop=True)

    return {
        "random": (train_random, val_random),
        "temporal": (train_temporal, val_temporal),
        "spatial_block": (train_spatial, val_spatial)
    }
