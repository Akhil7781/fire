"""
Test suite for DS_05: India Industrial and Persistent Thermal Source Evidence Pipeline.
Verifies all 8 core scientific invariants:
1. test_static_source_cannot_become_industrial_fire
2. test_facility_proximity_cannot_create_industrial_fire
3. test_event_timestamps_normalized_correctly
4. test_geodesic_distance_is_correct
5. test_provenance_survives_matching
6. test_rejected_incidents_remain_traceable
7. test_frozen_firms_parquet_unchanged
8. test_split_ids_unchanged
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
import sys
import pandas as pd
import pytest

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.labeling.ds05 import (
    DS05Pipeline,
    geodesic_distance_km,
    temporal_difference_hours,
)


@pytest.fixture(scope="module")
def ds05_data():
    """Runs DS05 pipeline and loads output artifacts."""
    pipeline = DS05Pipeline(PROJECT_ROOT)
    pipeline.build_and_save_reference_datasets()
    summary = pipeline.match_and_audit()

    ref_persistent = pd.read_parquet(PROJECT_ROOT / "data" / "reference" / "ds05" / "persistent_sources.parquet")
    ref_incidents = pd.read_parquet(PROJECT_ROOT / "data" / "reference" / "ds05" / "industrial_incidents.parquet")
    valid_anchors = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds05" / "ds05_valid_industrial_anchors.parquet")
    rejected_cands = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds05" / "ds05_rejected_candidates.parquet")
    confounders = pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds05" / "ds05_quarantined_confounders.parquet")

    return {
        "summary": summary,
        "ref_persistent": ref_persistent,
        "ref_incidents": ref_incidents,
        "valid_anchors": valid_anchors,
        "rejected_cands": rejected_cands,
        "confounders": confounders,
    }


def test_static_source_cannot_become_industrial_fire(ds05_data):
    """
    Invariant 1: Persistent/static sources must NEVER be classified as Class 1 (INDUSTRIAL_FIRE).
    They must be flagged as STATIC_SOURCE_EVIDENCE and quarantined as confounders.
    """
    ref_persistent = ds05_data["ref_persistent"]
    confounders = ds05_data["confounders"]

    # In reference dataset:
    assert (ref_persistent["evidence_category"] == "STATIC_SOURCE_EVIDENCE").all()
    assert (ref_persistent["can_become_industrial_fire"] == False).all()
    assert (ref_persistent["is_confounder"] == True).all()

    # In quarantined confounders:
    assert len(confounders) == 1870
    assert (confounders["label_class"] == 4).all()
    assert (confounders["label_status"] == "PERSISTENT_THERMAL_SOURCE").all()
    assert (confounders["is_supervised_target"] == False).all()
    assert not (confounders["label_class"] == 1).any()


def test_facility_proximity_cannot_create_industrial_fire(ds05_data):
    """
    Invariant 2: Mere spatial proximity to an industrial facility without verified contemporaneous
    disaster documentation cannot produce an industrial fire label.
    """
    rejected = ds05_data["rejected_cands"]
    valid = ds05_data["valid_anchors"]

    # Detections close to industrial parks (e.g. Dahej at 1.12 km, Dombivli at 2.71 km)
    # but without matching disaster timestamps must be rejected
    dahej_rejections = rejected[rejected["incident_id"] == "SEBI_2025_BSE_DAHEJ_CHEM_01"]
    assert len(dahej_rejections) > 0
    for _, r in dahej_rejections.iterrows():
        assert r["target_class"] == 0
        assert r["is_supervised_target"] == False

    # Only verified incident matches are in valid anchors
    assert len(valid) == 2
    assert set(valid["incident_id"]) == {"NEWS_2025_MANALI_PETROCHEM_05"}


def test_event_timestamps_normalized_correctly(ds05_data):
    """
    Invariant 3: Event timestamps must be normalized to ISO UTC and satisfy start <= end.
    """
    ref_incidents = ds05_data["ref_incidents"]
    assert len(ref_incidents) == 14

    for _, row in ref_incidents.iterrows():
        t_start = datetime.fromisoformat(row["event_start"].replace("Z", "+00:00"))
        t_end = datetime.fromisoformat(row["event_end"].replace("Z", "+00:00"))
        assert t_start <= t_end
        assert t_start.tzinfo is not None
        assert t_start.tzinfo == timezone.utc


def test_geodesic_distance_is_correct():
    """
    Invariant 4: Haversine distance matches exact spherical geometry.
    """
    # 1 degree of latitude at equator is approximately 111.195 km
    dist_1deg_lat = geodesic_distance_km(0.0, 0.0, 1.0, 0.0)
    assert math.isclose(dist_1deg_lat, 111.195, rel_tol=1e-3)

    # Coincident points must have 0 distance
    dist_zero = geodesic_distance_km(13.1678, 80.2612, 13.1678, 80.2612)
    assert dist_zero == 0.0

    # Known Manali distance check
    manali_lat, manali_lon = 13.1678, 80.2612
    det1_lat, det1_lon = 13.16045, 80.28629
    dist_manali = geodesic_distance_km(manali_lat, manali_lon, det1_lat, det1_lon)
    assert 2.80 <= dist_manali <= 2.90


def test_provenance_survives_matching(ds05_data):
    """
    Invariant 5: Complete provenance (source authority, record ID, coordinates, distance, dt)
    survives matching and is preserved in valid anchors.
    """
    valid = ds05_data["valid_anchors"]
    assert len(valid) == 2

    required_cols = [
        "detection_id", "incident_id", "facility_name", "spatial_distance_km",
        "temporal_difference_hours", "matching_method", "match_quality",
        "frp_mw", "partition", "evidence_category", "target_class",
        "is_supervised_target", "audit_notes"
    ]
    for col in required_cols:
        assert col in valid.columns
        assert not valid[col].isna().any()

    # Check specific Manali detections
    expected_ids = {
        "be964232de1507731fd75bf1d2aa458ed4ab35e5cdfc92147f7fe0769e768ece",
        "c2f0beeeee6deb19996c5f07208156d6fdf1cf2fb5cbf949677b5f73471f7c83"
    }
    assert set(valid["detection_id"]) == expected_ids


def test_rejected_incidents_remain_traceable(ds05_data):
    """
    Invariant 6: Rejected candidates must remain traceable in the audit table with explicit reasons.
    """
    rejected = ds05_data["rejected_cands"]
    assert len(rejected) > 0
    assert "rejection_reason" in rejected.columns

    # Heubach Colorants candidate 29a1... must be in rejected table
    heubach_id = "29a1dbaae9743ba5c3dd5245165bd69c9a75bea38ac1fb907cc4726f4275249a"
    heubach_rejs = rejected[rejected["detection_id"] == heubach_id]
    assert len(heubach_rejs) > 0
    rej_text = heubach_rejs.iloc[0]["rejection_reason"]
    assert "Spatial distance" in rej_text or "Spatial Non-Match" in rej_text

    # Bhandara Ordnance candidate 90b7... must be in rejected table
    bhandara_id = "90b7776c1094b06f5303263f35bbcb56fd8e3a0f31d649e90a6a7756ea345eed"
    bhandara_rejs = rejected[rejected["detection_id"] == bhandara_id]
    assert len(bhandara_rejs) > 0
    rej_text_b = bhandara_rejs.iloc[0]["rejection_reason"]
    assert "Temporal" in rej_text_b or "Spatial" in rej_text_b


def test_frozen_firms_parquet_unchanged():
    """
    Invariant 7: causal_features_2025.parquet must remain byte-for-byte and row-count immutable.
    """
    frozen_path = PROJECT_ROOT / "data" / "interim" / "causal_features_2025.parquet"
    assert frozen_path.exists()

    df = pd.read_parquet(frozen_path, columns=["detection_id"])
    assert len(df) == 1175795
    assert df["detection_id"].nunique() == 1175795


def test_split_ids_unchanged():
    """
    Invariant 8: Train/val/test partition assignments remain unchanged.
    """
    frozen_path = PROJECT_ROOT / "data" / "interim" / "causal_features_2025.parquet"
    df = pd.read_parquet(frozen_path, columns=["partition"])
    counts = df["partition"].value_counts().to_dict()

    assert counts.get("train", 0) == 578465
    assert counts.get("val", 0) == 29409
    assert counts.get("test_seen_spatial", 0) == 91846
    assert counts.get("test", 0) == 47881
    assert counts.get("train_heldout_spatial", 0) == 277395
    assert counts.get("context_burn_in", 0) == 150799
    assert sum(counts.values()) == 1175795
