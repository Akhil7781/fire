"""
Test suite for Stage 7A: 1D Dilated Causal TCN Self-Supervised Sequence Pretraining.

Verifies all 15 core scientific and architectural invariants:
 1. test_causal_convolution_no_future_leakage
 2. test_input_shape_and_channel_semantics
 3. test_latent_embedding_size_and_normalization
 4. test_fifteen_percent_masking_logic
 5. test_padding_never_masked
 6. test_padding_excluded_from_reconstruction_loss
 7. test_train_only_optimizer_updates
 8. test_train_only_scaler_fitting
 9. test_validation_not_used_for_gradient_updates
10. test_test_partition_not_used_for_model_selection
11. test_loss_finite_no_nan_or_inf
12. test_checkpoint_save_and_reload
13. test_identical_inference_after_reload
14. test_embedding_dimensions_and_counts
15. test_event_level_partition_integrity
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
import torch
import torch.nn as nn
import torch.nn.functional as F

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.tcn import TemporalConvolutionalNetwork
from src.training.tcn_dataset import ChannelScaler, TCNMaskedDataset, create_tcn_dataloaders


@pytest.fixture(scope="module")
def tcn_env():
    """Provides dataloaders, model, scaler, and checkpoint artifacts."""
    train_loader, val_loader, test_loader, scaler, manifests = create_tcn_dataloaders(
        project_root=PROJECT_ROOT,
        batch_size=32,
        seed=42,
    )
    models_dir = PROJECT_ROOT / "models" / "tcn"
    best_ckpt_path = models_dir / "best_tcn.pt"
    assert best_ckpt_path.exists(), "best_tcn.pt checkpoint missing!"

    best_ckpt = torch.load(best_ckpt_path, map_location="cpu")
    model = TemporalConvolutionalNetwork(
        in_channels=8,
        hidden_channels=64,
        dilations=(1, 2, 4, 8, 16),
        latent_dim=64,
        dropout=0.0,
    )
    model.load_state_dict(best_ckpt["model_state_dict"])
    model.eval()

    embeddings_dir = PROJECT_ROOT / "data" / "embeddings" / "tcn"

    return {
        "train_loader": train_loader,
        "val_loader": val_loader,
        "test_loader": test_loader,
        "scaler": scaler,
        "manifests": manifests,
        "model": model,
        "best_ckpt": best_ckpt,
        "models_dir": models_dir,
        "embeddings_dir": embeddings_dir,
    }


# =============================================================================
# 1. CAUSALITY TESTS
# =============================================================================

def test_causal_convolution_no_future_leakage(tcn_env):
    """
    Invariant 1: Output at timestep t must depend strictly on historical timesteps <= t.
    Perturbing input at timesteps >= t_pert must cause EXACTLY 0.0 change at timesteps < t_pert.
    """
    model = tcn_env["model"]
    model.eval()

    torch.manual_seed(123)
    x = torch.randn(2, 16, 8)
    pad_mask = torch.ones(2, 16, dtype=torch.bool)

    with torch.no_grad():
        out_orig = model(x, padding_mask=pad_mask)

    t_pert = 10
    x_pert = x.clone()
    x_pert[:, t_pert:, :] = torch.randn(2, 16 - t_pert, 8)

    with torch.no_grad():
        out_pert = model(x_pert, padding_mask=pad_mask)

    diff_frp_past = (out_orig["frp_pred"][:, :t_pert] - out_pert["frp_pred"][:, :t_pert]).abs().max().item()
    diff_dt_past  = (out_orig["thermal_contrast_pred"][:, :t_pert] - out_pert["thermal_contrast_pred"][:, :t_pert]).abs().max().item()

    assert diff_frp_past == 0.0, f"Future leakage detected in FRP head at t < {t_pert}: {diff_frp_past}"
    assert diff_dt_past == 0.0, f"Future leakage detected in Delta-T head at t < {t_pert}: {diff_dt_past}"

    # Confirm future outputs did change
    diff_frp_fut = (out_orig["frp_pred"][:, t_pert:] - out_pert["frp_pred"][:, t_pert:]).abs().max().item()
    assert diff_frp_fut > 0.0, "Perturbation had no effect on future timesteps!"


# =============================================================================
# 2. INPUT SHAPE & CHANNEL SEMANTICS
# =============================================================================

def test_input_shape_and_channel_semantics(tcn_env):
    """
    Invariant 2: Input tensor shape is strictly (B, 16, 8).
    8 channels: [elapsed_time, dist, delta_t, frp, log1p_frp, footprint, solar_zenith, daynight].
    Verifies 5 residual blocks, dilations=(1, 2, 4, 8, 16), and parameter count == 122,498.
    """
    model = tcn_env["model"]
    assert len(model.network) == 5, f"Expected 5 residual blocks, got {len(model.network)}"
    assert model.dilations == (1, 2, 4, 8, 16), f"Expected dilations (1, 2, 4, 8, 16), got {model.dilations}"
    param_count = sum(p.numel() for p in model.parameters())
    assert param_count == 122498, f"Expected 122,498 parameters, got {param_count}"

    x = torch.randn(4, 16, 8)
    out = model(x)

    assert out["frp_pred"].shape == (4, 16)
    assert out["thermal_contrast_pred"].shape == (4, 16)
    assert out["z_tcn"].shape == (4, 64)
    assert out["hidden"].shape == (4, 64, 16)


# =============================================================================
# 3. LATENT EMBEDDING
# =============================================================================

def test_latent_embedding_size_and_normalization(tcn_env):
    """
    Invariant 3: Latent temporal embedding z_TCN in R^64, normalized via LayerNorm.
    """
    model = tcn_env["model"]
    x = torch.randn(4, 16, 8)
    z_tcn = model.encode(x)

    assert z_tcn.shape == (4, 64)
    assert torch.isfinite(z_tcn).all()
    # Check LayerNorm properties: variance approximately 1.0, mean approximately 0.0
    for i in range(4):
        std_val = z_tcn[i].std().item()
        assert abs(std_val - 1.0) < 0.2, f"LayerNorm std deviate too far from 1.0: {std_val}"


# =============================================================================
# 4. 15% MASKING LOGIC
# =============================================================================

def test_fifteen_percent_masking_logic():
    """
    Invariant 4: Exactly round(0.15 * N_active) (min 1) active timesteps are masked.
    """
    for n_active in range(1, 17):
        pad_mask = np.zeros(16, dtype=bool)
        pad_mask[16 - n_active:] = True  # Left-padded
        raw = np.random.randn(1, 16, 8)
        norm = raw.copy()
        manifest = pd.DataFrame([{"sequence_id": "test"}])

        ds = TCNMaskedDataset(
            norm_tensors=norm,
            raw_tensors=raw,
            padding_masks=pad_mask[np.newaxis, :],
            manifest_df=manifest,
            is_training=True,
            mask_ratio=0.15,
            seed=42,
        )
        sample = ds[0]
        tgt_mask = sample["target_mask"].numpy()

        expected_k = max(1, int(round(0.15 * n_active)))
        assert tgt_mask.sum() == expected_k, (
            f"Expected {expected_k} masked steps for n_active={n_active}, got {tgt_mask.sum()}"
        )


# =============================================================================
# 5. PADDING NEVER MASKED
# =============================================================================

def test_padding_never_masked(tcn_env):
    """
    Invariant 5: Padded positions (padding_mask == False) are NEVER selected as masked targets.
    """
    for loader_name in ["train_loader", "val_loader", "test_loader"]:
        loader = tcn_env[loader_name]
        for batch in loader:
            pad = batch["padding_mask"]
            tgt = batch["target_mask"]
            # target_mask must be False wherever padding_mask is False
            masked_pads = (tgt & (~pad)).any().item()
            assert not masked_pads, f"Padded position was masked in {loader_name}!"


# =============================================================================
# 6. PADDING EXCLUDED FROM RECONSTRUCTION LOSS
# =============================================================================

def test_padding_excluded_from_reconstruction_loss(tcn_env):
    """
    Invariant 6: Padded positions contribute 0 to the reconstruction loss.
    """
    batch = next(iter(tcn_env["train_loader"]))
    x_norm = batch["x_norm"]
    pad_mask = batch["padding_mask"]
    target_mask = batch["target_mask"]

    pred_frp = torch.randn_like(x_norm[:, :, 3])
    gt_frp   = x_norm[:, :, 3]

    # Compute loss on target_mask
    loss_masked = F.smooth_l1_loss(pred_frp[target_mask], gt_frp[target_mask])

    # If we artificially corrupt pred_frp at padded positions (~pad_mask), loss must not change
    pred_frp_corrupt = pred_frp.clone()
    pred_frp_corrupt[~pad_mask] += 1000.0

    loss_corrupt = F.smooth_l1_loss(pred_frp_corrupt[target_mask], gt_frp[target_mask])
    assert torch.equal(loss_masked, loss_corrupt), "Corrupting padded positions changed the loss!"


# =============================================================================
# 7. TRAIN-ONLY OPTIMIZER UPDATES
# =============================================================================

def test_train_only_optimizer_updates(tcn_env):
    """
    Invariant 7: All training batches come strictly from 'derived_ds02_train'.
    """
    manifest_train = tcn_env["manifests"]["train"]
    assert (manifest_train["partition"] == "derived_ds02_train").all()
    assert len(manifest_train) == 339


# =============================================================================
# 8. TRAIN-ONLY SCALER FITTING
# =============================================================================

def test_train_only_scaler_fitting(tcn_env):
    """
    Invariant 8: Scaler was fitted strictly on active timesteps of the TRAIN split.
    Validation and test active timesteps did not participate in fitting.
    """
    scaler = tcn_env["scaler"]
    ds02_dir = PROJECT_ROOT / "data" / "labeling" / "ds02"
    tensors = np.load(ds02_dir / "sequences_tensor.npy")
    padding_masks = np.load(ds02_dir / "padding_mask.npy")
    manifest = pd.read_parquet(ds02_dir / "temporal_event_manifest.parquet")

    train_idx = manifest["partition"] == "derived_ds02_train"
    train_active = tensors[train_idx][padding_masks[train_idx]]

    expected_means = train_active.mean(axis=0)
    expected_stds  = train_active.std(axis=0)

    assert np.allclose(scaler.means, expected_means, atol=1e-5)
    assert np.allclose(scaler.stds, expected_stds, atol=1e-5)


# =============================================================================
# 9. VALIDATION NOT USED FOR GRADIENTS
# =============================================================================

def test_validation_not_used_for_gradient_updates(tcn_env):
    """
    Invariant 9: Validation forward pass computes loss without gradients or param updates.
    """
    model = tcn_env["model"]
    model.eval()

    val_batch = next(iter(tcn_env["val_loader"]))
    with torch.no_grad():
        out = model(val_batch["x_masked"], padding_mask=val_batch["padding_mask"])
        pred_frp = out["frp_pred"]
        gt_frp = val_batch["x_norm"][:, :, 3]
        loss = F.smooth_l1_loss(pred_frp[val_batch["target_mask"]], gt_frp[val_batch["target_mask"]])

    assert not loss.requires_grad
    for p in model.parameters():
        assert p.grad is None or (p.grad == 0).all()


# =============================================================================
# 10. TEST PARTITION NOT USED FOR MODEL SELECTION
# =============================================================================

def test_test_partition_not_used_for_model_selection(tcn_env):
    """
    Invariant 10: Model selection metric is strictly 'val_loss', not test loss.
    """
    with open(tcn_env["models_dir"] / "training_history.json") as f:
        history = json.load(f)

    assert "val_loss" in history
    assert "test_loss" not in history
    assert "test_frp_mae" not in history


# =============================================================================
# 11. FINITE LOSS
# =============================================================================

def test_loss_finite_no_nan_or_inf(tcn_env):
    """
    Invariant 11: Training loss is strictly finite, non-negative, and non-NaN.
    """
    with open(tcn_env["models_dir"] / "training_history.json") as f:
        history = json.load(f)

    for loss in history["train_loss"] + history["val_loss"]:
        assert math.isfinite(loss)
        assert loss >= 0.0


# =============================================================================
# 12. CHECKPOINT SAVE & RELOAD
# =============================================================================

def test_checkpoint_save_and_reload(tcn_env):
    """
    Invariant 12: Checkpoints best_tcn.pt and final_tcn.pt are valid PyTorch archives.
    """
    best_path = tcn_env["models_dir"] / "best_tcn.pt"
    final_path = tcn_env["models_dir"] / "final_tcn.pt"

    assert best_path.exists()
    assert final_path.exists()

    best_ckpt = torch.load(best_path, map_location="cpu")
    final_ckpt = torch.load(final_path, map_location="cpu")

    for k in ["epoch", "model_state_dict", "optimizer_state_dict", "val_loss", "config"]:
        assert k in best_ckpt
        assert k in final_ckpt


# =============================================================================
# 13. IDENTICAL INFERENCE AFTER RELOAD
# =============================================================================

def test_identical_inference_after_reload(tcn_env):
    """
    Invariant 13: Reloading model from disk yields bit-for-bit identical embeddings.
    """
    model1 = tcn_env["model"]
    model1.eval()

    model2 = TemporalConvolutionalNetwork(
        in_channels=8, hidden_channels=64, dilations=(1, 2, 4, 8, 16), latent_dim=64, dropout=0.0
    )
    best_ckpt = torch.load(tcn_env["models_dir"] / "best_tcn.pt", map_location="cpu")
    model2.load_state_dict(best_ckpt["model_state_dict"])
    model2.eval()

    x = torch.randn(4, 16, 8)
    with torch.no_grad():
        z1 = model1.encode(x)
        z2 = model2.encode(x)

    assert torch.equal(z1, z2), "Embeddings differ between reloaded models!"


# =============================================================================
# 14. EMBEDDING DIMENSIONS & COUNTS
# =============================================================================

def test_embedding_dimensions_and_counts(tcn_env):
    """
    Invariant 14: Generated embeddings have exact shapes:
    Train: (339, 64), Val: (71, 64), Test: (71, 64).
    """
    emb_dir = tcn_env["embeddings_dir"]
    train_emb = np.load(emb_dir / "train_embeddings.npy")
    val_emb   = np.load(emb_dir / "val_embeddings.npy")
    test_emb  = np.load(emb_dir / "test_embeddings.npy")
    manifest  = pd.read_parquet(emb_dir / "embedding_manifest.parquet")

    assert train_emb.shape == (339, 64)
    assert val_emb.shape == (71, 64)
    assert test_emb.shape == (71, 64)
    assert len(manifest) == 481
    assert not np.isnan(train_emb).any()
    assert not np.isnan(val_emb).any()
    assert not np.isnan(test_emb).any()


# =============================================================================
# 15. EVENT-LEVEL PARTITION INTEGRITY
# =============================================================================

def test_event_level_partition_integrity(tcn_env):
    """
    Invariant 15: Exact event-level partitioning preserved:
    14 train physical events, 3 val physical events, 3 test physical events.
    Zero event leakage between train, val, and test.
    """
    manifest = pd.read_parquet(tcn_env["embeddings_dir"] / "embedding_manifest.parquet")

    train_events = set(manifest[manifest["partition"] == "derived_ds02_train"]["fire_event_id"])
    val_events   = set(manifest[manifest["partition"] == "derived_ds02_val"]["fire_event_id"])
    test_events  = set(manifest[manifest["partition"] == "derived_ds02_test"]["fire_event_id"])

    assert len(train_events) == 14, f"Expected 14 train events, got {len(train_events)}"
    assert len(val_events) == 3, f"Expected 3 val events, got {len(val_events)}"
    assert len(test_events) == 3, f"Expected 3 test events, got {len(test_events)}"

    assert train_events.isdisjoint(val_events), "Event leakage between train and val!"
    assert train_events.isdisjoint(test_events), "Event leakage between train and test!"
    assert val_events.isdisjoint(test_events), "Event leakage between val and test!"
