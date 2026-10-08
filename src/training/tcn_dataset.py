"""
Dataset and DataLoader for TCN Self-Supervised Sequence Pretraining.

Invariants enforced:
  1. Strict Data Isolation:
     - Fitted scalers and normalizers are computed STRICTLY using active timesteps
       from the TRAIN partition ('derived_ds02_train').
     - Zero validation or test samples ever enter the scaler fitting routine.
  2. 15% Active Timestep Masking:
     - Exactly round(0.15 * N_active) (minimum 1) active timesteps are selected for masking.
     - Padded positions (where padding_mask is False) are NEVER selected as masked targets.
     - Padded positions are NEVER included in the reconstruction loss.
  3. Deterministic Validation / Test Masking:
     - In validation mode, masking uses a deterministic seed per sequence index
       so evaluation loss is exact, stable, and reproducible across training epochs.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset


@dataclass
class ScalerParams:
    """Stores fitted channel-wise means and standard deviations."""
    means: List[float]
    stds: List[float]
    channel_names: List[str]

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> ScalerParams:
        return cls(
            means=data["means"],
            stds=data["stds"],
            channel_names=data["channel_names"],
        )


class ChannelScaler:
    """
    Standardizes 8-channel temporal feature vectors using train-only statistics.
    Ensures padded zero-vectors remain strictly zero.
    """

    def __init__(self, channel_names: Optional[List[str]] = None):
        self.channel_names = channel_names or [
            "elapsed_time_hours",
            "geodesic_distance_km",
            "thermal_contrast_k",
            "frp_mw",
            "log1p_frp",
            "pixel_footprint_km2",
            "solar_zenith_deg",
            "daynight_flag",
        ]
        self.means: Optional[np.ndarray] = None
        self.stds: Optional[np.ndarray] = None
        self.is_fitted: bool = False

    def fit(self, train_tensor: np.ndarray, train_mask: np.ndarray) -> ChannelScaler:
        """
        Fits means and stds exclusively on ACTIVE timesteps of the TRAIN split.
        Args:
            train_tensor: (N_train, 16, 8) array
            train_mask: (N_train, 16) boolean array (True = active, False = pad)
        """
        active_vectors = train_tensor[train_mask]  # Shape: (total_active, 8)
        self.means = active_vectors.mean(axis=0).astype(np.float32)
        stds = active_vectors.std(axis=0).astype(np.float32)
        # Avoid division by zero
        self.stds = np.where(stds < 1e-6, 1.0, stds).astype(np.float32)
        self.is_fitted = True
        return self

    def transform(self, tensor: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Standardizes active timesteps; keeps padded timesteps at 0.0.
        Args:
            tensor: (N, 16, 8) array
            mask: (N, 16) boolean array
        Returns:
            normalized: (N, 16, 8) float32 array
        """
        assert self.is_fitted, "Scaler must be fitted before transform."
        norm = np.zeros_like(tensor, dtype=np.float32)
        # Standardize active steps
        norm[mask] = (tensor[mask] - self.means) / self.stds
        # Ensure padded steps remain strictly 0.0
        norm[~mask] = 0.0
        return norm

    def inverse_transform_channel(
        self, norm_values: Union[np.ndarray, torch.Tensor], channel_idx: int
    ) -> np.ndarray:
        """
        Converts standardized values back to physical units for metric computation.
        """
        assert self.is_fitted, "Scaler must be fitted before inverse transform."
        if isinstance(norm_values, torch.Tensor):
            vals = norm_values.detach().cpu().numpy()
        else:
            vals = np.asarray(norm_values)
        return vals * self.stds[channel_idx] + self.means[channel_idx]

    def get_params(self) -> ScalerParams:
        assert self.is_fitted
        return ScalerParams(
            means=self.means.tolist(),
            stds=self.stds.tolist(),
            channel_names=self.channel_names,
        )

    def load_params(self, params: ScalerParams) -> None:
        self.means = np.array(params.means, dtype=np.float32)
        self.stds = np.array(params.stds, dtype=np.float32)
        self.channel_names = params.channel_names
        self.is_fitted = True


class TCNMaskedDataset(Dataset):
    """
    PyTorch Dataset implementing 15% active-timestep masking for self-supervised TCN.
    """

    def __init__(
        self,
        norm_tensors: np.ndarray,
        raw_tensors: np.ndarray,
        padding_masks: np.ndarray,
        manifest_df: pd.DataFrame,
        is_training: bool = True,
        mask_ratio: float = 0.15,
        seed: int = 42,
    ):
        """
        Args:
            norm_tensors: (N, 16, 8) normalized feature tensor
            raw_tensors: (N, 16, 8) raw physical feature tensor
            padding_masks: (N, 16) bool (True = active, False = pad)
            manifest_df: DataFrame of sequence metadata
            is_training: If True, uses random masking; if False, uses deterministic masking
            mask_ratio: Proportion of active timesteps to mask (0.15)
            seed: Base random seed
        """
        assert len(norm_tensors) == len(padding_masks) == len(manifest_df)
        self.norm_tensors = norm_tensors.astype(np.float32)
        self.raw_tensors = raw_tensors.astype(np.float32)
        self.padding_masks = padding_masks.astype(bool)
        self.manifest_df = manifest_df.reset_index(drop=True)
        self.is_training = is_training
        self.mask_ratio = mask_ratio
        self.seed = seed

    def __len__(self) -> int:
        return len(self.norm_tensors)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        x_norm = self.norm_tensors[idx].copy()  # (16, 8)
        x_raw = self.raw_tensors[idx].copy()    # (16, 8)
        pad_mask = self.padding_masks[idx]       # (16,) True=active, False=pad

        # Find active timestep positions
        active_indices = np.where(pad_mask)[0]
        n_active = len(active_indices)
        assert n_active >= 1, f"Sequence {idx} has zero active timesteps!"

        # Number of active steps to mask: exactly round(mask_ratio * n_active), minimum 1
        k_mask = max(1, int(round(self.mask_ratio * n_active)))

        # Masking selection
        if self.is_training:
            masked_indices = np.random.choice(active_indices, size=k_mask, replace=False)
        else:
            # Deterministic selection for evaluation reproducibility
            rng = np.random.RandomState(self.seed + idx * 1009)
            masked_indices = rng.choice(active_indices, size=k_mask, replace=False)

        # Target mask: True strictly for masked active positions
        target_mask = np.zeros(16, dtype=bool)
        target_mask[masked_indices] = True

        # Invariant: padding positions are NEVER masked
        assert not np.any(target_mask & (~pad_mask)), "Padding position was masked!"

        # Create masked input tensor: zero out all features at masked positions
        x_masked = x_norm.copy()
        x_masked[masked_indices, :] = 0.0

        return {
            "x_masked": torch.from_numpy(x_masked),          # (16, 8)
            "x_norm": torch.from_numpy(x_norm),              # (16, 8) unmasked norm
            "x_raw": torch.from_numpy(x_raw),                # (16, 8) unmasked raw
            "padding_mask": torch.from_numpy(pad_mask),      # (16,)
            "target_mask": torch.from_numpy(target_mask),    # (16,) True at masked positions
            "seq_idx": torch.tensor(idx, dtype=torch.long),
        }


def create_tcn_dataloaders(
    project_root: Path,
    batch_size: int = 32,
    mask_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple[
    DataLoader,
    DataLoader,
    DataLoader,
    ChannelScaler,
    Dict[str, pd.DataFrame],
]:
    """
    Loads DS_02 artifacts, fits scaler strictly on train, and builds DataLoaders.
    Returns:
      train_loader, val_loader, test_loader, fitted_scaler, manifests_dict
    """
    ds02_dir = project_root / "data" / "labeling" / "ds02"
    tensors = np.load(ds02_dir / "sequences_tensor.npy")
    padding_masks = np.load(ds02_dir / "padding_mask.npy")
    manifest = pd.read_parquet(ds02_dir / "temporal_event_manifest.parquet")

    # Split indices based on frozen partition column
    train_mask_idx = manifest["partition"] == "derived_ds02_train"
    val_mask_idx   = manifest["partition"] == "derived_ds02_val"
    test_mask_idx  = manifest["partition"] == "derived_ds02_test"

    train_df = manifest[train_mask_idx].copy()
    val_df   = manifest[val_mask_idx].copy()
    test_df  = manifest[test_mask_idx].copy()

    assert len(train_df) == 339, f"Expected 339 train sequences, got {len(train_df)}"
    assert len(val_df) == 71, f"Expected 71 val sequences, got {len(val_df)}"
    assert len(test_df) == 71, f"Expected 71 test sequences, got {len(test_df)}"

    train_tensors = tensors[train_mask_idx]
    train_pads    = padding_masks[train_mask_idx]

    val_tensors   = tensors[val_mask_idx]
    val_pads      = padding_masks[val_mask_idx]

    test_tensors  = tensors[test_mask_idx]
    test_pads     = padding_masks[test_mask_idx]

    # Invariant: Scaler fitted STRICTLY on train partition
    scaler = ChannelScaler()
    scaler.fit(train_tensors, train_pads)

    train_norm = scaler.transform(train_tensors, train_pads)
    val_norm   = scaler.transform(val_tensors, val_pads)
    test_norm  = scaler.transform(test_tensors, test_pads)

    train_dataset = TCNMaskedDataset(
        norm_tensors=train_norm,
        raw_tensors=train_tensors,
        padding_masks=train_pads,
        manifest_df=train_df,
        is_training=True,
        mask_ratio=mask_ratio,
        seed=seed,
    )
    val_dataset = TCNMaskedDataset(
        norm_tensors=val_norm,
        raw_tensors=val_tensors,
        padding_masks=val_pads,
        manifest_df=val_df,
        is_training=False,
        mask_ratio=mask_ratio,
        seed=seed,
    )
    test_dataset = TCNMaskedDataset(
        norm_tensors=test_norm,
        raw_tensors=test_tensors,
        padding_masks=test_pads,
        manifest_df=test_df,
        is_training=False,
        mask_ratio=mask_ratio,
        seed=seed,
    )

    # Deterministic DataLoader worker seeding
    generator = torch.Generator().manual_seed(seed)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        generator=generator,
        drop_last=False,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        drop_last=False,
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        drop_last=False,
    )

    manifests = {
        "train": train_df,
        "val": val_df,
        "test": test_df,
        "full": manifest,
    }

    return train_loader, val_loader, test_loader, scaler, manifests
