"""
Training and Evaluation Engine for Stage 8.30.
"""

import copy
import json
import math
import os
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_30.models import (
    HistoricalThermalRecurrenceEncoder,
    CurrentThermalEncoder,
    RegistryFreeCausalClassifier,
    compute_hierarchical_probabilities,
)

CURR_COLS = [
    "current_frp", "current_bright_ti4", "current_bright_ti5", "current_delta_ti", "current_is_night",
    "detections_observed_so_far", "elapsed_observation_hours", "mean_frp_observed_so_far",
    "max_frp_observed_so_far", "std_frp_observed_so_far", "night_ratio_observed_so_far",
    "spatial_extent_observed_so_far", "frp_trend_observed_so_far", "time_since_prev_h"
]

GEO_COLS = [
    "dist_to_fac_km", "within_1km_fac", "within_5km_fac", "facility_baseline_frp",
    "frp_deviation", "facility_frp_zscore", "centroid_lat", "centroid_lon",
    "forest_biome_score", "agri_heartland_score", "s2_available"
]

def seed_everything(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

class ThermalEventDataset(Dataset):
    def __init__(
        self,
        features_df: pd.DataFrame,
        sequences_dict: Dict[str, np.ndarray],
        curr_cols: List[str],
        geo_cols: List[str],
        hist_sum_cols: List[str],
        curr_scaler: Tuple[np.ndarray, np.ndarray] = None,
        geo_scaler: Tuple[np.ndarray, np.ndarray] = None,
        hist_scaler: Tuple[np.ndarray, np.ndarray] = None,
        max_seq_len: int = 40
    ):
        self.df = features_df.reset_index(drop=True)
        self.sequences_dict = sequences_dict
        self.curr_cols = curr_cols
        self.geo_cols = geo_cols
        self.hist_sum_cols = hist_sum_cols
        self.max_seq_len = max_seq_len

        curr_mat = self.df[curr_cols].values.astype(np.float32)
        geo_mat = self.df[geo_cols].values.astype(np.float32)
        hist_mat = self.df[hist_sum_cols].values.astype(np.float32)

        # Scale features
        if curr_scaler is None:
            self.curr_mean = np.mean(curr_mat, axis=0)
            self.curr_std = np.std(curr_mat, axis=0) + 1e-5
        else:
            self.curr_mean, self.curr_std = curr_scaler

        if geo_scaler is None:
            self.geo_mean = np.mean(geo_mat, axis=0)
            self.geo_std = np.std(geo_mat, axis=0) + 1e-5
        else:
            self.geo_mean, self.geo_std = geo_scaler

        if hist_scaler is None:
            self.hist_mean = np.mean(hist_mat, axis=0)
            self.hist_std = np.std(hist_mat, axis=0) + 1e-5
        else:
            self.hist_mean, self.hist_std = hist_scaler

        self.curr_norm = (curr_mat - self.curr_mean) / self.curr_std
        self.geo_norm = (geo_mat - self.geo_mean) / self.geo_std
        self.hist_norm = (hist_mat - self.hist_mean) / self.hist_std

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        eid = row["event_id"]
        cid = int(row["class_id"])

        seq = self.sequences_dict.get(eid, np.zeros((0, 11), dtype=np.float32))
        L = len(seq)
        if L > self.max_seq_len:
            # Keep most recent historical detections
            seq = seq[-self.max_seq_len:]
            L = self.max_seq_len

        pad_seq = np.zeros((self.max_seq_len, 11), dtype=np.float32)
        mask = np.zeros(self.max_seq_len, dtype=bool)
        if L > 0:
            pad_seq[:L] = seq
            mask[:L] = True

        return {
            "event_id": eid,
            "horizon": row.get("horizon", "H0"),
            "class_id": torch.tensor(cid, dtype=torch.long),
            "is_persistent": torch.tensor(1 if cid == 3 else 0, dtype=torch.long),
            "subclass_id": torch.tensor(min(cid, 2), dtype=torch.long),
            "curr_feats": torch.tensor(self.curr_norm[idx], dtype=torch.float32),
            "geo_feats": torch.tensor(self.geo_norm[idx], dtype=torch.float32),
            "hist_sum_feats": torch.tensor(self.hist_norm[idx], dtype=torch.float32),
            "hist_seq": torch.tensor(pad_seq, dtype=torch.float32),
            "hist_mask": torch.tensor(mask, dtype=torch.bool)
        }

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    acc = float(np.mean(y_true == y_pred))
    classes = [0, 1, 2, 3]
    f1s = []
    recalls = []
    for c in classes:
        tp = np.sum((y_true == c) & (y_pred == c))
        fp = np.sum((y_true != c) & (y_pred == c))
        fn = np.sum((y_true == c) & (y_pred != c))
        p = tp / max(tp + fp, 1e-9)
        r = tp / max(tp + fn, 1e-9)
        f1 = (2 * p * r) / max(p + r, 1e-9)
        f1s.append(f1)
        recalls.append(r)

    macro_f1 = float(np.mean(f1s))
    balanced_acc = float(np.mean(recalls))
    return {
        "accuracy": acc,
        "macro_f1": macro_f1,
        "balanced_acc": balanced_acc,
        "f1_ind": float(f1s[0]),
        "f1_for": float(f1s[1]),
        "f1_agr": float(f1s[2]),
        "f1_per": float(f1s[3])
    }

def quick_test():
    p_feat = Path("data/interim/ds08_stage8_30_causal_features.parquet")
    p_seq = Path("data/interim/ds08_stage8_30_historical_sequences.parquet")
    df_feat = pd.read_parquet(p_feat)
    df_seq = pd.read_parquet(p_seq)

    seq_dict = {}
    for _, r in df_seq.iterrows():
        seq_dict[r["event_id"]] = np.array(r["seq_tensor"], dtype=np.float32)

    hist_sum_cols = [c for c in df_feat.columns if c.startswith("hist_")]
    print(f"Num curr cols: {len(CURR_COLS)}, geo cols: {len(GEO_COLS)}, hist sum cols: {len(hist_sum_cols)}")

    train_df = df_feat[(df_feat["split"] == "train") & (df_feat["horizon"] == "H0")]
    ds = ThermalEventDataset(train_df, seq_dict, CURR_COLS, GEO_COLS, hist_sum_cols)
    print("Dataset len:", len(ds))
    item = ds[0]
    print("Item shapes: curr:", item["curr_feats"].shape, "geo:", item["geo_feats"].shape, "hist_sum:", item["hist_sum_feats"].shape, "seq:", item["hist_seq"].shape)

if __name__ == "__main__":
    quick_test()
