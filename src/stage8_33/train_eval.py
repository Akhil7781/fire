"""
Stage 8.33 Training and Evaluation Utility Module.
Handles PyTorch model training, early stopping, evaluation, and calibration.
DEEP LEARNING ONLY. STRICT TEST LOCK.
"""

import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score, f1_score, balanced_accuracy_score, precision_recall_fscore_support, confusion_matrix

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_33.dataset import MultiModalThermalDataset, get_feature_groups
from src.stage8_33.model import FocalLoss, HierarchicalLoss

CLASS_NAMES = [
    "Industrial Fire",
    "Forest Fire",
    "Agricultural Fire",
    "Other / Persistent"
]

def compute_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    """Computes Expected Calibration Error (ECE) across multi-class predictions."""
    preds = np.argmax(probs, axis=1)
    confs = np.max(probs, axis=1)
    accs = (preds == labels).astype(float)
    
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        in_bin = (confs > bin_boundaries[i]) & (confs <= bin_boundaries[i + 1])
        prop_in_bin = np.mean(in_bin)
        if prop_in_bin > 0:
            acc_in_bin = np.mean(accs[in_bin])
            conf_in_bin = np.mean(confs[in_bin])
            ece += np.abs(acc_in_bin - conf_in_bin) * prop_in_bin
    return float(ece)

def compute_brier_score(probs: np.ndarray, labels: np.ndarray) -> float:
    """Computes multi-class Brier score."""
    n_classes = probs.shape[1]
    one_hot = np.zeros_like(probs)
    for i, c in enumerate(labels):
        one_hot[i, c] = 1.0
    return float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)))

def evaluate_model(
    model: nn.Module,
    val_dataset: MultiModalThermalDataset,
    batch_size: int = 32,
    device: str = "cpu"
) -> Dict[str, Any]:
    """Evaluates a PyTorch model on a dataset and computes all performance metrics."""
    model.eval()
    loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    all_preds = []
    all_targets = []
    all_probs = []
    all_event_ids = []

    with torch.no_grad():
        for batch in loader:
            batch_dev = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
            probs = model.predict_probabilities(batch_dev)
            preds = torch.argmax(probs, dim=-1)
            
            all_probs.append(probs.cpu().numpy())
            all_preds.append(preds.cpu().numpy())
            all_targets.append(batch["class_id"].numpy())
            all_event_ids.extend(batch["event_id"])

    y_true = np.concatenate(all_targets)
    y_pred = np.concatenate(all_preds)
    probs_mat = np.concatenate(all_probs)

    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))

    prec, rec, f1s, supp = precision_recall_fscore_support(y_true, y_pred, labels=[0, 1, 2, 3], zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2, 3])

    ece = compute_ece(probs_mat, y_true)
    brier = compute_brier_score(probs_mat, y_true)

    per_class = {}
    for i, name in enumerate(CLASS_NAMES):
        per_class[name] = {
            "precision": round(float(prec[i]), 4),
            "recall": round(float(rec[i]), 4),
            "f1": round(float(f1s[i]), 4),
            "support": int(supp[i]),
            "tp": int(cm[i, i]),
            "fp": int(cm[:, i].sum() - cm[i, i]),
            "fn": int(cm[i, :].sum() - cm[i, i])
        }

    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "balanced_accuracy": round(bal_acc, 4),
        "brier_score": round(brier, 4),
        "ece": round(ece, 4),
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "probabilities": probs_mat,
        "predictions": y_pred,
        "targets": y_true,
        "event_ids": all_event_ids
    }

def train_model(
    model: nn.Module,
    train_dataset: MultiModalThermalDataset,
    val_dataset: Optional[MultiModalThermalDataset] = None,
    epochs: int = 45,
    lr: float = 0.002,
    weight_decay: float = 1e-4,
    loss_type: str = "focal_loss",
    gamma: float = 1.5,
    batch_size: int = 16,
    device: str = "cpu"
) -> Tuple[nn.Module, List[float], List[float]]:
    """Trains a PyTorch model with specified loss function and returns history."""
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    
    # Class weights computed on training set
    train_classes = train_dataset.class_ids
    class_counts = np.bincount(train_classes, minlength=4)
    weights = np.zeros(4, dtype=np.float32)
    for c in range(4):
        weights[c] = (len(train_classes) / (4.0 * max(class_counts[c], 1)))
    weight_tensor = torch.tensor(weights, dtype=torch.float32).to(device)

    if loss_type == "focal_loss":
        criterion_4c = FocalLoss(alpha=weight_tensor, gamma=gamma)
    else: # weighted_ce
        criterion_4c = nn.CrossEntropyLoss(weight=weight_tensor)

    criterion_bin = nn.CrossEntropyLoss()
    criterion_sub = nn.CrossEntropyLoss()
    hierarchical_loss = HierarchicalLoss()

    loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    train_losses = []
    val_losses = []
    best_val_f1 = -1.0
    best_state = None

    for ep in range(epochs):
        model.train()
        ep_loss = 0.0
        n_batches = 0
        for batch in loader:
            batch_dev = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
            optimizer.zero_grad()
            
            out = model(batch_dev)
            cid = batch_dev["class_id"]

            if loss_type == "hierarchical" and "logits_binary" in out and "logits_subclass" in out:
                loss = hierarchical_loss(out["logits_binary"], out["logits_subclass"], cid)
                if "logits_4class" in out:
                    loss = loss + 0.5 * criterion_4c(out["logits_4class"], cid)
            elif "logits_binary" in out and "logits_subclass" in out:
                # Multi-task loss
                loss_4c = criterion_4c(out["logits_4class"], cid)
                loss_bin = criterion_bin(out["logits_binary"], batch_dev["is_persistent"])
                
                acute_mask = (cid < 3)
                if acute_mask.sum() > 0:
                    loss_sub = criterion_sub(out["logits_subclass"][acute_mask], batch_dev["subclass_id"][acute_mask])
                else:
                    loss_sub = torch.tensor(0.0, device=device)
                
                loss = loss_4c + 0.5 * loss_bin + 0.5 * loss_sub
            else:
                loss = criterion_4c(out["logits_4class"], cid)

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
            optimizer.step()

            ep_loss += loss.item()
            n_batches += 1

        avg_tr_loss = ep_loss / max(n_batches, 1)
        train_losses.append(avg_tr_loss)

        if val_dataset is not None:
            val_eval = evaluate_model(model, val_dataset, batch_size=batch_size, device=device)
            val_f1 = val_eval["macro_f1"]
            val_losses.append(val_eval["brier_score"])
            if val_f1 > best_val_f1:
                best_val_f1 = val_f1
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    return model, train_losses, val_losses
