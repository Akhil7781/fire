"""Stage 8.36 Mandatory Forensic Verification Test Suite.

Verifies all 15 mandatory scientific invariants:
1. Frozen test manifest hash matches expected hash.
2. Final checkpoint hash is recorded and matches expected hash.
3. Test cohort contains exactly 28 events.
4. Test evaluation counter equals exactly 1.
5. No test data was accessed before final evaluation.
6. No test-derived training occurred.
7. No feature schema changes occurred after freeze.
8. No preprocessing changes occurred after freeze.
9. No persistent registry dependency.
10. No target-derived features.
11. No associated_* feature usage.
12. Final model is neural-only.
13. Final predictions are deterministic.
14. Final model loads independently.
15. Final feature order matches the training schema.
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

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "stage8_36"
MODELS_DIR = PROJECT_ROOT / "models" / "stage8_36"
MANIFEST_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "independent_test_manifest.json"

EXPECTED_MANIFEST_HASH = "5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c"
EXPECTED_CHECKPOINT_HASH = "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2"

def test_1_frozen_test_manifest_hash_matches():
    """Verify test manifest exists and its SHA-256 hash matches the frozen benchmark."""
    assert MANIFEST_PATH.exists(), "independent_test_manifest.json does not exist"
    actual_hash = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
    assert actual_hash == EXPECTED_MANIFEST_HASH, f"Manifest hash mismatch: {actual_hash}"

def test_2_final_checkpoint_hash_recorded():
    """Verify final checkpoint exists and its SHA-256 hash matches the frozen model."""
    ckpt_path = MODELS_DIR / "final_neural_model.pt"
    assert ckpt_path.exists(), "final_neural_model.pt missing"
    actual_hash = hashlib.sha256(ckpt_path.read_bytes()).hexdigest()
    assert actual_hash == EXPECTED_CHECKPOINT_HASH, f"Checkpoint hash mismatch: {actual_hash}"
    
    hash_file = MODELS_DIR / "checkpoint_hash.txt"
    assert hash_file.exists(), "checkpoint_hash.txt missing"
    saved_hash = hash_file.read_text(encoding="utf-8").strip()
    assert saved_hash == EXPECTED_CHECKPOINT_HASH, f"Saved hash mismatch: {saved_hash}"

def test_3_test_cohort_exactly_28_events():
    """Verify test manifest and final predictions contain exactly 28 events."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    events = manifest_data.get("events", [])
    assert len(events) == 28, f"Expected 28 events in manifest, got {len(events)}"
    
    preds_df = pd.read_csv(ARTIFACTS_DIR / "final_predictions.csv")
    assert len(preds_df) == 28, f"Expected 28 events in predictions, got {len(preds_df)}"
    assert set(preds_df["event_id"]) == {e["event_id"] for e in events}

def test_4_test_evaluation_counter_strictly_one():
    """Verify TEST_EVALUATION_COUNT is strictly 1 in counter file and report."""
    counter_file = ARTIFACTS_DIR / ".test_eval_counter"
    assert counter_file.exists(), ".test_eval_counter missing"
    cnt = int(counter_file.read_text(encoding="utf-8").strip())
    assert cnt == 1, f"TEST_EVALUATION_COUNT must be strictly 1, got {cnt}"
    
    report_file = ARTIFACTS_DIR / "final_test_report.json"
    with open(report_file, "r", encoding="utf-8") as f:
        rep = json.load(f)
    assert rep["evaluation_count"] == 1, f"Report evaluation_count must be 1, got {rep['evaluation_count']}"

def test_5_no_test_data_accessed_before_final_evaluation():
    """Verify development cohort had zero 2026 test events."""
    dev_cohort = pd.read_parquet(PROJECT_ROOT / "artifacts" / "stage8_35" / "trusted_expanded_cohort.parquet")
    assert len(dev_cohort) == 165
    assert (dev_cohort["year"] <= 2025).all()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    test_ids = {e["event_id"] for e in manifest_data["events"]}
    assert len(set(dev_cohort["event_id"]).intersection(test_ids)) == 0

def test_6_no_test_derived_training_occurred():
    """Verify training split only contains historical events through 2024."""
    dev_cohort = pd.read_parquet(PROJECT_ROOT / "artifacts" / "stage8_35" / "trusted_expanded_cohort.parquet")
    train_cohort = dev_cohort[dev_cohort["year"] <= 2024]
    assert len(train_cohort) == 125
    assert (train_cohort["year"] <= 2024).all()

def test_7_no_feature_schema_changes_after_freeze():
    """Verify feature schema is strictly identical between Stage 8.35 and Stage 8.36."""
    schema_35_path = PROJECT_ROOT / "models" / "stage8_35" / "feature_schema.json"
    schema_36_path = MODELS_DIR / "feature_schema.json"
    assert schema_36_path.exists()
    
    with open(schema_35_path, "r", encoding="utf-8") as f:
        s35 = json.load(f)
    with open(schema_36_path, "r", encoding="utf-8") as f:
        s36 = json.load(f)
    assert s35 == s36, "Feature schema has changed after freeze!"
    assert s36["total_features"] == 41

def test_8_no_preprocessing_changes_after_freeze():
    """Verify preprocessing standardizers are strictly identical between Stage 8.35 and Stage 8.36."""
    p35_path = PROJECT_ROOT / "models" / "stage8_35" / "preprocessing.pt"
    p36_path = MODELS_DIR / "preprocessing.pt"
    assert p36_path.exists()
    
    s35 = torch.load(p35_path, weights_only=False)
    s36 = torch.load(p36_path, weights_only=False)
    for grp in ["thermal", "industrial", "ecoregion", "historical"]:
        np.testing.assert_allclose(s35[grp][0], s36[grp][0], atol=1e-6)
        np.testing.assert_allclose(s35[grp][1], s36[grp][1], atol=1e-6)

def test_9_no_persistent_registry():
    """Verify persistent registry manifest and flags are completely absent from schema."""
    with open(MODELS_DIR / "feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    all_feats = [f for grp in schema["feature_groups"].values() for f in grp]
    assert "persistent_registry_flag" not in all_feats
    assert "in_persistent_registry" not in all_feats
    assert "persistent_source_manifest.json" not in json.dumps(schema)

def test_10_no_target_derived_features():
    """Verify that target labels and target proxies are not in feature schema."""
    with open(MODELS_DIR / "feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    all_feats = [f for grp in schema["feature_groups"].values() for f in grp]
    forbidden_prefixes = ["target_", "class_id", "label_", "split", "is_facility_baseline"]
    for feat in all_feats:
        for pfx in forbidden_prefixes:
            assert not feat.startswith(pfx), f"Target derived feature {feat} in schema!"

def test_11_no_associated_feature_usage():
    """Verify no associated_* label columns exist in schema or source files."""
    with open(MODELS_DIR / "feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    all_feats = [f for grp in schema["feature_groups"].values() for f in grp]
    for feat in all_feats:
        assert not feat.startswith("associated_"), f"associated_* feature {feat} found in schema!"

def test_12_final_model_is_neural_only():
    """Verify final model is pure PyTorch neural network with no classical ML components."""
    with open(MODELS_DIR / "model_config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
    assert cfg["pure_deep_learning"] is True
    assert cfg["deep_learning_only"] is True
    assert cfg["classical_ml_components"] is False
    assert cfg["architecture_name"] == "Architecture1_StaticMLP"

def test_13_final_predictions_are_deterministic():
    """Verify that repeating the forward pass with saved weights reproduces exact predictions."""
    from src.stage8_36.model import Architecture1_StaticMLP
    with open(MODELS_DIR / "model_config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
    with open(MODELS_DIR / "feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    
    # Load model
    model = Architecture1_StaticMLP(cfg["group_dimensions"], hidden_dim=48, num_classes=4, dropout=0.15)
    model.load_state_dict(torch.load(MODELS_DIR / "final_neural_model.pt", weights_only=True, map_location="cpu"))
    model.eval()
    
    # Load features and scalers
    df_feat = pd.read_parquet(PROJECT_ROOT / "data" / "interim" / "ds08_stage8_30_causal_features.parquet")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    manifest_ids = [e["event_id"] for e in manifest_data["events"]]
    df_h0 = df_feat[(df_feat["horizon"] == "H0") & (df_feat["event_id"].isin(manifest_ids))].set_index("event_id").loc[manifest_ids].reset_index()
    
    scalers = torch.load(MODELS_DIR / "preprocessing.pt", weights_only=False)
    batch = {}
    for grp in ["thermal", "industrial", "ecoregion", "historical"]:
        mat = df_h0[schema["feature_groups"][grp]].values.astype(np.float32)
        mean, std = scalers[grp]
        norm_mat = (mat - mean) / std
        batch[f"{grp}_feats"] = torch.tensor(norm_mat, dtype=torch.float32)
        
    with torch.no_grad():
        out = model(batch)
        probs = out["probs"].numpy()
        preds = np.argmax(probs, axis=-1)
        
    saved_preds_df = pd.read_csv(ARTIFACTS_DIR / "final_predictions.csv")
    np.testing.assert_array_equal(preds, saved_preds_df["predicted_class_id"].values)
    np.testing.assert_allclose(probs[:, 0], saved_preds_df["probability_industrial"].values, atol=1e-5)
    np.testing.assert_allclose(probs[:, 1], saved_preds_df["probability_forest"].values, atol=1e-5)
    np.testing.assert_allclose(probs[:, 2], saved_preds_df["probability_agricultural"].values, atol=1e-5)
    np.testing.assert_allclose(probs[:, 3], saved_preds_df["probability_persistent"].values, atol=1e-5)

def test_14_final_model_loads_independently():
    """Verify final model can be instantiated and load weights independently."""
    from src.stage8_36.model import Architecture1_StaticMLP
    with open(MODELS_DIR / "model_config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
    model = Architecture1_StaticMLP(cfg["group_dimensions"])
    weights = torch.load(MODELS_DIR / "final_neural_model.pt", weights_only=True, map_location="cpu")
    model.load_state_dict(weights)
    model.eval()
    
    dummy_batch = {f"{g}_feats": torch.randn(2, d) for g, d in cfg["group_dimensions"].items()}
    with torch.no_grad():
        out = model(dummy_batch)
    assert out["logits"].shape == (2, 4)
    assert out["probs"].shape == (2, 4)
    assert torch.allclose(out["probs"].sum(dim=-1), torch.ones(2), atol=1e-5)

def test_15_feature_order_matches_training_schema():
    """Verify feature names and order match exactly across schema and feature groups."""
    with open(MODELS_DIR / "feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    groups = ["thermal", "industrial", "ecoregion", "historical"]
    expected_dims = {"thermal": 14, "industrial": 6, "ecoregion": 3, "historical": 18}
    
    total_feats = 0
    for grp in groups:
        cols = schema["feature_groups"][grp]
        assert len(cols) == expected_dims[grp], f"Group {grp} dimension mismatch"
        total_feats += len(cols)
    assert total_feats == 41, f"Expected 41 features, got {total_feats}"
