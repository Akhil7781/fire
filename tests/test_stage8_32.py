"""
Stage 8.32 Forensic and Neural-Only Architecture Test Suite.
Verifies all 12 key mandatory invariants:
1. Frozen test manifest hash unchanged.
2. Test cohort unchanged (28 events, exactly matching manifest).
3. No target-derived input columns.
4. No associated_* label columns used.
5. No persistent registry access.
6. No future information in historical features (t <= t0 - 7 days).
7. Spatial split has no spatial leakage under the chosen grouping method.
8. Preprocessing fitted only on training data.
9. Neural model loads independently.
10. Same input schema at training/inference.
11. Final model contains no classical ML component (Deep Learning Only).
12. Test evaluation counter equals exactly 1.
"""

import hashlib
import json
import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import torch

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def test_1_frozen_test_manifest_hash_unchanged():
    manifest_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "independent_test_manifest.json"
    assert manifest_path.exists(), "independent_test_manifest.json does not exist"
    h = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    expected_hash = "5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c"
    assert h == expected_hash, f"Frozen manifest hash modified! Got {h}"

def test_2_test_cohort_unchanged():
    manifest_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "independent_test_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    manifest_ids = {item["event_id"] for item in manifest_data.get("events", [])}

    df_feat = pd.read_parquet(PROJECT_ROOT / "data" / "interim" / "ds08_stage8_30_causal_features.parquet")
    test_df = df_feat[(df_feat["horizon"] == "H0") & (df_feat["split"] == "test")]
    test_ids = set(test_df["event_id"])

    assert len(test_ids) == 28, f"Expected 28 test events, found {len(test_ids)}"
    assert test_ids == manifest_ids, "Test cohort IDs mismatch between features and manifest!"

def test_3_no_target_derived_input_columns():
    schema_path = PROJECT_ROOT / "models" / "stage8_32" / "feature_schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    forbidden_names = ["class_id", "target_class", "split", "year", "label", "target"]
    for grp, cols in schema.items():
        for col in cols:
            assert col not in forbidden_names, f"Target derived column {col} in feature group {grp}!"

def test_4_no_associated_label_columns_used():
    source_files = [
        PROJECT_ROOT / "src" / "stage8_32" / "dataset.py",
        PROJECT_ROOT / "src" / "stage8_32" / "model.py",
        PROJECT_ROOT / "src" / "stage8_32" / "train_final.py"
    ]
    forbidden_terms = [
        "associated_persistent_id",
        "associated_forest_id",
        "associated_agri_id",
        "associated_incident_id"
    ]
    for sf in source_files:
        if sf.exists():
            txt = sf.read_text(encoding="utf-8")
            for term in forbidden_terms:
                assert term not in txt, f"Forbidden label column {term} found in {sf.name}!"

def test_5_no_persistent_registry_access():
    source_files = list((PROJECT_ROOT / "src" / "stage8_32").glob("*.py"))
    for sf in source_files:
        txt = sf.read_text(encoding="utf-8")
        assert "persistent_source_manifest.json" not in txt, f"Persistent manifest accessed in {sf.name}!"

def test_6_no_future_information_in_historical_features():
    report_path = PROJECT_ROOT / "artifacts" / "stage8_31" / "causality_test_report.json"
    assert report_path.exists(), "Causality test report missing"
    with open(report_path, "r", encoding="utf-8") as f:
        causality = json.load(f)
    assert causality["FUTURE_INJECTION_INVARIANT"] == "PASS"
    assert causality["status"] == "PASS"

def test_7_spatial_split_no_leakage():
    from src.stage8_32.spatial_split import load_development_events, get_splits
    dev_df = load_development_events()
    splits = get_splits(dev_df)
    tr_sp, va_sp = splits["spatial_block"]

    # Verify that Central_West events do NOT appear in training
    assert len(set(tr_sp["event_id"]).intersection(set(va_sp["event_id"]))) == 0
    assert (tr_sp["spatial_region"] != "Central_West").all()
    assert (va_sp["spatial_region"] == "Central_West").all()

def test_8_preprocessing_fitted_only_on_training_data():
    prep_path = PROJECT_ROOT / "models" / "stage8_32" / "preprocessing.pt"
    assert prep_path.exists(), "preprocessing.pt missing"
    scalers = torch.load(prep_path, weights_only=False)

    df_feat = pd.read_parquet(PROJECT_ROOT / "data" / "interim" / "ds08_stage8_30_causal_features.parquet")
    train_df = df_feat[(df_feat["horizon"] == "H0") & (df_feat["split"] == "train")]

    # Check thermal mean matches train split
    from src.stage8_32.dataset import CURRENT_THERMAL_COLS
    expected_thermal_mean = train_df[CURRENT_THERMAL_COLS].mean().values.astype(np.float32)
    saved_thermal_mean = scalers["thermal"][0]
    np.testing.assert_allclose(saved_thermal_mean, expected_thermal_mean, rtol=1e-3, atol=1e-3)

def test_9_neural_model_loads_independently():
    from src.stage8_32.model import GroupedCausalThermalClassifier
    config_path = PROJECT_ROOT / "models" / "stage8_32" / "model_config.json"
    weights_path = PROJECT_ROOT / "models" / "stage8_32" / "final_neural_model.pt"

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    model = GroupedCausalThermalClassifier(
        group_dims=cfg["feature_group_dims"],
        hidden_dim=cfg["hidden_dim"],
        num_res_blocks=cfg["num_res_blocks"],
        dropout=cfg["dropout"]
    )
    state = torch.load(weights_path, weights_only=True)
    model.load_state_dict(state)
    model.eval()

    # Pass dummy batch to verify forward pass
    dummy_batch = {}
    for grp, dim in cfg["feature_group_dims"].items():
        dummy_batch[f"{grp}_feats"] = torch.randn(2, dim)

    out = model(dummy_batch)
    assert out["logits_4class"].shape == (2, 4)
    assert out["logits_binary"].shape == (2, 2)
    assert out["logits_subclass"].shape == (2, 3)

def test_10_same_input_schema_at_training_and_inference():
    schema_path = PROJECT_ROOT / "models" / "stage8_32" / "feature_schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    df_feat = pd.read_parquet(PROJECT_ROOT / "data" / "interim" / "ds08_stage8_30_causal_features.parquet")
    for grp, cols in schema.items():
        for col in cols:
            assert col in df_feat.columns, f"Schema feature {col} missing from inference dataset!"

def test_11_final_model_contains_no_classical_ml_component():
    config_path = PROJECT_ROOT / "models" / "stage8_32" / "model_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    assert cfg["deep_learning_only"] is True
    assert cfg["classical_ml_components"] is False
    assert "RandomForest" not in cfg["model_type"]
    assert "XGBoost" not in cfg["model_type"]
    assert "GradientBoosting" not in cfg["model_type"]

def test_12_test_evaluation_counter_strictly_one():
    counter_file = PROJECT_ROOT / "artifacts" / "stage8_32" / ".test_eval_counter"
    assert counter_file.exists(), "Test evaluation counter file does not exist"
    cnt = int(counter_file.read_text().strip())
    assert cnt == 1, f"TEST_EVALUATION_COUNT must be strictly 1, but is {cnt}!"
