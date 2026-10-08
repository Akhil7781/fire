"""
Stage 8.22: Model Training, Baselines, Ablations, and Explainability Module.
Implements:
1. Deterministic training of MultimodalLateFusionMLP with class weighting.
2. Comprehensive evaluation with honest N/A reporting for zero-support classes.
3. 6 standard baseline comparisons.
4. 9 modality ablation evaluations.
5. Modality-level interpretability (Leave-One-Modality-Out).
6. Persistence integration and evidence-based prediction explanations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

from src.stage8_22.fusion_cohort import (
    CAUSAL_GEO_FEATURES,
    CLASS_NAME_TO_ID,
    ID_TO_CLASS_NAME,
    MODALITY_DIMS,
    MODALITY_NAMES,
    TARGET_TAXONOMY,
)
from src.stage8_22.fusion_model import MultimodalLateFusionMLP

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models" / "fusion"


def confusion_matrix_np(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int = 4) -> np.ndarray:
    """Computes confusion matrix using pure NumPy without sklearn."""
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        if 0 <= t < num_classes and 0 <= p < num_classes:
            cm[t, p] += 1
    return cm


class MultimodalFusionDataset(Dataset):
    """PyTorch dataset for multimodal fusion tensors."""

    def __init__(self, df: pd.DataFrame, is_train: bool = False):
        self.df = df.reset_index(drop=True)
        self.is_train = is_train

        # Extract tensor blocks
        tcn_cols = [f"z_tcn_{i}" for i in range(MODALITY_DIMS["tcn"])]
        sad_cols = [f"z_sad_{i}" for i in range(MODALITY_DIMS["sad"])]
        infra_cols = [f"z_infra_{i}" for i in range(MODALITY_DIMS["yolo_infra"])]
        fire_cols = [f"z_fire_smoke_{i}" for i in range(MODALITY_DIMS["yolo_fire"])]
        s2_cols = [f"z_s2_{i}" for i in range(MODALITY_DIMS["s2"])]
        geo_cols = CAUSAL_GEO_FEATURES
        mask_cols = [f"mask_{name}" for name in MODALITY_NAMES]

        self.x_tcn = torch.tensor(self.df[tcn_cols].values, dtype=torch.float32)
        self.x_sad = torch.tensor(self.df[sad_cols].values, dtype=torch.float32)
        self.x_infra = torch.tensor(self.df[infra_cols].values, dtype=torch.float32)
        self.x_fire = torch.tensor(self.df[fire_cols].values, dtype=torch.float32)
        self.x_s2 = torch.tensor(self.df[s2_cols].values, dtype=torch.float32)
        self.x_geo = torch.tensor(self.df[geo_cols].values, dtype=torch.float32)
        self.mask = torch.tensor(self.df[mask_cols].values, dtype=torch.float32)

        # Target class: only valid non-negative labels
        self.targets = torch.tensor(self.df["target_class_id"].values, dtype=torch.long)
        self.detection_ids = self.df["detection_id"].tolist()

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return {
            "x_tcn": self.x_tcn[idx],
            "x_sad": self.x_sad[idx],
            "x_infra": self.x_infra[idx],
            "x_fire": self.x_fire[idx],
            "x_s2": self.x_s2[idx],
            "x_geo": self.x_geo[idx],
            "mask": self.mask[idx],
            "target": self.targets[idx],
            "index": torch.tensor(idx, dtype=torch.long),
        }


def compute_classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Computes classification metrics with strict N/A reporting for classes with zero support.
    """
    cm = confusion_matrix_np(y_true, y_pred, num_classes=4)
    num_classes = len(TARGET_TAXONOMY)

    per_class_metrics: Dict[str, Dict[str, Any]] = {}
    valid_f1s: List[float] = []
    valid_recalls: List[float] = []

    for c in range(num_classes):
        cname = ID_TO_CLASS_NAME[c]
        support = int((y_true == c).sum())
        predicted_count = int((y_pred == c).sum())
        tp = int(cm[c, c])

        if support == 0:
            per_class_metrics[cname] = {
                "support": 0,
                "predicted": predicted_count,
                "precision": "N/A",
                "recall": "N/A",
                "f1": "N/A",
            }
        else:
            recall = tp / support if support > 0 else 0.0
            precision = tp / predicted_count if predicted_count > 0 else 0.0
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

            per_class_metrics[cname] = {
                "support": support,
                "predicted": predicted_count,
                "precision": round(float(precision), 4),
                "recall": round(float(recall), 4),
                "f1": round(float(f1), 4),
            }
            valid_f1s.append(f1)
            valid_recalls.append(recall)

    macro_f1 = float(np.mean(valid_f1s)) if valid_f1s else 0.0
    balanced_acc = float(np.mean(valid_recalls)) if valid_recalls else 0.0
    overall_acc = float((y_true == y_pred).mean()) if len(y_true) > 0 else 0.0

    return {
        "overall_accuracy": round(overall_acc, 4),
        "balanced_accuracy": round(balanced_acc, 4),
        "macro_f1": round(macro_f1, 4),
        "supported_classes_count": len(valid_f1s),
        "per_class": per_class_metrics,
        "confusion_matrix": cm.tolist(),
        "total_samples": len(y_true),
    }


def train_fusion_model(
    df_labeled: pd.DataFrame,
    epochs: int = 15,
    batch_size: int = 32,
    lr: float = 1e-3,
    weight_decay: float = 1e-4,
    random_seed: int = 42,
    output_dir: Optional[Path] = None,
) -> Tuple[MultimodalLateFusionMLP, Dict[str, Any]]:
    """
    Trains MultimodalLateFusionMLP using class-weighted Cross-Entropy loss.
    """
    torch.manual_seed(random_seed)
    np.random.seed(random_seed)

    save_dir = output_dir or MODELS_DIR
    save_dir.mkdir(parents=True, exist_ok=True)

    # Exclude non-fire uncertain controls from supervised loss
    df_sup = df_labeled[df_labeled["target_class_id"] >= 0].copy()

    # Split into train, val, test
    train_mask = df_sup["partition"].isin(["train", "train_heldout_spatial"])
    val_mask = df_sup["partition"] == "val"
    test_mask = df_sup["partition"].isin(["test", "test_seen_spatial"])

    df_train = df_sup[train_mask].reset_index(drop=True)
    df_val = df_sup[val_mask].reset_index(drop=True)
    df_test = df_sup[test_mask].reset_index(drop=True)

    print(f"Training partition size: {len(df_train)} (Classes: {df_train['target_class_id'].value_counts().to_dict()})")
    print(f"Validation partition size: {len(df_val)} (Classes: {df_val['target_class_id'].value_counts().to_dict()})")
    print(f"Test partition size: {len(df_test)} (Classes: {df_test['target_class_id'].value_counts().to_dict()})")

    # Compute class weights for imbalanced loss
    # Classes with 0 train instances receive weight 1.0; others inverse frequency
    class_counts = df_train["target_class_id"].value_counts().to_dict()
    total_train = len(df_train)
    weights = []
    for c in range(4):
        cnt = class_counts.get(c, 0)
        if cnt == 0:
            weights.append(1.0)
        else:
            # Smoothed inverse frequency
            w = total_train / (4.0 * cnt)
            weights.append(float(w))
    weights_tensor = torch.tensor(weights, dtype=torch.float32)
    print(f"Computed loss class weights: {[round(w, 3) for w in weights]}")

    train_ds = MultimodalFusionDataset(df_train, is_train=True)
    val_ds = MultimodalFusionDataset(df_val, is_train=False)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    model = MultimodalLateFusionMLP()
    criterion = nn.CrossEntropyLoss(weight=weights_tensor)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    best_val_loss = float("inf")
    best_state = None
    best_epoch = 0
    history = []

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        for batch in train_loader:
            optimizer.zero_grad()
            logits = model(
                batch["x_tcn"],
                batch["x_sad"],
                batch["x_infra"],
                batch["x_fire"],
                batch["x_s2"],
                batch["x_geo"],
                batch["mask"],
            )
            loss = criterion(logits, batch["target"])
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(batch["target"])

        train_loss /= len(train_ds)

        # Validation pass
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch in val_loader:
                logits = model(
                    batch["x_tcn"],
                    batch["x_sad"],
                    batch["x_infra"],
                    batch["x_fire"],
                    batch["x_s2"],
                    batch["x_geo"],
                    batch["mask"],
                )
                loss = criterion(logits, batch["target"])
                val_loss += loss.item() * len(batch["target"])
        val_loss /= len(val_ds) if len(val_ds) > 0 else 1.0

        history.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss})
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    # Load best weights
    if best_state is not None:
        model.load_state_dict(best_state)

    # Save model checkpoint and metadata
    checkpoint_path = save_dir / "best_multimodal_fusion.pt"
    model.save_checkpoint(checkpoint_path, extra_metadata={
        "best_epoch": best_epoch,
        "best_val_loss": best_val_loss,
        "epochs": epochs,
        "random_seed": random_seed,
    })

    # Save training config & metrics
    metrics_path = save_dir / "training_metrics.json"
    config_path = save_dir / "fusion_config.json"
    schema_path = save_dir / "feature_schema.json"

    training_summary = {
        "best_epoch": best_epoch,
        "best_val_loss": round(best_val_loss, 4),
        "epochs": epochs,
        "history": history,
        "train_samples": len(df_train),
        "val_samples": len(df_val),
        "test_samples": len(df_test),
        "class_weights": weights,
    }
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(training_summary, f, indent=2)

    config = {
        "architecture": "MultimodalLateFusionMLP",
        "proj_dim": 64,
        "fusion_hidden_dim": 256,
        "fused_embedding_dim": 128,
        "num_classes": 4,
        "dropout": 0.2,
        "optimizer": "AdamW",
        "lr": lr,
        "weight_decay": weight_decay,
        "seed": random_seed,
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    schema = {
        "modality_dimensions": MODALITY_DIMS,
        "modality_names": MODALITY_NAMES,
        "causal_geo_features": CAUSAL_GEO_FEATURES,
        "target_taxonomy": TARGET_TAXONOMY,
    }
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    print(f"\nModel training complete. Best checkpoint saved to {checkpoint_path}.")
    return model, training_summary


def evaluate_dataset(
    model: MultimodalLateFusionMLP,
    dataset: MultimodalFusionDataset,
    override_mask: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Runs inference and computes classification metrics on a dataset."""
    model.eval()
    loader = DataLoader(dataset, batch_size=64, shuffle=False)

    all_preds = []
    all_targets = []
    all_probs = []

    with torch.no_grad():
        for batch in loader:
            mask = batch["mask"]
            if override_mask is not None:
                mask = torch.tensor(override_mask, dtype=torch.float32).repeat(len(mask), 1)

            logits = model(
                batch["x_tcn"],
                batch["x_sad"],
                batch["x_infra"],
                batch["x_fire"],
                batch["x_s2"],
                batch["x_geo"],
                mask,
            )
            probs = F.softmax(logits, dim=-1)
            preds = torch.argmax(probs, dim=-1)

            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(batch["target"].cpu().numpy())
            all_probs.extend(probs.cpu().numpy())

    return compute_classification_metrics(
        np.array(all_targets),
        np.array(all_preds),
        np.array(all_probs),
    )


def run_baselines_and_ablations(
    model: MultimodalLateFusionMLP,
    df_labeled: pd.DataFrame,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Evaluates standard baselines and ablation studies across validation and test splits.
    """
    df_sup = df_labeled[df_labeled["target_class_id"] >= 0].copy()
    val_ds = MultimodalFusionDataset(df_sup[df_sup["partition"] == "val"], is_train=False)
    test_ds = MultimodalFusionDataset(df_sup[df_sup["partition"].isin(["test", "test_seen_spatial"])], is_train=False)

    # 1. Baselines (mask order: [tcn, sad, yolo_infra, yolo_fire, s2, geo])
    baseline_configs: Dict[str, Optional[List[float]]] = {
        "1. FIRMS Geospatial Only": [0, 0, 0, 0, 0, 1],
        "2. TCN + FIRMS": [1, 0, 0, 0, 0, 1],
        "3. FIRMS + TCN + Deep SAD": [1, 1, 0, 0, 0, 1],
        "4. FIRMS + TCN + YOLO": [1, 0, 1, 1, 0, 1],
        "5. FIRMS + TCN + Sentinel-2": [1, 0, 0, 0, 1, 1],
        "6. Full Multimodal Fusion": None,  # use actual observed mask
    }

    baseline_results: Dict[str, Any] = {}
    print("\n" + "=" * 60)
    print("PHASE F: BASELINE EVALUATIONS (Validation Split)")
    print("=" * 60)
    for name, mask in baseline_configs.items():
        res_val = evaluate_dataset(model, val_ds, override_mask=mask)
        res_test = evaluate_dataset(model, test_ds, override_mask=mask)
        baseline_results[name] = {"val": res_val, "test": res_test}
        print(f"  {name:30s} | Val Macro F1: {res_val['macro_f1']} | Val Bal Acc: {res_val['balanced_accuracy']} | Test Acc: {res_test['overall_accuracy']}")

    # 2. Ablations (mask order: [tcn, sad, yolo_infra, yolo_fire, s2, geo])
    ablation_configs: Dict[str, Optional[List[float]]] = {
        "Geometry / Thermal Only": [0, 0, 0, 0, 0, 1],
        "Temporal Only": [1, 0, 0, 0, 0, 0],
        "Anomaly Only": [0, 1, 0, 0, 0, 0],
        "Optical Only (S2)": [0, 0, 0, 0, 1, 0],
        "Infrastructure Visual Only": [0, 0, 1, 0, 0, 0],
        "Fire / Smoke Visual Only": [0, 0, 0, 1, 0, 0],
        "Temporal + Geospatial": [1, 0, 0, 0, 0, 1],
        "Geospatial + Sentinel-2": [0, 0, 0, 0, 1, 1],
        "Full Fusion": None,
    }

    ablation_results: Dict[str, Any] = {}
    print("\n" + "=" * 60)
    print("PHASE G: ABLATION STUDY (Validation Split)")
    print("=" * 60)
    for name, mask in ablation_configs.items():
        res_val = evaluate_dataset(model, val_ds, override_mask=mask)
        res_test = evaluate_dataset(model, test_ds, override_mask=mask)
        ablation_results[name] = {"val": res_val, "test": res_test}
        print(f"  {name:30s} | Val Macro F1: {res_val['macro_f1']} | Val Bal Acc: {res_val['balanced_accuracy']} | Test Acc: {res_test['overall_accuracy']}")

    return baseline_results, ablation_results


def compute_modality_importance(
    model: MultimodalLateFusionMLP,
    dataset: MultimodalFusionDataset,
) -> Dict[str, float]:
    """
    Computes Leave-One-Modality-Out (LOMO) importance based on validation Macro F1 delta.
    """
    baseline_res = evaluate_dataset(model, dataset)
    base_macro_f1 = baseline_res["macro_f1"]

    importance: Dict[str, float] = {}
    # Modality order: tcn, sad, yolo_infra, yolo_fire, s2, geo
    for idx, name in enumerate(MODALITY_NAMES):
        mask_override = [1.0 if i != idx else 0.0 for i in range(6)]
        res = evaluate_dataset(model, dataset, override_mask=mask_override)
        drop = base_macro_f1 - res["macro_f1"]
        importance[name] = round(float(drop), 4)

    return importance


def generate_prediction_record(
    model: MultimodalLateFusionMLP,
    sample_row: pd.Series,
) -> Dict[str, Any]:
    """
    Generates a full attribution prediction record with honest explanation.
    """
    model.eval()
    tcn_cols = [f"z_tcn_{i}" for i in range(MODALITY_DIMS["tcn"])]
    sad_cols = [f"z_sad_{i}" for i in range(MODALITY_DIMS["sad"])]
    infra_cols = [f"z_infra_{i}" for i in range(MODALITY_DIMS["yolo_infra"])]
    fire_cols = [f"z_fire_smoke_{i}" for i in range(MODALITY_DIMS["yolo_fire"])]
    s2_cols = [f"z_s2_{i}" for i in range(MODALITY_DIMS["s2"])]
    geo_cols = CAUSAL_GEO_FEATURES
    mask_cols = [f"mask_{name}" for name in MODALITY_NAMES]

    x_tcn = torch.tensor(sample_row[tcn_cols].values.astype(np.float32), dtype=torch.float32).unsqueeze(0)
    x_sad = torch.tensor(sample_row[sad_cols].values.astype(np.float32), dtype=torch.float32).unsqueeze(0)
    x_infra = torch.tensor(sample_row[infra_cols].values.astype(np.float32), dtype=torch.float32).unsqueeze(0)
    x_fire = torch.tensor(sample_row[fire_cols].values.astype(np.float32), dtype=torch.float32).unsqueeze(0)
    x_s2 = torch.tensor(sample_row[s2_cols].values.astype(np.float32), dtype=torch.float32).unsqueeze(0)
    x_geo = torch.tensor(sample_row[geo_cols].values.astype(np.float32), dtype=torch.float32).unsqueeze(0)
    mask = torch.tensor(sample_row[mask_cols].values.astype(np.float32), dtype=torch.float32).unsqueeze(0)

    with torch.no_grad():
        logits = model(x_tcn, x_sad, x_infra, x_fire, x_s2, x_geo, mask)
        probs = F.softmax(logits, dim=-1).squeeze(0).numpy()
        pred_id = int(np.argmax(probs))
        pred_class = ID_TO_CLASS_NAME[pred_id]
        conf = float(probs[pred_id])

    # Modality presence
    mod_avail = {name: bool(sample_row[f"has_{name}"]) for name in MODALITY_NAMES}

    # Persistence indicators
    hist_24h = int(sample_row.get("hist_count_24h_2km", 0))
    time_since_last = float(sample_row.get("time_since_last_det_2km", 999.0))
    day_ratio = float(sample_row.get("day_ratio_24h_2km", 0.0))
    is_persistent = (hist_24h >= 4 and day_ratio > 0.3)
    persistence_score = min(1.0, hist_24h / 10.0)
    acute_likelihood = max(0.0, 1.0 - persistence_score)

    # Explanation construction based on actual inputs
    evidence_bullets = []
    if mod_avail["tcn"]:
        evidence_bullets.append("Causal TCN 64D temporal cooling kinetics sequence active")
    if mod_avail["sad"]:
        evidence_bullets.append(f"Deep SAD anomaly latent projection active (dim=32)")
    if mod_avail["geo"]:
        evidence_bullets.append(f"FIRMS physical observations (FRP={sample_row.get('frp', 0.0):.1f} MW, BT4={sample_row.get('bright_ti4', 0.0):.1f} K)")
    if mod_avail["s2"]:
        evidence_bullets.append("Sentinel-2 multi-spectral 128D visual embedding co-registered")
    if is_persistent:
        evidence_bullets.append(f"High historical detection density ({hist_24h} hits in prior 24h within 2 km) indicating stationary thermal emitter")
    else:
        evidence_bullets.append("Low historical cluster recurrence indicating acute episodic combustion")

    explanation_text = f"Attributed Class: '{pred_class}' (Confidence: {conf*100:.1f}%)\nSupported by:\n- " + "\n- ".join(evidence_bullets)

    return {
        "observation_id": sample_row["detection_id"],
        "predicted_class": pred_class,
        "predicted_class_id": pred_id,
        "confidence": round(conf, 4),
        "class_probabilities": {ID_TO_CLASS_NAME[i]: round(float(probs[i]), 4) for i in range(4)},
        "modality_availability": mod_avail,
        "persistence_score": round(persistence_score, 4),
        "acute_likelihood": round(acute_likelihood, 4),
        "explanation": explanation_text,
    }
