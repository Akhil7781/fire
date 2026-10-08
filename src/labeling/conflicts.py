"""
Deterministic conflict resolution logic for multi-class evidence matches.
Implements the 4-rule priority protocol from label_matching_plan.md Section 3.
"""

from __future__ import annotations

from typing import List, Tuple
from src.labeling.schemas import (
    ConfidenceTier,
    EvidenceCategory,
    EvidenceMatch,
    LabelStatus,
    OfficialnessLevel,
    SourceType,
    TargetClass,
)


def resolve_match_conflicts(
    matches: List[EvidenceMatch],
) -> Tuple[TargetClass, ConfidenceTier, LabelStatus, float, EvidenceMatch, str]:
    """
    Resolves multi-class evidence conflicts according to label_matching_plan.md:
    1. Tier Superiority: Tier A (Confirmed) strictly overrides Tier B and Tier C.
    2. Specific Incident Priority: Statutory/regulatory incident proof overrides general land cover masks.
    3. Persistent Confounder Priority: Known flares, kilns, and power stations default to Class 4 unless disaster proven.
    4. Unresolvable Tie: Equal conflicting evidence produces CONFLICTED (Class 0, Tier C).

    Returns:
        (resolved_class, resolved_tier, resolved_status, confidence_score, primary_match, resolution_reason)
    """
    if not matches:
        raise ValueError("Cannot resolve empty match list")

    def _status_for_match(m: EvidenceMatch) -> LabelStatus:
        if m.evidence_category == EvidenceCategory.STATIC_SOURCE_EVIDENCE:
            return LabelStatus.PERSISTENT_THERMAL_SOURCE
        elif m.evidence_category == EvidenceCategory.CONTEXT_ONLY:
            return LabelStatus.CONTEXT_ONLY
        elif m.evidence_tier == ConfidenceTier.TIER_A:
            return LabelStatus.CONFIRMED_EVENT
        else:
            return LabelStatus.PROBABLE_EVENT

    # Group matches by candidate class
    classes = set(m.candidate_class for m in matches)
    if len(classes) == 1:
        # No conflict - return best match
        best_match = max(matches, key=lambda m: m.base_confidence)
        status = _status_for_match(best_match)
        return best_match.candidate_class, best_match.evidence_tier, status, best_match.base_confidence, best_match, "SINGLE_CLASS_UNANIMOUS"

    # Sort matches by tier weight and base confidence
    tier_ranks = {
        ConfidenceTier.TIER_A: 4,
        ConfidenceTier.TIER_B: 3,
        ConfidenceTier.TIER_C: 2,
        ConfidenceTier.TIER_D: 1,
    }

    # Find highest tier present
    max_tier_rank = max(tier_ranks[m.evidence_tier] for m in matches)
    top_tier_matches = [m for m in matches if tier_ranks[m.evidence_tier] == max_tier_rank]
    top_tier_classes = set(m.candidate_class for m in top_tier_matches)

    # RULE 1: Tier Superiority
    if len(top_tier_classes) == 1:
        best_match = max(top_tier_matches, key=lambda m: m.base_confidence)
        status = _status_for_match(best_match)
        reason = f"RULE_1_TIER_SUPERIORITY: {best_match.evidence_tier.value} overrides lower tier candidates"
        return best_match.candidate_class, best_match.evidence_tier, status, best_match.base_confidence, best_match, reason

    # RULE 2: Specific Disaster / Incident Proof Priority
    # Verified event evidence with statutory or high officialness overrides stationary / contextual evidence
    event_matches = [
        m for m in top_tier_matches
        if m.evidence_category == EvidenceCategory.EVENT_EVIDENCE
    ]
    event_classes = set(m.candidate_class for m in event_matches)
    if len(event_classes) == 1:
        best_match = max(event_matches, key=lambda m: m.base_confidence)
        status = _status_for_match(best_match)
        reason = "RULE_2_INCIDENT_PRIORITY: Specific disaster event proof overrides general land cover/contextual masks"
        return best_match.candidate_class, best_match.evidence_tier, status, best_match.base_confidence, best_match, reason

    # RULE 3: Persistent Emitter Priority
    # If one of the conflicting classes is Class 4 (Other Thermal - flare, kiln, coal fire),
    # persistent emitter takes precedence over transient wildfire/agri assumption unless acute accident is proven
    if TargetClass.OTHER_THERMAL_SOURCE in top_tier_classes:
        c4_matches = [m for m in top_tier_matches if m.candidate_class == TargetClass.OTHER_THERMAL_SOURCE]
        best_match = max(c4_matches, key=lambda m: m.base_confidence)
        reason = "RULE_3_PERSISTENT_EMITTER_PRIORITY: Validated stationary thermal source overrides transient assumption"
        return TargetClass.OTHER_THERMAL_SOURCE, best_match.evidence_tier, LabelStatus.PERSISTENT_THERMAL_SOURCE, best_match.base_confidence, best_match, reason

    # RULE 4: Unresolvable Tie between conflicting classes of equal priority
    best_match = top_tier_matches[0]
    conflict_desc = f"Unresolvable tie between classes: {[c.name for c in top_tier_classes]}"
    return (
        TargetClass.UNLABELED,
        ConfidenceTier.TIER_C,
        LabelStatus.CONFLICTED,
        0.50,
        best_match,
        f"RULE_4_UNRESOLVABLE_TIE: {conflict_desc}",
    )
