"""
Stage 8.33 Dataset & Feature Pipeline Module.
Implements modular grouped tabular features and causal historical FIRMS sequence processing.
STRICT TEST LOCK: ZERO READS OF FROZEN 2026 TEST COHORT.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CURRENT_THERMAL_COLS = [
    "current_frp", "current_bright_ti4", "current_bright_ti5", "current_delta_ti", "current_is_night",
    "detections_observed_so_far", "elapsed_observation_hours", "mean_frp_observed_so_far",
    "max_frp_observed_so_far", "std_frp_observed_so_far", "night_ratio_observed_so_far",
    "spatial_extent_observed_so_far", "frp_trend_observed_so_far", "time_since_prev_h"
]

INDUSTRIAL_CONTEXT_COLS = [
    "dist_to_fac_km", "within_1km_fac", "within_5km_fac",
    "facility_baseline_frp", "frp_deviation", "facility_frp_zscore"
]

ECOREGION_COLS = [
    "forest_biome_score", "agri_heartland_score", "s2_available"
]

GEOGRAPHIC_COLS = [
    "centroid_lat", "centroid_lon"
]

def load_development_features() -> pd.DataFrame:
    """
    Loads development features dataframe strictly for train and val splits at H0 horizon.
    VERIFIES that no 2026 test events are present.
    """
    df_feat = pd.read_parquet(PROJECT_ROOT / "data" / "interim" / "ds08_stage8_30_causal_features.parquet")
    dev_df = df_feat[(df_feat["horizon"] == "H0") & (df_feat["split"].isin(["train", "val"]))].copy().reset_index(drop=True)
    assert "test" not in dev_df["split"].values, "Violation: Test events loaded in development dataset"
    assert len(dev_df) == 131, f"Expected 131 dev events, got {len(dev_df)}"
    return dev_df

def load_development_sequences() -> Dict[str, np.ndarray]:
    """
    Loads causal historical FIRMS sequences strictly for development events.
    Returns dict mapping event_id -> (seq_len, 11) float32 numpy array.
    """
    df_seq = pd.read_parquet(PROJECT_ROOT / "data" / "interim" / "ds08_stage8_30_historical_sequences.parquet")
    dev_seq = df_seq[df_seq["split"].isin(["train", "val"])].copy().reset_index(drop=True)
    assert "test" not in dev_seq["split"].values, "Violation: Test events loaded in development sequences"
    seq_dict = {}
    for _, row in dev_seq.iterrows():
        eid = row["event_id"]
        t = row["seq_tensor"]
        if len(t) > 0:
            arr = np.array([np.asarray(x, dtype=np.float32) for x in t], dtype=np.float32)
        else:
            arr = np.zeros((0, 11), dtype=np.float32)
        seq_dict[eid] = arr
    return seq_dict

def get_feature_groups(all_cols: List[str], include_geo: bool = True) -> Dict[str, List[str]]:
    """Returns explicit dictionary of feature names by group."""
    hist_cols = sorted([c for c in all_cols if c.startswith("hist_")])
    groups = {
        "thermal": CURRENT_THERMAL_COLS,
        "historical": hist_cols,
        "industrial": INDUSTRIAL_CONTEXT_COLS,
        "ecoregion": ECOREGION_COLS,
    }
    if include_geo:
        groups["geographic"] = GEOGRAPHIC_COLS
    return groups

class MultiModalThermalDataset(Dataset):
    """
    PyTorch Dataset providing:
    - Grouped tabular features (thermal, historical, industrial, ecoregion, geographic)
    - Padded historical sequence tensor (seq_len, 11) and length/mask for TCN/GRU models.
    - Labels: class_id (0..3), is_persistent (0..1), subclass_id (0..2 for acute fires).
    Scalers are strictly fitted on the training split only.
    """
    def __init__(
        self,
        df: pd.DataFrame,
        feature_groups: Dict[str, List[str]],
        scalers: Optional[Dict[str, Tuple[np.ndarray, np.ndarray]]] = None,
        seq_dict: Optional[Dict[str, np.ndarray]] = None,
        max_seq_len: int = 50
    ):
        self.df = df.reset_index(drop=True)
        self.feature_groups = feature_groups
        self.scalers = {}
        self.tensors = {}
        self.seq_dict = seq_dict
        self.max_seq_len = max_seq_len

        # Process tabular feature groups
        for grp_name, cols in feature_groups.items():
            if len(cols) == 0:
                self.tensors[grp_name] = np.zeros((len(self.df), 0), dtype=np.float32)
                continue

            mat = self.df[cols].values.astype(np.float32)
            mat = np.nan_to_num(mat, nan=0.0, posinf=0.0, neginf=0.0)

            if scalers is None or grp_name not in scalers:
                mean = np.mean(mat, axis=0)
                std = np.std(mat, axis=0)
                std[std < 1e-5] = 1.0
                self.scalers[grp_name] = (mean, std)
            else:
                mean, std = scalers[grp_name]
                self.scalers[grp_name] = (mean, std)

            norm_mat = (mat - mean) / std
            self.tensors[grp_name] = norm_mat.astype(np.float32)

        # Labels
        self.class_ids = self.df["class_id"].values.astype(np.int64) if "class_id" in self.df.columns else np.zeros(len(self.df), dtype=np.int64)
        self.event_ids = self.df["event_id"].tolist() if "event_id" in self.df.columns else [f"EVT_{i}" for i in range(len(self.df))]

        # Precompute padded sequence tensors if seq_dict provided
        self.has_sequences = self.seq_dict is not None
        if self.has_sequences:
            n_events = len(self.df)
            self.padded_seqs = np.zeros((n_events, self.max_seq_len, 11), dtype=np.float32)
            self.seq_lengths = np.zeros(n_events, dtype=np.int64)
            self.seq_masks = np.zeros((n_events, self.max_seq_len), dtype=np.float32)

            for i, eid in enumerate(self.event_ids):
                if eid in self.seq_dict:
                    raw_s = self.seq_dict[eid]
                    length = min(len(raw_s), self.max_seq_len)
                    self.seq_lengths[i] = length
                    if length > 0:
                        # Most recent `length` observations
                        self.padded_seqs[i, :length, :] = raw_s[-length:, :]
                        self.seq_masks[i, :length] = 1.0

    def get_scalers(self) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        return self.scalers

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        cid = int(self.class_ids[idx])
        is_persistent = 1 if cid == 3 else 0
        subclass_id = min(cid, 2)  # 0=Ind, 1=For, 2=Agr for acute

        item = {
            "event_id": self.event_ids[idx],
            "class_id": torch.tensor(cid, dtype=torch.long),
            "is_persistent": torch.tensor(is_persistent, dtype=torch.long),
            "subclass_id": torch.tensor(subclass_id, dtype=torch.long)
        }

        # Tabular features
        for grp_name, mat in self.tensors.items():
            item[f"{grp_name}_feats"] = torch.tensor(mat[idx], dtype=torch.float32)

        # Sequence features
        if self.has_sequences:
            item["seq_tensor"] = torch.tensor(self.padded_seqs[idx], dtype=torch.float32)
            item["seq_len"] = torch.tensor(self.seq_lengths[idx], dtype=torch.long)
            item["seq_mask"] = torch.tensor(self.seq_masks[idx], dtype=torch.float32)

        return item
