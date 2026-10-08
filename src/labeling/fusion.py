"""
Evidence fusion engine combining normalized matches into final audited label records.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from src.labeling.conflicts import resolve_match_conflicts
from src.labeling.schemas import (
    ConfidenceTier,
    EvidenceCategory,
    EvidenceMatch,
    FinalLabelRecord,
    LabelStatus,
    TargetClass,
)


def fuse_detection_matches(
    detection_id: str,
    matches: List[EvidenceMatch],
) -> FinalLabelRecord:
    """
    Fuses all candidate evidence matches for a single FIRMS detection into a canonical FinalLabelRecord.
    Handles UNLABELED cases explicitly when matches list is empty.
    Enforces strict separation of EVENT_EVIDENCE from STATIC_SOURCE_EVIDENCE and CONTEXT_ONLY.
    """
    if not matches:
        # Step 5 & Non-Negotiable rule: Unmatched detections MUST be explicitly UNLABELED (Class 0, Tier D)
        return FinalLabelRecord(
            detection_id=detection_id,
            label_class=int(TargetClass.UNLABELED),
            confidence_score=0.0,
            confidence_tier=ConfidenceTier.TIER_D.value,
            label_status=LabelStatus.UNLABELED.value,
            evidence_category="NONE",
            evidence_count=0,
            primary_evidence_id=None,
            primary_source=None,
            secondary_evidence_ids=[],
            matching_method="NO_INDEPENDENT_EVIDENCE_FOUND",
            spatial_distance_km=-1.0,
            temporal_difference_hours=-1.0,
            is_supervised_target=False,
            downgrade_reason=None,
        )

    # Multi-evidence or single-evidence resolution
    resolved_class, resolved_tier, resolved_status, conf_score, primary_match, reason = resolve_match_conflicts(matches)

    secondary_ids = [m.evidence_id for m in matches if m.evidence_id != primary_match.evidence_id]

    # Semantic evaluation based on EvidenceCategory
    if resolved_status == LabelStatus.CONFLICTED:
        final_class = int(TargetClass.UNLABELED)
        final_tier = ConfidenceTier.TIER_C.value
        final_status = LabelStatus.CONFLICTED.value
        final_conf = 0.50
        is_supervised = False
        downgrade_reason = reason
        category_str = primary_match.evidence_category.value

    elif primary_match.evidence_category == EvidenceCategory.CONTEXT_ONLY:
        # Rule: Village centroid / regional context cannot create positive event label
        final_class = int(TargetClass.UNLABELED)
        final_conf = 0.0
        final_tier = ConfidenceTier.TIER_D.value
        final_status = LabelStatus.CONTEXT_ONLY.value
        is_supervised = False
        category_str = EvidenceCategory.CONTEXT_ONLY.value
        downgrade_reason = (
            f"CONTEXT_ONLY_EXCLUSION: Administrative village/district centroid match "
            f"({primary_match.spatial_distance_km:.2f} km) represents regional context "
            f"without parcel-level event proof; excluded from positive target labels."
        )

    elif primary_match.evidence_category == EvidenceCategory.STATIC_SOURCE_EVIDENCE:
        # Rule: Static thermal sources cannot automatically become acute fire events
        # Proximity to static infrastructure confirms chronic/background heating, never Tier A confirmed event
        final_class = int(TargetClass.OTHER_THERMAL_SOURCE)
        final_conf = conf_score
        final_tier = ConfidenceTier.TIER_B.value
        final_status = LabelStatus.PERSISTENT_THERMAL_SOURCE.value
        is_supervised = False  # Not an acute fire event; cannot be a positive supervised fire target
        category_str = EvidenceCategory.STATIC_SOURCE_EVIDENCE.value

        rec_id = ((primary_match.evidence_ref.source_record_id or "") + "_" + primary_match.evidence_id).upper()
        if "COAL" in rec_id or "JHARIA" in rec_id or "RANIGANJ" in rec_id:
            downgrade_reason = (
                "STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indicates chronic background "
                "coal seam heating, not a confirmed acute fire event. Stripped of Tier A."
            )
        elif "POWER" in rec_id or "MUNDRA" in rec_id or "VINDHYACHAL" in rec_id:
            downgrade_reason = (
                "STATIC_SOURCE_PROXIMITY: Proximity to thermal power station indicates operational "
                "heat dissipation, not an emergency fire incident. Stripped of Tier A."
            )
        elif "VOLCANO" in rec_id or "BARREN" in rec_id:
            downgrade_reason = (
                "PERSISTENT_VOLCANIC_EMISSION: Active volcanic vent produces continuous basaltic "
                "thermal emission, not an acute disaster event. Preserved as persistent thermal source."
            )
        elif "FLARE" in rec_id:
            downgrade_reason = (
                "PERSISTENT_FLARING_STACK: Industrial flare stack operational combustion, "
                "not an uncontained fire event. Preserved as persistent thermal source."
            )
        else:
            downgrade_reason = (
                "STATIC_SOURCE_PROXIMITY: Proximity to stationary thermal infrastructure "
                "without acute event verification."
            )

    elif primary_match.evidence_category == EvidenceCategory.EVENT_EVIDENCE:
        final_class = int(resolved_class)
        final_conf = conf_score
        category_str = EvidenceCategory.EVENT_EVIDENCE.value
        if resolved_tier == ConfidenceTier.TIER_A:
            final_tier = ConfidenceTier.TIER_A.value
            final_status = LabelStatus.CONFIRMED_EVENT.value
            downgrade_reason = None
        else:
            final_tier = ConfidenceTier.TIER_B.value
            final_status = LabelStatus.PROBABLE_EVENT.value
            downgrade_reason = (
                "PROBABLE_EVENT: Corroborated event without contemporaneous high-resolution "
                "optical burn scar confirmation"
            )
        is_supervised = bool(final_class != int(TargetClass.UNLABELED))

    else:
        # Default fallback
        final_class = int(resolved_class)
        final_conf = conf_score
        final_tier = resolved_tier.value
        final_status = resolved_status.value
        category_str = primary_match.evidence_category.value
        is_supervised = bool(
            final_class != int(TargetClass.UNLABELED)
            and final_status in (LabelStatus.CONFIRMED_EVENT.value, LabelStatus.PROBABLE_EVENT.value)
        )
        downgrade_reason = None

    return FinalLabelRecord(
        detection_id=detection_id,
        label_class=final_class,
        confidence_score=final_conf,
        confidence_tier=final_tier,
        label_status=final_status,
        evidence_category=category_str,
        evidence_count=len(matches),
        primary_evidence_id=primary_match.evidence_id,
        primary_source=primary_match.source_name,
        secondary_evidence_ids=secondary_ids,
        matching_method=primary_match.matching_method,
        spatial_distance_km=primary_match.spatial_distance_km,
        temporal_difference_hours=primary_match.temporal_difference_hours,
        is_supervised_target=is_supervised,
        downgrade_reason=downgrade_reason,
    )
