"""Stage 8.37 Frozen Model Loader.

Loads the Stage 8.36 final neural model once and caches it in memory.
Verifies the cryptographic SHA-256 hash before returning the model.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional
import torch

from src.stage8_36.model import Architecture1_StaticMLP

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
MODEL_PATH = PROJECT_ROOT / "models" / "stage8_36" / "final_neural_model.pt"
CONFIG_PATH = PROJECT_ROOT / "models" / "stage8_36" / "model_config.json"
EXPECTED_CHECKPOINT_HASH = "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2"

_CACHED_MODEL: Optional[Architecture1_StaticMLP] = None
_CACHED_CONFIG: Optional[dict] = None

def compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_model() -> Architecture1_StaticMLP:
    """Loads and returns the singleton instance of the frozen neural model."""
    global _CACHED_MODEL, _CACHED_CONFIG
    if _CACHED_MODEL is not None:
        return _CACHED_MODEL

    logger.info("Initializing Stage 8.36 frozen neural model...")
    assert MODEL_PATH.exists(), f"Model checkpoint not found at {MODEL_PATH}"
    assert CONFIG_PATH.exists(), f"Model config not found at {CONFIG_PATH}"

    # Verify SHA-256 integrity
    actual_hash = compute_sha256(MODEL_PATH)
    assert actual_hash == EXPECTED_CHECKPOINT_HASH, (
        f"CRITICAL SECURITY VIOLATION: Checkpoint hash mismatch! "
        f"Expected {EXPECTED_CHECKPOINT_HASH}, got {actual_hash}"
    )

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        _CACHED_CONFIG = json.load(f)

    group_dims = _CACHED_CONFIG["group_dimensions"]
    model = Architecture1_StaticMLP(group_dims=group_dims, hidden_dim=48, num_classes=4, dropout=0.15)
    weights = torch.load(MODEL_PATH, weights_only=True, map_location="cpu")
    model.load_state_dict(weights)
    model.eval()

    _CACHED_MODEL = model
    logger.info(f"Loaded frozen neural model successfully. Hash: {actual_hash}")
    return _CACHED_MODEL

def get_model_metadata() -> dict:
    """Returns metadata about the active model."""
    global _CACHED_CONFIG
    if _CACHED_CONFIG is None:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            _CACHED_CONFIG = json.load(f)
    return {
        "architecture_name": _CACHED_CONFIG.get("architecture_name", "Architecture1_StaticMLP"),
        "pure_deep_learning": _CACHED_CONFIG.get("pure_deep_learning", True),
        "checkpoint_sha256": EXPECTED_CHECKPOINT_HASH,
        "model_version": "8.36_final",
        "total_tabular_features": _CACHED_CONFIG.get("total_tabular_features", 41),
        "group_dimensions": _CACHED_CONFIG.get("group_dimensions", {})
    }
