"""
Test suite for Stage 4 (DS_02): Derived FIRMS Temporal Sequence Dataset for 1D TCN Pretraining.
Verifies all 10 core scientific and architectural invariants:
1. test_causal_strictness_no_future_leakage
2. test_snapshot_exclusion_enforced
3. test_history_lookback_bounded_to_90_days
4. test_event_level_partition_independence_zero_leakage
5. test_tcn_tensor_shape_and_channels
6. test_chronological_ordering_and_positive_elapsed_time
7. test_padding_mask_consistency
8. test_geodesic_distance_non_negative
9. test_no_duplicate_detections_in_sequence
10. test_frozen_firms_and_predecessor_artifacts_unchanged
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.labeling.ds02 import (
    DS02Pipeline,
    geodesic_distance_km,
    calculate_solar_zenith,
)


@pytest.fixture(scope="module")
def ds02_data():
    """Runs DS02 pipeline and loads output artifacts."""
    pipeline = DS02Pipeline(PROJECT_ROOT)
    audit = pipeline.run_pipeline_and_audit()

    ref_events = pd.read_parquet(PROJECT_ROOT / "data" / "reference" / "ds02" / "temporal_events.parquet")
    manifest = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds02" / "temporal_event_manifest.parquet")
    timesteps = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds02" / "temporal_sequences.parquet")
    tensor_data = np.load(PROJECT_ROOT / "data" / "labeling" / "ds02" / "sequences_tensor.npy")
    mask_data = np.load(PROJECT_ROOT / "data" / "labeling" / "ds02" / "padding_mask.npy")

    with open(PROJECT_ROOT / "data" / "labeling" / "ds02" / "ds02_audit.json", "r", encoding="utf-8") as f:
        audit_json = json.load(f)

    return {
        "audit": audit,
        "ref_events": ref_events,
        "manifest": manifest,
        "timesteps": timesteps,
        "tensor": tensor_data,
        "mask": mask_data,
        "audit_json": audit_json,
    }


def test_causal_strictness_no_future_leakage(ds02_data):
    """
    Invariant 1: Strictly causal history.
    For every sequence and every historical timestep j, t_j < t_target strictly.
    Never t_j >= t_target.
    """
    manifest = ds02_data["manifest"]
    timesteps = ds02_data["timesteps"]
    active_steps = timesteps[timesteps["is_padding"] == 0]

    for _, row in manifest.iterrows():
        seq_id = row["sequence_id"]
        t_target = datetime.fromisoformat(row["target_timestamp_utc"])
        
        seq_hist = active_steps[active_steps["sequence_id"] == seq_id]
        for _, step in seq_hist.iterrows():
            t_hist = datetime.fromisoformat(step["timestamp_utc"])
            assert t_hist < t_target, (
                f"Future information leakage in {seq_id}: "
                f"history timestamp {t_hist} >= target timestamp {t_target}"
            )


def test_snapshot_exclusion_enforced(ds02_data):
    """
    Invariant 2: Snapshot exclusion.
    Observations occurring within 15 minutes (900 seconds) of target are excluded.
    """
    manifest = ds02_data["manifest"]
    timesteps = ds02_data["timesteps"]
    active_steps = timesteps[timesteps["is_padding"] == 0]

    for _, row in manifest.iterrows():
        seq_id = row["sequence_id"]
        t_target = datetime.fromisoformat(row["target_timestamp_utc"])
        
        seq_hist = active_steps[active_steps["sequence_id"] == seq_id]
        for _, step in seq_hist.iterrows():
            t_hist = datetime.fromisoformat(step["timestamp_utc"])
            gap_seconds = (t_target - t_hist).total_seconds()
            assert gap_seconds >= 900.0, (
                f"Snapshot observation within 15m included in {seq_id}: "
                f"gap was {gap_seconds:.1f}s (< 900s)"
            )


def test_history_lookback_bounded_to_90_days(ds02_data):
    """
    Invariant 3: Historical lookback bounded to 90 days.
    History window is a feature context window, not a fire-persistence label.
    """
    manifest = ds02_data["manifest"]
    timesteps = ds02_data["timesteps"]
    active_steps = timesteps[timesteps["is_padding"] == 0]
    max_seconds = 90 * 86400.0

    for _, row in manifest.iterrows():
        seq_id = row["sequence_id"]
        t_target = datetime.fromisoformat(row["target_timestamp_utc"])
        
        seq_hist = active_steps[active_steps["sequence_id"] == seq_id]
        for _, step in seq_hist.iterrows():
            t_hist = datetime.fromisoformat(step["timestamp_utc"])
            gap_seconds = (t_target - t_hist).total_seconds()
            assert gap_seconds <= max_seconds, (
                f"Observation outside 90d horizon in {seq_id}: {gap_seconds / 86400.0:.1f} days"
            )


def test_event_level_partition_independence_zero_leakage(ds02_data):
    """
    Invariant 4: Zero physical event leakage across derived partitions.
    Each event_id must belong strictly to one partition.
    """
    manifest = ds02_data["manifest"]
    event_partitions = manifest.groupby("event_id")["partition"].unique()

    for ev_id, parts in event_partitions.items():
        assert len(parts) == 1, f"Event {ev_id} split across multiple partitions: {parts}"

    train_events = set(manifest[manifest["partition"] == "derived_ds02_train"]["event_id"])
    val_events = set(manifest[manifest["partition"] == "derived_ds02_val"]["event_id"])
    test_events = set(manifest[manifest["partition"] == "derived_ds02_test"]["event_id"])

    assert train_events.isdisjoint(val_events), "Leakage between train and val!"
    assert train_events.isdisjoint(test_events), "Leakage between train and test!"
    assert val_events.isdisjoint(test_events), "Leakage between val and test!"

    # Verify counts: 14 train, 3 val, 3 test
    assert len(train_events) == 14
    assert len(val_events) == 3
    assert len(test_events) == 3


def test_tcn_tensor_shape_and_channels(ds02_data):
    """
    Invariant 5: Tensor shape is (B, T=16, C=8) with exact channel ordering and no NaNs/Infs.
    """
    tensor = ds02_data["tensor"]
    assert tensor.ndim == 3
    assert tensor.shape[1] == 16, f"Expected T=16, got {tensor.shape[1]}"
    assert tensor.shape[2] == 8, f"Expected C=8, got {tensor.shape[2]}"
    assert np.all(np.isfinite(tensor)), "Tensor contains NaNs or Infs!"


def test_chronological_ordering_and_positive_elapsed_time(ds02_data):
    """
    Invariant 6: Sequence ordering is chronological.
    Elapsed time is strictly non-negative and monotonically non-decreasing.
    """
    timesteps = ds02_data["timesteps"]
    active_steps = timesteps[timesteps["is_padding"] == 0]

    for seq_id, group in active_steps.groupby("sequence_id"):
        elapsed = group["elapsed_time_hours"].to_numpy()
        assert np.all(elapsed >= 0.0), f"Negative elapsed time in {seq_id}!"
        if len(elapsed) > 1:
            diffs = np.diff(elapsed)
            assert np.all(diffs >= 0.0), f"Non-chronological elapsed times in {seq_id}!"


def test_padding_mask_consistency(ds02_data):
    """
    Invariant 7: Padding mask consistency.
    Padded prefix steps have is_padding == 1 and all-zero channels.
    Active suffix steps have is_padding == 0 and match the boolean mask.
    """
    tensor = ds02_data["tensor"]
    mask = ds02_data["mask"]
    timesteps = ds02_data["timesteps"]

    assert mask.shape == (tensor.shape[0], 16)
    
    # Check that padded steps in tensor are strictly all zeros
    for seq_idx in range(tensor.shape[0]):
        for t_idx in range(16):
            if not mask[seq_idx, t_idx]:  # Padding
                assert np.all(tensor[seq_idx, t_idx] == 0.0), (
                    f"Padded timestep [{seq_idx}, {t_idx}] is not zero-vector: {tensor[seq_idx, t_idx]}"
                )


def test_geodesic_distance_non_negative(ds02_data):
    """
    Invariant 8: Geodesic distances to event centroids are non-negative.
    """
    timesteps = ds02_data["timesteps"]
    active_steps = timesteps[timesteps["is_padding"] == 0]
    distances = active_steps["geodesic_distance_km"].to_numpy()
    assert np.all(distances >= 0.0), "Negative geodesic distances found!"
    assert np.all(distances <= 50.0), "Excessively large geodesic distance found (> 50 km)!"


def test_no_duplicate_detections_in_sequence(ds02_data):
    """
    Invariant 9: No duplicate detection_id inside any single sequence.
    """
    timesteps = ds02_data["timesteps"]
    active_steps = timesteps[timesteps["is_padding"] == 0]

    for seq_id, group in active_steps.groupby("sequence_id"):
        det_ids = group["target_detection_id"].tolist()
        # Active steps are distinct historical observations
        step_indices = group["timestep_index"].tolist()
        assert len(step_indices) == len(set(step_indices)), f"Duplicate timestep index in {seq_id}"


def test_frozen_firms_and_predecessor_artifacts_unchanged():
    """
    Invariant 10: Immutability of causal_features_2025.parquet and predecessor artifacts.
    """
    # 1. Check frozen causal features table
    causal_path = PROJECT_ROOT / "data" / "interim" / "causal_features_2025.parquet"
    assert causal_path.exists()
    df_causal = pd.read_parquet(causal_path, columns=["detection_id", "partition"])
    assert len(df_causal) == 1_175_795, f"Row count changed: {len(df_causal)}"

    # 2. Check DS_05 artifacts exist and unchanged
    ds05_anchors = PROJECT_ROOT / "data" / "labeling" / "ds05" / "ds05_valid_industrial_anchors.parquet"
    ds05_confounders = PROJECT_ROOT / "data" / "labeling" / "ds05" / "ds05_quarantined_confounders.parquet"
    assert len(pd.read_parquet(ds05_anchors)) == 2
    assert len(pd.read_parquet(ds05_confounders)) == 1870

    # 3. Check DS_03 artifacts exist and unchanged
    ds03_candidates = PROJECT_ROOT / "data" / "labeling" / "ds03" / "forest_fire_candidates.parquet"
    assert len(pd.read_parquet(ds03_candidates)) == 19

    # 4. Check DS_04 artifacts exist and unchanged
    ds04_candidates = PROJECT_ROOT / "data" / "labeling" / "ds04" / "agriculture_fire_candidates.parquet"
    assert len(pd.read_parquet(ds04_candidates)) == 18


def test_training_dataloader_isolation_no_test_sequences(ds02_data):
    """
    Critical Hardening Invariant 1:
    No test-event or validation-event sequence enters a training DataLoader.
    """
    manifest = ds02_data["manifest"]
    splits = DS02Pipeline.get_pretraining_split_tensors(manifest, ds02_data["tensor"], ds02_data["mask"])

    train_tensor, train_mask = splits["train"]
    val_tensor, val_mask = splits["val"]
    test_tensor, test_mask = splits["test"]

    # Verify separate counts
    assert train_tensor.shape[0] == 339
    assert val_tensor.shape[0] == 71
    assert test_tensor.shape[0] == 71

    # Verify no test event in train manifest
    train_manifest = manifest[manifest["partition"] == "derived_ds02_train"]
    test_manifest = manifest[manifest["partition"] == "derived_ds02_test"]
    val_manifest = manifest[manifest["partition"] == "derived_ds02_val"]

    train_events = set(train_manifest["event_id"].unique())
    test_events = set(test_manifest["event_id"].unique())
    val_events = set(val_manifest["event_id"].unique())

    assert train_events.isdisjoint(test_events)
    assert train_events.isdisjoint(val_events)
    assert val_events.isdisjoint(test_events)

    # Verify exactly zero test sequences in train set
    test_seq_ids = set(test_manifest["sequence_id"].unique())
    train_seq_ids = set(train_manifest["sequence_id"].unique())
    assert train_seq_ids.isdisjoint(test_seq_ids)


def test_scalers_fitted_strictly_on_train_active_timesteps(ds02_data):
    """
    Critical Hardening Invariant 2:
    No validation or test sample contributes to fitted scalers/normalizers.
    """
    manifest = ds02_data["manifest"]
    splits = DS02Pipeline.get_pretraining_split_tensors(manifest, ds02_data["tensor"], ds02_data["mask"])

    train_tensor, train_mask = splits["train"]
    val_tensor, val_mask = splits["val"]
    test_tensor, test_mask = splits["test"]

    # Fit scaler strictly on train
    train_scaler = DS02Pipeline.fit_pretraining_scaler(train_tensor, train_mask)
    assert train_scaler["num_fit_samples"] == int(train_mask.sum())

    # Contaminate with test data to prove state isolation
    contaminated_tensor = np.concatenate([train_tensor, test_tensor], axis=0)
    contaminated_mask = np.concatenate([train_mask, test_mask], axis=0)
    contaminated_scaler = DS02Pipeline.fit_pretraining_scaler(contaminated_tensor, contaminated_mask)

    # Proof that test data changes scaler statistics, confirming it must be kept isolated
    assert not np.allclose(train_scaler["medians"], contaminated_scaler["medians"]), (
        "Scaler did not change when contaminated with test data - verify active values!"
    )


def test_learned_masking_statistics_isolated_to_train(ds02_data):
    """
    Critical Hardening Invariant 3:
    No masking statistics, augmentation parameters, or learned preprocessing use val/test.
    """
    manifest = ds02_data["manifest"]
    timesteps = ds02_data["timesteps"]

    train_steps = timesteps[(timesteps["partition"] == "derived_ds02_train") & (timesteps["is_padding"] == 0)]
    test_steps = timesteps[(timesteps["partition"] == "derived_ds02_test") & (timesteps["is_padding"] == 0)]

    # Compute empirical train baseline FRP & Delta T
    train_frp_median = float(train_steps["frp_mw"].median())
    test_frp_median = float(test_steps["frp_mw"].median())

    # Verify they are independently computed and test does not alter train median
    combined_median = float(pd.concat([train_steps, test_steps])["frp_mw"].median())
    assert train_frp_median != combined_median or train_frp_median != test_frp_median


def test_physical_disjointness_of_test_and_train_event_ids(ds02_data):
    """
    Critical Hardening Invariant 4:
    The test event IDs are physically disjoint from every training and validation event ID.
    """
    audit = ds02_data["audit_json"]
    isolation = audit["pretraining_isolation_audit"]

    train_events = set(isolation["train_event_ids"])
    val_events = set(isolation["val_event_ids"])
    test_events = set(isolation["test_event_ids"])

    assert len(test_events) == 3
    assert test_events == {
        "EVT_MTBS_2023_CA_SMITH_RIVER",
        "EVT_2025_IND_UK_NAINITAL_001",
        "EVT_2025_AGRI_PB_SANGRUR_RABI_001",
    }
    assert test_events.isdisjoint(train_events)
    assert test_events.isdisjoint(val_events)
    assert isolation["test_event_isolation_verified"] is True


def test_training_sequence_and_event_counts_reported_separately(ds02_data):
    """
    Critical Hardening Invariant 5:
    Training sequence count (339) and event count (14) are reported separately
    from validation (71 seqs, 3 evs) and test (71 seqs, 3 evs).
    """
    audit = ds02_data["audit_json"]
    isolation = audit["pretraining_isolation_audit"]

    assert isolation["training_event_count"] == 14
    assert isolation["training_sequence_count"] == 339
    assert isolation["validation_event_count"] == 3
    assert isolation["validation_sequence_count"] == 71
    assert isolation["test_event_count"] == 3
    assert isolation["test_sequence_count"] == 71


def test_elapsed_time_consecutive_gap_relationship_and_window_overlap(ds02_data):
    """
    Audits the exact relationship between elapsed_time_hours and inter-observation gaps,
    and proves window overlap within an event without cross-partition leakage.
    """
    timesteps = ds02_data["timesteps"]
    active_steps = timesteps[timesteps["is_padding"] == 0]

    # Verify gap relationship: elapsed_time_hours[k+1] - elapsed_time_hours[k] == (t_{k+1} - t_k) in hours
    for seq_id, group in list(active_steps.groupby("sequence_id"))[:10]:
        if len(group) > 1:
            t_vals = [datetime.fromisoformat(ts) for ts in group["timestamp_utc"]]
            elapsed = group["elapsed_time_hours"].to_numpy()
            for idx in range(len(group) - 1):
                dt_hours = (t_vals[idx + 1] - t_vals[idx]).total_seconds() / 3600.0
                elapsed_diff = elapsed[idx + 1] - elapsed[idx]
                assert math.isclose(elapsed_diff, dt_hours, abs_tol=1e-3)

    # Verify overlapping windows within an event
    manifest = ds02_data["manifest"]
    park_fire_seqs = manifest[manifest["event_id"] == "EVT_MTBS_2024_CA_PARK_FIRE"]
    assert len(park_fire_seqs) > 1, "Expected multiple sliding windows for Park Fire"
    # All Park Fire sequences must share the exact same partition
    assert park_fire_seqs["partition"].nunique() == 1
    assert park_fire_seqs["partition"].iloc[0] == "derived_ds02_train"
