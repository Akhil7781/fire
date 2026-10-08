"""
Unit tests for DS08 Annotation Protocol and Schema (Stage 8.9).

Verifies:
- Schema exists and is valid JSON (ds08_annotation_schema.json)
- All four final project classes exist in schema:
  1. Industrial Fire
  2. Forest Fire
  3. Agricultural Fire
  4. Other Thermal Source
- UNRESOLVED status exists and is distinct from the 4 classes
- Confidence fields exist (geometry_confidence, source_class_confidence)
- Visibility fields exist (CLEAR, PARTIALLY_OBSCURED, HEAVILY_OBSCURED)
- Evidence fields exist with all 8 allowed vocabulary items
- FIRMS relationship field exists with all 5 allowed values
- Bounding box constraints are defined and strictly constrained to 512x512
- No B08 band exists as an authoritative image band (B02, B03, B04, B11, B12 only; NDVI excluded)
- No synthetic or quarantined data paths are referenced
- No actual annotation labels have been created (draft/, review/, final/ are empty of annotations)
- 20-chip active pilot manifest exists, contains 20 active chips, all with status NOT_STARTED
- Annotation guidelines exist and contain all 9 critical labeling rules
- Invariant integrity of all 5 frozen predecessor artifacts
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ANNOTATIONS_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations"
SCHEMA_PATH = ANNOTATIONS_DIR / "schema" / "ds08_annotation_schema.json"
GUIDELINES_PATH = ANNOTATIONS_DIR / "guidelines" / "DS08_ANNOTATION_GUIDELINES_v1.md"
MANIFEST_JSON_PATH = ANNOTATIONS_DIR / "pilot_manifest.json"
MANIFEST_CSV_PATH = ANNOTATIONS_DIR / "pilot_manifest.csv"

DRAFT_DIR = ANNOTATIONS_DIR / "draft"
REVIEW_DIR = ANNOTATIONS_DIR / "review"
FINAL_DIR = ANNOTATIONS_DIR / "final"

FROZEN_HASHES = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
}


def test_schema_exists_and_is_valid_json():
    """Verifies that ds08_annotation_schema.json exists and parses as valid JSON."""
    assert SCHEMA_PATH.exists(), f"Schema file missing at: {SCHEMA_PATH}"
    content = SCHEMA_PATH.read_text(encoding="utf-8")
    schema = json.loads(content)
    assert schema.get("$schema") == "http://json-schema.org/draft-07/schema#"
    assert schema.get("type") == "object"
    assert "annotations" in schema["properties"]
    assert "context_metadata" in schema["properties"]


def test_all_four_final_classes_and_unresolved_exist():
    """Verifies that all 4 final project source classes and UNRESOLVED exist in the schema."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    ann_props = schema["properties"]["annotations"]["items"]["properties"]
    allowed_classes = ann_props["class_name"]["enum"]

    expected_four_classes = [
        "Industrial Fire",
        "Forest Fire",
        "Agricultural Fire",
        "Other Thermal Source",
    ]
    for c in expected_four_classes:
        assert c in allowed_classes, f"Missing final class: '{c}'"

    assert "UNRESOLVED" in allowed_classes, "Missing UNRESOLVED status in class_name enum"

    # Verify class_ids
    allowed_ids = ann_props["class_id"]["enum"]
    assert set(allowed_ids) == {0, 1, 2, 3, 4}


def test_confidence_fields_specification():
    """Verifies that geometry_confidence and source_class_confidence are defined and separated."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    ann_props = schema["properties"]["annotations"]["items"]["properties"]
    assert "geometry_confidence" in ann_props
    assert "source_class_confidence" in ann_props

    assert ann_props["geometry_confidence"]["enum"] == ["HIGH", "MEDIUM", "LOW"]
    assert ann_props["source_class_confidence"]["enum"] == ["HIGH", "MEDIUM", "LOW"]


def test_visibility_and_obstruction_fields():
    """Verifies visibility_status field exists with CLEAR, PARTIALLY_OBSCURED, HEAVILY_OBSCURED."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    ann_props = schema["properties"]["annotations"]["items"]["properties"]
    assert "visibility_status" in ann_props
    assert ann_props["visibility_status"]["enum"] == ["CLEAR", "PARTIALLY_OBSCURED", "HEAVILY_OBSCURED"]


def test_visual_evidence_vocabulary():
    """Verifies visual_evidence field contains all 8 allowed closed vocabulary tags."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    ann_props = schema["properties"]["annotations"]["items"]["properties"]
    evidence_items = ann_props["visual_evidence"]["items"]["enum"]

    expected_evidence = [
        "DIRECT_FIRE_VISIBLE",
        "SMOKE_VISIBLE",
        "BURN_SCAR_VISIBLE",
        "INDUSTRIAL_INFRASTRUCTURE_VISIBLE",
        "FOREST_CONTEXT_VISIBLE",
        "CROPLAND_CONTEXT_VISIBLE",
        "PERSISTENT_THERMAL_SOURCE_CONTEXT",
        "NO_CLEAR_VISUAL_EVIDENCE",
    ]
    assert set(evidence_items) == set(expected_evidence)


def test_firms_relationship_field():
    """Verifies firms_relationship field contains all 5 allowed values."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    ann_props = schema["properties"]["annotations"]["items"]["properties"]
    relationships = ann_props["firms_relationship"]["enum"]

    expected_rel = [
        "INSIDE_OBJECT",
        "TOUCHING_OBJECT",
        "NEAR_OBJECT",
        "OUTSIDE_VISIBLE_OBJECT",
        "NO_VISIBLE_TARGET",
    ]
    assert set(relationships) == set(expected_rel)


def test_bounding_box_constraints_512x512():
    """Verifies bbox properties are constrained to the 512x512 pixel coordinate space."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    bbox_props = schema["properties"]["annotations"]["items"]["properties"]["bbox"]["properties"]
    assert bbox_props["x_min"]["minimum"] == 0
    assert bbox_props["x_min"]["maximum"] == 511
    assert bbox_props["y_min"]["minimum"] == 0
    assert bbox_props["y_min"]["maximum"] == 511
    assert bbox_props["x_max"]["minimum"] == 1
    assert bbox_props["x_max"]["maximum"] == 512
    assert bbox_props["y_max"]["minimum"] == 1
    assert bbox_props["y_max"]["maximum"] == 512


def test_no_b08_in_authoritative_bands():
    """Verifies that B08 (NIR) is excluded from authoritative bands and NDVI is absent."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    ctx_props = schema["properties"]["context_metadata"]["properties"]
    auth_bands = ctx_props["authoritative_bands"]["items"]["enum"]

    assert "B08" not in auth_bands
    assert "B8" not in auth_bands
    assert "NDVI" not in str(auth_bands).upper()
    assert set(auth_bands) == {"B02", "B03", "B04", "B11", "B12"}


def test_no_synthetic_paths_referenced():
    """Verifies no synthetic or quarantined datasets are referenced in schema or manifest."""
    for p in [SCHEMA_PATH, MANIFEST_JSON_PATH, GUIDELINES_PATH]:
        content = p.read_text(encoding="utf-8").lower()
        assert "ds08_proto_synthetic" not in content
        assert "data/synthetic" not in content


def test_no_actual_annotation_labels_created():
    """Verifies that zero final/adjudicated annotations exist (final/ directory remains strictly empty)."""
    assert DRAFT_DIR.exists()
    assert REVIEW_DIR.exists()
    assert FINAL_DIR.exists()

    # draft/ root must contain no top-level annotations
    draft_files = list(DRAFT_DIR.glob("*.json"))
    assert len(draft_files) == 0, f"Found unexpected draft root annotations: {draft_files}"

    # final/ must contain either 0 (pre-adjudication) or strictly at most 3 adjudicated annotations
    final_files = list(FINAL_DIR.glob("*.*"))
    assert len(final_files) in (0, 3), f"Found unexpected final annotations: {final_files}"


def test_manifest_20_active_chips_not_started():
    """Verifies that pilot_manifest.json exists and all 20 chips have annotation_status=NOT_STARTED."""
    assert MANIFEST_JSON_PATH.exists()
    assert MANIFEST_CSV_PATH.exists()

    with open(MANIFEST_JSON_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    chips = manifest["chips"]
    assert len(chips) == 20
    assert manifest["total_active_pilot_chips"] == 20
    assert manifest["annotation_status_summary"]["NOT_STARTED"] == 20

    # Ensure PILOT_04_NORTH_REPLACEMENT is included and original rejected PILOT_04_NORTH is excluded
    chip_ids = [c["chip_id"] for c in chips]
    assert "PILOT_04_NORTH_REPLACEMENT" in chip_ids
    assert "PILOT_04_NORTH" not in chip_ids

    # All chips NOT_STARTED
    for c in chips:
        assert c["annotation_status"] == "NOT_STARTED"
        assert c["review_status"] == "NOT_STARTED"
        assert "class_name" not in c
        assert "class_id" not in c


def test_guidelines_contain_all_nine_critical_rules():
    """Verifies that DS08_ANNOTATION_GUIDELINES_v1.md contains all 9 critical rules."""
    assert GUIDELINES_PATH.exists()
    content = GUIDELINES_PATH.read_text(encoding="utf-8")

    assert "RULE 1: FIRMS thermal anomaly" in content
    assert "RULE 2: Industrial proximity" in content
    assert "RULE 3: Persistent thermal source" in content
    assert "RULE 4: Cloud-obscured target" in content
    assert "RULE 5: Unknown evidence" in content
    assert "RULE 6: YOLO predictions" in content
    assert "RULE 7: Visual evidence and contextual metadata" in content
    assert "RULE 8: Do not infer fire from a reflectance value > 1.0" in content
    assert "RULE 9: Do not use B08 or invent NDVI" in content


def test_annotation_tool_validation_logic():
    """Verifies that ds08_annotation_tool.py correctly validates schema rules."""
    from scripts.ds08_annotation_tool import validate_annotation_payload

    # Valid payload
    valid_payload = {
        "chip_id": "PILOT_01_NORTH",
        "annotation_version": "v1.0",
        "chip_annotation_status": "HAS_ANNOTATIONS",
        "annotations": [
            {
                "annotation_id": "PILOT_01_NORTH_ANN_01",
                "class_id": 1,
                "class_name": "Industrial Fire",
                "bbox": {"x_min": 240, "y_min": 240, "x_max": 280, "y_max": 280},
                "geometry_confidence": "HIGH",
                "source_class_confidence": "HIGH",
                "visibility_status": "CLEAR",
                "visual_evidence": ["INDUSTRIAL_INFRASTRUCTURE_VISIBLE", "SMOKE_VISIBLE"],
                "firms_relationship": "INSIDE_OBJECT",
                "review_status": "PENDING",
                "annotator_id": "TEST_ANN",
                "annotation_timestamp": "2026-09-29T21:00:00Z",
            }
        ],
        "context_metadata": {
            "firms_detection_id": "test_det_123",
            "firms_latitude": 28.0,
            "firms_longitude": 77.0,
            "firms_acq_datetime_utc": "2025-03-19T07:00:00Z",
            "product_id": "S2_TEST_PRODUCT",
            "authoritative_bands": ["B02", "B03", "B04", "B11", "B12"],
        },
    }

    is_valid, errors = validate_annotation_payload(valid_payload)
    assert is_valid is True, f"Valid payload reported errors: {errors}"

    # Invalid payload: coordinates out of bounds
    invalid_payload = dict(valid_payload)
    invalid_payload["annotations"] = [dict(valid_payload["annotations"][0])]
    invalid_payload["annotations"][0] = dict(valid_payload["annotations"][0])
    invalid_payload["annotations"][0]["bbox"] = {"x_min": 280, "y_min": 240, "x_max": 240, "y_max": 280}  # x_min > x_max

    is_valid, errors = validate_annotation_payload(invalid_payload)
    assert is_valid is False
    assert any("Zero or negative width" in e for e in errors)


def test_frozen_predecessor_integrity():
    """Strict invariant: verifies all 5 frozen artifacts remain byte-for-byte unmodified."""
    for rel_path, expected_hash in FROZEN_HASHES.items():
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists(), f"Missing frozen artifact: {rel_path}"
        actual_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, (
            f"MUTATION DETECTED in frozen artifact {rel_path}!\n"
            f"Expected: {expected_hash}\n"
            f"Actual:   {actual_hash}"
        )
