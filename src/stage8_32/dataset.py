"""
Stage 8.32 Dataset and Feature Group Processing Module.
Defines clean grouped feature schemas and strictly causal PyTorch Datasets.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")

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

def get_feature_groups(all_cols: List[str]) -> Dict[str, List[str]]:
    hist_cols = [c for c in all_cols if c.startswith("hist_")]
    return {
        "thermal": CURRENT_THERMAL_COLS,
        "historical": hist_cols,
        "industrial": INDUSTRIAL_CONTEXT_COLS,
        "ecoregion": ECOREGION_COLS,
        "geographic": GEOGRAPHIC_COLS
    }

class GroupedThermalDataset(Dataset):
    """
    Modular PyTorch Dataset returning grouped tensors for each physical modality.
    Scalers are fitted strictly on the training partition and applied to validation/test.
    """
    def __init__(
        self,
        df: pd.DataFrame,
        feature_groups: Dict[str, List[str]],
        scalers: Optional[Dict[str, Tuple[np.ndarray, np.ndarray]]] = None
    ):
        self.df = df.reset_index(drop=True)
        self.feature_groups = feature_groups
        self.scalers = {}

        self.tensors = {}
        for grp_name, cols in feature_groups.items():
            if len(cols) == 0:
                self.tensors[grp_name] = np.zeros((len(self.df), 0), dtype=np.float32)
                continue

            mat = self.df[cols].values.astype(np.float32)
            # Impute any nan with 0.0
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

        self.class_ids = self.df["class_id"].values.astype(np.int64) if "class_id" in self.df.columns else np.zeros(len(self.df), dtype=np.int64)
        self.event_ids = self.df["event_id"].tolist() if "event_id" in self.df.columns else [f"EVT_{i}" for i in range(len(self.df))]

    def get_scalers(self) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        return self.scalers

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        cid = self.class_ids[idx]
        is_persistent = 1 if cid == 3 else 0
        subclass_id = min(cid, 2) # 0=Ind, 1=For, 2=Agr (for acute)

        item = {
            "event_id": self.event_ids[idx],
            "class_id": torch.tensor(cid, dtype=torch.long),
            "is_persistent": torch.tensor(is_persistent, dtype=torch.long),
            "subclass_id": torch.tensor(subclass_id, dtype=torch.long)
        }

        for grp_name, mat in self.tensors.items():
            item[f"{grp_name}_feats"] = torch.tensor(mat[idx], dtype=torch.float32)

        return item
