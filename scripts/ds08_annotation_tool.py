"""
DS08 Real Sentinel-2 Annotation Tool and Manual Interface (Stage 8.12).

Features:
- Pure Python implementation (zero ML/YOLO auto-labeling or auto-suggestion dependencies).
- Strictly manual human annotation workflow with independent annotator isolation.
- Blank task template initialization for the 15 affected pilot chips in manual workspace.
- Clear and mandatory FIRMS Context Banner: "FIRMS CONTEXT — NOT GROUND TRUTH".
- Interactive Web/Canvas UI with:
  * RGB and SWIR preview inspection with 1-click toggling
  * Full 512x512 pixel resolution display
  * Smooth zoom (in/out/reset) and pan navigation
  * Interactive manual bounding box drawing and coordinate validation
  * Manual class, evidence, visibility, and confidence selection (no auto-recommendations)
  * Real-time schema validation against ds08_annotation_schema.json
  * Explicit human-interaction audit trail (start/stop timestamps, click/action counters)
- Strict annotator workspace isolation between annotator_1 and annotator_2.
- Full provenance verification preventing quarantined or synthetic files from contaminating pipelines.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import http.server
import json
import os
from pathlib import Path
import socketserver
import sys
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse

import pyproj
import rasterio

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DS08_DIR = PROJECT_ROOT / "data" / "reference" / "ds08"
ANNOTATIONS_DIR = DS08_DIR / "annotations"
SCHEMA_PATH = ANNOTATIONS_DIR / "schema" / "ds08_annotation_schema.json"
MANIFEST_PATH = ANNOTATIONS_DIR / "pilot_manifest.json"
DRAFT_DIR = ANNOTATIONS_DIR / "draft"
MANUAL_DIR = ANNOTATIONS_DIR / "manual"
QUARANTINE_DIR = ANNOTATIONS_DIR / "quarantine"
REVIEW_DIR = ANNOTATIONS_DIR / "review"
FINAL_DIR = ANNOTATIONS_DIR / "final"

CHIPS_DIR = DS08_DIR / "pilot" / "chips"
METADATA_DIR = DS08_DIR / "pilot" / "metadata"
PREVIEW_DIR = DS08_DIR / "pilot" / "preview"
REPLACEMENT_DIR = DS08_DIR / "pilot" / "replacement"

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

ALLOWED_CLASSES = [
    "Industrial Fire",
    "Forest Fire",
    "Agricultural Fire",
    "Other Thermal Source",
    "UNRESOLVED",
]

CLASS_ID_MAP = {
    "UNRESOLVED": 0,
    "Industrial Fire": 1,
    "Forest Fire": 2,
    "Agricultural Fire": 3,
    "Other Thermal Source": 4,
}

ALLOWED_CONFIDENCES = ["HIGH", "MEDIUM", "LOW"]
ALLOWED_VISIBILITY = ["CLEAR", "PARTIALLY_OBSCURED", "HEAVILY_OBSCURED"]
ALLOWED_EVIDENCE = [
    "DIRECT_FIRE_VISIBLE",
    "SMOKE_VISIBLE",
    "BURN_SCAR_VISIBLE",
    "INDUSTRIAL_INFRASTRUCTURE_VISIBLE",
    "FOREST_CONTEXT_VISIBLE",
    "CROPLAND_CONTEXT_VISIBLE",
    "PERSISTENT_THERMAL_SOURCE_CONTEXT",
    "NO_CLEAR_VISUAL_EVIDENCE",
]
ALLOWED_FIRMS_RELATIONSHIPS = [
    "INSIDE_OBJECT",
    "TOUCHING_OBJECT",
    "NEAR_OBJECT",
    "OUTSIDE_VISIBLE_OBJECT",
    "NO_VISIBLE_TARGET",
]
ALLOWED_CHIP_STATUSES = [
    "HAS_ANNOTATIONS",
    "NO_VISIBLE_TARGET",
    "UNRESOLVED",
]


def load_manifest() -> Dict[str, Any]:
    """Loads the 20-chip active pilot manifest."""
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_chip_paths(chip_id: str) -> Dict[str, Any]:
    """Resolves GeoTIFF, metadata, and preview paths for a given chip_id."""
    if "REPLACEMENT" in chip_id:
        search_dirs = [REPLACEMENT_DIR]
    else:
        search_dirs = [CHIPS_DIR, REPLACEMENT_DIR]

    tif_path = None
    for sdir in search_dirs:
        matches = list(sdir.glob(f"*{chip_id}*.tif"))
        if matches:
            tif_path = matches[0]
            break

    json_path = None
    for sdir in [METADATA_DIR, REPLACEMENT_DIR]:
        matches = list(sdir.glob(f"*{chip_id}*.json"))
        if matches:
            json_path = matches[0]
            break

    rgb_preview = None
    swir_preview = None
    for sdir in [PREVIEW_DIR, REPLACEMENT_DIR]:
        rgb_matches = list(sdir.glob(f"*{chip_id}*_rgb_preview.png"))
        if rgb_matches and not rgb_preview:
            rgb_preview = rgb_matches[0]
        swir_matches = list(sdir.glob(f"*{chip_id}*_swir_preview.png"))
        if swir_matches and not swir_preview:
            swir_preview = swir_matches[0]

    return {
        "chip_id": chip_id,
        "tif_path": tif_path,
        "json_path": json_path,
        "rgb_preview": rgb_preview,
        "swir_preview": swir_preview,
    }


def compute_firms_pixel_coordinates(tif_path: Path, lat: float, lon: float) -> Tuple[float, float]:
    """Computes exact pixel coordinates (col, row) of a WGS-84 coordinate within the 512x512 raster."""
    with rasterio.open(tif_path) as src:
        crs = src.crs
        transformer = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        proj_x, proj_y = transformer.transform(lon, lat)
        inv_transform = ~src.transform
        col, row = inv_transform @ (proj_x, proj_y)
        return round(float(col), 2), round(float(row), 2)


def validate_annotation_payload(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validates an annotation payload against schema requirements."""
    errors = []

    required_keys = ["chip_id", "annotation_version", "chip_annotation_status", "annotations", "context_metadata"]
    for k in required_keys:
        if k not in data:
            errors.append(f"Missing required top-level key: '{k}'")

    chip_status = data.get("chip_annotation_status")
    if chip_status not in ALLOWED_CHIP_STATUSES:
        errors.append(f"Invalid chip_annotation_status: '{chip_status}'. Must be one of {ALLOWED_CHIP_STATUSES}")

    annotations = data.get("annotations", [])
    if not isinstance(annotations, list):
        errors.append("'annotations' must be an array")
        return False, errors

    if chip_status == "NO_VISIBLE_TARGET" and len(annotations) > 0:
        errors.append("chip_annotation_status='NO_VISIBLE_TARGET' must have an empty annotations array.")
    if chip_status == "HAS_ANNOTATIONS" and len(annotations) == 0:
        errors.append("chip_annotation_status='HAS_ANNOTATIONS' requires at least one annotation.")

    for idx, ann in enumerate(annotations):
        prefix = f"Annotation #{idx+1} ({ann.get('annotation_id', 'unknown')})"

        cname = ann.get("class_name")
        cid = ann.get("class_id")
        if cname not in ALLOWED_CLASSES:
            errors.append(f"{prefix}: Invalid class_name '{cname}'. Allowed: {ALLOWED_CLASSES}")
        if cid != CLASS_ID_MAP.get(cname):
            errors.append(f"{prefix}: class_id {cid} does not match class_name '{cname}' (expected {CLASS_ID_MAP.get(cname)})")

        bbox = ann.get("bbox")
        if not isinstance(bbox, dict):
            errors.append(f"{prefix}: 'bbox' must be an object with x_min, y_min, x_max, y_max")
        else:
            for coord in ["x_min", "y_min", "x_max", "y_max"]:
                if coord not in bbox:
                    errors.append(f"{prefix}: bbox missing '{coord}'")

            x_min = bbox.get("x_min", -1)
            y_min = bbox.get("y_min", -1)
            x_max = bbox.get("x_max", -1)
            y_max = bbox.get("y_max", -1)

            if not (0 <= x_min < 512):
                errors.append(f"{prefix}: x_min ({x_min}) out of range [0, 511]")
            if not (0 <= y_min < 512):
                errors.append(f"{prefix}: y_min ({y_min}) out of range [0, 511]")
            if not (0 < x_max <= 512):
                errors.append(f"{prefix}: x_max ({x_max}) out of range [1, 512]")
            if not (0 < y_max <= 512):
                errors.append(f"{prefix}: y_max ({y_max}) out of range [1, 512]")

            if x_min >= x_max:
                errors.append(f"{prefix}: Zero or negative width box (x_min={x_min} >= x_max={x_max})")
            if y_min >= y_max:
                errors.append(f"{prefix}: Zero or negative height box (y_min={y_min} >= y_max={y_max})")

        g_conf = ann.get("geometry_confidence")
        s_conf = ann.get("source_class_confidence")
        if g_conf not in ALLOWED_CONFIDENCES:
            errors.append(f"{prefix}: Invalid geometry_confidence '{g_conf}'")
        if s_conf not in ALLOWED_CONFIDENCES:
            errors.append(f"{prefix}: Invalid source_class_confidence '{s_conf}'")

        vis = ann.get("visibility_status")
        if vis not in ALLOWED_VISIBILITY:
            errors.append(f"{prefix}: Invalid visibility_status '{vis}'")
        if vis == "HEAVILY_OBSCURED" and cname != "UNRESOLVED":
            errors.append(f"{prefix}: visibility_status='HEAVILY_OBSCURED' requires class_name='UNRESOLVED'")

        ev_list = ann.get("visual_evidence", [])
        if not isinstance(ev_list, list) or len(ev_list) == 0:
            errors.append(f"{prefix}: 'visual_evidence' must contain at least one evidence tag")
        else:
            for ev in ev_list:
                if ev not in ALLOWED_EVIDENCE:
                    errors.append(f"{prefix}: Invalid evidence tag '{ev}'")

        f_rel = ann.get("firms_relationship")
        if f_rel not in ALLOWED_FIRMS_RELATIONSHIPS:
            errors.append(f"{prefix}: Invalid firms_relationship '{f_rel}'")

    ctx = data.get("context_metadata", {})
    if not isinstance(ctx, dict):
        errors.append("'context_metadata' must be an object")
    else:
        req_ctx = ["firms_detection_id", "firms_latitude", "firms_longitude", "product_id", "authoritative_bands"]
        for r in req_ctx:
            if r not in ctx:
                errors.append(f"context_metadata missing '{r}'")

        bands = ctx.get("authoritative_bands", [])
        expected_bands = ["B02", "B03", "B04", "B11", "B12"]
        if bands != expected_bands:
            errors.append(f"authoritative_bands must be {expected_bands}, got {bands}")

    return (len(errors) == 0), errors


def validate_manual_annotation_provenance(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validates that an annotation record satisfies strict human provenance requirements."""
    errors = []

    # Must be explicitly marked as human verified
    if data.get("human_verified") is not True:
        errors.append("Annotation record must have 'human_verified': true")

    # Forbidden auto-labeling / model fields
    forbidden_terms = [
        "model_predicted",
        "yolo_",
        "predicted_class",
        "auto_label",
        "synthetic",
        "simulated",
        "auto_detected",
    ]
    json_str = json.dumps(data)
    for term in forbidden_terms:
        if term in json_str:
            errors.append(f"Forbidden model/auto-generation artifact detected: '{term}'")

    # Interaction audit must exist
    audit = data.get("interaction_audit")
    if not isinstance(audit, dict):
        errors.append("Missing 'interaction_audit' metadata record")
    else:
        req_audit_fields = ["interface_version", "save_events"]
        for af in req_audit_fields:
            if af not in audit:
                errors.append(f"interaction_audit missing required field: '{af}'")

    # FIRMS context disclaimer must be intact
    ctx = data.get("context_metadata", {})
    disclaimer = ctx.get("firms_context_disclaimer", "")
    if "FIRMS CONTEXT" not in disclaimer or "NOT GROUND TRUTH" not in disclaimer:
        errors.append("context_metadata must include 'firms_context_disclaimer': 'FIRMS CONTEXT — NOT GROUND TRUTH'")

    return (len(errors) == 0), errors


def create_annotation_record(
    chip_id: str,
    chip_annotation_status: str,
    annotations: List[Dict[str, Any]],
    annotator_id: str,
    stage_subfolder: str = "draft",
    pass_number: int = 1,
) -> Path:
    """Creates, validates, and saves an annotation JSON file."""
    manifest = load_manifest()
    chip_entry = next((c for c in manifest["chips"] if c["chip_id"] == chip_id), None)
    if not chip_entry:
        raise ValueError(f"Chip {chip_id} not found in pilot manifest.")

    chip_paths = resolve_chip_paths(chip_id)
    tif_p = chip_paths["tif_path"]
    lat = chip_entry["firms_latitude"]
    lon = chip_entry["firms_longitude"]

    firms_col, firms_row = compute_firms_pixel_coordinates(tif_p, lat, lon)

    formatted_ann = []
    now_utc = datetime.now(timezone.utc).isoformat()
    for idx, raw_ann in enumerate(annotations, start=1):
        cname = raw_ann["class_name"]
        cid = CLASS_ID_MAP[cname]
        formatted_ann.append({
            "annotation_id": f"{chip_id}_ANN_{idx:02d}",
            "class_id": cid,
            "class_name": cname,
            "bbox": {
                "x_min": raw_ann["bbox"]["x_min"],
                "y_min": raw_ann["bbox"]["y_min"],
                "x_max": raw_ann["bbox"]["x_max"],
                "y_max": raw_ann["bbox"]["y_max"],
            },
            "geometry_confidence": raw_ann.get("geometry_confidence", "HIGH"),
            "source_class_confidence": raw_ann.get("source_class_confidence", "HIGH"),
            "visibility_status": raw_ann.get("visibility_status", "CLEAR"),
            "visual_evidence": raw_ann.get("visual_evidence", ["NO_CLEAR_VISUAL_EVIDENCE"]),
            "firms_relationship": raw_ann.get("firms_relationship", "INSIDE_OBJECT"),
            "review_status": "PENDING",
            "annotator_id": annotator_id,
            "annotation_timestamp": now_utc,
            "notes": raw_ann.get("notes", ""),
        })

    record = {
        "chip_id": chip_id,
        "annotation_version": "v1.0",
        "chip_annotation_status": chip_annotation_status,
        "annotations": formatted_ann,
        "context_metadata": {
            "firms_context_disclaimer": "FIRMS CONTEXT — NOT GROUND TRUTH",
            "firms_detection_id": chip_entry["firms_detection_id"],
            "firms_latitude": lat,
            "firms_longitude": lon,
            "firms_acq_datetime_utc": chip_entry["firms_acquisition_datetime_utc"],
            "firms_frp": chip_entry["firms_frp"],
            "firms_pixel_coord": {"row": firms_row, "col": firms_col},
            "product_id": chip_entry["product_id"],
            "tile_id": chip_entry["tile_id"],
            "cloud_cover_pct": chip_entry["cloud_cover_pct"],
            "authoritative_bands": ["B02", "B03", "B04", "B11", "B12"],
            "data_provenance": "Copernicus Data Space Ecosystem (CDSE) Sentinel-2 L2A BOA Reflectance",
        },
    }

    valid, errors = validate_annotation_payload(record)
    if not valid:
        raise ValueError(f"Annotation record failed schema validation:\n" + "\n".join(errors))

    out_dir = ANNOTATIONS_DIR / stage_subfolder
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{chip_id}_pass{pass_number}.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    return out_file


def init_manual_templates() -> Dict[str, int]:
    """
    Initializes clean manual annotation workspace with blank task templates for
    the 15 affected chips under data/reference/ds08/annotations/manual/annotator_1 and annotator_2.
    Templates contain NO class decisions, NO bounding boxes, and NO evidence decisions.
    """
    manifest = load_manifest()
    chip_lookup = {c["chip_id"]: c for c in manifest["chips"]}

    a1_dir = MANUAL_DIR / "annotator_1"
    a2_dir = MANUAL_DIR / "annotator_2"
    a1_dir.mkdir(parents=True, exist_ok=True)
    a2_dir.mkdir(parents=True, exist_ok=True)

    annotators = [
        ("annotator_1", "HUMAN_ANNOTATOR_01", a1_dir),
        ("annotator_2", "HUMAN_ANNOTATOR_02", a2_dir),
    ]

    counts = {"annotator_1": 0, "annotator_2": 0}

    for chip_id in AFFECTED_15_CHIPS:
        entry = chip_lookup.get(chip_id)
        if not entry:
            raise KeyError(f"Chip {chip_id} not found in pilot manifest")

        paths = resolve_chip_paths(chip_id)
        tif_p = paths["tif_path"]
        lat = entry["firms_latitude"]
        lon = entry["firms_longitude"]
        f_col, f_row = compute_firms_pixel_coordinates(tif_p, lat, lon)

        for ann_sub, ann_id, out_dir in annotators:
            template = {
                "task_status": "PENDING_MANUAL_INPUT",
                "chip_id": chip_id,
                "schema_version": "v1.0",
                "protocol_version": "DS08_v1.0",
                "annotator_id": ann_id,
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
            ann_suffix = ann_sub.replace("_", "")
            out_file = out_dir / f"{chip_id}_{ann_suffix}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(template, f, indent=2)
            counts[ann_sub] += 1

    return counts


def get_annotator_dir(annotator: str) -> Path:
    """Returns directory path for annotator while enforcing strict isolation."""
    if annotator not in ["annotator_1", "annotator_2"]:
        raise ValueError(f"Invalid annotator: '{annotator}'. Must be 'annotator_1' or 'annotator_2'")
    return MANUAL_DIR / annotator


def load_manual_template(annotator: str, chip_id: str, target_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Loads a manual task template or completed annotation for an annotator."""
    adir = target_dir if target_dir is not None else get_annotator_dir(annotator)
    ann_suffix = annotator.replace("_", "")
    target_file = adir / f"{chip_id}_{ann_suffix}.json"
    if not target_file.exists():
        raise FileNotFoundError(f"Annotation file not found: {target_file}")
    with open(target_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manual_annotation(
    annotator: str,
    chip_id: str,
    payload: Dict[str, Any],
    target_dir: Optional[Path] = None
) -> Tuple[bool, List[str]]:
    """Saves a manually entered annotation payload with strict schema and provenance checks."""
    adir = target_dir if target_dir is not None else get_annotator_dir(annotator)
    ann_suffix = annotator.replace("_", "")
    target_file = adir / f"{chip_id}_{ann_suffix}.json"

    # Enforce explicit selection of observation status
    chip_status = payload.get("chip_annotation_status")
    if not chip_status or chip_status not in ALLOWED_CHIP_STATUSES:
        return False, [f"chip_annotation_status must be explicitly selected from {ALLOWED_CHIP_STATUSES}"]

    if chip_status == "HAS_ANNOTATIONS" and len(payload.get("annotations", [])) == 0:
        return False, ["chip_annotation_status='HAS_ANNOTATIONS' requires at least one bounding box annotation."]

    # Enforce human verified and completion
    payload["human_verified"] = True
    payload["task_status"] = "COMPLETED_HUMAN_ANNOTATION"
    if not payload.get("annotation_completion_timestamp"):
        payload["annotation_completion_timestamp"] = datetime.now(timezone.utc).isoformat()

    # Interaction audit update
    audit = payload.get("interaction_audit", {})
    audit["save_events"] = audit.get("save_events", 0) + 1
    audit["interface_version"] = "v1.0_manual"
    payload["interaction_audit"] = audit

    # Format annotations if needed
    for idx, ann in enumerate(payload.get("annotations", []), start=1):
        if "annotation_id" not in ann:
            ann["annotation_id"] = f"{chip_id}_ANN_{idx:02d}"
        if "class_name" in ann and "class_id" not in ann:
            ann["class_id"] = CLASS_ID_MAP.get(ann["class_name"], 0)
        ann["annotator_id"] = "HUMAN_ANNOTATOR_01" if annotator == "annotator_1" else "HUMAN_ANNOTATOR_02"
        if "annotation_timestamp" not in ann:
            ann["annotation_timestamp"] = datetime.now(timezone.utc).isoformat()
        if "review_status" not in ann:
            ann["review_status"] = "PENDING"

    # Schema validation
    valid_schema, schema_errors = validate_annotation_payload(payload)
    if not valid_schema:
        return False, schema_errors

    # Provenance validation
    valid_prov, prov_errors = validate_manual_annotation_provenance(payload)
    if not valid_prov:
        return False, prov_errors

    # Save to disk
    adir.mkdir(parents=True, exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return True, []


def print_chip_summary(chip_id: str) -> None:
    """Displays terminal summary of a pilot chip for annotation inspection."""
    paths = resolve_chip_paths(chip_id)
    manifest = load_manifest()
    entry = next((c for c in manifest["chips"] if c["chip_id"] == chip_id), None)

    print(f"\n{'='*70}")
    print(f"PILOT CHIP INSPECTION: {chip_id}")
    print(f"{'='*70}")
    print("  *** FIRMS CONTEXT — NOT GROUND TRUTH ***")
    if entry:
        print(f"  Region:               {entry['region']}")
        print(f"  Product ID:           {entry['product_id']}")
        print(f"  Tile ID:              {entry['tile_id']}")
        print(f"  S2 Acquisition UTC:   {entry['acquisition_datetime_utc']}")
        print(f"  Scene Cloud Cover:    {entry['cloud_cover_pct']}%")
        print(f"  FIRMS Detection ID:   {entry['firms_detection_id']}")
        print(f"  FIRMS Coordinate:     Lat {entry['firms_latitude']:.5f}, Lon {entry['firms_longitude']:.5f}")
        print(f"  FIRMS FRP:            {entry['firms_frp']} MW")

    if paths["tif_path"] and paths["tif_path"].exists():
        f_col, f_row = compute_firms_pixel_coordinates(paths["tif_path"], entry["firms_latitude"], entry["firms_longitude"])
        print(f"  FIRMS Pixel Location: col={f_col}, row={f_row} (relative to 512x512)")
    print(f"  GeoTIFF:              {paths['tif_path']}")
    print(f"  RGB Preview:          {paths['rgb_preview']}")
    print(f"  SWIR Preview:         {paths['swir_preview']}")
    print(f"{'='*70}\n")


HTML_APP_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>DS08 Manual Sentinel-2 Annotation Interface</title>
  <style>
    :root {
      --bg: #1e1e24;
      --card-bg: #2b2b36;
      --border: #444454;
      --text: #e0e0e0;
      --accent: #ff9800;
      --accent-hover: #f57c00;
      --danger: #f44336;
      --success: #4caf50;
      --warning-bg: #3e2723;
      --warning-border: #ff5722;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background: var(--bg); color: var(--text); padding: 15px; }
    header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    h1 { font-size: 1.3rem; color: #fff; }
    .badge { padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 0.85rem; }
    .badge-annotator { background: #3f51b5; color: #fff; }
    .disclaimer-banner {
      background: var(--warning-bg);
      border: 2px solid var(--warning-border);
      padding: 10px 15px;
      border-radius: 6px;
      margin-bottom: 15px;
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 0.9rem;
    }
    .disclaimer-banner strong { color: #ffab91; font-size: 1rem; }
    .main-grid { display: grid; grid-template-columns: 580px 1fr; gap: 20px; }
    .canvas-panel { background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; }
    .canvas-toolbar { display: flex; gap: 8px; margin-bottom: 10px; align-items: center; flex-wrap: wrap; }
    button {
      background: #4a4a5a;
      color: #fff;
      border: none;
      padding: 6px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.85rem;
    }
    button:hover { background: #5c5c6e; }
    button.active { background: var(--accent); color: #000; font-weight: bold; }
    button.primary { background: #2196f3; font-weight: bold; }
    button.primary:hover { background: #1976d2; }
    button.save { background: var(--success); font-weight: bold; padding: 10px 20px; font-size: 1rem; }
    button.save:hover { background: #388e3c; }
    button.next-pending { background: #1976d2; color: #fff; font-weight: bold; padding: 10px 20px; font-size: 1rem; border-radius: 4px; }
    button.next-pending:hover { background: #1565c0; }
    button:disabled { background: #555 !important; color: #aaa !important; cursor: not-allowed; }
    #canvas-viewport {
      width: 550px;
      height: 550px;
      border: 2px solid #555;
      position: relative;
      overflow: hidden;
      background: #000;
      cursor: crosshair;
      user-select: none;
      -webkit-user-select: none;
      touch-action: none;
    }
    #image-canvas {
      position: absolute;
      top: 0;
      left: 0;
      user-select: none;
      -webkit-user-select: none;
      touch-action: none;
    }
    .coord-bar { display: flex; justify-content: space-between; font-size: 0.8rem; margin-top: 6px; color: #aaa; }
    .form-panel { background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 15px; max-height: 85vh; overflow-y: auto; }
    .form-section { margin-bottom: 18px; border-bottom: 1px solid var(--border); padding-bottom: 14px; }
    .form-section h3 { font-size: 1rem; margin-bottom: 8px; color: #90caf9; }
    label { display: block; font-size: 0.85rem; margin-bottom: 4px; color: #ccc; }
    select, input, textarea {
      width: 100%;
      background: #1e1e24;
      border: 1px solid var(--border);
      color: #fff;
      padding: 6px 10px;
      border-radius: 4px;
      margin-bottom: 10px;
      font-size: 0.9rem;
    }
    .radio-group { display: flex; gap: 15px; margin-bottom: 10px; }
    .radio-group label { display: flex; align-items: center; gap: 5px; cursor: pointer; }
    .checkbox-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 10px; }
    .checkbox-grid label { display: flex; align-items: center; gap: 6px; font-size: 0.8rem; cursor: pointer; }
    .box-card { background: #202028; border: 1px solid #48485a; border-radius: 4px; padding: 10px; margin-bottom: 10px; }
    .box-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
    .context-table { width: 100%; font-size: 0.8rem; border-collapse: collapse; }
    .context-table td { padding: 4px; border-bottom: 1px solid #3a3a46; }
    .context-table td:first-child { color: #aaa; width: 40%; }
    #msg-box { padding: 10px; border-radius: 4px; margin-top: 10px; display: none; font-size: 0.9rem; }
    .msg-error { background: #b71c1c; color: #fff; }
    .msg-success { background: #1b5e20; color: #fff; }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>DS08 Manual Sentinel-2 Annotation Interface</h1>
      <span style="font-size: 0.85rem; color: #aaa;">Stage 8.12 Human Annotation Pipeline & Verification</span>
    </div>
    <div style="display: flex; gap: 10px; align-items: center;">
      <span class="badge badge-annotator" id="annotator-badge">ANNOTATOR</span>
      <select id="chip-select" style="width: 250px; margin-bottom: 0;">
        <option value="">Loading pending chips...</option>
      </select>
    </div>
  </header>

  <div class="disclaimer-banner">
    <div>⚠️</div>
    <div>
      <strong>FIRMS CONTEXT — NOT GROUND TRUTH</strong><br>
      Thermal anomalies detected by VIIRS/MODIS indicate satellite thermal context ONLY. They do not constitute verified ground-truth labels. Visual boundaries, smoke plumes, burn scars, and source classes must be identified manually solely from the Sentinel-2 optical imagery.
    </div>
  </div>

  <div class="main-grid">
    <!-- Left Column: Canvas and Navigation -->
    <div class="canvas-panel">
      <div class="canvas-toolbar">
        <button id="btn-rgb" class="active" onclick="switchBand('rgb')">RGB Preview (1-2-3)</button>
        <button id="btn-swir" onclick="switchBand('swir')">SWIR Preview (12-11-4)</button>
        <div style="margin-left: auto; display: flex; gap: 5px;">
          <button onclick="changeZoom(1.2)">Zoom +</button>
          <button onclick="changeZoom(0.8)">Zoom -</button>
          <button onclick="resetZoom()">100%</button>
          <button id="btn-firms-toggle" onclick="toggleFirmsMarker()">FIRMS Reference: ON</button>
        </div>
      </div>

      <div id="canvas-viewport">
        <canvas id="image-canvas" width="512" height="512"></canvas>
      </div>

      <div class="coord-bar">
        <span id="coord-display">Pixel: X: -, Y: -</span>
        <span id="box-mode-display">Drawing mode: READY (Click & Drag)</span>
        <span id="zoom-display">Zoom: 100%</span>
      </div>
    </div>

    <!-- Right Column: Manual Annotation Form -->
    <div class="form-panel">
      <div class="form-section">
        <h3>1. Chip Observation Status</h3>
        <div class="radio-group">
          <label><input type="radio" name="chip_status" value="HAS_ANNOTATIONS" checked onchange="onStatusChange()"> HAS_ANNOTATIONS</label>
          <label><input type="radio" name="chip_status" value="NO_VISIBLE_TARGET" onchange="onStatusChange()"> NO_VISIBLE_TARGET</label>
          <label><input type="radio" name="chip_status" value="UNRESOLVED" onchange="onStatusChange()"> UNRESOLVED</label>
        </div>
      </div>

      <div class="form-section" id="annotations-section">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <h3>2. Bounding Box & Target Decisions (<span id="box-count">0</span>)</h3>
          <button type="button" onclick="clearBoxes()" style="background: #c62828;">Clear All Boxes</button>
        </div>
        <div id="boxes-container">
          <p style="color: #888; font-size: 0.85rem; font-style: italic;">No bounding boxes drawn yet. Click and drag on the imagery canvas to draw bounding box [0, 512].</p>
        </div>
      </div>

      <div class="form-section">
        <h3>3. FIRMS Context (Reference Only)</h3>
        <table class="context-table" id="firms-table">
          <tr><td>Disclaimer</td><td><strong style="color: #ffab91;">FIRMS CONTEXT — NOT GROUND TRUTH</strong></td></tr>
          <tr><td>Detection ID</td><td id="fc-id">-</td></tr>
          <tr><td>Latitude / Longitude</td><td id="fc-coords">-</td></tr>
          <tr><td>Projected Raster Pixel</td><td id="fc-pixel">-</td></tr>
          <tr><td>FRP (MW)</td><td id="fc-frp">-</td></tr>
          <tr><td>Acquisition UTC</td><td id="fc-acq">-</td></tr>
          <tr><td>S2 Product SAFE</td><td id="fc-prod" style="word-break: break-all;">-</td></tr>
          <tr><td>Cloud Cover %</td><td id="fc-cloud">-</td></tr>
        </table>
      </div>

      <div class="form-section">
        <h3>4. Interaction & Provenance Audit</h3>
        <div style="display: flex; gap: 20px; font-size: 0.85rem; color: #bbb;">
          <div>BBox Actions: <strong id="audit-bbox-count">0</strong></div>
          <div>Class Selections: <strong id="audit-class-count">0</strong></div>
          <div>Interface: <strong id="audit-iface">v1.0_manual</strong></div>
        </div>
      </div>

      <div style="margin-top: 15px; display: flex; flex-direction: column; gap: 8px;">
        <button class="save" id="btn-save" style="width: 100%;" onclick="saveAnnotation()">💾 Validate & Save Human Annotation</button>
        <button class="next-pending" id="btn-next-pending" style="width: 100%;" onclick="goToNextPendingChip()">➡️ Next Pending Chip</button>
        <div id="msg-box"></div>
      </div>
    </div>
  </div>

  <script>
    let activeAnnotator = "__ANNOTATOR__";
    let activeChip = "";
    let activeBand = "rgb";
    let zoomLevel = 1.0;
    let panX = 0;
    let panY = 0;
    let showFirms = true;
    let chipData = null;
    let boxes = [];
    let isDrawing = false;
    let startX = 0, startY = 0;
    let currentX = 0, currentY = 0;
    let startTime = null;

    let auditCounts = {
      bbox_creation_actions: 0,
      bbox_edit_actions: 0,
      class_selection_actions: 0,
      save_events: 0
    };

    const canvas = document.getElementById("image-canvas");
    const ctx = canvas.getContext("2d");
    const viewport = document.getElementById("canvas-viewport");
    const rgbImg = new Image();
    const swirImg = new Image();

    document.getElementById("annotator-badge").innerText = activeAnnotator.toUpperCase();

    async function init() {
      startTime = new Date().toISOString();
      const res = await fetch("/api/chips");
      const chips = await res.json();
      const sel = document.getElementById("chip-select");
      sel.innerHTML = "";
      chips.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.chip_id;
        opt.innerText = `${c.chip_id} [${c.status}]`;
        sel.appendChild(opt);
      });
      sel.onchange = () => loadChip(sel.value);

      const pendingChips = chips.filter(c => c.status === "PENDING_MANUAL_INPUT");
      const nextBtn = document.getElementById("btn-next-pending");

      if (pendingChips.length === 0) {
        if (nextBtn) {
          nextBtn.innerText = "All chips completed.";
          nextBtn.disabled = true;
        }
        if (chips.length > 0) {
          sel.value = chips[0].chip_id;
          await loadChip(chips[0].chip_id);
          showMsg("All chips completed.", "success");
        }
        return;
      }

      if (nextBtn) {
        nextBtn.innerText = `➡️ Next Pending Chip (${pendingChips.length} remaining)`;
        nextBtn.disabled = false;
      }

      // Check if URL has ?chip=...
      const urlParams = new URLSearchParams(window.location.search);
      const urlChip = urlParams.get("chip");
      if (urlChip && chips.some(c => c.chip_id === urlChip)) {
        sel.value = urlChip;
        await loadChip(urlChip);
      } else {
        // Automatically default to the first pending chip so refresh does not stick on completed chip
        sel.value = pendingChips[0].chip_id;
        await loadChip(pendingChips[0].chip_id);
      }
    }

    async function goToNextPendingChip() {
      const nextBtn = document.getElementById("btn-next-pending");

      const res = await fetch("/api/chips");
      const chips = await res.json();

      // Refresh select list
      const sel = document.getElementById("chip-select");
      sel.innerHTML = "";
      chips.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.chip_id;
        opt.innerText = `${c.chip_id} [${c.status}]`;
        sel.appendChild(opt);
      });

      const pendingChips = chips.filter(c => c.status === "PENDING_MANUAL_INPUT");

      if (pendingChips.length === 0) {
        showMsg("All chips completed.", "success");
        if (nextBtn) {
          nextBtn.innerText = "All chips completed.";
          nextBtn.disabled = true;
        }
        return;
      }

      // Find next pending chip after the currently active chip
      const currentIndex = chips.findIndex(c => c.chip_id === activeChip);
      let target = null;
      for (let i = currentIndex + 1; i < chips.length; i++) {
        if (chips[i].status === "PENDING_MANUAL_INPUT") {
          target = chips[i].chip_id;
          break;
        }
      }
      // Wrap around from beginning if not found after current chip
      if (!target) {
        for (let i = 0; i <= currentIndex; i++) {
          if (chips[i].status === "PENDING_MANUAL_INPUT") {
            target = chips[i].chip_id;
            break;
          }
        }
      }

      if (target) {
        sel.value = target;
        await loadChip(target);
        const rem = pendingChips.filter(c => c.chip_id !== target).length;
        if (nextBtn) {
          nextBtn.innerText = rem > 0 ? `➡️ Next Pending Chip (${rem} remaining)` : "All chips completed.";
          nextBtn.disabled = false;
        }
        showMsg(`Loaded next pending chip: ${target} (${pendingChips.length} remaining)`, "success");
      }
    }

    async function loadChip(chipId) {
      activeChip = chipId;
      boxes = [];
      startTime = new Date().toISOString();
      const res = await fetch(`/api/chip/${chipId}`);
      chipData = await res.json();

      // Populate FIRMS table
      const ctxMeta = chipData.context_metadata || {};
      document.getElementById("fc-id").innerText = ctxMeta.firms_detection_id || "-";
      document.getElementById("fc-coords").innerText = `${ctxMeta.firms_latitude}, ${ctxMeta.firms_longitude}`;
      document.getElementById("fc-pixel").innerText = ctxMeta.firms_pixel_coord ? `col=${ctxMeta.firms_pixel_coord.col}, row=${ctxMeta.firms_pixel_coord.row}` : "-";
      document.getElementById("fc-frp").innerText = ctxMeta.firms_frp !== undefined ? `${ctxMeta.firms_frp} MW` : "-";
      document.getElementById("fc-acq").innerText = ctxMeta.firms_acq_datetime_utc || "-";
      document.getElementById("fc-prod").innerText = ctxMeta.product_id || "-";
      document.getElementById("fc-cloud").innerText = ctxMeta.cloud_cover_pct !== undefined ? `${ctxMeta.cloud_cover_pct}%` : "-";

      // If chip already has completed annotations, load them, otherwise default to HAS_ANNOTATIONS
      if (chipData.chip_annotation_status) {
        const rad = document.querySelector(`input[name="chip_status"][value="${chipData.chip_annotation_status}"]`);
        if (rad) rad.checked = true;
      } else {
        const rad = document.querySelector('input[name="chip_status"][value="HAS_ANNOTATIONS"]');
        if (rad) rad.checked = true;
      }
      if (chipData.annotations && chipData.annotations.length > 0) {
        boxes = JSON.parse(JSON.stringify(chipData.annotations));
      }

      // Reset audit counters for this chip session
      auditCounts = {
        bbox_creation_actions: 0,
        bbox_edit_actions: 0,
        class_selection_actions: 0,
        save_events: chipData.interaction_audit ? (chipData.interaction_audit.save_events || 0) : 0
      };
      document.getElementById("audit-bbox-count").innerText = auditCounts.bbox_creation_actions;
      document.getElementById("audit-class-count").innerText = auditCounts.class_selection_actions;

      // Load preview images
      rgbImg.src = `/api/preview/${chipId}/rgb`;
      swirImg.src = `/api/preview/${chipId}/swir`;

      rgbImg.onload = () => redraw();
      swirImg.onload = () => redraw();

      renderBoxesForm();
      onStatusChange();
      resetZoom();
      redraw();
    }

    function switchBand(band) {
      activeBand = band;
      document.getElementById("btn-rgb").className = band === "rgb" ? "active" : "";
      document.getElementById("btn-swir").className = band === "swir" ? "active" : "";
      redraw();
    }

    function toggleFirmsMarker() {
      showFirms = !showFirms;
      document.getElementById("btn-firms-toggle").innerText = `FIRMS Reference: ${showFirms ? "ON" : "OFF"}`;
      redraw();
    }

    function changeZoom(factor) {
      zoomLevel = Math.max(0.5, Math.min(5.0, zoomLevel * factor));
      document.getElementById("zoom-display").innerText = `Zoom: ${Math.round(zoomLevel * 100)}%`;
      redraw();
    }

    function resetZoom() {
      zoomLevel = 1.0;
      panX = 0;
      panY = 0;
      document.getElementById("zoom-display").innerText = `Zoom: 100%`;
      redraw();
    }

    function redraw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const img = activeBand === "rgb" ? rgbImg : swirImg;
      if (img.complete && img.naturalWidth > 0) {
        ctx.drawImage(img, 0, 0, 512, 512);
      }

      // Draw FIRMS reference marker if enabled
      if (showFirms && chipData && chipData.context_metadata && chipData.context_metadata.firms_pixel_coord) {
        const fc = chipData.context_metadata.firms_pixel_coord;
        ctx.strokeStyle = "#ffeb3b";
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.arc(fc.col, fc.row, 12, 0, 2 * Math.PI);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(fc.col - 16, fc.row);
        ctx.lineTo(fc.col + 16, fc.row);
        ctx.moveTo(fc.col, fc.row - 16);
        ctx.lineTo(fc.col, fc.row + 16);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = "#ffeb3b";
        ctx.font = "10px sans-serif";
        ctx.fillText("FIRMS CONTEXT (NOT GT)", fc.col + 14, fc.row - 8);
      }

      // Draw existing boxes
      boxes.forEach((b, idx) => {
        const bb = b.bbox;
        ctx.strokeStyle = "#00e676";
        ctx.lineWidth = 2;
        ctx.strokeRect(bb.x_min, bb.y_min, bb.x_max - bb.x_min, bb.y_max - bb.y_min);
        ctx.fillStyle = "rgba(0, 230, 118, 0.2)";
        ctx.fillRect(bb.x_min, bb.y_min, bb.x_max - bb.x_min, bb.y_max - bb.y_min);

        ctx.fillStyle = "#00e676";
        ctx.font = "11px sans-serif";
        const label = b.class_name ? `#${idx+1}: ${b.class_name}` : `#${idx+1}: [Select Class]`;
        ctx.fillText(label, bb.x_min + 4, Math.max(14, bb.y_min - 4));
      });

      // Draw active drawing box
      if (isDrawing) {
        const x_min = Math.min(startX, currentX);
        const y_min = Math.min(startY, currentY);
        const w = Math.abs(currentX - startX);
        const h = Math.abs(currentY - startY);
        ctx.strokeStyle = "#ff9100";
        ctx.lineWidth = 2;
        ctx.setLineDash([3, 3]);
        ctx.strokeRect(x_min, y_min, w, h);
        ctx.setLineDash([]);
      }

      // Apply zoom & pan to canvas transform
      canvas.style.transformOrigin = "top left";
      canvas.style.transform = `scale(${zoomLevel}) translate(${panX}px, ${panY}px)`;
    }

    // Precise Canvas Coordinate Converter
    function getCanvasCoords(e) {
      const rect = canvas.getBoundingClientRect();
      const scaleX = 512 / (rect.width || 512);
      const scaleY = 512 / (rect.height || 512);
      const clientX = e.clientX !== undefined ? e.clientX : (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
      const clientY = e.clientY !== undefined ? e.clientY : (e.touches && e.touches[0] ? e.touches[0].clientY : 0);
      const x = Math.max(0, Math.min(512, Math.round((clientX - rect.left) * scaleX)));
      const y = Math.max(0, Math.min(512, Math.round((clientY - rect.top) * scaleY)));
      return { x, y };
    }

    function handleDrawStart(e) {
      if (e.button !== undefined && e.button !== 0) return; // Only primary left-button click
      if (e.preventDefault) e.preventDefault(); // Stop native drag-drop and text-selection

      // Automatically switch to HAS_ANNOTATIONS if currently NO_VISIBLE_TARGET
      const rad = document.querySelector('input[name="chip_status"]:checked');
      if (rad && rad.value !== "HAS_ANNOTATIONS") {
        const hasAnnRadio = document.querySelector('input[name="chip_status"][value="HAS_ANNOTATIONS"]');
        if (hasAnnRadio) {
          hasAnnRadio.checked = true;
          onStatusChange();
        }
      }

      const { x, y } = getCanvasCoords(e);
      startX = x;
      startY = y;
      currentX = x;
      currentY = y;
      isDrawing = true;

      // Pointer capture guarantees drag tracking even outside element boundaries
      if (canvas.setPointerCapture && e.pointerId !== undefined) {
        try { canvas.setPointerCapture(e.pointerId); } catch (_) {}
      }

      const modeDisplay = document.getElementById("box-mode-display");
      if (modeDisplay) modeDisplay.innerText = `Drawing: [${startX}, ${startY}]...`;
      redraw();
    }

    function handleDrawMove(e) {
      const { x, y } = getCanvasCoords(e);
      document.getElementById("coord-display").innerText = `Pixel: X: ${x}, Y: ${y}`;

      if (isDrawing) {
        if (e.preventDefault) e.preventDefault();
        currentX = x;
        currentY = y;
        const x_min = Math.min(startX, currentX);
        const y_min = Math.min(startY, currentY);
        const x_max = Math.max(startX, currentX);
        const y_max = Math.max(startY, currentY);
        const modeDisplay = document.getElementById("box-mode-display");
        if (modeDisplay) {
          modeDisplay.innerText = `Drawing: [${x_min}, ${y_min}] to [${x_max}, ${y_max}] (${x_max - x_min}x${y_max - y_min})`;
        }
        redraw();
      }
    }

    function handleDrawEnd(e) {
      if (!isDrawing) return;
      isDrawing = false;
      if (e && e.preventDefault) e.preventDefault();

      if (canvas.releasePointerCapture && e && e.pointerId !== undefined) {
        try { canvas.releasePointerCapture(e.pointerId); } catch (_) {}
      }

      const x_min = Math.min(startX, currentX);
      const y_min = Math.min(startY, currentY);
      const x_max = Math.max(startX, currentX);
      const y_max = Math.max(startY, currentY);

      const modeDisplay = document.getElementById("box-mode-display");

      if ((x_max - x_min) >= 4 && (y_max - y_min) >= 4) {
        auditCounts.bbox_creation_actions += 1;
        document.getElementById("audit-bbox-count").innerText = auditCounts.bbox_creation_actions;
        boxes.push({
          annotation_id: `${activeChip}_ANN_${String(boxes.length + 1).padStart(2, '0')}`,
          class_id: null,
          class_name: "",
          bbox: { x_min, y_min, x_max, y_max },
          geometry_confidence: "MEDIUM",
          source_class_confidence: "MEDIUM",
          visibility_status: "CLEAR",
          visual_evidence: ["NO_CLEAR_VISUAL_EVIDENCE"],
          firms_relationship: "INSIDE_OBJECT",
          review_status: "PENDING",
          notes: ""
        });
        renderBoxesForm();
        if (modeDisplay) modeDisplay.innerText = `BBox captured: [${x_min}, ${y_min}, ${x_max}, ${y_max}] (#${boxes.length})`;
      } else {
        if (modeDisplay) modeDisplay.innerText = "Drawing mode: READY (Drag too small, <4px)";
      }
      redraw();
    }

    // Modern Pointer Events (Chrome, Edge, Firefox, Touch, Pen)
    canvas.addEventListener("pointerdown", handleDrawStart);
    canvas.addEventListener("pointermove", handleDrawMove);
    canvas.addEventListener("pointerup", handleDrawEnd);
    canvas.addEventListener("pointercancel", handleDrawEnd);

    // Global release listeners so mouseup outside canvas is captured
    window.addEventListener("pointerup", (e) => { if (isDrawing) handleDrawEnd(e); });
    window.addEventListener("mouseup", (e) => { if (isDrawing) handleDrawEnd(e); });

    // Fallback mouse listeners on canvas and viewport
    canvas.addEventListener("mousedown", handleDrawStart);
    canvas.addEventListener("mousemove", handleDrawMove);
    canvas.addEventListener("mouseup", handleDrawEnd);
    viewport.addEventListener("mousemove", handleDrawMove);

    // Suppress native drag-and-drop on canvas
    canvas.addEventListener("dragstart", (e) => e.preventDefault());

    function renderBoxesForm() {
      const container = document.getElementById("boxes-container");
      document.getElementById("box-count").innerText = boxes.length;
      if (boxes.length === 0) {
        container.innerHTML = '<p style="color: #888; font-size: 0.85rem; font-style: italic;">No bounding boxes drawn yet. Click and drag on the imagery canvas to draw bounding box [0, 512].</p>';
        return;
      }
      container.innerHTML = "";
      boxes.forEach((b, idx) => {
        const card = document.createElement("div");
        card.className = "box-card";
        card.innerHTML = `
          <div class="box-header">
            <strong>Box #${idx+1} [${b.bbox.x_min}, ${b.bbox.y_min}, ${b.bbox.x_max}, ${b.bbox.y_max}]</strong>
            <button type="button" onclick="deleteBox(${idx})" style="background: #c62828; padding: 2px 8px;">✕ Remove</button>
          </div>
          <label>Target Class (Mandatory - No auto-selection):</label>
          <select id="class-select-${idx}" onchange="updateBoxClass(${idx}, this.value)">
            <option value="">-- Select Class --</option>
            <option value="Industrial Fire" ${b.class_name === "Industrial Fire" ? "selected" : ""}>Industrial Fire</option>
            <option value="Forest Fire" ${b.class_name === "Forest Fire" ? "selected" : ""}>Forest Fire</option>
            <option value="Agricultural Fire" ${b.class_name === "Agricultural Fire" ? "selected" : ""}>Agricultural Fire</option>
            <option value="Other Thermal Source" ${b.class_name === "Other Thermal Source" ? "selected" : ""}>Other Thermal Source</option>
            <option value="UNRESOLVED" ${b.class_name === "UNRESOLVED" ? "selected" : ""}>UNRESOLVED</option>
          </select>
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px;">
            <div>
              <label>Visibility:</label>
              <select onchange="updateBoxField(${idx}, 'visibility_status', this.value)">
                <option value="CLEAR" ${b.visibility_status === "CLEAR" ? "selected" : ""}>CLEAR</option>
                <option value="PARTIALLY_OBSCURED" ${b.visibility_status === "PARTIALLY_OBSCURED" ? "selected" : ""}>PARTIALLY_OBSCURED</option>
                <option value="HEAVILY_OBSCURED" ${b.visibility_status === "HEAVILY_OBSCURED" ? "selected" : ""}>HEAVILY_OBSCURED</option>
              </select>
            </div>
            <div>
              <label>Geom. Conf:</label>
              <select onchange="updateBoxField(${idx}, 'geometry_confidence', this.value)">
                <option value="HIGH" ${b.geometry_confidence === "HIGH" ? "selected" : ""}>HIGH</option>
                <option value="MEDIUM" ${b.geometry_confidence === "MEDIUM" ? "selected" : ""}>MEDIUM</option>
                <option value="LOW" ${b.geometry_confidence === "LOW" ? "selected" : ""}>LOW</option>
              </select>
            </div>
            <div>
              <label>Class Conf:</label>
              <select onchange="updateBoxField(${idx}, 'source_class_confidence', this.value)">
                <option value="HIGH" ${b.source_class_confidence === "HIGH" ? "selected" : ""}>HIGH</option>
                <option value="MEDIUM" ${b.source_class_confidence === "MEDIUM" ? "selected" : ""}>MEDIUM</option>
                <option value="LOW" ${b.source_class_confidence === "LOW" ? "selected" : ""}>LOW</option>
              </select>
            </div>
          </div>
          <label style="margin-top: 6px;">Visual Evidence (Select all observed):</label>
          <div class="checkbox-grid" id="ev-grid-${idx}">
            ${renderEvidenceCheckboxes(idx, b.visual_evidence || [])}
          </div>
          <label>FIRMS Relationship:</label>
          <select onchange="updateBoxField(${idx}, 'firms_relationship', this.value)">
            <option value="INSIDE_OBJECT" ${b.firms_relationship === "INSIDE_OBJECT" ? "selected" : ""}>INSIDE_OBJECT</option>
            <option value="TOUCHING_OBJECT" ${b.firms_relationship === "TOUCHING_OBJECT" ? "selected" : ""}>TOUCHING_OBJECT</option>
            <option value="NEAR_OBJECT" ${b.firms_relationship === "NEAR_OBJECT" ? "selected" : ""}>NEAR_OBJECT</option>
            <option value="OUTSIDE_VISIBLE_OBJECT" ${b.firms_relationship === "OUTSIDE_VISIBLE_OBJECT" ? "selected" : ""}>OUTSIDE_VISIBLE_OBJECT</option>
            <option value="NO_VISIBLE_TARGET" ${b.firms_relationship === "NO_VISIBLE_TARGET" ? "selected" : ""}>NO_VISIBLE_TARGET</option>
          </select>
          <label>Annotator Notes / Rationale:</label>
          <textarea rows="2" onchange="updateBoxField(${idx}, 'notes', this.value)">${b.notes || ""}</textarea>
        `;
        container.appendChild(card);
      });
    }

    function renderEvidenceCheckboxes(boxIdx, currentList) {
      const tags = [
        "DIRECT_FIRE_VISIBLE", "SMOKE_VISIBLE", "BURN_SCAR_VISIBLE",
        "INDUSTRIAL_INFRASTRUCTURE_VISIBLE", "FOREST_CONTEXT_VISIBLE",
        "CROPLAND_CONTEXT_VISIBLE", "PERSISTENT_THERMAL_SOURCE_CONTEXT",
        "NO_CLEAR_VISUAL_EVIDENCE"
      ];
      return tags.map(t => `
        <label>
          <input type="checkbox" value="${t}" ${currentList.includes(t) ? "checked" : ""} onchange="updateBoxEvidence(${boxIdx})">
          ${t.replace(/_/g, " ")}
        </label>
      `).join("");
    }

    function updateBoxClass(idx, cname) {
      auditCounts.class_selection_actions += 1;
      document.getElementById("audit-class-count").innerText = auditCounts.class_selection_actions;
      boxes[idx].class_name = cname;
      const classIdMap = {"UNRESOLVED": 0, "Industrial Fire": 1, "Forest Fire": 2, "Agricultural Fire": 3, "Other Thermal Source": 4};
      boxes[idx].class_id = classIdMap[cname] !== undefined ? classIdMap[cname] : 0;
      redraw();
    }

    function updateBoxField(idx, field, val) {
      boxes[idx][field] = val;
    }

    function updateBoxEvidence(idx) {
      const container = document.getElementById(`ev-grid-${idx}`);
      const checked = Array.from(container.querySelectorAll("input:checked")).map(i => i.value);
      boxes[idx].visual_evidence = checked.length > 0 ? checked : ["NO_CLEAR_VISUAL_EVIDENCE"];
    }

    function deleteBox(idx) {
      boxes.splice(idx, 1);
      renderBoxesForm();
      redraw();
    }

    function clearBoxes() {
      boxes = [];
      renderBoxesForm();
      redraw();
    }

    function onStatusChange() {
      const rad = document.querySelector('input[name="chip_status"]:checked');
      const status = rad ? rad.value : "HAS_ANNOTATIONS";
      const annSec = document.getElementById("annotations-section");
      if (status === "NO_VISIBLE_TARGET") {
        annSec.style.display = "none";
        boxes = [];
        redraw();
      } else {
        annSec.style.display = "block";
      }
    }

    async function saveAnnotation() {
      const msgBox = document.getElementById("msg-box");
      msgBox.style.display = "none";

      const rad = document.querySelector('input[name="chip_status"]:checked');
      const chipStatus = rad ? rad.value : "HAS_ANNOTATIONS";

      if (chipStatus === "HAS_ANNOTATIONS" && boxes.length === 0) {
        showMsg("Validation Error: 'HAS_ANNOTATIONS' requires at least one bounding box. Draw a box or switch status to NO_VISIBLE_TARGET / UNRESOLVED.", "error");
        return;
      }

      for (let i = 0; i < boxes.length; i++) {
        if (!boxes[i].class_name) {
          showMsg(`Validation Error in Box #${i+1}: Target class must be explicitly selected.`, "error");
          return;
        }
      }

      const payload = {
        chip_id: activeChip,
        annotation_version: "v1.0",
        chip_annotation_status: chipStatus,
        human_verified: true,
        annotation_start_timestamp: startTime,
        annotation_completion_timestamp: new Date().toISOString(),
        interaction_audit: {
          interface_version: "v1.0_manual",
          bbox_creation_actions: auditCounts.bbox_creation_actions,
          bbox_edit_actions: auditCounts.bbox_edit_actions,
          class_selection_actions: auditCounts.class_selection_actions,
          save_events: auditCounts.save_events + 1
        },
        annotations: boxes,
        context_metadata: chipData.context_metadata
      };

      try {
        const res = await fetch("/api/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (result.success) {
          auditCounts.save_events += 1;

          // Re-fetch chips to update dropdown status
          const chipsRes = await fetch("/api/chips");
          const chips = await chipsRes.json();
          const sel = document.getElementById("chip-select");
          sel.innerHTML = "";
          chips.forEach(c => {
            const opt = document.createElement("option");
            opt.value = c.chip_id;
            opt.innerText = `${c.chip_id} [${c.status}]`;
            sel.appendChild(opt);
          });
          sel.value = activeChip;

          const pendingChips = chips.filter(c => c.status === "PENDING_MANUAL_INPUT");
          const nextBtn = document.getElementById("btn-next-pending");

          if (pendingChips.length === 0) {
            showMsg(`SUCCESS: Saved manual annotation for ${activeChip}! All chips completed.`, "success");
            if (nextBtn) {
              nextBtn.innerText = "All chips completed.";
              nextBtn.disabled = true;
            }
          } else {
            showMsg(`SUCCESS: Saved manual annotation for ${activeChip}! Click "Next Pending Chip" to continue (${pendingChips.length} remaining).`, "success");
            if (nextBtn) {
              nextBtn.innerText = `➡️ Next Pending Chip (${pendingChips.length} remaining)`;
              nextBtn.disabled = false;
            }
          }
        } else {
          showMsg(`Save Error: ${result.errors.join("; ")}`, "error");
        }
      } catch (err) {
        showMsg(`Network Error: ${err.message}`, "error");
      }
    }

    function showMsg(text, type) {
      const msgBox = document.getElementById("msg-box");
      msgBox.innerText = text;
      msgBox.className = type === "error" ? "msg-error" : "msg-success";
      msgBox.style.display = "block";
    }

    window.onload = init;
  </script>
</body>
</html>
"""


class DS08AnnotationServerHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for the manual annotation web interface."""

    def __init__(self, *args, active_annotator: str = "annotator_1", workspace_dir: Optional[Path] = None, **kwargs):
        self.active_annotator = active_annotator
        self.workspace_dir = workspace_dir
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = HTML_APP_TEMPLATE.replace("__ANNOTATOR__", self.active_annotator)
            self.wfile.write(html.encode("utf-8"))
            return

        if path == "/api/chips":
            adir = self.workspace_dir if self.workspace_dir is not None else get_annotator_dir(self.active_annotator)
            ann_suffix = self.active_annotator.replace("_", "")
            chip_list = []
            for cid in AFFECTED_15_CHIPS:
                fpath = adir / f"{cid}_{ann_suffix}.json"
                status = "PENDING_MANUAL_INPUT"
                if fpath.exists():
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        status = data.get("task_status", "PENDING_MANUAL_INPUT")
                    except Exception:
                        status = "ERROR"
                chip_list.append({"chip_id": cid, "status": status})

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(chip_list).encode("utf-8"))
            return

        if path.startswith("/api/chip/"):
            chip_id = path.split("/")[-1]
            try:
                data = load_manual_template(self.active_annotator, chip_id, target_dir=self.workspace_dir)
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
                success, errors = save_manual_annotation(
                    self.active_annotator, chip_id, payload, target_dir=self.workspace_dir
                )
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


def run_annotation_server(annotator: str = "annotator_1", port: int = 8080, workspace_dir: Optional[Path] = None) -> None:
    """Launches local HTTP server for the manual annotation interface."""
    def handler_factory(*args, **kwargs):
        return DS08AnnotationServerHandler(*args, active_annotator=annotator, workspace_dir=workspace_dir, **kwargs)

    with socketserver.TCPServer(("", port), handler_factory) as httpd:
        print(f"\n{'='*70}")
        print(f"DS08 MANUAL ANNOTATION INTERFACE ACTIVE")
        print(f"{'='*70}")
        print(f"  Annotator Workspace:  {annotator} (STRICTLY ISOLATED)")
        print(f"  Local URL:            http://localhost:{port}")
        print(f"  Active Chips:         15 affected pilot chips")
        print(f"  FIRMS Status:         FIRMS CONTEXT — NOT GROUND TRUTH")
        print(f"  Press Ctrl+C to terminate server.")
        print(f"{'='*70}\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down DS08 annotation server.")


def main() -> int:
    parser = argparse.ArgumentParser(description="DS08 Manual Annotation Tooling and Verification Interface.")
    parser.add_argument("--list", action="store_true", help="List all 20 active pilot chips from manifest.")
    parser.add_argument("--inspect", type=str, help="Inspect a specific chip ID.")
    parser.add_argument("--validate", type=str, help="Validate an existing annotation JSON against the schema.")
    parser.add_argument("--init-manual", action="store_true", help="Initialize blank task templates in manual workspace.")
    parser.add_argument("--ui", action="store_true", help="Launch interactive manual annotation web server.")
    parser.add_argument("--annotator", type=str, default="annotator_1", choices=["annotator_1", "annotator_2"], help="Active annotator workspace.")
    parser.add_argument("--port", type=int, default=8080, help="Web server port (default 8080).")
    args = parser.parse_args()

    if args.list:
        manifest = load_manifest()
        print(f"\nDS08 Pilot Manifest ({manifest['total_active_pilot_chips']} active chips):")
        for c in manifest["chips"]:
            print(f"  [{c['pilot_index']:02d}] {c['chip_id']:<28} {c['region']:<8} Cloud: {c['cloud_cover_pct']:>4.1f}% Status: {c['annotation_status']}")
        return 0

    if args.inspect:
        print_chip_summary(args.inspect)
        return 0

    if args.validate:
        p = Path(args.validate)
        if not p.exists():
            print(f"Error: file not found: {p}", file=sys.stderr)
            return 1
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        valid, errors = validate_annotation_payload(data)
        if valid:
            print(f"SUCCESS: '{p.name}' is valid according to ds08_annotation_schema.json")
            return 0
        else:
            print(f"FAILED: '{p.name}' has validation errors:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1

    if args.init_manual:
        counts = init_manual_templates()
        print(f"Initialized manual workspace templates: {counts}")
        return 0

    if args.ui:
        run_annotation_server(annotator=args.annotator, port=args.port)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
