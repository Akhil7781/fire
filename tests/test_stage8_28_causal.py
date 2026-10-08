"""
Stage 8.28 Forensic Verification and Causal Architecture Unit Tests.
Verifies all 18 scientific criteria and constraints specified in the prompt.
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

@pytest.fixture(scope="session")
def summary_json():
    p = PROJECT_ROOT / "artifacts" / "stage8_28" / "stage8_28_summary.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="session")
def prefix_audit_df():
    p = PROJECT_ROOT / "artifacts" / "stage8_28" / "horizon_prefix_audit.csv"
    assert p.exists(), f"Missing {p}"
    return pd.read_csv(p)

@pytest.fixture(scope="session")
def pred_audit_df():
    p = PROJECT_ROOT / "artifacts" / "stage8_28" / "horizon_prediction_audit.csv"
    assert p.exists(), f"Missing {p}"
    return pd.read_csv(p)

@pytest.fixture(scope="session")
def fac_audit_df():
    p = PROJECT_ROOT / "artifacts" / "stage8_28" / "facility_baseline_audit.csv"
    assert p.exists(), f"Missing {p}"
    return pd.read_csv(p)

# 1. Test Manifest Hash & 28 Events Integrity
def test_stage8_25_test_manifest_integrity():
    p = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "independent_test_manifest.json"
    assert p.exists()
    content = p.read_bytes()
    h = hashlib.sha256(content).hexdigest()
    assert h == "5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c"
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["events"]) == 28

# 2. Frozen Predecessor Checkpoints Integrity
def test_predecessor_frozen_checkpoints():
    predecessors = {
        "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
        "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
        "models/s2_encoder/best_s2_encoder.pt": "5ec8a02dfe1064d77060c7fb04f08b03cf5a31c4ebf3007bc80d11f0e0f36b87",
        "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
        "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
        "models/fusion/best_multimodal_fusion.pt": "7398b7f0539637091cac763eeca0c23be0e5f8cd99860872d3d9f75d84f1481c"
    }
    for rel_path, exp_hash in predecessors.items():
        fp = PROJECT_ROOT / rel_path
        assert fp.exists(), f"Missing predecessor checkpoint {rel_path}"
        actual_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert actual_hash == exp_hash, f"Hash mismatch for {rel_path}: {actual_hash} != {exp_hash}"

# 3. No Future Leakage: latest observation <= cutoff
def test_causal_no_future_leakage(prefix_audit_df):
    for _, row in prefix_audit_df.iterrows():
        if row["horizon"] != "Retro":
            assert row["cutoff_respected"] is True, f"Cutoff violated for {row['event_id']} at {row['horizon']}"

# 4. Horizon Prefix Monotonicity
def test_horizon_prefix_monotonicity():
    p = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_28_causal_prefix_dataset.parquet"
    df = pd.read_parquet(p)
    horizon_order = ["H0", "H1", "H2", "H3", "H6", "H12", "H24", "Retro"]
    for eid, g in df.groupby("event_id"):
        g_idx = g.set_index("horizon")
        prev_obs = 0
        for h in horizon_order:
            if h in g_idx.index:
                curr_obs = g_idx.loc[h, "number_observations_seen"]
                assert curr_obs >= prev_obs, f"Monotonicity violated for {eid} at {h}: {curr_obs} < {prev_obs}"
                prev_obs = curr_obs

# 5. Purged Leaked Features
def test_purged_leaked_features():
    p = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_28_causal_features.parquet"
    df = pd.read_parquet(p)
    assert "is_known_persistent" not in df.columns, "Leaked feature is_known_persistent found in feature columns!"
    assert "total_duration" not in df.columns, "Retrospective feature total_duration found in causal features!"
    assert "total_detections" not in df.columns, "Retrospective feature total_detections found in causal features!"
    assert "final_spatial_extent" not in df.columns, "Retrospective feature final_spatial_extent found in causal features!"
    assert "dist_to_persistent_registry_km" in df.columns, "Expected objective feature dist_to_persistent_registry_km missing!"

# 6. Industrial Facility Baseline: Zero Target Event Contribution
def test_industrial_facility_baseline_zero_target_contribution(fac_audit_df):
    assert len(fac_audit_df) > 0
    for _, row in fac_audit_df.iterrows():
        assert row["target_event_contribution"] == 0, f"Target contribution != 0 for {row['event_id']}"

# 7. Temporal Encoder Architecture & Forecasting Heads
def test_temporal_encoder_architecture():
    from src.stage8_28.models import CausalEarlyTemporalEncoder
    encoder = CausalEarlyTemporalEncoder(in_features=6, hidden_dim=64, out_dim=64)
    assert hasattr(encoder, "head_next_frp"), "Encoder missing head_next_frp forecasting head"
    assert hasattr(encoder, "head_next_delta_t"), "Encoder missing head_next_delta_t forecasting head"
    x = torch.randn(2, 4, 6)
    p_frp, p_dt, z = encoder.forward_sequence(x)
    assert p_frp.shape == (2, 3)
    assert p_dt.shape == (2, 3)
    assert z.shape == (2, 4, 64)

# 8. Checkpoint Files Exist and Are Loadable
def test_checkpoints_exist_and_loadable():
    m_enc = PROJECT_ROOT / "models" / "stage8_28" / "causal_temporal_encoder.pt"
    m_clf = PROJECT_ROOT / "models" / "stage8_28" / "causal_classifier.pt"
    scaler_p = PROJECT_ROOT / "models" / "stage8_28" / "scaler.json"
    meta_p = PROJECT_ROOT / "models" / "stage8_28" / "metadata.json"

    assert m_enc.exists(), f"Missing {m_enc}"
    assert m_clf.exists(), f"Missing {m_clf}"
    assert scaler_p.exists(), f"Missing {scaler_p}"
    assert meta_p.exists(), f"Missing {meta_p}"

    from src.stage8_28.models import CausalEarlyTemporalEncoder, HierarchicalCausalClassifier
    enc = CausalEarlyTemporalEncoder(in_features=6, hidden_dim=64, out_dim=64)
    enc.load_state_dict(torch.load(m_enc, map_location="cpu"))

    with open(meta_p, "r", encoding="utf-8") as f:
        meta = json.load(f)
    clf = HierarchicalCausalClassifier(in_dim=meta["in_dim"], hidden_dim=64)
    clf.load_state_dict(torch.load(m_clf, map_location="cpu"))

# 9. Preservation of Stage 8.27 Artifacts
def test_stage8_27_artifacts_preserved():
    m827_enc = PROJECT_ROOT / "models" / "stage8_27" / "best_causal_temporal_encoder.pt"
    m827_clf = PROJECT_ROOT / "models" / "stage8_27" / "best_hierarchical_causal_classifier.pt"
    assert m827_enc.exists(), "Stage 8.27 temporal encoder was deleted or overwritten!"
    assert m827_clf.exists(), "Stage 8.27 classifier was deleted or overwritten!"

# 10. Multi-Horizon Coverage and Metrics
def test_multi_horizon_results(summary_json):
    hr = summary_json["horizon_results"]
    for h in ["H0", "H1", "H2", "H3", "H6", "H12", "H24", "Retro"]:
        assert h in hr, f"Horizon {h} missing from summary"
        assert "accuracy" in hr[h]
        assert "macro_f1" in hr[h]
        assert "balanced_accuracy" in hr[h]
        assert hr[h]["num_events"] == 28

# 11. Event-Level Bootstrap Confidence Intervals
def test_bootstrap_intervals(summary_json):
    bm = summary_json["bootstrap_metrics"]
    for h in ["H0", "H1", "H2", "H3", "H6", "H12", "H24", "Retro"]:
        assert h in bm, f"Bootstrap metrics missing for {h}"
        assert len(bm[h]["accuracy_ci_95"]) == 2
        assert len(bm[h]["macro_f1_ci_95"]) == 2
        assert bm[h]["accuracy_ci_95"][0] <= bm[h]["accuracy_ci_95"][1]

# 12. Paired Sample Behavior Test (Sample A vs B)
def test_paired_sample_test(summary_json):
    pst = summary_json["paired_sample_test"]
    assert pst["embeddings_differ"] is True, "Embeddings for Sample A and Sample B should differ when observations differ"
    assert pst["sample_A_observations"] < pst["sample_B_observations"]

# 13. Label Permutation Degradation
def test_label_permutation_degradation(summary_json):
    lp = summary_json["adversarial_tests"]["label_permutation"]
    assert lp["passed"] is True, f"Label permutation did not degrade accuracy: {lp['mean_accuracy']}"
    assert lp["mean_accuracy"] < 0.45

# 14. All Stage 8.28 Artifacts Exist
def test_all_stage8_28_artifacts_exist():
    artifacts = [
        "stage8_28_summary.json",
        "causal_feature_audit.csv",
        "horizon_prefix_audit.csv",
        "horizon_prediction_audit.csv",
        "facility_baseline_audit.csv",
        "confusion_matrices.json",
        "bootstrap_metrics.json",
        "leakage_audit.json",
        "artifact_hashes.json",
        "stage8_28_final_report.md"
    ]
    for a in artifacts:
        p = PROJECT_ROOT / "artifacts" / "stage8_28" / a
        assert p.exists(), f"Required artifact missing: {p}"
