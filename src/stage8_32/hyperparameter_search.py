"""
Tasks 4, 5, 7, 8: Neural Architecture Formulation, Loss Benchmarking, and Hyperparameter Search.
Strictly evaluated on Train (2018-2024, N=107) and Validation (2025, N=24) cohorts.
Saves artifacts/stage8_32/experiments.csv.
"""

import copy
import itertools
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_30.train_and_evaluate import compute_metrics, seed_everything
from src.stage8_32.dataset import get_feature_groups, GroupedThermalDataset
from src.stage8_32.model import GroupedCausalThermalClassifier, FocalLoss
from src.stage8_32.spatial_split import load_development_events, get_splits

def run_experiment(
    exp_id: str,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    feature_groups: Dict[str, List[str]],
    hidden_dim: int,
    num_res_blocks: int,
    dropout: float,
    lr: float,
    weight_decay: float,
    loss_type: str,
    formulation: str,
    epochs: int = 40,
    seed: int = 42
) -> Dict[str, Any]:
    seed_everything(seed)

    train_ds = GroupedThermalDataset(train_df, feature_groups)
    scalers = train_ds.get_scalers()
    val_ds = GroupedThermalDataset(val_df, feature_groups, scalers=scalers)

    train_loader = DataLoader(train_ds, batch_size=16, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=32, shuffle=False)

    train_classes = train_df["class_id"].values
    class_counts = np.bincount(train_classes, minlength=4)
    class_weights = torch.tensor(len(train_classes) / (4.0 * np.maximum(class_counts, 1.0)), dtype=torch.float32)

    group_dims = {k: len(v) for k, v in feature_groups.items()}
    model = GroupedCausalThermalClassifier(
        group_dims=group_dims,
        hidden_dim=hidden_dim,
        num_res_blocks=num_res_blocks,
        dropout=dropout
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    # Primary 4-class loss
    if loss_type == "focal_loss":
        criterion_4c = FocalLoss(alpha=class_weights, gamma=1.5)
    else: # weighted_ce
        criterion_4c = nn.CrossEntropyLoss(weight=class_weights)

    criterion_bin = nn.CrossEntropyLoss()
    criterion_sub = nn.CrossEntropyLoss()

    best_val_f1 = -1.0
    best_state = None

    for ep in range(epochs):
        model.train()
        for b in train_loader:
            optimizer.zero_grad()
            out = model(b)

            l4c = criterion_4c(out["logits_4class"], b["class_id"])

            if formulation == "4_CLASS_ONLY":
                loss = l4c
            elif formulation == "4_CLASS_PLUS_PERSISTENCE":
                lbin = criterion_bin(out["logits_binary"], b["is_persistent"])
                loss = l4c + 0.3 * lbin
            else: # MULTI_TASK / HIERARCHICAL (Task A + Task B + Task C)
                lbin = criterion_bin(out["logits_binary"], b["is_persistent"])
                acute_mask = b["class_id"] < 3
                lsub = criterion_sub(out["logits_subclass"][acute_mask], b["class_id"][acute_mask]) if acute_mask.any() else 0.0
                loss = l4c + 0.3 * lbin + 0.2 * lsub

            loss.backward()
            optimizer.step()

        # Check validation
        model.eval()
        v_preds, v_targets = [], []
        with torch.no_grad():
            for b in val_loader:
                inf_mode = "direct_4class" if formulation == "4_CLASS_ONLY" else "hierarchical" if formulation == "HIERARCHICAL" else "multi_task_blend"
                probs = model.predict_probabilities(b, mode=inf_mode)
                pr = torch.argmax(probs, dim=-1).cpu().numpy()
                v_preds.extend(pr)
                v_targets.extend(b["class_id"].cpu().numpy())

        vm = compute_metrics(np.array(v_targets), np.array(v_preds))
        if vm["macro_f1"] > best_val_f1:
            best_val_f1 = vm["macro_f1"]
            best_state = copy.deepcopy(model.state_dict())

    if best_state is not None:
        model.load_state_dict(best_state)

    # Final evaluation on validation
    model.eval()
    all_preds, all_targets = [], []
    with torch.no_grad():
        for b in val_loader:
            inf_mode = "direct_4class" if formulation == "4_CLASS_ONLY" else "hierarchical" if formulation == "HIERARCHICAL" else "multi_task_blend"
            probs = model.predict_probabilities(b, mode=inf_mode)
            pr = torch.argmax(probs, dim=-1).cpu().numpy()
            all_preds.extend(pr)
            all_targets.extend(b["class_id"].cpu().numpy())

    metrics = compute_metrics(np.array(all_targets), np.array(all_preds))

    return {
        "exp_id": exp_id,
        "formulation": formulation,
        "loss_type": loss_type,
        "hidden_dim": hidden_dim,
        "num_res_blocks": num_res_blocks,
        "dropout": dropout,
        "lr": lr,
        "weight_decay": weight_decay,
        "val_accuracy": round(metrics["accuracy"], 4),
        "val_macro_f1": round(metrics["macro_f1"], 4),
        "val_balanced_acc": round(metrics["balanced_acc"], 4),
        "val_ind_f1": round(metrics["f1_ind"], 4),
        "val_for_f1": round(metrics["f1_for"], 4),
        "val_agr_f1": round(metrics["f1_agr"], 4),
        "val_per_f1": round(metrics["f1_per"], 4)
    }

def run_hyperparameter_search():
    print("=" * 80)
    print("TASKS 4, 5, 7, 8: ARCHITECTURE FORMULATION & HYPERPARAMETER SEARCH")
    print("Strictly on Train (N=107) and Validation (N=24). Zero test set access.")
    print("=" * 80)

    dev_df = load_development_events()
    splits = get_splits(dev_df, seed=42)
    tr_df, va_df = splits["temporal"]
    feature_groups = get_feature_groups(dev_df.columns.tolist())

    experiments = []
    exp_counter = 1

    # 1. Compare Formulations (Task 4 & 5): 4_CLASS_ONLY vs 4_CLASS_PLUS_PERSISTENCE vs HIERARCHICAL vs MULTI_TASK
    formulations = ["4_CLASS_ONLY", "4_CLASS_PLUS_PERSISTENCE", "HIERARCHICAL", "MULTI_TASK"]
    for form in formulations:
        rec = run_experiment(
            exp_id=f"EXP_{exp_counter:02d}",
            train_df=tr_df,
            val_df=va_df,
            feature_groups=feature_groups,
            hidden_dim=64,
            num_res_blocks=2,
            dropout=0.15,
            lr=1e-3,
            weight_decay=1e-4,
            loss_type="weighted_ce",
            formulation=form
        )
        experiments.append(rec)
        print(f"[{rec['exp_id']}] Form={form:<26} | Val Acc={rec['val_accuracy']:.4f} | Macro-F1={rec['val_macro_f1']:.4f} | Agr F1={rec['val_agr_f1']:.4f}")
        exp_counter += 1

    # 2. Compare Loss Functions (Task 7): weighted_ce vs focal_loss
    losses = ["weighted_ce", "focal_loss"]
    for l_type in losses:
        if l_type == "weighted_ce":
            continue # Already in exp 4
        rec = run_experiment(
            exp_id=f"EXP_{exp_counter:02d}",
            train_df=tr_df,
            val_df=va_df,
            feature_groups=feature_groups,
            hidden_dim=64,
            num_res_blocks=2,
            dropout=0.15,
            lr=1e-3,
            weight_decay=1e-4,
            loss_type=l_type,
            formulation="MULTI_TASK"
        )
        experiments.append(rec)
        print(f"[{rec['exp_id']}] Loss={l_type:<26} | Val Acc={rec['val_accuracy']:.4f} | Macro-F1={rec['val_macro_f1']:.4f} | Agr F1={rec['val_agr_f1']:.4f}")
        exp_counter += 1

    # 3. Compact Search over Capacity & Regularization (Task 8)
    search_space = [
        {"hidden_dim": 48, "num_res_blocks": 1, "dropout": 0.1, "lr": 1e-3, "loss": "focal_loss"},
        {"hidden_dim": 64, "num_res_blocks": 1, "dropout": 0.15, "lr": 1e-3, "loss": "focal_loss"},
        {"hidden_dim": 64, "num_res_blocks": 2, "dropout": 0.2, "lr": 1e-3, "loss": "focal_loss"},
        {"hidden_dim": 96, "num_res_blocks": 2, "dropout": 0.2, "lr": 5e-4, "loss": "focal_loss"},
        {"hidden_dim": 64, "num_res_blocks": 2, "dropout": 0.15, "lr": 5e-4, "loss": "focal_loss"},
        {"hidden_dim": 64, "num_res_blocks": 2, "dropout": 0.15, "lr": 2e-3, "loss": "focal_loss"}
    ]

    for p in search_space:
        rec = run_experiment(
            exp_id=f"EXP_{exp_counter:02d}",
            train_df=tr_df,
            val_df=va_df,
            feature_groups=feature_groups,
            hidden_dim=p["hidden_dim"],
            num_res_blocks=p["num_res_blocks"],
            dropout=p["dropout"],
            lr=p["lr"],
            weight_decay=1e-4,
            loss_type=p["loss"],
            formulation="MULTI_TASK"
        )
        experiments.append(rec)
        print(f"[{rec['exp_id']}] Dim={p['hidden_dim']} Blocks={p['num_res_blocks']} Drp={p['dropout']} LR={p['lr']} | Val Acc={rec['val_accuracy']:.4f} | Macro-F1={rec['val_macro_f1']:.4f} | Agr F1={rec['val_agr_f1']:.4f}")
        exp_counter += 1

    df_exp = pd.DataFrame(experiments)
    out_dir = PROJECT_ROOT / "artifacts" / "stage8_32"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "experiments.csv"
    df_exp.to_csv(csv_path, index=False)
    print(f"\nSaved {csv_path} ({len(df_exp)} experiments)")

    # Select Best Config
    best_row = df_exp.sort_values(by=["val_macro_f1", "val_accuracy"], ascending=False).iloc[0]
    print(f"\nTOP SELECTED NEURAL CONFIGURATION:")
    print(best_row.to_dict())

if __name__ == "__main__":
    run_hyperparameter_search()
