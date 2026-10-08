#!/usr/bin/env python3
"""
Test Suite: DS08 Stage 8.17 Dataset Packaging and Validation
------------------------------------------------------------
Verifies:
1. Package existence, completeness, and directory layout.
2. Exact cohort membership (15 chips) and absence of duplicates.
3. Media matching (GeoTIFF, RGB, SWIR, metadata) and positive sizes.
4. Bit-for-bit checksum integrity across manifest.json.
5. Annotation schema compliance and valid class IDs.
6. Bounding box coordinates, bounds, and absence of dummy placeholders.
7. Visual evidence consistency (zero contradictory flags).
8. Definitive observation status (zero UNRESOLVED).
9. Full provenance traceability to Stage 8.14 (9 chips) and Stage 8.16 (6 chips).
10. Proper exclusion of screening chips and quarantine boundary isolation.
11. Immutability of baseline A1/A2, Stage 8.15 review records, and frozen predecessors.
12. Package validation report generation and passing verdict.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "packages" / "ds08_pilot_v1"
A1_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "manual" / "annotator_1"
A2_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "manual" / "annotator_2"
REVIEW_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "adjudication" / "review"
CORRECTIONS_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "adjudication" / "corrections"
SOURCE_MANIFEST_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "adjudication" / "stage8_16_source_manifest.json"
QUARANTINE_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "quarantine"

EXPECTED_15_CHIPS = sorted([
    "PILOT_02_NORTH",
    "PILOT_03_NORTH",
    "PILOT_04_NORTH_REPLACEMENT",
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
])

UNANIMOUS_9_CHIPS = sorted([
    "PILOT_02_NORTH",
    "PILOT_04_NORTH_REPLACEMENT",
    "PILOT_07_CENTRAL",
    "PILOT_10_SOUTH",
    "PILOT_11_SOUTH",
    "PILOT_12_SOUTH",
    "PILOT_14_EAST",
    "PILOT_19_WEST",
    "PILOT_20_WEST",
])

DISPUTED_6_CHIPS = sorted([
    "PILOT_03_NORTH",
    "PILOT_06_CENTRAL",
    "PILOT_08_CENTRAL",
    "PILOT_15_EAST",
    "PILOT_16_EAST",
    "PILOT_18_WEST",
])

EXCLUDED_5_CHIPS = sorted([
    "PILOT_01_NORTH",
    "PILOT_05_CENTRAL",
    "PILOT_09_SOUTH",
    "PILOT_13_EAST",
    "PILOT_17_WEST",
])

ALLOWED_CLASSES = ["Forest Fire", "Agricultural Fire", "Industrial Fire", "Other Thermal Source"]
CLASS_ID_MAP = {"Forest Fire": 2, "Agricultural Fire": 3, "Industrial Fire": 1, "Other Thermal Source": 4}

FROZEN_PREDECESSORS = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
}


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_1_package_exists_and_directory_structure():
    assert PACKAGE_DIR.exists(), f"Package directory missing: {PACKAGE_DIR}"
    assert (PACKAGE_DIR / "manifest.json").exists(), "manifest.json missing"
    assert (PACKAGE_DIR / "manifest.csv").exists(), "manifest.csv missing"
    assert (PACKAGE_DIR / "README.md").exists(), "README.md missing"
    assert (PACKAGE_DIR / "annotations").is_dir(), "annotations dir missing"
    assert (PACKAGE_DIR / "chips").is_dir(), "chips dir missing"
    assert (PACKAGE_DIR / "previews").is_dir(), "previews dir missing"
    assert (PACKAGE_DIR / "metadata").is_dir(), "metadata dir missing"


def test_2_cohort_membership_exact_15_chips():
    manifest = json.loads((PACKAGE_DIR / "manifest.json").read_text(encoding="utf-8"))
    cids = [c["chip_id"] for c in manifest.get("chips", [])]
    assert len(cids) == 15, f"Expected 15 chips, got {len(cids)}"
    assert sorted(cids) == EXPECTED_15_CHIPS, "Cohort does not match expected 15 chips"
    assert len(set(cids)) == 15, "Duplicate chip IDs present"


def test_3_media_matching_and_positive_sizes():
    for cid in EXPECTED_15_CHIPS:
        ann = PACKAGE_DIR / "annotations" / f"{cid}.json"
        tif = PACKAGE_DIR / "chips" / f"{cid}_chip.tif"
        rgb = PACKAGE_DIR / "previews" / f"{cid}_rgb.png"
        swir = PACKAGE_DIR / "previews" / f"{cid}_swir.png"
        meta = PACKAGE_DIR / "metadata" / f"{cid}_metadata.json"

        for p in [ann, tif, rgb, swir, meta]:
            assert p.exists(), f"Missing media file: {p}"
            assert p.stat().st_size > 0, f"File is empty: {p}"


def test_4_manifest_checksum_integrity():
    manifest = json.loads((PACKAGE_DIR / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["chips"]:
        for ftype, finfo in entry["files"].items():
            fp = PACKAGE_DIR / finfo["path"]
            assert fp.exists(), f"File {finfo['path']} missing on disk"
            disk_sha = compute_sha256(fp)
            assert disk_sha == finfo["sha256"], f"Checksum mismatch for {finfo['path']}"


def test_5_annotation_schema_and_classes():
    total_boxes = 0
    for cid in EXPECTED_15_CHIPS:
        ann = json.loads((PACKAGE_DIR / "annotations" / f"{cid}.json").read_text(encoding="utf-8"))
        assert ann["chip_id"] == cid
        assert "annotation_version" in ann
        assert "chip_annotation_status" in ann
        assert "annotations" in ann
        assert "context_metadata" in ann
        assert "consensus_provenance" in ann

        for b in ann["annotations"]:
            total_boxes += 1
            assert b["class_name"] in ALLOWED_CLASSES
            assert b["class_id"] == CLASS_ID_MAP[b["class_name"]]
    assert total_boxes == 10, f"Expected exactly 10 bounding boxes across cohort, got {total_boxes}"


def test_6_bounding_box_geometry_and_no_placeholders():
    for cid in EXPECTED_15_CHIPS:
        ann = json.loads((PACKAGE_DIR / "annotations" / f"{cid}.json").read_text(encoding="utf-8"))
        for b in ann["annotations"]:
            bbox = b["bbox"]
            xmin, ymin, xmax, ymax = bbox["x_min"], bbox["y_min"], bbox["x_max"], bbox["y_max"]
            assert 0 <= xmin < xmax <= 512
            assert 0 <= ymin < ymax <= 512
            assert (xmax - xmin) >= 4
            assert (ymax - ymin) >= 4
            assert not (xmin == 200 and ymin == 200 and xmax == 300 and ymax == 300), "Placeholder coordinates detected!"


def test_7_visual_evidence_zero_contradictions():
    for cid in EXPECTED_15_CHIPS:
        ann = json.loads((PACKAGE_DIR / "annotations" / f"{cid}.json").read_text(encoding="utf-8"))
        for b in ann["annotations"]:
            bev = b.get("visual_evidence", [])
            has_pos = ("DIRECT_FIRE_VISIBLE" in bev or "BURN_SCAR_VISIBLE" in bev)
            has_neg = ("NO_CLEAR_VISUAL_EVIDENCE" in bev)
            assert not (has_pos and has_neg), f"{cid} contains contradictory evidence: {bev}"


def test_8_definitive_observation_status():
    for cid in EXPECTED_15_CHIPS:
        ann = json.loads((PACKAGE_DIR / "annotations" / f"{cid}.json").read_text(encoding="utf-8"))
        st = ann["chip_annotation_status"]
        assert st in ["HAS_ANNOTATIONS", "NO_VISIBLE_TARGET"], f"Invalid or non-definitive status: {st}"
        if st == "NO_VISIBLE_TARGET":
            assert len(ann["annotations"]) == 0
        if st == "HAS_ANNOTATIONS":
            assert len(ann["annotations"]) > 0


def test_9_provenance_and_stage_traceability():
    manifest = json.loads((PACKAGE_DIR / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["chips"]:
        cid = entry["chip_id"]
        prov = entry["source_provenance"]
        if cid in UNANIMOUS_9_CHIPS:
            assert prov["source_cohort"] == "UNANIMOUS_AGREEMENT"
            assert prov["source_stage"] == "STAGE_8_14"
        elif cid in DISPUTED_6_CHIPS:
            assert prov["source_cohort"] == "HUMAN_ADJUDICATED_CONSENSUS"
            assert prov["source_stage"] == "STAGE_8_16"
            # Verify primary source is the Stage 8.16 corrected file, NOT the Stage 8.15 review file
            assert "corrections" in prov["primary_source_path"]
            assert "corrected_v2" in prov["primary_source_path"]


def test_10_excluded_chips_and_quarantine_isolation():
    for exc in EXCLUDED_5_CHIPS:
        assert not any(exc in p.name for p in PACKAGE_DIR.glob("**/*")), f"Excluded chip {exc} present in package!"

    package_hashes = {compute_sha256(p) for p in PACKAGE_DIR.glob("**/*") if p.is_file()}
    for qf in QUARANTINE_DIR.glob("**/*.json"):
        qh = compute_sha256(qf)
        assert qh not in package_hashes, f"Quarantined invalid file {qf.name} hash leaked into package!"


def test_11_baseline_a1_a2_and_frozen_predecessors_protected():
    a1_files = list(A1_DIR.glob("*.json"))
    a2_files = list(A2_DIR.glob("*.json"))
    assert len(a1_files) == 15 and len(a2_files) == 15

    p02 = A1_DIR / "PILOT_02_NORTH_annotator1.json"
    assert compute_sha256(p02) == "a7b3e2a1796c64ba4b2d6e1afdfae23c2144b0b1effe223597b100fa1bdf1d50"

    src_manifest = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    for cid, finfo in src_manifest["files"].items():
        fp = REVIEW_DIR / finfo["filename"]
        assert compute_sha256(fp) == finfo["sha256"]

    for rel_p, exp_h in FROZEN_PREDECESSORS.items():
        fp = PROJECT_ROOT / rel_p
        assert compute_sha256(fp) == exp_h


def test_12_validation_report_generated_and_passing():
    val_report_path = PACKAGE_DIR / "validation_report.json"
    assert val_report_path.exists(), "validation_report.json missing"
    vr = json.loads(val_report_path.read_text(encoding="utf-8"))
    assert vr["overall_status"] == "PASSED", f"Validation status is {vr['overall_status']}"
    assert vr["failures_count"] == 0, f"Failures detected: {vr['failures_count']}"
    assert len(vr["checks"]) == 10, f"Expected 10 checks, got {len(vr['checks'])}"
