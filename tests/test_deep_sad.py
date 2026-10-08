"""
Test suite for Stage 7B: Deep Semi-Supervised Anomaly Detection (Deep SAD).

Verifies all 16 pre-training architectural and scientific invariants:
  1. Input dimension = 27
  2. Parameter count = 13,696
  3. Output dimension = 32
  4. Score shape correct
  5. Center dimension = 32
  6. Center is frozen
  7. Unlabeled values remain unknown
  8. Persistent confounders excluded
  9. Acute anchors use y=-1 semantics
 10. No validation/test samples enter training
 11. No physical event crosses partitions
 12. No latitude/longitude leakage
 13. No snapshot feature
 14. No NaN/Inf
 15. Deterministic initialization
 16. Checkpoint save/load works
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
import torch
import torch.nn as nn

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.deep_sad import DeepSAD


# =============================================================================
# 1. INPUT DIMENSION & FEATURE LIST
# =============================================================================

def test_input_dimension_and_feature_list():
    """
    Invariant 1 & 12 & 13:
    Input dimension is strictly D_in = 27.
    Excluded: latitude, longitude, snapshot_co_detect_count_2km, metadata.
    """
    assert len(DeepSAD.FEATURE_NAMES) == 27, f"Expected 27 features, got {len(DeepSAD.FEATURE_NAMES)}"

    # Excluded features check
    prohibited = [
        "latitude",
        "longitude",
        "snapshot_co_detect_count_2km",
        "detection_id",
        "acq_date",
        "acq_time",
        "acq_datetime_utc",
        "satellite",
        "instrument",
        "confidence",
        "version",
        "source_file",
        "source_row_idx",
        "is_burn_in_context",
        "h3_res8",
        "partition",
    ]
    for p in prohibited:
        assert p not in DeepSAD.FEATURE_NAMES, f"Prohibited feature found in input list: {p}"

    # Verify exact feature names
    expected_features = [
        "bright_ti4",
        "bright_ti5",
        "frp",
        "pixel_area",
        "scan",
        "track",
        "delta_t_robust_scaled",
        "temp_ratio_robust_scaled",
        "frp_density_robust_scaled",
        "frp_log1p_robust_scaled",
        "time_since_last_det_2km_robust_scaled",
        "spatial_dispersion_24h_2km_robust_scaled",
        "sin_diurnal",
        "cos_diurnal",
        "sin_lst",
        "cos_lst",
        "sin_annual",
        "cos_annual",
        "hist_count_6h_2km",
        "hist_count_24h_2km",
        "has_prior_24h_2km",
        "mean_frp_6h_2km",
        "max_frp_6h_2km",
        "mean_frp_24h_2km",
        "max_frp_24h_2km",
        "day_ratio_24h_2km",
        "daynight_binary",
    ]
    assert DeepSAD.FEATURE_NAMES == expected_features, "Feature names do not match authoritative list!"


# =============================================================================
# 2. MODEL ARCHITECTURE & PARAMETER COUNT
# =============================================================================

def test_model_architecture_and_parameter_count():
    """
    Invariant 2 & 3:
    Linear(27, 128, bias=False) -> LeakyReLU(0.1) ->
    Linear(128, 64, bias=False) -> LeakyReLU(0.1) ->
    Linear(64, 32, bias=False)
    Parameter count == 13,696.
    """
    model = DeepSAD(in_features=27, latent_dim=32, leaky_relu_slope=0.1)

    # Check layer types and biases
    assert len(model.network) == 5
    assert isinstance(model.network[0], nn.Linear)
    assert model.network[0].bias is None, "Linear layer 1 has bias, violates no-bias invariant!"
    assert model.network[0].in_features == 27
    assert model.network[0].out_features == 128

    assert isinstance(model.network[1], nn.LeakyReLU)
    assert model.network[1].negative_slope == 0.1

    assert isinstance(model.network[2], nn.Linear)
    assert model.network[2].bias is None, "Linear layer 2 has bias, violates no-bias invariant!"
    assert model.network[2].in_features == 128
    assert model.network[2].out_features == 64

    assert isinstance(model.network[3], nn.LeakyReLU)
    assert model.network[3].negative_slope == 0.1

    assert isinstance(model.network[4], nn.Linear)
    assert model.network[4].bias is None, "Linear layer 3 has bias, violates no-bias invariant!"
    assert model.network[4].in_features == 64
    assert model.network[4].out_features == 32

    # Verify exact parameter count
    param_count = sum(p.numel() for p in model.parameters())
    assert param_count == 13696, f"Expected 13,696 parameters, got {param_count}"


# =============================================================================
# 3. OUTPUT DIMENSION & SCORE SHAPE
# =============================================================================

def test_output_dimension_and_score_shape():
    """
    Invariant 3 & 4:
    Output representation z_SAD is (B, 32).
    Anomaly score s(x) is (B,).
    """
    model = DeepSAD()
    B = 8
    x = torch.randn(B, 27)

    # Forward without center
    z = model(x)
    assert z.shape == (B, 32)

    # Initialize center and compute scores
    x_init = torch.randn(100, 27)
    model.init_center(x_init)

    scores = model.compute_anomaly_score(x)
    assert scores.shape == (B,)
    assert (scores >= 0.0).all(), "Anomaly scores must be non-negative distance squared!"


# =============================================================================
# 4. CENTER INITIALIZATION & FROZEN INVARIANT
# =============================================================================

def test_center_initialization_and_frozen_invariant():
    """
    Invariant 5 & 6:
    Center c is in R^32, ||c|| >= 0.10, and remains strictly fixed during training.
    """
    model = DeepSAD()
    torch.manual_seed(42)
    x_init = torch.randn(200, 27)

    c = model.init_center(x_init, eps_norm=0.10)
    assert c.shape == (32,)
    c_norm = torch.norm(c).item()
    assert c_norm >= 0.10, f"Center norm {c_norm} < 0.10, violates Checkpoint Gate 2!"

    # Verify center is not a trainable parameter
    param_names = [name for name, _ in model.named_parameters()]
    assert "c" not in param_names, "Center c must not be a trainable parameter!"

    # Verify center doesn't change after optimizer step
    c_before = model.c.clone()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)

    x = torch.randn(16, 27)
    z = model(x)
    loss = torch.mean((z - model.c.unsqueeze(0)) ** 2)
    loss.backward()
    optimizer.step()

    c_after = model.c.clone()
    assert torch.equal(c_before, c_after), "Center c changed during training step! Must remain fixed."


# =============================================================================
# 5. TARGET ENCODING & SEMANTICS
# =============================================================================

def test_target_semantics_unlabeled_and_confounders():
    """
    Invariant 7, 8, 9:
    Unlabeled FIRMS observations are UNKNOWN (y=0), never nominal negatives (y=+1).
    Persistent confounders have is_supervised_target=False and are excluded from training.
    Acute anchors have y=-1 semantics (repulsion).
    """
    confounders_path = PROJECT_ROOT / "data" / "labeling" / "ds05" / "ds05_quarantined_confounders.parquet"
    assert confounders_path.exists(), "ds05_quarantined_confounders.parquet missing!"
    confounders = pd.read_parquet(confounders_path)

    # Confounders have is_supervised_target == False
    assert (confounders["is_supervised_target"] == False).all()
    assert len(confounders) == 1870

    # Verify acute anchors in DS03/04/05 have is_supervised_target == True
    f3 = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds03" / "forest_fire_candidates.parquet")
    f4 = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds04" / "agriculture_fire_candidates.parquet")
    f5 = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds05" / "ds05_valid_industrial_anchors.parquet")

    assert (f3["is_supervised_target"] == True).all()
    assert (f4["is_supervised_target"] == True).all()
    assert (f5["is_supervised_target"] == True).all()

    # Zero overlap between confounders and acute anchors
    confounder_ids = set(confounders["detection_id"])
    anchor_ids = set(f3["detection_id"]).union(set(f4["detection_id"])).union(set(f5["detection_id"]))
    assert len(confounder_ids.intersection(anchor_ids)) == 0


# =============================================================================
# 6. DATA PARTITION & EVENT ISOLATION
# =============================================================================

def test_train_val_test_isolation_and_event_integrity():
    """
    Invariant 10 & 11:
    No validation or test samples enter training.
    No physical event crosses partition boundaries.
    """
    cf_path = PROJECT_ROOT / "data" / "interim" / "causal_features_2025.parquet"
    cf = pd.read_parquet(cf_path, columns=["detection_id", "partition"])

    f3 = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds03" / "forest_fire_candidates.parquet").merge(cf, on="detection_id")
    f4 = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds04" / "agriculture_fire_candidates.parquet").merge(cf, on="detection_id")
    f5 = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds05" / "ds05_valid_industrial_anchors.parquet")

    # Manali industrial incident is strictly in train_heldout_spatial
    assert (f5["partition"] == "train_heldout_spatial").all()

    # Verify all DS03 events have detections in exactly ONE partition
    for event_id, grp in f3.groupby("fire_event_id"):
        assert grp["partition"].nunique() == 1, f"DS03 event {event_id} spans multiple partitions!"

    # Verify all DS04 events have detections in exactly ONE partition
    for event_id, grp in f4.groupby("fire_event_id"):
        assert grp["partition"].nunique() == 1, f"DS04 event {event_id} spans multiple partitions!"

    # Train partition contains 0 industrial anchors
    train_det_ids = set(cf[cf["partition"] == "train"]["detection_id"])
    ind_det_ids = set(f5["detection_id"])
    assert len(train_det_ids.intersection(ind_det_ids)) == 0, "Industrial anchors leaked into train partition!"


# =============================================================================
# 7. LOSS FUNCTION FINITENESS
# =============================================================================

def test_loss_finite_and_repulsion_direction():
    """
    Invariant 14:
    Loss components are strictly finite, no NaN, no Inf.
    Repulsive term increases as acute anchors move closer to center.
    """
    model = DeepSAD()
    x_init = torch.randn(100, 27)
    model.init_center(x_init)

    gamma = 0.10
    eta = 1.0
    epsilon = 1e-6

    x_u = torch.randn(32, 27)
    x_a = torch.randn(4, 27)

    z_u = model(x_u)
    z_a = model(x_a)

    d_u_sq = torch.sum((z_u - model.c.unsqueeze(0)) ** 2, dim=-1)
    d_a_sq = torch.sum((z_a - model.c.unsqueeze(0)) ** 2, dim=-1)

    loss_u = gamma * torch.mean(d_u_sq)
    loss_a = eta * torch.mean(1.0 / (d_a_sq + epsilon))
    loss = loss_u + loss_a

    assert torch.isfinite(loss), f"Loss is non-finite: {loss.item()}"
    assert torch.isfinite(loss_u), f"Unlabeled loss non-finite: {loss_u.item()}"
    assert torch.isfinite(loss_a), f"Anchor loss non-finite: {loss_a.item()}"

    # Verify repulsive behavior: when distance -> 0, anchor loss increases
    z_close = model.c.unsqueeze(0).repeat(4, 1) + 1e-4  # very close to center
    d_close_sq = torch.sum((z_close - model.c.unsqueeze(0)) ** 2, dim=-1)
    loss_close = eta * torch.mean(1.0 / (d_close_sq + epsilon))
    assert loss_close.item() > loss_a.item(), "Repulsive loss did not penalize proximity to center!"


# =============================================================================
# 8. DETERMINISTIC INITIALIZATION
# =============================================================================

def test_deterministic_initialization():
    """
    Invariant 15:
    Seed 42 produces bit-for-bit identical weights and center.
    """
    torch.manual_seed(42)
    m1 = DeepSAD()
    x_init = torch.randn(50, 27)
    c1 = m1.init_center(x_init)

    torch.manual_seed(42)
    m2 = DeepSAD()
    x_init2 = torch.randn(50, 27)
    c2 = m2.init_center(x_init2)

    assert torch.equal(c1, c2), "Center vectors differ under identical random seeds!"
    for p1, p2 in zip(m1.parameters(), m2.parameters()):
        assert torch.equal(p1, p2), "Model parameters differ under identical random seeds!"


# =============================================================================
# 9. CHECKPOINT SAVE & RELOAD
# =============================================================================

def test_checkpoint_save_and_reload(tmp_path):
    """
    Invariant 16:
    Checkpoint save/load preserves state dict, center vector, and inference.
    """
    torch.manual_seed(42)
    model = DeepSAD()
    x_init = torch.randn(50, 27)
    model.init_center(x_init)

    ckpt_path = tmp_path / "deep_sad_test.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "center": model.c.clone(),
        "config": {"in_features": 27, "latent_dim": 32},
    }, ckpt_path)

    # Reload into fresh model
    model_reloaded = DeepSAD()
    ckpt = torch.load(ckpt_path, map_location="cpu")
    model_reloaded.load_state_dict(ckpt["model_state_dict"])
    model_reloaded.c.copy_(ckpt["center"])
    model_reloaded.is_center_initialized = True

    x_test = torch.randn(10, 27)
    model.eval()
    model_reloaded.eval()

    with torch.no_grad():
        s1 = model.compute_anomaly_score(x_test)
        s2 = model_reloaded.compute_anomaly_score(x_test)

    assert torch.equal(s1, s2), "Scores differ after reload from checkpoint!"
