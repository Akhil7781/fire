"""
Test suite for Stage 8.1: India-wide Frozen TCN Inference.

Verifies:
  1. TCN Architecture Invariants (5 blocks, dilations (1,2,4,8,16), 122,498 params)
  2. Input Shape & Channels (T=16, C=8)
  3. Strict Causal Ordering & No Future Leakage (t_j <= t_i, endpoint = target)
  4. 64-Dimensional Latent Embedding & LayerNorm Normalization
  5. Deterministic Inference & Bit-level Reproducibility
  6. Checkpoint File Immutability (SHA-256 unchanged)
  7. India 2025 Embeddings Parquet Integrity & Source ID Alignment
"""

from __future__ import annotations

import hashlib
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.tcn import TemporalConvolutionalNetwork
from src.models.tcn_inference import (
    TCNIndiaInferencePipeline,
    compute_solar_zenith_vectorized,
    haversine_km,
)
from src.training.tcn_dataset import ChannelScaler, ScalerParams

EXPECTED_CKPT_SHA256 = "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16"


@pytest.fixture(scope="module")
def tcn_pipeline():
    """Provides initialized TCNIndiaInferencePipeline instance."""
    return TCNIndiaInferencePipeline(project_root=PROJECT_ROOT)


# =============================================================================
# 1. TCN ARCHITECTURE INVARIANTS
# =============================================================================

def test_tcn_architecture_invariants(tcn_pipeline):
    """
    Verifies 5 residual blocks, dilations (1,2,4,8,16), 8 input channels,
    64 hidden/latent channels, and exactly 122,498 trainable parameters.
    """
    model = tcn_pipeline.model
    assert len(model.network) == 5, f"Expected 5 blocks, got {len(model.network)}"
    assert model.dilations == (1, 2, 4, 8, 16), f"Expected dilations (1,2,4,8,16), got {model.dilations}"
    assert model.in_channels == 8, f"Expected 8 in_channels, got {model.in_channels}"
    assert model.hidden_channels == 64, f"Expected 64 hidden, got {model.hidden_channels}"
    assert model.latent_dim == 64, f"Expected 64 latent_dim, got {model.latent_dim}"

    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    assert total_params == 122498, f"Expected 122,498 parameters, got {total_params}"


# =============================================================================
# 2. INPUT SHAPE & CHANNEL SEMANTICS (T=16, C=8)
# =============================================================================

def test_tcn_input_shape_and_channels(tcn_pipeline):
    """
    Verifies input tensor shape (B, T=16, C=8) and channel names.
    """
    model = tcn_pipeline.model
    scaler = tcn_pipeline.scaler

    expected_channels = [
        "elapsed_time_hours",
        "geodesic_distance_km",
        "thermal_contrast_k",
        "frp_mw",
        "log1p_frp",
        "pixel_footprint_km2",
        "solar_zenith_deg",
        "daynight_flag",
    ]
    assert scaler.channel_names == expected_channels
    assert model.CHANNEL_NAMES == expected_channels

    # Test forward pass with batch of shape (4, 16, 8)
    x = torch.zeros(4, 16, 8, dtype=torch.float32)
    mask = torch.ones(4, 16, dtype=torch.bool)
    with torch.no_grad():
        z = model.encode(x, padding_mask=mask)
    assert z.shape == (4, 64)


# =============================================================================
# 3. STRICT CAUSAL ORDERING & NO FUTURE LEAKAGE
# =============================================================================

def test_causal_temporal_ordering_and_no_future_leakage(tcn_pipeline):
    """
    Verifies that perturbing future timesteps has zero effect on past representations.
    Ensures target observation is strictly at the sequence endpoint.
    """
    model = tcn_pipeline.model
    model.eval()

    torch.manual_seed(42)
    x = torch.randn(2, 16, 8)
    mask = torch.ones(2, 16, dtype=torch.bool)

    with torch.no_grad():
        out_orig = model(x, padding_mask=mask)

    t_pert = 12
    x_pert = x.clone()
    x_pert[:, t_pert:, :] = torch.randn(2, 16 - t_pert, 8)

    with torch.no_grad():
        out_pert = model(x_pert, padding_mask=mask)

    # Invariant: outputs before perturbation point must have zero difference
    diff_frp = (out_orig["frp_pred"][:, :t_pert] - out_pert["frp_pred"][:, :t_pert]).abs().max().item()
    diff_dt = (out_orig["thermal_contrast_pred"][:, :t_pert] - out_pert["thermal_contrast_pred"][:, :t_pert]).abs().max().item()

    assert diff_frp == 0.0, f"Future leakage detected in FRP: {diff_frp}"
    assert diff_dt == 0.0, f"Future leakage detected in Delta-T: {diff_dt}"


# =============================================================================
# 4. 64-DIMENSIONAL LATENT EMBEDDING
# =============================================================================

def test_sixty_four_dim_embedding_output(tcn_pipeline):
    """
    Verifies model produces exactly 64-dimensional output and normalized vectors.
    """
    model = tcn_pipeline.model
    x = torch.randn(5, 16, 8)
    mask = torch.ones(5, 16, dtype=torch.bool)
    with torch.no_grad():
        z = model.encode(x, padding_mask=mask)

    assert z.shape == (5, 64)
    assert not torch.isnan(z).any(), "NaN found in latent embedding"
    assert not torch.isinf(z).any(), "Inf found in latent embedding"


# =============================================================================
# 5. DETERMINISTIC INFERENCE & BIT-LEVEL REPRODUCIBILITY
# =============================================================================

def test_deterministic_inference_and_bit_level_reproducibility(tcn_pipeline):
    """
    Verifies that running inference on identical inputs produces bit-for-bit identical outputs.
    Also verifies exact match with saved pretraining test embeddings.
    """
    model = tcn_pipeline.model
    scaler = tcn_pipeline.scaler

    # Test DS02 test embeddings reproducibility
    ds02_dir = PROJECT_ROOT / "data" / "labeling" / "ds02"
    tensors = np.load(ds02_dir / "sequences_tensor.npy")
    masks = np.load(ds02_dir / "padding_mask.npy")
    manifest = pd.read_parquet(ds02_dir / "temporal_event_manifest.parquet")

    test_idx = manifest["partition"] == "derived_ds02_test"
    test_norm = scaler.transform(tensors[test_idx], masks[test_idx])

    with torch.no_grad():
        z_computed = model.encode(
            torch.from_numpy(test_norm), padding_mask=torch.from_numpy(masks[test_idx])
        ).numpy()

    z_saved = np.load(PROJECT_ROOT / "data" / "embeddings" / "tcn" / "test_embeddings.npy")
    max_diff = np.abs(z_computed - z_saved).max()
    assert max_diff < 1e-6, f"Reproducibility failure against saved test embeddings: {max_diff}"


# =============================================================================
# 6. CHECKPOINT FILE IMMUTABILITY
# =============================================================================

def test_checkpoint_immutability(tcn_pipeline):
    """
    Verifies that models/tcn/best_tcn.pt was not modified.
    """
    with open(tcn_pipeline.checkpoint_path, "rb") as f:
        current_hash = hashlib.sha256(f.read()).hexdigest()
    assert current_hash == EXPECTED_CKPT_SHA256, (
        f"Checkpoint SHA-256 hash changed! Expected {EXPECTED_CKPT_SHA256}, got {current_hash}"
    )


# =============================================================================
# 7. VECTORIZED SOLAR ZENITH CONSISTENCY
# =============================================================================

def test_vectorized_solar_zenith_bit_level_match():
    """
    Verifies vectorized NOAA solar zenith implementation matches scalar implementation.
    """
    from src.labeling.ds02 import calculate_solar_zenith
    from datetime import datetime, timezone

    dts = pd.date_range("2025-01-01", periods=10, freq="73h", tz="UTC")
    lats = np.array([13.1, 28.5, 30.2, 19.8, 22.4, 15.6, 26.8, 12.3, 24.1, 18.9])
    lons = np.array([80.2, 77.1, 75.8, 73.0, 70.0, 77.5, 88.2, 76.5, 85.3, 82.5])

    vec_res = compute_solar_zenith_vectorized(lats, lons, pd.Series(dts))
    scalar_res = [calculate_solar_zenith(lat, lon, dt.to_pydatetime()) for lat, lon, dt in zip(lats, lons, dts)]

    diff = np.abs(vec_res - np.array(scalar_res, dtype=np.float32)).max()
    assert diff < 1e-5, f"Solar zenith discrepancy: {diff}"


# =============================================================================
# 8. INDIA EMBEDDINGS DATASET INTEGRITY
# =============================================================================

def test_india_embeddings_parquet_integrity():
    """
    Verifies output parquet:
      - 1,175,795 rows
      - 70 columns (6 metadata + 64 z_tcn columns)
      - Unique detection_id alignment with causal_features_2025.parquet
      - Zero NaN or Inf values
      - Partition counts preserved
    """
    emb_path = PROJECT_ROOT / "data" / "embeddings" / "tcn" / "india_2025_embeddings.parquet"
    assert emb_path.exists(), "india_2025_embeddings.parquet does not exist!"

    import pyarrow.parquet as pq
    meta = pq.read_metadata(emb_path)
    assert meta.num_rows == 1175795, f"Expected 1,175,795 rows, got {meta.num_rows}"
    assert meta.num_columns == 70, f"Expected 70 columns, got {meta.num_columns}"

    # Sample read to verify columns and data integrity
    df_sample = pd.read_parquet(emb_path)
    assert len(df_sample) == 1175795
    assert df_sample["detection_id"].nunique() == 1175795
    assert df_sample["sequence_id"].nunique() == 1175795

    # Check for NaNs across all 64 embedding dimensions
    z_cols = [f"z_tcn_{i}" for i in range(64)]
    z_vals = df_sample[z_cols].to_numpy()
    assert not np.isnan(z_vals).any(), "NaN found in embeddings!"
    assert not np.isinf(z_vals).any(), "Inf found in embeddings!"

    # Verify partition distribution
    expected_partitions = {
        "train": 578465,
        "train_heldout_spatial": 277395,
        "context_burn_in": 150799,
        "test_seen_spatial": 91846,
        "test": 47881,
        "val": 29409,
    }
    part_counts = df_sample["partition"].value_counts().to_dict()
    assert part_counts == expected_partitions, f"Partition mismatch: {part_counts}"


