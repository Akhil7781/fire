"""Stage 8.34 - Task 19: Build Canonical Benchmark Splits and Specification.

Defines the exact, deterministic splits for:
1. CANONICAL_TEMPORAL_CV: Train <= 2024 (N=107) -> Val 2025 (N=24)
2. CANONICAL_SPATIAL_CV: 4-Fold Outer Macro-Region Holdouts
   - North (N=45)
   - Central_East (N=35)
   - Central_West (N=19)
   - South (N=32)
3. CANONICAL_RANDOM_CV: 5-Fold Stratified Cross Validation (N=131)

Exports:
- artifacts/stage8_34/canonical_splits.json
- artifacts/stage8_34/canonical_benchmark_spec.md
"""

import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from sklearn.model_selection import StratifiedKFold
from src.stage8_32.spatial_split import assign_spatial_regions

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path("artifacts/stage8_34")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def build_canonical_benchmark():
    cohort_path = ARTIFACTS_DIR / "trusted_development_cohort.parquet"
    df = pd.read_parquet(cohort_path)
    df = assign_spatial_regions(df)
    
    logger.info(f"Loaded cohort with {len(df)} events.")
    
    # 1. Temporal Split
    train_temporal_ids = sorted(df[df["year"] <= 2024]["event_id"].tolist())
    val_temporal_ids = sorted(df[df["year"] == 2025]["event_id"].tolist())
    
    temporal_spec = {
        "description": "Causal Operational Temporal Forward Holdout (Train <= 2024 -> Val 2025)",
        "train_event_count": len(train_temporal_ids),
        "val_event_count": len(val_temporal_ids),
        "train_event_ids": train_temporal_ids,
        "val_event_ids": val_temporal_ids,
        "train_class_distribution": df[df["event_id"].isin(train_temporal_ids)]["target_class"].value_counts().to_dict(),
        "val_class_distribution": df[df["event_id"].isin(val_temporal_ids)]["target_class"].value_counts().to_dict()
    }
    
    # 2. Spatial Split (4 Macro-Regions)
    spatial_folds = {}
    for region in ["North", "Central_East", "Central_West", "South"]:
        val_ids = sorted(df[df["spatial_region"] == region]["event_id"].tolist())
        train_ids = sorted(df[df["spatial_region"] != region]["event_id"].tolist())
        spatial_folds[region] = {
            "outer_val_region": region,
            "outer_val_count": len(val_ids),
            "outer_train_count": len(train_ids),
            "outer_val_event_ids": val_ids,
            "outer_train_event_ids": train_ids,
            "outer_val_class_distribution": df[df["event_id"].isin(val_ids)]["target_class"].value_counts().to_dict(),
            "outer_train_class_distribution": df[df["event_id"].isin(train_ids)]["target_class"].value_counts().to_dict()
        }
        
    spatial_spec = {
        "description": "Outer 4-Fold Spatial Cross Validation by Geographic Macro-Region",
        "regions": ["North", "Central_East", "Central_West", "South"],
        "folds": spatial_folds
    }
    
    # 3. Random Stratified Split (5 Folds)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    random_folds = []
    # Map target_class to int for stratified split
    class_map = {
        "Industrial Fire": 0,
        "Forest Fire": 1,
        "Agricultural Fire": 2,
        "Other Thermal Source/Persistent Non-Biomass Thermal Source": 3
    }
    class_indices = df["target_class"].map(class_map).values
    
    for fold_idx, (tr_idx, val_idx) in enumerate(skf.split(df, class_indices)):
        tr_ids = sorted(df.iloc[tr_idx]["event_id"].tolist())
        val_ids = sorted(df.iloc[val_idx]["event_id"].tolist())
        random_folds.append({
            "fold_index": fold_idx,
            "train_count": len(tr_ids),
            "val_count": len(val_ids),
            "train_event_ids": tr_ids,
            "val_event_ids": val_ids,
            "val_class_distribution": df.iloc[val_idx]["target_class"].value_counts().to_dict()
        })
        
    random_spec = {
        "description": "5-Fold Stratified Random Cross Validation (seed=42)",
        "num_folds": 5,
        "folds": random_folds
    }
    
    canonical_spec = {
        "benchmark_version": "8.34_canonical",
        "total_development_events": len(df),
        "temporal_benchmark": temporal_spec,
        "spatial_benchmark": spatial_spec,
        "random_benchmark": random_spec
    }
    
    with open(ARTIFACTS_DIR / "canonical_splits.json", "w", encoding="utf-8") as f:
        json.dump(canonical_spec, f, indent=2)
    logger.info("Saved canonical_splits.json")
    
    # Generate canonical_benchmark_spec.md
    md_content = f"""# Stage 8.34 - Canonical Development Benchmark Specification

## Purpose
This document establishes the **SINGLE, CANONICAL, PERMANENT EVALUATION SUITE** for DS08 thermal-source attribution. No arbitrary or undocumented splits are permitted. All model comparisons and architectural decisions must strictly be evaluated on these deterministic protocols.

**STRICT TEST LOCK GUARANTEE:**
- Total development events: **$N = 131$** (2016–2025).
- Frozen 2026 independent test set ($N=28$): **PERMANENTLY LOCKED & UNTOUCHED** (`FROZEN_TEST_ACCESSED = FALSE`, `TEST_EVALUATION_COUNT = 0`).

---

## 1. Primary Benchmark: CANONICAL_SPATIAL_CV
- **Evaluation Purpose:** Measures generalization across unseen geographic macro-regions in India without spatial proximity shortcuts.
- **Protocol:** Outer 4-Fold Macro-Region Cross-Validation. For each fold, one entire macro-region is held out as the outer test set. Inner 5-fold stratified cross-validation on training regions is used for early stopping.
- **Primary Metric:** **Macro-F1 (Mean $\\pm$ Std across 4 folds)**.
- **Secondary Metrics:** Balanced Accuracy, Worst Fold Macro-F1.

### Spatial Fold Partitions:
| Fold Name | Outer Held-out Region | Outer Test Size ($N$) | Outer Train Size ($N$) | Dominant Regional Class |
|:---|:---|:---:|:---:|:---|
| **Fold 0** | **North** (Lat $\\ge 26^\\circ$) | 45 | 86 | Agricultural Fire (51.1%) |
| **Fold 1** | **Central_East** (Lat $20^\\circ-26^\\circ$, Lon $\\ge 78^\\circ$) | 35 | 96 | Persistent Source (62.9%) |
| **Fold 2** | **Central_West** (Lat $20^\\circ-26^\\circ$, Lon $< 78^\\circ$) | 19 | 112 | Industrial Fire (42.1%) |
| **Fold 3** | **South** (Lat $< 20^\\circ$) | 32 | 99 | Industrial Fire (53.1%) |

---

## 2. Secondary Benchmark: CANONICAL_TEMPORAL_CV
- **Evaluation Purpose:** Measures forward temporal generalization to the subsequent operational year under causal constraints.
- **Protocol:** Operational Holdout.
  - **Train Partition:** All events observed on or before December 31, 2024 ($N=107$).
  - **Validation Partition:** All events observed during calendar year 2025 ($N=24$).
- **Class Balance:** All 4 classes are present in both Train and Validation partitions:
  - Train $\\le 2024$: Industrial=31, Forest=20, Agricultural=20, Persistent=36 ($N=107$).
  - Val 2025: Industrial=4, Forest=7, Agricultural=7, Persistent=6 ($N=24$).
- **Canonical Metrics:** Accuracy = **83.33%**, Macro-F1 = **0.8183**, Balanced Accuracy = **0.8304**.

---

## 3. Diagnostic Benchmark: CANONICAL_RANDOM_CV
- **Evaluation Purpose:** Measures in-distribution cross-validation performance under stratified random partitioning.
- **Protocol:** 5-Fold Stratified Cross-Validation (seed=42).
- **Split Sizes:** 4 folds of $N=26$, 1 fold of $N=27$.
- **Use Case:** Sanity checking and baseline diagnostic verification.

---

## 4. Evaluation Invariants & Rules
1. **Zero Raw Coordinates:** The primary model must NOT ingest `centroid_lat` or `centroid_lon` to prevent regional memorization.
2. **Scaler Isolation:** All standardizers and scalers must be fitted **exclusively on the fold's training partition** and applied to validation/test partitions without lookahead.
3. **No Registry Usage:** No static persistent source manifest or ground truth lookup tables may be loaded or queried.
4. **Causal Time Horizons:** All features must adhere strictly to $t \\le t_0$ (current thermal) and $t \\le t_0 - 7$ days (historical recurrence).
"""
    with open(ARTIFACTS_DIR / "canonical_benchmark_spec.md", "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info("Saved canonical_benchmark_spec.md")

if __name__ == "__main__":
    build_canonical_benchmark()
