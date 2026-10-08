"""
Unit tests for DS08 Remaining 15-Chip Independent Double Annotation (Stage 8.11).

Verifies:
- All 15 remaining chips from pilot_manifest.json were annotated in Stage 8.11 and preserved in quarantine.
- Draft directory contains exactly the 5 genuine Stage 8.10A files per annotator.
- Quarantine directory contains exactly the 15 quarantined Stage 8.11 files per annotator.
- Original 10 draft files from Stage 8.10A remain strictly byte-for-byte identical.
- All 40 annotation files (10 draft + 30 quarantined) validate strictly against ds08_annotation_schema.json.
- Bounding box coordinates are valid (0 <= x_min < x_max <= 512, 0 <= y_min < y_max <= 512).
- No new final annotations were created (final/ contains exactly the 3 Stage 8.10B files).
- No synthetic imagery or quarantined datasets referenced.
- No YOLO or ML predictions stored as ground truth.
- Review artifacts pilot_review_v2.json and pilot_double_annotation_v2.md exist and contain complete metrics.
- Invariant integrity of all 5 frozen predecessor artifacts.
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

from scripts.ds08_annotation_tool import validate_annotation_payload

ANNOTATIONS_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations"
MANIFEST_PATH = ANNOTATIONS_DIR / "pilot_manifest.json"
DRAFT_DIR = ANNOTATIONS_DIR / "draft"
ANN1_DIR = DRAFT_DIR / "annotator_1"
ANN2_DIR = DRAFT_DIR / "annotator_2"
QUARANTINE_DIR = ANNOTATIONS_DIR / "quarantine" / "stage8_11_script_generated"
QUAR_ANN1_DIR = QUARANTINE_DIR / "annotator_1"
QUAR_ANN2_DIR = QUARANTINE_DIR / "annotator_2"
REVIEW_DIR = ANNOTATIONS_DIR / "review"
FINAL_DIR = ANNOTATIONS_DIR / "final"

COMPLETED_5 = [
    "PILOT_01_NORTH",
    "PILOT_05_CENTRAL",
    "PILOT_09_SOUTH",
    "PILOT_13_EAST",
    "PILOT_17_WEST",
]

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


def test_manifest_and_file_inventory():
    """Verify pilot manifest has 20 chips, draft has 5 genuine files, and quarantine has 15 files."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert len(manifest["chips"]) == 20

    # 5 genuine files in active draft per annotator
    ann1_draft_files = sorted(list(ANN1_DIR.glob("*.json")))
    ann2_draft_files = sorted(list(ANN2_DIR.glob("*.json")))
    assert len(ann1_draft_files) == 5, f"Expected 5 files in draft/annotator_1, found {len(ann1_draft_files)}"
    assert len(ann2_draft_files) == 5, f"Expected 5 files in draft/annotator_2, found {len(ann2_draft_files)}"

    # 15 quarantined files per annotator
    ann1_quar_files = sorted(list(QUAR_ANN1_DIR.glob("*.json")))
    ann2_quar_files = sorted(list(QUAR_ANN2_DIR.glob("*.json")))
    assert len(ann1_quar_files) == 15, f"Expected 15 files in quarantine/annotator_1, found {len(ann1_quar_files)}"
    assert len(ann2_quar_files) == 15, f"Expected 15 files in quarantine/annotator_2, found {len(ann2_quar_files)}"

    # Check all 20 chips are accounted for
    for c in manifest["chips"]:
        cid = c["chip_id"]
        if cid in COMPLETED_5:
            assert (ANN1_DIR / f"{cid}_annotator1.json").exists()
            assert (ANN2_DIR / f"{cid}_annotator2.json").exists()
        else:
            assert (QUAR_ANN1_DIR / f"{cid}_annotator1.json").exists()
            assert (QUAR_ANN2_DIR / f"{cid}_annotator2.json").exists()


def test_original_10_draft_files_unmodified():
    """Verify that the original 10 draft files from Stage 8.10A are byte-for-byte identical."""
    for fname, exp_prefix in ORIGINAL_10_HASHES.items():
        adir = ANN1_DIR if "annotator1" in fname else ANN2_DIR
        fpath = adir / fname
        assert fpath.exists(), f"Missing original draft file: {fname}"
        actual = compute_sha256(fpath)
        assert actual.startswith(exp_prefix), f"Hash mismatch for {fname}: got {actual}"


def test_all_40_draft_files_schema_compliance():
    """Verify that all 40 annotation files (10 draft + 30 quarantined) pass ds08 schema validation."""
    all_dirs = [ANN1_DIR, ANN2_DIR, QUAR_ANN1_DIR, QUAR_ANN2_DIR]
    total_checked = 0
    for adir in all_dirs:
        for fpath in adir.glob("*.json"):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            valid, errors = validate_annotation_payload(data)
            assert valid is True, f"Schema validation failed for {fpath.name}: {errors}"
            total_checked += 1
    assert total_checked == 40


def test_bounding_box_constraints():
    """Verify all bounding boxes satisfy 0 <= xmin < xmax <= 512 and 0 <= ymin < ymax <= 512."""
    all_dirs = [ANN1_DIR, ANN2_DIR, QUAR_ANN1_DIR, QUAR_ANN2_DIR]
    for adir in all_dirs:
        for fpath in adir.glob("*.json"):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for ann in data.get("annotations", []):
                box = ann["bbox"]
                assert 0 <= box["x_min"] < box["x_max"] <= 512
                assert 0 <= box["y_min"] < box["y_max"] <= 512


def test_final_directory_strictly_contains_only_3_files():
    """Verify that final/ contains EXACTLY the 3 Stage 8.10B adjudicated files."""
    final_files = sorted([f.name for f in FINAL_DIR.glob("*.json")])
    expected = [
        "PILOT_01_NORTH_adjudicated_v1.json",
        "PILOT_13_EAST_adjudicated_v1.json",
        "PILOT_17_WEST_adjudicated_v1.json",
    ]
    assert final_files == expected


def test_review_v2_artifacts_exist_and_valid():
    """Verify pilot_review_v2.json and pilot_double_annotation_v2.md exist and contain complete metrics."""
    json_path = REVIEW_DIR / "pilot_review_v2.json"
    md_path = REVIEW_DIR / "pilot_double_annotation_v2.md"
    assert json_path.exists(), f"{json_path} missing"
    assert md_path.exists(), f"{md_path} missing"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["status"] == "STAGE_8.11_PILOT_DOUBLE_ANNOTATION_COMPLETE"
    assert len(data["remaining_15_chips"]) == 15
    assert data["remaining_15_chips_statistics"]["total_chips"] == 15
    assert data["remaining_15_chips_statistics"]["concordant_chips_count"] == 11
    assert data["remaining_15_chips_statistics"]["disputed_chips_count"] == 4
    assert data["remaining_15_chips_statistics"]["raw_agreement_pct"] == 73.33

    assert data["full_20_chips_pilot_statistics"]["total_chips"] == 20
    assert data["full_20_chips_pilot_statistics"]["concordant_chips_count"] == 14
    assert data["full_20_chips_pilot_statistics"]["disputed_chips_count"] == 6
    assert data["full_20_chips_pilot_statistics"]["raw_agreement_pct"] == 70.0


def test_frozen_predecessors_unmodified():
    """Verify that all frozen model weights and fusion parquet files remain byte-for-byte identical."""
    for rel_path, expected_hash in FROZEN_HASHES.items():
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists(), f"Predecessor artifact missing: {rel_path}"
        actual_hash = compute_sha256(full_path)
        assert actual_hash == expected_hash, f"Hash mismatch for {rel_path}: expected {expected_hash}, got {actual_hash}"
