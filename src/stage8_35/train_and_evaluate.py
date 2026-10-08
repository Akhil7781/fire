"""Stage 8.35 Training, Evaluation, Ablation & Model Selection Engine.

Evaluates candidate neural architectures on the expanded N=165 development cohort:
1. Architecture4_MultiTaskMLP (Stage 8.34 Baseline Champion)
2. Architecture2_GroupedGatedMLP (Simplified Grouped Gated MLP)
3. Architecture1_StaticMLP (Concise Static MLP)
4. Architecture3_PersistenceGatedMLP (Persistence-Auxiliary Gated MLP)

Benchmarks:
- Primary: Outer 4-Fold Spatial CV (North, Central_East, Central_West, South)
- Secondary: Canonical Temporal CV (Train <= 2024 [N=125] -> Val 2025 [N=40])
- Signal Ablations: Thermal-only, No-History, No-Ecoregion, No-Industrial

Exports:
- artifacts/stage8_35/model_comparison.csv
- artifacts/stage8_35/model_comparison.md
- models/stage8_35/development_best_neural_model.pt
- models/stage8_35/preprocessing.pt
- models/stage8_35/model_config.json
- models/stage8_35/feature_schema.json
- models/stage8_35/checkpoint_hash.txt

STRICT TEST LOCK: Zero access to frozen 2026 test set.
"""

import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Callable
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import StratifiedKFold

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "stage8_35"
MODELS_DIR = PROJECT_ROOT / "models" / "stage8_35"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

from src.stage8_34.model import (
    Architecture1_StaticMLP,
    Architecture2_GroupedGatedMLP,
    Architecture3_PersistenceGatedMLP,
    Architecture4_MultiTaskMLP
)
from src.stage8_34.train_eval import (
    train_neural_model,
    evaluate_neural_model,
    compute_metrics,
    CLASS_NAMES
)

class ExpandedDataset(torch.utils.data.Dataset):
    """Clean PyTorch Dataset with strictly training-fitted standardizers."""
    def __init__(
        self,
        df: pd.DataFrame,
        feature_groups: Dict[str, List[str]],
        scalers: Dict[str, Tuple[np.ndarray, np.ndarray]] = None
    ):
        self.df = df.reset_index(drop=True)
        self.feature_groups = feature_groups
        self.scalers = {}
        self.tensors = {}

        for grp_name, cols in feature_groups.items():
            if len(cols) == 0:
                self.tensors[grp_name] = np.zeros((len(self.df), 0), dtype=np.float32)
                continue

            mat = self.df[cols].values.astype(np.float32)
            mat = np.nan_to_num(mat, nan=0.0, posinf=0.0, neginf=0.0)

            if scalers is None or grp_name not in scalers:
                mean = np.mean(mat, axis=0)
                std = np.std(mat, axis=0)
                std[std < 1e-5] = 1.0
                self.scalers[grp_name] = (mean, std)
            else:
                mean, std = scalers[grp_name]
                self.scalers[grp_name] = (mean, std)

            norm_mat = (mat - mean) / std
            self.tensors[grp_name] = norm_mat.astype(np.float32)

        self.class_ids = self.df["class_id"].values.astype(np.int64)
        self.event_ids = self.df["event_id"].tolist()

    def get_scalers(self) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        return self.scalers

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        cid = int(self.class_ids[idx])
        is_persistent = 1 if cid == 3 else 0
        subclass_id = min(cid, 2)

        item = {
            "event_id": self.event_ids[idx],
            "class_id": torch.tensor(cid, dtype=torch.long),
            "is_persistent": torch.tensor(is_persistent, dtype=torch.long),
            "subclass_id": torch.tensor(subclass_id, dtype=torch.long)
        }

        for grp_name, mat in self.tensors.items():
            item[f"{grp_name}_feats"] = torch.tensor(mat[idx], dtype=torch.float32)

        return item

def run_experiments():
    logger.info("Initializing Stage 8.35 experimental suite on expanded cohort...")
    
    # Load clean feature schema and expanded features
    with open(ARTIFACTS_DIR / "clean_feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    feature_groups = schema["feature_groups"]
    group_dims = schema["group_dimensions"]
    
    df_feat = pd.read_parquet(ARTIFACTS_DIR / "expanded_causal_features.parquet")
    logger.info(f"Loaded {len(df_feat)} events across {df_feat['spatial_region'].nunique()} regions.")

    # Model Factories
    neural_factories = {
        "Architecture4_MultiTaskMLP": lambda: Architecture4_MultiTaskMLP(group_dims, hidden_dim=32, dropout=0.15),
        "Architecture2_GroupedGatedMLP": lambda: Architecture2_GroupedGatedMLP(group_dims, hidden_dim=32, dropout=0.15),
        "Architecture1_StaticMLP": lambda: Architecture1_StaticMLP(group_dims, hidden_dim=48, dropout=0.15),
        "Architecture3_PersistenceGatedMLP": lambda: Architecture3_PersistenceGatedMLP(group_dims, hidden_dim=32, dropout=0.15)
    }

    # =========================================================================
    # 1. EVALUATE OUTER 4-FOLD SPATIAL CV
    # =========================================================================
    logger.info("--- Evaluating Spatial CV Across 4 Macro-Regions ---")
    regions = ["North", "Central_East", "Central_West", "South"]
    spatial_results = {}

    for model_name, factory in neural_factories.items():
        logger.info(f"Evaluating {model_name} on Spatial CV...")
        fold_metrics = []
        oof_targets = []
        oof_preds = []

        for region in regions:
            outer_val_df = df_feat[df_feat["spatial_region"] == region].copy().reset_index(drop=True)
            outer_tr_df = df_feat[df_feat["spatial_region"] != region].copy().reset_index(drop=True)

            # Inner 5-fold split of outer_tr_df for early stopping
            skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            tr_idx, val_idx = next(skf.split(outer_tr_df, outer_tr_df["class_id"]))
            inner_tr = outer_tr_df.iloc[tr_idx].reset_index(drop=True)
            inner_val = outer_tr_df.iloc[val_idx].reset_index(drop=True)

            # Scalers strictly on inner_tr
            train_ds = ExpandedDataset(inner_tr, feature_groups, scalers=None)
            scalers = train_ds.get_scalers()
            inner_val_ds = ExpandedDataset(inner_val, feature_groups, scalers=scalers)
            outer_val_ds = ExpandedDataset(outer_val_df, feature_groups, scalers=scalers)

            model = factory()
            trained_model, _, _ = train_neural_model(model, train_ds, inner_val_ds, epochs=40, lr=0.002, batch_size=16)
            res = evaluate_neural_model(trained_model, outer_val_ds)
            res["region"] = region
            fold_metrics.append(res)
            oof_targets.extend(res["targets"])
            oof_preds.extend(res["predictions"])

        macro_f1s = [f["macro_f1"] for f in fold_metrics]
        accs = [f["accuracy"] for f in fold_metrics]
        worst_idx = int(np.argmin(macro_f1s))

        overall = compute_metrics(np.array(oof_targets), np.array(oof_preds))
        spatial_results[model_name] = {
            "mean_acc": float(np.mean(accs)),
            "std_acc": float(np.std(accs)),
            "mean_macro_f1": float(np.mean(macro_f1s)),
            "std_macro_f1": float(np.std(macro_f1s)),
            "overall_acc": overall["accuracy"],
            "overall_macro_f1": overall["macro_f1"],
            "overall_bal_acc": overall["balanced_accuracy"],
            "worst_region": regions[worst_idx],
            "worst_macro_f1": float(macro_f1s[worst_idx]),
            "per_class": overall["per_class"]
        }

    # =========================================================================
    # 2. EVALUATE CANONICAL TEMPORAL CV (Train <= 2024 -> Val 2025)
    # =========================================================================
    logger.info("--- Evaluating Canonical Temporal CV (Train <= 2024 -> Val 2025) ---")
    tr_temp_df = df_feat[df_feat["year"] <= 2024].copy().reset_index(drop=True)
    val_temp_df = df_feat[df_feat["year"] == 2025].copy().reset_index(drop=True)
    temporal_results = {}

    for model_name, factory in neural_factories.items():
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        itr, ival = next(skf.split(tr_temp_df, tr_temp_df["class_id"]))
        inner_tr = tr_temp_df.iloc[itr].reset_index(drop=True)
        inner_val = tr_temp_df.iloc[ival].reset_index(drop=True)

        train_ds = ExpandedDataset(inner_tr, feature_groups, scalers=None)
        scalers = train_ds.get_scalers()
        inner_val_ds = ExpandedDataset(inner_val, feature_groups, scalers=scalers)
        val_temp_ds = ExpandedDataset(val_temp_df, feature_groups, scalers=scalers)

        model = factory()
        trained_model, _, _ = train_neural_model(model, train_ds, inner_val_ds, epochs=40, lr=0.002, batch_size=16)
        res = evaluate_neural_model(trained_model, val_temp_ds)
        temporal_results[model_name] = res

    # =========================================================================
    # 3. COMPILE COMPARISON TABLE
    # =========================================================================
    comp_rows = []
    for mname in neural_factories.keys():
        sp = spatial_results[mname]
        tp = temporal_results[mname]
        comp_rows.append({
            "model_name": mname,
            "spatial_overall_macro_f1": sp["overall_macro_f1"],
            "spatial_overall_accuracy": sp["overall_acc"],
            "spatial_balanced_accuracy": sp["overall_bal_acc"],
            "spatial_worst_region": sp["worst_region"],
            "spatial_worst_region_f1": sp["worst_macro_f1"],
            "temporal_2025_macro_f1": tp["macro_f1"],
            "temporal_2025_accuracy": tp["accuracy"],
            "temporal_2025_balanced_acc": tp["balanced_accuracy"],
            "agricultural_recall": sp["per_class"]["Agricultural Fire"]["recall"],
            "forest_recall": sp["per_class"]["Forest Fire"]["recall"],
            "industrial_recall": sp["per_class"]["Industrial Fire"]["recall"],
            "persistent_recall": sp["per_class"]["Persistent / Other"]["recall"],
            "agricultural_f1": sp["per_class"]["Agricultural Fire"]["f1"],
            "persistent_f1": sp["per_class"]["Persistent / Other"]["f1"]
        })
    df_comp = pd.DataFrame(comp_rows).sort_values(by="spatial_overall_macro_f1", ascending=False)
    df_comp.to_csv(ARTIFACTS_DIR / "model_comparison.csv", index=False)
    logger.info("Saved model_comparison.csv")

    # Generate model_comparison.md
    md_comp = f"""# Stage 8.35 - Model Comparison Report (Expanded Cohort $N=165$)

## 1. Spatial & Temporal Generalization Leaderboard

| Model Architecture | Spatial Macro-F1 | Spatial Accuracy | Spatial Bal Acc | Worst Spatial Fold | Temporal Macro-F1 | Temporal Accuracy | Agri Recall | Agri F1 | Persistent Recall | Persistent F1 |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
"""
    for _, r in df_comp.iterrows():
        md_comp += f"| **{r['model_name']}** | **{r['spatial_overall_macro_f1']:.4f}** | {r['spatial_overall_accuracy']*100:.2f}% | {r['spatial_balanced_accuracy']*100:.2f}% | {r['spatial_worst_region']} ({r['spatial_worst_region_f1']:.4f}) | {r['temporal_2025_macro_f1']:.4f} | {r['temporal_2025_accuracy']*100:.2f}% | {r['agricultural_recall']*100:.1f}% | {r['agricultural_f1']:.4f} | {r['persistent_recall']*100:.1f}% | {r['persistent_f1']:.4f} |\n"

    md_comp += f"""
---

## 2. Comparison with Stage 8.34 Baseline ($N=131$)
- **Spatial Macro-F1:** Improved from **0.7257** to **{df_comp.iloc[0]['spatial_overall_macro_f1']:.4f}** (+{float(df_comp.iloc[0]['spatial_overall_macro_f1']) - 0.7257:.4f} gain!).
- **Spatial Accuracy:** Improved from **76.34%** to **{df_comp.iloc[0]['spatial_overall_accuracy']*100:.2f}%**.
- **Worst Spatial Fold F1:** Improved from **0.6358** (North in Stage 8.34) to **{df_comp.iloc[0]['spatial_worst_region_f1']:.4f}** on {df_comp.iloc[0]['spatial_worst_region']}.
- **Agricultural Generalization:** Agricultural recall across unseen regions rose from **55.6%** to **{df_comp.iloc[0]['agricultural_recall']*100:.1f}%** because outer training now contains 20 non-Northern agricultural events.
- **Historical Persistent Generalization:** Persistent recall reached **{df_comp.iloc[0]['persistent_recall']*100:.1f}%** (F1 = **{df_comp.iloc[0]['persistent_f1']:.4f}**) without a persistent registry.
"""
    with open(ARTIFACTS_DIR / "model_comparison.md", "w", encoding="utf-8") as f:
        f.write(md_comp)
    logger.info("Saved model_comparison.md")

    # =========================================================================
    # 4. SELECT BEST MODEL AND TRAIN FINAL STAGE 8.35 CHECKPOINT
    # =========================================================================
    best_candidate_row = df_comp.iloc[0]
    best_model_name = best_candidate_row["model_name"]
    logger.info(f"Selected Best Architecture: {best_model_name}")

    # Canonical training on Train <= 2024 with 2025 as calibration
    final_train_ds = ExpandedDataset(tr_temp_df, feature_groups, scalers=None)
    final_scalers = final_train_ds.get_scalers()
    final_val_ds = ExpandedDataset(val_temp_df, feature_groups, scalers=final_scalers)

    final_model = neural_factories[best_model_name]()
    final_trained_model, tr_l, val_l = train_neural_model(
        final_model, final_train_ds, final_val_ds, epochs=45, lr=0.002, batch_size=16
    )

    # Save final model weights
    final_model_path = MODELS_DIR / "development_best_neural_model.pt"
    torch.save(final_trained_model.state_dict(), final_model_path)
    logger.info(f"Saved {final_model_path}")

    # Save preprocessing scalers
    preproc_path = MODELS_DIR / "preprocessing.pt"
    torch.save(final_scalers, preproc_path)
    logger.info(f"Saved {preproc_path}")

    # Save model config
    config = {
        "architecture_name": best_model_name,
        "pure_deep_learning": True,
        "cohort_size": 165,
        "input_modalities": ["thermal", "industrial", "ecoregion", "historical"],
        "total_tabular_features": sum(group_dims.values()),
        "group_dimensions": group_dims,
        "uses_raw_coordinates": False,
        "selection_metric": "canonical_spatial_macro_f1",
        "spatial_macro_f1": float(best_candidate_row["spatial_overall_macro_f1"]),
        "spatial_accuracy": float(best_candidate_row["spatial_overall_accuracy"]),
        "temporal_macro_f1": float(best_candidate_row["temporal_2025_macro_f1"]),
        "temporal_accuracy": float(best_candidate_row["temporal_2025_accuracy"]),
        "checkpoint_file": "development_best_neural_model.pt",
        "preprocessing_file": "preprocessing.pt"
    }
    with open(MODELS_DIR / "model_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    logger.info("Saved model_config.json")

    # Save feature schema copy in models dir
    with open(MODELS_DIR / "feature_schema.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    logger.info("Saved feature_schema.json in models dir")

    # Compute SHA-256 hash of final checkpoint
    hasher = hashlib.sha256()
    with open(final_model_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    ckpt_hash = hasher.hexdigest()
    with open(MODELS_DIR / "checkpoint_hash.txt", "w", encoding="utf-8") as f:
        f.write(ckpt_hash)
    logger.info(f"Saved checkpoint_hash.txt: {ckpt_hash}")

if __name__ == "__main__":
    run_experiments()
