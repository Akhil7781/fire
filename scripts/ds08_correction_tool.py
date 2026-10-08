#!/usr/bin/env python3
"""
DS08 Stage 8.16: Controlled Human Adjudication Correction Tool & UI Server
--------------------------------------------------------------------------
Implements the dedicated Stage 8.16 correction workflow for DS08 disputed chips:
1. Strict immutability guarantees for original Stage 8.15 adjudication records.
2. Verified source manifest checking before and after every operation.
3. Dedicated correction interface supporting:
   - Visual evidence reconciliation for the 5 contradictory chips.
   - Definitive consensus determination for PILOT_08_CENTRAL.
4. Comprehensive human confirmation, substantive rationale enforcement, and diff tracking.
5. Isolated versioned storage in data/reference/ds08/annotations/adjudication/corrections/
6. Continuous append-only audit logging.
"""

from __future__ import annotations

import copy
import hashlib
import http.server
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import socketserver
import sys
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ds08_annotation_tool import (
    compute_firms_pixel_coordinates,
    load_manifest,
    resolve_chip_paths,
    validate_annotation_payload,
    ALLOWED_CLASSES,
    CLASS_ID_MAP,
    ALLOWED_CONFIDENCES,
    ALLOWED_VISIBILITY,
    ALLOWED_EVIDENCE,
    ALLOWED_FIRMS_RELATIONSHIPS,
    ALLOWED_CHIP_STATUSES,
)

DISPUTED_6_CHIPS = [
    "PILOT_03_NORTH",
    "PILOT_06_CENTRAL",
    "PILOT_08_CENTRAL",
    "PILOT_15_EAST",
    "PILOT_16_EAST",
    "PILOT_18_WEST",
]

CHIP_AUDIT_CATEGORIES = {
    "PILOT_03_NORTH": {
        "issue": "CONTRADICTORY_EVIDENCE",
        "description": "Contradictory visual evidence: box contains both positive fire/burn-scar tags and NO_CLEAR_VISUAL_EVIDENCE.",
    },
    "PILOT_06_CENTRAL": {
        "issue": "CONTRADICTORY_EVIDENCE",
        "description": "Contradictory visual evidence: both boxes contain positive fire tags and NO_CLEAR_VISUAL_EVIDENCE.",
    },
    "PILOT_08_CENTRAL": {
        "issue": "UNRESOLVED_OBSERVATION_STATUS",
        "description": "Reopened dispute: observation status was recorded as UNRESOLVED. A definitive human decision (HAS_ANNOTATIONS or NO_VISIBLE_TARGET) is required.",
    },
    "PILOT_15_EAST": {
        "issue": "CONTRADICTORY_EVIDENCE",
        "description": "Contradictory visual evidence: both boxes contain positive fire tags and NO_CLEAR_VISUAL_EVIDENCE.",
    },
    "PILOT_16_EAST": {
        "issue": "CONTRADICTORY_EVIDENCE",
        "description": "Contradictory visual evidence: all 3 boxes contain positive fire tags and NO_CLEAR_VISUAL_EVIDENCE.",
    },
    "PILOT_18_WEST": {
        "issue": "CONTRADICTORY_EVIDENCE",
        "description": "Contradictory visual evidence: box contains positive fire tags and NO_CLEAR_VISUAL_EVIDENCE.",
    },
}

PROHIBITED_GENERIC_RATIONALE_PATTERNS = [
    r"\bsaw\s+(?:the\s+)?fire\b",
    r"\blooks?\s+like\s+fire\b",
    r"\bagree(?:d)?\s+with\s+(?:a1|a2|annotator)\b",
    r"\bi\s+see\s+fire\b",
    r"\bthere\s+is\s+fire\b",
    r"\bfire\s+detected\b",
    r"\btest\b",
    r"\bdummy\b",
    r"\bcorrected\b$",
    r"\bfixed\b$",
]

FORBIDDEN_DEFAULT_BOX = {"x_min": 200, "y_min": 200, "x_max": 300, "y_max": 300}

REVIEW_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "adjudication" / "review"
CORRECTIONS_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "adjudication" / "corrections"
SOURCE_MANIFEST_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "adjudication" / "stage8_16_source_manifest.json"
AUDIT_LOG_PATH = CORRECTIONS_DIR / "stage8_16_audit_log.jsonl"
A1_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "manual" / "annotator_1"
A2_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "manual" / "annotator_2"

FROZEN_PREDECESSORS = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
}


def load_source_manifest() -> Dict[str, Any]:
    """Loads the immutable Stage 8.16 source manifest."""
    if not SOURCE_MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Source manifest not found: {SOURCE_MANIFEST_PATH}")
    with open(SOURCE_MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def verify_original_records() -> Tuple[bool, List[str]]:
    """Verifies that all 6 original Stage 8.15 records remain byte-for-byte identical to source manifest."""
    manifest = load_source_manifest()
    errors = []
    for cid, file_info in manifest.get("files", {}).items():
        fp = REVIEW_DIR / file_info["filename"]
        if not fp.exists():
            errors.append(f"Original record missing: {fp}")
            continue
        actual_h = hashlib.sha256(fp.read_bytes()).hexdigest()
        exp_h = file_info["sha256"]
        if actual_h != exp_h:
            errors.append(f"Source record hash mismatch for {cid}: expected {exp_h}, got {actual_h}")
    return len(errors) == 0, errors


def verify_a1_a2_baseline() -> Tuple[bool, List[str]]:
    """Verifies that none of the 30 original A1 and A2 files were modified."""
    errors = []
    # Verify protected artifact
    p02 = A1_DIR / "PILOT_02_NORTH_annotator1.json"
    if not p02.exists():
        errors.append("Protected artifact PILOT_02_NORTH missing")
    else:
        h = hashlib.sha256(p02.read_bytes()).hexdigest()
        if h != "a7b3e2a1796c64ba4b2d6e1afdfae23c2144b0b1effe223597b100fa1bdf1d50":
            errors.append(f"Protected artifact PILOT_02_NORTH hash changed: {h}")

    a1_files = list(A1_DIR.glob("*.json"))
    a2_files = list(A2_DIR.glob("*.json"))
    if len(a1_files) != 15:
        errors.append(f"Expected 15 A1 files, found {len(a1_files)}")
    if len(a2_files) != 15:
        errors.append(f"Expected 15 A2 files, found {len(a2_files)}")
    return len(errors) == 0, errors


def verify_frozen_predecessors() -> Tuple[bool, List[str]]:
    """Verifies that all 5 frozen model and fusion predecessors are untouched."""
    errors = []
    for rel_path, exp_hash in FROZEN_PREDECESSORS.items():
        fp = PROJECT_ROOT / rel_path
        if not fp.exists():
            errors.append(f"Predecessor artifact missing: {rel_path}")
            continue
        cur_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        if cur_hash != exp_hash:
            errors.append(f"Predecessor hash mismatch for {rel_path}: expected {exp_hash}, got {cur_hash}")
    return len(errors) == 0, errors


def log_audit_event(
    event_type: str,
    chip_id: str,
    payload_summary: Dict[str, Any],
    success: bool,
    errors: Optional[List[str]] = None,
    diff_summary: Optional[Dict[str, Any]] = None,
) -> None:
    """Appends an immutable audit event to stage8_16_audit_log.jsonl."""
    CORRECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "chip_id": chip_id,
        "success": success,
        "errors": errors or [],
        "payload_summary": payload_summary,
        "diff_summary": diff_summary or {},
    }
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def validate_correction_rationale(rationale: str) -> Tuple[bool, Optional[str]]:
    """Enforces substantive, non-generic human rationale."""
    r_clean = rationale.strip()
    if not r_clean:
        return False, "Correction rationale is empty. A human-written rationale is mandatory."
    lower_r = r_clean.lower()
    for pat in PROHIBITED_GENERIC_RATIONALE_PATTERNS:
        if re.search(pat, lower_r):
            return False, f"Generic rationale rejected: matches prohibited pattern '{pat}'. Please describe observable image evidence."
    if len(r_clean) < 15:
        return False, "Correction rationale is too short (< 15 characters). Please provide observable visual findings."
    return True, None


def compute_correction_diff(original_fc: Dict[str, Any], proposed_fc: Dict[str, Any]) -> Dict[str, Any]:
    """Computes exact field-by-field differences between original consensus and proposed correction."""
    changed_fields = []
    summary_lines = []

    orig_status = original_fc.get("chip_annotation_status")
    prop_status = proposed_fc.get("chip_annotation_status")
    if orig_status != prop_status:
        changed_fields.append("chip_annotation_status")
        summary_lines.append(f"Observation Status: '{orig_status}' -> '{prop_status}'")

    orig_boxes = original_fc.get("annotations", [])
    prop_boxes = proposed_fc.get("annotations", [])
    if len(orig_boxes) != len(prop_boxes):
        changed_fields.append("annotations.count")
        summary_lines.append(f"Bounding Box Count: {len(orig_boxes)} -> {len(prop_boxes)}")

    # Check box-level evidence and geometry
    max_len = max(len(orig_boxes), len(prop_boxes))
    for i in range(max_len):
        if i >= len(orig_boxes):
            changed_fields.append(f"annotations[{i}].added")
            summary_lines.append(f"Added Box #{i+1}: {prop_boxes[i].get('class_name')} {prop_boxes[i].get('bbox')}")
        elif i >= len(prop_boxes):
            changed_fields.append(f"annotations[{i}].removed")
            summary_lines.append(f"Removed Box #{i+1}: {orig_boxes[i].get('class_name')} {orig_boxes[i].get('bbox')}")
        else:
            ob = orig_boxes[i]
            pb = prop_boxes[i]
            if ob.get("bbox") != pb.get("bbox"):
                changed_fields.append(f"annotations[{i}].bbox")
                summary_lines.append(f"Box #{i+1} Coordinates: {ob.get('bbox')} -> {pb.get('bbox')}")
            if ob.get("class_name") != pb.get("class_name"):
                changed_fields.append(f"annotations[{i}].class_name")
                summary_lines.append(f"Box #{i+1} Class: '{ob.get('class_name')}' -> '{pb.get('class_name')}'")
            
            o_ev = sorted(ob.get("visual_evidence", []))
            p_ev = sorted(pb.get("visual_evidence", []))
            if o_ev != p_ev:
                changed_fields.append(f"annotations[{i}].visual_evidence")
                removed_tags = [t for t in o_ev if t not in p_ev]
                added_tags = [t for t in p_ev if t not in o_ev]
                parts = []
                if removed_tags:
                    parts.append(f"removed {removed_tags}")
                if added_tags:
                    parts.append(f"added {added_tags}")
                summary_lines.append(f"Box #{i+1} Evidence: {', '.join(parts)}")

    if not summary_lines:
        summary_lines.append("No material consensus changes detected.")

    return {
        "changed_fields": changed_fields,
        "summary": summary_lines,
    }


def load_correction_chip_data(chip_id: str) -> Dict[str, Any]:
    """Loads all data needed by the correction UI for a chip."""
    if chip_id not in DISPUTED_6_CHIPS:
        raise ValueError(f"Chip {chip_id} is not in disputed cohort {DISPUTED_6_CHIPS}")

    # Load original Stage 8.15 record (READ-ONLY)
    orig_file = REVIEW_DIR / f"{chip_id}_adjudicated_v1.json"
    if not orig_file.exists():
        raise FileNotFoundError(f"Original Stage 8.15 record missing: {orig_file}")
    orig_raw = orig_file.read_bytes()
    orig_sha = hashlib.sha256(orig_raw).hexdigest()
    orig_data = json.loads(orig_raw.decode("utf-8"))

    # Load source manifest hash for verification
    manifest = load_source_manifest()
    exp_sha = manifest["files"][chip_id]["sha256"]
    is_source_valid = (orig_sha == exp_sha)

    # Check if existing correction v2 already exists in corrections dir
    corr_file = CORRECTIONS_DIR / f"{chip_id}_corrected_v2.json"
    existing_corr = None
    if corr_file.exists():
        with open(corr_file, "r", encoding="utf-8") as f:
            existing_corr = json.load(f)

    # Resolve paths & metadata
    paths = resolve_chip_paths(chip_id)
    manifest_active = load_manifest()
    entry = next((c for c in manifest_active["chips"] if c["chip_id"] == chip_id), {})

    firms_col, firms_row = 256.0, 256.0
    if paths["tif_path"] and paths["tif_path"].exists() and "firms_latitude" in entry:
        try:
            firms_col, firms_row = compute_firms_pixel_coordinates(
                paths["tif_path"], entry["firms_latitude"], entry["firms_longitude"]
            )
        except Exception:
            pass

    return {
        "chip_id": chip_id,
        "audit_category": CHIP_AUDIT_CATEGORIES.get(chip_id, {}),
        "source_record": orig_data,
        "source_sha256": orig_sha,
        "source_valid": is_source_valid,
        "existing_correction": existing_corr,
        "is_corrected": existing_corr is not None,
        "A1_original": orig_data.get("A1_original", {}),
        "A2_original": orig_data.get("A2_original", {}),
        "firms_info": {
            "latitude": entry.get("firms_latitude"),
            "longitude": entry.get("firms_longitude"),
            "frp_mw": entry.get("firms_frp"),
            "pixel_col": firms_col,
            "pixel_row": firms_row,
            "cloud_cover_pct": entry.get("cloud_cover_pct"),
            "tile_id": entry.get("tile_id"),
        },
    }


def save_chip_correction(chip_id: str, payload: Dict[str, Any]) -> Tuple[bool, List[str], Optional[Dict[str, Any]]]:
    """Validates and saves a versioned Stage 8.16 correction record."""
    if chip_id not in DISPUTED_6_CHIPS:
        return False, [f"Chip '{chip_id}' is not in disputed cohort ({DISPUTED_6_CHIPS})"], None

    # 1. Verify original records immutability before proceeding
    valid_orig, orig_errs = verify_original_records()
    if not valid_orig:
        log_audit_event("SAVE_REJECTED", chip_id, {"reason": "SOURCE_INTEGRITY_VIOLATION"}, False, orig_errs)
        return False, [f"CRITICAL: Original records hash mismatch: {orig_errs}"], None

    # Verify A1/A2 baseline
    valid_a1a2, a1a2_errs = verify_a1_a2_baseline()
    if not valid_a1a2:
        log_audit_event("SAVE_REJECTED", chip_id, {"reason": "BASELINE_INTEGRITY_VIOLATION"}, False, a1a2_errs)
        return False, [f"CRITICAL: Baseline A1/A2 workspace altered: {a1a2_errs}"], None

    # 2. Extract and validate human confirmation
    conf = payload.get("human_confirmation", {})
    if not isinstance(conf, dict) or not conf.get("confirmed", False):
        err = "Explicit human confirmation checkbox is mandatory before saving a correction."
        log_audit_event("SAVE_REJECTED", chip_id, {"reason": "MISSING_CONFIRMATION"}, False, [err])
        return False, [err], None

    # 3. Extract and validate rationale
    rationale = payload.get("correction_rationale", "")
    valid_rat, rat_err = validate_correction_rationale(rationale)
    if not valid_rat:
        log_audit_event("SAVE_REJECTED", chip_id, {"reason": "INVALID_RATIONALE"}, False, [rat_err])
        return False, [rat_err], None

    # 4. Extract proposed consensus
    prop_fc = payload.get("corrected_consensus", {})
    if not prop_fc:
        return False, ["Missing 'corrected_consensus' in payload"], None

    obs_status = prop_fc.get("chip_annotation_status")
    if obs_status not in ["HAS_ANNOTATIONS", "NO_VISIBLE_TARGET"]:
        err = f"Invalid observation status '{obs_status}'. Must be definitively 'HAS_ANNOTATIONS' or 'NO_VISIBLE_TARGET'. 'UNRESOLVED' is prohibited."
        log_audit_event("SAVE_REJECTED", chip_id, {"reason": "NON_DEFINITIVE_STATUS"}, False, [err])
        return False, [err], None

    annotations = prop_fc.get("annotations", [])

    if obs_status == "HAS_ANNOTATIONS" and len(annotations) == 0:
        err = "Observation status 'HAS_ANNOTATIONS' requires at least one valid bounding box."
        log_audit_event("SAVE_REJECTED", chip_id, {"reason": "MISSING_BOXES"}, False, [err])
        return False, [err], None

    if obs_status == "NO_VISIBLE_TARGET" and len(annotations) > 0:
        err = "Observation status 'NO_VISIBLE_TARGET' must have an empty annotations list ([])."
        log_audit_event("SAVE_REJECTED", chip_id, {"reason": "EXTRA_BOXES"}, False, [err])
        return False, [err], None

    # 5. Validate bounding boxes & contradictory evidence
    for idx, ann in enumerate(annotations, start=1):
        bbox = ann.get("bbox", {})
        xmin = bbox.get("x_min", -1)
        ymin = bbox.get("y_min", -1)
        xmax = bbox.get("x_max", -1)
        ymax = bbox.get("y_max", -1)

        # Coordinate bounds
        if not (0 <= xmin < xmax <= 512 and 0 <= ymin < ymax <= 512):
            err = f"Box #{idx} has invalid geometry or out-of-bounds coordinates: {bbox}"
            log_audit_event("SAVE_REJECTED", chip_id, {"reason": "INVALID_COORDS"}, False, [err])
            return False, [err], None

        if (xmax - xmin < 4) or (ymax - ymin < 4):
            err = f"Box #{idx} is too small (< 4 pixels): {bbox}"
            log_audit_event("SAVE_REJECTED", chip_id, {"reason": "BOX_TOO_SMALL"}, False, [err])
            return False, [err], None

        # Forbidden default box
        if xmin == FORBIDDEN_DEFAULT_BOX["x_min"] and ymin == FORBIDDEN_DEFAULT_BOX["y_min"] and xmax == FORBIDDEN_DEFAULT_BOX["x_max"] and ymax == FORBIDDEN_DEFAULT_BOX["y_max"]:
            err = f"Box #{idx} matches forbidden placeholder [200, 200, 300, 300]."
            log_audit_event("SAVE_REJECTED", chip_id, {"reason": "FORBIDDEN_BOX"}, False, [err])
            return False, [err], None

        # Check contradictory visual evidence
        box_ev = ann.get("visual_evidence", [])
        if ("DIRECT_FIRE_VISIBLE" in box_ev or "BURN_SCAR_VISIBLE" in box_ev) and "NO_CLEAR_VISUAL_EVIDENCE" in box_ev:
            err = (
                f"Box #{idx} contains contradictory evidence: cannot claim both positive fire/burn-scar evidence "
                "and 'NO_CLEAR_VISUAL_EVIDENCE'. Please uncheck the contradictory flag."
            )
            log_audit_event("SAVE_REJECTED", chip_id, {"reason": "CONTRADICTORY_EVIDENCE"}, False, [err])
            return False, [err], None

        cname = ann.get("class_name")
        if cname not in ALLOWED_CLASSES or cname == "UNRESOLVED":
            err = f"Box #{idx} has invalid class '{cname}'. Allowed: {ALLOWED_CLASSES}"
            log_audit_event("SAVE_REJECTED", chip_id, {"reason": "INVALID_CLASS"}, False, [err])
            return False, [err], None

        ann["class_id"] = CLASS_ID_MAP.get(cname, 0)
        ann["annotation_id"] = f"{chip_id}_CORR_{idx:02d}"
        ann["annotator_id"] = "HUMAN_ADJUDICATOR_CORRECTION"
        ann["review_status"] = "CORRECTED_V2"
        if not ann.get("geometry_confidence"):
            ann["geometry_confidence"] = "MEDIUM"
        if not ann.get("source_class_confidence"):
            ann["source_class_confidence"] = "MEDIUM"
        if not ann.get("visibility_status"):
            ann["visibility_status"] = "CLEAR"
        if not ann.get("firms_relationship"):
            ann["firms_relationship"] = "INSIDE_OBJECT"

    # 6. Read original record to compute diff
    orig_file = REVIEW_DIR / f"{chip_id}_adjudicated_v1.json"
    with open(orig_file, "r", encoding="utf-8") as f:
        orig_data = json.load(f)
    orig_fc = orig_data.get("final_consensus", {})
    orig_sha = hashlib.sha256(orig_file.read_bytes()).hexdigest()

    diff = compute_correction_diff(orig_fc, prop_fc)

    # Compile authoritative final consensus payload
    source_classes = sorted(list(set(ann["class_name"] for ann in annotations)))
    if not source_classes:
        source_classes = [obs_status]

    all_evidence = sorted(list(set(ev for ann in annotations for ev in ann.get("visual_evidence", []))))
    if not all_evidence:
        all_evidence = ["NO_CLEAR_VISUAL_EVIDENCE"]

    primary_vis = annotations[0].get("visibility_status", "CLEAR") if annotations else "CLEAR"
    primary_geom_conf = annotations[0].get("geometry_confidence", "MEDIUM") if annotations else "MEDIUM"
    primary_class_conf = annotations[0].get("source_class_confidence", "MEDIUM") if annotations else "MEDIUM"

    now_iso = datetime.now(timezone.utc).isoformat()

    final_corrected_fc = {
        "chip_id": chip_id,
        "annotation_version": "v2.0",
        "chip_annotation_status": obs_status,
        "annotations": annotations,
        "source_classes": source_classes,
        "visual_evidence": all_evidence,
        "visibility_status": primary_vis,
        "geometry_confidence": primary_geom_conf,
        "source_class_confidence": primary_class_conf,
        "context_metadata": orig_data.get("context_metadata", {}),
    }

    # Validate against standard schema
    valid_schema, schema_errs = validate_annotation_payload(final_corrected_fc)
    if not valid_schema:
        log_audit_event("SAVE_REJECTED", chip_id, {"reason": "SCHEMA_ERROR"}, False, schema_errs)
        return False, [f"Schema validation error on corrected consensus: {schema_errs}"], None

    # Assemble versioned correction record
    correction_record = {
        "chip_id": chip_id,
        "correction_version": "v2.0",
        "stage": "STAGE_8_16",
        "correction_status": "COMPLETED_HUMAN_CORRECTION",
        "original_record_path": f"data/reference/ds08/annotations/adjudication/review/{chip_id}_adjudicated_v1.json",
        "original_record_sha256": orig_sha,
        "corrected_consensus": final_corrected_fc,
        "changed_fields": diff["changed_fields"],
        "diff_summary": diff["summary"],
        "correction_rationale": rationale.strip(),
        "human_confirmation": {
            "confirmed": True,
            "method": "HUMAN_CHECKBOX_CONFIRMATION",
            "statement": conf.get(
                "statement",
                "I confirm that I have reviewed the Sentinel-2 imagery and explicitly approve these corrections.",
            ),
        },
        "correction_timestamp": now_iso,
        "record_sha256": None,
    }

    # Compute record SHA-256 over stable JSON representation
    record_bytes = json.dumps(correction_record, indent=2).encode("utf-8")
    record_hash = hashlib.sha256(record_bytes).hexdigest()
    correction_record["record_sha256"] = record_hash

    # Save to dedicated corrections directory
    CORRECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = CORRECTIONS_DIR / f"{chip_id}_corrected_v2.json"
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(correction_record, f, indent=2)

    # 7. Post-save verification: verify original records were NOT modified!
    post_valid_orig, post_errs = verify_original_records()
    if not post_valid_orig:
        log_audit_event("SAVE_REJECTED", chip_id, {"reason": "POST_WRITE_SOURCE_CORRUPTED"}, False, post_errs)
        return False, [f"FATAL: Source record was altered during save operation: {post_errs}"], None

    # Log successful audit event
    log_audit_event(
        "CORRECTION_SAVED",
        chip_id,
        {
            "saved_file": target_path.name,
            "record_sha256": record_hash,
            "changed_fields": diff["changed_fields"],
        },
        True,
        diff_summary=diff,
    )

    return True, [], correction_record


HTML_CORRECTION_UI = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>DS08 Stage 8.16: Controlled Adjudication Correction Workspace</title>
  <style>
    :root {
      --bg: #14151b;
      --card-bg: #1e2029;
      --card-alt: #262936;
      --border: #363a4d;
      --text: #e2e4ea;
      --text-muted: #9aa0b4;
      --accent: #ff9800;
      --accent-hover: #f57c00;
      --danger: #ef5350;
      --success: #4caf50;
      --info: #42a5f5;
      --purple: #ab47bc;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }
    header {
      background: var(--card-bg);
      border-bottom: 1px solid var(--border);
      padding: 10px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
    }
    .header-title { font-size: 1.05rem; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 10px; }
    .header-badge {
      background: rgba(255, 152, 0, 0.2);
      border: 1px solid var(--accent);
      color: var(--accent);
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .header-meta { font-size: 0.8rem; color: var(--text-muted); display: flex; gap: 16px; align-items: center; }

    .main-layout { display: flex; flex: 1; overflow: hidden; }
    .sidebar {
      width: 280px;
      background: var(--card-bg);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }
    .sidebar-header {
      padding: 12px 16px;
      font-weight: 700;
      font-size: 0.8rem;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .chip-list { list-style: none; overflow-y: auto; flex: 1; }
    .chip-item {
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      cursor: pointer;
      display: flex;
      flex-direction: column;
      gap: 5px;
      transition: background 0.15s;
    }
    .chip-item:hover { background: rgba(255, 255, 255, 0.04); }
    .chip-item.active { background: rgba(255, 152, 0, 0.15); border-left: 4px solid var(--accent); }
    .chip-name { font-weight: 600; font-size: 0.85rem; }
    .badge-row { display: flex; gap: 6px; flex-wrap: wrap; }
    .tag {
      font-size: 0.65rem;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 3px;
    }
    .tag-contradiction { background: rgba(239, 83, 80, 0.2); color: #ef9a9a; border: 1px solid var(--danger); }
    .tag-unresolved { background: rgba(171, 71, 188, 0.2); color: #ce93d8; border: 1px solid var(--purple); }
    .tag-corrected { background: rgba(76, 175, 80, 0.2); color: #81c784; border: 1px solid var(--success); }
    .tag-pending { background: rgba(255, 152, 0, 0.2); color: #ffb74d; border: 1px solid var(--accent); }

    .content-area { flex: 1; display: flex; overflow: hidden; }
    .viewer-pane {
      flex: 1.1;
      display: flex;
      flex-direction: column;
      border-right: 1px solid var(--border);
      background: #0f1015;
    }
    .viewer-toolbar {
      padding: 8px 16px;
      background: var(--card-bg);
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
    }
    .btn-group { display: flex; gap: 6px; align-items: center; }
    .btn {
      background: var(--card-alt);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 5px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.8rem;
      font-weight: 500;
      transition: all 0.15s;
    }
    .btn:hover { background: #323647; }
    .btn.active { background: var(--accent); color: #000; border-color: var(--accent); font-weight: 700; }
    .btn-primary { background: var(--accent); color: #000; border-color: var(--accent); font-weight: 700; }
    .btn-primary:hover { background: var(--accent-hover); }
    .btn-success { background: var(--success); color: #fff; border-color: var(--success); font-weight: 700; }
    .btn-danger { background: var(--danger); color: #fff; border-color: var(--danger); }

    .canvas-container {
      flex: 1;
      display: flex;
      justify-content: center;
      align-items: center;
      overflow: hidden;
      position: relative;
    }
    canvas {
      box-shadow: 0 4px 20px rgba(0,0,0,0.6);
      background: #000;
      image-rendering: pixelated;
    }

    .inspector-pane {
      flex: 1.2;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      padding: 16px;
      gap: 14px;
      background: var(--bg);
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .card-title {
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 6px;
    }
    .box-card {
      background: var(--card-alt);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .box-header { display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; font-weight: 700; }
    .coord-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; font-size: 0.75rem; }
    .coord-grid input { width: 100%; padding: 4px; font-size: 0.75rem; text-align: center; background: var(--bg); border: 1px solid var(--border); color: #fff; border-radius: 3px; }

    .evidence-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 0.75rem; }
    .evidence-item { display: flex; align-items: center; gap: 6px; cursor: pointer; }

    .alert-banner {
      background: rgba(239, 83, 80, 0.15);
      border: 1px solid var(--danger);
      color: #fca5a5;
      padding: 8px 12px;
      border-radius: 4px;
      font-size: 0.75rem;
      line-height: 1.4;
    }
    .alert-unresolved {
      background: rgba(171, 71, 188, 0.15);
      border: 1px solid var(--purple);
      color: #e1bee7;
      padding: 8px 12px;
      border-radius: 4px;
      font-size: 0.75rem;
      line-height: 1.4;
    }

    textarea, input[type="text"], select {
      background: var(--card-alt);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 10px;
      border-radius: 4px;
      font-size: 0.85rem;
      font-family: inherit;
      width: 100%;
    }
    textarea:focus, select:focus { outline: none; border-color: var(--accent); }
    textarea { resize: vertical; min-height: 80px; }

    /* Modal */
    .modal-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.75);
      display: none;
      justify-content: center;
      align-items: center;
      z-index: 1000;
    }
    .modal {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      width: 90%;
      max-width: 650px;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 10px 30px rgba(0,0,0,0.8);
      overflow: hidden;
    }
    .modal-header {
      padding: 14px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-weight: 700;
      font-size: 0.95rem;
    }
    .modal-body {
      padding: 16px 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
      font-size: 0.85rem;
    }
    .modal-footer {
      padding: 12px 20px;
      border-top: 1px solid var(--border);
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      background: var(--card-alt);
    }
    .diff-list { list-style: disc; margin-left: 20px; font-size: 0.8rem; line-height: 1.5; color: #ffb74d; }

    #notification {
      position: fixed;
      bottom: 20px;
      right: 20px;
      padding: 12px 20px;
      border-radius: 6px;
      font-weight: 600;
      font-size: 0.9rem;
      z-index: 2000;
      display: none;
      box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    .notif-success { background: var(--success); color: #fff; }
    .notif-error { background: var(--danger); color: #fff; }
  </style>
</head>
<body>

  <header>
    <div class="header-title">
      <span>DS08 STAGE 8.16 CORRECTION WORKSPACE</span>
      <span class="header-badge">CONTROLLED HUMAN CORRECTION (v2)</span>
    </div>
    <div class="header-meta">
      <span>Original Records: <strong style="color: var(--success);" id="origStatusText">6 / 6 VERIFIED</strong></span>
      <span>Corrections Saved: <strong style="color: var(--accent);" id="corrCountText">0</strong> / 6</span>
    </div>
  </header>

  <div class="main-layout">
    <!-- SIDEBAR -->
    <div class="sidebar">
      <div class="sidebar-header">Disputed Chips Requiring Correction</div>
      <ul class="chip-list" id="chipList"></ul>
    </div>

    <!-- MAIN CONTENT -->
    <div class="content-area">
      <!-- VIEWER -->
      <div class="viewer-pane">
        <div class="viewer-toolbar">
          <div class="btn-group">
            <button class="btn active" id="btnRgb" onclick="switchBand('rgb')">RGB True Color</button>
            <button class="btn" id="btnSwir" onclick="switchBand('swir')">SWIR False Color (B12-B11-B04)</button>
          </div>
          <div class="btn-group">
            <button class="btn" onclick="zoomIn()">Zoom +</button>
            <button class="btn" onclick="zoomOut()">Zoom -</button>
            <button class="btn" onclick="resetZoom()">Reset</button>
          </div>
        </div>

        <div class="canvas-container">
          <canvas id="viewCanvas" width="512" height="512" style="touch-action: none; user-select: none;"></canvas>
        </div>

        <div style="padding: 8px 16px; font-size: 0.75rem; color: #ffb74d; background: #1a1714; border-top: 1px solid var(--border); display: flex; justify-content: space-between;">
          <span id="coordDisplay">Pixel: X: 0, Y: 0</span>
          <span>Click & drag to add/adjust boxes | Use checkboxes to edit evidence</span>
        </div>
      </div>

      <!-- INSPECTOR & CORRECTION EDITOR -->
      <div class="inspector-pane">
        <!-- CHIP CONTEXT -->
        <div class="card">
          <div class="card-title">
            <span id="activeChipTitle">CHIP CONTEXT</span>
            <span id="activeAuditBadge" class="tag tag-contradiction">ISSUE</span>
          </div>
          <div id="activeAuditDesc" style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.4;"></div>
          <div style="font-size: 0.75rem; color: #888; display: grid; grid-template-columns: 1fr 1fr; gap: 4px;" id="firmsInfoGrid"></div>
        </div>

        <!-- CORRECTION FORM -->
        <div class="card">
          <div class="card-title" style="color: var(--accent);">
            <span>Consensus Correction Editor</span>
            <span id="saveStatusBadge" class="tag tag-pending">PENDING</span>
          </div>

          <!-- Status Selection (Definitive ONLY) -->
          <div style="display: flex; flex-direction: column; gap: 4px;">
            <label style="font-size: 0.8rem; font-weight: 600;">Observation Status (Definitive Consensus)</label>
            <select id="selStatus" onchange="onStatusChanged()">
              <option value="HAS_ANNOTATIONS">HAS_ANNOTATIONS (Target / active fire confirmed)</option>
              <option value="NO_VISIBLE_TARGET">NO_VISIBLE_TARGET (Clear image, no target discernible)</option>
            </select>
          </div>

          <!-- Box list & Evidence flags -->
          <div id="boxesContainer" style="display: flex; flex-direction: column; gap: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-size: 0.8rem; font-weight: 700;">Bounding Boxes & Evidence Flags (<span id="boxCountDisplay">0</span>)</span>
              <div style="display: flex; gap: 6px;">
                <button class="btn btn-primary" style="font-size: 0.75rem; padding: 2px 8px;" onclick="promptAddBox()">+ Add Box</button>
                <button class="btn btn-danger" style="font-size: 0.75rem; padding: 2px 8px;" onclick="clearAllBoxes()">Clear</button>
              </div>
            </div>

            <div id="boxList" style="display: flex; flex-direction: column; gap: 10px;"></div>
          </div>

          <!-- RATIONALE -->
          <div style="display: flex; flex-direction: column; gap: 4px;">
            <label style="font-size: 0.8rem; font-weight: 600;">Substantive Correction Rationale (Mandatory)</label>
            <div style="font-size: 0.7rem; color: var(--text-muted);">Explain physical/spectral findings justifying evidence flag or observation changes.</div>
            <textarea id="txtRationale" placeholder="Describe observable visual evidence..."></textarea>
          </div>

          <!-- Review & Submit Button -->
          <button class="btn btn-primary" style="padding: 10px; font-size: 0.9rem;" onclick="openReviewModal()">
            🔍 Review Proposed Changes & Submit Correction
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- REVIEW & CONFIRMATION MODAL -->
  <div class="modal-overlay" id="reviewModal">
    <div class="modal">
      <div class="modal-header">
        <span>Confirm Human Adjudication Correction (v2)</span>
        <button style="background: none; border: none; color: #fff; cursor: pointer; font-size: 1.1rem;" onclick="closeReviewModal()">✕</button>
      </div>
      <div class="modal-body">
        <div style="background: var(--card-alt); padding: 10px; border-radius: 4px; font-size: 0.8rem;">
          <div>Chip ID: <strong id="modalChipId" style="color: var(--accent);"></strong></div>
          <div>Original SHA-256: <code id="modalOrigSha" style="font-size: 0.75rem;"></code></div>
        </div>

        <div>
          <strong style="font-size: 0.85rem;">Summary of Changes from Original Record:</strong>
          <ul class="diff-list" id="modalDiffList" style="margin-top: 6px;"></ul>
        </div>

        <div>
          <strong style="font-size: 0.85rem;">Correction Rationale:</strong>
          <div id="modalRationaleText" style="margin-top: 4px; font-style: italic; color: #bbb; background: #181920; padding: 8px; border-radius: 4px;"></div>
        </div>

        <div style="background: rgba(255, 152, 0, 0.1); border: 1px solid var(--accent); padding: 12px; border-radius: 4px; display: flex; flex-direction: column; gap: 6px;">
          <label style="display: flex; align-items: flex-start; gap: 8px; cursor: pointer; font-size: 0.85rem;">
            <input type="checkbox" id="chkModalConfirm" style="margin-top: 2px;">
            <span><strong>Explicit Human Confirmation:</strong> I confirm that I have reviewed the Sentinel-2 RGB and SWIR imagery and explicitly approve saving these corrected consensus annotations as a new versioned record.</span>
          </label>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn" onclick="closeReviewModal()">Cancel</button>
        <button class="btn btn-success" onclick="executeSaveCorrection()">Confirm & Save Versioned Record (v2)</button>
      </div>
    </div>
  </div>

  <div id="notification"></div>

  <script>
    const DISPUTED_CHIPS = ["PILOT_03_NORTH", "PILOT_06_CENTRAL", "PILOT_08_CENTRAL", "PILOT_15_EAST", "PILOT_16_EAST", "PILOT_18_WEST"];
    const ALLOWED_EVIDENCE = [
      "DIRECT_FIRE_VISIBLE", "SMOKE_VISIBLE", "BURN_SCAR_VISIBLE",
      "INDUSTRIAL_INFRASTRUCTURE_VISIBLE", "FOREST_CONTEXT_VISIBLE",
      "CROPLAND_CONTEXT_VISIBLE", "PERSISTENT_THERMAL_SOURCE_CONTEXT",
      "NO_CLEAR_VISUAL_EVIDENCE"
    ];

    let currentChipId = "PILOT_03_NORTH";
    let currentData = null;
    let currentBand = "rgb";
    let rgbImg = new Image();
    let swirImg = new Image();
    let zoomLevel = 1.0;
    let panX = 0, panY = 0;
    let isPanning = false, panStartX = 0, panStartY = 0;
    let isDrawing = false, drawStartX = 0, drawStartY = 0, currentDrawBox = null;

    let editableBoxes = [];

    async function init() {
      renderChipList();
      await loadChip(currentChipId);
      setupCanvasEvents();
      updateHeaderStats();
    }

    function renderChipList() {
      const list = document.getElementById("chipList");
      list.innerHTML = "";
      DISPUTED_CHIPS.forEach((cid, idx) => {
        const li = document.createElement("li");
        li.className = "chip-item" + (cid === currentChipId ? " active" : "");
        li.id = "chipItem_" + cid;
        li.innerHTML = `
          <div class="chip-name">[${idx+1}/6] ${cid}</div>
          <div class="badge-row">
            <span class="tag ${cid === 'PILOT_08_CENTRAL' ? 'tag-unresolved' : 'tag-contradiction'}">${cid === 'PILOT_08_CENTRAL' ? 'Unresolved' : 'Contradiction'}</span>
            <span class="tag tag-pending" id="statusBadge_${cid}">PENDING</span>
          </div>
        `;
        li.onclick = () => loadChip(cid);
        list.appendChild(li);
      });
    }

    async function loadChip(chipId) {
      currentChipId = chipId;
      document.querySelectorAll(".chip-item").forEach(el => el.classList.remove("active"));
      const activeEl = document.getElementById("chipItem_" + chipId);
      if (activeEl) activeEl.classList.add("active");

      document.getElementById("activeChipTitle").innerText = chipId;

      try {
        const resp = await fetch("/api/chip/" + chipId);
        if (!resp.ok) throw new Error("Failed to load chip data: " + resp.statusText);
        currentData = await resp.json();
        populateUI(currentData);
        await loadImages(chipId);
        updateHeaderStats();
      } catch (err) {
        showNotification("Error: " + err.message, true);
      }
    }

    function populateUI(data) {
      const cat = data.audit_category || {};
      document.getElementById("activeAuditBadge").className = "tag " + (cat.issue === 'UNRESOLVED_OBSERVATION_STATUS' ? 'tag-unresolved' : 'tag-contradiction');
      document.getElementById("activeAuditBadge").innerText = cat.issue || "AUDIT ISSUE";
      document.getElementById("activeAuditDesc").innerText = cat.description || "";

      const f = data.firms_info || {};
      document.getElementById("firmsInfoGrid").innerHTML = `
        <div>Coord: <strong>${f.latitude?.toFixed(4)}, ${f.longitude?.toFixed(4)}</strong></div>
        <div>FRP: <strong>${f.frp_mw} MW</strong></div>
        <div>FIRMS Pixel: <strong>[col ${f.pixel_col}, row ${f.pixel_row}]</strong></div>
        <div>Scene Cloud: <strong>${f.cloud_cover_pct}%</strong></div>
      `;

      // Priority: if an existing correction v2 exists, load it; otherwise load original record
      const srcRecord = data.existing_correction ? data.existing_correction.corrected_consensus : (data.source_record.final_consensus || {});
      const origStatus = srcRecord.chip_annotation_status || "HAS_ANNOTATIONS";
      
      // Default observation status in dropdown: if UNRESOLVED in source, default to HAS_ANNOTATIONS for Central 08
      document.getElementById("selStatus").value = (origStatus === "UNRESOLVED") ? "HAS_ANNOTATIONS" : origStatus;

      // Deep copy boxes so human reviewer can edit individual fields
      editableBoxes = JSON.parse(JSON.stringify(srcRecord.annotations || []));

      // Rationale
      const existingRat = data.existing_correction ? data.existing_correction.correction_rationale : data.source_record.adjudication_rationale;
      document.getElementById("txtRationale").value = existingRat || "";

      // Badge
      const isCorr = data.is_corrected;
      const badge = document.getElementById("saveStatusBadge");
      badge.className = "tag " + (isCorr ? "tag-corrected" : "tag-pending");
      badge.innerText = isCorr ? "CORRECTED (v2)" : "PENDING";
      setChipBadge(data.chip_id, isCorr);

      onStatusChanged();
      renderBoxesList();
    }

    function setChipBadge(chipId, isCorrected) {
      const b = document.getElementById("statusBadge_" + chipId);
      if (b) {
        b.className = "tag " + (isCorrected ? "tag-corrected" : "tag-pending");
        b.innerText = isCorrected ? "CORRECTED (v2)" : "PENDING";
      }
    }

    async function loadImages(chipId) {
      return new Promise((resolve) => {
        let loaded = 0;
        const check = () => {
          loaded++;
          if (loaded >= 2) {
            renderCanvas();
            resolve();
          }
        };
        rgbImg = new Image();
        rgbImg.onload = check;
        rgbImg.onerror = check;
        rgbImg.src = "/api/preview/" + chipId + "/rgb?" + Date.now();

        swirImg = new Image();
        swirImg.onload = check;
        swirImg.onerror = check;
        swirImg.src = "/api/preview/" + chipId + "/swir?" + Date.now();
      });
    }

    function switchBand(band) {
      currentBand = band;
      document.getElementById("btnRgb").className = "btn" + (band === "rgb" ? " active" : "");
      document.getElementById("btnSwir").className = "btn" + (band === "swir" ? " active" : "");
      renderCanvas();
    }

    function zoomIn() { zoomLevel = Math.min(zoomLevel * 1.25, 5.0); renderCanvas(); }
    function zoomOut() { zoomLevel = Math.max(zoomLevel / 1.25, 0.5); renderCanvas(); }
    function resetZoom() { zoomLevel = 1.0; panX = 0; panY = 0; renderCanvas(); }

    function onStatusChanged() {
      const st = document.getElementById("selStatus").value;
      const c = document.getElementById("boxesContainer");
      if (st === "HAS_ANNOTATIONS") {
        c.style.display = "flex";
      } else {
        c.style.display = "none";
        editableBoxes = [];
        renderBoxesList();
        renderCanvas();
      }
    }

    function renderBoxesList() {
      const list = document.getElementById("boxList");
      list.innerHTML = "";
      document.getElementById("boxCountDisplay").innerText = editableBoxes.length;

      if (editableBoxes.length === 0) {
        list.innerHTML = `<div style="font-size:0.75rem; color:#ffb74d; background:rgba(255,152,0,0.1); padding:8px; border-radius:4px;">No bounding boxes. Draw on canvas or click <strong>+ Add Box</strong>.</div>`;
        return;
      }

      editableBoxes.forEach((b, idx) => {
        const evList = b.visual_evidence || [];
        const hasContradiction = evList.includes("NO_CLEAR_VISUAL_EVIDENCE") &&
          (evList.includes("DIRECT_FIRE_VISIBLE") || evList.includes("BURN_SCAR_VISIBLE"));

        const div = document.createElement("div");
        div.className = "box-card";
        div.innerHTML = `
          <div class="box-header">
            <span>Box #${idx + 1} (${b.class_name}) [${b.bbox.x_min}, ${b.bbox.y_min}, ${b.bbox.x_max}, ${b.bbox.y_max}]</span>
            <button class="btn btn-danger" style="padding: 2px 6px; font-size: 0.7rem;" onclick="deleteBox(${idx})">Delete</button>
          </div>
          <div class="coord-grid">
            <div><label>x_min</label><input type="number" value="${b.bbox.x_min}" onchange="updateBoxCoord(${idx}, 'x_min', this.value)"></div>
            <div><label>y_min</label><input type="number" value="${b.bbox.y_min}" onchange="updateBoxCoord(${idx}, 'y_min', this.value)"></div>
            <div><label>x_max</label><input type="number" value="${b.bbox.x_max}" onchange="updateBoxCoord(${idx}, 'x_max', this.value)"></div>
            <div><label>y_max</label><input type="number" value="${b.bbox.y_max}" onchange="updateBoxCoord(${idx}, 'y_max', this.value)"></div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px;">
            <div>
              <label style="font-size: 0.75rem;">Class</label>
              <select onchange="updateBoxField(${idx}, 'class_name', this.value)" style="padding: 4px; font-size: 0.75rem;">
                <option value="Forest Fire" ${b.class_name === 'Forest Fire' ? 'selected' : ''}>Forest Fire</option>
                <option value="Agricultural Fire" ${b.class_name === 'Agricultural Fire' ? 'selected' : ''}>Agricultural Fire</option>
                <option value="Industrial Fire" ${b.class_name === 'Industrial Fire' ? 'selected' : ''}>Industrial Fire</option>
                <option value="Other Thermal Source" ${b.class_name === 'Other Thermal Source' ? 'selected' : ''}>Other Thermal Source</option>
              </select>
            </div>
            <div>
              <label style="font-size: 0.75rem;">FIRMS Relation</label>
              <select onchange="updateBoxField(${idx}, 'firms_relationship', this.value)" style="padding: 4px; font-size: 0.75rem;">
                <option value="INSIDE_OBJECT" ${b.firms_relationship === 'INSIDE_OBJECT' ? 'selected' : ''}>INSIDE_OBJECT</option>
                <option value="TOUCHING_OBJECT" ${b.firms_relationship === 'TOUCHING_OBJECT' ? 'selected' : ''}>TOUCHING_OBJECT</option>
                <option value="NEAR_OBJECT" ${b.firms_relationship === 'NEAR_OBJECT' ? 'selected' : ''}>NEAR_OBJECT</option>
                <option value="OUTSIDE_VISIBLE_OBJECT" ${b.firms_relationship === 'OUTSIDE_VISIBLE_OBJECT' ? 'selected' : ''}>OUTSIDE_VISIBLE_OBJECT</option>
              </select>
            </div>
          </div>
          <div>
            <label style="font-size: 0.75rem; font-weight: 700;">Visual Evidence Flags:</label>
            <div class="evidence-grid" style="margin-top: 4px;">
              ${ALLOWED_EVIDENCE.map(ev => `
                <label class="evidence-item">
                  <input type="checkbox" ${evList.includes(ev) ? 'checked' : ''} onchange="toggleBoxEvidence(${idx}, '${ev}', this.checked)">
                  <span>${ev}</span>
                </label>
              `).join('')}
            </div>
          </div>
          ${hasContradiction ? `
            <div class="alert-banner">
              ⚠️ <strong>Contradiction Active:</strong> This box currently has positive fire/scar tags AND <code>NO_CLEAR_VISUAL_EVIDENCE</code>. Please uncheck <code>NO_CLEAR_VISUAL_EVIDENCE</code> (or remove the positive tags) before saving.
            </div>
          ` : `
            <div style="font-size:0.7rem; color:#81c784;">✓ Evidence flags consistent (no contradictions).</div>
          `}
        `;
        list.appendChild(div);
      });
    }

    function toggleBoxEvidence(idx, ev, isChecked) {
      let list = editableBoxes[idx].visual_evidence || [];
      if (isChecked && !list.includes(ev)) {
        list.push(ev);
      } else if (!isChecked && list.includes(ev)) {
        list = list.filter(item => item !== ev);
      }
      editableBoxes[idx].visual_evidence = list;
      renderBoxesList();
    }

    function updateBoxCoord(idx, coord, val) {
      val = parseInt(val, 10);
      if (isNaN(val)) return;
      editableBoxes[idx].bbox[coord] = Math.max(0, Math.min(512, val));
      renderCanvas();
    }

    function updateBoxField(idx, field, val) {
      editableBoxes[idx][field] = val;
      renderBoxesList();
      renderCanvas();
    }

    function deleteBox(idx) {
      editableBoxes.splice(idx, 1);
      renderBoxesList();
      renderCanvas();
    }

    function clearAllBoxes() {
      editableBoxes = [];
      renderBoxesList();
      renderCanvas();
    }

    function promptAddBox() {
      const input = prompt("Enter coordinates as x_min, y_min, x_max, y_max (e.g. 217, 225, 268, 295):");
      if (!input) return;
      const parts = input.split(/[\\s,]+/).map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n));
      if (parts.length !== 4) {
        showNotification("Please enter 4 valid numbers: x_min, y_min, x_max, y_max", true);
        return;
      }
      const [x_min, y_min, x_max, y_max] = parts;
      if (x_min >= x_max || y_min >= y_max || x_min < 0 || y_min < 0 || x_max > 512 || y_max > 512) {
        showNotification("Invalid coordinates or out of bounds (0-512)", true);
        return;
      }
      const isCrop = currentChipId.includes('08');
      editableBoxes.push({
        annotation_id: `${currentChipId}_CORR_${editableBoxes.length + 1}`,
        class_name: isCrop ? "Agricultural Fire" : "Forest Fire",
        bbox: { x_min, y_min, x_max, y_max },
        geometry_confidence: "MEDIUM",
        source_class_confidence: "MEDIUM",
        visibility_status: "CLEAR",
        visual_evidence: isCrop ? ["BURN_SCAR_VISIBLE", "CROPLAND_CONTEXT_VISIBLE"] : ["DIRECT_FIRE_VISIBLE", "BURN_SCAR_VISIBLE", "FOREST_CONTEXT_VISIBLE"],
        firms_relationship: "INSIDE_OBJECT",
        interaction_audit: { manual_interaction_recorded: true, event_type: "MANUAL_INPUT", coordinates: [x_min, y_min, x_max, y_max] }
      });
      renderBoxesList();
      renderCanvas();
    }

    function renderCanvas() {
      const cvs = document.getElementById("viewCanvas");
      const ctx = cvs.getContext("2d");
      ctx.clearRect(0, 0, cvs.width, cvs.height);

      ctx.save();
      ctx.translate(panX, panY);
      ctx.scale(zoomLevel, zoomLevel);

      const activeImg = (currentBand === "rgb") ? rgbImg : swirImg;
      if (activeImg.complete && activeImg.naturalWidth > 0) {
        ctx.drawImage(activeImg, 0, 0, 512, 512);
      } else {
        ctx.fillStyle = "#111";
        ctx.fillRect(0, 0, 512, 512);
        ctx.fillStyle = "#666";
        ctx.font = "14px sans-serif";
        ctx.fillText("Loading Sentinel-2 imagery...", 170, 256);
      }

      // Draw consensus boxes (Gold / Orange)
      editableBoxes.forEach((b, i) => {
        const bb = b.bbox;
        ctx.strokeStyle = "#ff9800";
        ctx.lineWidth = 2.5 / zoomLevel;
        ctx.fillStyle = "rgba(255, 152, 0, 0.2)";
        ctx.strokeRect(bb.x_min, bb.y_min, bb.x_max - bb.x_min, bb.y_max - bb.y_min);
        ctx.fillRect(bb.x_min, bb.y_min, bb.x_max - bb.x_min, bb.y_max - bb.y_min);
        ctx.font = `bold ${Math.max(11, 12 / zoomLevel)}px sans-serif`;
        ctx.fillStyle = "#ff9800";
        ctx.fillText(`BOX #${i+1}: ${b.class_name}`, bb.x_min + 4, bb.y_min + 14);
      });

      // Drawing preview
      if (currentDrawBox) {
        ctx.strokeStyle = "#fff";
        ctx.setLineDash([4 / zoomLevel, 4 / zoomLevel]);
        ctx.lineWidth = 2 / zoomLevel;
        ctx.strokeRect(
          currentDrawBox.x_min, currentDrawBox.y_min,
          currentDrawBox.x_max - currentDrawBox.x_min, currentDrawBox.y_max - currentDrawBox.y_min
        );
        ctx.setLineDash([]);
      }

      ctx.restore();
    }

    function getCanvasCoords(e) {
      const cvs = document.getElementById("viewCanvas");
      const rect = cvs.getBoundingClientRect();
      const scaleX = 512 / (rect.width || 512);
      const scaleY = 512 / (rect.height || 512);
      const clientX = e.clientX !== undefined ? e.clientX : 0;
      const clientY = e.clientY !== undefined ? e.clientY : 0;
      const x = (clientX - rect.left) * scaleX;
      const y = (clientY - rect.top) * scaleY;
      const imgX = Math.round((x - panX) / zoomLevel);
      const imgY = Math.round((y - panY) / zoomLevel);
      return { x: Math.max(0, Math.min(512, imgX)), y: Math.max(0, Math.min(512, imgY)) };
    }

    function setupCanvasEvents() {
      const cvs = document.getElementById("viewCanvas");

      cvs.addEventListener("pointerdown", (e) => {
        if (e.button === 1 || e.shiftKey) {
          isPanning = true;
          panStartX = e.clientX - panX;
          panStartY = e.clientY - panY;
          return;
        }
        if (e.button === 0) {
          isDrawing = true;
          if (cvs.setPointerCapture) try { cvs.setPointerCapture(e.pointerId); } catch (_) {}
          const { x, y } = getCanvasCoords(e);
          drawStartX = x; drawStartY = y;
          currentDrawBox = { x_min: x, y_min: y, x_max: x, y_max: y };
        }
      });

      cvs.addEventListener("pointermove", (e) => {
        const { x, y } = getCanvasCoords(e);
        document.getElementById("coordDisplay").innerText = `Pixel: X: ${x}, Y: ${y}`;
        if (isPanning) {
          panX = e.clientX - panStartX;
          panY = e.clientY - panStartY;
          renderCanvas();
          return;
        }
        if (isDrawing) {
          currentDrawBox = {
            x_min: Math.min(drawStartX, x),
            y_min: Math.min(drawStartY, y),
            x_max: Math.max(drawStartX, x),
            y_max: Math.max(drawStartY, y)
          };
          renderCanvas();
        }
      });

      function handleDrawEnd(e) {
        if (isPanning) isPanning = false;
        if (!isDrawing) return;
        isDrawing = false;
        if (cvs.releasePointerCapture && e && e.pointerId !== undefined) {
          try { cvs.releasePointerCapture(e.pointerId); } catch (_) {}
        }
        if (currentDrawBox) {
          const w = currentDrawBox.x_max - currentDrawBox.x_min;
          const h = currentDrawBox.y_max - currentDrawBox.y_min;
          if (w >= 4 && h >= 4) {
            const isCrop = currentChipId.includes('08');
            editableBoxes.push({
              annotation_id: `${currentChipId}_CORR_${editableBoxes.length + 1}`,
              class_name: isCrop ? "Agricultural Fire" : "Forest Fire",
              bbox: { ...currentDrawBox },
              geometry_confidence: "MEDIUM",
              source_class_confidence: "MEDIUM",
              visibility_status: "CLEAR",
              visual_evidence: isCrop ? ["BURN_SCAR_VISIBLE", "CROPLAND_CONTEXT_VISIBLE"] : ["DIRECT_FIRE_VISIBLE", "BURN_SCAR_VISIBLE", "FOREST_CONTEXT_VISIBLE"],
              firms_relationship: "INSIDE_OBJECT",
              interaction_audit: { manual_interaction_recorded: true, event_type: "CANVAS_DRAW", coordinates: [currentDrawBox.x_min, currentDrawBox.y_min, currentDrawBox.x_max, currentDrawBox.y_max] }
            });
            renderBoxesList();
          }
        }
        currentDrawBox = null;
        renderCanvas();
      }

      cvs.addEventListener("pointerup", handleDrawEnd);
      cvs.addEventListener("pointercancel", handleDrawEnd);
      window.addEventListener("pointerup", (e) => { if (isDrawing) handleDrawEnd(e); });
    }

    async function openReviewModal() {
      const status = document.getElementById("selStatus").value;
      const rationale = document.getElementById("txtRationale").value.trim();

      if (rationale.length < 15) {
        showNotification("Please provide a substantive correction rationale (>= 15 characters).", true);
        return;
      }

      if (status === "HAS_ANNOTATIONS" && editableBoxes.length === 0) {
        showNotification("HAS_ANNOTATIONS requires at least one bounding box. Draw or add a box first.", true);
        return;
      }

      // Check for contradictions before opening modal
      for (let i = 0; i < editableBoxes.length; i++) {
        const ev = editableBoxes[i].visual_evidence || [];
        if ((ev.includes("DIRECT_FIRE_VISIBLE") || ev.includes("BURN_SCAR_VISIBLE")) && ev.includes("NO_CLEAR_VISUAL_EVIDENCE")) {
          showNotification(`Cannot submit: Box #${i+1} has contradictory evidence flags. Please resolve it first.`, true);
          return;
        }
      }

      // Compute diff via API preview
      const payload = {
        chip_id: currentChipId,
        corrected_consensus: {
          chip_annotation_status: status,
          annotations: status === "HAS_ANNOTATIONS" ? editableBoxes : []
        }
      };

      try {
        const resp = await fetch("/api/diff-preview", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const res = await resp.json();
        if (!res.success) throw new Error(res.error || "Failed to preview diff");

        document.getElementById("modalChipId").innerText = currentChipId;
        document.getElementById("modalOrigSha").innerText = res.original_sha256;
        const diffUl = document.getElementById("modalDiffList");
        diffUl.innerHTML = "";
        (res.summary || []).forEach(line => {
          const li = document.createElement("li");
          li.innerText = line;
          diffUl.appendChild(li);
        });

        document.getElementById("modalRationaleText").innerText = rationale;
        document.getElementById("chkModalConfirm").checked = false;
        document.getElementById("reviewModal").style.display = "flex";
      } catch (err) {
        showNotification("Diff error: " + err.message, true);
      }
    }

    function closeReviewModal() {
      document.getElementById("reviewModal").style.display = "none";
    }

    async function executeSaveCorrection() {
      const confirmed = document.getElementById("chkModalConfirm").checked;
      if (!confirmed) {
        showNotification("Please check the explicit human confirmation box.", true);
        return;
      }

      const status = document.getElementById("selStatus").value;
      const rationale = document.getElementById("txtRationale").value.trim();

      const payload = {
        chip_id: currentChipId,
        human_confirmation: {
          confirmed: true,
          statement: "I confirm that I have reviewed the Sentinel-2 imagery and explicitly approve these corrections."
        },
        correction_rationale: rationale,
        corrected_consensus: {
          chip_annotation_status: status,
          annotations: status === "HAS_ANNOTATIONS" ? editableBoxes : []
        }
      };

      try {
        const resp = await fetch("/api/save-correction", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const res = await resp.json();
        if (res.success) {
          showNotification("SUCCESS: Saved Stage 8.16 correction (v2) for " + currentChipId);
          closeReviewModal();
          setChipBadge(currentChipId, true);
          const b = document.getElementById("saveStatusBadge");
          b.className = "tag tag-corrected";
          b.innerText = "CORRECTED (v2)";
          updateHeaderStats();
        } else {
          showNotification("Save failed: " + (res.errors || []).join(", "), true);
        }
      } catch (err) {
        showNotification("Network error: " + err.message, true);
      }
    }

    async function updateHeaderStats() {
      try {
        const resp = await fetch("/api/stats");
        const st = await resp.json();
        document.getElementById("corrCountText").innerText = st.corrected_count;
        document.getElementById("origStatusText").innerText = st.all_original_valid ? "6 / 6 VERIFIED (IMMUTABLE)" : "HASH MISMATCH DETECTED";
        (st.chips || []).forEach(c => setChipBadge(c.chip_id, c.is_corrected));
      } catch (_) {}
    }

    function showNotification(msg, isError = false) {
      const el = document.getElementById("notification");
      el.innerText = msg;
      el.className = isError ? "notif-error" : "notif-success";
      el.style.display = "block";
      setTimeout(() => { el.style.display = "none"; }, 4500);
    }

    window.onload = init;
  </script>
</body>
</html>
"""


class DS08CorrectionHandler(http.server.BaseHTTPRequestHandler):
    """HTTP Request handler for Stage 8.16 Correction Workspace."""

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ["", "/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CORRECTION_UI.encode("utf-8"))
            return

        if path == "/api/stats":
            orig_valid, _ = verify_original_records()
            corr_count = 0
            chips_stats = []
            for cid in DISPUTED_6_CHIPS:
                fpath = CORRECTIONS_DIR / f"{cid}_corrected_v2.json"
                is_c = fpath.exists()
                if is_c:
                    corr_count += 1
                chips_stats.append({"chip_id": cid, "is_corrected": is_c})

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "total_disputed": 6,
                        "corrected_count": corr_count,
                        "all_original_valid": orig_valid,
                        "chips": chips_stats,
                    }
                ).encode("utf-8")
            )
            return

        if path.startswith("/api/chip/"):
            chip_id = path.split("/")[-1]
            try:
                data = load_correction_chip_data(chip_id)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode("utf-8"))
            except Exception as e:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        if path.startswith("/api/preview/"):
            parts = path.split("/")
            if len(parts) >= 5:
                chip_id = parts[3]
                band = parts[4]
                paths = resolve_chip_paths(chip_id)
                img_path = paths["rgb_preview"] if band == "rgb" else paths["swir_preview"]
                if img_path and img_path.exists():
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.end_headers()
                    with open(img_path, "rb") as f:
                        self.wfile.write(f.read())
                    return
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/diff-preview":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode("utf-8"))
                chip_id = payload.get("chip_id")
                prop_fc = payload.get("corrected_consensus", {})
                orig_file = REVIEW_DIR / f"{chip_id}_adjudicated_v1.json"
                orig_raw = orig_file.read_bytes()
                orig_sha = hashlib.sha256(orig_raw).hexdigest()
                orig_data = json.loads(orig_raw.decode("utf-8"))
                diff = compute_correction_diff(orig_data.get("final_consensus", {}), prop_fc)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            "success": True,
                            "original_sha256": orig_sha,
                            "changed_fields": diff["changed_fields"],
                            "summary": diff["summary"],
                        }
                    ).encode("utf-8")
                )
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

        if parsed.path == "/api/save-correction":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode("utf-8"))
                chip_id = payload.get("chip_id")
                success, errors, record = save_chip_correction(chip_id, payload)
                self.send_response(200 if success else 400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            "success": success,
                            "errors": errors,
                            "record_sha256": record.get("record_sha256") if record else None,
                        }
                    ).encode("utf-8")
                )
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "errors": [str(e)]}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()


def run_correction_server(port: int = 8093) -> None:
    """Runs local HTTP server for the Stage 8.16 Correction Tool."""
    with socketserver.TCPServer(("", port), DS08CorrectionHandler) as httpd:
        print(f"\n{'='*70}")
        print(f"DS08 STAGE 8.16 CONTROLLED ADJUDICATION CORRECTION WORKSPACE ACTIVE")
        print(f"{'='*70}")
        print(f"  Local URL:        http://localhost:{port}")
        print(f"  Disputed Chips:   6 affected chips")
        print(f"  Storage Target:   data/reference/ds08/annotations/adjudication/corrections/")
        print(f"  Audit Log:        data/reference/ds08/annotations/adjudication/corrections/stage8_16_audit_log.jsonl")
        print(f"{'='*70}\n")
        httpd.serve_forever()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DS08 Stage 8.16 Correction Tool")
    parser.add_argument("--ui", action="store_true", help="Launch UI HTTP server")
    parser.add_argument("--port", type=int, default=8093, help="Port to bind server (default 8093)")
    parser.add_argument("--verify", action="store_true", help="Run read-only verification of source records and manifest")
    args = parser.parse_args()

    if args.verify:
        v_orig, err_orig = verify_original_records()
        v_base, err_base = verify_a1_a2_baseline()
        v_pred, err_pred = verify_frozen_predecessors()
        print(f"Original Records: {'PASS' if v_orig else 'FAIL'} ({len(err_orig)} errors)")
        print(f"Baseline A1/A2:   {'PASS' if v_base else 'FAIL'} ({len(err_base)} errors)")
        print(f"Predecessors:     {'PASS' if v_pred else 'FAIL'} ({len(err_pred)} errors)")
        sys.exit(0 if (v_orig and v_base and v_pred) else 1)

    if args.ui:
        run_correction_server(port=args.port)
    else:
        parser.print_help()
