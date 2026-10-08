"""Stage 8.37 Feature Preprocessor.

Loads the frozen standardizers from models/stage8_36/preprocessing.pt once.
Normalizes tabular feature groups using training-fitted means and standard deviations.
"""

import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, Any
import numpy as np
import torch

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
PREPROC_PATH = PROJECT_ROOT / "models" / "stage8_36" / "preprocessing.pt"

_CACHED_SCALERS: Optional[Dict[str, Tuple[np.ndarray, np.ndarray]]] = None

def get_scalers() -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """Loads and caches frozen standardizers."""
    global _CACHED_SCALERS
    if _CACHED_SCALERS is not None:
        return _CACHED_SCALERS

    assert PREPROC_PATH.exists(), f"Preprocessing scalers not found at {PREPROC_PATH}"
    _CACHED_SCALERS = torch.load(PREPROC_PATH, weights_only=False)
    logger.info("Loaded frozen preprocessing standardizers successfully.")
    return _CACHED_SCALERS

def preprocess_features(raw_group_features: Dict[str, np.ndarray]) -> Dict[str, torch.Tensor]:
    """Standardizes raw feature arrays into normalized PyTorch tensors.

    Args:
        raw_group_features: Mapping of group_name -> 2D numpy array (N, D_group)

    Returns:
        Mapping of '{group_name}_feats' -> torch.Tensor of shape (N, D_group)
    """
    scalers = get_scalers()
    batch_tensors = {}

    for grp_name in ["thermal", "industrial", "ecoregion", "historical"]:
        if grp_name not in raw_group_features:
            raise ValueError(f"Missing required feature group: {grp_name}")

        mat = np.asarray(raw_group_features[grp_name], dtype=np.float32)
        if mat.ndim == 1:
            mat = mat.reshape(1, -1)

        mat = np.nan_to_num(mat, nan=0.0, posinf=0.0, neginf=0.0)

        mean, std = scalers[grp_name]
        if mat.shape[1] != len(mean):
            raise ValueError(
                f"Dimension mismatch for group '{grp_name}': expected {len(mean)} features, got {mat.shape[1]}"
            )

        norm_mat = (mat - mean) / std
        batch_tensors[f"{grp_name}_feats"] = torch.tensor(norm_mat, dtype=torch.float32)

    return batch_tensors
