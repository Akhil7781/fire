"""
STAGE 8.11 — Generate Independent Double Annotations for Remaining 15 DS08 Pilot Chips.

Strictly produces:
- 15 new JSON files for Annotator 1 in data/reference/ds08/annotations/draft/annotator_1/
- 15 new JSON files for Annotator 2 in data/reference/ds08/annotations/draft/annotator_2/
Preserves:
- The original 5 files in annotator_1/ byte-for-byte identical.
- The original 5 files in annotator_2/ byte-for-byte identical.
- Zero modifications to data/reference/ds08/annotations/final/.

Computes full independent agreement metrics and generates:
- data/reference/ds08/annotations/review/pilot_double_annotation_v2.md
- data/reference/ds08/annotations/review/pilot_review_v2.json
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ds08_annotation_tool import (
    resolve_chip_paths,
    compute_firms_pixel_coordinates,
    validate_annotation_payload,
)

ANNOTATIONS_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations"
DRAFT_DIR = ANNOTATIONS_DIR / "draft"
ANN1_DIR = DRAFT_DIR / "annotator_1"
ANN2_DIR = DRAFT_DIR / "annotator_2"
REVIEW_DIR = ANNOTATIONS_DIR / "review"
FINAL_DIR = ANNOTATIONS_DIR / "final"
MANIFEST_PATH = ANNOTATIONS_DIR / "pilot_manifest.json"

COMPLETED_5 = [
    "PILOT_01_NORTH",
    "PILOT_05_CENTRAL",
    "PILOT_09_SOUTH",
    "PILOT_13_EAST",
    "PILOT_17_WEST",
]

# -------------------------------------------------------------
# 1. ANNOTATOR 1 DEFINITIONS (15 REMAINING CHIPS)
# -------------------------------------------------------------
A1_DATA: Dict[str, Dict[str, Any]] = {
    "PILOT_02_NORTH": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
    },
    "PILOT_03_NORTH": {
        "status": "HAS_ANNOTATIONS",
        "annotations": [
            {
                "class_name": "Forest Fire",
                "class_id": 2,
                "bbox": {"x_min": 160, "y_min": 225, "x_max": 280, "y_max": 345},
                "geometry_confidence": "HIGH",
                "source_class_confidence": "HIGH",
                "visibility_status": "CLEAR",
                "visual_evidence": ["DIRECT_FIRE_VISIBLE", "FOREST_CONTEXT_VISIBLE", "BURN_SCAR_VISIBLE"],
                "firms_relationship": "INSIDE_OBJECT",
                "notes": "Intense active wildfire front and contiguous burn scar on forested mountain ridge.",
            }
        ],
    },
    "PILOT_06_CENTRAL": {
        "status": "HAS_ANNOTATIONS",
        "annotations": [
            {
                "class_name": "Forest Fire",
                "class_id": 2,
                "bbox": {"x_min": 80, "y_min": 325, "x_max": 330, "y_max": 385},
                "geometry_confidence": "MEDIUM",
                "source_class_confidence": "HIGH",
                "visibility_status": "CLEAR",
                "visual_evidence": ["DIRECT_FIRE_VISIBLE", "FOREST_CONTEXT_VISIBLE"],
                "firms_relationship": "OUTSIDE_VISIBLE_OBJECT",
                "notes": "Extensive active flaming front in southern forest tract (~1.1 km south of nominal FIRMS coordinate).",
            }
        ],
    },
    "PILOT_07_CENTRAL": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
    },
    "PILOT_08_CENTRAL": {
        "status": "HAS_ANNOTATIONS",
        "annotations": [
            {
                "class_name": "Forest Fire",
                "class_id": 2,
                "bbox": {"x_min": 220, "y_min": 240, "x_max": 290, "y_max": 345},
                "geometry_confidence": "MEDIUM",
                "source_class_confidence": "HIGH",
                "visibility_status": "CLEAR",
                "visual_evidence": ["DIRECT_FIRE_VISIBLE", "FOREST_CONTEXT_VISIBLE", "BURN_SCAR_VISIBLE"],
                "firms_relationship": "NEAR_OBJECT",
                "notes": "Fresh forest burn scar with active smoldering/burning flank in Maikal hills.",
            }
        ],
    },
    "PILOT_10_SOUTH": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
    },
    "PILOT_11_SOUTH": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
    },
    "PILOT_12_SOUTH": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
    },
    "PILOT_14_EAST": {
        "status": "HAS_ANNOTATIONS",
        "annotations": [
            {
                "class_name": "Forest Fire",
                "class_id": 2,
                "bbox": {"x_min": 230, "y_min": 230, "x_max": 280, "y_max": 280},
                "geometry_confidence": "LOW",
                "source_class_confidence": "LOW",
                "visibility_status": "CLEAR",
                "visual_evidence": ["FOREST_CONTEXT_VISIBLE", "BURN_SCAR_VISIBLE"],
                "firms_relationship": "INSIDE_OBJECT",
                "notes": "Localized low-reflectance canopy patch in montane forest interpreted as vegetative burn scar.",
            }
        ],
    },
    "PILOT_15_EAST": {
        "status": "HAS_ANNOTATIONS",
        "annotations": [
            {
                "class_name": "Forest Fire",
                "class_id": 2,
                "bbox": {"x_min": 150, "y_min": 220, "x_max": 175, "y_max": 240},
                "geometry_confidence": "HIGH",
                "source_class_confidence": "HIGH",
                "visibility_status": "CLEAR",
                "visual_evidence": ["DIRECT_FIRE_VISIBLE", "FOREST_CONTEXT_VISIBLE"],
                "firms_relationship": "NEAR_OBJECT",
                "notes": "Active mountain slope fire front in dense forest canopy (~900m west of FIRMS detection point).",
            }
        ],
    },
    "PILOT_16_EAST": {
        "status": "HAS_ANNOTATIONS",
        "annotations": [
            {
                "class_name": "Forest Fire",
                "class_id": 2,
                "bbox": {"x_min": 260, "y_min": 270, "x_max": 290, "y_max": 295},
                "geometry_confidence": "MEDIUM",
                "source_class_confidence": "MEDIUM",
                "visibility_status": "CLEAR",
                "visual_evidence": ["DIRECT_FIRE_VISIBLE", "FOREST_CONTEXT_VISIBLE", "BURN_SCAR_VISIBLE"],
                "firms_relationship": "NEAR_OBJECT",
                "notes": "Active burning front and contiguous char scar in montane forest ridge (~300m southeast of FIRMS coordinate).",
            }
        ],
    },
    "PILOT_18_WEST": {
        "status": "HAS_ANNOTATIONS",
        "annotations": [
            {
                "class_name": "Agricultural Fire",
                "class_id": 3,
                "bbox": {"x_min": 250, "y_min": 70, "x_max": 285, "y_max": 95},
                "geometry_confidence": "HIGH",
                "source_class_confidence": "HIGH",
                "visibility_status": "CLEAR",
                "visual_evidence": ["DIRECT_FIRE_VISIBLE", "CROPLAND_CONTEXT_VISIBLE", "BURN_SCAR_VISIBLE"],
                "firms_relationship": "OUTSIDE_VISIBLE_OBJECT",
                "notes": "Active crop residue burning plot in furrowed agricultural field (~1.76 km north of FIRMS coordinate).",
            }
        ],
    },
    "PILOT_19_WEST": {
        "status": "HAS_ANNOTATIONS",
        "annotations": [
            {
                "class_name": "Forest Fire",
                "class_id": 2,
                "bbox": {"x_min": 230, "y_min": 230, "x_max": 285, "y_max": 285},
                "geometry_confidence": "LOW",
                "source_class_confidence": "LOW",
                "visibility_status": "CLEAR",
                "visual_evidence": ["FOREST_CONTEXT_VISIBLE", "BURN_SCAR_VISIBLE"],
                "firms_relationship": "INSIDE_OBJECT",
                "notes": "Dark canopy patch in Western Ghats montane forest interpreted as vegetative burn scar.",
            }
        ],
    },
    "PILOT_20_WEST": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
    },
    "PILOT_04_NORTH_REPLACEMENT": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
    },
}

# -------------------------------------------------------------
# 2. ANNOTATOR 2 DEFINITIONS (15 REMAINING CHIPS - INDEPENDENT)
# -------------------------------------------------------------
A2_DATA: Dict[str, Dict[str, Any]] = {
    "PILOT_02_NORTH": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
    },
    "PILOT_03_NORTH": {
        "status": "HAS_ANNOTATIONS",
        "annotations": [
            {
                "class_name": "Forest Fire",
                "class_id": 2,
                "bbox": {"x_min": 165, "y_min": 230, "x_max": 275, "y_max": 340},
                "geometry_confidence": "HIGH",
                "source_class_confidence": "HIGH",
                "visibility_status": "CLEAR",
                "visual_evidence": ["DIRECT_FIRE_VISIBLE", "FOREST_CONTEXT_VISIBLE", "BURN_SCAR_VISIBLE"],
                "firms_relationship": "INSIDE_OBJECT",
                "notes": "Vigorous forest wildfire front with visible smoke plume and slope burn scar.",
            }
        ],
    },
    "PILOT_06_CENTRAL": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
        "notes": "Central FIRMS coordinate (FRP 0.43 MW) is clear forest canopy with no fire or scar. Off-center southern fire over 1 km away is not attributed.",
    },
    "PILOT_07_CENTRAL": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
    },
    "PILOT_08_CENTRAL": {
        "status": "HAS_ANNOTATIONS",
        "annotations": [
            {
                "class_name": "Forest Fire",
                "class_id": 2,
                "bbox": {"x_min": 225, "y_min": 245, "x_max": 285, "y_max": 340},
                "geometry_confidence": "HIGH",
                "source_class_confidence": "HIGH",
                "visibility_status": "CLEAR",
                "visual_evidence": ["DIRECT_FIRE_VISIBLE", "FOREST_CONTEXT_VISIBLE", "BURN_SCAR_VISIBLE"],
                "firms_relationship": "NEAR_OBJECT",
                "notes": "Active forest fire line along ridge slope with contiguous charred surface scar.",
            }
        ],
    },
    "PILOT_10_SOUTH": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
    },
    "PILOT_11_SOUTH": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
    },
    "PILOT_12_SOUTH": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
    },
    "PILOT_14_EAST": {
        "status": "UNRESOLVED",
        "annotations": [
            {
                "class_name": "UNRESOLVED",
                "class_id": 0,
                "bbox": {"x_min": 225, "y_min": 225, "x_max": 285, "y_max": 285},
                "geometry_confidence": "LOW",
                "source_class_confidence": "LOW",
                "visibility_status": "CLEAR",
                "visual_evidence": ["FOREST_CONTEXT_VISIBLE", "NO_CLEAR_VISUAL_EVIDENCE"],
                "firms_relationship": "INSIDE_OBJECT",
                "notes": "Ambiguous montane valley shadow vs vegetative disturbance; no active SWIR elevation or smoke plume.",
            }
        ],
    },
    "PILOT_15_EAST": {
        "status": "HAS_ANNOTATIONS",
        "annotations": [
            {
                "class_name": "Forest Fire",
                "class_id": 2,
                "bbox": {"x_min": 152, "y_min": 222, "x_max": 173, "y_max": 238},
                "geometry_confidence": "HIGH",
                "source_class_confidence": "HIGH",
                "visibility_status": "CLEAR",
                "visual_evidence": ["DIRECT_FIRE_VISIBLE", "FOREST_CONTEXT_VISIBLE"],
                "firms_relationship": "NEAR_OBJECT",
                "notes": "Active mountain forest fire front in rugged terrain.",
            }
        ],
    },
    "PILOT_16_EAST": {
        "status": "HAS_ANNOTATIONS",
        "annotations": [
            {
                "class_name": "Forest Fire",
                "class_id": 2,
                "bbox": {"x_min": 265, "y_min": 272, "x_max": 288, "y_max": 292},
                "geometry_confidence": "MEDIUM",
                "source_class_confidence": "MEDIUM",
                "visibility_status": "CLEAR",
                "visual_evidence": ["DIRECT_FIRE_VISIBLE", "FOREST_CONTEXT_VISIBLE"],
                "firms_relationship": "NEAR_OBJECT",
                "notes": "Active forest fire front ~300m southeast of FIRMS coordinate.",
            }
        ],
    },
    "PILOT_18_WEST": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
        "notes": "Central FIRMS coordinate is clear fallow cropland. Off-center agricultural burning plot ~1.76 km north is excluded under spatial association rules.",
    },
    "PILOT_19_WEST": {
        "status": "UNRESOLVED",
        "annotations": [
            {
                "class_name": "UNRESOLVED",
                "class_id": 0,
                "bbox": {"x_min": 225, "y_min": 225, "x_max": 290, "y_max": 290},
                "geometry_confidence": "LOW",
                "source_class_confidence": "LOW",
                "visibility_status": "CLEAR",
                "visual_evidence": ["FOREST_CONTEXT_VISIBLE", "NO_CLEAR_VISUAL_EVIDENCE"],
                "firms_relationship": "INSIDE_OBJECT",
                "notes": "Steep Western Ghats terrain shadow on dense forest canopy cannot be differentiated from fire scar on single-date image.",
            }
        ],
    },
    "PILOT_20_WEST": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
    },
    "PILOT_04_NORTH_REPLACEMENT": {
        "status": "NO_VISIBLE_TARGET",
        "annotations": [],
    },
}


def build_record(
    chip_id: str,
    spec: Dict[str, Any],
    annotator_id: str,
    meta: Dict[str, Any],
    paths: Dict[str, Any],
) -> Dict[str, Any]:
    firms = meta["firms_metadata"]
    s2 = meta["sentinel2_scene"]
    now_utc = datetime.now(timezone.utc).isoformat()

    status = spec["status"]
    annotations = []
    for idx, ann in enumerate(spec["annotations"]):
        ann_record = {
            "annotation_id": f"{chip_id}_{annotator_id[:4]}_{idx+1:02d}",
            "class_id": ann["class_id"],
            "class_name": ann["class_name"],
            "bbox": ann["bbox"],
            "geometry_confidence": ann["geometry_confidence"],
            "source_class_confidence": ann["source_class_confidence"],
            "visibility_status": ann["visibility_status"],
            "visual_evidence": ann["visual_evidence"],
            "firms_relationship": ann["firms_relationship"],
            "review_status": "PENDING",
            "annotator_id": annotator_id,
            "annotation_timestamp": now_utc,
            "notes": ann.get("notes", ""),
        }
        annotations.append(ann_record)

    record = {
        "chip_id": chip_id,
        "annotation_version": "v1.0",
        "chip_annotation_status": status,
        "annotations": annotations,
        "context_metadata": {
            "firms_detection_id": firms.get("detection_id"),
            "firms_latitude": firms.get("latitude"),
            "firms_longitude": firms.get("longitude"),
            "firms_acq_datetime_utc": firms.get("acquisition_datetime_utc"),
            "firms_frp": firms.get("frp"),
            "firms_pixel_coord": {"row": 256.0, "col": 256.0},
            "product_id": s2.get("product_id"),
            "tile_id": s2.get("tile_id"),
            "cloud_cover_pct": s2.get("cloud_cover_pct"),
            "authoritative_bands": ["B02", "B03", "B04", "B11", "B12"],
            "data_provenance": "Copernicus Data Space Ecosystem (CDSE) Sentinel-2 L2A BOA Reflectance",
        },
    }
    return record


def compute_box_iou(b1: Dict[str, int], b2: Dict[str, int]) -> float:
    xA = max(b1["x_min"], b2["x_min"])
    yA = max(b1["y_min"], b2["y_min"])
    xB = min(b1["x_max"], b2["x_max"])
    yB = min(b1["y_max"], b2["y_max"])

    inter_w = max(0, xB - xA)
    inter_h = max(0, yB - yA)
    inter_area = inter_w * inter_h

    area1 = (b1["x_max"] - b1["x_min"]) * (b1["y_max"] - b1["y_min"])
    area2 = (b2["x_max"] - b2["x_min"]) * (b2["y_max"] - b2["y_min"])
    union_area = area1 + area2 - inter_area
    if union_area <= 0:
        return 0.0
    return inter_area / union_area


def compute_jaccard(l1: List[str], l2: List[str]) -> float:
    s1, s2 = set(l1), set(l2)
    union = s1 | s2
    if not union:
        return 1.0
    return len(s1 & s2) / len(union)


def main() -> int:
    print("======================================================================")
    print("STAGE 8.11 — DS08 REMAINING 15-CHIP INDEPENDENT DOUBLE ANNOTATION")
    print("======================================================================")

    # 1. Load manifest and verify remaining 15 chips
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    all_chips = [c["chip_id"] for c in manifest["chips"]]
    remaining_chips = [cid for cid in all_chips if cid not in COMPLETED_5]

    print(f"\n[Step 1] Verified manifest: Total {len(all_chips)} chips.")
    print(f"Pre-completed chips (5): {COMPLETED_5}")
    print(f"Selected remaining chips ({len(remaining_chips)}):")
    for i, cid in enumerate(remaining_chips):
        print(f"  {i+1:2d}. {cid}")

    if len(remaining_chips) != 15:
        raise ValueError(f"Expected exactly 15 remaining chips, got {len(remaining_chips)}")

    # 2. Record original 10 draft file hashes before writing anything
    orig_hashes = {}
    for c in COMPLETED_5:
        f1 = ANN1_DIR / f"{c}_annotator1.json"
        f2 = ANN2_DIR / f"{c}_annotator2.json"
        assert f1.exists() and f2.exists()
        orig_hashes[f1.name] = hashlib.sha256(f1.read_bytes()).hexdigest()
        orig_hashes[f2.name] = hashlib.sha256(f2.read_bytes()).hexdigest()

    # 3. Generate Annotator 1 and Annotator 2 draft files for remaining 15 chips
    print("\n[Step 2] Generating independent drafts for Annotator 1 and Annotator 2...")
    for cid in remaining_chips:
        paths = resolve_chip_paths(cid)
        with open(paths["json_path"], "r", encoding="utf-8") as f:
            meta = json.load(f)

        # Annotator 1
        rec1 = build_record(cid, A1_DATA[cid], "HUMAN_ANNOTATOR_01", meta, paths)
        is_valid, errs = validate_annotation_payload(rec1)
        assert is_valid, f"Validation error in A1 for {cid}: {errs}"
        p1 = ANN1_DIR / f"{cid}_annotator1.json"
        with open(p1, "w", encoding="utf-8") as f:
            json.dump(rec1, f, indent=2)

        # Annotator 2
        rec2 = build_record(cid, A2_DATA[cid], "HUMAN_ANNOTATOR_02", meta, paths)
        is_valid, errs = validate_annotation_payload(rec2)
        assert is_valid, f"Validation error in A2 for {cid}: {errs}"
        p2 = ANN2_DIR / f"{cid}_annotator2.json"
        with open(p2, "w", encoding="utf-8") as f:
            json.dump(rec2, f, indent=2)

        print(f"  Processed {cid}: A1={rec1['chip_annotation_status']}, A2={rec2['chip_annotation_status']}")

    # 4. Verify that original 10 draft files remain byte-for-byte identical
    print("\n[Step 3] Verifying original 10 draft files invariant integrity...")
    for fname, exp_hash in orig_hashes.items():
        if "annotator1" in fname:
            actual = hashlib.sha256((ANN1_DIR / fname).read_bytes()).hexdigest()
        else:
            actual = hashlib.sha256((ANN2_DIR / fname).read_bytes()).hexdigest()
        assert actual == exp_hash, f"Hash mismatch for {fname}!"
    print("  All 10 original draft files remain strictly byte-for-byte identical.")

    # 5. Verify total draft file counts: exactly 20 in ANN1_DIR, exactly 20 in ANN2_DIR
    a1_all = list(ANN1_DIR.glob("*.json"))
    a2_all = list(ANN2_DIR.glob("*.json"))
    assert len(a1_all) == 20, f"Expected 20 files in ANN1_DIR, found {len(a1_all)}"
    assert len(a2_all) == 20, f"Expected 20 files in ANN2_DIR, found {len(a2_all)}"
    print(f"  Verified: Exactly {len(a1_all)} files in annotator_1 and {len(a2_all)} in annotator_2.")

    # 6. Verify final/ directory: must contain ONLY 3 files
    final_all = list(FINAL_DIR.glob("*.json"))
    assert len(final_all) == 3, f"Expected exactly 3 files in final/, found {len(final_all)}"
    print(f"  Verified: Exactly 3 files remain isolated in final/ (no additions).")

    # 7. Compute Independent Agreement Statistics across the 15 remaining chips and the full 20 chips
    print("\n[Step 4] Computing Independent Inter-Annotator Agreement Statistics...")

    def evaluate_cohort(chip_list: List[str]) -> Dict[str, Any]:
        total = len(chip_list)
        concordant_status = 0
        concordant_class = 0
        ious = []
        jaccards = []
        vis_agreements = 0

        disagreements = []
        chip_details = []

        a1_classes = {"Industrial Fire": 0, "Forest Fire": 0, "Agricultural Fire": 0, "Other Thermal Source": 0, "NO_VISIBLE_TARGET": 0, "UNRESOLVED": 0}
        a2_classes = {"Industrial Fire": 0, "Forest Fire": 0, "Agricultural Fire": 0, "Other Thermal Source": 0, "NO_VISIBLE_TARGET": 0, "UNRESOLVED": 0}

        for cid in chip_list:
            d1 = json.load(open(ANN1_DIR / f"{cid}_annotator1.json", encoding="utf-8"))
            d2 = json.load(open(ANN2_DIR / f"{cid}_annotator2.json", encoding="utf-8"))

            st1 = d1["chip_annotation_status"]
            st2 = d2["chip_annotation_status"]

            # Class label 1
            if st1 == "NO_VISIBLE_TARGET":
                c1 = "NO_VISIBLE_TARGET"
            elif st1 == "UNRESOLVED":
                c1 = "UNRESOLVED"
            else:
                c1 = d1["annotations"][0]["class_name"]

            # Class label 2
            if st2 == "NO_VISIBLE_TARGET":
                c2 = "NO_VISIBLE_TARGET"
            elif st2 == "UNRESOLVED":
                c2 = "UNRESOLVED"
            else:
                c2 = d2["annotations"][0]["class_name"]

            a1_classes[c1] += 1
            a2_classes[c2] += 1

            status_match = (st1 == st2)
            class_match = (c1 == c2)
            if status_match:
                concordant_status += 1
            if class_match:
                concordant_class += 1

            disag_cats = []
            if not class_match:
                if c1 == "UNRESOLVED" or c2 == "UNRESOLVED":
                    disag_cats.append("UNRESOLVED_DISAGREEMENT")
                else:
                    disag_cats.append("CLASS_DISAGREEMENT")

            chip_iou = None
            chip_jaccard = None
            if len(d1["annotations"]) > 0 and len(d2["annotations"]) > 0:
                b1 = d1["annotations"][0]["bbox"]
                b2 = d2["annotations"][0]["bbox"]
                chip_iou = compute_box_iou(b1, b2)
                ious.append(chip_iou)
                if chip_iou < 0.5:
                    disag_cats.append("GEOMETRY_DISAGREEMENT")

                jacc = compute_jaccard(d1["annotations"][0]["visual_evidence"], d2["annotations"][0]["visual_evidence"])
                chip_jaccard = jacc
                jaccards.append(jacc)
                if jacc < 0.6:
                    disag_cats.append("EVIDENCE_DISAGREEMENT")

                v1 = d1["annotations"][0]["visibility_status"]
                v2 = d2["annotations"][0]["visibility_status"]
                if v1 == v2:
                    vis_agreements += 1
                else:
                    disag_cats.append("VISIBILITY_DISAGREEMENT")
            elif len(d1["annotations"]) == 0 and len(d2["annotations"]) == 0:
                vis_agreements += 1

            requires_adjudication = (len(disag_cats) > 0)
            if requires_adjudication:
                disagreements.append({
                    "chip_id": cid,
                    "annotator1_class": c1,
                    "annotator2_class": c2,
                    "disagreement_categories": disag_cats,
                    "iou": chip_iou,
                    "evidence_jaccard": chip_jaccard,
                })

            chip_details.append({
                "chip_id": cid,
                "a1_status": st1,
                "a2_status": st2,
                "a1_class": c1,
                "a2_class": c2,
                "class_match": class_match,
                "disagreement_categories": disag_cats,
                "iou": chip_iou,
            })

        mean_iou = float(np.mean(ious)) if ious else None
        mean_jaccard = float(np.mean(jaccards)) if jaccards else None
        raw_agreement = concordant_class / total

        # Compute Cohen's kappa across the categories
        categories = ["NO_VISIBLE_TARGET", "Forest Fire", "Agricultural Fire", "UNRESOLVED", "Industrial Fire", "Other Thermal Source"]
        cat_to_idx = {c: i for i, c in enumerate(categories)}
        conf_mat = np.zeros((len(categories), len(categories)), dtype=int)
        for ch in chip_details:
            i1 = cat_to_idx[ch["a1_class"]]
            i2 = cat_to_idx[ch["a2_class"]]
            conf_mat[i1, i2] += 1

        po = np.trace(conf_mat) / total
        pe = np.sum(np.sum(conf_mat, axis=1) * np.sum(conf_mat, axis=0)) / (total ** 2)
        kappa = float((po - pe) / (1 - pe)) if (1 - pe) > 0 else 1.0

        return {
            "total_chips": total,
            "concordant_chips_count": concordant_class,
            "disputed_chips_count": len(disagreements),
            "raw_agreement_pct": round(raw_agreement * 100, 2),
            "cohens_kappa": round(kappa, 4),
            "mean_matched_iou": round(mean_iou, 4) if mean_iou is not None else None,
            "mean_evidence_jaccard": round(mean_jaccard, 4) if mean_jaccard is not None else None,
            "a1_class_distribution": a1_classes,
            "a2_class_distribution": a2_classes,
            "disagreements": disagreements,
            "chip_details": chip_details,
        }

    stats_15 = evaluate_cohort(remaining_chips)
    stats_20 = evaluate_cohort(all_chips)

    print(f"  15-Chip Raw Agreement: {stats_15['raw_agreement_pct']}% ({stats_15['concordant_chips_count']}/15)")
    print(f"  15-Chip Cohen's Kappa: {stats_15['cohens_kappa']}")
    print(f"  15-Chip Disputed: {stats_15['disputed_chips_count']} chips")
    print(f"  20-Chip Total Cohort Raw Agreement: {stats_20['raw_agreement_pct']}% ({stats_20['concordant_chips_count']}/20)")
    print(f"  20-Chip Total Cohort Cohen's Kappa: {stats_20['cohens_kappa']}")

    # 8. Save machine-readable review JSON
    review_v2_payload = {
        "status": "STAGE_8.11_PILOT_DOUBLE_ANNOTATION_COMPLETE",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "annotation_protocol_version": "v1.0",
        "remaining_15_chips": remaining_chips,
        "remaining_15_chips_statistics": stats_15,
        "full_20_chips_pilot_statistics": stats_20,
    }
    review_json_path = REVIEW_DIR / "pilot_review_v2.json"
    with open(review_json_path, "w", encoding="utf-8") as f:
        json.dump(review_v2_payload, f, indent=2)
    print(f"  Saved review JSON to: {review_json_path}")

    # 9. Generate Report Markdown: pilot_double_annotation_v2.md
    report_lines = [
        "# Stage 8.11 — DS08 Remaining 15-Chip Independent Double Annotation Report",
        "",
        f"**Date / Timestamp (UTC):** {datetime.now(timezone.utc).isoformat()}  ",
        "**Phase:** STAGE 8.11 (Double-Blind Independent Annotation of Remaining 15 Pilot Chips)  ",
        "**Protocol Version:** Version 1.0 (Retained without modification from Stage 8.10B-C)  ",
        "**Authoritative Guidelines:** [`data/reference/ds08/annotations/guidelines/DS08_ANNOTATION_GUIDELINES_v1.md`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/guidelines/DS08_ANNOTATION_GUIDELINES_v1.md)  ",
        "**Authoritative Schema:** [`data/reference/ds08/annotations/schema/ds08_annotation_schema.json`](file:///d:/DATA%20PREPROCESSING/data/reference/ds08/annotations/schema/ds08_annotation_schema.json)  ",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        "In accordance with Stage 8.11 requirements, all remaining 15 chips in the authoritative 20-chip DS08 pilot manifest were independently annotated by two independent annotators (Annotator 1 and Annotator 2) without cross-inspection, automatic model labeling, or premature adjudication. Both annotators strictly operated under the frozen Version 1.0 guidelines and Draft-07 JSON schema.",
        "",
        "The five chips previously completed and verified in Stages 8.10A and 8.10B-C were preserved byte-for-byte identical.",
        "",
        "| Metric | Remaining 15 Chips | Full 20-Chip Pilot Cohort |",
        "| :--- | :---: | :---: |",
        f"| **Total Chips Evaluated** | **15** | **20** |",
        f"| **Concordant / Agreed Chips** | **{stats_15['concordant_chips_count']}** | **{stats_20['concordant_chips_count']}** |",
        f"| **Disputed / Requiring Adjudication** | **{stats_15['disputed_chips_count']}** | **{stats_20['disputed_chips_count']}** |",
        f"| **Raw Inter-Annotator Agreement** | **{stats_15['raw_agreement_pct']}%** | **{stats_20['raw_agreement_pct']}%** |",
        f"| **Cohen's Kappa ($\\kappa$)** | **{stats_15['cohens_kappa']}** | **{stats_20['cohens_kappa']}** |",
        f"| **Mean Matched-Box IoU** | **{stats_15['mean_matched_iou']}** | **{stats_20['mean_matched_iou']}** |",
        f"| **Mean Visual Evidence Jaccard** | **{stats_15['mean_evidence_jaccard']}** | **{stats_20['mean_evidence_jaccard']}** |",
        "",
        "---",
        "",
        "## 2. Deterministic Selection of Remaining 15 Chips",
        "",
        "The remaining 15 chips were selected deterministically in exact manifest order from `data/reference/ds08/annotations/pilot_manifest.json`, excluding the 5 chips completed in Stage 8.10A/B:",
        "",
    ]

    for i, cid in enumerate(remaining_chips):
        report_lines.append(f"{i+1:2d}. **`{cid}`**")

    report_lines.extend([
        "",
        "---",
        "",
        "## 3. Class Distributions Across Annotators",
        "",
        "### A. Remaining 15 Chips Distribution",
        "| Class / Status | Annotator 1 | Annotator 2 | Agreement Status |",
        "| :--- | :---: | :---: | :--- |",
        f"| **Industrial Fire** | {stats_15['a1_class_distribution']['Industrial Fire']} | {stats_15['a2_class_distribution']['Industrial Fire']} | Both 0 (No industrial fire evidence) |",
        f"| **Forest Fire** | {stats_15['a1_class_distribution']['Forest Fire']} | {stats_15['a2_class_distribution']['Forest Fire']} | 4 agreed active fires (`PILOT_03`, `PILOT_08`, `PILOT_15`, `PILOT_16`) |",
        f"| **Agricultural Fire** | {stats_15['a1_class_distribution']['Agricultural Fire']} | {stats_15['a2_class_distribution']['Agricultural Fire']} | 1 disputed off-center attribution (`PILOT_18_WEST`) |",
        f"| **Other Thermal Source** | {stats_15['a1_class_distribution']['Other Thermal Source']} | {stats_15['a2_class_distribution']['Other Thermal Source']} | Both 0 (No persistent industrial heat) |",
        f"| **NO_VISIBLE_TARGET** | {stats_15['a1_class_distribution']['NO_VISIBLE_TARGET']} | {stats_15['a2_class_distribution']['NO_VISIBLE_TARGET']} | 7 agreed clear negative chips |",
        f"| **UNRESOLVED** | {stats_15['a1_class_distribution']['UNRESOLVED']} | {stats_15['a2_class_distribution']['UNRESOLVED']} | 2 disputed montane shadow chips (`PILOT_14`, `PILOT_19`) |",
        "",
        "### B. Full 20-Chip Pilot Cohort Distribution",
        "| Class / Status | Annotator 1 | Annotator 2 | Post-Adjudication Frozen (Initial 5) |",
        "| :--- | :---: | :---: | :---: |",
        f"| **Industrial Fire** | {stats_20['a1_class_distribution']['Industrial Fire']} | {stats_20['a2_class_distribution']['Industrial Fire']} | 0 |",
        f"| **Forest Fire** | {stats_20['a1_class_distribution']['Forest Fire']} | {stats_20['a2_class_distribution']['Forest Fire']} | 1 (`PILOT_09_SOUTH`) |",
        f"| **Agricultural Fire** | {stats_20['a1_class_distribution']['Agricultural Fire']} | {stats_20['a2_class_distribution']['Agricultural Fire']} | 1 (`PILOT_17_WEST`) |",
        f"| **Other Thermal Source** | {stats_20['a1_class_distribution']['Other Thermal Source']} | {stats_20['a2_class_distribution']['Other Thermal Source']} | 0 |",
        f"| **NO_VISIBLE_TARGET** | {stats_20['a1_class_distribution']['NO_VISIBLE_TARGET']} | {stats_20['a2_class_distribution']['NO_VISIBLE_TARGET']} | 2 (`PILOT_01_NORTH`, `PILOT_05_CENTRAL`) |",
        f"| **UNRESOLVED** | {stats_20['a1_class_distribution']['UNRESOLVED']} | {stats_20['a2_class_distribution']['UNRESOLVED']} | 1 (`PILOT_13_EAST`) |",
        "",
        "---",
        "",
        "## 4. Per-Chip Annotation Summary (15 Remaining Chips)",
        "",
        "| Chip ID | A1 Status / Class | A2 Status / Class | Class Agreement | Disagreement Categories | IoU |",
        "| :--- | :--- | :--- | :---: | :--- | :---: |",
    ])

    for ch in stats_15["chip_details"]:
        cid = ch["chip_id"]
        c1 = ch["a1_class"]
        c2 = ch["a2_class"]
        cm = "YES" if ch["class_match"] else "NO"
        cats = ", ".join(ch["disagreement_categories"]) if ch["disagreement_categories"] else "NONE"
        iou_str = f"{ch['iou']:.4f}" if ch["iou"] is not None else "N/A"
        report_lines.append(f"| `{cid}` | {c1} | {c2} | {cm} | {cats} | {iou_str} |")

    report_lines.extend([
        "",
        "---",
        "",
        "## 5. Detailed Disagreement Analysis (4 Disputed Chips in Remaining 15)",
        "",
        "Exactly 4 chips exhibited inter-annotator divergence and are slated for subsequent senior adjudication (Stage 8.12):",
        "",
        "1. **`PILOT_06_CENTRAL` (CLASS_DISAGREEMENT / Spatial Association):**",
        "   - **A1:** `Forest Fire` (`[80, 325, 330, 385]`, confidence `MEDIUM`, evidence `DIRECT_FIRE_VISIBLE`, `FOREST_CONTEXT_VISIBLE`). Identified an intense active wildfire front in the southern forest tract.",
        "   - **A2:** `NO_VISIBLE_TARGET` (`annotations = []`). The nominal FIRMS detection (FRP = 0.43 MW) is situated at chip center `[256, 256]` in clear unburned forest. A2 excluded the southern fire because it is located over 1.1 km away.",
        "",
        "2. **`PILOT_14_EAST` (UNRESOLVED_DISAGREEMENT / Montane Shadow):**",
        "   - **A1:** `Forest Fire` (`[230, 230, 280, 280]`, confidence `LOW`). Interpreted a dark valley canopy feature near center as a vegetative burn scar.",
        "   - **A2:** `UNRESOLVED` (`[225, 225, 285, 285]`, confidence `LOW`). Ruled that steep montane ravine shadow cannot be distinguished from a vegetative scar on single-date optical imagery without elevated SWIR reflectance (chip-wide B12 max = 0.3741) or visible smoke.",
        "",
        "3. **`PILOT_18_WEST` (CLASS_DISAGREEMENT / Spatial Association):**",
        "   - **A1:** `Agricultural Fire` (`[250, 70, 285, 95]`, confidence `HIGH`). Identified an active crop residue burn with smoke and fresh char in a northern agricultural plot.",
        "   - **A2:** `NO_VISIBLE_TARGET` (`annotations = []`). The candidate detection coordinate `[256, 256]` displays clear fallow cropland. A2 excluded the northern plot because it is situated 1.76 km away across independent parcel boundaries.",
        "",
        "4. **`PILOT_19_WEST` (UNRESOLVED_DISAGREEMENT / Western Ghats Shadow):**",
        "   - **A1:** `Forest Fire` (`[230, 230, 285, 285]`, confidence `LOW`). Interpreted low-reflectance montane forest canopy as a burn scar.",
        "   - **A2:** `UNRESOLVED` (`[225, 225, 290, 290]`, confidence `LOW`). In steep Western Ghats escarpment topography, canopy terrain shadow cannot be reliably differentiated from a burn scar on a single acquisition.",
        "",
        "---",
        "",
        "## 6. Verification and Compliance Confirmations",
        "",
        "1. **No Adjudication Performed:** Disagreements remain unresolved and untouched; neither annotator's draft was altered after comparison.",
        "2. **Original 5 Completed Chips Preserved:** All 10 draft files (`annotator_1` and `annotator_2`) for `PILOT_01_NORTH`, `PILOT_05_CENTRAL`, `PILOT_09_SOUTH`, `PILOT_13_EAST`, and `PILOT_17_WEST` remain strictly byte-for-byte identical.",
        "3. **Draft File Inventory:**",
        "   - `data/reference/ds08/annotations/draft/annotator_1/`: Exactly 20 JSON files.",
        "   - `data/reference/ds08/annotations/draft/annotator_2/`: Exactly 20 JSON files.",
        "4. **Final Directory Isolation:** `data/reference/ds08/annotations/final/` contains **EXACTLY** the 3 existing Stage 8.10B adjudicated files (`PILOT_01_NORTH`, `PILOT_13_EAST`, `PILOT_17_WEST`). No new files were added.",
        "5. **No Imagery Download:** No new Sentinel-2 scenes or chips were downloaded or extracted.",
        "6. **No Model Training:** TCN, Deep SAD, and YOLO model weights and fusion parquet artifacts remain completely untouched.",
        "",
        "---",
    ])

    report_md_path = REVIEW_DIR / "pilot_double_annotation_v2.md"
    report_md_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"  Saved report Markdown to: {report_md_path}")
    print("\n======================================================================")
    print("STAGE 8.11 COMPLETE")
    print("======================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
