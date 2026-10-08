"""
Automated Pytest Suite for Stage 8.30 — Registry-Free Historical Thermal Recurrence Learning.
"""

import hashlib
import json
import re
from pathlib import Path
import pandas as pd
import pytest
import torch

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")

FROZEN_TEST_MANIFEST_SHA256 = "5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c"

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def test_stage8_25_test_manifest_frozen():
    manifest_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "independent_test_manifest.json"
    assert manifest_path.exists(), "Frozen test manifest missing!"
    current_hash = compute_sha256(manifest_path)
    assert current_hash == FROZEN_TEST_MANIFEST_SHA256, f"Frozen test manifest modified! {current_hash} != {FROZEN_TEST_MANIFEST_SHA256}"

def test_stage8_28_and_29_artifacts_preserved():
    for p in [
        PROJECT_ROOT / "models" / "stage8_28" / "causal_classifier.pt",
        PROJECT_ROOT / "artifacts" / "stage8_29" / "stage8_29_summary.json",
        PROJECT_ROOT / "artifacts" / "stage8_29" / "no_registry_horizon_results.csv",
    ]:
        assert p.exists(), f"Predecessor artifact missing: {p}"

def test_zero_persistent_registry_access_in_source_code():
    src_dir = PROJECT_ROOT / "src" / "stage8_30"
    forbidden_patterns = [
        r"persistent_source_manifest\.json",
        r"is_known_persistent",
        r"dist_to_persistent_registry_km",
        r"within_1km_persistent_registry",
        r"within_5km_persistent_registry",
    ]
    for py_file in src_dir.glob("*.py"):
        if py_file.name == "audit_code_proxy.py":
            continue
        content = py_file.read_text(encoding="utf-8")
        for pat in forbidden_patterns:
            matches = list(re.finditer(pat, content))
            assert len(matches) == 0, f"Forbidden pattern '{pat}' found in {py_file.name}!"

def test_strict_causal_history_cutoff():
    p_audit = PROJECT_ROOT / "artifacts" / "stage8_30" / "historical_sequence_audit.csv"
    assert p_audit.exists(), "historical_sequence_audit.csv missing!"
    df = pd.read_csv(p_audit)
    assert len(df) == 159, f"Expected 159 events in sequence audit, got {len(df)}"
    for _, r in df.iterrows():
        val = r["latest_history_ts"]
        if pd.notna(val) and str(val).strip() not in ["None", "nan", ""]:
            assert pd.to_datetime(val) <= pd.to_datetime(r["history_end"]), (
                f"History leakage for {r['event_id']}: {val} > {r['history_end']}"
            )

def test_target_events_not_in_history():
    p_feat_audit = PROJECT_ROOT / "artifacts" / "stage8_30" / "historical_sequence_audit.csv"
    df = pd.read_csv(p_feat_audit)
    assert df["zero_leakage_verified"].all(), "Not all historical sequences have zero target-event leakage verified!"

def test_feature_provenance_validity():
    p_prov = PROJECT_ROOT / "artifacts" / "stage8_30" / "feature_provenance.csv"
    assert p_prov.exists(), "feature_provenance.csv missing!"
    df = pd.read_csv(p_prov)
    assert len(df) >= 100, f"Expected >= 100 features in provenance table, got {len(df)}"
    assert df["allowed_in_primary_model"].all(), "Disallowed features present in primary model!"
    for _, r in df.iterrows():
        assert r["causal_status"] in ["STRICTLY_CAUSAL", "STATIC_AND_LABEL_INDEPENDENT"], (
            f"Invalid causal status: {r['causal_status']}"
        )

def test_ablation_results():
    p_abl = PROJECT_ROOT / "artifacts" / "stage8_30" / "ablation_results.csv"
    assert p_abl.exists(), "ablation_results.csv missing!"
    df = pd.read_csv(p_abl)
    assert len(df) == 8, f"Expected 8 ablation models, got {len(df)}"
    # Check baseline vs primary model
    m_base = df[df["Model"].str.contains("NO_REGISTRY baseline")].iloc[0]
    m_prim = df[df["Model"].str.contains("Primary")].iloc[0]
    assert m_base["H0 Accuracy"] == pytest.approx(0.785714, abs=0.01)
    assert m_prim["H0 Accuracy"] >= 0.85, f"Primary model failed to reach 85% accuracy: {m_prim['H0 Accuracy']}"
    assert m_prim["Macro-F1"] >= 0.85, f"Primary model failed to reach 0.85 Macro-F1: {m_prim['Macro-F1']}"

def test_multi_horizon_results():
    p_hor = PROJECT_ROOT / "artifacts" / "stage8_30" / "multi_horizon_results.csv"
    assert p_hor.exists(), "multi_horizon_results.csv missing!"
    df = pd.read_csv(p_hor)
    assert len(df) == 8, f"Expected 8 horizons, got {len(df)}"
    h0_row = df[df["Horizon"] == "H0"].iloc[0]
    assert h0_row["Accuracy"] >= 0.85, f"H0 accuracy below 85%: {h0_row['Accuracy']}"
    assert h0_row["Correct"] == "25/28", f"Expected 25/28 correct at H0, got {h0_row['Correct']}"

def test_persistent_discrimination_without_registry():
    p_err = PROJECT_ROOT / "artifacts" / "stage8_30" / "error_analysis.csv"
    assert p_err.exists(), "error_analysis.csv missing!"
    df = pd.read_csv(p_err)
    assert len(df) == 28, f"Expected 28 test events, got {len(df)}"
    pers_events = df[df["true_class"] == "Other / Persistent"]
    assert len(pers_events) == 10, f"Expected 10 persistent test events, got {len(pers_events)}"
    assert pers_events["prediction_correct"].all(), "Persistent source misclassified without registry!"
    # Ensure zero acute events misclassified as persistent
    acute_events = df[df["true_class"] != "Other / Persistent"]
    assert (acute_events["prediction"] != "Other / Persistent").all(), "Acute event misclassified as persistent!"

def test_all_stage8_30_artifacts_exist():
    required_files = [
        PROJECT_ROOT / "artifacts" / "stage8_30" / "stage8_30_final_report.md",
        PROJECT_ROOT / "artifacts" / "stage8_30" / "stage8_30_summary.json",
        PROJECT_ROOT / "artifacts" / "stage8_30" / "feature_provenance.csv",
        PROJECT_ROOT / "artifacts" / "stage8_30" / "historical_feature_audit.csv",
        PROJECT_ROOT / "artifacts" / "stage8_30" / "historical_sequence_audit.csv",
        PROJECT_ROOT / "artifacts" / "stage8_30" / "ablation_results.csv",
        PROJECT_ROOT / "artifacts" / "stage8_30" / "multi_horizon_results.csv",
        PROJECT_ROOT / "artifacts" / "stage8_30" / "prediction_flip_analysis.csv",
        PROJECT_ROOT / "artifacts" / "stage8_30" / "error_analysis.csv",
        PROJECT_ROOT / "artifacts" / "stage8_30" / "bootstrap_metrics.json",
        PROJECT_ROOT / "artifacts" / "stage8_30" / "artifact_hashes.json",
        PROJECT_ROOT / "models" / "stage8_30" / "historical_recurrence_encoder.pt",
        PROJECT_ROOT / "models" / "stage8_30" / "registry_free_causal_classifier.pt",
        PROJECT_ROOT / "models" / "stage8_30" / "scaler.json",
        PROJECT_ROOT / "models" / "stage8_30" / "metadata.json",
    ]
    for rf in required_files:
        assert rf.exists(), f"Required Stage 8.30 artifact missing: {rf}"
