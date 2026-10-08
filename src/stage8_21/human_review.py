"""
Stage 8.21 - Human Review Workflow and Annotation Schema
Provides schema validation, review templates, and persistence for visual human review.
Enforces strict separation between expected_target_class and human_observed_class.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

VALID_PRIMARY_CLASSES = [
    "Industrial Fire",
    "Forest Fire",
    "Agricultural Fire",
    "Other Thermal Source/Persistent Non-Biomass Thermal Source",
    "Uncertain",
]

VALID_CONFIDENCES = ["High", "Medium", "Low"]

VALID_EVIDENCE_TYPES = [
    "visible industrial infrastructure",
    "vegetation/burn pattern",
    "agricultural field context",
    "persistent/non-biomass context",
    "smoke/fire visual evidence",
    "thermal-source surroundings",
    "inconclusive",
]

VALID_DECISIONS = ["Accepted", "Needs Review", "Rejected"]


def validate_annotation_record(record: Dict[str, Any]) -> bool:
    """Validates that an annotation record adheres to Stage 8.21 schema and rules."""
    req_fields = [
        "sample_id",
        "expected_target_class",
        "human_observed_class",
        "confidence",
        "evidence_notes",
        "reviewer_decision",
        "reviewer_id",
        "review_timestamp_utc",
    ]
    for f in req_fields:
        if f not in record:
            raise KeyError(f"Missing required annotation field: {f}")

    if record["human_observed_class"] not in VALID_PRIMARY_CLASSES:
        raise ValueError(f"Invalid human_observed_class: {record['human_observed_class']}")

    if record["confidence"] not in VALID_CONFIDENCES:
        raise ValueError(f"Invalid confidence: {record['confidence']}")

    if record["reviewer_decision"] not in VALID_DECISIONS:
        raise ValueError(f"Invalid reviewer_decision: {record['reviewer_decision']}")

    for note in record.get("evidence_notes", []):
        if note not in VALID_EVIDENCE_TYPES:
            raise ValueError(f"Invalid evidence note: {note}")

    return True


def save_review_annotations(
    annotations: List[Dict[str, Any]],
    output_parquet: Path,
    output_json: Path,
) -> pd.DataFrame:
    """Validates and persists human review annotations in Parquet and JSON."""
    for ann in annotations:
        validate_annotation_record(ann)

    output_parquet = Path(output_parquet)
    output_json = Path(output_json)
    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(annotations, f, indent=2)

    df = pd.DataFrame(annotations)
    df_parquet = df.copy()
    df_parquet["evidence_notes"] = df_parquet["evidence_notes"].apply(lambda x: "; ".join(x) if isinstance(x, list) else str(x))
    df_parquet.to_parquet(output_parquet, index=False)

    return df
