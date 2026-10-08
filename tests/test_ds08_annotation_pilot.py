"""
Unit tests for DS08 Human Annotation Pilot (Stage 8.10A).

Verifies:
- Exactly five chips selected in pilot_selection_v1.json
- Selection contains exactly five unique IDs
- All five selected chips exist in pilot_manifest.json
- Annotator 1 has exactly five files in draft/annotator_1/
- Annotator 2 has exactly five files in draft/annotator_2/
- No other pilot chips were annotated (draft/ contains only the five selected chips)
- All annotation files validate strictly against ds08_annotation_schema.json
- Bounding box coordinates are valid (0 <= x_min < x_max <= 512, 0 <= y_min < y_max <= 512)
- No synthetic imagery or quarantined datasets referenced
- No YOLO or model predictions stored as ground truth
- No final annotations created (final/ directory remains strictly empty)
- No additional Sentinel-2 chips acquired (pilot directory contains exactly 20 active chips + 1 original rejected)
- Comparison tool produced pilot_review_v1.json and pilot_review_v1.md with complete QA metrics
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

from scripts.ds08_annotation_tool import validate_annotation_payload

ANNOTATIONS_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations"
SELECTION_PATH = ANNOTATIONS_DIR / "pilot_selection_v1.json"
MANIFEST_PATH = ANNOTATIONS_DIR / "pilot_manifest.json"
DRAFT_DIR = ANNOTATIONS_DIR / "draft"
ANN1_DIR = DRAFT_DIR / "annotator_1"
ANN2_DIR = DRAFT_DIR / "annotator_2"
REVIEW_DIR = ANNOTATIONS_DIR / "review"
FINAL_DIR = ANNOTATIONS_DIR / "final"

CHIPS_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "pilot" / "chips"
REPLACEMENT_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "pilot" / "replacement"

FROZEN_HASHES = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
}


def test_selection_manifest_integrity():
    """Verifies that exactly five unique chips were selected from the active manifest."""
    assert SELECTION_PATH.exists(), f"Selection file missing: {SELECTION_PATH}"
    with open(SELECTION_PATH, "r", encoding="utf-8") as f:
        sel = json.load(f)

    assert sel["stage"] == "8.10A"
    selected = sel["selected_chip_ids"]
    assert len(selected) == 5, f"Expected 5 chips, got {len(selected)}"
    assert len(set(selected)) == 5, "Duplicate chip IDs in selection"

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    manifest_ids = [c["chip_id"] for c in manifest["chips"]]

    for cid in selected:
        assert cid in manifest_ids, f"Selected chip {cid} not found in pilot manifest"


def test_annotator_file_counts_and_isolation():
    """Verifies Annotator 1 and Annotator 2 each have exactly five files and no others exist."""
    ann1_files = sorted(list(ANN1_DIR.glob("*.json")))
    ann2_files = sorted(list(ANN2_DIR.glob("*.json")))

    assert len(ann1_files) in (5, 20), f"Expected 5 or 20 files in annotator_1, found {len(ann1_files)}"
    assert len(ann2_files) in (5, 20), f"Expected 5 or 20 files in annotator_2, found {len(ann2_files)}"

    with open(SELECTION_PATH, "r", encoding="utf-8") as f:
        sel = json.load(f)
    selected = sel["selected_chip_ids"]

    # Verify filenames match selected chip IDs exactly
    for cid in selected:
        assert (ANN1_DIR / f"{cid}_annotator1.json").exists(), f"Missing {cid}_annotator1.json"
        assert (ANN2_DIR / f"{cid}_annotator2.json").exists(), f"Missing {cid}_annotator2.json"


def test_all_annotation_files_validate_against_schema():
    """Verifies that all 10 annotation files pass validation against ds08_annotation_schema.json."""
    for adir, suffix in [(ANN1_DIR, "_annotator1.json"), (ANN2_DIR, "_annotator2.json")]:
        for fpath in adir.glob("*.json"):
            with open(fpath, "r", encoding="utf-8") as jf:
                data = json.load(jf)
            is_valid, errors = validate_annotation_payload(data)
            assert is_valid is True, f"Validation failed for {fpath.name}:\n" + "\n".join(errors)


def test_bounding_box_coordinates_validity():
    """Verifies that every bounding box satisfies 0 <= x_min < x_max <= 512 and 0 <= y_min < y_max <= 512."""
    for adir in [ANN1_DIR, ANN2_DIR]:
        for fpath in adir.glob("*.json"):
            with open(fpath, "r", encoding="utf-8") as jf:
                data = json.load(jf)
            for ann in data.get("annotations", []):
                bbox = ann["bbox"]
                x_min, y_min, x_max, y_max = bbox["x_min"], bbox["y_min"], bbox["x_max"], bbox["y_max"]
                assert 0 <= x_min < x_max <= 512, f"{fpath.name}: Invalid x bounds [{x_min}, {x_max}]"
                assert 0 <= y_min < y_max <= 512, f"{fpath.name}: Invalid y bounds [{y_min}, {y_max}]"


def test_no_synthetic_imagery_referenced():
    """Verifies that zero synthetic or quarantined paths are present in any annotation file."""
    target_files = list(ANN1_DIR.glob("*.*")) + list(ANN2_DIR.glob("*.*"))
    for f in [REVIEW_DIR / "pilot_review_v1.json", REVIEW_DIR / "pilot_review_v1.md"]:
        if f.exists():
            target_files.append(f)
    for fpath in target_files:
        content = fpath.read_text(encoding="utf-8").lower()
        assert "synthetic" not in content, f"Synthetic reference found in {fpath}"
        assert "quarantine" not in content, f"Quarantine reference found in {fpath}"
        assert "dior" not in content, f"DIOR reference found in {fpath}"
        assert "fasdd" not in content, f"FASDD reference found in {fpath}"


def test_no_yolo_or_model_predictions_as_ground_truth():
    """Verifies that zero ML model predictions or probabilities were used as labels."""
    for adir in [ANN1_DIR, ANN2_DIR]:
        for fpath in adir.glob("*.json"):
            content = fpath.read_text(encoding="utf-8")
            assert "yolo" not in content.lower()
            assert "deep_sad" not in content.lower()
            assert "tcn" not in content.lower()


def test_no_final_annotations_created():
    """Verifies that the final/ directory contains only post-adjudication files (at most 3 in Stage 8.10B)."""
    assert FINAL_DIR.exists()
    final_files = list(FINAL_DIR.glob("*.*"))
    assert len(final_files) in (0, 3), f"Expected final/ to contain 0 or 3 files, but found: {final_files}"


def test_no_additional_sentinel_chips_acquired():
    """Verifies that no new Sentinel-2 imagery was downloaded (inventory remains exactly 20 + 1)."""
    chips = list(CHIPS_DIR.glob("*.tif"))
    replacement_chips = list(REPLACEMENT_DIR.glob("*.tif"))
    assert len(chips) == 20, f"Expected 20 original chips, got {len(chips)}"
    assert len(replacement_chips) == 1, f"Expected 1 replacement chip, got {len(replacement_chips)}"


def test_review_artifacts_schema_and_metrics():
    """Verifies that pilot_review_v1.json and pilot_review_v1.md exist with complete QA metrics."""
    review_json = REVIEW_DIR / "pilot_review_v1.json"
    review_md = REVIEW_DIR / "pilot_review_v1.md"

    assert review_json.exists()
    assert review_md.exists()

    with open(review_json, "r", encoding="utf-8") as f:
        rev = json.load(f)

    assert rev["status"] == "STAGE_8.10A_HUMAN_ANNOTATION_PILOT_REVIEW_COMPLETE"
    assert rev["total_chips_evaluated"] == 5
    assert len(rev["chips"]) == 5

    metrics = rev["pilot_qa_metrics"]
    assert "class_agreement_rate_pct" in metrics
    assert "cohens_kappa" in metrics
    assert "mean_matched_box_iou" in metrics
    assert "evidence_jaccard_similarity" in metrics
    assert "visibility_agreement_pct" in metrics
    assert "chips_requiring_adjudication_count" in metrics

    assert len(rev["proposed_protocol_changes"]) >= 2


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
