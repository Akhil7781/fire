"""Tests for DS08 Stage 8.14: Post-Annotation Integrity Audit and Agreement Analysis."""

import hashlib
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
MANUAL_DIR = ROOT / "data" / "reference" / "ds08" / "annotations" / "manual"
REVIEW_DIR = ROOT / "data" / "reference" / "ds08" / "annotations" / "review"
FINAL_DIR = ROOT / "data" / "reference" / "ds08" / "annotations" / "final"

EXPECTED_15_CHIPS = [
    "PILOT_02_NORTH",
    "PILOT_03_NORTH",
    "PILOT_06_CENTRAL",
    "PILOT_07_CENTRAL",
    "PILOT_08_CENTRAL",
    "PILOT_10_SOUTH",
    "PILOT_11_SOUTH",
    "PILOT_12_SOUTH",
    "PILOT_14_EAST",
    "PILOT_15_EAST",
    "PILOT_16_EAST",
    "PILOT_18_WEST",
    "PILOT_19_WEST",
    "PILOT_20_WEST",
    "PILOT_04_NORTH_REPLACEMENT",
]

PREDECESSOR_HASHES = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
}


def test_stage8_14_preconditions():
    """Verify all 30 human double annotation files exist and are verified completed."""
    a1_dir = MANUAL_DIR / "annotator_1"
    a2_dir = MANUAL_DIR / "annotator_2"
    assert a1_dir.exists(), "Annotator 1 directory missing"
    assert a2_dir.exists(), "Annotator 2 directory missing"

    for chip_id in EXPECTED_15_CHIPS:
        f1 = a1_dir / f"{chip_id}_annotator1.json"
        f2 = a2_dir / f"{chip_id}_annotator2.json"
        assert f1.exists(), f"Missing A1 file: {f1}"
        assert f2.exists(), f"Missing A2 file: {f2}"

        with open(f1, "r", encoding="utf-8") as fp:
            d1 = json.load(fp)
        with open(f2, "r", encoding="utf-8") as fp:
            d2 = json.load(fp)

        assert d1["task_status"] == "COMPLETED_HUMAN_ANNOTATION"
        assert d1["human_verified"] is True
        assert d1["chip_id"] == chip_id
        assert "interaction_audit" in d1

        assert d2["task_status"] == "COMPLETED_HUMAN_ANNOTATION"
        assert d2["human_verified"] is True
        assert d2["chip_id"] == chip_id
        assert "interaction_audit" in d2


def test_stage8_14_review_artifacts():
    """Verify review artifacts exist and are consistent."""
    json_path = REVIEW_DIR / "stage8_14_agreement_analysis_v1.json"
    md_path = REVIEW_DIR / "stage8_14_agreement_analysis_v1.md"
    assert json_path.exists(), "Stage 8.14 review JSON missing"
    assert md_path.exists(), "Stage 8.14 review Markdown missing"

    with open(json_path, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    assert data["stage"] == "STAGE_8.14"
    assert data["status"] == "COMPLETED"
    assert data["precondition_audit"]["overall_precondition_met"] is True
    assert data["precondition_audit"]["stop_condition_triggered"] is False
    assert data["agreement_metrics"]["total_chips_evaluated"] == 15
    assert data["agreement_metrics"]["class_agreement_count"] == "10/15"
    assert data["agreement_metrics"]["chips_requiring_adjudication_count"] == 6
    assert set(data["agreement_metrics"]["chips_requiring_adjudication_ids"]) == {
        "PILOT_03_NORTH",
        "PILOT_07_CENTRAL",
        "PILOT_08_CENTRAL",
        "PILOT_11_SOUTH",
        "PILOT_14_EAST",
        "PILOT_18_WEST",
    }
    assert data["adjudication_status"] == "DEFERRED_TO_STAGE_8.15"


def test_frozen_predecessors_untouched():
    """Verify frozen models and embeddings match SHA-256 hashes bit-for-bit."""
    for rel_path, expected_hash in PREDECESSOR_HASHES.items():
        full_path = ROOT / rel_path
        assert full_path.exists(), f"Predecessor missing: {rel_path}"
        sha256 = hashlib.sha256()
        with open(full_path, "rb") as fp:
            while chunk := fp.read(65536):
                sha256.update(chunk)
        assert sha256.hexdigest() == expected_hash, f"Hash mismatch for {rel_path}"


def test_zero_premature_adjudication():
    """Verify no 8.14 chips were prematurely written to final directory."""
    for chip_id in EXPECTED_15_CHIPS:
        final_file = FINAL_DIR / f"{chip_id}_final.json"
        assert not final_file.exists(), f"Premature final file exists: {final_file}"
