"""Stage 8.34 Dataset & Feature Pipeline Module.

Implements clean tabular feature extraction and causal historical FIRMS sequence loading.
CRITICAL INVARIANTS:
1. FROZEN TEST LOCK: ZERO ACCESS to frozen 2026 test cohort.
2. ZERO LEAKAGE: Scalers fitted strictly on training partition only.
3. ZERO COORDINATES: Primary feature schema does NOT include centroid_lat / centroid_lon.
4. ZERO TARGET PROXIES: associated_* fields are never loaded or passed to models.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "stage8_34"

def load_clean_feature_schema() -> Dict[str, Any]:
    schema_path = ARTIFACTS_DIR / "clean_feature_schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_development_data() -> Tuple[pd.DataFrame, Dict[str, np.ndarray]]:
    """
    Loads development cohort features and historical sequences for the trusted 131 events.
    Verifies test lock and no leakage.
    """
    cohort_path = ARTIFACTS_DIR / "trusted_development_cohort.parquet"
    cohort_df = pd.read_parquet(cohort_path)
    assert len(cohort_df) == 131, f"Expected 131 dev events, got {len(cohort_df)}"
    dev_ids = set(cohort_df["event_id"].tolist())

    # Load causal features
    feat_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_30_causal_features.parquet"
    df_feat = pd.read_parquet(feat_path)
    
    # Filter strictly to H0 horizon and dev events
    dev_feat = df_feat[(df_feat["horizon"] == "H0") & (df_feat["event_id"].isin(dev_ids))].copy()
    assert len(dev_feat) == 131, f"Expected 131 dev feature rows, got {len(dev_feat)}"
    assert "test" not in dev_feat["split"].values, "Violation: Test split found in development features"

    # Merge spatial metadata from trusted cohort if needed
    if "spatial_region" not in dev_feat.columns:
        from src.stage8_32.spatial_split import assign_spatial_regions
        dev_feat = assign_spatial_regions(dev_feat)

    # Load historical sequences
    seq_path = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_30_historical_sequences.parquet"
    df_seq = pd.read_parquet(seq_path)
    dev_seq = df_seq[df_seq["event_id"].isin(dev_ids)].copy()
    assert "test" not in dev_seq["split"].values, "Violation: Test split found in dev sequences"

    seq_dict = {}
    for _, row in dev_seq.iterrows():
        eid = row["event_id"]
        t = row["seq_tensor"]
        if len(t) > 0:
            arr = np.array([np.asarray(x, dtype=np.float32) for x in t], dtype=np.float32)
        else:
            arr = np.zeros((0, 11), dtype=np.float32)
        seq_dict[eid] = arr

    return dev_feat.reset_index(drop=True), seq_dict

class CleanMultiModalDataset(Dataset):
    """
    Multi-modal PyTorch dataset with strictly training-fitted standardizers.
    Excludes raw coordinates by default.
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

        # Process each modality group
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
        self.event_ids = self.df["event_id"].tolist()

        # Sequence tensor preparation
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
                        self.padded_seqs[i, :length, :] = raw_s[-length:, :]
                        self.seq_masks[i, :length] = 1.0

    def get_scalers(self) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        return self.scalers

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        cid = int(self.class_ids[idx])
        is_persistent = 1 if cid == 3 else 0
        subclass_id = min(cid, 2)

        item = {
            "event_id": self.event_ids[idx],
            "class_id": torch.tensor(cid, dtype=torch.long),
            "is_persistent": torch.tensor(is_persistent, dtype=torch.long),
            "subclass_id": torch.tensor(subclass_id, dtype=torch.long)
        }

        for grp_name, mat in self.tensors.items():
            item[f"{grp_name}_feats"] = torch.tensor(mat[idx], dtype=torch.float32)

        if self.has_sequences:
            item["seq_tensor"] = torch.tensor(self.padded_seqs[idx], dtype=torch.float32)
            item["seq_len"] = torch.tensor(self.seq_lengths[idx], dtype=torch.long)
            item["seq_mask"] = torch.tensor(self.seq_masks[idx], dtype=torch.float32)

        return item
