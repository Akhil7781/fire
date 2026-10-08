"""Unit tests for Stage 8.14 v2 genuine double-annotation agreement and provenance audit."""

import hashlib
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent

A1_DIR = ROOT / "data" / "reference" / "ds08" / "annotations" / "manual" / "annotator_1"
A2_DIR = ROOT / "data" / "reference" / "ds08" / "annotations" / "manual" / "annotator_2"
REVIEW_DIR = ROOT / "data" / "reference" / "ds08" / "annotations" / "review"
FINAL_DIR = ROOT / "data" / "reference" / "ds08" / "annotations" / "final"

AFFECTED_15_CHIPS = [
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

EXPECTED_PILOT02_HASH = "a7b3e2a1796c64ba4b2d6e1afdfae23c2144b0b1effe223597b100fa1bdf1d50"

FROZEN_PREDECESSORS = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
}


def test_provenance_completion_all_30_files():
    """Verify all 30 annotation files satisfy completion and human verification."""
    for adir, ann_sub in [(A1_DIR, "annotator1"), (A2_DIR, "annotator2")]:
        for cid in AFFECTED_15_CHIPS:
            fpath = adir / f"{cid}_{ann_sub}.json"
            assert fpath.exists(), f"Missing file: {fpath.name}"
            d = json.loads(fpath.read_text(encoding="utf-8"))
            assert d.get("task_status") == "COMPLETED_HUMAN_ANNOTATION"
            assert d.get("human_verified") is True
            assert d.get("chip_annotation_status") in ["HAS_ANNOTATIONS", "NO_VISIBLE_TARGET", "UNRESOLVED"]
            assert d.get("annotation_completion_timestamp") is not None
            assert d.get("interaction_audit", {}).get("save_events", 0) >= 1


def test_pilot02_protected_hash():
    """Verify PILOT_02_NORTH remains bit-for-bit identical to genuine hash."""
    fpath = A1_DIR / "PILOT_02_NORTH_annotator1.json"
    h = hashlib.sha256(fpath.read_bytes()).hexdigest()
    assert h == EXPECTED_PILOT02_HASH


def test_review_artifacts_exist_and_consistent():
    """Verify stage8_14_agreement_analysis_v2 artifacts exist and contain valid results."""
    json_path = REVIEW_DIR / "stage8_14_agreement_analysis_v2.json"
    md_path = REVIEW_DIR / "stage8_14_agreement_analysis_v2.md"
    assert json_path.exists()
    assert md_path.exists()

    d = json.load(json_path.open(encoding="utf-8"))
    assert d["stage"] == "STAGE_8.14"
    assert d["observation_status_agreement"]["agreement_count"] == 14
    assert d["observation_status_agreement"]["agreement_percentage"] == 93.33
    assert d["source_class_agreement"]["matched_boxes_class_agreement_pct"] == 100.0
    assert d["bounding_box_agreement"]["matched_boxes_count"] == 11
    assert d["bounding_box_agreement"]["mean_iou"] == 0.5260
    assert d["adjudication_status"]["adjudication_executed"] is False


def test_frozen_predecessors_match_hashes():
    """Verify all 5 frozen predecessor hashes match bit-for-bit."""
    for rel_p, exp_h in FROZEN_PREDECESSORS.items():
        p = ROOT / rel_p
        assert p.exists()
        assert hashlib.sha256(p.read_bytes()).hexdigest() == exp_h


def test_zero_adjudication_executed():
    """Verify no new final adjudicated files were created for the 15 pilot chips."""
    for cid in AFFECTED_15_CHIPS:
        fpath = FINAL_DIR / f"{cid}_adjudicated_v1.json"
        assert not fpath.exists(), f"Premature adjudicated file: {fpath.name}"
