"""
Stage 8.33 Task 2: Nested Spatial Validation Module.
Evaluates candidate deep learning architectures across deterministic spatial holdouts:
- North (N=45)
- Central_East (N=35)
- Central_West (N=19)
- South (N=32)
Zero leakage between train and test spatial folds.
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
from src.stage8_32.spatial_split import assign_spatial_regions
from src.stage8_33.train_eval import evaluate_model, train_model, CLASS_NAMES

REGIONS = ["North", "Central_East", "Central_West", "South"]

def run_nested_spatial_cv_for_model(
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
    Runs 4-fold Outer Spatial Cross Validation.
    For each fold:
      - Outer Test: held-out region
      - Outer Train: remaining 3 regions
      - Inner Val: 1 of the 3 training regions held out for inner early-stopping
    """
    torch.manual_seed(seed)
    np.random.seed(seed)

    dev_df = assign_spatial_regions(dev_df)
    group_dims = {g: len(cols) for g, cols in feature_groups.items()}

    fold_results = []
    all_val_targets = []
    all_val_preds = []
    all_val_probs = []

    for fold_idx, holdout_region in enumerate(REGIONS):
        outer_val_df = dev_df[dev_df["spatial_region"] == holdout_region].copy().reset_index(drop=True)
        outer_train_df = dev_df[dev_df["spatial_region"] != holdout_region].copy().reset_index(drop=True)

        # Inner split: 5/6 inner train, 1/6 inner val stratified by class_id to preserve class diversity
        from sklearn.model_selection import StratifiedKFold
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        itr, ival = next(skf.split(outer_train_df, outer_train_df["class_id"]))
        inner_train_df = outer_train_df.iloc[itr].reset_index(drop=True)
        inner_val_df = outer_train_df.iloc[ival].reset_index(drop=True)

        # Build datasets
        train_ds = MultiModalThermalDataset(
            inner_train_df, feature_groups=feature_groups, scalers=None, seq_dict=seq_dict
        )
        scalers = train_ds.get_scalers()
        
        inner_val_ds = MultiModalThermalDataset(
            inner_val_df, feature_groups=feature_groups, scalers=scalers, seq_dict=seq_dict
        )
        outer_val_ds = MultiModalThermalDataset(
            outer_val_df, feature_groups=feature_groups, scalers=scalers, seq_dict=seq_dict
        )

        # Instantiate model
        model = model_factory(group_dims)

        # Train model with inner validation
        trained_model, tr_loss, val_loss = train_model(
            model=model,
            train_dataset=train_ds,
            val_dataset=inner_val_ds,
            epochs=epochs,
            lr=0.002,
            loss_type=loss_type,
            gamma=gamma,
            batch_size=16
        )

        # Evaluate on outer held-out region
        res = evaluate_model(trained_model, outer_val_ds)
        res["holdout_region"] = holdout_region
        res["val_size"] = len(outer_val_df)
        res["train_size"] = len(outer_train_df)
        fold_results.append(res)

        all_val_targets.extend(res["targets"])
        all_val_preds.extend(res["predictions"])
        all_val_probs.append(res["probabilities"])

    # Aggregate nationwide out-of-fold metrics across all 131 events
    y_true_all = np.array(all_val_targets)
    y_pred_all = np.array(all_val_preds)
    
    overall_acc = float(np.mean(y_true_all == y_pred_all))
    from sklearn.metrics import f1_score, balanced_accuracy_score, precision_recall_fscore_support
    overall_macro_f1 = float(f1_score(y_true_all, y_pred_all, average="macro", zero_division=0))
    overall_bal_acc = float(balanced_accuracy_score(y_true_all, y_pred_all))
    
    prec_all, rec_all, f1_all, supp_all = precision_recall_fscore_support(
        y_true_all, y_pred_all, labels=[0, 1, 2, 3], zero_division=0
    )

    accs = [f["accuracy"] for f in fold_results]
    macro_f1s = [f["macro_f1"] for f in fold_results]
    bal_accs = [f["balanced_accuracy"] for f in fold_results]

    worst_fold_idx = int(np.argmin(macro_f1s))
    worst_fold = REGIONS[worst_fold_idx]
    worst_fold_macro_f1 = float(macro_f1s[worst_fold_idx])

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
        "mean_accuracy": round(float(np.mean(accs)), 4),
        "std_accuracy": round(float(np.std(accs)), 4),
        "mean_macro_f1": round(float(np.mean(macro_f1s)), 4),
        "std_macro_f1": round(float(np.std(macro_f1s)), 4),
        "overall_accuracy": round(overall_acc, 4),
        "overall_macro_f1": round(overall_macro_f1, 4),
        "overall_balanced_accuracy": round(overall_bal_acc, 4),
        "worst_fold_region": worst_fold,
        "worst_fold_macro_f1": round(worst_fold_macro_f1, 4),
        "per_class": per_class_summary,
        "folds": [
            {
                "region": f["holdout_region"],
                "val_size": f["val_size"],
                "accuracy": f["accuracy"],
                "macro_f1": f["macro_f1"],
                "balanced_accuracy": f["balanced_accuracy"]
            }
            for f in fold_results
        ]
    }
