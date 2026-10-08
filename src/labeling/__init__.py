"""
Label construction package initialization.
"""

from src.labeling.config import LabelConfig, get_label_config
from src.labeling.schemas import (
    ConfidenceTier,
    EvidenceMatch,
    FinalLabelRecord,
    LabelStatus,
    LocationPrecision,
    NormalizedEvidence,
    OfficialnessLevel,
    SourceType,
    TargetClass,
)
from src.labeling.matching import geodesic_distance_km, match_evidence_to_firms, temporal_difference_hours
from src.labeling.fusion import fuse_detection_matches
from src.labeling.conflicts import resolve_match_conflicts
from src.labeling.pipeline import LabelConstructionPipeline

__all__ = [
    "LabelConfig",
    "get_label_config",
    "ConfidenceTier",
    "EvidenceMatch",
    "FinalLabelRecord",
    "LabelStatus",
    "LocationPrecision",
    "NormalizedEvidence",
    "OfficialnessLevel",
    "SourceType",
    "TargetClass",
    "geodesic_distance_km",
    "match_evidence_to_firms",
    "temporal_difference_hours",
    "fuse_detection_matches",
    "resolve_match_conflicts",
    "LabelConstructionPipeline",
]
