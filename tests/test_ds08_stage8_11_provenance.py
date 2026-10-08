"""
Unit tests for Stage 8.11 Provenance Audit (DS08 Human Annotation Validity).

Verifies:
- Provenance audit artifacts exist (stage8_11_provenance_audit_v1.json and .md).
- Provenance audit verdict is explicitly classified as FAIL.
- Substantive scripted generation detected and recorded.
- Reconciled class counts for Annotator 1 and Annotator 2 across remaining 15 chips.
- Exact identification of 4 outstanding disagreements for future Stage 8.12 adjudication.
- Exact identification of 3 historical adjudications from Stage 8.10B.
- Isolation of final/ directory (contains only the 3 Stage 8.10B files).
- Preserved integrity of the original 10 draft files from Stage 8.10A.
- Preserved invariant integrity of all 5 frozen predecessor artifacts.
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
DRAFT_DIR = ANNOTATIONS_DIR / "draft"
ANN1_DIR = DRAFT_DIR / "annotator_1"
ANN2_DIR = DRAFT_DIR / "annotator_2"
REVIEW_DIR = ANNOTATIONS_DIR / "review"
FINAL_DIR = ANNOTATIONS_DIR / "final"

AUDIT_JSON_PATH = REVIEW_DIR / "stage8_11_provenance_audit_v1.json"
AUDIT_MD_PATH = REVIEW_DIR / "stage8_11_provenance_audit_v1.md"

ORIGINAL_10_HASHES = {
    "PILOT_01_NORTH_annotator1.json": "e76a7fbb8236ad27",
    "PILOT_01_NORTH_annotator2.json": "cad036e10fd48bfd",
    "PILOT_05_CENTRAL_annotator1.json": "9cc57f90ca3fb8d3",
    "PILOT_05_CENTRAL_annotator2.json": "9cc57f90ca3fb8d3",
    "PILOT_09_SOUTH_annotator1.json": "2d3f17b3b8a45eb4",
    "PILOT_09_SOUTH_annotator2.json": "72a6189bc007e8ef",
    "PILOT_13_EAST_annotator1.json": "632f8510441b3fe0",
    "PILOT_13_EAST_annotator2.json": "ce4b210e515a1be0",
    "PILOT_17_WEST_annotator1.json": "bca16c033943758b",
    "PILOT_17_WEST_annotator2.json": "16b3601372e0c54a",
}

FROZEN_HASHES = {
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


def test_provenance_audit_artifacts_exist_and_verdict_fail():
    """Verify that the audit artifacts exist and the human provenance classification is FAIL."""
    assert AUDIT_JSON_PATH.exists(), f"Missing audit JSON: {AUDIT_JSON_PATH}"
    assert AUDIT_MD_PATH.exists(), f"Missing audit MD: {AUDIT_MD_PATH}"

    with open(AUDIT_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["stage"] == "8.11_provenance_audit"
    assert data["status"] == "FAIL"
    assert data["human_annotation_provenance_verified"] is False
    assert data["automatic_labeling_detected"] is True
    assert data["model_inference_detected"] is False
    assert "hardcoded" in data["script_behavior"].lower()


def test_reconciled_15_chip_class_counts():
    """Verify exact reconciled class distributions for remaining 15 chips."""
    with open(AUDIT_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["a1_draft_count"] == 15
    assert data["a2_draft_count"] == 15

    # A1 reconciled counts for remaining 15 chips
    assert data["a1_class_counts"]["NO_VISIBLE_TARGET"] == 7
    assert data["a1_class_counts"]["Forest Fire"] == 7
    assert data["a1_class_counts"]["Agricultural Fire"] == 1
    assert data["reported_count_reconciled"] is True

    # Check the 7 explicit NO_VISIBLE_TARGET IDs
    expected_no_target = [
        "PILOT_02_NORTH",
        "PILOT_07_CENTRAL",
        "PILOT_10_SOUTH",
        "PILOT_11_SOUTH",
        "PILOT_12_SOUTH",
        "PILOT_20_WEST",
        "PILOT_04_NORTH_REPLACEMENT",
    ]
    assert sorted(data["a1_no_visible_target_ids"]) == sorted(expected_no_target)

    # A2 counts
    assert data["a2_class_counts"]["NO_VISIBLE_TARGET"] == 9
    assert data["a2_class_counts"]["Forest Fire"] == 4
    assert data["a2_class_counts"]["UNRESOLVED"] == 2


def test_historical_vs_outstanding_disagreements():
    """Verify distinct tracking of historical vs outstanding disagreements."""
    with open(AUDIT_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    expected_historical = ["PILOT_01_NORTH", "PILOT_13_EAST", "PILOT_17_WEST"]
    expected_outstanding = ["PILOT_06_CENTRAL", "PILOT_14_EAST", "PILOT_18_WEST", "PILOT_19_WEST"]

    assert sorted(data["historical_disagreements"]) == sorted(expected_historical)
    assert sorted(data["outstanding_disagreements"]) == sorted(expected_outstanding)


def test_final_directory_strictly_contains_only_3_files():
    """Verify that final/ contains EXACTLY the 3 Stage 8.10B adjudicated files."""
    final_files = sorted([f.name for f in FINAL_DIR.glob("*.json")])
    expected = [
        "PILOT_01_NORTH_adjudicated_v1.json",
        "PILOT_13_EAST_adjudicated_v1.json",
        "PILOT_17_WEST_adjudicated_v1.json",
    ]
    assert final_files == expected


def test_original_10_draft_files_unmodified():
    """Verify that the original 10 draft files from Stage 8.10A are byte-for-byte identical."""
    for fname, exp_prefix in ORIGINAL_10_HASHES.items():
        adir = ANN1_DIR if "annotator1" in fname else ANN2_DIR
        fpath = adir / fname
        assert fpath.exists(), f"Missing original draft file: {fname}"
        actual = compute_sha256(fpath)
        assert actual.startswith(exp_prefix), f"Hash mismatch for {fname}: got {actual}"


def test_frozen_predecessors_unmodified():
    """Verify that all frozen model weights and fusion parquet files remain byte-for-byte identical."""
    for rel_path, expected_hash in FROZEN_HASHES.items():
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists(), f"Predecessor artifact missing: {rel_path}"
        actual_hash = compute_sha256(full_path)
        assert actual_hash == expected_hash, f"Hash mismatch for {rel_path}: expected {expected_hash}, got {actual_hash}"
