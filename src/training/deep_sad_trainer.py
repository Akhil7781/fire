"""
Deep SAD Semi-Supervised Anomaly Training, Checkpointing, and Embeddings Pipeline.

Enforces:
  1. Strict Data Isolation:
     - Optimization updates: TRAIN ONLY (578,465 rows).
     - Validation: Checkpoint selection and metric tracking only.
     - Heldout spatial and test: Strictly untouched during optimization.
  2. Target Semantics:
     - Unlabeled = UNKNOWN (contracted toward c with gamma = 0.10).
     - Acute anchors = ANOMALY (y = -1, repelled from c via inverse quadratic penalty).
     - Persistent confounders = EXCLUDED from center and training loss.
  3. Preprocessing:
     - Train-only feature normalization for the 27 causal predictors.
  4. Center Invariant:
     - Initialized from 20,000 active unlabeled training samples.
     - Checked ||c|| >= 0.10.
     - Frozen permanently throughout training.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.utils.data import DataLoader, TensorDataset

import sys

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.deep_sad import DeepSAD


@dataclass
class DeepSADConfig:
    """Hyperparameters and configuration for Deep SAD training."""
    in_features: int = 27
    latent_dim: int = 32
    leaky_relu_slope: float = 0.1
    batch_size: int = 1024
    learning_rate: float = 1e-3
    weight_decay: float = 1e-6
    gamma: float = 0.10
    eta: float = 1.0
    epsilon: float = 1e-6
    n_init: int = 20000
    max_epochs: int = 20
    patience: int = 8
    seed: int = 42

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> DeepSADConfig:
        return cls(**data)


class DeepSADTrainer:
    """
    Manages semi-supervised anomaly representation training for Deep SAD.
    """

    def __init__(
        self,
        project_root: Path,
        config: Optional[DeepSADConfig] = None,
    ):
        self.project_root = project_root
        self.config = config or DeepSADConfig()
        self.output_dir = project_root / "models" / "deep_sad"
        self.embeddings_dir = project_root / "data" / "embeddings" / "deep_sad"

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)

        self.device = torch.device("cpu")

        # Set fixed deterministic seeds
        torch.manual_seed(self.config.seed)
        np.random.seed(self.config.seed)

    def load_and_preprocess_features(self) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray], Dict[str, List[float]]]:
        """
        Loads 27 causal features from causal_features_2025.parquet,
        quarantines persistent confounders, identifies acute anchors from Manifest B,
        and standardizes features strictly using train-only statistics.
        """
        cf_path = self.project_root / "data" / "interim" / "causal_features_2025.parquet"
        confounders_path = self.project_root / "data" / "labeling" / "ds05" / "ds05_quarantined_confounders.parquet"
        ds03_path = self.project_root / "data" / "labeling" / "ds03" / "forest_fire_candidates.parquet"
        ds04_path = self.project_root / "data" / "labeling" / "ds04" / "agriculture_fire_candidates.parquet"
        ds05_path = self.project_root / "data" / "labeling" / "ds05" / "ds05_valid_industrial_anchors.parquet"

        # Load confounder and anchor IDs
        confounders_df = pd.read_parquet(confounders_path, columns=["detection_id"])
        confounder_ids = set(confounders_df["detection_id"])

        f3 = pd.read_parquet(ds03_path, columns=["detection_id", "fire_event_id"])
        f4 = pd.read_parquet(ds04_path, columns=["detection_id", "fire_event_id"])
        f5 = pd.read_parquet(ds05_path, columns=["detection_id", "incident_id"])

        anchor_ids = set(f3["detection_id"]).union(set(f4["detection_id"])).union(set(f5["detection_id"]))

        # Load primary feature table
        cols_to_load = [c for c in DeepSAD.FEATURE_NAMES if c != "daynight_binary"] + ["daynight", "detection_id", "partition"]
        df = pd.read_parquet(cf_path, columns=cols_to_load)

        # Derive daynight_binary
        df["daynight_binary"] = (df["daynight"] == "D").astype(np.float32)
        df["has_prior_24h_2km"] = df["has_prior_24h_2km"].astype(np.float32)

        feature_cols = DeepSAD.FEATURE_NAMES

        # Filter partitions
        train_mask = df["partition"] == "train"
        val_mask = df["partition"] == "val"
        heldout_mask = df["partition"] == "train_heldout_spatial"
        test_mask = df["partition"] == "test"
        test_seen_mask = df["partition"] == "test_seen_spatial"

        # Separate train subsets
        df_train = df[train_mask].copy()
        train_is_confounder = df_train["detection_id"].isin(confounder_ids)
        train_is_anchor = df_train["detection_id"].isin(anchor_ids)
        train_is_unlabeled = (~train_is_confounder) & (~train_is_anchor)

        # Train unlabeled pool and anchors
        train_unlabeled_feats = df_train.loc[train_is_unlabeled, feature_cols].to_numpy(dtype=np.float32)
        train_anchor_feats = df_train.loc[train_is_anchor, feature_cols].to_numpy(dtype=np.float32)

        # Fit normalizer strictly on train unlabeled pool
        means = train_unlabeled_feats.mean(axis=0)
        stds = train_unlabeled_feats.std(axis=0)
        stds = np.where(stds < 1e-6, 1.0, stds).astype(np.float32)
        means = means.astype(np.float32)

        scaler_params = {
            "means": means.tolist(),
            "stds": stds.tolist(),
            "feature_names": feature_cols,
        }
        with open(self.output_dir / "scaler_params.json", "w") as f:
            json.dump(scaler_params, f, indent=2)

        def scale_array(arr: np.ndarray) -> np.ndarray:
            return (arr - means) / stds

        # Scale train features
        train_unlabeled_scaled = scale_array(train_unlabeled_feats)
        train_anchor_scaled = scale_array(train_anchor_feats)

        # Validation set
        df_val = df[val_mask].copy()
        val_is_confounder = df_val["detection_id"].isin(confounder_ids)
        val_is_anchor = df_val["detection_id"].isin(anchor_ids)
        val_is_unlabeled = (~val_is_confounder) & (~val_is_anchor)

        val_unlabeled_scaled = scale_array(df_val.loc[val_is_unlabeled, feature_cols].to_numpy(dtype=np.float32))
        val_anchor_scaled = scale_array(df_val.loc[val_is_anchor, feature_cols].to_numpy(dtype=np.float32))

        # Full partition arrays for post-training embedding extraction
        partitions_data = {
            "train": scale_array(df.loc[train_mask, feature_cols].to_numpy(dtype=np.float32)),
            "val": scale_array(df.loc[val_mask, feature_cols].to_numpy(dtype=np.float32)),
            "heldout_spatial": scale_array(df.loc[heldout_mask, feature_cols].to_numpy(dtype=np.float32)),
            "test": scale_array(df.loc[test_mask, feature_cols].to_numpy(dtype=np.float32)),
            "test_seen_spatial": scale_array(df.loc[test_seen_mask, feature_cols].to_numpy(dtype=np.float32)),
        }

        train_data = {
            "unlabeled": train_unlabeled_scaled,
            "anchors": train_anchor_scaled,
            "val_unlabeled": val_unlabeled_scaled,
            "val_anchors": val_anchor_scaled,
        }

        metadata = {
            "train_unlabeled_count": len(train_unlabeled_feats),
            "train_anchor_count": len(train_anchor_feats),
            "train_confounder_count": int(train_is_confounder.sum()),
            "val_unlabeled_count": int(val_is_unlabeled.sum()),
            "val_anchor_count": int(val_is_anchor.sum()),
            "val_confounder_count": int(val_is_confounder.sum()),
        }

        return train_data, partitions_data, scaler_params

    def train(self) -> Dict:
        """
        Executes full Deep SAD training with frozen center and inverse margin repulsion.
        """
        start_time = time.time()
        cfg = self.config

        print("Loading and standardizing 27 causal features...")
        train_data, partitions_data, scaler_params = self.load_and_preprocess_features()

        X_u = torch.from_numpy(train_data["unlabeled"]).to(self.device)
        X_a = torch.from_numpy(train_data["anchors"]).to(self.device)
        X_val_u = torch.from_numpy(train_data["val_unlabeled"]).to(self.device)
        X_val_a = torch.from_numpy(train_data["val_anchors"]).to(self.device)

        print(f"Data Loaded:")
        print(f"  Train Unlabeled Pool: {len(X_u):,} rows")
        print(f"  Train Acute Anchors:  {len(X_a)} rows (y = -1)")
        print(f"  Val Unlabeled Pool:   {len(X_val_u):,} rows")
        print(f"  Val Acute Anchors:    {len(X_val_a)} rows (y = -1)")

        # 1. Initialize Deep SAD model
        model = DeepSAD(
            in_features=cfg.in_features,
            latent_dim=cfg.latent_dim,
            leaky_relu_slope=cfg.leaky_relu_slope,
        ).to(self.device)

        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        assert total_params == 13696, f"Expected 13,696 parameters, got {total_params}"

        # 2. Initialize Center c from 20,000 active unlabeled training samples
        indices = np.random.choice(len(X_u), size=min(cfg.n_init, len(X_u)), replace=False)
        x_init = X_u[indices]
        c = model.init_center(x_init, eps_norm=0.10)
        c_norm = torch.norm(c).item()
        print(f"Center Initialized: norm = {c_norm:.4f} >= 0.10 (FROZEN)")
        assert c_norm >= 0.10, "Center norm violation!"

        np.save(self.output_dir / "center.npy", c.cpu().numpy())

        # 3. Setup optimizer
        optimizer = AdamW(
            model.parameters(),
            lr=cfg.learning_rate,
            weight_decay=cfg.weight_decay,
        )

        dataset_u = TensorDataset(X_u)
        loader_u = DataLoader(dataset_u, batch_size=cfg.batch_size, shuffle=True)

        history = {
            "epoch": [],
            "train_loss": [],
            "train_loss_unlabeled": [],
            "train_loss_repulsion": [],
            "val_loss": [],
            "val_mean_score_unlabeled": [],
            "val_mean_score_anchors": [],
            "val_separation_ratio": [],
        }

        best_val_loss = float("inf")
        best_epoch = 0
        patience_counter = 0

        print(f"\nStarting Deep SAD Training ({cfg.max_epochs} epochs, batch_size={cfg.batch_size}):")

        for epoch in range(1, cfg.max_epochs + 1):
            model.train()
            epoch_loss = 0.0
            epoch_loss_u = 0.0
            epoch_loss_a = 0.0
            n_batches = 0

            for (batch_x_u,) in loader_u:
                optimizer.zero_grad()

                # Forward pass on unlabeled batch
                z_u = model(batch_x_u)
                d_u_sq = torch.sum((z_u - model.c.unsqueeze(0)) ** 2, dim=-1)
                loss_u = cfg.gamma * torch.mean(d_u_sq)

                # Forward pass on acute anchors (repulsion)
                z_a = model(X_a)
                d_a_sq = torch.sum((z_a - model.c.unsqueeze(0)) ** 2, dim=-1)
                loss_a = cfg.eta * torch.mean(1.0 / (d_a_sq + cfg.epsilon))

                loss = loss_u + loss_a
                assert torch.isfinite(loss), f"Encountered non-finite loss at epoch {epoch}: {loss.item()}"

                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

                epoch_loss += loss.item()
                epoch_loss_u += loss_u.item()
                epoch_loss_a += loss_a.item()
                n_batches += 1

            avg_train_loss = epoch_loss / n_batches
            avg_train_u = epoch_loss_u / n_batches
            avg_train_a = epoch_loss_a / n_batches

            # Validation evaluation
            model.eval()
            with torch.no_grad():
                # Val unlabeled scores in batches
                val_u_scores = []
                for i in range(0, len(X_val_u), cfg.batch_size):
                    batch_val = X_val_u[i:i + cfg.batch_size]
                    s_u = model.compute_anomaly_score(batch_val)
                    val_u_scores.append(s_u)
                val_u_scores = torch.cat(val_u_scores)
                val_mean_u = torch.mean(val_u_scores).item()

                # Val anchors score
                val_a_scores = model.compute_anomaly_score(X_val_a)
                val_mean_a = torch.mean(val_a_scores).item()
                separation = val_mean_a / max(val_mean_u, 1e-6)

                val_loss_u = cfg.gamma * val_mean_u
                val_loss_a = cfg.eta * torch.mean(1.0 / (val_a_scores + cfg.epsilon)).item()
                val_loss = val_loss_u + val_loss_a

            history["epoch"].append(epoch)
            history["train_loss"].append(round(avg_train_loss, 5))
            history["train_loss_unlabeled"].append(round(avg_train_u, 5))
            history["train_loss_repulsion"].append(round(avg_train_a, 5))
            history["val_loss"].append(round(val_loss, 5))
            history["val_mean_score_unlabeled"].append(round(val_mean_u, 4))
            history["val_mean_score_anchors"].append(round(val_mean_a, 4))
            history["val_separation_ratio"].append(round(separation, 2))

            status_str = ""
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_epoch = epoch
                patience_counter = 0
                status_str = " -> BEST CHECKPOINT"
                # Save best checkpoint
                torch.save({
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "center": model.c.clone(),
                    "val_loss": val_loss,
                    "val_separation_ratio": separation,
                    "config": cfg.to_dict(),
                    "scaler_params": scaler_params,
                }, self.output_dir / "best_deep_sad.pt")
            else:
                patience_counter += 1

            print(
                f"Epoch {epoch:02d}/{cfg.max_epochs} | "
                f"Train Loss: {avg_train_loss:.4f} (Contr: {avg_train_u:.4f}, Repel: {avg_train_a:.4f}) | "
                f"Val Loss: {val_loss:.4f} | Val Score (Unl): {val_mean_u:.2f} | "
                f"Val Score (Anc): {val_mean_a:.2f} | Sep Ratio: {separation:.2f}x{status_str}"
            )

            if patience_counter >= cfg.patience:
                print(f"Early stopping triggered at epoch {epoch} (best epoch: {best_epoch})")
                break

        # Save final checkpoint
        torch.save({
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "center": model.c.clone(),
            "val_loss": val_loss,
            "config": cfg.to_dict(),
            "scaler_params": scaler_params,
        }, self.output_dir / "final_deep_sad.pt")

        with open(self.output_dir / "config.json", "w") as f:
            json.dump(cfg.to_dict(), f, indent=2)

        with open(self.output_dir / "training_history.json", "w") as f:
            json.dump(history, f, indent=2)

        training_time = time.time() - start_time
        print(f"\nTraining completed in {training_time:.2f}s. Best Epoch: {best_epoch} (Val Loss: {best_val_loss:.4f})")

        # 4. Generate post-training embeddings and scores using best checkpoint
        print("\nExtracting post-training 32-D latent representations and anomaly scores...")
        best_ckpt = torch.load(self.output_dir / "best_deep_sad.pt", map_location=self.device)
        model.load_state_dict(best_ckpt["model_state_dict"])
        model.c.copy_(best_ckpt["center"])
        model.is_center_initialized = True
        model.eval()

        counts = self.extract_all_partition_embeddings(model, partitions_data)

        summary = {
            "model_architecture": "Deep SAD (3-Layer MLP)",
            "in_features": cfg.in_features,
            "latent_dim": cfg.latent_dim,
            "total_parameters": total_params,
            "best_epoch": best_epoch,
            "total_epochs_trained": epoch,
            "best_val_loss": round(best_val_loss, 4),
            "final_train_loss": round(avg_train_loss, 4),
            "center_norm": round(float(torch.norm(model.c).item()), 4),
            "training_runtime_seconds": round(training_time, 2),
            "hardware": "CPU (PyTorch 2.14.0+cpu)",
            "partition_counts": counts,
        }
        with open(self.output_dir / "deep_sad_training_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        return summary

    def extract_all_partition_embeddings(
        self,
        model: DeepSAD,
        partitions_data: Dict[str, np.ndarray],
    ) -> Dict[str, int]:
        """
        Extracts 32-D latent representations and anomaly scores across all partitions.
        """
        counts = {}
        manifest_rows = []

        with torch.no_grad():
            for part_name, data_arr in partitions_data.items():
                emb_list = []
                score_list = []
                batch_size = 2048

                for i in range(0, len(data_arr), batch_size):
                    batch = torch.from_numpy(data_arr[i:i + batch_size]).to(self.device)
                    z = model(batch)
                    s = model.compute_anomaly_score(batch)
                    emb_list.append(z.cpu().numpy())
                    score_list.append(s.cpu().numpy())

                embs = np.concatenate(emb_list, axis=0)
                scores = np.concatenate(score_list, axis=0)

                np.save(self.embeddings_dir / f"{part_name}_embeddings.npy", embs)
                np.save(self.embeddings_dir / f"{part_name}_scores.npy", scores)
                counts[part_name] = len(embs)
                print(f"  {part_name:18s}: {len(embs):>7,d} rows -> {part_name}_embeddings.npy (32-D), {part_name}_scores.npy")

                manifest_rows.append({
                    "partition": part_name,
                    "row_count": len(embs),
                    "embedding_file": f"{part_name}_embeddings.npy",
                    "score_file": f"{part_name}_scores.npy",
                    "latent_dim": 32,
                    "mean_score": round(float(scores.mean()), 4),
                    "std_score": round(float(scores.std()), 4),
                    "median_score": round(float(np.median(scores)), 4),
                    "q95_score": round(float(np.percentile(scores, 95)), 4),
                })

        pd.DataFrame(manifest_rows).to_parquet(self.embeddings_dir / "deep_sad_embedding_manifest.parquet", index=False)
        return counts


if __name__ == "__main__":
    trainer = DeepSADTrainer(PROJECT_ROOT)
    summary = trainer.train()
    print("\nDeep SAD Execution Summary:")
    print(json.dumps(summary, indent=2))
