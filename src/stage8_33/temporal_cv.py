"""
Stage 8.33 Task 3: Temporal Generalization & Chronological Validation Module.
Evaluates model across forward-chaining chronological splits where training time
strictly contains ONLY observations earlier than the validation period.
STRICT TEST LOCK: Zero access to frozen 2026 test set.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Callable
import numpy as np
import pandas as pd
import torch

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_33.dataset import (
    load_development_features,
    load_development_sequences,
    get_feature_groups,
    MultiModalThermalDataset
)
from src.stage8_33.train_eval import evaluate_model, train_model, CLASS_NAMES

def run_chronological_evaluation_for_model(
    model_factory: Callable[[Dict[str, int]], torch.nn.Module],
    model_name: str,
    dev_df: pd.DataFrame,
    seq_dict: Dict[str, np.ndarray],
    feature_groups: Dict[str, List[str]],
    epochs: int = 40,
    loss_type: str = "focal_loss",
    gamma: float = 1.5,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Evaluates model across 3 forward-chaining chronological splits:
    1. Train <= 2022 (N=47) -> Val 2023 (N=11)
    2. Train <= 2023 (N=58) -> Val 2024 (N=49)
    3. Train <= 2024 (N=107) -> Val 2025 (N=24)
    Strict temporal causality: training data is ALWAYS earlier than validation year.
    """
    torch.manual_seed(seed)
    np.random.seed(seed)

    group_dims = {g: len(cols) for g, cols in feature_groups.items()}
    temporal_splits = [
        {"name": "2022_to_2023", "train_max_year": 2022, "val_year": 2023},
        {"name": "2023_to_2024", "train_max_year": 2023, "val_year": 2024},
        {"name": "2024_to_2025", "train_max_year": 2024, "val_year": 2025}
    ]

    split_results = []
    all_val_targets = []
    all_val_preds = []

    for sp in temporal_splits:
        tr_df = dev_df[dev_df["year"] <= sp["train_max_year"]].copy().reset_index(drop=True)
        val_df = dev_df[dev_df["year"] == sp["val_year"]].copy().reset_index(drop=True)

        train_ds = MultiModalThermalDataset(
            tr_df, feature_groups=feature_groups, scalers=None, seq_dict=seq_dict
        )
        scalers = train_ds.get_scalers()
        val_ds = MultiModalThermalDataset(
            val_df, feature_groups=feature_groups, scalers=scalers, seq_dict=seq_dict
        )

        model = model_factory(group_dims)
        trained_model, _, _ = train_model(
            model=model,
            train_dataset=train_ds,
            val_dataset=None,
            epochs=epochs,
            lr=0.002,
            loss_type=loss_type,
            gamma=gamma,
            batch_size=16
        )

        res = evaluate_model(trained_model, val_ds)
        res["split_name"] = sp["name"]
        res["val_year"] = sp["val_year"]
        res["train_size"] = len(tr_df)
        res["val_size"] = len(val_df)
        split_results.append(res)

        all_val_targets.extend(res["targets"])
        all_val_preds.extend(res["predictions"])

    y_true_all = np.array(all_val_targets)
    y_pred_all = np.array(all_val_preds)

    overall_acc = float(np.mean(y_true_all == y_pred_all))
    from sklearn.metrics import f1_score, balanced_accuracy_score, precision_recall_fscore_support
    overall_macro_f1 = float(f1_score(y_true_all, y_pred_all, average="macro", zero_division=0))
    overall_bal_acc = float(balanced_accuracy_score(y_true_all, y_pred_all))

    prec_all, rec_all, f1_all, supp_all = precision_recall_fscore_support(
        y_true_all, y_pred_all, labels=[0, 1, 2, 3], zero_division=0
    )

    per_class_summary = {}
    for i, name in enumerate(CLASS_NAMES):
        per_class_summary[name] = {
            "recall": round(float(rec_all[i]), 4),
            "precision": round(float(prec_all[i]), 4),
            "f1": round(float(f1_all[i]), 4),
            "support": int(supp_all[i])
        }

    return {
        "model_name": model_name,
        "overall_temporal_accuracy": round(overall_acc, 4),
        "overall_temporal_macro_f1": round(overall_macro_f1, 4),
        "overall_temporal_balanced_accuracy": round(overall_bal_acc, 4),
        "total_evaluated_events": len(y_true_all),
        "per_class": per_class_summary,
        "temporal_splits": [
            {
                "split_name": s["split_name"],
                "val_year": s["val_year"],
                "train_size": s["train_size"],
                "val_size": s["val_size"],
                "accuracy": s["accuracy"],
                "macro_f1": s["macro_f1"],
                "balanced_accuracy": s["balanced_accuracy"]
            }
            for s in split_results
        ]
    }
