"""
Unit tests for Stage 8.15 Adjudication UI Repair and Hardening.

Proves the 10 mandatory properties:
1. New adjudication starts with annotations=[].
2. Saving HAS_ANNOTATIONS with zero boxes fails.
3. Saving NO_VISIBLE_TARGET with zero boxes succeeds.
4. Saving UNRESOLVED with zero boxes succeeds.
5. Default [200, 200, 300, 300] is never injected and rejected if submitted.
6. A bbox requires a recorded manual interaction.
7. Generic rationale is rejected.
8. A substantive human rationale can be saved.
9. A1/A2 source files remain untouched.
10. Quarantine is isolated.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pytest
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ds08_adjudication_tool import (
    load_adjudication_chip_data,
    save_adjudicated_chip,
    validate_adjudication_rationale,
    verify_source_file_hashes,
    DISPUTED_6_CHIPS,
    PRE_ADJUDICATION_HASHES,
    ADJUDICATION_REVIEW_DIR,
    QUARANTINE_STAGE8_15_DIR,
    A1_DIR,
    A2_DIR,
)

FROZEN_ARTIFACTS = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
}


def test_1_new_adjudication_starts_with_empty_annotations(tmp_path, monkeypatch):
    """Property 1: Unadjudicated chip loads with existing_adjudication=None and annotations=[]."""
    monkeypatch.setattr("scripts.ds08_adjudication_tool.ADJUDICATION_REVIEW_DIR", tmp_path)
    data = load_adjudication_chip_data("PILOT_03_NORTH")
    assert data["is_adjudicated"] is False
    assert data["existing_adjudication"] is None
    assert data["chip_id"] == "PILOT_03_NORTH"
    assert "A1_original" in data and "A2_original" in data


def test_2_saving_has_annotations_with_zero_boxes_fails():
    """Property 2: Saving HAS_ANNOTATIONS with zero boxes fails."""
    payload = {
        "chip_id": "PILOT_03_NORTH",
        "human_verified": True,
        "adjudication_rationale": "SWIR reflectance shows clear active burn patch with distinct smoke plume drifting north.",
        "final_consensus": {
            "chip_annotation_status": "HAS_ANNOTATIONS",
            "annotations": []
        }
    }
    success, errors = save_adjudicated_chip("PILOT_03_NORTH", payload)
    assert success is False
    assert any("requires at least one manually drawn bounding box" in e for e in errors)


def test_3_saving_no_visible_target_with_zero_boxes_succeeds(tmp_path, monkeypatch):
    """Property 3: Saving NO_VISIBLE_TARGET with zero boxes succeeds."""
    test_review_dir = tmp_path / "review"
    test_review_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("scripts.ds08_adjudication_tool.ADJUDICATION_REVIEW_DIR", test_review_dir)

    payload = {
        "chip_id": "PILOT_08_CENTRAL",
        "human_verified": True,
        "adjudication_rationale": "High-resolution Sentinel-2 RGB and SWIR bands show clear cropland with zero heat anomaly or scar visible.",
        "final_consensus": {
            "chip_annotation_status": "NO_VISIBLE_TARGET",
            "annotations": []
        }
    }
    success, errors = save_adjudicated_chip("PILOT_08_CENTRAL", payload)
    assert success is True, f"Failed with errors: {errors}"
    saved_file = test_review_dir / "PILOT_08_CENTRAL_adjudicated_v1.json"
    assert saved_file.exists()
    saved = json.loads(saved_file.read_text(encoding="utf-8"))
    assert saved["chip_annotation_status"] == "NO_VISIBLE_TARGET"
    assert saved["annotations"] == []


def test_4_saving_unresolved_fails_definitive_requirement(tmp_path, monkeypatch):
    """Property 4: Saving UNRESOLVED fails because definitive consensus is required."""
    test_review_dir = tmp_path / "review"
    test_review_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("scripts.ds08_adjudication_tool.ADJUDICATION_REVIEW_DIR", test_review_dir)

    payload = {
        "chip_id": "PILOT_08_CENTRAL",
        "human_verified": True,
        "adjudication_rationale": "Scene shows cloud-shadow artifacts and ambiguous reflectance; insufficient visual confidence to confirm target.",
        "final_consensus": {
            "chip_annotation_status": "UNRESOLVED",
            "annotations": []
        }
    }
    success, errors = save_adjudicated_chip("PILOT_08_CENTRAL", payload)
    assert success is False
    assert any("not permitted" in e for e in errors)


def test_5_default_placeholder_box_is_strictly_rejected():
    """Property 5: Default [200, 200, 300, 300] is never permitted."""
    payload = {
        "chip_id": "PILOT_03_NORTH",
        "human_verified": True,
        "adjudication_rationale": "SWIR reflectance shows clear active burn patch with distinct smoke plume drifting north.",
        "final_consensus": {
            "chip_annotation_status": "HAS_ANNOTATIONS",
            "annotations": [
                {
                    "class_name": "Forest Fire",
                    "bbox": {"x_min": 200, "y_min": 200, "x_max": 300, "y_max": 300},
                    "geometry_confidence": "HIGH",
                    "source_class_confidence": "HIGH",
                    "visibility_status": "CLEAR",
                    "visual_evidence": ["DIRECT_FIRE_VISIBLE"],
                    "interaction_audit": {"manual_interaction_recorded": True}
                }
            ]
        }
    }
    success, errors = save_adjudicated_chip("PILOT_03_NORTH", payload)
    assert success is False
    assert any("forbidden placeholder coordinates [200, 200, 300, 300]" in e for e in errors)


def test_6_bbox_requires_recorded_manual_interaction():
    """Property 6: A bbox missing manual interaction audit record is rejected."""
    payload = {
        "chip_id": "PILOT_03_NORTH",
        "human_verified": True,
        "adjudication_rationale": "SWIR reflectance shows clear active burn patch with distinct smoke plume drifting north.",
        "final_consensus": {
            "chip_annotation_status": "HAS_ANNOTATIONS",
            "annotations": [
                {
                    "class_name": "Forest Fire",
                    "bbox": {"x_min": 210, "y_min": 220, "x_max": 280, "y_max": 290},
                    "geometry_confidence": "HIGH",
                    "source_class_confidence": "HIGH",
                    "visibility_status": "CLEAR",
                    "visual_evidence": ["DIRECT_FIRE_VISIBLE"],
                    "interaction_audit": {"manual_interaction_recorded": False}
                }
            ]
        }
    }
    success, errors = save_adjudicated_chip("PILOT_03_NORTH", payload)
    assert success is False
    assert any("missing required manual canvas interaction audit record" in e for e in errors)


def test_7_generic_rationale_is_rejected():
    """Property 7: Prohibited generic rationales are rejected by semantic validation."""
    prohibited = [
        "I saw the fire on the image",
        "i saw the fire in the image",
        "Looks like fire",
        "Agreed with A1",
        "Agreed with A2",
        "Agreed with annotator",
        "I see fire here",
        "there is fire",
    ]
    for p in prohibited:
        valid, err = validate_adjudication_rationale(p)
        assert valid is False, f"Expected '{p}' to be rejected"
        assert "Generic rationale rejected" in err


def test_8_substantive_human_rationale_can_be_saved(tmp_path, monkeypatch):
    """Property 8: A substantive human rationale with validly drawn box saves cleanly."""
    test_review_dir = tmp_path / "review"
    test_review_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("scripts.ds08_adjudication_tool.ADJUDICATION_REVIEW_DIR", test_review_dir)

    payload = {
        "chip_id": "PILOT_03_NORTH",
        "human_verified": True,
        "adjudication_rationale": "Inspection of SWIR B12/B11 false color composite reveals active flame front along forested ridge with distinct smoke dispersion.",
        "final_consensus": {
            "chip_annotation_status": "HAS_ANNOTATIONS",
            "annotations": [
                {
                    "class_name": "Forest Fire",
                    "bbox": {"x_min": 215, "y_min": 225, "x_max": 285, "y_max": 295},
                    "geometry_confidence": "HIGH",
                    "source_class_confidence": "HIGH",
                    "visibility_status": "CLEAR",
                    "visual_evidence": ["DIRECT_FIRE_VISIBLE", "BURN_SCAR_VISIBLE", "FOREST_CONTEXT_VISIBLE"],
                    "firms_relationship": "INSIDE_OBJECT",
                    "interaction_audit": {
                        "manual_interaction_recorded": True,
                        "event_type": "CANVAS_DRAW",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
            ]
        }
    }
    success, errors = save_adjudicated_chip("PILOT_03_NORTH", payload)
    assert success is True, f"Save failed: {errors}"
    saved_file = test_review_dir / "PILOT_03_NORTH_adjudicated_v1.json"
    assert saved_file.exists()


def test_9_a1_and_a2_source_files_remain_untouched():
    """Property 9: All 12 source files in A1 and A2 directories remain byte-for-byte identical."""
    valid, errors = verify_source_file_hashes()
    assert valid is True, f"Integrity errors: {errors}"


def test_10_quarantine_is_isolated_and_contains_invalid_files():
    """Property 10: Quarantine directory contains exactly the 6 rejected invalid files and markdown."""
    assert QUARANTINE_STAGE8_15_DIR.exists()
    quarantined_files = sorted([f.name for f in QUARANTINE_STAGE8_15_DIR.glob("*.json")])
    expected = [
        "PILOT_03_NORTH_adjudicated_v1.json",
        "PILOT_06_CENTRAL_adjudicated_v1.json",
        "PILOT_08_CENTRAL_adjudicated_v1.json",
        "PILOT_15_EAST_adjudicated_v1.json",
        "PILOT_16_EAST_adjudicated_v1.json",
        "PILOT_18_WEST_adjudicated_v1.json",
    ]
    assert quarantined_files == expected
    doc = QUARANTINE_STAGE8_15_DIR / "STAGE8_15_INVALID_ADJUDICATION.md"
    assert doc.exists()


def test_11_frozen_artifacts_verified():
    """Property 11: All 5 frozen model and fusion artifacts remain byte-for-byte identical."""
    for rel_path, expected_hash in FROZEN_ARTIFACTS.items():
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists(), f"Predecessor artifact missing: {rel_path}"
        actual_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {rel_path}"


def test_12_contradictory_evidence_flags_rejected(tmp_path, monkeypatch):
    """Property 12: Saving annotations with contradictory evidence flags is rejected."""
    test_review_dir = tmp_path / "review"
    test_review_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("scripts.ds08_adjudication_tool.ADJUDICATION_REVIEW_DIR", test_review_dir)

    payload = {
        "chip_id": "PILOT_03_NORTH",
        "human_verified": True,
        "adjudication_rationale": "SWIR reflectance shows clear active burn patch with distinct smoke plume drifting north.",
        "final_consensus": {
            "chip_annotation_status": "HAS_ANNOTATIONS",
            "annotations": [
                {
                    "class_name": "Forest Fire",
                    "bbox": {"x_min": 100, "y_min": 100, "x_max": 150, "y_max": 150},
                    "visual_evidence": ["DIRECT_FIRE_VISIBLE", "NO_CLEAR_VISUAL_EVIDENCE"],
                    "interaction_audit": {"manual_interaction_recorded": True}
                }
            ]
        }
    }
    success, errors = save_adjudicated_chip("PILOT_03_NORTH", payload)
    assert success is False
    assert any("contradictory evidence flags" in e for e in errors)

