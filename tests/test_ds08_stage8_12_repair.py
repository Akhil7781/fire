"""
Unit tests for DS08 Annotation Pipeline Repair and Provenance Verification (Stage 8.12).

Verifies Section 13 Provenance Requirements:
1. Stage 8.11 quarantined files cannot enter training datasets.
2. Invalid scripted annotations cannot enter agreement calculations.
3. Manual annotation files contain explicit human-annotation provenance and blank task templates.
4. No model prediction fields exist.
5. No auto-label fields exist.
6. A1 and A2 directories remain strictly independent and isolated.
7. The three Stage 8.10B-C final files remain unchanged.
8. Frozen predecessor model and fusion hashes remain unchanged.
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

from scripts.ds08_annotation_tool import (
    AFFECTED_15_CHIPS,
    get_annotator_dir,
    load_manual_template,
    save_manual_annotation,
    validate_annotation_payload,
    validate_manual_annotation_provenance,
)

ANNOTATIONS_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations"
DRAFT_DIR = ANNOTATIONS_DIR / "draft"
MANUAL_DIR = ANNOTATIONS_DIR / "manual"
QUARANTINE_DIR = ANNOTATIONS_DIR / "quarantine"
QUAR_MANIFEST_PATH = QUARANTINE_DIR / "stage8_11_script_generated" / "quarantine_manifest.json"
FINAL_DIR = ANNOTATIONS_DIR / "final"

FROZEN_ADJUDICATED_HASHES = {
    "PILOT_01_NORTH_adjudicated_v1.json": "cad036e10fd48bfd54f3d55c11a645eef0a0ddfa53f30c23dee3bff6ef84f489",
    "PILOT_13_EAST_adjudicated_v1.json": "73bc30817d059a8f138625033680f81c226ef4936c71dea9cccb4ce40a495922",
    "PILOT_17_WEST_adjudicated_v1.json": "3f5e311c9a88e37b70b78a5ba0623508c8144395c0c1493f13cf7e1975aa473b",
}

FROZEN_PREDECESSOR_HASHES = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
}


def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def test_quarantine_integrity_and_manifest():
    """Verify that Stage 8.11 quarantined files are intact and machine-readable metadata is set."""
    quar_dir = QUARANTINE_DIR / "stage8_11_script_generated"
    assert quar_dir.exists(), f"Quarantine directory {quar_dir} does not exist"

    doc_path = QUARANTINE_DIR / "STAGE8_11_INVALID_SCRIPT_GENERATED.md"
    assert doc_path.exists(), "Missing STAGE8_11_INVALID_SCRIPT_GENERATED.md"

    assert QUAR_MANIFEST_PATH.exists(), f"Missing quarantine manifest: {QUAR_MANIFEST_PATH}"
    with open(QUAR_MANIFEST_PATH, "r", encoding="utf-8") as f:
        qmeta = json.load(f)

    assert qmeta["status"] == "INVALID_SCRIPT_GENERATED"
    assert qmeta["human_verified"] is False
    assert qmeta["eligible_for_training"] is False
    assert qmeta["eligible_for_validation"] is False
    assert qmeta["eligible_for_evaluation"] is False
    assert qmeta["eligible_for_agreement"] is False
    assert qmeta["eligible_for_adjudication"] is False
    assert qmeta["total_quarantined_files"] == 30
    assert len(qmeta["quarantined_files"]) == 30

    # Verify every file on disk matches hash in manifest
    for item in qmeta["quarantined_files"]:
        fpath = PROJECT_ROOT / item["relative_path"]
        assert fpath.exists(), f"Quarantined file missing: {fpath}"
        actual_hash = compute_sha256(fpath)
        assert actual_hash == item["sha256"], f"Hash mismatch for quarantined file {fpath.name}"


def test_quarantined_files_excluded_from_draft_and_training():
    """Verify that active draft directory contains zero quarantined Stage 8.11 files."""
    a1_draft_files = sorted([f.name for f in (DRAFT_DIR / "annotator_1").glob("*.json")])
    a2_draft_files = sorted([f.name for f in (DRAFT_DIR / "annotator_2").glob("*.json")])

    # Must contain strictly the 5 Stage 8.10A files
    expected_draft = [
        "PILOT_01_NORTH",
        "PILOT_05_CENTRAL",
        "PILOT_09_SOUTH",
        "PILOT_13_EAST",
        "PILOT_17_WEST",
    ]
    assert len(a1_draft_files) == 5
    assert len(a2_draft_files) == 5

    for cid in expected_draft:
        assert f"{cid}_annotator1.json" in a1_draft_files
        assert f"{cid}_annotator2.json" in a2_draft_files

    # Ensure none of the 15 affected chips exist in draft/
    for cid in AFFECTED_15_CHIPS:
        assert f"{cid}_annotator1.json" not in a1_draft_files
        assert f"{cid}_annotator2.json" not in a2_draft_files


def test_manual_workspace_blank_templates():
    """Verify manual workspace templates have no pre-populated labels or bboxes."""
    a1_dir = MANUAL_DIR / "annotator_1"
    a2_dir = MANUAL_DIR / "annotator_2"
    assert a1_dir.exists()
    assert a2_dir.exists()

    a1_files = sorted(list(a1_dir.glob("*.json")))
    a2_files = sorted(list(a2_dir.glob("*.json")))
    assert len(a1_files) == 15
    assert len(a2_files) == 15

    for adir, ann_sub, expected_id in [
        (a1_dir, "annotator1", "HUMAN_ANNOTATOR_01"),
        (a2_dir, "annotator2", "HUMAN_ANNOTATOR_02"),
    ]:
        for cid in AFFECTED_15_CHIPS:
            fpath = adir / f"{cid}_{ann_sub}.json"
            assert fpath.exists(), f"Missing template {fpath.name}"
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Strict blank template requirements
            assert data["task_status"] == "PENDING_MANUAL_INPUT"
            assert data["human_verified"] is False
            assert data["chip_annotation_status"] is None, f"{fpath.name} must have null chip_annotation_status"
            assert data["annotations"] == [], f"{fpath.name} must have empty annotations array"
            assert data["annotator_id"] == expected_id

            # Audit interaction metadata initialized
            assert "interaction_audit" in data
            audit = data["interaction_audit"]
            assert audit["interface_version"] == "v1.0_manual"
            assert audit["bbox_creation_actions"] == 0
            assert audit["save_events"] == 0

            # FIRMS context disclaimer
            ctx = data["context_metadata"]
            assert "firms_context_disclaimer" in ctx
            assert "FIRMS CONTEXT" in ctx["firms_context_disclaimer"]
            assert "NOT GROUND TRUTH" in ctx["firms_context_disclaimer"]


def test_no_model_prediction_or_auto_label_fields():
    """Verify that manual templates contain ZERO model prediction or auto-labeling fields."""
    forbidden_tokens = [
        "model_predicted",
        "yolo_",
        "predicted_class",
        "auto_label",
        "synthetic",
        "simulated",
        "auto_detected",
        "suggested_class",
        "recommended_class",
    ]

    for adir in [MANUAL_DIR / "annotator_1", MANUAL_DIR / "annotator_2"]:
        for fpath in adir.glob("*.json"):
            content = fpath.read_text(encoding="utf-8")
            for token in forbidden_tokens:
                assert token not in content, f"Forbidden token '{token}' found in {fpath.name}"


def test_annotator_independence_and_isolation():
    """Verify that annotator_1 and annotator_2 workspaces are strictly isolated."""
    a1_dir = get_annotator_dir("annotator_1")
    a2_dir = get_annotator_dir("annotator_2")
    assert a1_dir != a2_dir
    assert a1_dir.name == "annotator_1"
    assert a2_dir.name == "annotator_2"

    with pytest.raises(ValueError):
        get_annotator_dir("annotator_3")
    with pytest.raises(ValueError):
        get_annotator_dir("shared")

    # Verify templates load independently
    t1 = load_manual_template("annotator_1", "PILOT_02_NORTH")
    t2 = load_manual_template("annotator_2", "PILOT_02_NORTH")
    assert t1["annotator_id"] == "HUMAN_ANNOTATOR_01"
    assert t2["annotator_id"] == "HUMAN_ANNOTATOR_02"


def test_manual_annotation_provenance_validation():
    """Verify validation logic for manual annotation payloads."""
    # Blank template is pending, cannot pass as completed annotation
    t1 = load_manual_template("annotator_1", "PILOT_02_NORTH")
    valid, errors = validate_manual_annotation_provenance(t1)
    assert valid is False
    assert any("human_verified" in e for e in errors)

    # Valid manual completed payload
    valid_payload = {
        "chip_id": "PILOT_02_NORTH",
        "annotation_version": "v1.0",
        "chip_annotation_status": "NO_VISIBLE_TARGET",
        "human_verified": True,
        "interaction_audit": {
            "interface_version": "v1.0_manual",
            "save_events": 1,
        },
        "annotations": [],
        "context_metadata": {
            "firms_context_disclaimer": "FIRMS CONTEXT — NOT GROUND TRUTH",
            "firms_detection_id": "0e0d9718f34bb069b02a4216d8525de8de8d2b7ed93b7c4c906ced898c959f5a",
            "firms_latitude": 28.80476,
            "firms_longitude": 77.26028,
            "firms_acq_datetime_utc": None,
            "product_id": "S2B_MSIL2A_20250324T052649_N0511_R105_T43RGM_20250324T074123.SAFE",
            "authoritative_bands": ["B02", "B03", "B04", "B11", "B12"],
        },
    }
    valid, errors = validate_manual_annotation_provenance(valid_payload)
    assert valid is True, f"Expected valid payload: {errors}"

    # Injected forbidden model field must fail
    invalid_payload = dict(valid_payload)
    invalid_payload["model_predicted_box"] = [10, 10, 50, 50]
    valid, errors = validate_manual_annotation_provenance(invalid_payload)
    assert valid is False
    assert any("Forbidden" in e for e in errors)


def test_three_stage8_10b_final_adjudicated_files_unmodified():
    """Verify that final/ contains EXACTLY the 3 Stage 8.10B adjudicated files."""
    final_files = sorted([f.name for f in FINAL_DIR.glob("*.json")])
    assert final_files == sorted(list(FROZEN_ADJUDICATED_HASHES.keys()))

    for fname, exp_hash in FROZEN_ADJUDICATED_HASHES.items():
        fpath = FINAL_DIR / fname
        assert fpath.exists(), f"Final file missing: {fname}"
        actual = compute_sha256(fpath)
        assert actual == exp_hash, f"Hash mismatch for {fname}: expected {exp_hash}, got {actual}"


def test_frozen_predecessors_unmodified():
    """Verify that all 5 frozen model weights and fusion parquet files remain byte-for-byte identical."""
    for rel_path, expected_hash in FROZEN_PREDECESSOR_HASHES.items():
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists(), f"Predecessor artifact missing: {rel_path}"
        actual_hash = compute_sha256(full_path)
        assert actual_hash == expected_hash, f"Hash mismatch for {rel_path}: expected {expected_hash}, got {actual_hash}"
