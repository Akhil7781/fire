"""
Data schemas and type definitions for the label construction pipeline.
Defines target classes, confidence tiers, normalized evidence model,
match structures, and final label output schema with strict separation
between EVENT_EVIDENCE and STATIC_SOURCE_EVIDENCE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional


class TargetClass(IntEnum):
    """
    Standard target classes for satellite thermal anomaly classification.
    UNLABELED is represented explicitly as 0.
    """
    UNLABELED = 0
    INDUSTRIAL_FIRE = 1
    FOREST_FIRE = 2
    AGRICULTURAL_FIRE = 3
    OTHER_THERMAL_SOURCE = 4

    @classmethod
    def from_value(cls, val: int) -> TargetClass:
        try:
            return cls(val)
        except ValueError:
            return cls.UNLABELED


class ConfidenceTier(str, Enum):
    """
    Standard confidence tiers defined in LABEL_SPEC.md.
    """
    TIER_A = "Tier A"  # Confirmed (statutory / direct optical proof of an acute EVENT)
    TIER_B = "Tier B"  # Probable / Weak (news / catalog / high-density match)
    TIER_C = "Tier C"  # Ambiguous (conflicting / spatial context only / static proximity)
    TIER_D = "Tier D"  # Unlabeled (no independent evidence)


class EvidenceCategory(str, Enum):
    """
    Standardized classification of independent evidence:
    - EVENT_EVIDENCE: Verified fire/combustion event with explicit start and end temporal bounds.
    - STATIC_SOURCE_EVIDENCE: Stationary asset, flare stack, mine, or infrastructure location.
    - REMOTE_SENSING_CORROBORATION: Independent decametric optical/SWIR scar confirmation (e.g. Sentinel-2 dNBR).
    - CONTEXT_ONLY: Administrative district/village summaries or land-use masks without localized event proof.
    """
    EVENT_EVIDENCE = "EVENT_EVIDENCE"
    STATIC_SOURCE_EVIDENCE = "STATIC_SOURCE_EVIDENCE"
    REMOTE_SENSING_CORROBORATION = "REMOTE_SENSING_CORROBORATION"
    CONTEXT_ONLY = "CONTEXT_ONLY"


class LabelStatus(str, Enum):
    """
    Semantic resolution status of a labeled detection.
    Explicitly distinguishes verified events from stationary thermal sources.
    """
    CONFIRMED_EVENT = "CONFIRMED_EVENT"
    PROBABLE_EVENT = "PROBABLE_EVENT"
    PERSISTENT_THERMAL_SOURCE = "PERSISTENT_THERMAL_SOURCE"
    CONTEXT_ONLY = "CONTEXT_ONLY"
    AMBIGUOUS = "AMBIGUOUS"
    UNLABELED = "UNLABELED"
    CONFLICTED = "CONFLICTED"


class SourceType(str, Enum):
    """
    Taxonomy of independent reference sources.
    """
    STATUTORY_DISCLOSURE = "STATUTORY_DISCLOSURE"
    REGULATORY_ORDER = "REGULATORY_ORDER"
    NEWS_EVENT = "NEWS_EVENT"
    SATELLITE_BURN_PRODUCT = "SATELLITE_BURN_PRODUCT"
    INFRASTRUCTURE_CATALOG = "INFRASTRUCTURE_CATALOG"
    GROUND_INSPECTION = "GROUND_INSPECTION"
    VOLCANIC_CATALOG = "VOLCANIC_CATALOG"
    MINING_PERIMETER = "MINING_PERIMETER"
    OPTICAL_VERIFICATION = "OPTICAL_VERIFICATION"


class LocationPrecision(str, Enum):
    """
    Spatial precision category of the reference location.
    """
    EXACT_POINT = "EXACT_POINT"              # Sub-100m geodetic point (e.g. stack, GPS)
    PLOT_POLYGON = "PLOT_POLYGON"            # Parcel / cadastral boundary (e.g. brick kiln, field)
    FACILITY_CENTROID = "FACILITY_CENTROID"  # Industrial estate / factory complex centroid
    DISTRICT_CENTROID = "DISTRICT_CENTROID"  # Broad district / administrative center


class OfficialnessLevel(str, Enum):
    """
    Hierarchy of authority for reference data.
    """
    STATUTORY_GOVERNMENT = "STATUTORY_GOVERNMENT"  # Legal filings, gazette notices, SPCB
    SCIENTIFIC_AGENCY = "SCIENTIFIC_AGENCY"        # FSI, ISRO, ICAR-IARI, World Bank, EOG
    COMMERCIAL_MEDIA = "COMMERCIAL_MEDIA"          # News wire, verified press reports
    CROWDSOURCED = "CROWDSOURCED"                  # OpenStreetMap, citizen science


@dataclass(frozen=True)
class NormalizedEvidence:
    """
    Canonical normalized evidence record conforming to STEP 2 specifications.
    Every reference dataset must be transformed into this structure.
    """
    evidence_id: str
    source_name: str
    source_type: SourceType
    evidence_category: EvidenceCategory
    class_candidate: TargetClass
    event_datetime_start: datetime  # Must be timezone-aware (UTC)
    event_datetime_end: datetime    # Must be timezone-aware (UTC)
    latitude: float                 # Centroid latitude in decimal degrees
    longitude: float                # Centroid longitude in decimal degrees
    location_precision: LocationPrecision
    officialness_level: OfficialnessLevel
    confidence_basis: str
    geometry_wkt: Optional[str] = None
    event_description: Optional[str] = None
    source_url: Optional[str] = None
    source_record_id: Optional[str] = None
    retrieval_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    license_notes: Optional[str] = None
    metadata_json: Optional[str] = None

    def __post_init__(self) -> None:
        # Enforce timezone-aware datetimes
        if self.event_datetime_start.tzinfo is None:
            raise ValueError(f"event_datetime_start must be timezone-aware for evidence {self.evidence_id}")
        if self.event_datetime_end.tzinfo is None:
            raise ValueError(f"event_datetime_end must be timezone-aware for evidence {self.evidence_id}")
        if self.event_datetime_start > self.event_datetime_end:
            raise ValueError(f"event_datetime_start cannot be after event_datetime_end for evidence {self.evidence_id}")
        # Enforce valid coordinate ranges
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"Invalid longitude: {self.longitude}")


@dataclass
class EvidenceMatch:
    """
    Represents a candidate match between a FIRMS detection and an evidence record.
    """
    detection_id: str
    evidence_id: str
    source_name: str
    evidence_category: EvidenceCategory
    candidate_class: TargetClass
    spatial_distance_km: float
    temporal_difference_hours: float
    matching_method: str
    base_confidence: float
    evidence_tier: ConfidenceTier
    evidence_ref: NormalizedEvidence


@dataclass
class FinalLabelRecord:
    """
    Final output label record keyed 1:1 by detection_id.
    Conforms to Section 4 of label_matching_plan.md and Step 9.
    """
    detection_id: str
    label_class: int
    confidence_score: float
    confidence_tier: str
    label_status: str
    evidence_category: str
    evidence_count: int
    primary_evidence_id: Optional[str]
    primary_source: Optional[str]
    secondary_evidence_ids: List[str]
    matching_method: str
    spatial_distance_km: float
    temporal_difference_hours: float
    is_supervised_target: bool
    downgrade_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detection_id": self.detection_id,
            "label_class": self.label_class,
            "confidence_score": round(self.confidence_score, 4),
            "confidence_tier": self.confidence_tier,
            "label_status": self.label_status,
            "evidence_category": self.evidence_category,
            "evidence_count": self.evidence_count,
            "primary_evidence_id": self.primary_evidence_id or "NONE",
            "primary_source": self.primary_source or "NONE",
            "secondary_evidence_ids": ",".join(self.secondary_evidence_ids) if self.secondary_evidence_ids else "NONE",
            "matching_method": self.matching_method,
            "spatial_distance_km": round(self.spatial_distance_km, 4),
            "temporal_difference_hours": round(self.temporal_difference_hours, 4),
            "is_supervised_target": self.is_supervised_target,
            "downgrade_reason": self.downgrade_reason or "NONE",
        }
