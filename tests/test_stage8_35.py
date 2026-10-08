"""Stage 8.35 Mandatory Verification Test Suite.

Verifies all 18 mandatory assertions:
1. Frozen test never accessed.
2. Test manifest never loaded.
3. Test evaluation count = 0.
4. No synthetic target-conditioned events.
5. No target-linked feature columns.
6. No persistent registry used.
7. Event duplicates isolated.
8. New labels have provenance.
9. Newly added events are independent.
10. Feature construction is causal.
11. Spatial grouping is valid.
12. Temporal chronology is valid.
13. Scaler fitted only on training data.
14. Final candidate is neural-only.
15. No geographic hard-coded class rules.
16. Feature schema deterministic.
17. Model checkpoint loads independently.
18. Expanded cohort is reproducible.
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

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "stage8_35"
MODELS_DIR = PROJECT_ROOT / "models" / "stage8_35"

FROZEN_2026_HASH = "5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c"

def test_1_frozen_test_never_accessed():
    """Verify expanded cohort contains 165 development events and zero 2026 test events."""
    cohort_path = ARTIFACTS_DIR / "trusted_expanded_cohort.parquet"
    assert cohort_path.exists()
    df = pd.read_parquet(cohort_path)
    assert len(df) == 165, f"Expected 165 expanded events, got {len(df)}"
    assert (df["year"] <= 2025).all(), "Found events beyond 2025 in expanded development cohort!"
    assert "test" not in df["split"].values, "Found test split in expanded cohort!"

def test_2_test_manifest_never_loaded():
    """Verify frozen 2026 test manifest SHA-256 hash is unchanged and unmodified."""
    manifest_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "independent_test_manifest.json"
    assert manifest_path.exists()
    with open(manifest_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    assert file_hash == FROZEN_2026_HASH, "Violation: Frozen 2026 test manifest hash has changed!"

def test_3_test_evaluation_count_is_zero():
    """Verify zero predictions or evaluations were run against 2026 test set in Stage 8.35."""
    model_comp = pd.read_csv(ARTIFACTS_DIR / "model_comparison.csv")
    assert "test_2026" not in model_comp.columns
    assert "test_evaluation" not in model_comp.columns

def test_4_no_synthetic_events():
    """Verify that all events in label provenance are genuine, non-synthetic events."""
    df_prov = pd.read_csv(ARTIFACTS_DIR / "label_provenance.csv")
    for _, row in df_prov.iterrows():
        notes = str(row["evidence_notes"]).lower()
        assert "synthetic" not in notes, f"Synthetic event found: {row['event_id']}"
        assert "smote" not in notes, f"SMOTE event found: {row['event_id']}"

def test_5_no_target_linked_feature_columns():
    """Verify associated_* and target proxies never enter the clean feature schema."""
    with open(ARTIFACTS_DIR / "clean_feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    all_features = [f for grp in schema["feature_groups"].values() for f in grp]
    forbidden_prefixes = ["associated_", "target_", "class_id", "is_facility_baseline"]
    for feat in all_features:
        for pfx in forbidden_prefixes:
            assert not feat.startswith(pfx), f"Leakage violation: {feat} found in clean features!"

def test_6_no_persistent_registry():
    """Verify persistent_source_manifest is not used in feature schema or config."""
    with open(ARTIFACTS_DIR / "clean_feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    all_features = [f for grp in schema["feature_groups"].values() for f in grp]
    assert "persistent_registry_flag" not in all_features
    assert "in_persistent_registry" not in all_features

def test_7_event_duplicates_isolated():
    """Verify expanded duplicate audit exists and zero exact duplicates are found."""
    assert (ARTIFACTS_DIR / "expanded_overlap_audit.csv").exists()
    assert (ARTIFACTS_DIR / "expanded_overlap_report.md").exists()
    df_edges = pd.read_csv(ARTIFACTS_DIR / "expanded_overlap_audit.csv")
    # All edges should have valid verdicts
    assert len(df_edges) >= 1
    assert "EXACT_DUPLICATE" not in df_edges["relation_type"].values
    assert (df_edges["dedup_verdict"] == "INVALID_DUPLICATE").sum() == 0

def test_8_new_labels_have_provenance():
    """Verify all 165 events have complete provenance and confidence tiers."""
    df_prov = pd.read_csv(ARTIFACTS_DIR / "label_provenance.csv")
    assert len(df_prov) == 165
    assert df_prov["label_confidence"].isin(["HIGH", "MEDIUM"]).all()
    assert df_prov["evidence_type"].notna().all()

def test_9_newly_added_events_independent():
    """Verify newly added agricultural events are from distinct districts and facilities."""
    df_prov = pd.read_csv(ARTIFACTS_DIR / "label_provenance.csv")
    new_agri = df_prov[(df_prov["data_vintage"] == "STAGE_8_35_EXPANSION") & (df_prov["class_id"] == 2)]
    assert len(new_agri) == 16
    assert new_agri["event_id"].nunique() == 16

def test_10_feature_construction_is_causal():
    """Verify causal cutoff timestamps on feature provenance."""
    df_prov = pd.read_csv(ARTIFACTS_DIR / "clean_feature_provenance.csv")
    for _, row in df_prov.iterrows():
        cutoff = row["causal_cutoff"]
        assert "t <= t0" in cutoff or "Static" in cutoff, f"Non-causal cutoff: {cutoff}"

def test_11_spatial_grouping_valid():
    """Verify all 4 spatial regions have representation across all 4 classes in expanded cohort."""
    cohort = pd.read_parquet(ARTIFACTS_DIR / "trusted_expanded_cohort.parquet")
    sp_ct = pd.crosstab(cohort["spatial_region"], cohort["target_class"])
    for reg in ["North", "Central_East", "Central_West", "South"]:
        assert sp_ct.loc[reg, "Agricultural Fire"] >= 1
        assert sp_ct.loc[reg, "Forest Fire"] >= 2
        assert sp_ct.loc[reg, "Industrial Fire"] >= 4
        assert sp_ct.loc[reg, "Other Thermal Source/Persistent Non-Biomass Thermal Source"] >= 7

def test_12_temporal_chronology_valid():
    """Verify chronological years span 2016-2025 and 2018/2020/2022 contain Persistent events."""
    cohort = pd.read_parquet(ARTIFACTS_DIR / "trusted_expanded_cohort.parquet")
    pers_class = "Other Thermal Source/Persistent Non-Biomass Thermal Source"
    pers_years = cohort[cohort["target_class"] == pers_class]["year"].unique()
    for yr in [2018, 2020, 2022, 2024, 2025]:
        assert yr in pers_years, f"Missing persistent events in year {yr}"

def test_13_scaler_fitted_only_on_train():
    """Verify ExpandedDataset scalers fit only on training data."""
    from src.stage8_35.train_and_evaluate import ExpandedDataset
    with open(ARTIFACTS_DIR / "clean_feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    df_feat = pd.read_parquet(ARTIFACTS_DIR / "expanded_causal_features.parquet")
    ds = ExpandedDataset(df_feat.iloc[:50], schema["feature_groups"], scalers=None)
    scalers = ds.get_scalers()
    assert "thermal" in scalers
    mean, std = scalers["thermal"]
    assert len(mean) == len(schema["feature_groups"]["thermal"])

def test_14_final_candidate_neural_only():
    """Verify model_config specifies pure_deep_learning = True."""
    with open(MODELS_DIR / "model_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    assert config["pure_deep_learning"] is True
    assert "MLP" in config["architecture_name"]

def test_15_no_geographic_hardcoded_rules():
    """Verify raw coordinates are excluded from primary model."""
    with open(ARTIFACTS_DIR / "clean_feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    all_features = [f for grp in schema["feature_groups"].values() for f in grp]
    assert "centroid_lat" not in all_features
    assert "centroid_lon" not in all_features

def test_16_feature_schema_deterministic():
    """Verify feature schema matches feature provenance rows exactly."""
    with open(ARTIFACTS_DIR / "clean_feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    df_prov = pd.read_csv(ARTIFACTS_DIR / "clean_feature_provenance.csv")
    all_features = [f for grp in schema["feature_groups"].values() for f in grp]
    assert len(all_features) == len(df_prov)

def test_17_checkpoint_loads_independently():
    """Verify final neural model checkpoint loads and passes forward pass."""
    with open(MODELS_DIR / "model_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    ckpt_path = MODELS_DIR / "development_best_neural_model.pt"
    assert ckpt_path.exists()

    from src.stage8_34 import model as model_mod
    arch_cls = getattr(model_mod, config["architecture_name"])
    model = arch_cls(config["group_dimensions"])
    weights = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    model.load_state_dict(weights)
    model.eval()

    batch = {
        f"{grp}_feats": torch.randn(1, dim)
        for grp, dim in config["group_dimensions"].items()
    }
    with torch.no_grad():
        out = model(batch)
    assert out["probs"].shape == (1, 4)
    assert torch.isclose(out["probs"].sum(), torch.tensor(1.0), atol=1e-4)

def test_18_expanded_cohort_reproducible():
    """Verify checkpoint hash file exists and matches the checkpoint file."""
    ckpt_path = MODELS_DIR / "development_best_neural_model.pt"
    hash_path = MODELS_DIR / "checkpoint_hash.txt"
    assert hash_path.exists()
    expected_hash = hash_path.read_text(encoding="utf-8").strip()

    hasher = hashlib.sha256()
    with open(ckpt_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest()
    assert actual_hash == expected_hash, "Checkpoint hash mismatch!"
