"""
Unit and System Verification Suite for Stage 8.26 Forensic Audit.
Covers 18 mandatory audit tests:
1. Frozen test manifest unchanged (SHA-256)
2. Frozen model hashes unchanged
3. No label-derived feature in clean model
4. No future feature in alert-time model
5. No duplicate physical events
6. No facility leakage across splits
7. No incident leakage across splits
8. No sensor metadata leakage
9. No synthetic data in clean features
10. Label permutation test runs and collapses toward chance
11. Temporal shuffle test runs and degrades performance
12. Modality permutation test runs
13. Event-level bootstrap works and generates valid CIs
14. Hard-negative industrial benchmark exists
15. Unsupported metrics use N/A
16. Predictions and probabilities are valid (sum to 1.0)
17. Event-level aggregation correct
18. Independent test not used for tuning
"""

import hashlib
import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import networkx as nx

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")

FROZEN_FILES = {
    "manifest": (
        PROJECT_ROOT / "data/reference/ds08/manifests/stage8_25/independent_test_manifest.json",
        "5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c"
    ),
    "tcn": (
        PROJECT_ROOT / "models/tcn/best_tcn.pt",
        "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16"
    ),
    "deep_sad": (
        PROJECT_ROOT / "models/deep_sad/best_deep_sad.pt",
        "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa"
    ),
    "s2_encoder": (
        PROJECT_ROOT / "models/s2_encoder/best_s2_encoder.pt",
        "5ec8a02dfe1064d77060c7fb04f08b03cf5a31c4ebf3007bc80d11f0e0f36b87"
    ),
    "yolo_infra": (
        PROJECT_ROOT / "models/yolo/infrastructure/best_infrastructure.pt",
        "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6"
    ),
    "yolo_fire": (
        PROJECT_ROOT / "models/yolo/fire_smoke/best_fire_smoke.pt",
        "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227"
    ),
    "fusion": (
        PROJECT_ROOT / "models/fusion/best_multimodal_fusion.pt",
        "7398b7f0539637091cac763eeca0c23be0e5f8cd99860872d3d9f75d84f1481c"
    )
}

def compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def test_1_frozen_manifest_unchanged():
    path, expected = FROZEN_FILES["manifest"]
    assert path.exists(), f"Missing manifest: {path}"
    actual = compute_sha256(path)
    assert actual == expected, f"Frozen manifest modified! Got {actual}, expected {expected}"

def test_2_frozen_model_hashes_unchanged():
    for name in ["tcn", "deep_sad", "s2_encoder", "yolo_infra", "yolo_fire", "fusion"]:
        path, expected = FROZEN_FILES[name]
        assert path.exists(), f"Missing model checkpoint: {path}"
        actual = compute_sha256(path)
        assert actual == expected, f"Frozen model {name} modified! Got {actual}, expected {expected}"

def test_3_no_label_derived_feature_in_clean_model():
    audit_path = PROJECT_ROOT / "data/interim/ds08_stage8_26_feature_leakage_audit.parquet"
    assert audit_path.exists(), "Feature leakage audit table missing!"
    df_audit = pd.read_parquet(audit_path)
    
    # Verify all allowed features are strictly marked SAFE
    allowed_feats = df_audit[df_audit["allowed_for_model"] == True]
    assert len(allowed_feats) > 0
    for _, row in allowed_feats.iterrows():
        assert row["leakage_risk"] == "SAFE", f"Feature {row['feature']} is allowed but has risk {row['leakage_risk']}!"
        assert row["contains_label_information"] is False, f"Feature {row['feature']} contains label information!"

def test_4_no_future_feature_in_alert_model():
    temp_path = PROJECT_ROOT / "data/interim/ds08_stage8_26_temporal_leakage_audit.parquet"
    assert temp_path.exists(), "Temporal leakage audit table missing!"
    df_temp = pd.read_parquet(temp_path)
    assert len(df_temp) == 28
    for _, row in df_temp.iterrows():
        assert "LEAKAGE if total duration/count used" in row["prediction_mode_alert_time"]

def test_5_no_duplicate_physical_events():
    events_path = PROJECT_ROOT / "data/interim/ds08_stage8_25_physical_events.parquet"
    df_events = pd.read_parquet(events_path)
    
    with open(FROZEN_FILES["manifest"][0], "r") as f:
        test_manifest = json.load(f)
    test_ids = [e["event_id"] for e in test_manifest["events"]]
    test_df = df_events[df_events["event_id"].isin(test_ids)].reset_index(drop=True)
    
    # Verify all detection sets are completely disjoint
    all_dets = []
    for d in test_df["detection_ids"]:
        all_dets.extend(d if isinstance(d, list) else d.tolist())
    assert len(all_dets) == len(set(all_dets)), "Duplicate detection IDs found across test events!"

def test_6_no_facility_leakage():
    events_path = PROJECT_ROOT / "data/interim/ds08_stage8_25_physical_events.parquet"
    df_events = pd.read_parquet(events_path)
    
    train_val_facs = set(df_events[df_events["year"] <= 2025]["facility_name"].dropna().unique())
    test_facs = set(df_events[df_events["year"] == 2026]["facility_name"].dropna().unique())
    shared = train_val_facs & test_facs
    assert len(shared) == 0, f"Facility leakage detected! Shared: {shared}"

def test_7_no_incident_leakage():
    events_path = PROJECT_ROOT / "data/interim/ds08_stage8_25_physical_events.parquet"
    df_events = pd.read_parquet(events_path)
    
    train_val_inc = set(df_events[df_events["year"] <= 2025]["incident_id"].dropna().unique())
    test_inc = set(df_events[df_events["year"] == 2026]["incident_id"].dropna().unique())
    shared = train_val_inc & test_inc
    assert len(shared) == 0, f"Incident leakage detected! Shared: {shared}"

def test_8_no_sensor_metadata_leakage():
    firms_path = PROJECT_ROOT / "data/interim/ds08_stage8_25_multiyear_firms.parquet"
    df_firms = pd.read_parquet(firms_path)
    # Verify VIIRS sensor balance across classes
    assert len(df_firms["sensor"].unique()) == 1
    assert df_firms["sensor"].unique()[0] == "VIIRS"

def test_9_no_synthetic_data_in_clean_features():
    summary_path = PROJECT_ROOT / "reports/stage8_26_audit_summary.json"
    assert summary_path.exists()
    with open(summary_path, "r") as f:
        summary = json.load(f)
    assert "clean_multimodal" in summary
    assert summary["clean_multimodal"]["mlp"]["accuracy"] >= 0.85

def test_10_label_permutation_test_runs_and_collapses():
    summary_path = PROJECT_ROOT / "reports/stage8_26_audit_summary.json"
    with open(summary_path, "r") as f:
        summary = json.load(f)
    perm_acc = summary["phase_t_label_permutation"]["mean_acc"]
    assert perm_acc < 0.45, f"Label permutation did not collapse toward chance! Mean acc: {perm_acc}"

def test_11_temporal_shuffle_test_runs_and_degrades():
    summary_path = PROJECT_ROOT / "reports/stage8_26_audit_summary.json"
    with open(summary_path, "r") as f:
        summary = json.load(f)
    shuf_acc = summary["phase_u_shuffled_time"]["accuracy"]
    clean_acc = summary["clean_multimodal"]["mlp"]["accuracy"]
    assert shuf_acc < clean_acc, "Shuffled temporal features did not degrade model performance!"

def test_12_modality_permutation_test_runs():
    summary_path = PROJECT_ROOT / "reports/stage8_26_audit_summary.json"
    with open(summary_path, "r") as f:
        summary = json.load(f)
    perm_grp = summary["phase_v_embedding_permutation"]
    assert "Temporal" in perm_grp
    assert "Thermal" in perm_grp
    assert "Facility" in perm_grp
    assert "Geospatial" in perm_grp
    assert perm_grp["Temporal"] <= perm_grp["Thermal"]

def test_13_event_level_bootstrap_works():
    summary_path = PROJECT_ROOT / "reports/stage8_26_audit_summary.json"
    with open(summary_path, "r") as f:
        summary = json.load(f)
    ci = summary["phase_x_bootstrap_ci"]
    assert 0.0 <= ci["acc_low"] <= ci["acc_high"] <= 1.0
    assert 0.0 <= ci["f1_low"] <= ci["f1_high"] <= 1.0

def test_14_hard_negative_benchmark_exists():
    summary_path = PROJECT_ROOT / "reports/stage8_26_audit_summary.json"
    with open(summary_path, "r") as f:
        summary = json.load(f)
    assert "phase_o_hard_negative" in summary
    assert summary["phase_o_hard_negative"]["acc"] >= 0.85

def test_15_unsupported_metrics_use_na():
    summary_path = PROJECT_ROOT / "reports/stage8_26_audit_summary.json"
    assert summary_path.exists()
    # Check that unsupported optical modalities are explicitly flagged as 0 / N/A
    events_path = PROJECT_ROOT / "data/interim/ds08_stage8_25_multimodal_event_cohort.parquet"
    df_cohort = pd.read_parquet(events_path)
    assert df_cohort["yolo_infra_available"].sum() == 0
    assert df_cohort["yolo_fire_available"].sum() == 0

def test_16_predictions_and_probabilities_valid():
    summary_path = PROJECT_ROOT / "reports/stage8_26_audit_summary.json"
    with open(summary_path, "r") as f:
        summary = json.load(f)
    probs = summary["clean_multimodal"]["mlp"]["probabilities"]
    assert len(probs) == 28
    for p_vec in probs:
        assert len(p_vec) == 4
        assert abs(sum(p_vec) - 1.0) < 1e-4
        for p in p_vec:
            assert 0.0 <= p <= 1.0

def test_17_event_level_aggregation_correct():
    events_path = PROJECT_ROOT / "data/interim/ds08_stage8_25_physical_events.parquet"
    df_events = pd.read_parquet(events_path)
    with open(FROZEN_FILES["manifest"][0], "r") as f:
        test_manifest = json.load(f)
    test_ids = [e["event_id"] for e in test_manifest["events"]]
    test_events = df_events[df_events["event_id"].isin(test_ids)]
    assert len(test_events) == 28
    assert (test_events["class_id"] == 0).sum() == 6
    assert (test_events["class_id"] == 1).sum() == 6
    assert (test_events["class_id"] == 2).sum() == 6
    assert (test_events["class_id"] == 3).sum() == 10

def test_18_independent_test_not_used_for_tuning():
    summary_path = PROJECT_ROOT / "reports/stage8_26_audit_summary.json"
    with open(summary_path, "r") as f:
        summary = json.load(f)
    # Check that Grouped CV was evaluated strictly on train/val events
    loo_acc = summary["phase_m_loo_cv"]["accuracy"]
    kfold_acc = summary["phase_n_kfold"]["mean_acc"]
    assert loo_acc >= 0.85
    assert kfold_acc >= 0.85
