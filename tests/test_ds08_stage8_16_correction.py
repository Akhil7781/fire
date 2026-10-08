"""
Unit tests for DS08 Stage 8.16: Controlled Human Adjudication Correction Workflow.
Covers:
- Original record immutability
- Hash verification & source manifest matching
- Evidence-flag correction & contradiction rejection
- Observation-status correction (definitive only)
- Required rationale & explicit human confirmation
- Bounding-box validation
- Correction versioning & metadata integrity
- Audit-log integrity
- Rejection of invalid/incomplete submissions
"""

import copy
import hashlib
import json
from pathlib import Path
import pytest
import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ds08_correction_tool import (
    DISPUTED_6_CHIPS,
    REVIEW_DIR,
    CORRECTIONS_DIR,
    SOURCE_MANIFEST_PATH,
    AUDIT_LOG_PATH,
    FORBIDDEN_DEFAULT_BOX,
    load_source_manifest,
    verify_original_records,
    verify_a1_a2_baseline,
    verify_frozen_predecessors,
    load_correction_chip_data,
    save_chip_correction,
    compute_correction_diff,
    validate_correction_rationale,
)


def test_1_source_manifest_integrity():
    """Verify source manifest exists and contains exact expected hashes for all 6 chips."""
    manifest = load_source_manifest()
    assert manifest["stage"] == "STAGE_8_16"
    assert len(manifest["files"]) == 6
    for cid in DISPUTED_6_CHIPS:
        assert cid in manifest["files"]
        f_info = manifest["files"][cid]
        assert len(f_info["sha256"]) == 64
        fp = REVIEW_DIR / f_info["filename"]
        assert fp.exists()
        actual_h = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert actual_h == f_info["sha256"], f"Hash mismatch for {cid} in source manifest"


def test_2_original_records_immutability():
    """Verify original records verification passes without modifications."""
    valid, errors = verify_original_records()
    assert valid is True, f"Source records compromised: {errors}"
    assert len(errors) == 0


def test_3_hash_verification_detects_tampering(tmp_path, monkeypatch):
    """Verify that verify_original_records strictly detects file modification."""
    fake_review = tmp_path / "review"
    fake_review.mkdir()
    # Copy files
    for cid in DISPUTED_6_CHIPS:
        src = REVIEW_DIR / f"{cid}_adjudicated_v1.json"
        dst = fake_review / f"{cid}_adjudicated_v1.json"
        dst.write_bytes(src.read_bytes())

    # Tamper with one file
    tampered_file = fake_review / "PILOT_03_NORTH_adjudicated_v1.json"
    tampered_file.write_bytes(tampered_file.read_bytes() + b"\n/* tampered */")

    monkeypatch.setattr("scripts.ds08_correction_tool.REVIEW_DIR", fake_review)
    valid, errors = verify_original_records()
    assert valid is False
    assert any("PILOT_03_NORTH" in e for e in errors)


def test_4_evidence_flag_correction_success(tmp_path, monkeypatch):
    """Verify successful correction removing contradictory evidence flag from PILOT_03_NORTH."""
    test_corr_dir = tmp_path / "corrections"
    test_corr_dir.mkdir()
    monkeypatch.setattr("scripts.ds08_correction_tool.CORRECTIONS_DIR", test_corr_dir)
    monkeypatch.setattr("scripts.ds08_correction_tool.AUDIT_LOG_PATH", test_corr_dir / "audit.jsonl")

    # Load original data
    data = load_correction_chip_data("PILOT_03_NORTH")
    orig_fc = data["source_record"]["final_consensus"]

    # Propose corrected box without NO_CLEAR_VISUAL_EVIDENCE
    prop_boxes = copy.deepcopy(orig_fc["annotations"])
    for b in prop_boxes:
        b["visual_evidence"] = ["DIRECT_FIRE_VISIBLE", "BURN_SCAR_VISIBLE", "FOREST_CONTEXT_VISIBLE"]

    payload = {
        "chip_id": "PILOT_03_NORTH",
        "human_confirmation": {
            "confirmed": True,
            "statement": "I confirm that I have reviewed the Sentinel-2 imagery and explicitly approve these corrections."
        },
        "correction_rationale": "High-resolution Sentinel-2 SWIR band 12 reflectance confirms unambiguous active thermal front and clear charcoal burn scar. Negative evidence flag removed.",
        "corrected_consensus": {
            "chip_annotation_status": "HAS_ANNOTATIONS",
            "annotations": prop_boxes
        }
    }

    success, errors, record = save_chip_correction("PILOT_03_NORTH", payload)
    assert success is True, f"Failed with errors: {errors}"
    assert record is not None
    assert record["correction_version"] == "v2.0"
    assert record["stage"] == "STAGE_8_16"
    assert "annotations[0].visual_evidence" in record["changed_fields"]

    saved_file = test_corr_dir / "PILOT_03_NORTH_corrected_v2.json"
    assert saved_file.exists()
    saved_doc = json.loads(saved_file.read_text(encoding="utf-8"))
    assert saved_doc["record_sha256"] is not None
    assert "NO_CLEAR_VISUAL_EVIDENCE" not in saved_doc["corrected_consensus"]["visual_evidence"]


def test_5_contradictory_evidence_rejected(tmp_path, monkeypatch):
    """Verify that retaining contradictory evidence flags is strictly rejected."""
    test_corr_dir = tmp_path / "corrections"
    test_corr_dir.mkdir()
    monkeypatch.setattr("scripts.ds08_correction_tool.CORRECTIONS_DIR", test_corr_dir)
    monkeypatch.setattr("scripts.ds08_correction_tool.AUDIT_LOG_PATH", test_corr_dir / "audit.jsonl")

    payload = {
        "chip_id": "PILOT_03_NORTH",
        "human_confirmation": {"confirmed": True},
        "correction_rationale": "Sentinel-2 SWIR reflectance shows clear active burn front in forested terrain.",
        "corrected_consensus": {
            "chip_annotation_status": "HAS_ANNOTATIONS",
            "annotations": [
                {
                    "class_name": "Forest Fire",
                    "bbox": {"x_min": 110, "y_min": 262, "x_max": 196, "y_max": 376},
                    "visual_evidence": ["DIRECT_FIRE_VISIBLE", "NO_CLEAR_VISUAL_EVIDENCE"]
                }
            ]
        }
    }
    success, errors, record = save_chip_correction("PILOT_03_NORTH", payload)
    assert success is False
    assert any("contradictory evidence" in e for e in errors)


def test_6_observation_status_unresolved_rejected(tmp_path, monkeypatch):
    """Verify that UNRESOLVED status is strictly rejected for Stage 8.16."""
    test_corr_dir = tmp_path / "corrections"
    test_corr_dir.mkdir()
    monkeypatch.setattr("scripts.ds08_correction_tool.CORRECTIONS_DIR", test_corr_dir)
    monkeypatch.setattr("scripts.ds08_correction_tool.AUDIT_LOG_PATH", test_corr_dir / "audit.jsonl")

    payload = {
        "chip_id": "PILOT_08_CENTRAL",
        "human_confirmation": {"confirmed": True},
        "correction_rationale": "Scene shows ambiguous agricultural pattern with cloud shadows.",
        "corrected_consensus": {
            "chip_annotation_status": "UNRESOLVED",
            "annotations": []
        }
    }
    success, errors, record = save_chip_correction("PILOT_08_CENTRAL", payload)
    assert success is False
    assert any("UNRESOLVED" in e for e in errors)


def test_7_definitive_status_pilot08_success(tmp_path, monkeypatch):
    """Verify definitive consensus determination for PILOT_08_CENTRAL (both options valid)."""
    test_corr_dir = tmp_path / "corrections"
    test_corr_dir.mkdir()
    monkeypatch.setattr("scripts.ds08_correction_tool.CORRECTIONS_DIR", test_corr_dir)
    monkeypatch.setattr("scripts.ds08_correction_tool.AUDIT_LOG_PATH", test_corr_dir / "audit.jsonl")

    # Test option A: HAS_ANNOTATIONS with valid agricultural fire box
    payload = {
        "chip_id": "PILOT_08_CENTRAL",
        "human_confirmation": {"confirmed": True},
        "correction_rationale": "Sentinel-2 SWIR reflection and cropland boundary analysis confirm localized agricultural burn scar in field plot.",
        "corrected_consensus": {
            "chip_annotation_status": "HAS_ANNOTATIONS",
            "annotations": [
                {
                    "class_name": "Agricultural Fire",
                    "bbox": {"x_min": 217, "y_min": 225, "x_max": 268, "y_max": 295},
                    "visual_evidence": ["BURN_SCAR_VISIBLE", "CROPLAND_CONTEXT_VISIBLE"]
                }
            ]
        }
    }
    success, errors, record = save_chip_correction("PILOT_08_CENTRAL", payload)
    assert success is True, f"Failed with errors: {errors}"
    assert record["corrected_consensus"]["chip_annotation_status"] == "HAS_ANNOTATIONS"
    assert len(record["corrected_consensus"]["annotations"]) == 1


def test_8_required_rationale_enforced(tmp_path, monkeypatch):
    """Verify empty, short, or generic rationales are rejected."""
    # Empty
    valid, err = validate_correction_rationale("")
    assert valid is False

    # Short (<15 chars)
    valid, err = validate_correction_rationale("fixed tags")
    assert valid is False

    # Generic prohibited phrases
    for generic in ["I saw the fire", "looks like fire", "Agreed with annotator", "i see fire"]:
        valid, err = validate_correction_rationale(f"{generic} in the image very clearly.")
        assert valid is False, f"Did not reject generic rationale: {generic}"


def test_9_explicit_human_confirmation_required(tmp_path, monkeypatch):
    """Verify missing or false human confirmation checkbox is rejected."""
    test_corr_dir = tmp_path / "corrections"
    test_corr_dir.mkdir()
    monkeypatch.setattr("scripts.ds08_correction_tool.CORRECTIONS_DIR", test_corr_dir)
    monkeypatch.setattr("scripts.ds08_correction_tool.AUDIT_LOG_PATH", test_corr_dir / "audit.jsonl")

    payload = {
        "chip_id": "PILOT_03_NORTH",
        "human_confirmation": {"confirmed": False},
        "correction_rationale": "SWIR reflectance confirms fire front and burn scar in forest.",
        "corrected_consensus": {
            "chip_annotation_status": "HAS_ANNOTATIONS",
            "annotations": [
                {
                    "class_name": "Forest Fire",
                    "bbox": {"x_min": 110, "y_min": 262, "x_max": 196, "y_max": 376},
                    "visual_evidence": ["DIRECT_FIRE_VISIBLE", "BURN_SCAR_VISIBLE"]
                }
            ]
        }
    }
    success, errors, record = save_chip_correction("PILOT_03_NORTH", payload)
    assert success is False
    assert any("confirmation" in e.lower() for e in errors)


def test_10_bounding_box_validation(tmp_path, monkeypatch):
    """Verify bounding box boundary and forbidden coordinate checks."""
    test_corr_dir = tmp_path / "corrections"
    test_corr_dir.mkdir()
    monkeypatch.setattr("scripts.ds08_correction_tool.CORRECTIONS_DIR", test_corr_dir)
    monkeypatch.setattr("scripts.ds08_correction_tool.AUDIT_LOG_PATH", test_corr_dir / "audit.jsonl")

    base_payload = {
        "chip_id": "PILOT_03_NORTH",
        "human_confirmation": {"confirmed": True},
        "correction_rationale": "SWIR reflectance confirms fire front and burn scar in forest.",
        "corrected_consensus": {
            "chip_annotation_status": "HAS_ANNOTATIONS",
            "annotations": []
        }
    }

    # Out of bounds (>512)
    p_oob = copy.deepcopy(base_payload)
    p_oob["corrected_consensus"]["annotations"] = [
        {"class_name": "Forest Fire", "bbox": {"x_min": 100, "y_min": 100, "x_max": 520, "y_max": 200}, "visual_evidence": ["DIRECT_FIRE_VISIBLE"]}
    ]
    s, errs, _ = save_chip_correction("PILOT_03_NORTH", p_oob)
    assert s is False
    assert any("out-of-bounds" in e.lower() or "invalid geometry" in e.lower() for e in errs)

    # Inverted (x_min >= x_max)
    p_inv = copy.deepcopy(base_payload)
    p_inv["corrected_consensus"]["annotations"] = [
        {"class_name": "Forest Fire", "bbox": {"x_min": 200, "y_min": 100, "x_max": 100, "y_max": 200}, "visual_evidence": ["DIRECT_FIRE_VISIBLE"]}
    ]
    s, errs, _ = save_chip_correction("PILOT_03_NORTH", p_inv)
    assert s is False

    # Forbidden default box [200, 200, 300, 300]
    p_forbid = copy.deepcopy(base_payload)
    p_forbid["corrected_consensus"]["annotations"] = [
        {"class_name": "Forest Fire", "bbox": FORBIDDEN_DEFAULT_BOX, "visual_evidence": ["DIRECT_FIRE_VISIBLE"]}
    ]
    s, errs, _ = save_chip_correction("PILOT_03_NORTH", p_forbid)
    assert s is False
    assert any("forbidden placeholder" in e for e in errs)


def test_11_audit_log_integrity(tmp_path, monkeypatch):
    """Verify that every correction attempt is appended to stage8_16_audit_log.jsonl."""
    test_corr_dir = tmp_path / "corrections"
    test_corr_dir.mkdir()
    log_file = test_corr_dir / "audit.jsonl"
    monkeypatch.setattr("scripts.ds08_correction_tool.CORRECTIONS_DIR", test_corr_dir)
    monkeypatch.setattr("scripts.ds08_correction_tool.AUDIT_LOG_PATH", log_file)

    # Test rejected attempt
    p_bad = {
        "chip_id": "PILOT_03_NORTH",
        "human_confirmation": {"confirmed": False},
        "correction_rationale": "SWIR reflectance confirms fire.",
        "corrected_consensus": {"chip_annotation_status": "NO_VISIBLE_TARGET", "annotations": []}
    }
    save_chip_correction("PILOT_03_NORTH", p_bad)

    # Test successful attempt
    p_good = {
        "chip_id": "PILOT_03_NORTH",
        "human_confirmation": {"confirmed": True},
        "correction_rationale": "SWIR reflectance confirms clear fire scar in forest. Positive evidence confirmed.",
        "corrected_consensus": {
            "chip_annotation_status": "HAS_ANNOTATIONS",
            "annotations": [
                {
                    "class_name": "Forest Fire",
                    "bbox": {"x_min": 110, "y_min": 262, "x_max": 196, "y_max": 376},
                    "visual_evidence": ["DIRECT_FIRE_VISIBLE", "BURN_SCAR_VISIBLE"]
                }
            ]
        }
    }
    save_chip_correction("PILOT_03_NORTH", p_good)

    assert log_file.exists()
    lines = [json.loads(line) for line in log_file.read_text(encoding="utf-8").strip().split("\n")]
    assert len(lines) == 2
    assert lines[0]["event_type"] == "SAVE_REJECTED"
    assert lines[0]["success"] is False
    assert lines[1]["event_type"] == "CORRECTION_SAVED"
    assert lines[1]["success"] is True


def test_12_a1_a2_baseline_and_predecessors_protected():
    """Verify that original A1/A2 and frozen predecessor models are 100% verified."""
    valid_base, errs_base = verify_a1_a2_baseline()
    assert valid_base is True, f"A1/A2 baseline altered: {errs_base}"

    valid_pred, errs_pred = verify_frozen_predecessors()
    assert valid_pred is True, f"Predecessors altered: {errs_pred}"
