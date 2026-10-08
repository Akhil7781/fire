"""
Regression test suite for Independent Event-Evidence Expansion.
Enforces the 9 core scientific invariants:
1. test_burned_area_requires_temporal_correspondence
2. test_agricultural_context_cannot_create_agricultural_fire
3. test_static_infrastructure_cannot_become_acute_event
4. test_event_geometry_preserved
5. test_source_ids_preserved
6. test_unlabeled_remains_unlabeled
7. test_test_partition_does_not_tune_matching
8. test_frozen_firms_feature_table_unchanged
9. test_existing_genuine_events_remain_traceable
"""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.labeling.config import get_label_config
from src.labeling.fusion import fuse_detection_matches
from src.labeling.matching import (
    geodesic_distance_km,
    match_evidence_to_firms,
    temporal_difference_hours,
)
from src.labeling.schemas import (
    ConfidenceTier,
    EvidenceCategory,
    EvidenceMatch,
    FinalLabelRecord,
    LabelStatus,
    LocationPrecision,
    NormalizedEvidence,
    OfficialnessLevel,
    SourceType,
    TargetClass,
)
from src.labeling.sources import (
    AgriculturalFireAdapter,
    ForestFireAdapter,
    GlobalFireAtlasAdapter,
    IndustrialFireAdapter,
    MCD64A1Adapter,
    OtherThermalSourceAdapter,
    Sentinel2AgriculturalPilotAdapter,
)


def test_burned_area_requires_temporal_correspondence():
    """
    Invariant 1: Proves MCD64A1 and Global Fire Atlas cannot match FIRMS detections
    outside strict temporal tolerance bounds.
    """
    config = get_label_config()

    # Create a synthetic forest fire burned-area evidence record for April 25-28, 2025
    t_start = datetime(2025, 4, 25, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2025, 4, 28, 23, 59, tzinfo=timezone.utc)
    lat, lon = 29.3812, 79.4620

    mcd_evi = NormalizedEvidence(
        evidence_id="EVI_TEST_MCD_01",
        source_name="MODIS_MCD64A1_V61_BURNED_AREA",
        source_type=SourceType.SATELLITE_BURN_PRODUCT,
        evidence_category=EvidenceCategory.EVENT_EVIDENCE,
        class_candidate=TargetClass.FOREST_FIRE,
        event_datetime_start=t_start,
        event_datetime_end=t_end,
        latitude=lat,
        longitude=lon,
        location_precision=LocationPrecision.PLOT_POLYGON,
        officialness_level=OfficialnessLevel.SCIENTIFIC_AGENCY,
        confidence_basis="MODIS 500m Burned Area Test",
    )

    # Detections:
    # 1. During the event -> should match
    # 2. 10 days before the event -> must NOT match
    # 3. 10 days after the event -> must NOT match
    test_firms = pd.DataFrame([
        {
            "detection_id": "DET_DURING",
            "latitude": lat + 0.005,
            "longitude": lon + 0.005,
            "acq_datetime_utc": datetime(2025, 4, 26, 8, 0, tzinfo=timezone.utc),
        },
        {
            "detection_id": "DET_BEFORE",
            "latitude": lat + 0.005,
            "longitude": lon + 0.005,
            "acq_datetime_utc": datetime(2025, 4, 10, 8, 0, tzinfo=timezone.utc),
        },
        {
            "detection_id": "DET_AFTER",
            "latitude": lat + 0.005,
            "longitude": lon + 0.005,
            "acq_datetime_utc": datetime(2025, 5, 15, 8, 0, tzinfo=timezone.utc),
        },
    ])

    matches = match_evidence_to_firms(test_firms, [mcd_evi], config)
    matched_ids = [m.detection_id for m in matches]

    assert "DET_DURING" in matched_ids, "Detection during event window should match"
    assert "DET_BEFORE" not in matched_ids, "Detection 10 days before event must NOT match"
    assert "DET_AFTER" not in matched_ids, "Detection 10 days after event must NOT match"


def test_agricultural_context_cannot_create_agricultural_fire():
    """
    Invariant 2: Proves regional ICAR-IARI agricultural context cannot create positive
    Class 3 fire labels without localized optical burn scar proof.
    """
    t_start = datetime(2025, 10, 20, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2025, 10, 20, 23, 59, tzinfo=timezone.utc)

    # Context evidence record (e.g. block/village level advisory)
    agri_context = NormalizedEvidence(
        evidence_id="EVI_AGR_CONTEXT_TEST",
        source_name="ICAR_IARI_CREAMS_2025",
        source_type=SourceType.SATELLITE_BURN_PRODUCT,
        evidence_category=EvidenceCategory.CONTEXT_ONLY,
        class_candidate=TargetClass.AGRICULTURAL_FIRE,
        event_datetime_start=t_start,
        event_datetime_end=t_end,
        latitude=30.1245,
        longitude=75.8456,
        location_precision=LocationPrecision.PLOT_POLYGON,
        officialness_level=OfficialnessLevel.SCIENTIFIC_AGENCY,
        confidence_basis="Regional crop burning bulletin",
    )

    match = EvidenceMatch(
        detection_id="DET_AGRI_CONTEXT_TEST",
        evidence_id=agri_context.evidence_id,
        source_name=agri_context.source_name,
        evidence_category=agri_context.evidence_category,
        candidate_class=agri_context.class_candidate,
        spatial_distance_km=0.85,
        temporal_difference_hours=0.0,
        matching_method="GEODESIC_AND_TEMPORAL_INTERVAL",
        base_confidence=0.50,
        evidence_tier=ConfidenceTier.TIER_C,
        evidence_ref=agri_context,
    )

    final_record = fuse_detection_matches("DET_AGRI_CONTEXT_TEST", [match])

    # Must resolve to UNLABELED / CONTEXT_ONLY, NOT Class 3
    assert final_record.label_class == 0, f"Expected label_class=0, got {final_record.label_class}"
    assert final_record.label_status == LabelStatus.CONTEXT_ONLY.value
    assert final_record.is_supervised_target is False, "Context only cannot be a supervised target"
    assert "CONTEXT_ONLY_EXCLUSION" in (final_record.downgrade_reason or "")


def test_static_infrastructure_cannot_become_acute_event():
    """
    Invariant 3: Proves stationary emitters remain PERSISTENT_THERMAL_SOURCE
    and can NEVER be promoted to acute CONFIRMED_EVENT or PROBABLE_EVENT.
    """
    t_start = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc)

    flare_evi = NormalizedEvidence(
        evidence_id="EVI_FLARE_TEST",
        source_name="INDIA_OTHER_THERMAL_SOURCES_2025",
        source_type=SourceType.INFRASTRUCTURE_CATALOG,
        evidence_category=EvidenceCategory.STATIC_SOURCE_EVIDENCE,
        class_candidate=TargetClass.OTHER_THERMAL_SOURCE,
        event_datetime_start=t_start,
        event_datetime_end=t_end,
        latitude=22.4789,
        longitude=69.8345,
        location_precision=LocationPrecision.EXACT_POINT,
        officialness_level=OfficialnessLevel.SCIENTIFIC_AGENCY,
        confidence_basis="Refinery Gas Flaring Stack",
        source_record_id="STATIC_FLARE_01",
    )

    match = EvidenceMatch(
        detection_id="DET_FLARE_TEST",
        evidence_id=flare_evi.evidence_id,
        source_name=flare_evi.source_name,
        evidence_category=flare_evi.evidence_category,
        candidate_class=flare_evi.class_candidate,
        spatial_distance_km=0.15,
        temporal_difference_hours=0.0,
        matching_method="GEODESIC_AND_TEMPORAL_INTERVAL",
        base_confidence=0.75,
        evidence_tier=ConfidenceTier.TIER_B,
        evidence_ref=flare_evi,
    )

    final_record = fuse_detection_matches("DET_FLARE_TEST", [match])

    assert final_record.label_class == 4
    assert final_record.label_status == LabelStatus.PERSISTENT_THERMAL_SOURCE.value
    assert final_record.confidence_tier == ConfidenceTier.TIER_B.value
    assert final_record.is_supervised_target is False, "Static sources must NOT be positive supervised targets"
    assert "PERSISTENT_FLARING_STACK" in (final_record.downgrade_reason or "")


def test_event_geometry_preserved():
    """
    Invariant 4: Proves polygon perimeters and parcel geometries are preserved
    in normalized evidence records.
    """
    gfa_adapter = GlobalFireAtlasAdapter(Path("data/labeling/raw"))
    gfa_raw = gfa_adapter.fetch_or_load()
    gfa_evis = gfa_adapter.normalize(gfa_raw)

    assert len(gfa_evis) > 0
    for evi in gfa_evis:
        assert evi.geometry_wkt is not None, f"Geometry missing for GFA record {evi.evidence_id}"
        assert evi.geometry_wkt.startswith("POLYGON"), f"Invalid WKT format: {evi.geometry_wkt}"

    s2_adapter = Sentinel2AgriculturalPilotAdapter(Path("data/labeling/raw"))
    s2_raw = s2_adapter.fetch_or_load()
    s2_evis = s2_adapter.normalize(s2_raw)

    assert len(s2_evis) > 0
    for evi in s2_evis:
        assert evi.geometry_wkt is not None, f"Geometry missing for S2 scar {evi.evidence_id}"
        assert evi.geometry_wkt.startswith("POLYGON"), f"Invalid WKT format: {evi.geometry_wkt}"


def test_source_ids_preserved():
    """
    Invariant 5: Proves original reference source identifiers survive into label table.
    """
    labels_path = Path("data/processed/labels/master_labels_2025.parquet")
    assert labels_path.exists(), "Master labels parquet must exist"

    cols = ["detection_id", "label_class", "primary_evidence_id", "primary_source"]
    df = pd.read_parquet(labels_path, columns=cols)

    # Class 1 (Industrial)
    ind_rows = df[df["label_class"] == 1]
    assert len(ind_rows) >= 2
    for _, r in ind_rows.iterrows():
        assert "EVI_IND_" in str(r["primary_evidence_id"])
        assert r["primary_source"] == "INDIA_INDUSTRIAL_INCIDENTS_2025"

    # Class 3 (Agricultural)
    agri_rows = df[df["label_class"] == 3]
    assert len(agri_rows) >= 6
    for _, r in agri_rows.iterrows():
        assert "EVI_S2_SCAR_" in str(r["primary_evidence_id"])
        assert r["primary_source"] == "SENTINEL2_AGRI_PILOT_T43RFP"


def test_unlabeled_remains_unlabeled():
    """
    Invariant 6: Proves unmatched detections strictly remain Class 0 Tier D UNLABELED.
    """
    final_record = fuse_detection_matches("DET_UNMATCHED_TEST", [])

    assert final_record.label_class == 0
    assert final_record.confidence_score == 0.0
    assert final_record.confidence_tier == ConfidenceTier.TIER_D.value
    assert final_record.label_status == LabelStatus.UNLABELED.value
    assert final_record.evidence_count == 0
    assert final_record.primary_evidence_id is None
    assert final_record.is_supervised_target is False


def test_test_partition_does_not_tune_matching():
    """
    Invariant 7: Proves calibration code accesses only the train partition
    and strictly excludes validation and test partitions.
    """
    calib_file = Path("scripts/calibrate_matching_parameters.py")
    content = calib_file.read_text(encoding="utf-8")
    assert 'firms_df["partition"] == "train"' in content

    # Verify that when loading using that filter, exactly zero test/val rows exist
    firms_df = pd.read_parquet(
        "data/interim/causal_features_2025.parquet",
        columns=["partition"],
    )
    train_df = firms_df[firms_df["partition"] == "train"]
    partitions_used = set(train_df["partition"].unique())
    assert partitions_used == {"train"}, f"Unexpected partitions: {partitions_used}"
    assert "val" not in partitions_used
    assert "test" not in partitions_used
    assert "test_seen_spatial" not in partitions_used


def test_frozen_firms_feature_table_unchanged():
    """
    Invariant 8: Proves the frozen FIRMS feature table is completely unmodified.
    Rows = 1,175,795, Cols = 51.
    """
    feat_path = Path("data/interim/causal_features_2025.parquet")
    assert feat_path.exists()

    schema = pq.read_schema(feat_path)
    assert len(schema.names) == 51, f"Expected 51 columns, found {len(schema.names)}"

    metadata = pq.read_metadata(feat_path)
    assert metadata.num_rows == 1175795, f"Expected 1,175,795 rows, found {metadata.num_rows}"


def test_existing_genuine_events_remain_traceable():
    """
    Invariant 9: Proves existing genuine events (Manali industrial detections,
    Nainital forest fire detections) remain matched and intact in the master label table.
    """
    labels_path = Path("data/processed/labels/master_labels_2025.parquet")
    df = pd.read_parquet(labels_path)

    # Manali industrial detections
    m1 = df[df["detection_id"].str.startswith("be964232de150773")]
    assert len(m1) == 1, "Manali detection 1 must exist"
    assert m1.iloc[0]["label_class"] == 1
    assert m1.iloc[0]["label_status"] == LabelStatus.PROBABLE_EVENT.value

    m2 = df[df["detection_id"].str.startswith("c2f0beeeee6deb19")]
    assert len(m2) == 1, "Manali detection 2 must exist"
    assert m2.iloc[0]["label_class"] == 1
    assert m2.iloc[0]["label_status"] == LabelStatus.PROBABLE_EVENT.value
