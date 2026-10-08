"""Stage 8.34 Training and Evaluation Engine.

Provides:
1. Training loop with inner validation early-stopping.
2. Comprehensive evaluation producing Macro-F1, Balanced Accuracy, Accuracy, Per-class metrics.
3. Diagnostic Classical ML Baselines (Random Forest, Logistic Regression) for scientific ablation only.
4. ZERO ACCESS to frozen 2026 test set.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score, f1_score, balanced_accuracy_score, precision_recall_fscore_support
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CLASS_NAMES = ["Industrial Fire", "Forest Fire", "Agricultural Fire", "Persistent / Other"]

class FocalLoss(nn.Module):
    """Multi-class Focal Loss for mitigating class imbalance."""
    def __init__(self, gamma: float = 1.5, weight: Optional[torch.Tensor] = None):
        super().__init__()
        self.gamma = gamma
        self.weight = weight

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        ce_loss = F.cross_entropy(logits, targets, weight=self.weight, reduction="none")
        pt = torch.exp(-ce_loss)
        focal_loss = ((1.0 - pt) ** self.gamma) * ce_loss
        return focal_loss.mean()

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))
    prec, rec, f1, supp = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1, 2, 3], zero_division=0
    )
    per_class = {}
    for i, name in enumerate(CLASS_NAMES):
        per_class[name] = {
            "precision": round(float(prec[i]), 4),
            "recall": round(float(rec[i]), 4),
            "f1": round(float(f1[i]), 4),
            "support": int(supp[i])
        }
    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "balanced_accuracy": round(bal_acc, 4),
        "per_class": per_class
    }

def train_neural_model(
    model: nn.Module,
    train_dataset,
    val_dataset,
    epochs: int = 40,
    lr: float = 0.002,
    batch_size: int = 16,
    weight_decay: float = 1e-4,
    device: str = "cpu"
) -> Tuple[nn.Module, float, float]:
    """Trains a neural model with early stopping based on inner val loss."""
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)
    
    # Class weights based on train set
    targets = [train_dataset[i]["class_id"].item() for i in range(len(train_dataset))]
    counts = np.bincount(targets, minlength=4)
    total = len(targets)
    weights = total / (4.0 * np.maximum(counts, 1).astype(np.float32))
    class_weights = torch.tensor(weights, dtype=torch.float32).to(device)
    criterion = FocalLoss(gamma=1.5, weight=class_weights)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    best_val_loss = float("inf")
    best_weights = None

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for batch in train_loader:
            optimizer.zero_grad()
            batch = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
            out = model(batch)
            loss = criterion(out["logits"], batch["class_id"])

            # Auxiliary loss if multi-task model
            if "aux_pers_logits" in out:
                bce_pers = F.binary_cross_entropy_with_logits(out["aux_pers_logits"], batch["is_persistent"].float())
                acute_mask = batch["is_persistent"] == 0
                if acute_mask.sum() > 0:
                    ce_acute = F.cross_entropy(out["aux_acute_logits"][acute_mask], batch["subclass_id"][acute_mask])
                else:
                    ce_acute = 0.0
                loss = loss + 0.3 * bce_pers + 0.3 * ce_acute

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item() * len(batch["class_id"])

        scheduler.step()
        train_loss /= len(train_dataset)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch in val_loader:
                batch = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
                out = model(batch)
                l = criterion(out["logits"], batch["class_id"])
                val_loss += l.item() * len(batch["class_id"])
        val_loss /= len(val_dataset)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    if best_weights is not None:
        model.load_state_dict(best_weights)

    return model, train_loss, best_val_loss

def evaluate_neural_model(model: nn.Module, dataset, device: str = "cpu") -> Dict[str, Any]:
    """Evaluates neural model on given dataset and returns full metrics."""
    model.eval()
    model = model.to(device)
    loader = DataLoader(dataset, batch_size=16, shuffle=False)

    all_targets = []
    all_preds = []
    all_probs = []

    with torch.no_grad():
        for batch in loader:
            batch = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
            out = model(batch)
            probs = out["probs"].cpu().numpy()
            preds = np.argmax(probs, axis=-1)
            targets = batch["class_id"].cpu().numpy()

            all_targets.extend(targets)
            all_preds.extend(preds)
            all_probs.extend(probs)

    y_true = np.array(all_targets)
    y_pred = np.array(all_preds)
    metrics = compute_metrics(y_true, y_pred)
    metrics["targets"] = y_true.tolist()
    metrics["predictions"] = y_pred.tolist()
    metrics["probabilities"] = np.array(all_probs).tolist()
    return metrics

def evaluate_classical_baseline(
    model_type: str,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: List[str]
) -> Dict[str, Any]:
    """Evaluates classical baseline (Random Forest or Logistic Regression) strictly for diagnostic purposes."""
    X_train = train_df[feature_cols].values.astype(np.float32)
    y_train = train_df["class_id"].values.astype(np.int64)
    X_test = test_df[feature_cols].values.astype(np.float32)
    y_test = test_df["class_id"].values.astype(np.int64)

    scaler = StandardScaler()
    X_train_norm = scaler.fit_transform(np.nan_to_num(X_train))
    X_test_norm = scaler.transform(np.nan_to_num(X_test))

    if model_type == "random_forest":
        clf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, class_weight="balanced")
    elif model_type == "logistic_regression":
        clf = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
    else:
        raise ValueError(f"Unknown classical model {model_type}")

    clf.fit(X_train_norm, y_train)
    y_pred = clf.predict(X_test_norm)
    probs = clf.predict_proba(X_test_norm)

    metrics = compute_metrics(y_test, y_pred)
    metrics["targets"] = y_test.tolist()
    metrics["predictions"] = y_pred.tolist()
    metrics["probabilities"] = probs.tolist()
    return metrics
