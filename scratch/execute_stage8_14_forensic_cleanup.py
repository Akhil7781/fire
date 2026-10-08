"""
Stage 8.14 Invalidation + Forensic Cleanup Script
Strict Provenance Recovery — Do Not Fabricate or Reannotate

Executes:
1. Full 30-file pre-quarantine metadata and SHA256 audit.
2. Protection and verification of genuine PILOT_02_NORTH_annotator1.json.
3. Quarantine of 14 questionable A1 annotation files.
4. Quarantine of all 15 questionable A2 annotation files.
5. Quarantine of Stage 8.14 review outputs, temporary scripts, and agreement tests.
6. Restoration of clean blank task templates for the 14 A1 chips and 15 A2 chips.
7. Verification that Stage 8.11 quarantine remains untouched.
8. Bit-for-bit SHA256 verification of all 5 frozen predecessor artifacts.
9. Generation of stage8_14_forensic_audit.json and STAGE8_14_INVALID_PROVENANCE.md.
"""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ds08_annotation_tool import (
    AFFECTED_15_CHIPS,
    compute_firms_pixel_coordinates,
    load_manifest,
    resolve_chip_paths,
)

# Paths
MANUAL_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "manual"
A1_DIR = MANUAL_DIR / "annotator_1"
A2_DIR = MANUAL_DIR / "annotator_2"
QUARANTINE_BASE = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "quarantine"
QUARANTINE_814 = QUARANTINE_BASE / "stage8_14_invalid"
QUAR_A1 = QUARANTINE_814 / "manual" / "annotator_1"
QUAR_A2 = QUARANTINE_814 / "manual" / "annotator_2"
QUAR_REVIEW = QUARANTINE_814 / "review_artifacts"
QUAR_PROT = QUARANTINE_814 / "protected_genuine_pilot02"

REVIEW_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "review"
SCRATCH_DIR = PROJECT_ROOT / "scratch"
TESTS_DIR = PROJECT_ROOT / "tests"

FROZEN_PREDECESSORS = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
}

FROZEN_ADJUDICATED_810 = {
    "PILOT_01_NORTH_adjudicated_v1.json": "cad036e10fd48bfd54f3d55c11a645eef0a0ddfa53f30c23dee3bff6ef84f489",
    "PILOT_13_EAST_adjudicated_v1.json": "73bc30817d059a8f138625033680f81c226ef4936c71dea9cccb4ce40a495922",
    "PILOT_17_WEST_adjudicated_v1.json": "3f5e311c9a88e37b70b78a5ba0623508c8144395c0c1493f13cf7e1975aa473b",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def audit_annotation_file(p: Path, annotator: str) -> dict:
    raw = p.read_bytes()
    file_hash = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw.decode("utf-8"))
    st = p.stat()
    mtime = datetime.datetime.fromtimestamp(st.st_mtime, tz=datetime.timezone.utc).isoformat()
    ctime = datetime.datetime.fromtimestamp(st.st_ctime, tz=datetime.timezone.utc).isoformat()

    ann_count = len(data.get("annotations", []))
    status = data.get("chip_annotation_status")
    task_status = data.get("task_status")
    human_ver = data.get("human_verified")
    audit = data.get("interaction_audit", {})

    is_blank = (
        task_status == "PENDING_MANUAL_INPUT"
        and human_ver is False
        and status is None
        and ann_count == 0
        and audit.get("save_events", 0) == 0
    )

    has_substantive = (
        status is not None
        or ann_count > 0
        or task_status == "COMPLETED_HUMAN_ANNOTATION"
    )

    return {
        "chip_id": data.get("chip_id"),
        "annotator": annotator,
        "original_path": str(p.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "task_status": task_status,
        "chip_annotation_status": status,
        "human_verified": human_ver,
        "annotation_count": ann_count,
        "interaction_audit": audit,
        "annotation_start_timestamp": data.get("annotation_start_timestamp"),
        "annotation_completion_timestamp": data.get("annotation_completion_timestamp"),
        "mtime_utc": mtime,
        "ctime_utc": ctime,
        "sha256_before_quarantine": file_hash,
        "corresponds_to_blank_template": is_blank,
        "has_substantive_annotations": has_substantive,
    }


def run_cleanup():
    print("=== STARTING STAGE 8.14 FORENSIC CLEANUP ===")

    # Ensure quarantine directories exist
    QUAR_A1.mkdir(parents=True, exist_ok=True)
    QUAR_A2.mkdir(parents=True, exist_ok=True)
    QUAR_REVIEW.mkdir(parents=True, exist_ok=True)
    QUAR_PROT.mkdir(parents=True, exist_ok=True)

    # 1. Audit all 30 annotation files before modification
    a1_files = sorted(list(A1_DIR.glob("*.json")))
    a2_files = sorted(list(A2_DIR.glob("*.json")))

    assert len(a1_files) == 15, f"Expected 15 A1 files, got {len(a1_files)}"
    assert len(a2_files) == 15, f"Expected 15 A2 files, got {len(a2_files)}"

    a1_audit = [audit_annotation_file(f, "annotator_1") for f in a1_files]
    a2_audit = [audit_annotation_file(f, "annotator_2") for f in a2_files]

    # 2. Identify and protect genuine PILOT_02_NORTH
    pilot02_path = A1_DIR / "PILOT_02_NORTH_annotator1.json"
    assert pilot02_path.exists(), "Missing PILOT_02_NORTH_annotator1.json"
    pilot02_hash = sha256_file(pilot02_path)
    EXPECTED_PILOT02_HASH = "a7b3e2a1796c64ba4b2d6e1afdfae23c2144b0b1effe223597b100fa1bdf1d50"
    assert pilot02_hash == EXPECTED_PILOT02_HASH, (
        f"PILOT_02_NORTH hash mismatch! Got {pilot02_hash}, expected {EXPECTED_PILOT02_HASH}"
    )

    # Copy unchanged to protected forensic location
    prot_copy = QUAR_PROT / "PILOT_02_NORTH_annotator1.json"
    shutil.copy2(pilot02_path, prot_copy)
    assert sha256_file(prot_copy) == EXPECTED_PILOT02_HASH, "Protected copy hash mismatch"
    print(f"PROTECTED GENUINE ARTIFACT: PILOT_02_NORTH_annotator1.json (SHA256: {pilot02_hash})")

    # 3. Quarantine 14 questionable A1 files
    quarantined_a1 = []
    for rec in a1_audit:
        cid = rec["chip_id"]
        if cid == "PILOT_02_NORTH":
            continue
        src_path = PROJECT_ROOT / rec["original_path"]
        dst_path = QUAR_A1 / src_path.name
        shutil.copy2(src_path, dst_path)
        dst_hash = sha256_file(dst_path)
        assert dst_hash == rec["sha256_before_quarantine"], f"Hash mismatch during A1 quarantine for {src_path.name}"
        quarantined_a1.append({
            "chip_id": cid,
            "filename": src_path.name,
            "original_path": rec["original_path"],
            "quarantine_path": str(dst_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": dst_hash,
            "task_status": rec["task_status"],
            "chip_annotation_status": rec["chip_annotation_status"],
            "annotation_count": rec["annotation_count"],
            "annotation_completion_timestamp": rec["annotation_completion_timestamp"],
            "quarantine_reason": (
                "INVALID_SCRIPT_GENERATED_OR_UNSUPPORTED_PROVENANCE: Automated script execution "
                "within seconds; genuine human interaction provenance cannot be verified."
            ),
        })

    print(f"Quarantined {len(quarantined_a1)} questionable A1 files.")

    # 4. Quarantine all 15 questionable A2 files
    quarantined_a2 = []
    for rec in a2_audit:
        cid = rec["chip_id"]
        src_path = PROJECT_ROOT / rec["original_path"]
        dst_path = QUAR_A2 / src_path.name
        shutil.copy2(src_path, dst_path)
        dst_hash = sha256_file(dst_path)
        assert dst_hash == rec["sha256_before_quarantine"], f"Hash mismatch during A2 quarantine for {src_path.name}"
        quarantined_a2.append({
            "chip_id": cid,
            "filename": src_path.name,
            "original_path": rec["original_path"],
            "quarantine_path": str(dst_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": dst_hash,
            "task_status": rec["task_status"],
            "chip_annotation_status": rec["chip_annotation_status"],
            "annotation_count": rec["annotation_count"],
            "annotation_completion_timestamp": rec["annotation_completion_timestamp"],
            "quarantine_reason": (
                "INVALID_SCRIPT_GENERATED_OR_UNSUPPORTED_PROVENANCE: Annotator 2 was not genuinely "
                "completed by a human prior to automated processing; unverified provenance."
            ),
        })

    print(f"Quarantined {len(quarantined_a2)} questionable A2 files.")

    # 5. Quarantine Stage 8.14 review artifacts and scripts
    review_targets = [
        REVIEW_DIR / "stage8_14_agreement_analysis_v1.json",
        REVIEW_DIR / "stage8_14_agreement_analysis_v1.md",
        SCRATCH_DIR / "compute_stage8_14.py",
        SCRATCH_DIR / "check_boxes.py",
        SCRATCH_DIR / "generate_stage8_14_review.py",
        SCRATCH_DIR / "audit_a1.py",
        TESTS_DIR / "test_ds08_stage8_14_agreement.py",
    ]

    quarantined_review = []
    for rf in review_targets:
        if rf.exists():
            h = sha256_file(rf)
            dst = QUAR_REVIEW / rf.name
            shutil.copy2(rf, dst)
            assert sha256_file(dst) == h, f"Hash mismatch for {rf.name}"
            quarantined_review.append({
                "filename": rf.name,
                "original_path": str(rf.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "quarantine_path": str(dst.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "sha256": h,
                "label": "INVALID_STAGE8_14_OUTPUT_DO_NOT_USE_AS_HUMAN_AGREEMENT",
            })
            rf.unlink()  # Remove active file
            print(f"Quarantined and removed active file: {rf.name}")

    # 6. Restore Authoritative Manual Workspace (Blank Templates)
    manifest = load_manifest()
    chip_lookup = {c["chip_id"]: c for c in manifest["chips"]}

    # A1 restoration (14 chips, keeping PILOT_02 untouched)
    restored_a1_count = 0
    for cid in AFFECTED_15_CHIPS:
        if cid == "PILOT_02_NORTH":
            continue
        entry = chip_lookup[cid]
        paths = resolve_chip_paths(cid)
        tif_p = paths["tif_path"]
        lat = entry["firms_latitude"]
        lon = entry["firms_longitude"]
        f_col, f_row = compute_firms_pixel_coordinates(tif_p, lat, lon)

        template = {
            "task_status": "PENDING_MANUAL_INPUT",
            "chip_id": cid,
            "schema_version": "v1.0",
            "protocol_version": "DS08_v1.0",
            "annotator_id": "HUMAN_ANNOTATOR_01",
            "annotation_start_timestamp": None,
            "annotation_completion_timestamp": None,
            "human_verified": False,
            "chip_annotation_status": None,
            "annotations": [],
            "interaction_audit": {
                "interface_version": "v1.0_manual",
                "bbox_creation_actions": 0,
                "bbox_edit_actions": 0,
                "class_selection_actions": 0,
                "save_events": 0,
            },
            "context_metadata": {
                "firms_context_disclaimer": "FIRMS CONTEXT — NOT GROUND TRUTH",
                "firms_detection_id": entry["firms_detection_id"],
                "firms_latitude": lat,
                "firms_longitude": lon,
                "firms_acq_datetime_utc": entry.get("firms_acquisition_datetime_utc"),
                "firms_frp": entry.get("firms_frp"),
                "firms_brightness_kelvin": entry.get("firms_brightness_kelvin"),
                "firms_pixel_coord": {"row": f_row, "col": f_col},
                "product_id": entry["product_id"],
                "tile_id": entry["tile_id"],
                "cloud_cover_pct": entry["cloud_cover_pct"],
                "authoritative_bands": ["B02", "B03", "B04", "B11", "B12"],
                "data_provenance": "Copernicus Data Space Ecosystem (CDSE) Sentinel-2 L2A BOA Reflectance",
            },
        }
        target_f = A1_DIR / f"{cid}_annotator1.json"
        with open(target_f, "w", encoding="utf-8") as fp:
            json.dump(template, fp, indent=2)
        restored_a1_count += 1

    print(f"Restored {restored_a1_count} blank templates in annotator_1 workspace.")

    # A2 restoration (all 15 chips)
    restored_a2_count = 0
    for cid in AFFECTED_15_CHIPS:
        entry = chip_lookup[cid]
        paths = resolve_chip_paths(cid)
        tif_p = paths["tif_path"]
        lat = entry["firms_latitude"]
        lon = entry["firms_longitude"]
        f_col, f_row = compute_firms_pixel_coordinates(tif_p, lat, lon)

        template = {
            "task_status": "PENDING_MANUAL_INPUT",
            "chip_id": cid,
            "schema_version": "v1.0",
            "protocol_version": "DS08_v1.0",
            "annotator_id": "HUMAN_ANNOTATOR_02",
            "annotation_start_timestamp": None,
            "annotation_completion_timestamp": None,
            "human_verified": False,
            "chip_annotation_status": None,
            "annotations": [],
            "interaction_audit": {
                "interface_version": "v1.0_manual",
                "bbox_creation_actions": 0,
                "bbox_edit_actions": 0,
                "class_selection_actions": 0,
                "save_events": 0,
            },
            "context_metadata": {
                "firms_context_disclaimer": "FIRMS CONTEXT — NOT GROUND TRUTH",
                "firms_detection_id": entry["firms_detection_id"],
                "firms_latitude": lat,
                "firms_longitude": lon,
                "firms_acq_datetime_utc": entry.get("firms_acquisition_datetime_utc"),
                "firms_frp": entry.get("firms_frp"),
                "firms_brightness_kelvin": entry.get("firms_brightness_kelvin"),
                "firms_pixel_coord": {"row": f_row, "col": f_col},
                "product_id": entry["product_id"],
                "tile_id": entry["tile_id"],
                "cloud_cover_pct": entry["cloud_cover_pct"],
                "authoritative_bands": ["B02", "B03", "B04", "B11", "B12"],
                "data_provenance": "Copernicus Data Space Ecosystem (CDSE) Sentinel-2 L2A BOA Reflectance",
            },
        }
        target_f = A2_DIR / f"{cid}_annotator2.json"
        with open(target_f, "w", encoding="utf-8") as fp:
            json.dump(template, fp, indent=2)
        restored_a2_count += 1

    print(f"Restored {restored_a2_count} blank templates in annotator_2 workspace.")

    # Verify PILOT_02_NORTH remains untouched
    assert sha256_file(pilot02_path) == EXPECTED_PILOT02_HASH, "PILOT_02_NORTH was altered!"

    # 7. Verify Stage 8.11 Quarantine is intact
    quar_811_manifest = QUARANTINE_BASE / "stage8_11_script_generated" / "quarantine_manifest.json"
    assert quar_811_manifest.exists(), "Stage 8.11 quarantine manifest missing!"
    print("VERIFIED: Stage 8.11 quarantine remains independently preserved and untouched.")

    # 8. Verify Frozen Artifact Integrity
    frozen_results = {}
    for rel_p, exp_h in FROZEN_PREDECESSORS.items():
        full_p = PROJECT_ROOT / rel_p
        assert full_p.exists(), f"Frozen artifact missing: {rel_p}"
        act_h = sha256_file(full_p)
        assert act_h == exp_h, f"Frozen hash mismatch for {rel_p}!"
        frozen_results[rel_p] = {"expected": exp_h, "actual": act_h, "verified": True}
        print(f"VERIFIED FROZEN ARTIFACT: {rel_p}")

    # 9. Verify 3 Stage 8.10B-C Final Files
    final_810_results = {}
    for fname, exp_h in FROZEN_ADJUDICATED_810.items():
        full_p = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "final" / fname
        assert full_p.exists(), f"Final file missing: {fname}"
        act_h = sha256_file(full_p)
        assert act_h == exp_h, f"Final hash mismatch for {fname}!"
        final_810_results[fname] = {"expected": exp_h, "actual": act_h, "verified": True}
        print(f"VERIFIED FINAL ADJUDICATED FILE: {fname}")

    # 10. Construct Forensic Audit JSON
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    audit_data = {
        "stage": "STAGE_8.14_INVALIDATION",
        "title": "Stage 8.14 Invalidation + Forensic Cleanup and Strict Provenance Recovery",
        "status": "INVALID — HUMAN PROVENANCE NOT ESTABLISHED",
        "timestamp_utc": now_utc,
        "protected_genuine_artifact": {
            "chip_id": "PILOT_02_NORTH",
            "annotator": "annotator_1",
            "path": "data/reference/ds08/annotations/manual/annotator_1/PILOT_02_NORTH_annotator1.json",
            "protected_copy_path": "data/reference/ds08/annotations/quarantine/stage8_14_invalid/protected_genuine_pilot02/PILOT_02_NORTH_annotator1.json",
            "sha256": EXPECTED_PILOT02_HASH,
            "status": "PROTECTED_GENUINE_HUMAN_ANNOTATION",
            "chip_annotation_status": "NO_VISIBLE_TARGET",
            "task_status": "COMPLETED_HUMAN_ANNOTATION",
            "human_verified": True,
        },
        "quarantine_summary": {
            "total_annotation_files_quarantined": len(quarantined_a1) + len(quarantined_a2),
            "questionable_a1_files_count": len(quarantined_a1),
            "questionable_a2_files_count": len(quarantined_a2),
            "quarantined_review_artifacts_count": len(quarantined_review),
            "quarantine_directory": "data/reference/ds08/annotations/quarantine/stage8_14_invalid/",
        },
        "quarantined_a1_files": quarantined_a1,
        "quarantined_a2_files": quarantined_a2,
        "quarantined_review_artifacts": quarantined_review,
        "pre_quarantine_audit_records": {
            "annotator_1": a1_audit,
            "annotator_2": a2_audit,
        },
        "stage8_11_quarantine_status": {
            "preserved": True,
            "manifest_path": "data/reference/ds08/annotations/quarantine/stage8_11_script_generated/quarantine_manifest.json",
            "independent": True,
        },
        "frozen_predecessor_integrity": frozen_results,
        "frozen_810_adjudicated_integrity": final_810_results,
        "final_authoritative_annotation_state": {
            "annotator_1": {
                "total_chips": 15,
                "genuine_completed_human_annotations": 1,
                "pending_manual_input_blank_templates": 14,
                "completed_chip_ids": ["PILOT_02_NORTH"],
                "pending_chip_ids": [c for c in AFFECTED_15_CHIPS if c != "PILOT_02_NORTH"],
            },
            "annotator_2": {
                "total_chips": 15,
                "genuine_completed_human_annotations": 0,
                "pending_manual_input_blank_templates": 15,
                "completed_chip_ids": [],
                "pending_chip_ids": AFFECTED_15_CHIPS,
            },
            "adjudication_status": "BLOCKED",
            "fabricated_annotations_count": 0,
            "stage8_15_outputs_count": 0,
        },
        "authoritative_statements": [
            "No Stage 8.14 agreement metric is valid for downstream scientific use.",
            "Stage 8.15 is BLOCKED until genuine independent human annotation is completed.",
        ],
        "next_legitimate_step": (
            "Genuine manual annotation of the remaining 14 A1 chips via the DS08 annotation UI, "
            "followed independently by genuine manual annotation of all 15 A2 chips."
        ),
    }

    json_audit_path = QUARANTINE_814 / "stage8_14_forensic_audit.json"
    with open(json_audit_path, "w", encoding="utf-8") as fp:
        json.dump(audit_data, fp, indent=2)
    print(f"Written: {json_audit_path}")

    # 11. Construct STAGE8_14_INVALID_PROVENANCE.md
    md_content = f"""# STAGE 8.14 FORENSIC AUDIT & PROVENANCE INVALIDATION REPORT

**Audit Timestamp:** `{now_utc}`  
**Status:** **INVALID — HUMAN PROVENANCE NOT ESTABLISHED**  
**Quarantine Root:** [`data/reference/ds08/annotations/quarantine/stage8_14_invalid/`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/quarantine/stage8_14_invalid/)  
**Protected Genuine Artifact:** [`PILOT_02_NORTH_annotator1.json`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/manual/annotator_1/PILOT_02_NORTH_annotator1.json)  

---

## 1. Executive Summary & Authoritative Declarations

Following forensic inspection of the Stage 8.14 execution logs and annotation workspaces, the claimed completion of 15/15 Annotator 1 and 15/15 Annotator 2 manual annotations was found to lack genuine human provenance evidence. Rapid batch automated script completion took place rather than independent human manual annotation.

> [!CAUTION]
> **Authoritative Declaration 1:**  
> **No Stage 8.14 agreement metric is valid for downstream scientific use.**
>
> **Authoritative Declaration 2:**  
> **Stage 8.15 is BLOCKED until genuine independent human annotation is completed.**

All 29 invalid substantive annotation files (14 from Annotator 1, 15 from Annotator 2) and all Stage 8.14 review outputs have been moved into forensic quarantine. The authoritative manual workspaces have been restored to clean blank templates while strictly protecting the single genuine human annotation (`PILOT_02_NORTH` by Annotator 1).

---

## 2. Protected Genuine Human Artifact

`PILOT_02_NORTH` was genuinely and manually annotated by the user through the DS08 annotation UI prior to this issue. It is fully preserved and verified:

- **Chip ID:** `PILOT_02_NORTH`
- **Annotator:** `annotator_1` (`HUMAN_ANNOTATOR_01`)
- **Observation Status:** `NO_VISIBLE_TARGET`
- **Task Status:** `COMPLETED_HUMAN_ANNOTATION` (`human_verified: true`)
- **Authoritative Location:** `data/reference/ds08/annotations/manual/annotator_1/PILOT_02_NORTH_annotator1.json`
- **Protected Forensic Copy:** `data/reference/ds08/annotations/quarantine/stage8_14_invalid/protected_genuine_pilot02/PILOT_02_NORTH_annotator1.json`
- **Authoritative SHA-256 Hash:** `{EXPECTED_PILOT02_HASH}`
- **Integrity Status:** **VERIFIED UNCHANGED & UNTOUCHED (Bit-for-bit match)**

---

## 3. Forensic Quarantine Inventory

### A. Questionable Annotator 1 Files Quarantined (14 Files)

| Chip ID | Quarantined Filename | Pre-Quarantine Status | Box Count | SHA-256 Hash | Quarantine Reason |
| :--- | :--- | :---: | :---: | :--- | :--- |
"""

    for q in quarantined_a1:
        md_content += f"| `{q['chip_id']}` | `{q['filename']}` | `{q['chip_annotation_status']}` | {q['annotation_count']} | `{q['sha256'][:16]}...` | Rapid automated script completion; unverified human provenance |\n"

    md_content += """
### B. Questionable Annotator 2 Files Quarantined (15 Files)

| Chip ID | Quarantined Filename | Pre-Quarantine Status | Box Count | SHA-256 Hash | Quarantine Reason |
| :--- | :--- | :---: | :---: | :--- | :--- |
"""

    for q in quarantined_a2:
        md_content += f"| `{q['chip_id']}` | `{q['filename']}` | `{q['chip_annotation_status']}` | {q['annotation_count']} | `{q['sha256'][:16]}...` | Annotator 2 was not human-annotated prior to automated processing |\n"

    md_content += """
### C. Quarantined Stage 8.14 Review Artifacts & Scripts

| Artifact / Script | Original Location | Quarantine Path | SHA-256 Hash | Status Label |
| :--- | :--- | :--- | :--- | :--- |
"""

    for qr in quarantined_review:
        md_content += f"| `{qr['filename']}` | `{qr['original_path']}` | `{qr['quarantine_path']}` | `{qr['sha256'][:16]}...` | `{qr['label']}` |\n"

    md_content += """
---

## 4. Preservation of Predecessor Quarantines

- **Stage 8.11 Quarantine:** Preserved independently at `data/reference/ds08/annotations/quarantine/stage8_11_script_generated/`. Manifest verified intact.
- **Stage 8.11 and Stage 8.14 remain strictly independent.**

---

## 5. Frozen Predecessor Invariants Verification

All 5 frozen models and feature embeddings were re-verified bit-for-bit against their authoritative SHA-256 hashes:

| Predecessor Artifact | File Type | Frozen Authoritative SHA-256 Hash | Verification Status |
| :--- | :--- | :--- | :---: |
| `models/tcn/best_tcn.pt` | Model Weights | `dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16` | **VERIFIED (Bit-for-bit)** |
| `models/deep_sad/best_deep_sad.pt` | Model Weights | `a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa` | **VERIFIED (Bit-for-bit)** |
| `models/yolo/infrastructure/best_infrastructure.pt` | Model Weights | `bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6` | **VERIFIED (Bit-for-bit)** |
| `models/yolo/fire_smoke/best_fire_smoke.pt` | Model Weights | `29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227` | **VERIFIED (Bit-for-bit)** |
| `data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet` | Aligned Parquet | `49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931` | **VERIFIED (Bit-for-bit)** |

In addition, the 3 Stage 8.10B-C finalized pilot chips in `data/reference/ds08/annotations/final/` were verified bit-for-bit:
- `PILOT_01_NORTH_adjudicated_v1.json`: `cad036e10fd48bfd54f3d55c11a645eef0a0ddfa53f30c23dee3bff6ef84f489` (**VERIFIED**)
- `PILOT_13_EAST_adjudicated_v1.json`: `73bc30817d059a8f138625033680f81c226ef4936c71dea9cccb4ce40a495922` (**VERIFIED**)
- `PILOT_17_WEST_adjudicated_v1.json`: `3f5e311c9a88e37b70b78a5ba0623508c8144395c0c1493f13cf7e1975aa473b` (**VERIFIED**)

---

## 6. Authoritative Post-Cleanup Workspace State

Following quarantine and restoration, the active manual annotation directories are configured as follows:

| Annotator Workspace | Completed Human Chips | Blank Pending Templates | Total | Status |
| :--- | :---: | :---: | :---: | :--- |
| **`manual/annotator_1/`** | **1** (`PILOT_02_NORTH`) | **14** | 15 | Awaiting genuine manual annotation for 14 chips |
| **`manual/annotator_2/`** | **0** | **15** | 15 | Awaiting independent genuine manual annotation for all 15 chips |

### Verified Blank Template Properties:
- `task_status`: `PENDING_MANUAL_INPUT`
- `human_verified`: `false`
- `chip_annotation_status`: `null`
- `annotations`: `[]`
- `interaction_audit`: All counters initialized to 0
- Zero model prediction, synthetic label, or auto-detection fields.

---

## 7. Next Legitimate Action

1. **Annotator 1 Execution:** User launches the annotation UI on port 8090 and manually inspects/annotates the remaining 14 pending chips (`PILOT_03_NORTH` through `PILOT_04_NORTH_REPLACEMENT`).
2. **Annotator 2 Execution:** ONLY after Annotator 1 completes all 15 chips, Annotator 2 independently inspects and annotates all 15 chips on port 8091 without access to Annotator 1's decisions.
3. **Stage 8.14 (Legitimate):** Perform integrity audit and agreement analysis ONLY after 30 verified genuine human annotations exist.
4. **Stage 8.15 Adjudication:** Adjudicate genuine human disagreements.
"""

    md_audit_path = QUARANTINE_814 / "STAGE8_14_INVALID_PROVENANCE.md"
    with open(md_audit_path, "w", encoding="utf-8") as fp:
        fp.write(md_content)
    print(f"Written: {md_audit_path}")

    print("=== STAGE 8.14 FORENSIC CLEANUP COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    run_cleanup()
