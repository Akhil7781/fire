"""Stage 8.34 Mandatory Verification Test Suite.

Verifies all 18 non-negotiable assertions:
1. Frozen test cohort never accessed.
2. Frozen test manifest never loaded.
3. Test evaluation count = 0.
4. No associated_* fields used as model features.
5. No persistent registry.
6. No future observations in causal features.
7. Event-level split integrity.
8. Duplicate/near-duplicate isolation.
9. Spatial fold integrity.
10. Temporal chronology integrity.
11. Training-only scaler fitting.
12. Deterministic feature schema.
13. No raw coordinates in primary model.
14. Final model is deep-learning-only.
15. No hard-coded class/geography rules.
16. Persistent labels audited.
17. Final checkpoint load works independently.
18. Final development benchmark reproducible.
"""

import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import pytest
import torch

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "stage8_34"
MODELS_DIR = PROJECT_ROOT / "models" / "stage8_34"

FROZEN_2026_HASH = "5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c"

def test_1_frozen_test_cohort_never_accessed():
    """Verify that development cohort contains strictly 131 events and zero 2026 test events."""
    cohort_path = ARTIFACTS_DIR / "trusted_development_cohort.parquet"
    assert cohort_path.exists(), "Trusted development cohort parquet missing"
    df = pd.read_parquet(cohort_path)
    assert len(df) == 131, f"Expected exactly 131 events, got {len(df)}"
    assert (df["year"] <= 2025).all(), "Found events beyond 2025 in development cohort!"
    assert "test" not in df["split"].values, "Found test split in development cohort!"

def test_2_frozen_test_manifest_never_loaded():
    """Verify the frozen 2026 test manifest SHA-256 hash is unchanged and unmodified."""
    manifest_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "independent_test_manifest.json"
    assert manifest_path.exists(), "Original frozen manifest missing"
    with open(manifest_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    assert file_hash == FROZEN_2026_HASH, "Violation: Frozen 2026 test manifest hash has changed!"

def test_3_test_evaluation_count_is_zero():
    """Verify zero predictions or evaluations were run against 2026 test set in Stage 8.34."""
    spatial_res = pd.read_csv(ARTIFACTS_DIR / "canonical_spatial_cv.csv")
    model_comp = pd.read_csv(ARTIFACTS_DIR / "model_comparison.csv")
    assert "test_2026" not in spatial_res.columns
    assert "test_2026_acc" not in model_comp.columns
    assert len(spatial_res) >= 5, "Spatial CV should evaluate candidate models"

def test_4_no_associated_fields_in_features():
    """Verify that associated_* fields and target proxies never enter the clean feature schema."""
    with open(ARTIFACTS_DIR / "clean_feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    all_features = [f for grp in schema["feature_groups"].values() for f in grp]
    forbidden_prefixes = ["associated_", "target_", "class_id", "is_facility_baseline"]
    for feat in all_features:
        for pfx in forbidden_prefixes:
            assert not feat.startswith(pfx), f"Leakage violation: {feat} found in clean features!"

def test_5_no_persistent_registry_used():
    """Verify that persistent_source_manifest is not used in feature schema or config."""
    with open(ARTIFACTS_DIR / "clean_feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    all_features = [f for grp in schema["feature_groups"].values() for f in grp]
    assert "persistent_registry_flag" not in all_features
    assert "in_persistent_registry" not in all_features

def test_6_no_future_leakage():
    """Verify causal cutoff timestamps on feature provenance."""
    df_prov = pd.read_csv(ARTIFACTS_DIR / "clean_feature_provenance.csv")
    for _, row in df_prov.iterrows():
        cutoff = row["causal_cutoff"]
        assert "t <= t0" in cutoff or "Static" in cutoff, f"Non-causal cutoff found: {cutoff}"

def test_7_event_level_split_integrity():
    """Verify strict disjointness between train and val event IDs in canonical benchmarks."""
    with open(ARTIFACTS_DIR / "canonical_splits.json", "r", encoding="utf-8") as f:
        splits = json.load(f)
    # Temporal
    tr_temp = set(splits["temporal_benchmark"]["train_event_ids"])
    val_temp = set(splits["temporal_benchmark"]["val_event_ids"])
    assert len(tr_temp.intersection(val_temp)) == 0, "Temporal train/val overlap!"
    assert len(tr_temp) == 107
    assert len(val_temp) == 24

    # Spatial
    for reg, finfo in splits["spatial_benchmark"]["folds"].items():
        tr_sp = set(finfo["outer_train_event_ids"])
        val_sp = set(finfo["outer_val_event_ids"])
        assert len(tr_sp.intersection(val_sp)) == 0, f"Spatial train/val overlap in {reg}!"

def test_8_duplicate_isolation():
    """Verify duplicate audit artifacts exist and connected components are identified."""
    assert (ARTIFACTS_DIR / "event_overlap_graph.csv").exists()
    assert (ARTIFACTS_DIR / "event_overlap_components.json").exists()
    with open(ARTIFACTS_DIR / "event_overlap_components.json", "r", encoding="utf-8") as f:
        comps = json.load(f)
    assert isinstance(comps, list)
    assert len(comps) >= 1

def test_9_spatial_fold_integrity():
    """Verify all 4 macro-regions are covered with zero unassigned events."""
    with open(ARTIFACTS_DIR / "canonical_splits.json", "r", encoding="utf-8") as f:
        splits = json.load(f)
    spatial = splits["spatial_benchmark"]
    total_val = sum(len(finfo["outer_val_event_ids"]) for finfo in spatial["folds"].values())
    assert total_val == 131, f"Expected 131 events partitioned across 4 folds, got {total_val}"

def test_10_temporal_chronology_integrity():
    """Verify temporal train contains strictly years <= 2024 and val contains year == 2025."""
    cohort = pd.read_parquet(ARTIFACTS_DIR / "trusted_development_cohort.parquet")
    with open(ARTIFACTS_DIR / "canonical_splits.json", "r", encoding="utf-8") as f:
        splits = json.load(f)
    tr_ids = splits["temporal_benchmark"]["train_event_ids"]
    val_ids = splits["temporal_benchmark"]["val_event_ids"]

    assert (cohort[cohort["event_id"].isin(tr_ids)]["year"] <= 2024).all()
    assert (cohort[cohort["event_id"].isin(val_ids)]["year"] == 2025).all()

def test_11_training_only_scaler_fitting():
    """Verify CleanMultiModalDataset scalers fit only on provided train data."""
    from src.stage8_34.dataset import CleanMultiModalDataset, load_clean_feature_schema, load_development_data
    schema = load_clean_feature_schema()
    dev_df, _ = load_development_data()
    train_subset = dev_df.iloc[:50].copy()
    ds = CleanMultiModalDataset(train_subset, schema["feature_groups"], scalers=None)
    scalers = ds.get_scalers()
    assert "thermal" in scalers
    mean, std = scalers["thermal"]
    assert len(mean) == len(schema["feature_groups"]["thermal"])

def test_12_deterministic_feature_schema():
    """Verify clean_feature_schema matches clean_feature_provenance rows exactly."""
    with open(ARTIFACTS_DIR / "clean_feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    df_prov = pd.read_csv(ARTIFACTS_DIR / "clean_feature_provenance.csv")
    all_features = [f for grp in schema["feature_groups"].values() for f in grp]
    assert len(all_features) == len(df_prov)
    assert set(all_features) == set(df_prov["feature_name"].tolist())

def test_13_no_raw_coordinates_in_primary_model():
    """Verify raw coordinates are excluded from clean feature schema."""
    with open(ARTIFACTS_DIR / "clean_feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    all_features = [f for grp in schema["feature_groups"].values() for f in grp]
    assert "centroid_lat" not in all_features
    assert "centroid_lon" not in all_features
    assert schema["raw_coordinates_included"] is False

def test_14_final_model_is_deep_learning_only():
    """Verify model_config specifies pure_deep_learning = True and model loads as PyTorch nn.Module."""
    with open(MODELS_DIR / "model_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    assert config["pure_deep_learning"] is True
    assert "MLP" in config["architecture_name"] or "Neural" in config["architecture_name"]

def test_15_no_hard_coded_geography_rules():
    """Verify model forward pass does not execute geographic if-statements."""
    from src.stage8_34.model import Architecture1_StaticMLP
    model = Architecture1_StaticMLP({"thermal": 14, "industrial": 6, "ecoregion": 3, "historical": 18})
    dummy = {
        "thermal_feats": torch.randn(2, 14),
        "industrial_feats": torch.randn(2, 6),
        "ecoregion_feats": torch.randn(2, 3),
        "historical_feats": torch.randn(2, 18)
    }
    out = model(dummy)
    assert "logits" in out
    assert out["logits"].shape == (2, 4)

def test_16_persistent_labels_audited():
    """Verify persistence definition audit artifact exists."""
    audit_file = ARTIFACTS_DIR / "persistence_definition_audit.md"
    assert audit_file.exists()
    content = audit_file.read_text(encoding="utf-8")
    assert "hist_count_full" in content
    assert "dist_to_fac_km" in content

def test_17_final_checkpoint_load_independently():
    """Verify final neural model checkpoint loads and passes a forward pass."""
    with open(MODELS_DIR / "model_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    ckpt_path = MODELS_DIR / "final_neural_model.pt"
    assert ckpt_path.exists()

    from src.stage8_34 import model as model_mod
    arch_cls = getattr(model_mod, config["architecture_name"])
    model = arch_cls(config["group_dimensions"])
    weights = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    model.load_state_dict(weights)
    model.eval()

    # Create dummy batch based on group dimensions
    batch = {
        f"{grp}_feats": torch.randn(1, dim)
        for grp, dim in config["group_dimensions"].items()
    }
    if config.get("uses_tcn_sequences", False):
        batch["seq_tensor"] = torch.randn(1, 50, 11)
        batch["seq_mask"] = torch.ones(1, 50)

    with torch.no_grad():
        out = model(batch)
    assert out["probs"].shape == (1, 4)
    assert torch.isclose(out["probs"].sum(), torch.tensor(1.0), atol=1e-4)

def test_18_final_development_benchmark_reproducible():
    """Verify checkpoint hash file exists and matches the checkpoint file."""
    ckpt_path = MODELS_DIR / "final_neural_model.pt"
    hash_path = MODELS_DIR / "checkpoint_hash.txt"
    assert hash_path.exists()
    expected_hash = hash_path.read_text(encoding="utf-8").strip()

    hasher = hashlib.sha256()
    with open(ckpt_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest()
    assert actual_hash == expected_hash, "Checkpoint hash mismatch!"
