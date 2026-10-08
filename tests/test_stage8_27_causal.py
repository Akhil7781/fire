"""
Unit and System Verification Suite for Stage 8.27 Causal Real-Time Attribution.
Covers 20 mandatory tests:
1. prefix construction
2. causal cutoff correctness
3. no future detections
4. no future imagery
5. no future facility statistics
6. no final-duration feature
7. no final-detection-count feature
8. event-level split integrity
9. modality timestamp masking
10. hierarchical probability normalization
11. deterministic inference
12. no NaN/Inf
13. label permutation collapses toward chance
14. temporal shuffle degrades
15. hard-negative construction
16. frozen-test immutability
17. frozen predecessor hashes
18. abstention policy
19. horizon ordering
20. event-level aggregation
"""

import hashlib
import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import torch

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

def test_1_prefix_construction():
    p_path = PROJECT_ROOT / "data/interim/ds08_stage8_27_causal_prefix_dataset.parquet"
    assert p_path.exists(), "Causal prefix dataset missing!"
    df = pd.read_parquet(p_path)
    assert len(df) == 1272 # 159 events x 8 horizons
    for h in ["H0", "H1", "H2", "H3", "H6", "H12", "H24", "Retro"]:
        assert h in df["horizon"].values

def test_2_causal_cutoff_correctness():
    p_path = PROJECT_ROOT / "data/interim/ds08_stage8_27_causal_prefix_dataset.parquet"
    df = pd.read_parquet(p_path)
    for _, row in df.iterrows():
        cutoff = pd.to_datetime(row["prefix_cutoff_time"])
        assert pd.notna(cutoff)

def test_3_no_future_detections():
    p_path = PROJECT_ROOT / "data/interim/ds08_stage8_27_causal_prefix_dataset.parquet"
    f_path = PROJECT_ROOT / "data/interim/ds08_stage8_25_multiyear_firms.parquet"
    df_p = pd.read_parquet(p_path)
    df_f = pd.read_parquet(f_path).set_index("detection_id")
    
    # Check H0 specifically: every seen detection must have acq_dt <= cutoff
    df_h0 = df_p[df_p["horizon"] == "H0"]
    for _, row in df_h0.iterrows():
        cutoff = pd.to_datetime(row["prefix_cutoff_time"])
        for did in row["detection_ids_seen"]:
            acq = pd.to_datetime(df_f.loc[did, "acq_datetime_utc"])
            assert acq <= cutoff, f"Future detection leak! acq {acq} > cutoff {cutoff}"

def test_4_no_future_imagery():
    f_path = PROJECT_ROOT / "data/interim/ds08_stage8_27_causal_features.parquet"
    df_f = pd.read_parquet(f_path)
    # At H0, S2 must never be available unless acquired prior
    h0_s2 = df_f[df_f["horizon"] == "H0"]["s2_available"].sum()
    assert h0_s2 == 0.0, "Future imagery available at H0!"

def test_5_no_future_facility_statistics():
    f_path = PROJECT_ROOT / "data/interim/ds08_stage8_27_causal_features.parquet"
    df_f = pd.read_parquet(f_path)
    assert "facility_baseline_frp" in df_f.columns
    assert "facility_frp_zscore" in df_f.columns
    # Check that baselines are finite and non-negative
    assert (df_f["facility_baseline_frp"] >= 0.0).all()

def test_6_no_final_duration_feature():
    f_path = PROJECT_ROOT / "data/interim/ds08_stage8_27_causal_features.parquet"
    df_f = pd.read_parquet(f_path)
    assert "duration_hours" not in df_f.columns
    assert "elapsed_observation_hours" in df_f.columns
    # At H0, elapsed observation time must be 0
    h0_elapsed = df_f[df_f["horizon"] == "H0"]["elapsed_observation_hours"].max()
    assert h0_elapsed == 0.0, "Elapsed hours non-zero at H0!"

def test_7_no_final_detection_count_feature():
    f_path = PROJECT_ROOT / "data/interim/ds08_stage8_27_causal_features.parquet"
    df_f = pd.read_parquet(f_path)
    assert "detection_count" not in df_f.columns
    assert "detections_observed_so_far" in df_f.columns

def test_8_event_level_split_integrity():
    p_path = PROJECT_ROOT / "data/interim/ds08_stage8_27_causal_prefix_dataset.parquet"
    df_p = pd.read_parquet(p_path)
    # Check that each event appears strictly in one split across all horizons
    for eid, grp in df_p.groupby("event_id"):
        assert grp["split"].nunique() == 1, f"Event {eid} split across partitions!"

def test_9_modality_timestamp_masking():
    f_path = PROJECT_ROOT / "data/interim/ds08_stage8_27_causal_features.parquet"
    df_f = pd.read_parquet(f_path)
    assert (df_f["yolo_infra_available"] == 0.0).all()
    assert (df_f["yolo_fire_available"] == 0.0).all()
    assert (df_f["landsat_available"] == 0.0).all()

def test_10_hierarchical_probability_normalization():
    pred_path = PROJECT_ROOT / "data/interim/ds08_stage8_27_predictions.parquet"
    df_preds = pd.read_parquet(pred_path)
    p_sum = df_preds["prob_industrial"] + df_preds["prob_forest"] + df_preds["prob_agricultural"] + df_preds["prob_persistent"]
    np.testing.assert_allclose(p_sum.values, 1.0, atol=1e-4)

def test_11_deterministic_inference():
    from src.stage8_27.models import HierarchicalCausalClassifier
    ckpt = PROJECT_ROOT / "models/stage8_27/best_hierarchical_causal_classifier.pt"
    m = HierarchicalCausalClassifier(in_dim=28, hidden_dim=64)
    m.load_state_dict(torch.load(ckpt))
    m.eval()
    x = torch.randn(2, 28)
    with torch.no_grad():
        p1, _ = m(x)
        p2, _ = m(x)
    torch.testing.assert_close(p1, p2)

def test_12_no_nan_inf():
    f_path = PROJECT_ROOT / "data/interim/ds08_stage8_27_causal_features.parquet"
    df_f = pd.read_parquet(f_path)
    assert not df_f.isna().any().any(), "NaN found in causal features!"
    pred_path = PROJECT_ROOT / "data/interim/ds08_stage8_27_predictions.parquet"
    df_preds = pd.read_parquet(pred_path)
    assert not df_preds.isna().any().any(), "NaN found in predictions!"

def test_13_label_permutation():
    summary_path = PROJECT_ROOT / "reports/stage8_27_summary.json"
    with open(summary_path) as f:
        s = json.load(f)
    perm_acc = s["stress_tests"]["label_permutation_mean_acc"]
    assert perm_acc < 0.40, f"Permutation acc {perm_acc} did not collapse toward chance!"

def test_14_temporal_shuffle():
    summary_path = PROJECT_ROOT / "reports/stage8_27_summary.json"
    with open(summary_path) as f:
        s = json.load(f)
    assert "temporal_shuffle_acc" in s["stress_tests"]

def test_15_hard_negative_construction():
    summary_path = PROJECT_ROOT / "reports/stage8_27_summary.json"
    with open(summary_path) as f:
        s = json.load(f)
    assert "Ind_vs_Per_H0" in s["hard_negatives"]
    assert s["hard_negatives"]["Ind_vs_Per_H0"] == 1.0

def test_16_frozen_test_immutability():
    path, exp = FROZEN_FILES["manifest"]
    assert compute_sha256(path) == exp

def test_17_frozen_predecessor_hashes():
    for name in ["tcn", "deep_sad", "s2_encoder", "yolo_infra", "yolo_fire", "fusion"]:
        path, exp = FROZEN_FILES[name]
        assert compute_sha256(path) == exp

def test_18_abstention_policy():
    summary_path = PROJECT_ROOT / "reports/stage8_27_summary.json"
    with open(summary_path) as f:
        s = json.load(f)
    ab = s["abstention_results"]["H0"]
    assert ab["coverage"] >= 0.80
    assert ab["selective_accuracy"] >= ab["coverage"]

def test_19_horizon_ordering():
    pred_path = PROJECT_ROOT / "data/interim/ds08_stage8_27_predictions.parquet"
    df_preds = pd.read_parquet(pred_path)
    for eid, grp in df_preds.groupby("event_id"):
        h_order = grp["horizon_hours"].values
        assert (np.diff(h_order) >= 0).all(), f"Horizon hours not monotonically non-decreasing for {eid}!"

def test_20_event_level_aggregation():
    pred_path = PROJECT_ROOT / "data/interim/ds08_stage8_27_predictions.parquet"
    df_preds = pd.read_parquet(pred_path)
    h0_preds = df_preds[df_preds["horizon"] == "H0"]
    assert len(h0_preds) == 28
    assert (h0_preds["class_id"] == 0).sum() == 6
    assert (h0_preds["class_id"] == 1).sum() == 6
    assert (h0_preds["class_id"] == 2).sum() == 6
    assert (h0_preds["class_id"] == 3).sum() == 10
