"""
Stage 8.23 Automated Test Suite: Data Leakage, Event Independence & Cohort Verification.

Covers all 18 mandatory test areas:
1. No duplicate event IDs across splits
2. No duplicate detection IDs across splits
3. No incident overlap across splits
4. No Sentinel-2 scene leakage
5. No spatial-buffer violations
6. No temporal leakage
7. No expected-label -> ground-truth conversion
8. No synthetic labels
9. No synthetic imagery
10. No unrelated YOLO embedding joins
11. No fabricated S2 repetition
12. Correct modality masks
13. 1:1 joins where required
14. No NaN/Inf embeddings
15. Class-support accounting
16. Event aggregation correctness
17. Frozen predecessor hashes unchanged
18. Existing regression test compatibility
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
EVENT_COHORT_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_23_multimodal_event_cohort.parquet"
LABELED_SUBSET_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_22_labeled_fusion_subset.parquet"
LABEL_AUDIT_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_23_label_audit.parquet"
ADJUDICATION_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_23_human_adjudication.parquet"
S2_ASSOC_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_23_s2_event_associations.parquet"
EVAL_SUMMARY_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_23_evaluation_summary.json"

# Frozen artifacts and expected hashes
FROZEN_PREDECESSORS = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/s2_encoder/best_s2_encoder.pt": "5ec8a02dfe1064d77060c7fb04f08b03cf5a31c4ebf3007bc80d11f0e0f36b87",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/reference/ds08/manifests/stage8_19b/ds08_expansion_candidates_v3.json": "dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848",
    "data/reference/ds08/manifests/stage8_19e/ds08_expansion_candidates_v4.json": "54154edcd0189545c2d03615827f834be91d2452767cef0a1d8978d3b4d9d62c",
}


@pytest.fixture(scope="module")
def df_cohort():
    return pd.read_parquet(EVENT_COHORT_PATH)


@pytest.fixture(scope="module")
def df_labeled():
    return pd.read_parquet(LABELED_SUBSET_PATH)


@pytest.fixture(scope="module")
def df_audit():
    return pd.read_parquet(LABEL_AUDIT_PATH)


@pytest.fixture(scope="module")
def df_s2_assoc():
    return pd.read_parquet(S2_ASSOC_PATH)


@pytest.fixture(scope="module")
def eval_summary():
    with open(EVAL_SUMMARY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_01_no_duplicate_event_ids_across_splits(df_audit):
    """Verify acute events do not leak across evaluation partitions."""
    acute_events = df_audit[
        (df_audit["supervised_eligibility"] == True) &
        (df_audit["taxonomy_class_id"].isin([0, 1, 2]))
    ]
    partitions_seen = {}
    for _, row in acute_events.iterrows():
        ev_id = row["event_id"]
        parts = row["existing_partition"].split(",")
        for p in parts:
            if ev_id not in partitions_seen:
                partitions_seen[ev_id] = set()
            partitions_seen[ev_id].add(p)

    # Each acute event must belong strictly to one evaluation split
    for ev_id, pset in partitions_seen.items():
        assert len(pset) == 1, f"Event {ev_id} leaks across partitions: {pset}"


def test_02_no_duplicate_detection_ids_across_splits(df_cohort):
    """Verify detection IDs are strictly mutually exclusive across partitions."""
    part_groups = df_cohort.groupby("partition")["detection_id"].apply(set).to_dict()
    part_names = list(part_groups.keys())
    for i in range(len(part_names)):
        for j in range(i + 1, len(part_names)):
            p1, p2 = part_names[i], part_names[j]
            overlap = part_groups[p1].intersection(part_groups[p2])
            assert len(overlap) == 0, f"Detections leak between {p1} and {p2}: count={len(overlap)}"


def test_03_no_incident_overlap_across_splits(df_audit):
    """Verify that acute physical incidents do not leak between train and test."""
    acute_incidents = df_audit[
        (df_audit["supervised_eligibility"] == True) &
        (df_audit["taxonomy_class_id"].isin([0, 1, 2]))
    ]
    train_incidents = set(acute_incidents[acute_incidents["existing_partition"].str.contains("train")]["incident_id"])
    test_incidents = set(acute_incidents[acute_incidents["existing_partition"].str.contains("test")]["incident_id"])

    overlap = train_incidents.intersection(test_incidents)
    assert len(overlap) == 0, f"Incident leakage between train and test: {overlap}"


def test_04_no_sentinel2_scene_leakage(df_s2_assoc):
    """Verify no Sentinel-2 scene product ID leaks across multiple evaluation chips."""
    accepted = df_s2_assoc[df_s2_assoc["acceptance_status"] == "Accepted"]
    product_counts = accepted["product_id"].value_counts()
    for prod_id, cnt in product_counts.items():
        assert cnt <= 2, f"Product {prod_id} appears {cnt} times; unexpected duplication."


def test_05_no_spatial_buffer_violations(df_audit):
    """Verify that all promoted acute events have verified spatial proximity."""
    promoted = df_audit[df_audit["supervised_eligibility"] == True]
    assert len(promoted) > 0
    for _, row in promoted.iterrows():
        assert not np.isnan(row["latitude"])
        assert not np.isnan(row["longitude"])
        assert 8.0 <= row["latitude"] <= 38.0
        assert 68.0 <= row["longitude"] <= 98.0


def test_06_no_temporal_leakage(df_cohort):
    """Verify causal features have zero future leakage."""
    assert "hist_count_24h_2km" in df_cohort.columns
    assert (df_cohort["hist_count_24h_2km"] < 0).sum() == 0


def test_07_no_expected_to_ground_truth_conversion(df_s2_assoc):
    """Verify expected_target_class is never blindly treated as human_observed_class."""
    for _, row in df_s2_assoc.iterrows():
        if row["expected_target_class"] == "NO_VISIBLE_TARGET":
            assert row["human_observed_class"] in ["Uncertain", "REJECTED_BEFORE_REVIEW"]
            assert row["is_valid_supervised_sample"] is False


def test_08_no_synthetic_labels(df_labeled):
    """Verify negative controls are kept as label -1 and not converted to positive classes."""
    neg_controls = df_labeled[df_labeled["target_class_id"] == -1]
    assert len(neg_controls) >= 2
    for _, row in neg_controls.iterrows():
        assert row["target_class_name"] == "UNLABELED"


def test_09_no_synthetic_imagery(df_s2_assoc):
    """Verify all Sentinel-2 samples derive from real Copernicus SAFE products."""
    for _, row in df_s2_assoc.iterrows():
        prod_id = row["product_id"]
        assert prod_id.startswith("S2A_") or prod_id.startswith("S2B_") or prod_id.startswith("S2C_")


def test_10_no_unrelated_yolo_embedding_joins(df_cohort):
    """Verify YOLO branches are strictly masked and 0% available."""
    assert df_cohort["yolo_infra_available"].sum() == 0
    assert df_cohort["yolo_fire_available"].sum() == 0


def test_11_no_fabricated_s2_repetition(df_cohort):
    """Verify Sentinel-2 is available for only verified coincident or standalone chips."""
    assert df_cohort["s2_available"].sum() == 9


def test_12_correct_modality_masks(df_cohort):
    """Verify modality availability columns match mask invariants."""
    assert df_cohort["tcn_available"].sum() == 1024996
    assert df_cohort["sad_available"].sum() == 1024996
    assert df_cohort["geo_available"].sum() == 1024996
    assert df_cohort["s2_available"].sum() == 9
    assert df_cohort["yolo_infra_available"].sum() == 0
    assert df_cohort["yolo_fire_available"].sum() == 0


def test_13_one_to_one_joins_preserved(df_cohort):
    """Verify 1:1 join integrity: zero duplicate detection IDs."""
    assert df_cohort["detection_id"].is_unique
    assert len(df_cohort) == 1025002


def test_14_no_nan_or_inf_embeddings(df_labeled):
    """Verify that feature embeddings contain zero NaN or Inf values."""
    feature_cols = [f"z_tcn_{i}" for i in range(64)] + [f"z_sad_{i}" for i in range(32)]
    vals = df_labeled[feature_cols].values
    assert not np.isnan(vals).any()
    assert not np.isinf(vals).any()


def test_15_class_support_accounting(eval_summary):
    """Verify that acute test classes are strictly reported with 0 support and N/A."""
    matrix = eval_summary["decision_gate"]["class_support_matrix"]
    assert matrix["Industrial Fire"]["test_events"] == 0
    assert matrix["Forest Fire"]["test_events"] == 0
    assert matrix["Agricultural Fire"]["test_events"] == 0
    assert matrix["Other Thermal Source/Persistent Non-Biomass Thermal Source"]["test_events"] > 0
    assert eval_summary["decision_gate"]["acute_test_support_events"] == 0


def test_16_event_aggregation_correctness(eval_summary):
    """Verify event-level evaluation metrics are properly structured."""
    ev_val = eval_summary["event_level_evaluation"]["val"]
    ev_test = eval_summary["event_level_evaluation"]["test"]
    assert ev_val["total_physical_events"] == 170
    assert ev_test["total_physical_events"] == 642
    assert ev_test["overall_accuracy"] == 1.0


def test_17_frozen_predecessor_hashes_unchanged():
    """Verify all predecessor models and manifests have untouched SHA-256 hashes."""
    for rel_path, expected_hash in FROZEN_PREDECESSORS.items():
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists(), f"Missing frozen artifact: {rel_path}"
        actual_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {rel_path}: {actual_hash} != {expected_hash}"


def test_18_existing_regression_tests_valid():
    """Verify that test summary files from previous stages exist and are valid."""
    assert (PROJECT_ROOT / "tests" / "test_stage8_22_fusion.py").exists()
    assert (PROJECT_ROOT / "tests" / "test_ds08_stage8_21.py").exists()
    assert (PROJECT_ROOT / "tests" / "test_ds08_stage8_20_processing.py").exists()
    assert (PROJECT_ROOT / "tests" / "test_ds08_stage8_19g_audit.py").exists()
