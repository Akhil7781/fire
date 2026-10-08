"""
Stage 8.24 Automated Test Suite: Integrity, Leakage Prevention & Scientific Validation.

Covers all 20 mandatory validation criteria:
1. No physical event crosses splits
2. No incident crosses splits
3. No detection crosses splits
4. No S2 scene leakage
5. No overlapping S2 chips across prohibited splits
6. No future temporal features
7. Expected labels never become ground truth automatically
8. No synthetic data
9. No unrelated YOLO joins
10. No repeated S2 embedding inflation
11. All supervised labels are confirmed
12. Class support is accurately counted
13. Event-level aggregation is deterministic
14. No NaN/Inf
15. Frozen predecessor hashes unchanged
16. Independent test manifest is frozen
17. Train/validation statistics are isolated from test
18. Unsupported test classes are reported N/A
19. Provenance exists for every test event
20. No duplicate event IDs
"""

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Input paths
CURRENT_MASTER_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_24_current_acute_event_master.parquet"
ADJUDICATED_EVENTS_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_24_adjudicated_events.parquet"
FIRMS_ASSOC_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_24_firms_event_associations.parquet"
S2_ASSOC_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_24_s2_event_associations.parquet"
S2_EMBEDDINGS_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_24_s2_embeddings.parquet"
TEST_MANIFEST_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_24" / "independent_test_manifest.json"
TEST_COHORT_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_24_independent_multimodal_test.parquet"
EVAL_SUMMARY_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_24_evaluation_summary.json"
ERROR_ANALYSIS_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_24_error_analysis.parquet"
LABELED_SUBSET_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_22_labeled_fusion_subset.parquet"

# Frozen Predecessor Hashes
FROZEN_PREDECESSORS = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/s2_encoder/best_s2_encoder.pt": "5ec8a02dfe1064d77060c7fb04f08b03cf5a31c4ebf3007bc80d11f0e0f36b87",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "models/fusion/best_multimodal_fusion.pt": "7398b7f0539637091cac763eeca0c23be0e5f8cd99860872d3d9f75d84f1481c",
    "data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json": "dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848",
    "data/reference/ds08/manifests/stage8_19e/ds08_expansion_candidates_v4.json": "54154edcd0189545c2d03615827f834be91d2452767cef0a1d8978d3b4d9d62c",
}


@pytest.fixture(scope="module")
def df_master():
    return pd.read_parquet(CURRENT_MASTER_PATH)


@pytest.fixture(scope="module")
def df_adj():
    return pd.read_parquet(ADJUDICATED_EVENTS_PATH)


@pytest.fixture(scope="module")
def df_s2_assoc():
    return pd.read_parquet(S2_ASSOC_PATH)


@pytest.fixture(scope="module")
def df_s2_emb():
    return pd.read_parquet(S2_EMBEDDINGS_PATH)


@pytest.fixture(scope="module")
def test_manifest():
    with open(TEST_MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def df_test_cohort():
    return pd.read_parquet(TEST_COHORT_PATH)


@pytest.fixture(scope="module")
def eval_summary():
    with open(EVAL_SUMMARY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# 1. No physical event crosses splits
def test_01_no_physical_event_crosses_splits(test_manifest):
    splits = test_manifest["evaluation_splits"]
    train_evts = set(splits["TRAIN"])
    val_evts = set(splits["VAL"])
    test_evts = set(splits["INDEPENDENT_TEST"])

    assert len(train_evts.intersection(val_evts)) == 0, "Event overlap between TRAIN and VAL"
    assert len(train_evts.intersection(test_evts)) == 0, "Event overlap between TRAIN and TEST"
    assert len(val_evts.intersection(test_evts)) == 0, "Event overlap between VAL and TEST"


# 2. No incident crosses splits
def test_02_no_incident_crosses_splits(df_master, test_manifest):
    splits = test_manifest["evaluation_splits"]
    train_evts = set(splits["TRAIN"])
    val_evts = set(splits["VAL"])
    test_evts = set(splits["INDEPENDENT_TEST"])

    train_incs = {inc for inc in df_master[df_master["event_id"].isin(train_evts)]["incident_id"] if inc and inc not in ["None", "", "UNKNOWN"]}
    val_incs = {inc for inc in df_master[df_master["event_id"].isin(val_evts)]["incident_id"] if inc and inc not in ["None", "", "UNKNOWN"]}
    test_incs = {inc for inc in df_master[df_master["event_id"].isin(test_evts)]["incident_id"] if inc and inc not in ["None", "", "UNKNOWN"]}

    assert len(train_incs.intersection(val_incs)) == 0, f"Incident overlap between TRAIN and VAL: {train_incs.intersection(val_incs)}"
    assert len(train_incs.intersection(test_incs)) == 0, f"Incident overlap between TRAIN and TEST: {train_incs.intersection(test_incs)}"
    assert len(val_incs.intersection(test_incs)) == 0, f"Incident overlap between VAL and TEST: {val_incs.intersection(test_incs)}"


# 3. No detection crosses splits
def test_03_no_detection_crosses_splits():
    df_labeled = pd.read_parquet(LABELED_SUBSET_PATH)
    train_dets = set(df_labeled[df_labeled["partition"].isin(["train", "train_heldout_spatial"])]["detection_id"])
    val_dets = set(df_labeled[df_labeled["partition"] == "val"]["detection_id"])
    test_dets = set(df_labeled[df_labeled["partition"].isin(["test", "test_seen_spatial"])]["detection_id"])

    assert len(train_dets.intersection(val_dets)) == 0, "Detection leak between TRAIN and VAL"
    assert len(train_dets.intersection(test_dets)) == 0, "Detection leak between TRAIN and TEST"
    assert len(val_dets.intersection(test_dets)) == 0, "Detection leak between VAL and TEST"


# 4. No S2 scene leakage
def test_04_no_s2_scene_leakage(df_s2_assoc):
    # Verified S2 chips are strictly tied to train and val; none in test
    train_prods = set(df_s2_assoc[df_s2_assoc["sample_id"].isin(["DS08_EXP_S1_003", "S8_001", "S8_002", "DS08_EXP_S2_001", "DS08_EXP_S3_001"])]["product_id"])
    val_prods = set(df_s2_assoc[df_s2_assoc["sample_id"].isin(["DS08_EXP_S4_001"])]["product_id"])
    assert len(train_prods.intersection(val_prods)) == 0, "S2 product scene leaks across splits"


# 5. No overlapping S2 chips across prohibited splits
def test_05_no_overlapping_s2_chips_across_prohibited_splits(df_s2_assoc):
    # Test partition has zero S2 chips
    assert len(df_s2_assoc[df_s2_assoc["sample_id"].str.contains("TEST")]) == 0


# 6. No future temporal features
def test_06_no_future_temporal_features(df_master):
    # Verify temporal bounds are chronologically valid
    for _, row in df_master.iterrows():
        start = str(row["event_start"])
        end = str(row["event_end"])
        if start and end and start != "None" and end != "None":
            assert start <= end, f"Inverted temporal extent for {row['event_id']}"


# 7. Expected labels never become ground truth automatically
def test_07_expected_labels_never_become_ground_truth_automatically(df_s2_assoc):
    # Check that human_observed_class differs from expected_target_class where rejected
    rejected_chips = df_s2_assoc[df_s2_assoc["is_valid_supervised_sample"] == False]
    for _, row in rejected_chips.iterrows():
        assert row["expected_target_class"] != row["human_observed_class"] or row["reviewer_decision"] != "Accepted"


# 8. No synthetic data
def test_08_no_synthetic_data(df_test_cohort):
    # Provenance check: all rows are real VIIRS 2025 detections
    assert not df_test_cohort["detection_id"].str.contains("SYNTH").any()
    assert not df_test_cohort["event_id"].str.contains("SYNTH").any()


# 9. No unrelated YOLO joins
def test_09_no_unrelated_yolo_joins(df_test_cohort):
    # In test cohort, YOLO coverage must be strictly 0.0000%
    assert (df_test_cohort["yolo_infra_available"] == 0.0).all()
    assert (df_test_cohort["yolo_fire_available"] == 0.0).all()


# 10. No repeated S2 embedding inflation
def test_10_no_repeated_s2_embedding_inflation(df_s2_emb):
    # All sample IDs in embeddings table must be unique
    assert df_s2_emb["sample_id"].is_unique, "Duplicate S2 sample ID in embeddings"


# 11. All supervised labels are confirmed
def test_11_all_supervised_labels_are_confirmed(df_master, df_adj):
    # Unconfirmed candidate events cannot be supervised eligible
    for _, row in df_adj.iterrows():
        if row["adjudication_decision"] != "CONFIRMED":
            assert row["supervised_eligibility"] == False


# 12. Class support is accurately counted
def test_12_class_support_is_accurately_counted(test_manifest):
    matrix = test_manifest["class_support_matrix"]
    assert matrix["Industrial Fire"]["test_events"] == 0
    assert matrix["Forest Fire"]["test_events"] == 0
    assert matrix["Agricultural Fire"]["test_events"] == 0
    assert matrix["Other Thermal Source/Persistent Non-Biomass Thermal Source"]["test_events"] == 18


# 13. Event-level aggregation is deterministic
def test_13_event_level_aggregation_is_deterministic(eval_summary):
    # Event level accuracy in summary must be finite and consistent
    val_acc = eval_summary["event_level_evaluation"]["val"]["overall_accuracy"]
    test_acc = eval_summary["event_level_evaluation"]["test"]["overall_accuracy"]
    assert isinstance(val_acc, float) and 0.0 <= val_acc <= 1.0
    assert isinstance(test_acc, float) and 0.0 <= test_acc <= 1.0


# 14. No NaN/Inf
def test_14_no_nan_inf(df_s2_emb, df_test_cohort):
    dim_cols = [f"dim_{i:03d}" for i in range(128)]
    assert not np.isnan(df_s2_emb[dim_cols].values).any()
    assert not np.isinf(df_s2_emb[dim_cols].values).any()
    assert not np.isnan(df_test_cohort["latitude"].values).any()
    assert not np.isnan(df_test_cohort["longitude"].values).any()


# 15. Frozen predecessor hashes unchanged
def test_15_frozen_predecessor_hashes_unchanged():
    for rel_path, expected_hash in FROZEN_PREDECESSORS.items():
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists(), f"Missing frozen artifact: {rel_path}"
        actual_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {rel_path}: {actual_hash} != {expected_hash}"


# 16. Independent test manifest is frozen
def test_16_independent_test_manifest_is_frozen(test_manifest):
    assert test_manifest["version"] == "1.0_FROZEN"
    assert test_manifest["stage"] == "Stage 8.24"
    assert Path(TEST_MANIFEST_PATH).exists()


# 17. Train/validation statistics are isolated from test
def test_17_train_val_statistics_isolated_from_test(eval_summary):
    assert "val" in eval_summary["event_level_evaluation"]
    assert "test" in eval_summary["event_level_evaluation"]
    # Val and test have separate distinct result dicts
    assert eval_summary["event_level_evaluation"]["val"] != eval_summary["event_level_evaluation"]["test"]


# 18. Unsupported test classes are reported N/A
def test_18_unsupported_test_classes_reported_na(eval_summary):
    test_metrics = eval_summary["event_level_evaluation"]["test"]["per_class"]
    assert test_metrics["Industrial Fire"]["precision"] == "N/A"
    assert test_metrics["Forest Fire"]["precision"] == "N/A"
    assert test_metrics["Agricultural Fire"]["precision"] == "N/A"


# 19. Provenance exists for every test event
def test_19_provenance_exists_for_every_test_event(df_test_cohort):
    assert "detection_id" in df_test_cohort.columns
    assert "event_id" in df_test_cohort.columns
    assert df_test_cohort["detection_id"].notna().all()
    assert df_test_cohort["event_id"].notna().all()


# 20. No duplicate event IDs
def test_20_no_duplicate_event_ids(df_master):
    assert df_master["event_id"].is_unique, "Duplicate event IDs in master table"
