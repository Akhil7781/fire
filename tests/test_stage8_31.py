"""
Stage 8.31 Forensic Reconciliation and Verification Test Suite.
Validates all 12 key criteria across reconciliation, feature provenance, causality invariance,
ablation completeness, GRU gradient audit, single test evaluation count, and uncertainty quantification.
"""

import hashlib
import json
from pathlib import Path
import pytest
import pandas as pd

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")

def test_1_2025_reconciliation_report():
    rec_json_path = PROJECT_ROOT / "artifacts" / "stage8_31" / "2025_reconciliation.json"
    rec_md_path = PROJECT_ROOT / "artifacts" / "stage8_31" / "2025_reconciliation.md"
    assert rec_json_path.exists(), "2025_reconciliation.json does not exist"
    assert rec_md_path.exists(), "2025_reconciliation.md does not exist"

    with open(rec_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cohort = data["cohort_comparison"]
    assert cohort["same_cohort"] is True
    assert cohort["total_events"] == 24
    assert len(cohort["event_ids"]) == 24
    assert len(cohort["class_distribution"]) == 4
    assert cohort["class_distribution"]["Industrial Fire"] == 4
    assert cohort["class_distribution"]["Forest Fire"] == 7
    assert cohort["class_distribution"]["Agricultural Fire"] == 7
    assert cohort["class_distribution"]["Other / Persistent"] == 6

def test_2_feature_provenance_audit():
    prov_csv = PROJECT_ROOT / "artifacts" / "stage8_31" / "feature_provenance.csv"
    prov_md = PROJECT_ROOT / "artifacts" / "stage8_31" / "feature_provenance.md"
    assert prov_csv.exists(), "feature_provenance.csv does not exist"
    assert prov_md.exists(), "feature_provenance.md does not exist"

    df_prov = pd.read_csv(prov_csv)
    assert len(df_prov) >= 120, f"Expected >=120 features, found {len(df_prov)}"

    # All features must have zero label dependency and zero persistent registry dependency
    assert (df_prov["label_dependency"] == "NO").all(), "Found feature with label dependency"
    assert (df_prov["test_dependency"] == "NO").all(), "Found feature with test dependency"
    assert (df_prov["persistent_registry_dependency"] == "NO").all(), "Found feature with persistent registry dependency"
    assert (df_prov["safe_for_alert_time"] == "YES").all(), "Found feature unsafe for alert-time inference"

def test_3_raw_firms_no_associated_label_access():
    # Verify candidate selection in feature extraction never uses associated_* labels
    extractor_files = [
        PROJECT_ROOT / "src" / "stage8_30" / "history_dataset.py",
        PROJECT_ROOT / "src" / "stage8_31" / "test_causality.py"
    ]
    forbidden_terms = [
        "associated_persistent_id",
        "associated_forest_id",
        "associated_agri_id",
        "associated_incident_id"
    ]

    for f_path in extractor_files:
        if f_path.exists():
            code = f_path.read_text(encoding="utf-8")
            # In history_dataset.py, check that these columns are not used in candidate filtering
            for term in forbidden_terms:
                # If mentioned, verify it's only in comments or assertions, not query logic
                lines = [l.strip() for l in code.splitlines() if term in l]
                for l in lines:
                    assert not ("df_firms[" in l and term in l), f"Forbidden column {term} used in query logic in {f_path.name}: {l}"

def test_4_future_injection_invariance():
    causality_json = PROJECT_ROOT / "artifacts" / "stage8_31" / "causality_test_report.json"
    causality_md = PROJECT_ROOT / "artifacts" / "stage8_31" / "causality_test_report.md"
    assert causality_json.exists(), "causality_test_report.json does not exist"
    assert causality_md.exists(), "causality_test_report.md does not exist"

    with open(causality_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["FUTURE_INJECTION_INVARIANT"] == "PASS"
    assert data["status"] == "PASS"
    assert data["part_a_violations"] == 0
    assert data["part_b_violations"] == 0

def test_5_gru_gradient_audit():
    gru_path = PROJECT_ROOT / "artifacts" / "stage8_31" / "gru_gradient_audit.json"
    assert gru_path.exists(), "gru_gradient_audit.json does not exist"

    with open(gru_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    grad_stats = data["training_gradient_stats"]
    assert "gru_grad_norm_mean" in grad_stats
    assert "context_proj_grad_norm_mean" in grad_stats
    # Confirm that context projection received substantially higher gradient than GRU
    assert grad_stats["context_proj_grad_norm_mean"] > grad_stats["gru_grad_norm_mean"]
    assert "vanishing_or_exploding_gradients" in data

def test_6_ablations_matrix_completeness():
    abl_csv = PROJECT_ROOT / "artifacts" / "stage8_31" / "ablations.csv"
    abl_md = PROJECT_ROOT / "artifacts" / "stage8_31" / "ablation_summary.md"
    assert abl_csv.exists(), "ablations.csv does not exist"
    assert abl_md.exists(), "ablation_summary.md does not exist"

    df_abl = pd.read_csv(abl_csv)
    expected_ablations = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
    assert len(df_abl) == 12, f"Expected 12 ablations, found {len(df_abl)}"
    assert list(df_abl["Ablation"]) == expected_ablations

    # Confirm all evaluated on validation split (Correct / 24)
    for corr in df_abl["Val_Correct"]:
        assert corr.endswith("/24"), f"Ablation not evaluated on 24-event validation cohort: {corr}"

def test_7_feature_importance_report():
    feat_md = PROJECT_ROOT / "artifacts" / "stage8_31" / "feature_contribution_report.md"
    feat_json = PROJECT_ROOT / "artifacts" / "stage8_31" / "feature_importance.json"
    assert feat_md.exists(), "feature_contribution_report.md does not exist"
    assert feat_json.exists(), "feature_importance.json does not exist"

    with open(feat_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data["top_10_features"]) == 10
    assert len(data["bottom_10_features"]) == 10
    assert len(data["group_importance"]) >= 5

def test_8_frozen_test_manifest_hash():
    manifest_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "independent_test_manifest.json"
    assert manifest_path.exists(), "independent_test_manifest.json does not exist"
    h = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    expected_hash = "5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c"
    assert h == expected_hash, f"Independent test manifest has been modified! Hash: {h}"

def test_9_test_evaluation_count_strictly_one():
    counter_file = PROJECT_ROOT / "artifacts" / "stage8_31" / ".test_eval_counter"
    assert counter_file.exists(), "Test evaluation counter file does not exist"
    cnt = int(counter_file.read_text().strip())
    assert cnt == 1, f"TEST_EVALUATION_COUNT must be strictly 1, but is {cnt}!"

def test_10_final_test_report_metrics_and_ci():
    report_json = PROJECT_ROOT / "artifacts" / "stage8_31" / "final_test_report.json"
    report_md = PROJECT_ROOT / "artifacts" / "stage8_31" / "final_test_report.md"
    assert report_json.exists(), "final_test_report.json does not exist"
    assert report_md.exists(), "final_test_report.md does not exist"

    with open(report_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    perf = data["performance_metrics"]
    uq = data["uncertainty_quantification"]
    assert perf["total_test_events"] == 28
    assert perf["accuracy"] >= 0.80, f"Expected accuracy >= 0.80, got {perf['accuracy']}"
    assert "accuracy_95_bootstrap_ci" in uq
    assert "accuracy_95_wilson_ci" in uq
    assert "single_event_shift_percentage" in uq
    assert uq["single_event_shift_percentage"] == 3.57

def test_11_final_model_checkpoint_exists():
    models_dir = PROJECT_ROOT / "models" / "stage8_31"
    assert (models_dir / "random_forest_component.joblib").exists()
    assert (models_dir / "static_mlp_component.pt").exists()
    assert (models_dir / "tabular_scaler.joblib").exists()
    assert (models_dir / "nn_scalers.pt").exists()

def test_12_stage8_31_summary_report():
    summary_md = PROJECT_ROOT / "artifacts" / "stage8_31" / "stage8_31_summary.md"
    assert summary_md.exists(), "stage8_31_summary.md does not exist"
    txt = summary_md.read_text(encoding="utf-8")
    assert "2025 Performance Reconciliation" in txt
    assert "Feature Provenance & Causal Independence" in txt
    assert "Future-Record Injection Invariance" in txt
    assert "Controlled Ablations (A..L) & GRU Audit" in txt
    assert "Permutation Feature Importance" in txt
    assert "Frozen 2026 Independent Evaluation" in txt
