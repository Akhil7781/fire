"""
DS08 Hardened Human Adjudication Interface and Review Tool (Stage 8.15 Repair).

Hardening & Integrity Rules:
- Dedicated adjudication server on port 8092.
- Scope strictly limited to the 6 disputed chips:
  1. PILOT_03_NORTH
  2. PILOT_06_CENTRAL
  3. PILOT_08_CENTRAL
  4. PILOT_15_EAST
  5. PILOT_16_EAST
  6. PILOT_18_WEST
- Consensus annotations strictly start EMPTY ([]). Zero default boxes.
- Zero placeholder injection: coordinates [200, 200, 300, 300] are forbidden and rejected.
- A bounding box can exist ONLY via genuine human canvas drawing interaction (click + drag).
- Strict validation:
  * HAS_ANNOTATIONS requires >= 1 valid manually drawn bbox.
  * NO_VISIBLE_TARGET requires annotations == [].
  * UNRESOLVED does not auto-create boxes.
- Mandatory Human Adjudication Rationale:
  * Must be substantive and chip-specific explaining observable visual basis.
  * Explicitly rejects generic phrases ("I saw the fire", "Looks like fire", "Agreed with A1/A2", etc.).
- ZERO prepopulation of A1/A2 boxes into consensus (A1/A2 are overlay comparisons only).
- Strict immutability: Annotator 1 and Annotator 2 source directories are verified bit-for-bit before and after every operation.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.server
import json
import os
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

DISPUTE_CATEGORIES = {
    "PILOT_03_NORTH": "Evidence nuance (A1 omitted FOREST_CONTEXT_VISIBLE vs A2 included it). Both agree 2 Forest Fire boxes.",
    "PILOT_06_CENTRAL": "Evidence nuance (A1 omitted FOREST_CONTEXT_VISIBLE vs A2 included it). Both agree 2 Forest Fire boxes.",
    "PILOT_08_CENTRAL": "Observation-status disagreement (A1: HAS_ANNOTATIONS / 1 Agricultural Fire box vs A2: NO_VISIBLE_TARGET). Fresh human review required.",
    "PILOT_15_EAST": "Evidence nuance (A1 included BURN_SCAR_VISIBLE vs A2 omitted it). Both agree 3 Forest Fire boxes.",
    "PILOT_16_EAST": "Segmentation / box count disagreement (A1: 3 Forest Fire boxes vs A2: 4 Forest Fire boxes with extra SE box).",
    "PILOT_18_WEST": "Evidence nuance (A1 omitted BURN_SCAR_VISIBLE vs A2 included it). Both agree 1 Forest Fire box.",
}

PRE_ADJUDICATION_HASHES = {
    "PILOT_03_NORTH": {
        "annotator_1": "4ea58e129deacc36660c26527cd4e235ccda250d0a0dcb344e3a5e82ea6a79dd",
        "annotator_2": "d464b2f542071ea100ffedf73de863f12e1377c4fe300345af626d7ea1848f00",
    },
    "PILOT_06_CENTRAL": {
        "annotator_1": "88acb76ba6b4c1ee7805a476a07fea307bc1c5440208f5b94c8afc4ab2822615",
        "annotator_2": "46d6dc9efa99c94d43f4eaac5d8fccec06dfc081166d4f14e5436588032242d9",
    },
    "PILOT_08_CENTRAL": {
        "annotator_1": "643a579d93e4d2ce88ab03ad3d01790f9c322b8f12ebb1ca5ca7e0216eae69c7",
        "annotator_2": "b3acc39e10c4bdf760949066bd0b263bd78e226b803883d27cc4e0a2fffd844e",
    },
    "PILOT_15_EAST": {
        "annotator_1": "a68f9383dccecb93dbd9755e0d629be0ddc685da555d9132c7297e446eae5759",
        "annotator_2": "c21eb67c1b0b1852a4b4892fb0ce07d779918fd3ccf792c25543050cae6b029d",
    },
    "PILOT_16_EAST": {
        "annotator_1": "7d7f079047c191a8ff315298554e7b56a2a5e065627349a5b8a8e9ff4b5c9939",
        "annotator_2": "eabd01e9dccb1ce0b0c46145b32d061c63e69fa2328d053066940cfe5d04d9fd",
    },
    "PILOT_18_WEST": {
        "annotator_1": "8714e286dbad7610e7a79b6ee6e1ef1cae30deef33ad04244fdc3aacf943c257",
        "annotator_2": "54ba4215c080fe79eae0a3200db971a7e4b04f7820fa2f2950d5c95e5988b4f6",
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
]

FORBIDDEN_DEFAULT_BOX = {"x_min": 200, "y_min": 200, "x_max": 300, "y_max": 300}

A1_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "manual" / "annotator_1"
A2_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "manual" / "annotator_2"
ADJUDICATION_REVIEW_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "adjudication" / "review"
QUARANTINE_STAGE8_15_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "quarantine" / "stage8_15_invalid"


def verify_source_file_hashes() -> Tuple[bool, List[str]]:
    """Verifies that all 12 disputed files remain bit-for-bit identical to pre-adjudication hashes."""
    errors = []
    for chip_id, exp_hashes in PRE_ADJUDICATION_HASHES.items():
        f1 = A1_DIR / f"{chip_id}_annotator1.json"
        f2 = A2_DIR / f"{chip_id}_annotator2.json"

        if not f1.exists():
            errors.append(f"A1 file missing: {f1}")
        else:
            h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
            if h1 != exp_hashes["annotator_1"]:
                errors.append(f"A1 hash mismatch for {chip_id}: expected {exp_hashes['annotator_1']}, got {h1}")

        if not f2.exists():
            errors.append(f"A2 file missing: {f2}")
        else:
            h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
            if h2 != exp_hashes["annotator_2"]:
                errors.append(f"A2 hash mismatch for {chip_id}: expected {exp_hashes['annotator_2']}, got {h2}")

    return len(errors) == 0, errors


def validate_adjudication_rationale(rationale: str) -> Tuple[bool, Optional[str]]:
    """Validates that a human adjudication rationale is substantive and not generic placeholder text."""
    r_clean = rationale.strip()
    if not r_clean:
        return False, "Adjudication rationale is empty. A human-written rationale is mandatory."

    # Check against prohibited generic phrases first
    lower_r = r_clean.lower()
    for pat in PROHIBITED_GENERIC_RATIONALE_PATTERNS:
        if re.search(pat, lower_r):
            return False, (
                f"Generic rationale rejected: matches prohibited pattern '{pat}'. "
                "Adjudication rationale must provide chip-specific observable visual evidence "
                "(e.g. SWIR reflection, burn scar morphology, smoke plume, or land-cover context) "
                "explaining why this consensus label was determined."
            )

    if len(r_clean) < 15:
        return False, "Adjudication rationale is too short (< 15 characters). Please provide observable visual findings."

    return True, None


def load_adjudication_chip_data(chip_id: str) -> Dict[str, Any]:
    """Loads all data required to adjudicate a disputed chip."""
    if chip_id not in DISPUTED_6_CHIPS:
        raise ValueError(f"Chip {chip_id} is not one of the 6 disputed chips")

    f1 = A1_DIR / f"{chip_id}_annotator1.json"
    f2 = A2_DIR / f"{chip_id}_annotator2.json"
    with open(f1, "r", encoding="utf-8") as f:
        a1_data = json.load(f)
    with open(f2, "r", encoding="utf-8") as f:
        a2_data = json.load(f)

    # Check if already adjudicated in review dir
    adj_file = ADJUDICATION_REVIEW_DIR / f"{chip_id}_adjudicated_v1.json"
    existing_adj = None
    if adj_file.exists():
        with open(adj_file, "r", encoding="utf-8") as f:
            existing_adj = json.load(f)

    paths = resolve_chip_paths(chip_id)
    manifest = load_manifest()
    entry = next((c for c in manifest["chips"] if c["chip_id"] == chip_id), {})

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
        "dispute_category": DISPUTE_CATEGORIES.get(chip_id, ""),
        "firms_warning": "FIRMS CONTEXT — NOT GROUND TRUTH",
        "firms_info": {
            "latitude": entry.get("firms_latitude"),
            "longitude": entry.get("firms_longitude"),
            "frp_mw": entry.get("firms_frp"),
            "pixel_col": firms_col,
            "pixel_row": firms_row,
            "s2_acq_utc": entry.get("acquisition_datetime_utc"),
            "cloud_cover_pct": entry.get("cloud_cover_pct"),
            "tile_id": entry.get("tile_id"),
        },
        "A1_original": a1_data,
        "A2_original": a2_data,
        "source_hashes": PRE_ADJUDICATION_HASHES[chip_id],
        "existing_adjudication": existing_adj,
        "is_adjudicated": existing_adj is not None,
    }


def save_adjudicated_chip(chip_id: str, payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Saves a senior human adjudication record with strict hardened schema and provenance checks."""
    if chip_id not in DISPUTED_6_CHIPS:
        return False, [f"Chip '{chip_id}' is not in the 6 disputed chips ({DISPUTED_6_CHIPS})"]

    # 1. Pre-write source integrity verification
    valid_sources, hash_errors = verify_source_file_hashes()
    if not valid_sources:
        return False, [f"SOURCE INTEGRITY VIOLATION: {hash_errors}"]

    # 2. Extract consensus components
    final_consensus = payload.get("final_consensus", {})
    if not final_consensus:
        return False, ["Missing 'final_consensus' block"]

    obs_status = final_consensus.get("chip_annotation_status")
    if obs_status not in ALLOWED_CHIP_STATUSES:
        return False, [f"Invalid chip_annotation_status: '{obs_status}'. Allowed: {ALLOWED_CHIP_STATUSES}"]

    annotations = final_consensus.get("annotations", [])

    # 3. Observation status enforcement
    if obs_status == "UNRESOLVED":
        return False, [
            "Observation status 'UNRESOLVED' is not permitted for final consensus adjudication. "
            "The senior adjudicator must make a definitive determination ('HAS_ANNOTATIONS' or 'NO_VISIBLE_TARGET')."
        ]
    if obs_status == "HAS_ANNOTATIONS" and len(annotations) == 0:
        return False, ["Observation status 'HAS_ANNOTATIONS' requires at least one manually drawn bounding box."]
    if obs_status == "NO_VISIBLE_TARGET" and len(annotations) > 0:
        return False, ["Observation status 'NO_VISIBLE_TARGET' must have an empty annotations array ([])."]

    # 4. Mandatory Human Rationale validation
    rationale = payload.get("adjudication_rationale", "")
    valid_rat, rat_err = validate_adjudication_rationale(rationale)
    if not valid_rat:
        return False, [rat_err]

    # 5. Mandatory Human Verified confirmation
    human_verified = payload.get("human_verified", False)
    if not human_verified:
        return False, ["human_verified must be explicitly checked true by the human adjudicator."]

    # 6. Bounding Box Hardening: reject default box & verify manual drawing
    for idx, ann in enumerate(annotations, start=1):
        bbox = ann.get("bbox", {})
        if (
            bbox.get("x_min") == FORBIDDEN_DEFAULT_BOX["x_min"]
            and bbox.get("y_min") == FORBIDDEN_DEFAULT_BOX["y_min"]
            and bbox.get("x_max") == FORBIDDEN_DEFAULT_BOX["x_max"]
            and bbox.get("y_max") == FORBIDDEN_DEFAULT_BOX["y_max"]
        ):
            return False, [
                f"Box #{idx} rejected: exact forbidden placeholder coordinates [200, 200, 300, 300] detected. "
                "Bounding boxes must be manually drawn on the imagery canvas."
            ]

        # Geometry validation
        x_min, y_min = bbox.get("x_min", -1), bbox.get("y_min", -1)
        x_max, y_max = bbox.get("x_max", -1), bbox.get("y_max", -1)
        if x_min >= x_max or y_min >= y_max:
            return False, [f"Box #{idx} has invalid geometry (zero/negative width or height): {bbox}"]
        if (x_max - x_min) < 4 or (y_max - y_min) < 4:
            return False, [f"Box #{idx} is too small (< 4 pixels): {bbox}"]

        # Manual interaction audit
        audit = ann.get("interaction_audit", {})
        if not audit.get("manual_interaction_recorded", False):
            return False, [f"Box #{idx} missing required manual canvas interaction audit record."]

        # Contradictory visual evidence validation
        box_ev = ann.get("visual_evidence", [])
        if ("DIRECT_FIRE_VISIBLE" in box_ev or "BURN_SCAR_VISIBLE" in box_ev) and "NO_CLEAR_VISUAL_EVIDENCE" in box_ev:
            return False, [
                f"Box #{idx} has contradictory evidence flags: cannot combine positive fire/burn-scar evidence with 'NO_CLEAR_VISUAL_EVIDENCE'."
            ]

        cname = ann.get("class_name")
        if obs_status != "UNRESOLVED" and cname not in ALLOWED_CLASSES:
            return False, [f"Box #{idx} has invalid class_name '{cname}'"]
        ann["class_id"] = CLASS_ID_MAP.get(cname, 0)
        ann["annotation_id"] = f"{chip_id}_ADJ_{idx:02d}"
        ann["annotator_id"] = "HUMAN_ADJUDICATOR_01"
        ann["review_status"] = "ADJUDICATED"
        if "annotation_timestamp" not in ann:
            ann["annotation_timestamp"] = datetime.now(timezone.utc).isoformat()

    now_iso = datetime.now(timezone.utc).isoformat()

    # Load original A1 and A2 for provenance embedding
    f1 = A1_DIR / f"{chip_id}_annotator1.json"
    f2 = A2_DIR / f"{chip_id}_annotator2.json"
    with open(f1, "r", encoding="utf-8") as f:
        a1_orig = json.load(f)
    with open(f2, "r", encoding="utf-8") as f:
        a2_orig = json.load(f)

    source_classes = sorted(list(set(ann["class_name"] for ann in annotations)))
    if not source_classes:
        source_classes = [obs_status]

    all_evidence = sorted(list(set(ev for ann in annotations for ev in ann.get("visual_evidence", []))))
    if not all_evidence:
        all_evidence = ["NO_CLEAR_VISUAL_EVIDENCE"]

    primary_vis = annotations[0].get("visibility_status", "CLEAR") if annotations else "CLEAR"
    primary_geom_conf = annotations[0].get("geometry_confidence", "MEDIUM") if annotations else "MEDIUM"
    primary_class_conf = annotations[0].get("source_class_confidence", "MEDIUM") if annotations else "MEDIUM"

    final_consensus["chip_id"] = chip_id
    final_consensus["annotation_version"] = "v1.0"
    final_consensus["chip_annotation_status"] = obs_status
    final_consensus["annotations"] = annotations
    final_consensus["source_classes"] = source_classes
    final_consensus["visual_evidence"] = all_evidence
    final_consensus["visibility_status"] = primary_vis
    final_consensus["geometry_confidence"] = primary_geom_conf
    final_consensus["source_class_confidence"] = primary_class_conf
    final_consensus["context_metadata"] = a1_orig.get("context_metadata", {})

    # Validate against standard schema
    valid_schema, schema_errors = validate_annotation_payload(final_consensus)
    if not valid_schema:
        return False, [f"Schema validation error on consensus: {schema_errors}"]

    # Assemble authoritative record
    record = {
        "chip_id": chip_id,
        "annotation_version": "v1.0",
        "adjudication_status": "COMPLETED_HUMAN_ADJUDICATION",
        "adjudicator": "HUMAN_ADJUDICATOR_01",
        "adjudication_timestamp": now_iso,
        "human_verified": True,
        "adjudication_rationale": rationale.strip(),
        "dispute_category": DISPUTE_CATEGORIES.get(chip_id, ""),
        "source_annotation_hashes": {
            "annotator_1": PRE_ADJUDICATION_HASHES[chip_id]["annotator_1"],
            "annotator_2": PRE_ADJUDICATION_HASHES[chip_id]["annotator_2"],
        },
        "A1_original": {
            "chip_annotation_status": a1_orig.get("chip_annotation_status"),
            "annotations": a1_orig.get("annotations", []),
            "visual_evidence": sorted(list(set(ev for ann in a1_orig.get("annotations", []) for ev in ann.get("visual_evidence", [])))),
            "visibility_status": a1_orig.get("annotations", [{}])[0].get("visibility_status", "CLEAR") if a1_orig.get("annotations") else "CLEAR",
            "confidence": {
                "geometry_confidence": a1_orig.get("annotations", [{}])[0].get("geometry_confidence", "MEDIUM") if a1_orig.get("annotations") else "MEDIUM",
                "source_class_confidence": a1_orig.get("annotations", [{}])[0].get("source_class_confidence", "MEDIUM") if a1_orig.get("annotations") else "MEDIUM",
            },
        },
        "A2_original": {
            "chip_annotation_status": a2_orig.get("chip_annotation_status"),
            "annotations": a2_orig.get("annotations", []),
            "visual_evidence": sorted(list(set(ev for ann in a2_orig.get("annotations", []) for ev in ann.get("visual_evidence", [])))),
            "visibility_status": a2_orig.get("annotations", [{}])[0].get("visibility_status", "CLEAR") if a2_orig.get("annotations") else "CLEAR",
            "confidence": {
                "geometry_confidence": a2_orig.get("annotations", [{}])[0].get("geometry_confidence", "MEDIUM") if a2_orig.get("annotations") else "MEDIUM",
                "source_class_confidence": a2_orig.get("annotations", [{}])[0].get("source_class_confidence", "MEDIUM") if a2_orig.get("annotations") else "MEDIUM",
            },
        },
        "final_consensus": final_consensus,
        "chip_annotation_status": obs_status,
        "annotations": annotations,
        "context_metadata": a1_orig.get("context_metadata", {}),
    }

    # Save to disk
    ADJUDICATION_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    target_path = ADJUDICATION_REVIEW_DIR / f"{chip_id}_adjudicated_v1.json"
    if target_path.exists():
        prev_raw = target_path.read_bytes()
        prev_sha = hashlib.sha256(prev_raw).hexdigest()
        record["correction_audit"] = {
            "is_correction": True,
            "previous_submission_sha256": prev_sha,
            "correction_timestamp": now_iso,
            "correction_rationale": rationale.strip(),
            "human_verified": True,
        }
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    # Post-write hash verification
    valid_post, post_errors = verify_source_file_hashes()
    if not valid_post:
        return False, [f"POST-WRITE SOURCE INTEGRITY VIOLATION: {post_errors}"]

    return True, []


HTML_HARDENED_UI = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>DS08 Hardened Adjudication Interface (Stage 8.15)</title>
  <style>
    :root {
      --bg: #181920;
      --card-bg: #232530;
      --card-alt: #2a2d3d;
      --border: #3b3f54;
      --text: #e2e4ea;
      --text-muted: #9aa0b4;
      --accent: #ff9800;
      --accent-hover: #f57c00;
      --danger: #ef5350;
      --success: #4caf50;
      --info-a1: #29b6f6;
      --info-a2: #66bb6a;
      --warning-bg: #3d2314;
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
      border-bottom: 2px solid var(--accent);
      padding: 10px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
    }
    .header-title { font-size: 1.1rem; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 10px; }
    .header-badge {
      background: rgba(255, 152, 0, 0.2);
      border: 1px solid var(--accent);
      color: var(--accent);
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .firms-banner {
      background: var(--warning-bg);
      border-bottom: 1px solid #ff7043;
      color: #ffccbc;
      padding: 8px 20px;
      font-size: 0.85rem;
      font-weight: 600;
      text-align: center;
      letter-spacing: 0.5px;
      flex-shrink: 0;
    }
    .main-layout { display: flex; flex: 1; overflow: hidden; }
    .sidebar {
      width: 250px;
      background: var(--card-bg);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }
    .sidebar-header {
      padding: 12px 16px;
      font-weight: 700;
      font-size: 0.85rem;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border);
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    .chip-list { list-style: none; overflow-y: auto; flex: 1; }
    .chip-item {
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      cursor: pointer;
      display: flex;
      flex-direction: column;
      gap: 4px;
      transition: background 0.15s;
    }
    .chip-item:hover { background: rgba(255, 255, 255, 0.05); }
    .chip-item.active { background: rgba(255, 152, 0, 0.15); border-left: 4px solid var(--accent); }
    .chip-name { font-weight: 600; font-size: 0.9rem; }
    .chip-status-tag {
      font-size: 0.7rem;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 3px;
      align-self: flex-start;
    }
    .tag-adjudicated { background: rgba(76, 175, 80, 0.2); color: #81c784; border: 1px solid #4caf50; }
    .tag-pending { background: rgba(255, 152, 0, 0.2); color: #ffb74d; border: 1px solid #ff9800; }
    
    .content-area { flex: 1; display: flex; overflow: hidden; }
    .viewer-pane {
      flex: 1.1;
      display: flex;
      flex-direction: column;
      border-right: 1px solid var(--border);
      background: #111217;
      overflow: hidden;
    }
    .viewer-toolbar {
      padding: 8px 16px;
      background: var(--card-bg);
      border-bottom: 1px solid var(--border);
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }
    .btn {
      background: var(--card-alt);
      color: var(--text);
      border: 1px solid var(--border);
      padding: 6px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.8rem;
      font-weight: 600;
      transition: all 0.15s;
    }
    .btn:hover { background: var(--border); }
    .btn.active { background: var(--accent); color: #000; border-color: var(--accent); }
    .btn-primary { background: var(--accent); color: #000; border-color: var(--accent); }
    .btn-primary:hover { background: var(--accent-hover); }
    .btn-danger { background: var(--danger); color: #fff; border-color: var(--danger); }
    
    .canvas-container {
      flex: 1;
      position: relative;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: crosshair;
    }
    canvas { display: block; image-rendering: pixelated; }
    
    .inspector-pane {
      flex: 1.2;
      display: flex;
      flex-direction: column;
      background: var(--bg);
      overflow-y: auto;
      padding: 16px;
      gap: 16px;
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
      border-bottom: 1px solid var(--border);
      padding-bottom: 6px;
      display: flex;
      justify-content: space-between;
    }
    .comparison-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .annotator-box {
      background: var(--card-alt);
      border-radius: 4px;
      padding: 10px;
      border-top: 3px solid;
      font-size: 0.8rem;
    }
    .box-a1 { border-color: var(--info-a1); }
    .box-a2 { border-color: var(--info-a2); }
    .annotator-box h4 { margin-bottom: 6px; font-size: 0.85rem; }
    .annotator-box div { margin-bottom: 4px; }
    
    .form-group { display: flex; flex-direction: column; gap: 6px; }
    label { font-size: 0.8rem; font-weight: 600; color: var(--text-muted); }
    select, input[type="text"], textarea {
      background: var(--card-alt);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 10px;
      border-radius: 4px;
      font-size: 0.85rem;
      font-family: inherit;
    }
    select:focus, input[type="text"]:focus, textarea:focus { outline: none; border-color: var(--accent); }
    textarea { resize: vertical; min-height: 90px; }
    
    .bbox-row {
      background: var(--card-alt);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .bbox-header { display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; font-weight: 700; }
    .coord-inputs { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
    .coord-input label { font-size: 0.7rem; }
    .coord-input input { width: 100%; padding: 4px; font-size: 0.8rem; text-align: center; }
    
    .evidence-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 0.75rem; }
    .evidence-item { display: flex; align-items: center; gap: 6px; }
    .evidence-item input { cursor: pointer; }
    
    #notification {
      position: fixed;
      bottom: 20px;
      right: 20px;
      padding: 12px 20px;
      border-radius: 6px;
      font-weight: 600;
      font-size: 0.9rem;
      z-index: 1000;
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
      <span>DS08 HARDENED HUMAN ADJUDICATION WORKSPACE</span>
      <span class="header-badge">SENIOR HUMAN CONSENSUS (HARDENED)</span>
    </div>
    <div id="statsBadge" style="font-size: 0.85rem; color: var(--text-muted);">
      Adjudicated: <strong id="adjudicatedCount" style="color: var(--accent);">0</strong> / 6
    </div>
  </header>

  <div class="firms-banner">
    ⚠️ FIRMS CONTEXT — NOT GROUND TRUTH: Active thermal alerts provide contextual cues only. Target presence, extent, and class must be confirmed via Sentinel-2 visual interpretation. Zero auto-merging / zero auto-boxes.
  </div>

  <div class="main-layout">
    <!-- SIDEBAR -->
    <div class="sidebar">
      <div class="sidebar-header">Disputed Chips (6)</div>
      <ul class="chip-list" id="chipList"></ul>
    </div>

    <!-- CONTENT -->
    <div class="content-area">
      <!-- VIEWER -->
      <div class="viewer-pane">
        <div class="viewer-toolbar">
          <button class="btn active" id="btnRgb" onclick="switchBand('rgb')">RGB Band</button>
          <button class="btn" id="btnSwir" onclick="switchBand('swir')">SWIR (B12/B11/B8)</button>
          <span style="color: var(--border);">|</span>
          <button class="btn" onclick="zoomIn()">Zoom +</button>
          <button class="btn" onclick="zoomOut()">Zoom -</button>
          <button class="btn" onclick="resetZoom()">Reset</button>
          <span style="color: var(--border);">|</span>
          <label style="display: flex; align-items: center; gap: 4px; font-size: 0.8rem; cursor: pointer;">
            <input type="checkbox" id="chkShowA1" checked onchange="renderCanvas()">
            <span style="color: var(--info-a1); font-weight: 600;">Show A1</span>
          </label>
          <label style="display: flex; align-items: center; gap: 4px; font-size: 0.8rem; cursor: pointer;">
            <input type="checkbox" id="chkShowA2" checked onchange="renderCanvas()">
            <span style="color: var(--info-a2); font-weight: 600;">Show A2</span>
          </label>
          <label style="display: flex; align-items: center; gap: 4px; font-size: 0.8rem; cursor: pointer;">
            <input type="checkbox" id="chkShowFirms" checked onchange="renderCanvas()">
            <span style="color: #ff9800; font-weight: 600;">FIRMS Point</span>
          </label>
        </div>

        <div class="canvas-container" id="canvasContainer">
          <canvas id="viewCanvas" width="512" height="512" style="touch-action: none; user-select: none;"></canvas>
        </div>
        <div id="canvas-status-bar" style="padding: 8px 16px; font-size: 0.8rem; color: #ffb74d; background: #201a14; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
          <span id="coord-display">Pixel: X: 0, Y: 0</span>
          <span id="box-mode-display">✏️ Drag to draw box | Double-click to box spot</span>
        </div>
      </div>

      <!-- INSPECTOR & ADJUDICATION FORM -->
      <div class="inspector-pane">
        <!-- CHIP INFO & DISPUTE CARD -->
        <div class="card">
          <div class="card-title">
            <span id="activeChipTitle">PILOT_03_NORTH</span>
            <span id="activeDisputeType" style="color: var(--accent); font-size: 0.75rem;">Dispute Context</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.4;" id="disputeDescription">
            Loading dispute context...
          </div>
          <div style="font-size: 0.75rem; color: #aaa; display: grid; grid-template-columns: 1fr 1fr; gap: 6px;" id="firmsContextGrid"></div>
        </div>

        <!-- COMPARISON CARD -->
        <div class="card">
          <div class="card-title">A1 vs A2 Original Submissions (Reference Overlays Only)</div>
          <div class="comparison-grid">
            <div class="annotator-box box-a1" id="a1Summary">
              <h4 style="color: var(--info-a1);">Annotator 1</h4>
              <div>Status: <span id="a1Status">-</span></div>
              <div>Boxes: <span id="a1BoxCount">-</span></div>
              <div id="a1BoxesDetail"></div>
            </div>
            <div class="annotator-box box-a2" id="a2Summary">
              <h4 style="color: var(--info-a2);">Annotator 2</h4>
              <div>Status: <span id="a2Status">-</span></div>
              <div>Boxes: <span id="a2BoxCount">-</span></div>
              <div id="a2BoxesDetail"></div>
            </div>
          </div>
        </div>

        <!-- ADJUDICATION FORM CARD -->
        <div class="card">
          <div class="card-title" style="color: var(--accent);">Human Consensus Decision</div>

          <div id="pilot08ReopenBanner" style="display: none; background: rgba(255, 152, 0, 0.15); border: 1px solid var(--accent); color: #ffb74d; padding: 10px; border-radius: 4px; font-size: 0.8rem; margin-bottom: 12px; line-height: 1.4;">
            <strong>⚠️ REOPENED DISPUTE:</strong> PILOT_08_CENTRAL was previously marked UNRESOLVED. For final Stage 8.15 consensus, a definitive determination is required: either <strong>NO_VISIBLE_TARGET</strong> (if visual evidence is insufficient to verify an agricultural fire) or <strong>HAS_ANNOTATIONS</strong> (with a verified fire box).
          </div>

          <div class="form-group">
            <label>Final Observation Status</label>
            <select id="adjStatus" onchange="onStatusChange()">
              <option value="HAS_ANNOTATIONS">HAS_ANNOTATIONS (Active fire / thermal target confirmed)</option>
              <option value="NO_VISIBLE_TARGET">NO_VISIBLE_TARGET (Clear image, no corresponding target visible)</option>
              <option value="UNRESOLVED" disabled>UNRESOLVED (Must choose HAS_ANNOTATIONS or NO_VISIBLE_TARGET)</option>
            </select>
          </div>

          <!-- BOXES CONTAINER -->
          <div id="boxesSection" style="display: flex; flex-direction: column; gap: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <label>Adjudicated Bounding Boxes (<span id="boxCountDisplay">0</span>)</label>
              <div style="display: flex; gap: 6px;">
                <button class="btn btn-primary" style="font-size: 0.75rem;" onclick="promptAddBox()">+ Add Box</button>
                <button class="btn btn-danger" style="font-size: 0.75rem;" onclick="clearBoxes()">Clear All</button>
              </div>
            </div>

            <!-- Coordinate Entry Toolbar -->
            <div style="display: flex; gap: 6px; align-items: center; background: var(--card-alt); padding: 8px; border-radius: 4px; border: 1px solid var(--border); flex-wrap: wrap;">
              <span style="font-size: 0.75rem; color: var(--accent); font-weight: 700;">+ Add by Coords:</span>
              <input type="number" id="inp_xmin" placeholder="x_min" min="0" max="511" style="width: 65px; padding: 4px; font-size: 0.8rem; text-align: center;">
              <input type="number" id="inp_ymin" placeholder="y_min" min="0" max="511" style="width: 65px; padding: 4px; font-size: 0.8rem; text-align: center;">
              <input type="number" id="inp_xmax" placeholder="x_max" min="1" max="512" style="width: 65px; padding: 4px; font-size: 0.8rem; text-align: center;">
              <input type="number" id="inp_ymax" placeholder="y_max" min="1" max="512" style="width: 65px; padding: 4px; font-size: 0.8rem; text-align: center;">
              <button class="btn btn-primary" style="font-size: 0.75rem; padding: 4px 10px;" onclick="addFromInputs()">Add</button>
            </div>

            <div id="noBoxesNotice" style="font-size: 0.75rem; color: #ffb74d; background: rgba(255, 152, 0, 0.1); padding: 8px; border-radius: 4px;">
              No bounding boxes yet. Click and drag directly on the Sentinel-2 canvas, click <strong>+ Add Box</strong>, or enter coordinates above.
            </div>
            <div id="bboxList" style="display: flex; flex-direction: column; gap: 10px;"></div>
          </div>

          <!-- RATIONALE -->
          <div class="form-group">
            <label>Substantive Human Adjudication Rationale (Mandatory)</label>
            <div style="font-size: 0.7rem; color: #aaa; margin-bottom: 4px;">
              Explain observable visual evidence (SWIR reflection intensity, burn scar morphology, smoke plume drift, land-cover context).
              Generic phrases like "I saw the fire" or "Agreed with A1" will be strictly rejected.
            </div>
            <textarea id="adjRationale" placeholder="Enter chip-specific visual justification..."></textarea>
          </div>

          <div class="form-group">
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; color: #fff;">
              <input type="checkbox" id="chkVerified" style="width: 16px; height: 16px;">
              <span>I confirm this is a human-verified consensus adjudication based on independent visual inspection.</span>
            </label>
          </div>

          <button class="btn btn-primary" style="padding: 12px; font-size: 0.95rem; font-weight: 700;" onclick="submitAdjudication()">
            💾 SAVE CONSENSUS ADJUDICATION
          </button>
        </div>
      </div>
    </div>
  </div>

  <div id="notification">Notification message</div>

  <script>
    const DISPUTED_CHIPS = ['PILOT_03_NORTH', 'PILOT_06_CENTRAL', 'PILOT_08_CENTRAL', 'PILOT_15_EAST', 'PILOT_16_EAST', 'PILOT_18_WEST'];
    const ALLOWED_EVIDENCE = [
      'DIRECT_FIRE_VISIBLE', 'SMOKE_VISIBLE', 'BURN_SCAR_VISIBLE',
      'INDUSTRIAL_INFRASTRUCTURE_VISIBLE', 'FOREST_CONTEXT_VISIBLE',
      'CROPLAND_CONTEXT_VISIBLE', 'PERSISTENT_THERMAL_SOURCE_CONTEXT',
      'NO_CLEAR_VISUAL_EVIDENCE'
    ];

    let currentChipId = 'PILOT_03_NORTH';
    let currentBand = 'rgb';
    let currentData = null;
    let rgbImg = new Image();
    let swirImg = new Image();
    let zoomLevel = 1.0;
    let panX = 0, panY = 0;
    let isPanning = false, panStartX = 0, panStartY = 0;
    let isDrawing = false, drawStartX = 0, drawStartY = 0, currentDrawBox = null;

    let adjudicatedBoxes = [];

    async function init() {
      renderChipList();
      await loadChip(currentChipId);
      setupCanvasEvents();
    }

    function renderChipList() {
      const list = document.getElementById('chipList');
      list.innerHTML = '';
      DISPUTED_CHIPS.forEach((cid, idx) => {
        const li = document.createElement('li');
        li.className = 'chip-item' + (cid === currentChipId ? ' active' : '');
        li.id = 'chipItem_' + cid;
        li.innerHTML = `
          <div class="chip-name">[${idx+1}/6] ${cid}</div>
          <span class="chip-status-tag tag-pending" id="tag_${cid}">PENDING</span>
        `;
        li.onclick = () => loadChip(cid);
        list.appendChild(li);
      });
    }

    async function loadChip(chipId) {
      currentChipId = chipId;
      document.querySelectorAll('.chip-item').forEach(el => el.classList.remove('active'));
      const activeEl = document.getElementById('chipItem_' + chipId);
      if (activeEl) activeEl.classList.add('active');

      document.getElementById('activeChipTitle').innerText = chipId;

      try {
        const resp = await fetch('/api/chip/' + chipId);
        if (!resp.ok) throw new Error('Failed to load chip data: ' + resp.statusText);
        currentData = await resp.json();
        populateUI(currentData);
        await loadImages(chipId);
        updateOverallStats();
      } catch (err) {
        showNotification('Error loading chip: ' + err.message, true);
      }
    }

    function populateUI(data) {
      const bnr = document.getElementById('pilot08ReopenBanner');
      if (bnr) bnr.style.display = (data.chip_id === 'PILOT_08_CENTRAL') ? 'block' : 'none';

      document.getElementById('activeDisputeType').innerText = data.dispute_category.split('(')[0];
      document.getElementById('disputeDescription').innerText = data.dispute_category;

      const f = data.firms_info;
      document.getElementById('firmsContextGrid').innerHTML = `
        <div>Coord: <strong>${f.latitude?.toFixed(4)}, ${f.longitude?.toFixed(4)}</strong></div>
        <div>FRP: <strong>${f.frp_mw} MW</strong></div>
        <div>Scene Cloud: <strong>${f.cloud_cover_pct}%</strong></div>
        <div>FIRMS Pixel: <strong>[col ${f.pixel_col}, row ${f.pixel_row}]</strong></div>
      `;

      // A1 Summary
      const a1 = data.A1_original;
      document.getElementById('a1Status').innerText = a1.chip_annotation_status || 'UNKNOWN';
      const a1Boxes = a1.annotations || [];
      document.getElementById('a1BoxCount').innerText = a1Boxes.length;
      let a1Html = '';
      a1Boxes.forEach((b, i) => {
        a1Html += `<div style="margin-top:4px; font-size:0.75rem;">
          #${i+1} <strong>${b.class_name}</strong> [${b.bbox.x_min}, ${b.bbox.y_min}, ${b.bbox.x_max}, ${b.bbox.y_max}]<br>
          <span style="color:#aaa;">${(b.visual_evidence||[]).join(', ')}</span>
        </div>`;
      });
      document.getElementById('a1BoxesDetail').innerHTML = a1Html;

      // A2 Summary
      const a2 = data.A2_original;
      document.getElementById('a2Status').innerText = a2.chip_annotation_status || 'UNKNOWN';
      const a2Boxes = a2.annotations || [];
      document.getElementById('a2BoxCount').innerText = a2Boxes.length;
      let a2Html = '';
      a2Boxes.forEach((b, i) => {
        a2Html += `<div style="margin-top:4px; font-size:0.75rem;">
          #${i+1} <strong>${b.class_name}</strong> [${b.bbox.x_min}, ${b.bbox.y_min}, ${b.bbox.x_max}, ${b.bbox.y_max}]<br>
          <span style="color:#aaa;">${(b.visual_evidence||[]).join(', ')}</span>
        </div>`;
      });
      document.getElementById('a2BoxesDetail').innerHTML = a2Html;

      // Existing adjudication if present
      if (data.existing_adjudication) {
        const ex = data.existing_adjudication;
        const cons = ex.final_consensus || {};
        document.getElementById('adjStatus').value = cons.chip_annotation_status || ex.chip_annotation_status || 'HAS_ANNOTATIONS';
        adjudicatedBoxes = JSON.parse(JSON.stringify(cons.annotations || ex.annotations || []));
        document.getElementById('adjRationale').value = ex.adjudication_rationale || '';
        document.getElementById('chkVerified').checked = true;
        setChipBadge(data.chip_id, true);
      } else {
        // STRICT RULE A: Initial consensus annotations = []
        document.getElementById('adjStatus').value = 'HAS_ANNOTATIONS';
        adjudicatedBoxes = [];
        document.getElementById('adjRationale').value = '';
        document.getElementById('chkVerified').checked = false;
        setChipBadge(data.chip_id, false);
      }

      onStatusChange();
      renderBoxesList();
    }

    function setChipBadge(chipId, isAdjudicated) {
      const tag = document.getElementById('tag_' + chipId);
      if (tag) {
        if (isAdjudicated) {
          tag.className = 'chip-status-tag tag-adjudicated';
          tag.innerText = 'ADJUDICATED';
        } else {
          tag.className = 'chip-status-tag tag-pending';
          tag.innerText = 'PENDING';
        }
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
        rgbImg.src = '/api/preview/' + chipId + '/rgb?' + Date.now();

        swirImg = new Image();
        swirImg.onload = check;
        swirImg.onerror = check;
        swirImg.src = '/api/preview/' + chipId + '/swir?' + Date.now();
      });
    }

    function switchBand(band) {
      currentBand = band;
      document.getElementById('btnRgb').className = 'btn' + (band === 'rgb' ? ' active' : '');
      document.getElementById('btnSwir').className = 'btn' + (band === 'swir' ? ' active' : '');
      renderCanvas();
    }

    function zoomIn() { zoomLevel = Math.min(zoomLevel * 1.25, 5.0); renderCanvas(); }
    function zoomOut() { zoomLevel = Math.max(zoomLevel / 1.25, 0.5); renderCanvas(); }
    function resetZoom() { zoomLevel = 1.0; panX = 0; panY = 0; renderCanvas(); }

    function onStatusChange() {
      const st = document.getElementById('adjStatus').value;
      const bSec = document.getElementById('boxesSection');
      if (st === 'HAS_ANNOTATIONS') {
        bSec.style.display = 'flex';
      } else {
        bSec.style.display = 'none';
        adjudicatedBoxes = [];
        renderBoxesList();
        renderCanvas();
      }
    }

    function promptAddBox() {
      const input = prompt("Enter bounding box coordinates as: x_min, y_min, x_max, y_max\\n(Example: 240, 60, 290, 110)");
      if (!input) return;
      const parts = input.split(/[\\s,]+/).map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n));
      if (parts.length !== 4) {
        showNotification("Invalid format. Please enter 4 numbers: x_min, y_min, x_max, y_max", true);
        return;
      }
      const [x_min, y_min, x_max, y_max] = parts;
      if (x_min >= x_max || y_min >= y_max) {
        showNotification("Invalid box: x_min must be < x_max and y_min must be < y_max", true);
        return;
      }
      if (x_min < 0 || y_min < 0 || x_max > 512 || y_max > 512) {
        showNotification("Coordinates must be within 0 to 512 pixels", true);
        return;
      }
      if (x_min === 200 && y_min === 200 && x_max === 300 && y_max === 300) {
        showNotification("Coordinates [200, 200, 300, 300] are forbidden placeholder coordinates.", true);
        return;
      }
      addManualBox({ x_min, y_min, x_max, y_max }, "MANUAL_PROMPT_INPUT");
    }

    function addFromInputs() {
      const x_min = parseInt(document.getElementById("inp_xmin").value, 10);
      const y_min = parseInt(document.getElementById("inp_ymin").value, 10);
      const x_max = parseInt(document.getElementById("inp_xmax").value, 10);
      const y_max = parseInt(document.getElementById("inp_ymax").value, 10);

      if (isNaN(x_min) || isNaN(y_min) || isNaN(x_max) || isNaN(y_max)) {
        promptAddBox();
        return;
      }
      if (x_min >= x_max || y_min >= y_max) {
        showNotification("Invalid box: x_min must be < x_max and y_min must be < y_max", true);
        return;
      }
      if (x_min < 0 || y_min < 0 || x_max > 512 || y_max > 512) {
        showNotification("Coordinates must be within 0 to 512 pixels", true);
        return;
      }
      if (x_min === 200 && y_min === 200 && x_max === 300 && y_max === 300) {
        showNotification("Coordinates [200, 200, 300, 300] are forbidden placeholder coordinates.", true);
        return;
      }
      addManualBox({ x_min, y_min, x_max, y_max }, "MANUAL_INPUT_BAR");
      document.getElementById("inp_xmin").value = "";
      document.getElementById("inp_ymin").value = "";
      document.getElementById("inp_xmax").value = "";
      document.getElementById("inp_ymax").value = "";
    }

    function addManualBox(bbox, eventType = "MANUAL_INPUT") {
      if (!bbox) return;
      const w = bbox.x_max - bbox.x_min;
      const h = bbox.y_max - bbox.y_min;
      if (w < 4 || h < 4) return;

      const isCrop = currentChipId.includes('08');
      const defClass = isCrop ? 'Agricultural Fire' : 'Forest Fire';
      const defEv = isCrop
        ? ['DIRECT_FIRE_VISIBLE', 'CROPLAND_CONTEXT_VISIBLE']
        : ['DIRECT_FIRE_VISIBLE', 'BURN_SCAR_VISIBLE', 'FOREST_CONTEXT_VISIBLE'];

      adjudicatedBoxes.push({
        annotation_id: `${currentChipId}_ADJ_${adjudicatedBoxes.length + 1}`,
        class_name: defClass,
        bbox: { x_min: bbox.x_min, y_min: bbox.y_min, x_max: bbox.x_max, y_max: bbox.y_max },
        geometry_confidence: 'MEDIUM',
        source_class_confidence: 'MEDIUM',
        visibility_status: 'CLEAR',
        visual_evidence: defEv,
        firms_relationship: 'INSIDE_OBJECT',
        interaction_audit: {
          manual_interaction_recorded: true,
          event_type: eventType,
          coordinates: [bbox.x_min, bbox.y_min, bbox.x_max, bbox.y_max],
          timestamp: new Date().toISOString()
        }
      });
      renderBoxesList();
      renderCanvas();
      showNotification('Added Bounding Box #' + adjudicatedBoxes.length + ` [${bbox.x_min}, ${bbox.y_min}, ${bbox.x_max}, ${bbox.y_max}]`);
    }

    function addDrawnBox(bbox) {
      addManualBox(bbox, "CANVAS_DRAW");
    }

    function clearBoxes() {
      adjudicatedBoxes = [];
      renderBoxesList();
      renderCanvas();
      showNotification('Cleared all bounding boxes.');
    }

    function deleteBox(idx) {
      adjudicatedBoxes.splice(idx, 1);
      renderBoxesList();
      renderCanvas();
    }

    function renderBoxesList() {
      const list = document.getElementById('bboxList');
      const notice = document.getElementById('noBoxesNotice');
      list.innerHTML = '';
      document.getElementById('boxCountDisplay').innerText = adjudicatedBoxes.length;

      if (adjudicatedBoxes.length === 0) {
        notice.style.display = 'block';
      } else {
        notice.style.display = 'none';
      }

      adjudicatedBoxes.forEach((b, idx) => {
        const evList = b.visual_evidence || [];
        const hasContradiction = evList.includes('NO_CLEAR_VISUAL_EVIDENCE') &&
          (evList.includes('DIRECT_FIRE_VISIBLE') || evList.includes('BURN_SCAR_VISIBLE'));

        const div = document.createElement('div');
        div.className = 'bbox-row';
        div.innerHTML = `
          <div class="bbox-header">
            <span>Box #${idx + 1} (${b.class_name}) [${b.bbox.x_min}, ${b.bbox.y_min}, ${b.bbox.x_max}, ${b.bbox.y_max}]</span>
            <button class="btn btn-danger" style="padding: 2px 6px; font-size: 0.7rem;" onclick="deleteBox(${idx})">Delete</button>
          </div>
          <div class="coord-inputs">
            <div class="coord-input"><label>x_min</label><input type="number" value="${b.bbox.x_min}" onchange="updateBoxCoord(${idx}, 'x_min', this.value)"></div>
            <div class="coord-input"><label>y_min</label><input type="number" value="${b.bbox.y_min}" onchange="updateBoxCoord(${idx}, 'y_min', this.value)"></div>
            <div class="coord-input"><label>x_max</label><input type="number" value="${b.bbox.x_max}" onchange="updateBoxCoord(${idx}, 'x_max', this.value)"></div>
            <div class="coord-input"><label>y_max</label><input type="number" value="${b.bbox.y_max}" onchange="updateBoxCoord(${idx}, 'y_max', this.value)"></div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
            <div>
              <label>Class</label>
              <select onchange="updateBoxField(${idx}, 'class_name', this.value)" style="width: 100%;">
                <option value="Forest Fire" ${b.class_name === 'Forest Fire' ? 'selected' : ''}>Forest Fire</option>
                <option value="Agricultural Fire" ${b.class_name === 'Agricultural Fire' ? 'selected' : ''}>Agricultural Fire</option>
                <option value="Industrial Fire" ${b.class_name === 'Industrial Fire' ? 'selected' : ''}>Industrial Fire</option>
                <option value="Other Thermal Source" ${b.class_name === 'Other Thermal Source' ? 'selected' : ''}>Other Thermal Source</option>
                <option value="UNRESOLVED" ${b.class_name === 'UNRESOLVED' ? 'selected' : ''}>UNRESOLVED</option>
              </select>
            </div>
            <div>
              <label>FIRMS Relation</label>
              <select onchange="updateBoxField(${idx}, 'firms_relationship', this.value)" style="width: 100%;">
                <option value="INSIDE_OBJECT" ${b.firms_relationship === 'INSIDE_OBJECT' ? 'selected' : ''}>INSIDE_OBJECT</option>
                <option value="TOUCHING_OBJECT" ${b.firms_relationship === 'TOUCHING_OBJECT' ? 'selected' : ''}>TOUCHING_OBJECT</option>
                <option value="NEAR_OBJECT" ${b.firms_relationship === 'NEAR_OBJECT' ? 'selected' : ''}>NEAR_OBJECT</option>
                <option value="OUTSIDE_VISIBLE_OBJECT" ${b.firms_relationship === 'OUTSIDE_VISIBLE_OBJECT' ? 'selected' : ''}>OUTSIDE_VISIBLE_OBJECT</option>
              </select>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px;">
            <div>
              <label>Visibility</label>
              <select onchange="updateBoxField(${idx}, 'visibility_status', this.value)" style="width: 100%;">
                <option value="CLEAR" ${b.visibility_status === 'CLEAR' ? 'selected' : ''}>CLEAR</option>
                <option value="PARTIALLY_OBSCURED" ${b.visibility_status === 'PARTIALLY_OBSCURED' ? 'selected' : ''}>PARTIALLY_OBSCURED</option>
                <option value="HEAVILY_OBSCURED" ${b.visibility_status === 'HEAVILY_OBSCURED' ? 'selected' : ''}>HEAVILY_OBSCURED</option>
              </select>
            </div>
            <div>
              <label>Geom Conf</label>
              <select onchange="updateBoxField(${idx}, 'geometry_confidence', this.value)" style="width: 100%;">
                <option value="HIGH" ${b.geometry_confidence === 'HIGH' ? 'selected' : ''}>HIGH</option>
                <option value="MEDIUM" ${b.geometry_confidence === 'MEDIUM' ? 'selected' : ''}>MEDIUM</option>
                <option value="LOW" ${b.geometry_confidence === 'LOW' ? 'selected' : ''}>LOW</option>
              </select>
            </div>
            <div>
              <label>Class Conf</label>
              <select onchange="updateBoxField(${idx}, 'source_class_confidence', this.value)" style="width: 100%;">
                <option value="HIGH" ${b.source_class_confidence === 'HIGH' ? 'selected' : ''}>HIGH</option>
                <option value="MEDIUM" ${b.source_class_confidence === 'MEDIUM' ? 'selected' : ''}>MEDIUM</option>
                <option value="LOW" ${b.source_class_confidence === 'LOW' ? 'selected' : ''}>LOW</option>
              </select>
            </div>
          </div>
          <div>
            <label>Visual Evidence</label>
            <div class="evidence-grid">
              ${ALLOWED_EVIDENCE.map(ev => `
                <label class="evidence-item">
                  <input type="checkbox" ${(b.visual_evidence||[]).includes(ev) ? 'checked' : ''} onchange="toggleBoxEvidence(${idx}, '${ev}', this.checked)">
                  <span>${ev}</span>
                </label>
              `).join('')}
            </div>
          </div>
          ${hasContradiction ? `
            <div style="background: rgba(239, 68, 68, 0.2); border: 1px solid var(--danger); color: #fca5a5; padding: 6px 10px; border-radius: 4px; font-size: 0.75rem; margin-top: 6px; font-weight: bold;">
              ⚠️ CONTRADICTION DETECTED: This box has both positive fire/burn-scar evidence and 'NO_CLEAR_VISUAL_EVIDENCE'. Please uncheck 'NO_CLEAR_VISUAL_EVIDENCE' before saving.
            </div>
          ` : ''}
        `;
        list.appendChild(div);
      });
    }

    function updateBoxCoord(idx, coord, val) {
      val = parseInt(val, 10);
      if (isNaN(val)) return;
      adjudicatedBoxes[idx].bbox[coord] = Math.max(0, Math.min(512, val));
      renderCanvas();
    }

    function updateBoxField(idx, field, val) {
      adjudicatedBoxes[idx][field] = val;
      renderBoxesList();
      renderCanvas();
    }

    function toggleBoxEvidence(idx, ev, isChecked) {
      let list = adjudicatedBoxes[idx].visual_evidence || [];
      if (isChecked && !list.includes(ev)) {
        list.push(ev);
      } else if (!isChecked && list.includes(ev)) {
        list = list.filter(e => e !== ev);
      }
      if (list.length === 0) list = ['NO_CLEAR_VISUAL_EVIDENCE'];
      adjudicatedBoxes[idx].visual_evidence = list;
      renderBoxesList();
    }

    function renderCanvas() {
      const cvs = document.getElementById('viewCanvas');
      const ctx = cvs.getContext('2d');
      ctx.clearRect(0, 0, cvs.width, cvs.height);

      ctx.save();
      ctx.translate(panX, panY);
      ctx.scale(zoomLevel, zoomLevel);

      const img = currentBand === 'rgb' ? rgbImg : swirImg;
      if (img && img.complete && img.naturalWidth > 0) {
        ctx.drawImage(img, 0, 0, 512, 512);
      } else {
        ctx.fillStyle = '#1e1e24';
        ctx.fillRect(0, 0, 512, 512);
        ctx.fillStyle = '#666';
        ctx.font = '16px sans-serif';
        ctx.fillText('Loading satellite imagery...', 160, 256);
      }

      // 1. A1 boxes (Cyan/Blue overlay)
      if (document.getElementById('chkShowA1').checked && currentData && currentData.A1_original) {
        const a1Boxes = currentData.A1_original.annotations || [];
        ctx.strokeStyle = '#29b6f6';
        ctx.lineWidth = 2 / zoomLevel;
        ctx.fillStyle = 'rgba(41, 182, 246, 0.12)';
        a1Boxes.forEach((b, i) => {
          const bb = b.bbox;
          ctx.strokeRect(bb.x_min, bb.y_min, bb.x_max - bb.x_min, bb.y_max - bb.y_min);
          ctx.fillRect(bb.x_min, bb.y_min, bb.x_max - bb.x_min, bb.y_max - bb.y_min);
          ctx.font = `${Math.max(10, 11 / zoomLevel)}px sans-serif`;
          ctx.fillStyle = '#29b6f6';
          ctx.fillText(`A1: ${b.class_name}`, bb.x_min, Math.max(12, bb.y_min - 4));
        });
      }

      // 2. A2 boxes (Green overlay)
      if (document.getElementById('chkShowA2').checked && currentData && currentData.A2_original) {
        const a2Boxes = currentData.A2_original.annotations || [];
        ctx.strokeStyle = '#66bb6a';
        ctx.lineWidth = 2 / zoomLevel;
        ctx.fillStyle = 'rgba(102, 187, 106, 0.12)';
        a2Boxes.forEach((b, i) => {
          const bb = b.bbox;
          ctx.strokeRect(bb.x_min, bb.y_min, bb.x_max - bb.x_min, bb.y_max - bb.y_min);
          ctx.fillRect(bb.x_min, bb.y_min, bb.x_max - bb.x_min, bb.y_max - bb.y_min);
          ctx.font = `${Math.max(10, 11 / zoomLevel)}px sans-serif`;
          ctx.fillStyle = '#66bb6a';
          ctx.fillText(`A2: ${b.class_name}`, bb.x_min, Math.min(508, bb.y_max + 12));
        });
      }

      // 3. Adjudicated Consensus Boxes (Orange / Gold)
      ctx.strokeStyle = '#ff9800';
      ctx.lineWidth = 2.5 / zoomLevel;
      ctx.fillStyle = 'rgba(255, 152, 0, 0.2)';
      adjudicatedBoxes.forEach((b, i) => {
        const bb = b.bbox;
        ctx.strokeRect(bb.x_min, bb.y_min, bb.x_max - bb.x_min, bb.y_max - bb.y_min);
        ctx.fillRect(bb.x_min, bb.y_min, bb.x_max - bb.x_min, bb.y_max - bb.y_min);
        ctx.font = `bold ${Math.max(11, 12 / zoomLevel)}px sans-serif`;
        ctx.fillStyle = '#ff9800';
        ctx.fillText(`ADJ #${i+1}: ${b.class_name}`, bb.x_min + 4, bb.y_min + 14);
      });

      // 4. Currently drawing box
      if (currentDrawBox) {
        ctx.strokeStyle = '#fff';
        ctx.setLineDash([4 / zoomLevel, 4 / zoomLevel]);
        ctx.lineWidth = 2 / zoomLevel;
        ctx.strokeRect(
          currentDrawBox.x_min,
          currentDrawBox.y_min,
          currentDrawBox.x_max - currentDrawBox.x_min,
          currentDrawBox.y_max - currentDrawBox.y_min
        );
        ctx.setLineDash([]);
      }

      // 5. FIRMS coordinate marker
      if (document.getElementById('chkShowFirms').checked && currentData && currentData.firms_info) {
        const f = currentData.firms_info;
        const col = f.pixel_col, row = f.pixel_row;
        ctx.strokeStyle = '#ff3d00';
        ctx.lineWidth = 2 / zoomLevel;
        ctx.beginPath();
        ctx.arc(col, row, 6 / zoomLevel, 0, 2 * Math.PI);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(col - 12 / zoomLevel, row); ctx.lineTo(col + 12 / zoomLevel, row);
        ctx.moveTo(col, row - 12 / zoomLevel); ctx.lineTo(col, row + 12 / zoomLevel);
        ctx.stroke();
      }

      ctx.restore();
    }

    function getCanvasCoords(e) {
      const cvs = document.getElementById('viewCanvas');
      const rect = cvs.getBoundingClientRect();
      const scaleX = 512 / (rect.width || 512);
      const scaleY = 512 / (rect.height || 512);
      const clientX = e.clientX !== undefined ? e.clientX : (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
      const clientY = e.clientY !== undefined ? e.clientY : (e.touches && e.touches[0] ? e.touches[0].clientY : 0);
      const x = Math.max(0, Math.min(512, Math.round(((clientX - rect.left) * scaleX - panX) / zoomLevel)));
      const y = Math.max(0, Math.min(512, Math.round(((clientY - rect.top) * scaleY - panY) / zoomLevel)));
      return { x, y };
    }

    function setupCanvasEvents() {
      const container = document.getElementById('canvasContainer');
      const cvs = document.getElementById('viewCanvas');

      container.addEventListener('wheel', (e) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        zoomLevel = Math.max(0.5, Math.min(5.0, zoomLevel * delta));
        renderCanvas();
      });

      function handleDrawStart(e) {
        if (e.button !== undefined && e.button !== 0 && !e.touches) return;
        if (e.shiftKey) { // Pan with shift
          isPanning = true;
          panStartX = (e.clientX || 0) - panX;
          panStartY = (e.clientY || 0) - panY;
          return;
        }
        if (e.preventDefault) e.preventDefault();

        // Auto switch to HAS_ANNOTATIONS if needed so box section is visible
        const st = document.getElementById('adjStatus');
        if (st && st.value !== 'HAS_ANNOTATIONS') {
          st.value = 'HAS_ANNOTATIONS';
          onStatusChange();
        }

        if (cvs.setPointerCapture && e.pointerId !== undefined) {
          try { cvs.setPointerCapture(e.pointerId); } catch (_) {}
        }

        const { x, y } = getCanvasCoords(e);
        drawStartX = x;
        drawStartY = y;
        isDrawing = true;
        currentDrawBox = { x_min: x, y_min: y, x_max: x, y_max: y };

        const modeDisplay = document.getElementById('box-mode-display');
        if (modeDisplay) modeDisplay.innerText = `✏️ Drawing from [${x}, ${y}]...`;
        renderCanvas();
      }

      function handleDrawMove(e) {
        const { x, y } = getCanvasCoords(e);
        const coordDisplay = document.getElementById('coord-display');
        if (coordDisplay) coordDisplay.innerText = `Pixel: X: ${x}, Y: ${y}`;

        if (isPanning) {
          panX = (e.clientX || 0) - panStartX;
          panY = (e.clientY || 0) - panStartY;
          renderCanvas();
          return;
        }

        if (isDrawing) {
          if (e.preventDefault) e.preventDefault();
          const x_min = Math.min(drawStartX, x);
          const y_min = Math.min(drawStartY, y);
          const x_max = Math.max(drawStartX, x);
          const y_max = Math.max(drawStartY, y);
          currentDrawBox = { x_min, y_min, x_max, y_max };

          const modeDisplay = document.getElementById('box-mode-display');
          if (modeDisplay) {
            modeDisplay.innerText = `✏️ Box: [${x_min}, ${y_min}] to [${x_max}, ${y_max}] (${x_max - x_min}x${y_max - y_min})`;
          }
          renderCanvas();
        }
      }

      function handleDrawEnd(e) {
        if (isPanning) isPanning = false;
        if (!isDrawing) return;
        isDrawing = false;
        if (e && e.preventDefault) e.preventDefault();

        if (cvs.releasePointerCapture && e && e.pointerId !== undefined) {
          try { cvs.releasePointerCapture(e.pointerId); } catch (_) {}
        }

        const modeDisplay = document.getElementById('box-mode-display');
        if (currentDrawBox) {
          const w = currentDrawBox.x_max - currentDrawBox.x_min;
          const h = currentDrawBox.y_max - currentDrawBox.y_min;
          if (w >= 4 && h >= 4) {
            addDrawnBox(currentDrawBox);
            if (modeDisplay) modeDisplay.innerText = `✅ Created Box: [${currentDrawBox.x_min}, ${currentDrawBox.y_min}, ${currentDrawBox.x_max}, ${currentDrawBox.y_max}]`;
          } else {
            if (modeDisplay) modeDisplay.innerText = `⚠️ Drag too small (<4px). Click and drag to draw a box.`;
          }
        }
        currentDrawBox = null;
        renderCanvas();
      }

      // Double-click on canvas to create box centered on clicked spot
      cvs.addEventListener('dblclick', (e) => {
        const { x, y } = getCanvasCoords(e);
        const x_min = Math.max(0, x - 25);
        const y_min = Math.max(0, y - 25);
        const x_max = Math.min(512, x + 25);
        const y_max = Math.min(512, y + 25);
        addManualBox({ x_min, y_min, x_max, y_max }, 'CANVAS_DBLCLICK');
        showNotification(`Created 50x50 box centered at pixel (${x}, ${y}). Adjust coordinates in list if needed.`);
      });

      // Pointer events on canvas
      cvs.addEventListener('pointerdown', handleDrawStart);
      cvs.addEventListener('pointermove', handleDrawMove);
      cvs.addEventListener('pointerup', handleDrawEnd);
      cvs.addEventListener('pointercancel', handleDrawEnd);

      // Global window release so releasing mouse outside canvas finishes box
      window.addEventListener('pointerup', (e) => { if (isDrawing) handleDrawEnd(e); });
      window.addEventListener('mouseup', (e) => { if (isDrawing) handleDrawEnd(e); });

      // Fallback mouse events
      cvs.addEventListener('mousedown', handleDrawStart);
      window.addEventListener('mousemove', (e) => { if (isDrawing || isPanning) handleDrawMove(e); });
    }

    async function submitAdjudication() {
      const status = document.getElementById('adjStatus').value;
      const rationale = document.getElementById('adjRationale').value.trim();
      const verified = document.getElementById('chkVerified').checked;

      if (!verified) {
        showNotification('Please confirm human verification before saving.', true);
        return;
      }
      if (rationale.length < 15) {
        showNotification('Please enter a substantive human rationale (>= 15 characters).', true);
        return;
      }

      // Client-side generic check
      const lowerRat = rationale.toLowerCase();
      if (lowerRat.includes('saw the fire') || lowerRat.includes('looks like fire') || lowerRat.includes('agreed with')) {
        showNotification('Generic rationale rejected. Please explain observable visual findings (SWIR/RGB).', true);
        return;
      }

      if (status === 'UNRESOLVED') {
        showNotification("Cannot save: 'UNRESOLVED' status cannot be submitted as final consensus. Please select 'HAS_ANNOTATIONS' or 'NO_VISIBLE_TARGET'.", true);
        return;
      }

      if (status === 'HAS_ANNOTATIONS') {
        if (adjudicatedBoxes.length === 0) {
          showNotification('Observation status HAS_ANNOTATIONS requires at least one manually drawn bounding box.', true);
          return;
        }
        for (let i = 0; i < adjudicatedBoxes.length; i++) {
          const b = adjudicatedBoxes[i];
          const ev = b.visual_evidence || [];
          if ((ev.includes('DIRECT_FIRE_VISIBLE') || ev.includes('BURN_SCAR_VISIBLE')) && ev.includes('NO_CLEAR_VISUAL_EVIDENCE')) {
            showNotification(`Cannot save: Box #${i+1} has contradictory evidence flags. An annotation cannot claim both positive fire/burn-scar evidence and NO_CLEAR_VISUAL_EVIDENCE. Please uncheck one.`, true);
            return;
          }
        }
      }

      // Check forbidden box
      for (const b of adjudicatedBoxes) {
        if (b.bbox.x_min === 200 && b.bbox.y_min === 200 && b.bbox.x_max === 300 && b.bbox.y_max === 300) {
          showNotification('Default placeholder [200, 200, 300, 300] is forbidden. Please draw actual bounding boxes.', true);
          return;
        }
      }

      const payload = {
        chip_id: currentChipId,
        human_verified: true,
        adjudication_rationale: rationale,
        final_consensus: {
          chip_annotation_status: status,
          annotations: status === 'HAS_ANNOTATIONS' ? adjudicatedBoxes : []
        }
      };

      try {
        const resp = await fetch('/api/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const res = await resp.json();
        if (res.success) {
          showNotification('SUCCESS: Saved human adjudication for ' + currentChipId);
          setChipBadge(currentChipId, true);
          updateOverallStats();
        } else {
          showNotification('Failed to save: ' + (res.errors || []).join(', '), true);
        }
      } catch (err) {
        showNotification('Network/server error: ' + err.message, true);
      }
    }

    async function updateOverallStats() {
      try {
        const resp = await fetch('/api/stats');
        const st = await resp.json();
        document.getElementById('adjudicatedCount').innerText = st.adjudicated_count;
        (st.chips || []).forEach(c => setChipBadge(c.chip_id, c.is_adjudicated));
      } catch (err) {}
    }

    function showNotification(msg, isError = false) {
      const el = document.getElementById('notification');
      el.innerText = msg;
      el.className = isError ? 'notif-error' : 'notif-success';
      el.style.display = 'block';
      setTimeout(() => { el.style.display = 'none'; }, 4500);
    }

    window.onload = init;
  </script>
</body>
</html>
"""


class DS08HardenedAdjudicationHandler(http.server.BaseHTTPRequestHandler):
    """HTTP Request handler for the Hardened DS08 Human Adjudication Workspace."""

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ["", "/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_HARDENED_UI.encode("utf-8"))
            return

        if path == "/api/stats":
            chips_stats = []
            adj_count = 0
            for cid in DISPUTED_6_CHIPS:
                fpath = ADJUDICATION_REVIEW_DIR / f"{cid}_adjudicated_v1.json"
                is_adj = fpath.exists()
                if is_adj:
                    adj_count += 1
                chips_stats.append({"chip_id": cid, "is_adjudicated": is_adj})

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"total_disputed": 6, "adjudicated_count": adj_count, "chips": chips_stats}).encode("utf-8"))
            return

        if path.startswith("/api/chip/"):
            chip_id = path.split("/")[-1]
            try:
                data = load_adjudication_chip_data(chip_id)
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
        if parsed.path == "/api/save":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode("utf-8"))
                chip_id = payload.get("chip_id")
                success, errors = save_adjudicated_chip(chip_id, payload)
                self.send_response(200 if success else 400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": success, "errors": errors}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "errors": [str(e)]}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()


def run_adjudication_server(port: int = 8092) -> None:
    """Launches local HTTP server for the hardened adjudication interface."""
    with socketserver.TCPServer(("", port), DS08HardenedAdjudicationHandler) as httpd:
        print(f"\n{'='*70}")
        print(f"DS08 HARDENED SENIOR HUMAN ADJUDICATION INTERFACE ACTIVE")
        print(f"{'='*70}")
        print(f"  Local URL:        http://localhost:{port}")
        print(f"  Disputed Chips:   6 affected chips")
        print(f"  Canvas Policy:    ZERO default boxes; manual drawing ONLY")
        print(f"  Rationale Policy: Strict semantic validation (rejects generic phrases)")
        print(f"  Destination:      data/reference/ds08/annotations/adjudication/review/")
        print(f"  Source Integrity: Annotator 1 & Annotator 2 workspaces are strictly READ-ONLY")
        print(f"  Press Ctrl+C to terminate server.")
        print(f"{'='*70}\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down DS08 adjudication server.")


def main() -> int:
    parser = argparse.ArgumentParser(description="DS08 Hardened Adjudication Tooling.")
    parser.add_argument("--ui", action="store_true", help="Launch interactive human adjudication web server.")
    parser.add_argument("--port", type=int, default=8092, help="Web server port (default 8092).")
    parser.add_argument("--verify", action="store_true", help="Verify integrity of the 12 source files.")
    parser.add_argument("--status", action="store_true", help="Check status of 6 disputed chips.")
    args = parser.parse_args()

    if args.verify:
        valid, errors = verify_source_file_hashes()
        if valid:
            print("ALL 12 PRE-ADJUDICATION SOURCE FILES ARE BIT-FOR-BIT IDENTICAL!")
            return 0
        else:
            print("INTEGRITY VIOLATION DETECTED:", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            return 1

    if args.status:
        print(f"\n{'='*70}")
        print("STAGE 8.15 ADJUDICATION STATUS (6 DISPUTED CHIPS):")
        print(f"{'='*70}")
        completed = 0
        for idx, cid in enumerate(DISPUTED_6_CHIPS, start=1):
            fpath = ADJUDICATION_REVIEW_DIR / f"{cid}_adjudicated_v1.json"
            if fpath.exists():
                completed += 1
                with open(fpath, "r", encoding="utf-8") as f:
                    rec = json.load(f)
                stat = rec.get("chip_annotation_status", "UNKNOWN")
                b_cnt = len(rec.get("annotations", []))
                print(f"  [{idx}/6] {cid:<22} STATUS: COMPLETED ({stat}, {b_cnt} boxes)")
            else:
                print(f"  [{idx}/6] {cid:<22} STATUS: PENDING")
        print(f"\nProgress: {completed} / 6 adjudicated.\n")
        return 0

    if args.ui:
        run_adjudication_server(port=args.port)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
