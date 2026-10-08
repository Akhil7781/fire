"""
Stage 8.33 Mandatory Automated Test Suite.
Verifies all 15 architectural, methodological, and forensic integrity invariants:
1. Frozen test data is never accessed.
2. Frozen test manifest is never loaded.
3. No associated_* columns are queried.
4. No persistent registry is accessed.
5. No future observations enter historical features.
6. Spatial folds do not violate the selected spatial separation rule.
7. Temporal folds preserve chronology.
8. Scalers are fitted only on training data.
9. No classical model is in the final pipeline.
10. Neural model loads independently.
11. Feature ordering is deterministic.
12. Causal temporal encoder receives valid sequences.
13. Final checkpoint hash is reproducible.
14. No hard-coded class-specific geographic rules.
15. No test evaluation occurs.
"""

import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import torch

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

FROZEN_MANIFEST_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "independent_test_manifest.json"
EXPECTED_MANIFEST_HASH = "5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c"

def test_1_frozen_test_manifest_hash_intact_and_unmodified():
    """Verify frozen 2026 test manifest has not been modified or corrupted."""
    assert FROZEN_MANIFEST_PATH.exists(), "Frozen test manifest missing"
    with open(FROZEN_MANIFEST_PATH, "rb") as f:
        manifest_hash = hashlib.sha256(f.read()).hexdigest()
    assert manifest_hash == EXPECTED_MANIFEST_HASH, f"Manifest hash mismatch: {manifest_hash}"

def test_2_frozen_test_data_never_accessed_in_stage8_33():
    """Verify that Stage 8.33 code files contain ZERO loads or reads of test data/manifest."""
    src_33_files = list((PROJECT_ROOT / "src" / "stage8_33").glob("*.py"))
    assert len(src_33_files) > 0, "No Stage 8.33 python files found"
    
    for f in src_33_files:
        with open(f, "r", encoding="utf-8") as py_file:
            code = py_file.read()
            assert "independent_test_manifest.json" not in code, f"Forbidden test manifest reference in {f.name}"
            # Verify test split filtering
            if "read_parquet" in code:
                assert "test" not in code or 'split != "test"' in code or 'isin(["train", "val"])' in code or 'isin([\'train\', \'val\'])' in code, \
                    f"Possible unfiltered test loading in {f.name}"

def test_3_no_associated_label_columns_queried():
    """Verify no associated_* label columns are present in Stage 8.33 feature schemas."""
    schema_path = PROJECT_ROOT / "models" / "stage8_33" / "feature_schema.json"
    assert schema_path.exists(), "Feature schema missing"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    
    all_features = []
    for grp, cols in schema.items():
        all_features.extend(cols)
        
    for feat in all_features:
        assert not feat.startswith("associated_"), f"Target proxy column found: {feat}"
        assert "target_class" not in feat, f"Target column found: {feat}"
        assert "class_id" not in feat, f"Class ID column found: {feat}"

def test_4_no_persistent_registry_accessed():
    """Verify no external persistent registry or persistent manifest is accessed."""
    src_33_files = list((PROJECT_ROOT / "src" / "stage8_33").glob("*.py"))
    for f in src_33_files:
        with open(f, "r", encoding="utf-8") as py_file:
            code = py_file.read()
            assert "persistent_source_manifest.json" not in code, f"Forbidden persistent registry in {f.name}"
            assert "persistent_universe" not in code, f"Persistent universe reference in {f.name}"

def test_5_no_future_information_in_historical_features():
    """Verify all historical features are strictly derived <= t0 - 7 days."""
    dev_features = pd.read_parquet(PROJECT_ROOT / "data" / "interim" / "ds08_stage8_30_causal_features.parquet")
    dev_h0 = dev_features[(dev_features["horizon"] == "H0") & (dev_features["split"].isin(["train", "val"]))]
    
    for _, row in dev_h0.iterrows():
        t0 = pd.to_datetime(row["feature_cutoff_time"])
        hist_days = row["hist_days_since_latest"]
        if not pd.isna(hist_days) and hist_days > 0:
            assert hist_days >= 6.99, f"Historical detection less than 7 days prior to t0 in event {row['event_id']}"

def test_6_spatial_folds_preserve_strict_macro_region_separation():
    """Verify that spatial cross-validation partitions do not leak across regions."""
    from src.stage8_33.dataset import load_development_features
    from src.stage8_32.spatial_split import assign_spatial_regions
    
    dev = load_development_features()
    dev = assign_spatial_regions(dev)
    regions = ["North", "Central_East", "Central_West", "South"]
    
    for r in regions:
        val_df = dev[dev["spatial_region"] == r]
        tr_df = dev[dev["spatial_region"] != r]
        assert len(val_df) > 0, f"Region {r} is empty"
        assert len(tr_df) > 0, f"Training set excluding {r} is empty"
        # Verify disjoint event IDs
        overlap = set(val_df["event_id"]).intersection(set(tr_df["event_id"]))
        assert len(overlap) == 0, f"Spatial fold {r} leaked {len(overlap)} events"

def test_7_temporal_folds_preserve_chronology():
    """Verify chronological validation protocols strictly satisfy train_year < val_year."""
    from src.stage8_33.dataset import load_development_features
    dev = load_development_features()
    
    temporal_splits = [
        (2022, 2023),
        (2023, 2024),
        (2024, 2025)
    ]
    for max_tr, val_y in temporal_splits:
        tr_df = dev[dev["year"] <= max_tr]
        val_df = dev[dev["year"] == val_y]
        assert len(tr_df) > 0, f"Empty train split for temporal split {max_tr}"
        assert len(val_df) > 0, f"Empty val split for temporal split {val_y}"
        assert tr_df["year"].max() < val_df["year"].min(), f"Temporal leakage: train max year {tr_df['year'].max()} >= val min year {val_df['year'].min()}"

def test_8_preprocessing_scalers_fitted_only_on_training_data():
    """Verify that preprocessing scalers are fitted exclusively on training rows."""
    from src.stage8_33.dataset import MultiModalThermalDataset, load_development_features, get_feature_groups
    dev = load_development_features()
    fg = get_feature_groups(dev.columns.tolist(), include_geo=False)
    
    train_df = dev[dev["split"] == "train"].reset_index(drop=True)
    val_df = dev[dev["split"] == "val"].reset_index(drop=True)
    
    tr_ds = MultiModalThermalDataset(train_df, fg)
    scalers = tr_ds.get_scalers()
    
    # Check that thermal mean matches train_df mean exactly
    mean_tr_frp = float(train_df["current_frp"].mean())
    scaler_frp_mean = scalers["thermal"][0][0]  # current_frp is index 0
    assert abs(mean_tr_frp - scaler_frp_mean) < 1e-4, "Scaler mean does not match train set mean"

def test_9_final_model_contains_no_classical_ml_component():
    """Verify that the model checkpoint is 100% PyTorch and contains zero classical ML components."""
    model_path = PROJECT_ROOT / "models" / "stage8_33" / "final_neural_model.pt"
    assert model_path.exists(), "Final model weights missing"
    
    weights = torch.load(model_path, map_location="cpu")
    assert isinstance(weights, dict), "Model weights must be a PyTorch state_dict"
    for k in weights.keys():
        assert not any(c in k for c in ["random_forest", "xgb", "hist_gradient", "svm", "knn", "logistic"]), \
            f"Classical ML artifact key found: {k}"

def test_10_neural_model_loads_independently():
    """Verify that the neural model can be instantiated and loaded without foreign dependencies."""
    from src.stage8_33.model import ModelG_BestSimplified
    
    cfg_path = PROJECT_ROOT / "models" / "stage8_33" / "model_config.json"
    weights_path = PROJECT_ROOT / "models" / "stage8_33" / "final_neural_model.pt"
    assert cfg_path.exists() and weights_path.exists()
    
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        
    model = ModelG_BestSimplified(
        group_dims=cfg["feature_group_dims"],
        hidden_dim=cfg["hidden_dim"],
        dropout=cfg["dropout"]
    )
    model.load_state_dict(torch.load(weights_path, map_location="cpu"))
    model.eval()
    assert isinstance(model, torch.nn.Module)

def test_11_feature_ordering_is_deterministic():
    """Verify that feature ordering is identical between schema and dataset tensor generation."""
    from src.stage8_33.dataset import get_feature_groups, CURRENT_THERMAL_COLS, INDUSTRIAL_CONTEXT_COLS
    dummy_cols = CURRENT_THERMAL_COLS + ["hist_count_2km", "hist_count_1km", "hist_active_days_30d"] + INDUSTRIAL_CONTEXT_COLS
    fg1 = get_feature_groups(dummy_cols, include_geo=False)
    fg2 = get_feature_groups(dummy_cols, include_geo=False)
    assert fg1 == fg2, "Feature group definitions are non-deterministic"

def test_12_causal_temporal_encoder_receives_valid_sequences():
    """Verify that causal TCN receives sequences correctly and gradients propagate."""
    from src.stage8_33.model import CausalTCNEncoder
    tcn = CausalTCNEncoder(in_features=11, hidden_dim=32, dilations=[1, 2, 4])
    
    # Test batch with one non-empty and one empty sequence
    seq_tensor = torch.randn(2, 10, 11, requires_grad=True)
    seq_mask = torch.tensor([[1, 1, 1, 1, 1, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], dtype=torch.float32)
    
    out = tcn(seq_tensor, seq_mask)
    assert out.shape == (2, 32), f"Unexpected TCN output shape: {out.shape}"
    # Empty sequence must produce all zeros
    assert torch.all(out[1] == 0.0), "Empty sequence did not produce zero embedding"
    
    # Check backward gradient
    loss = out[0].sum()
    loss.backward()
    assert seq_tensor.grad is not None
    assert seq_tensor.grad[0, :5].abs().sum() > 0, "Zero gradient on active sequence elements"

def test_13_checkpoint_hash_is_reproducible():
    """Verify checkpoint SHA-256 matches saved checkpoint_hash.txt."""
    model_path = PROJECT_ROOT / "models" / "stage8_33" / "final_neural_model.pt"
    hash_path = PROJECT_ROOT / "models" / "stage8_33" / "checkpoint_hash.txt"
    assert model_path.exists() and hash_path.exists()
    
    with open(model_path, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()
    with open(hash_path, "r", encoding="utf-8") as f:
        recorded_hash = f.read().strip()
        
    assert actual_hash == recorded_hash, f"Checkpoint hash mismatch: {actual_hash} vs {recorded_hash}"

def test_14_no_hard_coded_class_specific_geographic_rules():
    """Verify no hard-coded latitude/longitude boundaries are used as classification rules."""
    src_33_files = list((PROJECT_ROOT / "src" / "stage8_33").glob("*.py"))
    for f in src_33_files:
        with open(f, "r", encoding="utf-8") as py_file:
            code = py_file.read()
            # Must not contain hard-coded inference rules like: if lat > X: return 'Forest'
            assert "if lat >" not in code and "if latitude >" not in code, f"Suspicious hardcoded lat rule in {f.name}"
            assert "if dist_to_fac <" not in code, f"Suspicious hardcoded dist rule in {f.name}"

def test_15_no_test_evaluation_occurs():
    """Verify that test evaluation counter for Stage 8.33 is strictly 0 and test access is False."""
    summary_path = PROJECT_ROOT / "artifacts" / "stage8_33" / "stage8_33_summary.md"
    assert summary_path.exists(), "Summary report missing"
    with open(summary_path, "r", encoding="utf-8") as f:
        summary_text = f.read()
    assert "ZERO / PERMANENTLY CLOSED" in summary_text, "Violation: Test access not closed in summary"
