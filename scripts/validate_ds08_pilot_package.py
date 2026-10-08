#!/usr/bin/env python3
"""
DS08 Stage 8.17: Comprehensive Read-Only Package Validation Script
------------------------------------------------------------------
Executes rigorous, read-only validation across the ds08_pilot_v1 dataset package:
1. Cohort membership & duplicate prevention.
2. Complete file inventory & media matching (GeoTIFF, RGB, SWIR, metadata).
3. Annotation schema compliance & class validation.
4. Bounding box coordinates & geometric integrity.
5. Visual evidence flag consistency (zero contradictions).
6. Definitive observation status enforcement (zero UNRESOLVED).
7. Traceable provenance & cryptographic source hashes.
8. Package manifest integrity & internal bit-for-bit checksums.
9. Protection of baseline A1/A2, review records, and frozen predecessors.
10. Proper exclusion of screening chips and quarantine isolation.

Outputs machine-readable validation report:
  data/reference/ds08/packages/ds08_pilot_v1/validation_report.json
  data/reference/ds08/annotations/review/stage8_17_validation_report.json
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Paths
DATA_DIR = PROJECT_ROOT / "data" / "reference" / "ds08"
PACKAGE_DIR = DATA_DIR / "packages" / "ds08_pilot_v1"
A1_DIR = DATA_DIR / "annotations" / "manual" / "annotator_1"
A2_DIR = DATA_DIR / "annotations" / "manual" / "annotator_2"
REVIEW_DIR = DATA_DIR / "annotations" / "adjudication" / "review"
CORRECTIONS_DIR = DATA_DIR / "annotations" / "adjudication" / "corrections"
SOURCE_MANIFEST_PATH = DATA_DIR / "annotations" / "adjudication" / "stage8_16_source_manifest.json"
QUARANTINE_DIR = DATA_DIR / "annotations" / "quarantine"
REPORT_OUTPUT_DIR = DATA_DIR / "annotations" / "review"

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
    """Computes SHA-256 hex digest of file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def validate_package() -> Dict[str, Any]:
    print("=" * 70)
    print("STARTING DS08 STAGE 8.17 PACKAGE VALIDATION AUDIT")
    print("=" * 70)

    report: Dict[str, Any] = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "package_directory": str(PACKAGE_DIR.relative_to(PROJECT_ROOT)),
        "checks": {},
        "overall_status": "PENDING",
        "failures_count": 0,
        "warnings_count": 0,
    }

    def record_check(check_id: str, title: str, status: str, details: Dict[str, Any], errors: List[str]):
        report["checks"][check_id] = {
            "title": title,
            "status": status,  # "PASS", "FAIL", "NOT VERIFIED"
            "details": details,
            "errors": errors,
        }
        if status == "FAIL":
            report["failures_count"] += len(errors) if errors else 1

    # -------------------------------------------------------------
    # Check 1: Cohort Membership & Uniqueness
    # -------------------------------------------------------------
    c1_errors = []
    manifest_path = PACKAGE_DIR / "manifest.json"
    if not manifest_path.exists():
        c1_errors.append(f"manifest.json missing at {manifest_path}")
        record_check("CHECK_1_COHORT_MEMBERSHIP", "Expected Cohort Membership & Duplicate Prevention", "FAIL", {}, c1_errors)
        return report

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    chips_in_manifest = [c["chip_id"] for c in manifest_data.get("chips", [])]
    unique_chips = sorted(list(set(chips_in_manifest)))

    if len(chips_in_manifest) != 15:
        c1_errors.append(f"Expected exactly 15 chips in manifest, found {len(chips_in_manifest)}")
    if len(unique_chips) != len(chips_in_manifest):
        c1_errors.append(f"Duplicate chip IDs detected in manifest: {len(chips_in_manifest) - len(unique_chips)} duplicates")
    if unique_chips != EXPECTED_15_CHIPS:
        c1_errors.append(f"Mismatch in expected chip cohort: missing {set(EXPECTED_15_CHIPS) - set(unique_chips)}, extra {set(unique_chips) - set(EXPECTED_15_CHIPS)}")

    record_check(
        "CHECK_1_COHORT_MEMBERSHIP",
        "Expected Cohort Membership & Duplicate Prevention",
        "PASS" if not c1_errors else "FAIL",
        {"total_chips": len(chips_in_manifest), "unique_chips": len(unique_chips)},
        c1_errors,
    )

    # -------------------------------------------------------------
    # Check 2: File Inventory & Image-to-Annotation Matching
    # -------------------------------------------------------------
    c2_errors = []
    c2_details = {"verified_files": 0, "chips_fully_matched": 0}

    for cid in EXPECTED_15_CHIPS:
        ann_file = PACKAGE_DIR / "annotations" / f"{cid}.json"
        tif_file = PACKAGE_DIR / "chips" / f"{cid}_chip.tif"
        rgb_file = PACKAGE_DIR / "previews" / f"{cid}_rgb.png"
        swir_file = PACKAGE_DIR / "previews" / f"{cid}_swir.png"
        meta_file = PACKAGE_DIR / "metadata" / f"{cid}_metadata.json"

        chip_files_ok = True
        for ftype, fp in [("Annotation", ann_file), ("GeoTIFF", tif_file), ("RGB", rgb_file), ("SWIR", swir_file), ("Metadata", meta_file)]:
            if not fp.exists():
                c2_errors.append(f"{cid}: {ftype} file missing ({fp.name})")
                chip_files_ok = False
            elif fp.stat().st_size == 0:
                c2_errors.append(f"{cid}: {ftype} file is empty (0 bytes)")
                chip_files_ok = False
            else:
                c2_details["verified_files"] += 1

        if chip_files_ok:
            c2_details["chips_fully_matched"] += 1

    record_check(
        "CHECK_2_IMAGE_ANNOTATION_MATCHING",
        "Complete File Inventory & Image-to-Annotation Matching",
        "PASS" if not c2_errors else "FAIL",
        c2_details,
        c2_errors,
    )

    # -------------------------------------------------------------
    # Check 3: Annotation Schema & Valid Class Names
    # -------------------------------------------------------------
    c3_errors = []
    total_boxes = 0
    class_counts = {}

    for cid in EXPECTED_15_CHIPS:
        ann_file = PACKAGE_DIR / "annotations" / f"{cid}.json"
        if not ann_file.exists(): continue
        ann_data = json.loads(ann_file.read_text(encoding="utf-8"))

        # Required fields
        for rf in ["chip_id", "annotation_version", "chip_annotation_status", "annotations", "context_metadata", "consensus_provenance"]:
            if rf not in ann_data:
                c3_errors.append(f"{cid}: missing required top-level field '{rf}'")

        # Class names
        for bidx, box in enumerate(ann_data.get("annotations", []), 1):
            total_boxes += 1
            cname = box.get("class_name")
            cid_val = box.get("class_id")
            class_counts[cname] = class_counts.get(cname, 0) + 1

            if cname not in ALLOWED_CLASSES:
                c3_errors.append(f"{cid} Box #{bidx}: invalid class_name '{cname}'")
            if cid_val != CLASS_ID_MAP.get(cname):
                c3_errors.append(f"{cid} Box #{bidx}: class_id {cid_val} does not match class_name '{cname}'")

    record_check(
        "CHECK_3_SCHEMA_AND_CLASSES",
        "Annotation Schema & Target Class Name Compliance",
        "PASS" if not c3_errors else "FAIL",
        {"total_boxes_audited": total_boxes, "class_counts": class_counts},
        c3_errors,
    )

    # -------------------------------------------------------------
    # Check 4: Bounding Box Geometry & Limits
    # -------------------------------------------------------------
    c4_errors = []
    c4_details = {"boxes_audited": 0, "widths": [], "heights": []}

    for cid in EXPECTED_15_CHIPS:
        ann_file = PACKAGE_DIR / "annotations" / f"{cid}.json"
        if not ann_file.exists(): continue
        ann_data = json.loads(ann_file.read_text(encoding="utf-8"))

        for bidx, box in enumerate(ann_data.get("annotations", []), 1):
            c4_details["boxes_audited"] += 1
            bbox = box.get("bbox", {})
            xmin = bbox.get("x_min", -1)
            ymin = bbox.get("y_min", -1)
            xmax = bbox.get("x_max", -1)
            ymax = bbox.get("y_max", -1)

            if not (0 <= xmin < xmax <= 512 and 0 <= ymin < ymax <= 512):
                c4_errors.append(f"{cid} Box #{bidx}: coordinate out of bounds {bbox}")

            w = xmax - xmin
            h = ymax - ymin
            c4_details["widths"].append(w)
            c4_details["heights"].append(h)

            if w < 4 or h < 4:
                c4_errors.append(f"{cid} Box #{bidx}: box dimension too small (< 4px): w={w}, h={h}")

            if xmin == 200 and ymin == 200 and xmax == 300 and ymax == 300:
                c4_errors.append(f"{cid} Box #{bidx}: prohibited placeholder coordinate [200, 200, 300, 300]")

    record_check(
        "CHECK_4_BBOX_GEOMETRY",
        "Bounding Box Geometry, Bounds & Placeholder Detection",
        "PASS" if not c4_errors else "FAIL",
        {
            "total_boxes": c4_details["boxes_audited"],
            "min_width": min(c4_details["widths"]) if c4_details["widths"] else 0,
            "max_width": max(c4_details["widths"]) if c4_details["widths"] else 0,
            "min_height": min(c4_details["heights"]) if c4_details["heights"] else 0,
            "max_height": max(c4_details["heights"]) if c4_details["heights"] else 0,
        },
        c4_errors,
    )

    # -------------------------------------------------------------
    # Check 5: Visual Evidence Consistency (Zero Contradictions)
    # -------------------------------------------------------------
    c5_errors = []
    total_evidence_tags = 0

    for cid in EXPECTED_15_CHIPS:
        ann_file = PACKAGE_DIR / "annotations" / f"{cid}.json"
        if not ann_file.exists(): continue
        ann_data = json.loads(ann_file.read_text(encoding="utf-8"))

        for bidx, box in enumerate(ann_data.get("annotations", []), 1):
            bev = box.get("visual_evidence", [])
            total_evidence_tags += len(bev)
            has_pos = ("DIRECT_FIRE_VISIBLE" in bev or "BURN_SCAR_VISIBLE" in bev)
            has_neg = ("NO_CLEAR_VISUAL_EVIDENCE" in bev)

            if has_pos and has_neg:
                c5_errors.append(f"{cid} Box #{bidx}: contradictory visual evidence: positive fire tags + NO_CLEAR_VISUAL_EVIDENCE")

    record_check(
        "CHECK_5_EVIDENCE_CONSISTENCY",
        "Visual Evidence Consistency & Contradiction Elimination",
        "PASS" if not c5_errors else "FAIL",
        {"total_evidence_tags_audited": total_evidence_tags, "contradictions_found": len(c5_errors)},
        c5_errors,
    )

    # -------------------------------------------------------------
    # Check 6: Definitive Status & Valid Empty Cases
    # -------------------------------------------------------------
    c6_errors = []
    status_counts = {}

    for cid in EXPECTED_15_CHIPS:
        ann_file = PACKAGE_DIR / "annotations" / f"{cid}.json"
        if not ann_file.exists(): continue
        ann_data = json.loads(ann_file.read_text(encoding="utf-8"))
        st = ann_data.get("chip_annotation_status")
        status_counts[st] = status_counts.get(st, 0) + 1
        bcount = len(ann_data.get("annotations", []))

        if st not in ["HAS_ANNOTATIONS", "NO_VISIBLE_TARGET"]:
            c6_errors.append(f"{cid}: invalid observation status '{st}' (UNRESOLVED is strictly prohibited)")

        if st == "NO_VISIBLE_TARGET" and bcount > 0:
            c6_errors.append(f"{cid}: status is NO_VISIBLE_TARGET but has {bcount} annotations (must be empty [])")

        if st == "HAS_ANNOTATIONS" and bcount == 0:
            c6_errors.append(f"{cid}: status is HAS_ANNOTATIONS but has 0 annotations")

    record_check(
        "CHECK_6_DEFINITIVE_STATUS",
        "Definitive Observation Status & Empty-Annotation Cases",
        "PASS" if not c6_errors else "FAIL",
        {"status_counts": status_counts},
        c6_errors,
    )

    # -------------------------------------------------------------
    # Check 7: Provenance & Source Hashes
    # -------------------------------------------------------------
    c7_errors = []
    c7_details = {"unanimous_verified": 0, "adjudicated_verified": 0}

    source_manifest = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))

    for cid in EXPECTED_15_CHIPS:
        ann_file = PACKAGE_DIR / "annotations" / f"{cid}.json"
        if not ann_file.exists(): continue
        ann_data = json.loads(ann_file.read_text(encoding="utf-8"))
        prov = ann_data.get("consensus_provenance", {})

        if cid in UNANIMOUS_9_CHIPS:
            if prov.get("cohort_type") != "UNANIMOUS_AGREEMENT" or prov.get("stage") != "STAGE_8_14":
                c7_errors.append(f"{cid}: expected UNANIMOUS_AGREEMENT provenance from STAGE_8_14")
            # Verify that source hashes in prov match actual disk files
            f1 = A1_DIR / f"{cid}_annotator1.json"
            f2 = A2_DIR / f"{cid}_annotator2.json"
            if not f1.exists() or not f2.exists():
                c7_errors.append(f"{cid}: source A1 or A2 file missing")
            else:
                h1 = compute_sha256(f1)
                h2 = compute_sha256(f2)
                if prov["source_hashes"]["annotator_1_sha256"] != h1:
                    c7_errors.append(f"{cid}: A1 source hash mismatch")
                if prov["source_hashes"]["annotator_2_sha256"] != h2:
                    c7_errors.append(f"{cid}: A2 source hash mismatch")
            c7_details["unanimous_verified"] += 1

        elif cid in DISPUTED_6_CHIPS:
            if prov.get("cohort_type") != "HUMAN_ADJUDICATED_CONSENSUS" or prov.get("stage") != "STAGE_8_16":
                c7_errors.append(f"{cid}: expected HUMAN_ADJUDICATED_CONSENSUS provenance from STAGE_8_16")

            # Verify that source is Stage 8.16 corrected file and matches disk
            corr_file = CORRECTIONS_DIR / f"{cid}_corrected_v2.json"
            if not corr_file.exists():
                c7_errors.append(f"{cid}: Stage 8.16 correction file missing: {corr_file.name}")
            else:
                actual_corr_h = compute_sha256(corr_file)
                if prov["source_hashes"]["stage8_16_corrected_sha256"] != actual_corr_h:
                    c7_errors.append(f"{cid}: Stage 8.16 correction file hash mismatch")

            # Verify source Stage 8.15 record hash against immutable manifest
            exp_815_sha = source_manifest["files"][cid]["sha256"]
            if prov["source_hashes"]["stage8_15_source_sha256"] != exp_815_sha:
                c7_errors.append(f"{cid}: embedded Stage 8.15 source hash mismatch")
            c7_details["adjudicated_verified"] += 1

    record_check(
        "CHECK_7_PROVENANCE_AND_SOURCE_HASHES",
        "Authoritative Provenance & Cryptographic Source Hashes",
        "PASS" if not c7_errors else "FAIL",
        c7_details,
        c7_errors,
    )

    # -------------------------------------------------------------
    # Check 8: Package Manifest Integrity & File Checksums
    # -------------------------------------------------------------
    c8_errors = []
    c8_details = {"package_files_verified": 0}

    for entry in manifest_data.get("chips", []):
        cid = entry["chip_id"]
        for ftype, finfo in entry.get("files", {}).items():
            rel_p = finfo["path"]
            exp_sha = finfo["sha256"]
            actual_file = PACKAGE_DIR / rel_p

            if not actual_file.exists():
                c8_errors.append(f"Package file missing: {rel_p}")
                continue

            actual_sha = compute_sha256(actual_file)
            if actual_sha != exp_sha:
                c8_errors.append(f"Checksum mismatch for {rel_p}: expected {exp_sha}, got {actual_sha}")
            else:
                c8_details["package_files_verified"] += 1

    record_check(
        "CHECK_8_PACKAGE_MANIFEST_INTEGRITY",
        "Package Manifest Internal Integrity & Bit-for-Bit Checksums",
        "PASS" if not c8_errors else "FAIL",
        c8_details,
        c8_errors,
    )

    # -------------------------------------------------------------
    # Check 9: Protection of Predecessors & Baselines
    # -------------------------------------------------------------
    c9_errors = []
    # A1/A2
    a1_files = list(A1_DIR.glob("*.json"))
    a2_files = list(A2_DIR.glob("*.json"))
    if len(a1_files) != 15 or len(a2_files) != 15:
        c9_errors.append(f"Baseline A1/A2 count mismatch: {len(a1_files)} A1, {len(a2_files)} A2")

    p02_file = A1_DIR / "PILOT_02_NORTH_annotator1.json"
    if compute_sha256(p02_file) != "a7b3e2a1796c64ba4b2d6e1afdfae23c2144b0b1effe223597b100fa1bdf1d50":
        c9_errors.append("Benchmark PILOT_02_NORTH A1 hash changed!")

    # Original Stage 8.15 records
    for cid, finfo in source_manifest["files"].items():
        fp = REVIEW_DIR / finfo["filename"]
        if not fp.exists() or compute_sha256(fp) != finfo["sha256"]:
            c9_errors.append(f"Original Stage 8.15 review file for {cid} was modified or missing")

    # Frozen predecessors
    for rel_p, exp_h in FROZEN_PREDECESSORS.items():
        fp = PROJECT_ROOT / rel_p
        if not fp.exists():
            c9_errors.append(f"Frozen predecessor missing: {rel_p}")
        elif compute_sha256(fp) != exp_h:
            c9_errors.append(f"Frozen predecessor altered: {rel_p}")

    record_check(
        "CHECK_9_PREDECESSORS_AND_BASELINES",
        "Baseline Annotations, Review Records & Predecessors Immutability",
        "PASS" if not c9_errors else "FAIL",
        {"predecessors_audited": len(FROZEN_PREDECESSORS), "baseline_files": len(a1_files) + len(a2_files)},
        c9_errors,
    )

    # -------------------------------------------------------------
    # Check 10: Excluded Chips & Quarantine Isolation
    # -------------------------------------------------------------
    c10_errors = []
    # Verify excluded chips not in package
    for exc_id in EXCLUDED_5_CHIPS:
        if any(exc_id in p.name for p in PACKAGE_DIR.glob("**/*")):
            c10_errors.append(f"Excluded screening chip {exc_id} found inside package!")

    # Verify quarantine files have zero hash collision with package
    package_hashes = {compute_sha256(p) for p in PACKAGE_DIR.glob("**/*") if p.is_file()}
    quarantine_files = list(QUARANTINE_DIR.glob("**/*.json"))
    for qf in quarantine_files:
        qh = compute_sha256(qf)
        if qh in package_hashes:
            c10_errors.append(f"HASH COLLISION: Quarantined invalid file {qf.name} matches a file in package!")

    record_check(
        "CHECK_10_EXCLUSION_AND_QUARANTINE_ISOLATION",
        "Screening Chip Exclusion & Quarantine Boundary Isolation",
        "PASS" if not c10_errors else "FAIL",
        {"excluded_chips_verified": len(EXCLUDED_5_CHIPS), "quarantine_files_audited": len(quarantine_files)},
        c10_errors,
    )

    # Overall Status
    report["overall_status"] = "PASSED" if report["failures_count"] == 0 else "FAILED"

    # Save reports
    REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out1 = PACKAGE_DIR / "validation_report.json"
    out2 = REPORT_OUTPUT_DIR / "stage8_17_validation_report.json"

    with open(out1, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    with open(out2, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nVALIDATION COMPLETED: {report['overall_status']}")
    print(f"Total Checks: {len(report['checks'])} | Failures: {report['failures_count']}")
    print(f"Report written to: {out1} and {out2}")
    print("=" * 70)

    return report


if __name__ == "__main__":
    report = validate_package()
    sys.exit(0 if report["overall_status"] == "PASSED" else 1)
