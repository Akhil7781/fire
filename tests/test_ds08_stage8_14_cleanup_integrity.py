"""Unit tests verifying Stage 8.14 Invalidation, Forensic Cleanup, and Integrity."""

import hashlib
import json
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MANUAL_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "manual"
A1_DIR = MANUAL_DIR / "annotator_1"
A2_DIR = MANUAL_DIR / "annotator_2"

QUARANTINE_814 = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "quarantine" / "stage8_14_invalid"
QUARANTINE_811 = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "quarantine" / "stage8_11_script_generated"
FINAL_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "final"

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


def test_pilot02_protected_genuine_artifact():
    """Verify PILOT_02_NORTH in manual/annotator_1 is untouched and matches protected hash."""
    fpath = A1_DIR / "PILOT_02_NORTH_annotator1.json"
    assert fpath.exists(), "PILOT_02_NORTH_annotator1.json missing"
    raw = fpath.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_PILOT02_HASH
    data = json.loads(raw.decode("utf-8"))
    assert data["task_status"] == "COMPLETED_HUMAN_ANNOTATION"
    assert data["human_verified"] is True
    assert data["chip_annotation_status"] == "NO_VISIBLE_TARGET"

    # Protected backup also exists and matches
    backup = QUARANTINE_814 / "protected_genuine_pilot02" / "PILOT_02_NORTH_annotator1.json"
    assert backup.exists(), "Protected backup missing"
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == EXPECTED_PILOT02_HASH


def test_annotator_1_remaining_14_blank_templates():
    """Verify remaining 14 chips in A1 workspace are clean blank templates."""
    for cid in AFFECTED_15_CHIPS:
        if cid == "PILOT_02_NORTH":
            continue
        fpath = A1_DIR / f"{cid}_annotator1.json"
        assert fpath.exists(), f"Missing template {fpath.name}"
        with open(fpath, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        assert d["task_status"] == "PENDING_MANUAL_INPUT"
        assert d["human_verified"] is False
        assert d["chip_annotation_status"] is None
        assert d["annotations"] == []
        assert d["annotator_id"] == "HUMAN_ANNOTATOR_01"


def test_annotator_2_all_15_blank_templates():
    """Verify all 15 chips in A2 workspace are clean blank templates."""
    for cid in AFFECTED_15_CHIPS:
        fpath = A2_DIR / f"{cid}_annotator2.json"
        assert fpath.exists(), f"Missing template {fpath.name}"
        with open(fpath, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        assert d["task_status"] == "PENDING_MANUAL_INPUT"
        assert d["human_verified"] is False
        assert d["chip_annotation_status"] is None
        assert d["annotations"] == []
        assert d["annotator_id"] == "HUMAN_ANNOTATOR_02"


def test_quarantine_814_contents():
    """Verify quarantine contains all 14 A1, 15 A2, review artifacts, and report files."""
    assert (QUARANTINE_814 / "stage8_14_forensic_audit.json").exists()
    assert (QUARANTINE_814 / "STAGE8_14_INVALID_PROVENANCE.md").exists()

    q_a1_files = list((QUARANTINE_814 / "manual" / "annotator_1").glob("*.json"))
    assert len(q_a1_files) == 14

    q_a2_files = list((QUARANTINE_814 / "manual" / "annotator_2").glob("*.json"))
    assert len(q_a2_files) == 15

    q_review_files = list((QUARANTINE_814 / "review_artifacts").iterdir())
    assert len(q_review_files) >= 5


def test_stage8_11_quarantine_preserved():
    """Verify Stage 8.11 quarantine is untouched."""
    manifest = QUARANTINE_811 / "quarantine_manifest.json"
    assert manifest.exists()


def test_frozen_predecessors_match():
    """Verify all 5 frozen predecessor hashes bit-for-bit."""
    for rel_p, exp_h in FROZEN_PREDECESSORS.items():
        p = PROJECT_ROOT / rel_p
        assert p.exists()
        assert hashlib.sha256(p.read_bytes()).hexdigest() == exp_h


def test_final_directory_unchanged():
    """Verify final directory contains strictly only the 3 Stage 8.10B-C files."""
    final_files = sorted([f.name for f in FINAL_DIR.glob("*.json")])
    assert final_files == [
        "PILOT_01_NORTH_adjudicated_v1.json",
        "PILOT_13_EAST_adjudicated_v1.json",
        "PILOT_17_WEST_adjudicated_v1.json",
    ]
