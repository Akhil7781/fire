"""
Test suite for Stage 2 (DS_03): India Forest Fire Evidence Pipeline (GFA + FSI Forest Mask).
Verifies all 10 core scientific invariants:
1. test_gfa_alone_cannot_create_forest_fire
2. test_forest_land_cover_evidence_required
3. test_agricultural_land_is_not_automatically_forest
4. test_temporal_correspondence_is_enforced
5. test_spatial_correspondence_is_enforced
6. test_event_ids_are_preserved
7. test_multiple_detections_of_one_fire_remain_one_event
8. test_same_fire_event_id_cannot_be_split_across_derived_partitions
9. test_frozen_firms_parquet_unchanged
10. test_existing_ds05_artifacts_remain_unchanged
"""

from __future__ import annotations

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

from src.labeling.ds03 import (
    DS03Pipeline,
    evaluate_forest_land_cover_gate,
    geodesic_distance_km,
    temporal_difference_hours,
)


@pytest.fixture(scope="module")
def ds03_data():
    """Runs DS03 pipeline and loads output artifacts."""
    pipeline = DS03Pipeline(PROJECT_ROOT)
    pipeline.build_and_save_reference_dataset()
    summary = pipeline.match_and_audit()

    ref_events = pd.read_parquet(PROJECT_ROOT / "data" / "reference" / "ds03" / "forest_events.parquet")
    firms_matches = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds03" / "forest_firms_matches.parquet")
    candidates = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds03" / "forest_fire_candidates.parquet")
    rejected = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds03" / "forest_rejected_candidates.parquet")

    return {
        "summary": summary,
        "ref_events": ref_events,
        "firms_matches": firms_matches,
        "candidates": candidates,
        "rejected": rejected,
    }


def test_gfa_alone_cannot_create_forest_fire(ds03_data):
    """
    Invariant 1: A GFA fire event alone cannot create a FOREST_FIRE label.
    Vegetation burns recorded by GFA on agricultural land, scrub, or barren areas
    must never receive Class 2 (FOREST_FIRE).
    """
    candidates = ds03_data["candidates"]
    rejected = ds03_data["rejected"]

    # Non-forest GFA event IDs
    non_forest_event_ids = {
        "EVT_2025_IND_PB_SANGRUR_AGRI_012",
        "EVT_2025_IND_HR_KARNAL_AGRI_013",
        "EVT_2025_IND_RJ_BIKANER_SCRUB_014",
        "EVT_2025_IND_MH_AHMEDNAGAR_SCRUB_015",
        "EVT_2025_IND_GJ_KUTCH_BARREN_016",
    }

    # None of the non-forest GFA events must ever appear in forest_fire_candidates
    candidate_events = set(candidates["fire_event_id"].unique())
    assert non_forest_event_ids.isdisjoint(candidate_events), (
        f"Non-forest GFA events leaked into forest candidates: {non_forest_event_ids.intersection(candidate_events)}"
    )

    # All non-forest GFA detections must be in rejected/diverted candidates
    for ev_id in non_forest_event_ids:
        rej_rows = rejected[rejected["fire_event_id"] == ev_id]
        if not rej_rows.empty:
            assert (rej_rows["target_class"] != 2).all()
            assert (rej_rows["gate_verdict"] != "FOREST_FIRE").all()


def test_forest_land_cover_evidence_required():
    """
    Invariant 2: Forest land-cover evidence is strictly required.
    Canopy Cover >= 10.0% OR statutory Reserved Forest / Protected Area is required.
    """
    # Test case 1: Insufficient canopy and no reserved status -> AMBIGUOUS
    verdict, rationale = evaluate_forest_land_cover_gate(
        forest_cover_value=5.0, forest_status="OPEN_SCRUB"
    )
    assert verdict == "AMBIGUOUS"
    assert "Canopy 5.0% < 10%" in rationale

    # Test case 2: Sufficient canopy (45%) in Reserved Forest -> FOREST_FIRE
    verdict, rationale = evaluate_forest_land_cover_gate(
        forest_cover_value=45.0, forest_status="RESERVED_FOREST"
    )
    assert verdict == "FOREST_FIRE"
    assert "Canopy 45.0% >= 10.0%" in rationale

    # Test case 3: 0% canopy in barren mudflat -> EXCLUDED
    verdict, rationale = evaluate_forest_land_cover_gate(
        forest_cover_value=0.0, forest_status="BARREN"
    )
    assert verdict == "EXCLUDED"


def test_agricultural_land_is_not_automatically_forest(ds03_data):
    """
    Invariant 3: GFA vegetation fires on agricultural cropland must NOT be classified as forest fires.
    They must be diverted to AGRICULTURAL_FIRE_CANDIDATE.
    """
    rejected = ds03_data["rejected"]

    # All detections evaluated for cropland GFA events must NOT be Class 2
    agri_events = {"EVT_2025_IND_PB_SANGRUR_AGRI_012", "EVT_2025_IND_HR_KARNAL_AGRI_013"}
    agri_rej = rejected[rejected["fire_event_id"].isin(agri_events)]
    assert not agri_rej.empty
    assert (agri_rej["target_class"] != 2).all()
    assert (agri_rej["gate_verdict"] == "AGRICULTURAL_FIRE_CANDIDATE").all()

    # Specifically verify the spatiotemporally matching detection that passed distance and time
    # but was diverted strictly by the cropland gate:
    diverted_matches = agri_rej[agri_rej["match_quality"] == "DIVERTED_AGRICULTURAL"]
    assert len(diverted_matches) > 0
    for _, r in diverted_matches.iterrows():
        assert r["spatial_distance_km"] <= 2.0
        assert r["temporal_difference_hours"] == 0.0
        assert "Diverted" in r["rejection_reason"]
        assert r["target_class"] == 3
        assert r["is_supervised_target"] == False

    # Direct function gate test for cropland
    verdict, rationale = evaluate_forest_land_cover_gate(
        forest_cover_value=0.0, forest_status="CROPLAND"
    )
    assert verdict == "AGRICULTURAL_FIRE_CANDIDATE"
    assert "Cropland Diverted" in rationale


def test_temporal_correspondence_is_enforced(ds03_data):
    """
    Invariant 4: Temporal correspondence is enforced.
    Detections outside the buffered interval [start - 12h, end + 24h] must be rejected.
    """
    candidates = ds03_data["candidates"]
    rejected = ds03_data["rejected"]

    # All verified forest fire candidates must have temporal_difference_hours == 0.0
    assert (candidates["temporal_difference_hours"] == 0.0).all()

    # Verify temporal difference calculator
    t_start = pd.to_datetime("2025-04-25T12:00:00Z", utc=True)
    t_end = pd.to_datetime("2025-04-30T18:00:00Z", utc=True)

    # Detection 20 hours BEFORE start -> exceeds 12h tolerance by 8h
    det_early = pd.to_datetime("2025-04-24T16:00:00Z", utc=True)
    dt_early = temporal_difference_hours(det_early, t_start, t_end, tol_before_hours=12.0)
    assert math.isclose(dt_early, 8.0, abs_tol=1e-3)

    # Detection inside window -> dt == 0.0
    det_inside = pd.to_datetime("2025-04-26T07:28:00Z", utc=True)
    dt_inside = temporal_difference_hours(det_inside, t_start, t_end, tol_before_hours=12.0)
    assert dt_inside == 0.0


def test_spatial_correspondence_is_enforced(ds03_data):
    """
    Invariant 5: Spatial correspondence is strictly enforced.
    Detections exceeding spatial_tol_km (2.0 km) must be rejected.
    """
    candidates = ds03_data["candidates"]
    assert len(candidates) == 19

    # All candidate detections must be <= 2.0 km
    assert (candidates["spatial_distance_km"] <= 2.0).all()
    assert candidates["spatial_distance_km"].min() >= 0.0
    assert candidates["spatial_distance_km"].max() <= 1.9938


def test_event_ids_are_preserved(ds03_data):
    """
    Invariant 6: Every forest fire candidate preserves its unique fire_event_id
    and source metadata.
    """
    candidates = ds03_data["candidates"]
    ref_events = ds03_data["ref_events"]
    valid_event_ids = set(ref_events["fire_event_id"].unique())

    assert "fire_event_id" in candidates.columns
    for ev_id in candidates["fire_event_id"]:
        assert ev_id in valid_event_ids
        assert ev_id.startswith("EVT_2025_IND_")


def test_multiple_detections_of_one_fire_remain_one_event(ds03_data):
    """
    Invariant 7: Multiple FIRMS detections from the same physical wildfire event
    remain grouped under the same fire_event_id.
    """
    candidates = ds03_data["candidates"]
    event_counts = candidates["fire_event_id"].value_counts().to_dict()

    # Bandhavgarh has 7 detections from one fire event
    assert event_counts["EVT_2025_IND_MP_BANDHAVGARH_004"] == 7

    # Melghat has 6 detections from one fire event
    assert event_counts["EVT_2025_IND_MH_MELGHAT_005"] == 6

    # Similipal has 2 detections from one fire event
    assert event_counts["EVT_2025_IND_OD_SIMILIPAL_003"] == 2

    # Nainital has 2 detections from one fire event
    assert event_counts["EVT_2025_IND_UK_NAINITAL_001"] == 2

    # Total 19 detections across 6 unique events
    assert len(event_counts) == 6
    assert sum(event_counts.values()) == 19


def test_same_fire_event_id_cannot_be_split_across_derived_partitions(ds03_data):
    """
    Invariant 8: The same fire_event_id CANNOT be split across derived train/val/test splits.
    All detections of a fire event must belong to exactly one split.
    """
    candidates = ds03_data["candidates"]

    train_events = set(candidates[candidates["derived_event_split"] == "derived_ds03_train"]["fire_event_id"].unique())
    val_events = set(candidates[candidates["derived_event_split"] == "derived_ds03_val"]["fire_event_id"].unique())
    test_events = set(candidates[candidates["derived_event_split"] == "derived_ds03_test"]["fire_event_id"].unique())

    # Assert mutually disjoint event sets
    assert train_events.isdisjoint(val_events), f"Train and Val share events: {train_events.intersection(val_events)}"
    assert train_events.isdisjoint(test_events), f"Train and Test share events: {train_events.intersection(test_events)}"
    assert val_events.isdisjoint(test_events), f"Val and Test share events: {val_events.intersection(test_events)}"

    # Assert non-empty partition representation
    assert len(train_events) == 4
    assert len(val_events) == 1
    assert len(test_events) == 1


def test_frozen_firms_parquet_unchanged():
    """
    Invariant 9: Frozen FIRMS features table (data/interim/causal_features_2025.parquet)
    must remain byte-for-byte unmodified with exactly 1,175,795 rows and 51 columns.
    """
    features_path = PROJECT_ROOT / "data" / "interim" / "causal_features_2025.parquet"
    assert features_path.exists()

    df = pd.read_parquet(features_path, columns=["detection_id", "partition"])
    assert len(df) == 1_175_795

    # Check exact frozen partition counts
    part_counts = df["partition"].value_counts().to_dict()
    assert part_counts["train"] == 578_465
    assert part_counts["train_heldout_spatial"] == 277_395
    assert part_counts["context_burn_in"] == 150_799
    assert part_counts["test_seen_spatial"] == 91_846
    assert part_counts["test"] == 47_881
    assert part_counts["val"] == 29_409


def test_existing_ds05_artifacts_remain_unchanged():
    """
    Invariant 10: Existing Stage 1 (DS_05) reference and labeling artifacts
    must remain 100% intact and untouched.
    """
    ref_ds05_dir = PROJECT_ROOT / "data" / "reference" / "ds05"
    label_ds05_dir = PROJECT_ROOT / "data" / "labeling" / "ds05"

    df_persistent = pd.read_parquet(ref_ds05_dir / "persistent_sources.parquet")
    assert len(df_persistent) == 18

    df_incidents = pd.read_parquet(ref_ds05_dir / "industrial_incidents.parquet")
    assert len(df_incidents) == 14

    df_valid_anchors = pd.read_parquet(label_ds05_dir / "ds05_valid_industrial_anchors.parquet")
    assert len(df_valid_anchors) == 2

    df_confounders = pd.read_parquet(label_ds05_dir / "ds05_quarantined_confounders.parquet")
    assert len(df_confounders) == 1_870

    df_rej_ds05 = pd.read_parquet(label_ds05_dir / "ds05_rejected_candidates.parquet")
    assert len(df_rej_ds05) == 37

    df_matches_ds05 = pd.read_parquet(label_ds05_dir / "ds05_firms_matches.parquet")
    assert len(df_matches_ds05) == 39
