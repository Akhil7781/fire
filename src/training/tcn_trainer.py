"""
TCN Self-Supervised Sequence Pretraining Loop and Checkpointing.

Enforces:
  1. Data Isolation:
     - Optimizer updates: TRAIN ONLY.
     - Validation: Model selection and early stopping only.
     - Test: Untouched until final embedding extraction.
  2. Loss Computation:
     - Smooth L1 (Huber) loss computed strictly on masked active positions.
     - Padded positions have zero contribution to loss.
  3. Physical Metrics:
     - Reports unnormalized MAE and RMSE for FRP (MW) and Thermal Contrast Delta-T (K).
  4. Reproducibility & Checkpointing:
     - Saves best_tcn.pt, final_tcn.pt, config.json, training_history.json, scaler_params.json.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau

import sys

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.tcn import TemporalConvolutionalNetwork
from src.training.tcn_dataset import ChannelScaler, create_tcn_dataloaders


@dataclass
class TCNTrainConfig:
    """TCN Pretraining Hyperparameters and Settings."""
    in_channels: int = 8
    hidden_channels: int = 64
    dilations: Tuple[int, ...] = (1, 2, 4, 8, 16)
    latent_dim: int = 64
    dropout: float = 0.2
    batch_size: int = 32
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    max_epochs: int = 60
    patience: int = 12
    mask_ratio: float = 0.15
    seed: int = 42

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["dilations"] = list(self.dilations)
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> TCNTrainConfig:
        data_copy = data.copy()
        if "dilations" in data_copy:
            data_copy["dilations"] = tuple(data_copy["dilations"])
        return cls(**data_copy)


class TCNTrainer:
    """
    Manages self-supervised masked pretraining for 1D Causal TCN.
    """

    def __init__(
        self,
        project_root: Path,
        config: Optional[TCNTrainConfig] = None,
    ):
        self.project_root = project_root
        self.config = config or TCNTrainConfig()
        self.output_dir = project_root / "models" / "tcn"
        self.embeddings_dir = project_root / "data" / "embeddings" / "tcn"

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)

        self.device = torch.device("cpu")

        # Set fixed random seeds
        torch.manual_seed(self.config.seed)
        np.random.seed(self.config.seed)

    def train(self) -> Dict:
        """
        Executes full self-supervised pretraining with early stopping.
        """
        start_time = time.time()
        cfg = self.config

        # 1. Build DataLoaders & Scaler
        train_loader, val_loader, test_loader, scaler, manifests = create_tcn_dataloaders(
            project_root=self.project_root,
            batch_size=cfg.batch_size,
            mask_ratio=cfg.mask_ratio,
            seed=cfg.seed,
        )

        # 2. Build TCN Model
        model = TemporalConvolutionalNetwork(
            in_channels=cfg.in_channels,
            hidden_channels=cfg.hidden_channels,
            dilations=cfg.dilations,
            latent_dim=cfg.latent_dim,
            dropout=cfg.dropout,
        ).to(self.device)

        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

        # 3. Optimizer & Scheduler
        optimizer = AdamW(
            model.parameters(),
            lr=cfg.learning_rate,
            weight_decay=cfg.weight_decay,
        )
        scheduler = ReduceLROnPlateau(
            optimizer,
            mode="min",
            factor=0.5,
            patience=5,
            min_lr=1e-5,
        )

        history = {
            "epoch": [],
            "train_loss": [],
            "train_loss_frp": [],
            "train_loss_dt": [],
            "val_loss": [],
            "val_loss_frp": [],
            "val_loss_dt": [],
            "val_frp_mae": [],
            "val_frp_rmse": [],
            "val_dt_mae": [],
            "val_dt_rmse": [],
            "learning_rate": [],
        }

        best_val_loss = float("inf")
        best_epoch = 0
        patience_counter = 0

        # Channel indices for targets
        CH_DT = 2   # thermal_contrast_k
        CH_FRP = 3  # frp_mw

        print(f"Starting TCN Self-Supervised Pretraining:")
        print(f"  Train sequences: {len(manifests['train'])} | Val sequences: {len(manifests['val'])}")
        print(f"  Model parameters: {total_params:,}")
        print(f"  Batch size: {cfg.batch_size} | Max epochs: {cfg.max_epochs} | Patience: {cfg.patience}")

        for epoch in range(1, cfg.max_epochs + 1):
            # -----------------------------------------------------------------
            # Training Phase (TRAIN ONLY)
            # -----------------------------------------------------------------
            model.train()
            train_losses, train_frp_losses, train_dt_losses = [], [], []

            for batch in train_loader:
                x_masked = batch["x_masked"].to(self.device)
                x_norm = batch["x_norm"].to(self.device)
                pad_mask = batch["padding_mask"].to(self.device)
                target_mask = batch["target_mask"].to(self.device)

                optimizer.zero_grad()
                out = model(x_masked, padding_mask=pad_mask)

                pred_frp = out["frp_pred"]                  # (B, T)
                pred_dt  = out["thermal_contrast_pred"]      # (B, T)
                gt_frp   = x_norm[:, :, CH_FRP]             # (B, T)
                gt_dt    = x_norm[:, :, CH_DT]              # (B, T)

                # Loss strictly on masked active positions
                loss_frp = F.smooth_l1_loss(pred_frp[target_mask], gt_frp[target_mask], beta=1.0)
                loss_dt  = F.smooth_l1_loss(pred_dt[target_mask], gt_dt[target_mask], beta=1.0)
                loss = loss_frp + loss_dt

                assert torch.isfinite(loss), f"Encountered non-finite loss at epoch {epoch}: {loss.item()}"

                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

                train_losses.append(loss.item())
                train_frp_losses.append(loss_frp.item())
                train_dt_losses.append(loss_dt.item())

            avg_train_loss = float(np.mean(train_losses))
            avg_train_frp  = float(np.mean(train_frp_losses))
            avg_train_dt   = float(np.mean(train_dt_losses))

            # -----------------------------------------------------------------
            # Validation Phase (NO GRADIENTS, NO PARAMETER UPDATES)
            # -----------------------------------------------------------------
            model.eval()
            val_losses, val_frp_losses, val_dt_losses = [], [], []
            val_preds_frp_phys, val_gts_frp_phys = [], []
            val_preds_dt_phys, val_gts_dt_phys = [], []

            with torch.no_grad():
                for batch in val_loader:
                    x_masked = batch["x_masked"].to(self.device)
                    x_norm = batch["x_norm"].to(self.device)
                    x_raw = batch["x_raw"].to(self.device)
                    pad_mask = batch["padding_mask"].to(self.device)
                    target_mask = batch["target_mask"].to(self.device)

                    out = model(x_masked, padding_mask=pad_mask)
                    pred_frp = out["frp_pred"]
                    pred_dt  = out["thermal_contrast_pred"]
                    gt_frp_norm = x_norm[:, :, CH_FRP]
                    gt_dt_norm  = x_norm[:, :, CH_DT]

                    loss_frp = F.smooth_l1_loss(pred_frp[target_mask], gt_frp_norm[target_mask], beta=1.0)
                    loss_dt  = F.smooth_l1_loss(pred_dt[target_mask], gt_dt_norm[target_mask], beta=1.0)
                    loss = loss_frp + loss_dt

                    val_losses.append(loss.item())
                    val_frp_losses.append(loss_frp.item())
                    val_dt_losses.append(loss_dt.item())

                    # Unscale predictions to physical units
                    p_frp_norm = pred_frp[target_mask].cpu().numpy()
                    p_dt_norm  = pred_dt[target_mask].cpu().numpy()
                    raw_frp    = x_raw[:, :, CH_FRP][target_mask].cpu().numpy()
                    raw_dt     = x_raw[:, :, CH_DT][target_mask].cpu().numpy()

                    p_frp_phys = scaler.inverse_transform_channel(p_frp_norm, CH_FRP)
                    p_dt_phys  = scaler.inverse_transform_channel(p_dt_norm, CH_DT)

                    val_preds_frp_phys.extend(p_frp_phys.tolist())
                    val_gts_frp_phys.extend(raw_frp.tolist())
                    val_preds_dt_phys.extend(p_dt_phys.tolist())
                    val_gts_dt_phys.extend(raw_dt.tolist())

            avg_val_loss = float(np.mean(val_losses))
            avg_val_frp  = float(np.mean(val_frp_losses))
            avg_val_dt   = float(np.mean(val_dt_losses))

            # Physical error metrics
            err_frp = np.array(val_preds_frp_phys) - np.array(val_gts_frp_phys)
            err_dt  = np.array(val_preds_dt_phys) - np.array(val_gts_dt_phys)

            val_frp_mae  = float(np.mean(np.abs(err_frp)))
            val_frp_rmse = float(np.sqrt(np.mean(err_frp ** 2)))
            val_dt_mae   = float(np.mean(np.abs(err_dt)))
            val_dt_rmse  = float(np.sqrt(np.mean(err_dt ** 2)))

            current_lr = float(optimizer.param_groups[0]["lr"])
            scheduler.step(avg_val_loss)

            history["epoch"].append(epoch)
            history["train_loss"].append(avg_train_loss)
            history["train_loss_frp"].append(avg_train_frp)
            history["train_loss_dt"].append(avg_train_dt)
            history["val_loss"].append(avg_val_loss)
            history["val_loss_frp"].append(avg_val_frp)
            history["val_loss_dt"].append(avg_val_dt)
            history["val_frp_mae"].append(val_frp_mae)
            history["val_frp_rmse"].append(val_frp_rmse)
            history["val_dt_mae"].append(val_dt_mae)
            history["val_dt_rmse"].append(val_dt_rmse)
            history["learning_rate"].append(current_lr)

            if epoch % 5 == 0 or epoch == 1:
                print(
                    f"Epoch {epoch:02d}/{cfg.max_epochs:02d} | "
                    f"Train Loss: {avg_train_loss:.4f} | "
                    f"Val Loss: {avg_val_loss:.4f} | "
                    f"FRP MAE: {val_frp_mae:.2f} MW | "
                    f"d_T MAE: {val_dt_mae:.2f} K | "
                    f"LR: {current_lr:.1e}"
                )

            # Check for best model
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                best_epoch = epoch
                patience_counter = 0

                # Save best checkpoint
                torch.save(
                    {
                        "epoch": epoch,
                        "model_state_dict": model.state_dict(),
                        "optimizer_state_dict": optimizer.state_dict(),
                        "val_loss": avg_val_loss,
                        "val_frp_mae": val_frp_mae,
                        "val_dt_mae": val_dt_mae,
                        "config": cfg.to_dict(),
                        "scaler_params": scaler.get_params().to_dict(),
                    },
                    self.output_dir / "best_tcn.pt",
                )
            else:
                patience_counter += 1
                if patience_counter >= cfg.patience:
                    print(f"Early stopping triggered at epoch {epoch} (best epoch: {best_epoch})")
                    break

        training_runtime = round(time.time() - start_time, 2)

        # 4. Save Final Checkpoint & Metadata
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": avg_val_loss,
                "config": cfg.to_dict(),
                "scaler_params": scaler.get_params().to_dict(),
            },
            self.output_dir / "final_tcn.pt",
        )

        with open(self.output_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(cfg.to_dict(), f, indent=2)

        with open(self.output_dir / "training_history.json", "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        with open(self.output_dir / "scaler_params.json", "w", encoding="utf-8") as f:
            json.dump(scaler.get_params().to_dict(), f, indent=2)

        # 5. Extract Embeddings with Best Model
        print(f"\nLoading best checkpoint from epoch {best_epoch} for embedding generation...")
        best_ckpt = torch.save if False else torch.load(self.output_dir / "best_tcn.pt")
        model.load_state_dict(best_ckpt["model_state_dict"])
        model.eval()

        emb_stats = self._extract_and_save_embeddings(model, scaler, manifests)

        summary = {
            "model_architecture": "1D Dilated Causal TCN",
            "in_channels": cfg.in_channels,
            "hidden_channels": cfg.hidden_channels,
            "dilations": list(cfg.dilations),
            "latent_dim": cfg.latent_dim,
            "total_parameters": total_params,
            "best_epoch": best_epoch,
            "total_epochs_trained": epoch,
            "best_val_loss": round(best_val_loss, 4),
            "final_train_loss": round(avg_train_loss, 4),
            "val_frp_mae_mw": round(history["val_frp_mae"][best_epoch - 1], 3),
            "val_frp_rmse_mw": round(history["val_frp_rmse"][best_epoch - 1], 3),
            "val_dt_mae_k": round(history["val_dt_mae"][best_epoch - 1], 3),
            "val_dt_rmse_k": round(history["val_dt_rmse"][best_epoch - 1], 3),
            "training_runtime_seconds": training_runtime,
            "hardware": "CPU (PyTorch 2.14.0+cpu)",
            "embeddings": emb_stats,
            "data_isolation_guarantee": (
                "Train partition alone was used for optimizer gradient updates and scaler fitting. "
                "Validation was used exclusively for checkpoint selection and early stopping. "
                "Test partition was strictly untouched until post-training embedding inference."
            ),
        }

        with open(self.output_dir / "tcn_training_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        return summary

    def _extract_and_save_embeddings(
        self,
        model: nn.Module,
        scaler: ChannelScaler,
        manifests: Dict[str, pd.DataFrame],
    ) -> Dict:
        """
        Extracts 64-D latent vectors z_TCN for train, val, and test partitions
        without masking (unmasked sequence inference).
        """
        ds02_dir = self.project_root / "data" / "labeling" / "ds02"
        tensors = np.load(ds02_dir / "sequences_tensor.npy")
        padding_masks = np.load(ds02_dir / "padding_mask.npy")
        manifest_full = manifests["full"]

        partitions = ["derived_ds02_train", "derived_ds02_val", "derived_ds02_test"]
        emb_counts = {}

        manifest_rows = []

        with torch.no_grad():
            for part in partitions:
                part_mask = manifest_full["partition"] == part
                part_indices = np.where(part_mask)[0]
                part_tensors = tensors[part_indices]
                part_pads = padding_masks[part_indices]

                # Normalize active timesteps with train-fitted scaler
                norm_tensors = scaler.transform(part_tensors, part_pads)

                # Batch extraction
                x_tensor = torch.from_numpy(norm_tensors).to(self.device)
                p_tensor = torch.from_numpy(part_pads).to(self.device)

                # Extract unmasked z_TCN
                z_tcn = model.encode(x_tensor, padding_mask=p_tensor).cpu().numpy()
                assert z_tcn.shape == (len(part_indices), 64)

                short_name = part.replace("derived_ds02_", "")
                save_path = self.embeddings_dir / f"{short_name}_embeddings.npy"
                np.save(save_path, z_tcn)
                emb_counts[short_name] = len(z_tcn)

                # Record manifest metadata
                part_df = manifest_full.iloc[part_indices]
                for emb_idx, (_, row) in enumerate(part_df.iterrows()):
                    manifest_rows.append({
                        "sequence_id": row["sequence_id"],
                        "fire_event_id": row["event_id"],
                        "target_detection_id": row["target_detection_id"],
                        "partition": part,
                        "embedding_index": emb_idx,
                        "embedding_file": f"{short_name}_embeddings.npy",
                        "embedding_dim": 64,
                    })

        df_emb_manifest = pd.DataFrame(manifest_rows)
        manifest_path = self.embeddings_dir / "embedding_manifest.parquet"
        df_emb_manifest.to_parquet(manifest_path, index=False)

        print(f"Embeddings saved to {self.embeddings_dir}:")
        print(f"  Train: {emb_counts['train']} x 64")
        print(f"  Val:   {emb_counts['val']} x 64")
        print(f"  Test:  {emb_counts['test']} x 64")
        print(f"  Manifest: {manifest_path} ({len(df_emb_manifest)} records)")

        return emb_counts


if __name__ == "__main__":
    trainer = TCNTrainer(Path("d:/DATA PREPROCESSING"))
    summary = trainer.train()
    print("\nTCN Training Finished:")
    print(json.dumps(summary, indent=2))
