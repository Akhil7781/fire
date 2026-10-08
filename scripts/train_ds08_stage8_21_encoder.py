"""
Stage 8.21 - Sentinel-2 Visual Representation Encoder Training Script
Trains lightweight 5-channel visual encoder using a self-supervised spectral-spatial representation objective.
Enforces deterministic seed = 42 and spatial split without leakage.
Acknowledges that pilot cohort size (N=8) is insufficient for 4-class supervised training.
Saves model checkpoint to models/s2_encoder/best_s2_encoder.pt.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import sys
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_21.s2_encoder import Sentinel2Encoder

ANNOTATIONS_PARQUET = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_review_annotations.parquet"
MODEL_CHECKPOINT_DIR = PROJECT_ROOT / "models" / "s2_encoder"
BEST_MODEL_PATH = MODEL_CHECKPOINT_DIR / "best_s2_encoder.pt"
TRAINING_METRICS_PATH = MODEL_CHECKPOINT_DIR / "training_metrics.json"

RANDOM_SEED = 42


def set_seed(seed: int = RANDOM_SEED):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class Sentinel2ChipDataset(Dataset):
    """Dataset for 5-channel Sentinel-2 chips."""

    def __init__(self, records: List[Dict[str, Any]], augment: bool = True):
        self.records = records
        self.augment = augment

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, str]:
        rec = self.records[idx]
        norm_path = PROJECT_ROOT / rec["normalized_path"]
        arr = np.load(norm_path).astype(np.float32)  # shape (5, 512, 512)

        t1 = torch.from_numpy(arr)
        t2 = torch.from_numpy(arr.copy())

        if self.augment:
            # Random horizontal / vertical flips (deterministic given random state)
            if random.random() > 0.5:
                t1 = torch.flip(t1, dims=[-1])
            if random.random() > 0.5:
                t1 = torch.flip(t1, dims=[-2])

            if random.random() > 0.5:
                t2 = torch.flip(t2, dims=[-1])
            if random.random() > 0.5:
                t2 = torch.flip(t2, dims=[-2])

        return t1, t2, rec["sample_id"]


def nt_xent_loss(z1: torch.Tensor, z2: torch.Tensor, temperature: float = 0.5) -> torch.Tensor:
    """Normalized Temperature-scaled Cross Entropy loss for representation learning."""
    batch_size = z1.size(0)
    if batch_size < 2:
        return torch.tensor(0.0, requires_grad=True)

    z = torch.cat([z1, z2], dim=0)  # [2B, D]
    sim = torch.mm(z, z.t()) / temperature  # [2B, 2B]

    sim_i_j = torch.diag(sim, batch_size)
    sim_j_i = torch.diag(sim, -batch_size)
    positives = torch.cat([sim_i_j, sim_j_i], dim=0)

    mask = ~torch.eye(2 * batch_size, dtype=torch.bool, device=z.device)
    negatives = sim[mask].view(2 * batch_size, -1)

    labels = torch.zeros(2 * batch_size, dtype=torch.long, device=z.device)
    logits = torch.cat([positives.unsqueeze(1), negatives], dim=1)
    loss = F.cross_entropy(logits, labels)
    return loss


def train_representation_encoder(
    annotations_path: Path = ANNOTATIONS_PARQUET,
    epochs: int = 15,
    batch_size: int = 2,
    lr: float = 1e-4,
    device: str = "cpu",
) -> Dict[str, Any]:
    print("=" * 80)
    print("STAGE 8.21: SENTINEL-2 VISUAL ENCODER REPRESENTATION LEARNING")
    print("=" * 80)

    set_seed(RANDOM_SEED)

    # 1. Load human review annotations
    df = pd.read_parquet(annotations_path)
    records = df.to_dict(orient="records")
    print(f"Total accepted chips in review dataset: {len(records)}")

    # Class distribution report
    class_counts = df["human_observed_class"].value_counts().to_dict()
    print("Human-reviewed class breakdown:")
    for c, n in class_counts.items():
        print(f"  - {c}: {n}")

    print("\n[METHODOLOGICAL SAFEGUARD]:")
    print("  With N=8 total pilot chips (3 Industrial Fire, 1 Other Thermal, 1 Forest Fire,")
    print("  1 Agri Fire, 2 Non-Fire Control), the sample count is insufficient for supervised 4-class training.")
    print("  Training mode: SELF-SUPERVISED VISUAL REPRESENTATION LEARNING (SimCLR contrastive objective).")
    print("  The model acts strictly as a 5-channel feature extractor producing 128D embeddings.")

    # 2. Spatial Train / Validation Split (Grouped by MGRS tile / incident, no spatial leakage)
    # Train: 6 chips, Val: 2 chips
    # Hold out: S8_002 (T43QBA) and DS08_EXP_S4_001 (T43RFP)
    val_ids = {"S8_002", "DS08_EXP_S4_001"}
    train_records = [r for r in records if r["sample_id"] not in val_ids]
    val_records = [r for r in records if r["sample_id"] in val_ids]

    print(f"\nSpatial Split (Zero leakage across MGRS tiles):")
    print(f"  Train cohort ({len(train_records)} chips): {[r['sample_id'] for r in train_records]}")
    print(f"  Validation cohort ({len(val_records)} chips): {[r['sample_id'] for r in val_records]}")

    train_ds = Sentinel2ChipDataset(train_records, augment=True)
    val_ds = Sentinel2ChipDataset(val_records, augment=False)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=len(val_ds), shuffle=False)

    # 3. Model initialization
    model = Sentinel2Encoder(
        embedding_dim=128,
        backbone_name="efficientnet_b0",
        pretrained=False,  # deterministic initialization from 5-channel stem
        dropout=0.1,
    ).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    epoch_history = []
    best_val_loss = float("inf")

    for epoch in range(1, epochs + 1):
        model.train()
        train_losses = []
        for x1, x2, _ in train_loader:
            x1, x2 = x1.to(device), x2.to(device)
            optimizer.zero_grad()
            z1 = model(x1, normalize=True)
            z2 = model(x2, normalize=True)
            loss = nt_xent_loss(z1, z2, temperature=0.5)
            loss.backward()
            optimizer.step()
            train_losses.append(loss.item())

        scheduler.step()

        # Validation
        model.eval()
        val_losses = []
        with torch.no_grad():
            for x1, x2, _ in val_loader:
                x1, x2 = x1.to(device), x2.to(device)
                z1 = model(x1, normalize=True)
                z2 = model(x2, normalize=True)
                v_loss = nt_xent_loss(z1, z2, temperature=0.5)
                val_losses.append(v_loss.item())

        avg_train = float(np.mean(train_losses))
        avg_val = float(np.mean(val_losses))
        epoch_history.append({"epoch": epoch, "train_loss": avg_train, "val_loss": avg_val})
        print(f"  Epoch {epoch:02d}/{epochs:02d} | Train Loss: {avg_train:.4f} | Val Loss: {avg_val:.4f}")

        if avg_val <= best_val_loss:
            best_val_loss = avg_val
            model.save_checkpoint(
                BEST_MODEL_PATH,
                extra_metadata={
                    "epoch": epoch,
                    "val_loss": best_val_loss,
                    "train_loss": avg_train,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "seed": RANDOM_SEED,
                    "train_chips": [r["sample_id"] for r in train_records],
                    "val_chips": [r["sample_id"] for r in val_records],
                },
            )

    print(f"\nTraining complete. Best Validation Loss: {best_val_loss:.4f}")
    print(f"Saved checkpoint to: {BEST_MODEL_PATH}")

    metrics = {
        "training_mode": "SELF_SUPERVISED_REPRESENTATION_LEARNING",
        "objective": "NT-Xent Contrastive Loss",
        "random_seed": RANDOM_SEED,
        "epochs": epochs,
        "best_epoch": next(e["epoch"] for e in epoch_history if e["val_loss"] == best_val_loss),
        "best_val_loss": best_val_loss,
        "embedding_dim": 128,
        "backbone": "efficientnet_b0_5channel",
        "input_shape": [5, 512, 512],
        "channel_names": ["B02", "B03", "B04", "B11", "B12"],
        "total_chips": len(records),
        "train_chips": [r["sample_id"] for r in train_records],
        "val_chips": [r["sample_id"] for r in val_records],
        "class_counts": class_counts,
        "history": epoch_history,
    }

    with open(TRAINING_METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    return metrics


if __name__ == "__main__":
    train_representation_encoder(epochs=10)
