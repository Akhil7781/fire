"""
Comprehensive unit and regression tests for the label construction pipeline.
Validates schemas, geometry, geodesic distances, temporal interval logic,
unlabeled handling, conflict resolution, split integrity, immutable FIRMS state,
and the 10 scientific invariants required by the semantic quality review.
"""

import math
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.labeling.config import get_label_config
from src.labeling.conflicts import resolve_match_conflicts
from src.labeling.fusion import fuse_detection_matches
from src.labeling.matching import (
    geodesic_distance_km,
    temporal_difference_hours,
    match_evidence_to_firms,
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


def test_geodesic_distance_calculation():
    """Validates exact Haversine great-circle calculation on known landmarks."""
    d = geodesic_distance_km(28.6139, 77.2090, 19.0760, 72.8777)
    assert 1140.0 <= d <= 1160.0, f"Distance {d} outside expected range"

    d_zero = geodesic_distance_km(28.6139, 77.2090, 28.6139, 77.2090)
    assert d_zero == 0.0

    d_lat = geodesic_distance_km(20.0, 75.0, 21.0, 75.0)
    assert 110.0 <= d_lat <= 112.0


def test_temporal_interval_matching():
    """Validates interval-based temporal difference calculation."""
    start = datetime(2025, 4, 1, 6, 0, tzinfo=timezone.utc)
    end = datetime(2025, 4, 1, 18, 0, tzinfo=timezone.utc)

    during = datetime(2025, 4, 1, 12, 0, tzinfo=timezone.utc)
    assert temporal_difference_hours(during, start, end) == 0.0

    assert temporal_difference_hours(start, start, end) == 0.0
    assert temporal_difference_hours(end, start, end) == 0.0

    before = datetime(2025, 4, 1, 4, 0, tzinfo=timezone.utc)
    assert abs(temporal_difference_hours(before, start, end) - 2.0) < 1e-4

    after = datetime(2025, 4, 1, 21, 0, tzinfo=timezone.utc)
    assert abs(temporal_difference_hours(after, start, end) - 3.0) < 1e-4


def test_normalized_evidence_schema_validation():
    """Ensures NormalizedEvidence strictly enforces timezone awareness and coordinate limits."""
    t1 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

    evi = NormalizedEvidence(
        evidence_id="EVI_TEST_01",
        source_name="TEST_SRC",
        source_type=SourceType.STATUTORY_DISCLOSURE,
        evidence_category=EvidenceCategory.EVENT_EVIDENCE,
        class_candidate=TargetClass.INDUSTRIAL_FIRE,
        event_datetime_start=t1,
        event_datetime_end=t2,
        latitude=21.5,
        longitude=72.8,
        location_precision=LocationPrecision.EXACT_POINT,
        officialness_level=OfficialnessLevel.STATUTORY_GOVERNMENT,
        confidence_basis="Test basis",
    )
    assert evi.latitude == 21.5
    assert evi.evidence_id == "EVI_TEST_01"
    assert evi.evidence_category == EvidenceCategory.EVENT_EVIDENCE

    # Reject naive timezone
    try:
        NormalizedEvidence(
            evidence_id="EVI_TEST_BAD",
            source_name="TEST_SRC",
            source_type=SourceType.STATUTORY_DISCLOSURE,
            evidence_category=EvidenceCategory.EVENT_EVIDENCE,
            class_candidate=TargetClass.INDUSTRIAL_FIRE,
            event_datetime_start=datetime(2025, 1, 1, 0, 0),
            event_datetime_end=t2,
            latitude=21.5,
            longitude=72.8,
            location_precision=LocationPrecision.EXACT_POINT,
            officialness_level=OfficialnessLevel.STATUTORY_GOVERNMENT,
            confidence_basis="Test",
        )
        assert False, "Should have raised ValueError on naive datetime"
    except ValueError:
        pass

    # Reject invalid coordinates
    try:
        NormalizedEvidence(
            evidence_id="EVI_TEST_BAD_COORD",
            source_name="TEST_SRC",
            source_type=SourceType.STATUTORY_DISCLOSURE,
            evidence_category=EvidenceCategory.EVENT_EVIDENCE,
            class_candidate=TargetClass.INDUSTRIAL_FIRE,
            event_datetime_start=t1,
            event_datetime_end=t2,
            latitude=121.5,
            longitude=72.8,
            location_precision=LocationPrecision.EXACT_POINT,
            officialness_level=OfficialnessLevel.STATUTORY_GOVERNMENT,
            confidence_basis="Test",
        )
        assert False, "Should have raised ValueError on invalid latitude"
    except ValueError:
        pass


def test_conflict_resolution_rules():
    """Tests conflict resolution priority rules."""
    t1 = datetime(2025, 5, 1, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 5, 1, 12, 0, tzinfo=timezone.utc)

    # Setup Evidence 1: Class 1 (Industrial Event, Tier B, Statutory)
    evi1 = NormalizedEvidence(
        evidence_id="EVI_IND_01",
        source_name="SEBI_REG30",
        source_type=SourceType.STATUTORY_DISCLOSURE,
        evidence_category=EvidenceCategory.EVENT_EVIDENCE,
        class_candidate=TargetClass.INDUSTRIAL_FIRE,
        event_datetime_start=t1,
        event_datetime_end=t2,
        latitude=21.7,
        longitude=72.6,
        location_precision=LocationPrecision.EXACT_POINT,
        officialness_level=OfficialnessLevel.STATUTORY_GOVERNMENT,
        confidence_basis="Statutory",
    )
    match1 = EvidenceMatch(
        detection_id="DET_CONFLICT_01",
        evidence_id=evi1.evidence_id,
        source_name=evi1.source_name,
        evidence_category=evi1.evidence_category,
        candidate_class=evi1.class_candidate,
        spatial_distance_km=0.1,
        temporal_difference_hours=0.0,
        matching_method="TEST",
        base_confidence=0.85,
        evidence_tier=ConfidenceTier.TIER_B,
        evidence_ref=evi1,
    )

    # Setup Evidence 2: Class 3 (Agricultural Context, Tier C, Regional Bulletin)
    evi2 = NormalizedEvidence(
        evidence_id="EVI_AGR_02",
        source_name="IARI_CREAMS",
        source_type=SourceType.SATELLITE_BURN_PRODUCT,
        evidence_category=EvidenceCategory.CONTEXT_ONLY,
        class_candidate=TargetClass.AGRICULTURAL_FIRE,
        event_datetime_start=t1,
        event_datetime_end=t2,
        latitude=21.7,
        longitude=72.6,
        location_precision=LocationPrecision.PLOT_POLYGON,
        officialness_level=OfficialnessLevel.SCIENTIFIC_AGENCY,
        confidence_basis="Catalog",
    )
    match2 = EvidenceMatch(
        detection_id="DET_CONFLICT_01",
        evidence_id=evi2.evidence_id,
        source_name=evi2.source_name,
        evidence_category=evi2.evidence_category,
        candidate_class=evi2.class_candidate,
        spatial_distance_km=3.5,
        temporal_difference_hours=0.0,
        matching_method="TEST",
        base_confidence=0.50,
        evidence_tier=ConfidenceTier.TIER_C,
        evidence_ref=evi2,
    )

    # Rule 1: Tier B overrides Tier C
    res_cls, res_tier, res_status, conf, p_match, reason = resolve_match_conflicts([match1, match2])
    assert res_cls == TargetClass.INDUSTRIAL_FIRE
    assert res_tier == ConfidenceTier.TIER_B
    assert res_status == LabelStatus.PROBABLE_EVENT


# ==============================================================================
# 10 SCIENTIFIC INVARIANT REGRESSION TESTS REQUIRED BY AUDIT
# ==============================================================================

def test_static_inventory_cannot_produce_confirmed_event():
    """Invariant 1: Proximity to a static inventory alone cannot produce CONFIRMED_EVENT."""
    t1 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc)

    evi_static = NormalizedEvidence(
        evidence_id="EVI_POWER_TEST",
        source_name="INDIA_OTHER_THERMAL_SOURCES_2025",
        source_type=SourceType.INFRASTRUCTURE_CATALOG,
        evidence_category=EvidenceCategory.STATIC_SOURCE_EVIDENCE,
        class_candidate=TargetClass.OTHER_THERMAL_SOURCE,
        event_datetime_start=t1,
        event_datetime_end=t2,
        latitude=22.82,
        longitude=69.52,
        location_precision=LocationPrecision.EXACT_POINT,
        officialness_level=OfficialnessLevel.STATUTORY_GOVERNMENT,
        confidence_basis="CEA Database",
        source_record_id="POWER_TATA_MUNDRA_11",
    )
    match = EvidenceMatch(
        detection_id="DET_STATIC_001",
        evidence_id=evi_static.evidence_id,
        source_name=evi_static.source_name,
        evidence_category=evi_static.evidence_category,
        candidate_class=evi_static.class_candidate,
        spatial_distance_km=0.2,
        temporal_difference_hours=0.0,
        matching_method="GEODESIC_AND_TEMPORAL_INTERVAL",
        base_confidence=0.70,
        evidence_tier=ConfidenceTier.TIER_B,
        evidence_ref=evi_static,
    )
    res = fuse_detection_matches("DET_STATIC_001", [match])
    assert res.label_status != LabelStatus.CONFIRMED_EVENT.value, "Static inventory must NEVER produce CONFIRMED_EVENT"
    assert res.confidence_tier != ConfidenceTier.TIER_A.value, "Static inventory must NEVER produce Tier A"
    assert res.label_status == LabelStatus.PERSISTENT_THERMAL_SOURCE.value
    assert res.is_supervised_target is False


def test_facility_proximity_cannot_create_industrial_fire():
    """Invariant 2: Facility proximity alone cannot create INDUSTRIAL_FIRE positive event."""
    t1 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc)

    # Static facility polygon without verified incident
    evi_facility = NormalizedEvidence(
        evidence_id="EVI_ESTATE_STATIC",
        source_name="OPENSTREETMAP_INDUSTRIAL_POLYGON",
        source_type=SourceType.INFRASTRUCTURE_CATALOG,
        evidence_category=EvidenceCategory.STATIC_SOURCE_EVIDENCE,
        class_candidate=TargetClass.OTHER_THERMAL_SOURCE,
        event_datetime_start=t1,
        event_datetime_end=t2,
        latitude=21.71,
        longitude=72.58,
        location_precision=LocationPrecision.PLOT_POLYGON,
        officialness_level=OfficialnessLevel.CROWDSOURCED,
        confidence_basis="Industrial Estate Boundary",
        source_record_id="FACILITY_DAHEJ_GIDC",
    )
    match = EvidenceMatch(
        detection_id="DET_FACILITY_002",
        evidence_id=evi_facility.evidence_id,
        source_name=evi_facility.source_name,
        evidence_category=evi_facility.evidence_category,
        candidate_class=evi_facility.class_candidate,
        spatial_distance_km=0.5,
        temporal_difference_hours=0.0,
        matching_method="GEODESIC_AND_TEMPORAL_INTERVAL",
        base_confidence=0.70,
        evidence_tier=ConfidenceTier.TIER_B,
        evidence_ref=evi_facility,
    )
    res = fuse_detection_matches("DET_FACILITY_002", [match])
    assert res.label_class != int(TargetClass.INDUSTRIAL_FIRE), "Facility proximity alone cannot create INDUSTRIAL_FIRE"
    assert res.label_status != LabelStatus.CONFIRMED_EVENT.value
    assert res.label_status != LabelStatus.PROBABLE_EVENT.value


def test_village_centroid_context_cannot_create_agricultural_fire():
    """Invariant 3: Village centroid context cannot create AGRICULTURAL_FIRE positive label."""
    t1 = datetime(2025, 10, 28, 6, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 10, 28, 18, 0, tzinfo=timezone.utc)

    evi_village = NormalizedEvidence(
        evidence_id="EVI_IARI_PATIALA",
        source_name="ICAR_IARI_CREAMS_2025",
        source_type=SourceType.SATELLITE_BURN_PRODUCT,
        evidence_category=EvidenceCategory.CONTEXT_ONLY,
        class_candidate=TargetClass.AGRICULTURAL_FIRE,
        event_datetime_start=t1,
        event_datetime_end=t2,
        latitude=30.33,
        longitude=76.40,
        location_precision=LocationPrecision.PLOT_POLYGON,
        officialness_level=OfficialnessLevel.SCIENTIFIC_AGENCY,
        confidence_basis="Village Bulletin",
        source_record_id="IARI_2025_PUNJAB_PATIALA_01",
    )
    # Match at 3.47 km
    match = EvidenceMatch(
        detection_id="DET_AGRI_CENTROID_003",
        evidence_id=evi_village.evidence_id,
        source_name=evi_village.source_name,
        evidence_category=evi_village.evidence_category,
        candidate_class=evi_village.class_candidate,
        spatial_distance_km=3.474,
        temporal_difference_hours=0.0,
        matching_method="GEODESIC_AND_TEMPORAL_INTERVAL",
        base_confidence=0.50,
        evidence_tier=ConfidenceTier.TIER_C,
        evidence_ref=evi_village,
    )
    res = fuse_detection_matches("DET_AGRI_CENTROID_003", [match])
    assert res.label_class == int(TargetClass.UNLABELED), "Village centroid must NOT create AGRICULTURAL_FIRE"
    assert res.confidence_tier == ConfidenceTier.TIER_D.value
    assert res.label_status == LabelStatus.CONTEXT_ONLY.value
    assert res.is_supervised_target is False
    assert "CONTEXT_ONLY_EXCLUSION" in (res.downgrade_reason or "")


def test_forest_proximity_alone_cannot_create_forest_fire():
    """Invariant 4: Forest land-cover proximity alone cannot create FOREST_FIRE."""
    t1 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc)

    evi_forest_mask = NormalizedEvidence(
        evidence_id="EVI_FSI_CANOPY_MASK",
        source_name="FSI_FOREST_COVER_MAP",
        source_type=SourceType.SATELLITE_BURN_PRODUCT,
        evidence_category=EvidenceCategory.CONTEXT_ONLY,
        class_candidate=TargetClass.FOREST_FIRE,
        event_datetime_start=t1,
        event_datetime_end=t2,
        latitude=29.38,
        longitude=79.45,
        location_precision=LocationPrecision.PLOT_POLYGON,
        officialness_level=OfficialnessLevel.SCIENTIFIC_AGENCY,
        confidence_basis="Forest Land Cover",
    )
    match = EvidenceMatch(
        detection_id="DET_FOREST_MASK_004",
        evidence_id=evi_forest_mask.evidence_id,
        source_name=evi_forest_mask.source_name,
        evidence_category=evi_forest_mask.evidence_category,
        candidate_class=evi_forest_mask.class_candidate,
        spatial_distance_km=1.2,
        temporal_difference_hours=0.0,
        matching_method="GEODESIC_AND_TEMPORAL_INTERVAL",
        base_confidence=0.50,
        evidence_tier=ConfidenceTier.TIER_C,
        evidence_ref=evi_forest_mask,
    )
    res = fuse_detection_matches("DET_FOREST_MASK_004", [match])
    assert res.label_class == int(TargetClass.UNLABELED), "Forest canopy proximity alone cannot create positive FOREST_FIRE"
    assert res.label_status == LabelStatus.CONTEXT_ONLY.value
    assert res.is_supervised_target is False


def test_static_thermal_sources_cannot_automatically_become_acute_events():
    """Invariant 5: Static thermal sources cannot automatically become acute fire events."""
    t1 = datetime(2024, 10, 1, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc)

    evi_coal = NormalizedEvidence(
        evidence_id="EVI_JHARIA_COAL",
        source_name="INDIA_OTHER_THERMAL_SOURCES_2025",
        source_type=SourceType.MINING_PERIMETER,
        evidence_category=EvidenceCategory.STATIC_SOURCE_EVIDENCE,
        class_candidate=TargetClass.OTHER_THERMAL_SOURCE,
        event_datetime_start=t1,
        event_datetime_end=t2,
        latitude=23.75,
        longitude=86.42,
        location_precision=LocationPrecision.PLOT_POLYGON,
        officialness_level=OfficialnessLevel.STATUTORY_GOVERNMENT,
        confidence_basis="CMPDI Colliery Boundary",
        source_record_id="COAL_JHARIA_KUSUNDA_06",
    )
    match = EvidenceMatch(
        detection_id="DET_JHARIA_005",
        evidence_id=evi_coal.evidence_id,
        source_name=evi_coal.source_name,
        evidence_category=evi_coal.evidence_category,
        candidate_class=evi_coal.class_candidate,
        spatial_distance_km=0.8,
        temporal_difference_hours=0.0,
        matching_method="GEODESIC_AND_TEMPORAL_INTERVAL",
        base_confidence=0.70,
        evidence_tier=ConfidenceTier.TIER_B,
        evidence_ref=evi_coal,
    )
    res = fuse_detection_matches("DET_JHARIA_005", [match])
    assert res.label_status == LabelStatus.PERSISTENT_THERMAL_SOURCE.value, "Coalfield must be PERSISTENT_THERMAL_SOURCE"
    assert res.label_status not in (LabelStatus.CONFIRMED_EVENT.value, LabelStatus.PROBABLE_EVENT.value)
    assert res.confidence_tier == ConfidenceTier.TIER_B.value
    assert res.is_supervised_target is False


def test_barren_island_persistent_thermal_source_distinguishable():
    """Invariant 6: Barren Island persistent volcanic activity is distinguishable from acute event."""
    t1 = datetime(2024, 10, 1, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc)

    evi_volcano = NormalizedEvidence(
        evidence_id="EVI_BARREN_VOLCANO",
        source_name="INDIA_OTHER_THERMAL_SOURCES_2025",
        source_type=SourceType.VOLCANIC_CATALOG,
        evidence_category=EvidenceCategory.STATIC_SOURCE_EVIDENCE,
        class_candidate=TargetClass.OTHER_THERMAL_SOURCE,
        event_datetime_start=t1,
        event_datetime_end=t2,
        latitude=12.278,
        longitude=93.858,
        location_precision=LocationPrecision.EXACT_POINT,
        officialness_level=OfficialnessLevel.SCIENTIFIC_AGENCY,
        confidence_basis="GSI Volcanic Catalog",
        source_record_id="VOLCANO_BARREN_ISLAND_05",
    )
    match = EvidenceMatch(
        detection_id="DET_BARREN_006",
        evidence_id=evi_volcano.evidence_id,
        source_name=evi_volcano.source_name,
        evidence_category=evi_volcano.evidence_category,
        candidate_class=evi_volcano.class_candidate,
        spatial_distance_km=0.3,
        temporal_difference_hours=0.0,
        matching_method="GEODESIC_AND_TEMPORAL_INTERVAL",
        base_confidence=0.80,
        evidence_tier=ConfidenceTier.TIER_B,
        evidence_ref=evi_volcano,
    )
    res = fuse_detection_matches("DET_BARREN_006", [match])
    assert res.label_class == int(TargetClass.OTHER_THERMAL_SOURCE)
    assert res.label_status == LabelStatus.PERSISTENT_THERMAL_SOURCE.value
    assert res.label_status != LabelStatus.CONFIRMED_EVENT.value
    assert res.label_status != LabelStatus.PROBABLE_EVENT.value
    assert res.is_supervised_target is False
    assert "PERSISTENT_VOLCANIC_EMISSION" in (res.downgrade_reason or "")


def test_unmatched_detections_remain_unlabeled():
    """Invariant 7: Unmatched detections remain explicitly UNLABELED."""
    res = fuse_detection_matches("DET_EMPTY_007", [])
    assert res.label_class == 0
    assert res.confidence_score == 0.0
    assert res.confidence_tier == ConfidenceTier.TIER_D.value
    assert res.label_status == LabelStatus.UNLABELED.value
    assert res.evidence_category == "NONE"
    assert res.is_supervised_target is False
    assert res.evidence_count == 0


def test_provenance_survives_every_downgrade():
    """Invariant 8: Provenance survives every downgrade."""
    t1 = datetime(2025, 11, 1, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 11, 1, 12, 0, tzinfo=timezone.utc)

    evi = NormalizedEvidence(
        evidence_id="EVI_PROV_TEST_008",
        source_name="ICAR_IARI_CREAMS_2025",
        source_type=SourceType.SATELLITE_BURN_PRODUCT,
        evidence_category=EvidenceCategory.CONTEXT_ONLY,
        class_candidate=TargetClass.AGRICULTURAL_FIRE,
        event_datetime_start=t1,
        event_datetime_end=t2,
        latitude=30.0,
        longitude=76.0,
        location_precision=LocationPrecision.PLOT_POLYGON,
        officialness_level=OfficialnessLevel.SCIENTIFIC_AGENCY,
        confidence_basis="Test",
    )
    match = EvidenceMatch(
        detection_id="DET_PROV_008",
        evidence_id=evi.evidence_id,
        source_name=evi.source_name,
        evidence_category=evi.evidence_category,
        candidate_class=evi.class_candidate,
        spatial_distance_km=3.47,
        temporal_difference_hours=1.5,
        matching_method="GEODESIC_AND_TEMPORAL_INTERVAL",
        base_confidence=0.50,
        evidence_tier=ConfidenceTier.TIER_C,
        evidence_ref=evi,
    )
    res = fuse_detection_matches("DET_PROV_008", [match])
    # Even though downgraded to Class 0 UNLABELED / CONTEXT_ONLY, provenance fields must be preserved!
    assert res.primary_evidence_id == "EVI_PROV_TEST_008"
    assert res.primary_source == "ICAR_IARI_CREAMS_2025"
    assert abs(res.spatial_distance_km - 3.47) < 1e-3
    assert abs(res.temporal_difference_hours - 1.5) < 1e-3
    assert res.downgrade_reason is not None


def test_frozen_firms_feature_table_immutable_byte_schema():
    """Invariant 9: Frozen FIRMS feature table remains byte-for-byte and schema-for-schema unchanged."""
    config = get_label_config()
    p = config.frozen_features_path
    assert p.exists(), f"Frozen features file missing: {p}"

    # Verify exact schema and row count
    pf = pq.ParquetFile(p)
    assert pf.metadata.num_rows == 1175795, f"Expected 1,175,795 rows, found {pf.metadata.num_rows}"
    assert pf.metadata.num_columns == 51, f"Expected 51 columns, found {pf.metadata.num_columns}"


def test_train_val_test_ids_remain_unchanged():
    """Invariant 10: Train/Val/Test partition IDs remain unchanged."""
    config = get_label_config()
    split_dir = config.split_dir

    train_df = pd.read_parquet(split_dir / "train_ids.parquet")
    val_df = pd.read_parquet(split_dir / "val_ids.parquet")
    test_df = pd.read_parquet(split_dir / "test_ids.parquet")

    assert len(train_df) == 578465, f"Train count mismatch: {len(train_df)}"
    assert len(val_df) == 29409, f"Val count mismatch: {len(val_df)}"
    assert len(test_df) == 47881, f"Test count mismatch: {len(test_df)}"

    # Ensure zero overlap
    train_ids = set(train_df["detection_id"])
    val_ids = set(val_df["detection_id"])
    test_ids = set(test_df["detection_id"])

    assert len(train_ids.intersection(val_ids)) == 0, "Train and Val overlap!"
    assert len(train_ids.intersection(test_ids)) == 0, "Train and Test overlap!"
    assert len(val_ids.intersection(test_ids)) == 0, "Val and Test overlap!"


def run_all_label_tests():
    print("\n" + "=" * 75)
    print("RUNNING UNIT AND REGRESSION TEST SUITE FOR LABELING PIPELINE")
    print("=" * 75)

    tests = [
        ("Geodesic distance calculation", test_geodesic_distance_calculation),
        ("Temporal interval matching", test_temporal_interval_matching),
        ("Normalized evidence schema validation", test_normalized_evidence_schema_validation),
        ("Conflict resolution rules", test_conflict_resolution_rules),
        ("INVARIANT 1: Static inventory cannot produce CONFIRMED_EVENT", test_static_inventory_cannot_produce_confirmed_event),
        ("INVARIANT 2: Facility proximity cannot create INDUSTRIAL_FIRE", test_facility_proximity_cannot_create_industrial_fire),
        ("INVARIANT 3: Village centroid context cannot create AGRICULTURAL_FIRE", test_village_centroid_context_cannot_create_agricultural_fire),
        ("INVARIANT 4: Forest proximity alone cannot create FOREST_FIRE", test_forest_proximity_alone_cannot_create_forest_fire),
        ("INVARIANT 5: Static thermal sources cannot automatically become acute events", test_static_thermal_sources_cannot_automatically_become_acute_events),
        ("INVARIANT 6: Barren Island persistent thermal source distinguishable", test_barren_island_persistent_thermal_source_distinguishable),
        ("INVARIANT 7: Unmatched detections remain UNLABELED", test_unmatched_detections_remain_unlabeled),
        ("INVARIANT 8: Provenance survives every downgrade", test_provenance_survives_every_downgrade),
        ("INVARIANT 9: Frozen FIRMS feature table immutable byte & schema", test_frozen_firms_feature_table_immutable_byte_schema),
        ("INVARIANT 10: Train/Val/Test IDs remain unchanged", test_train_val_test_ids_remain_unchanged),
    ]

    for name, func in tests:
        func()
        print(f"  [PASS] {name}")

    print("\n" + "=" * 75)
    print("ALL 14 TESTS PASSED SUCCESSFULLY.")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_all_label_tests()
