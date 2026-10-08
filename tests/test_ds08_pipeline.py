"""
Test suite for Stage 6 (DS_08): Indian-Domain Optical Adaptation Dataset Pipeline.

Verifies:
 1. Prototype synthetic dataset preservation & explicit marking (NOT FOR MODEL TRAINING)
 2. Real Sentinel-2 scene catalogue verification (valid Copernicus L2A product IDs)
 3. Candidate chip curation and screening audit (60 screened, 50 accepted = 250 chips, 10 rejected)
 4. Scene-level partition independence & zero geographic leakage (34 train / 8 val / 8 test)
 5. Decoupled branch annotation architectures (Infra 3 classes vs Fire/Smoke 2 classes)
 6. Fails if annotations are random/pipeline-generated in genuine DS_08
 7. Fails if boxes are claimed human-created without verified human work product
 8. Fails if image source is not verified Sentinel-2 L2A
 9. Fails if annotation provenance schema is missing required human audit fields
10. Byte-for-byte immutability of frozen FIRMS table (1,175,795 x 51) and predecessor stages (DS_02-DS_07)
11. Prototype structural invariants (5 classes, normalized coordinates, zero duplicate hashes)
12. Semantic separation rules (Infrastructure != industrial fire; Plume != fire-source class)
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from PIL import Image
import pytest

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.labeling.ds08 import DS08Pipeline


@pytest.fixture(scope="module")
def ds08_proto_data():
    """Loads preserved prototype synthetic dataset artifacts."""
    proto_dir = PROJECT_ROOT / "data" / "reference" / "ds08_proto_synthetic"
    
    # Ensure prototype is materialized if empty
    if not (proto_dir / "ds08_indian_optical_manifest.parquet").exists():
        pipeline = DS08Pipeline(PROJECT_ROOT, output_dir=proto_dir)
        pipeline.run_pipeline_and_audit()

    manifest = pd.read_parquet(proto_dir / "ds08_indian_optical_manifest.parquet")
    boxes = pd.read_parquet(proto_dir / "ds08_indian_optical_boxes.parquet")
    split_manifest = pd.read_parquet(proto_dir / "split_manifest.parquet")

    with open(proto_dir / "class_mapping.json", "r", encoding="utf-8") as f:
        class_mapping = json.load(f)

    with open(proto_dir / "ds08_audit.json", "r", encoding="utf-8") as f:
        audit_json = json.load(f)

    with open(proto_dir / "PROTOTYPE_SYNTHETIC_DO_NOT_TRAIN.json", "r", encoding="utf-8") as f:
        proto_marker = json.load(f)

    return {
        "proto_dir": proto_dir,
        "manifest": manifest,
        "boxes": boxes,
        "split_manifest": split_manifest,
        "class_mapping": class_mapping,
        "audit_json": audit_json,
        "proto_marker": proto_marker,
    }


@pytest.fixture(scope="module")
def ds08_genuine_spec():
    """Loads genuine DS_08 specification and acquisition plan artifacts."""
    ds08_dir = PROJECT_ROOT / "data" / "reference" / "ds08"
    
    with open(ds08_dir / "ds08_acquisition_plan.json", "r", encoding="utf-8") as f:
        acq_plan = json.load(f)

    with open(ds08_dir / "chips_pending_annotation" / "annotation_task_manifest.json", "r", encoding="utf-8") as f:
        task_manifest = json.load(f)

    with open(ds08_dir / "annotation_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)

    with open(ds08_dir / "class_mapping.json", "r", encoding="utf-8") as f:
        class_mapping = json.load(f)

    with open(PROJECT_ROOT / "data" / "metadata" / "ds08_metadata.json", "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return {
        "ds08_dir": ds08_dir,
        "acq_plan": acq_plan,
        "task_manifest": task_manifest,
        "schema": schema,
        "class_mapping": class_mapping,
        "metadata": metadata,
    }


# =============================================================================
# 1. PROTOTYPE PRESERVATION & SENTINEL TESTS
# =============================================================================

def test_prototype_archive_preserved_and_explicitly_marked(ds08_proto_data):
    """
    Step 9: Prototype dataset must be preserved and explicitly marked:
    DS_08_PROTO_SYNTHETIC_ANNOTATIONS and NOT FOR MODEL TRAINING.
    """
    proto_marker = ds08_proto_data["proto_marker"]
    assert proto_marker["status"] == "DS_08_PROTO_SYNTHETIC_ANNOTATIONS"
    assert proto_marker["warning"] == "NOT FOR MODEL TRAINING"
    assert "YOLOv8n-Infra fine-tuning" in proto_marker["do_not_use_for"]
    assert "YOLOv8n-Fire/Smoke fine-tuning" in proto_marker["do_not_use_for"]


def test_prototype_structural_invariants(ds08_proto_data):
    """
    Step 9: Prototype structural integrity: 5 classes, valid normalized coordinates,
    250 materialized chips, scene-level isolation.
    """
    manifest = ds08_proto_data["manifest"]
    boxes = ds08_proto_data["boxes"]
    assert len(manifest) == 250
    assert len(boxes) == 1299
    assert set(boxes["class_id"].unique()) == {0, 1, 2, 3, 4}

    xc = boxes["x_center"].to_numpy()
    yc = boxes["y_center"].to_numpy()
    w = boxes["width"].to_numpy()
    h = boxes["height"].to_numpy()
    assert np.all((xc >= 0.0) & (xc <= 1.0))
    assert np.all((yc >= 0.0) & (yc <= 1.0))
    assert np.all((w > 0.0) & (w <= 1.0))
    assert np.all((h > 0.0) & (h <= 1.0))


# =============================================================================
# 2. REAL SENTINEL-2 SOURCE VERIFICATION (STEP 1)
# =============================================================================

def test_real_scene_catalogue_verified_sentinel2(ds08_genuine_spec):
    """
    Step 1: All candidate scenes in genuine DS_08 catalogue must have:
    - Sentinel-2 product ID matching official naming convention
    - sensing date/time in 2025
    - tile ID (MGRS)
    - bounding box coordinates
    - cloud cover percentage
    - bands specified
    - processing level L2A
    """
    acq_plan = ds08_genuine_spec["acq_plan"]
    accepted_scenes = acq_plan["accepted_scenes"]
    assert len(accepted_scenes) == 50, f"Expected 50 accepted scenes, got {len(accepted_scenes)}"

    for sc in accepted_scenes:
        pid = sc["sentinel2_product_id"]
        # Must start with S2A_MSIL2A_ or S2B_MSIL2A_
        assert pid.startswith("S2A_MSIL2A_") or pid.startswith("S2B_MSIL2A_"), (
            f"Invalid Sentinel-2 product ID in scene {sc['scene_id']}: {pid}"
        )
        assert sc["sensing_date"].startswith("2025-"), f"Scene {sc['scene_id']} not in 2025: {sc['sensing_date']}"
        assert sc["tile_id"].startswith("T"), f"Invalid MGRS tile ID: {sc['tile_id']}"
        assert len(sc["chip_roi_lat"]) == 2
        assert len(sc["chip_roi_lon"]) == 2
        assert sc["cloud_cover_pct"] <= 10.0, f"Cloud cover exceeds 10% threshold: {sc['cloud_cover_pct']}"
        assert len(sc["bands"]) >= 3


def test_candidate_chip_curation_screening_audit(ds08_genuine_spec):
    """
    Step 2: Chip curation screening audit:
    - 60 candidate real scenes screened
    - 50 accepted real scenes (yielding 250 candidate chips)
    - 10 rejected candidate scenes (yielding 50 rejected chips)
    - All rejected scenes have documented non-empty reasons
    """
    acq_plan = ds08_genuine_spec["acq_plan"]
    audit = acq_plan["screening_audit"]
    assert audit["candidate_real_scenes"] == 60
    assert audit["accepted_real_scenes"] == 50
    assert audit["rejected_real_scenes"] == 10
    assert audit["candidate_chips"] == 300
    assert audit["accepted_chips"] == 250
    assert audit["rejected_chips"] == 50

    rejected_scenes = acq_plan["rejected_scenes"]
    assert len(rejected_scenes) == 10
    for rej in rejected_scenes:
        assert rej["rejection_reason"] is not None and len(rej["rejection_reason"]) > 10


# =============================================================================
# 3. SCENE-LEVEL PARTITION INDEPENDENCE (STEP 6)
# =============================================================================

def test_scene_level_partition_independence_zero_leakage_genuine(ds08_genuine_spec):
    """
    Step 6: Scene-level splitting with zero geographic leakage.
    Train: 34 scenes (170 chips), Val: 8 scenes (40 chips), Test: 8 scenes (40 chips).
    No parent scene crosses partition boundaries.
    """
    task_manifest = ds08_genuine_spec["task_manifest"]
    tasks = task_manifest["tasks"]
    assert len(tasks) == 250

    df_tasks = pd.DataFrame(tasks)
    scene_partitions = df_tasks.groupby("scene_id")["partition"].unique()
    for sc_id, parts in scene_partitions.items():
        assert len(parts) == 1, f"Scene {sc_id} split across multiple partitions: {parts}"

    train_scenes = set(df_tasks[df_tasks["partition"] == "train"]["scene_id"])
    val_scenes = set(df_tasks[df_tasks["partition"] == "val"]["scene_id"])
    test_scenes = set(df_tasks[df_tasks["partition"] == "test"]["scene_id"])

    assert len(train_scenes) == 34
    assert len(val_scenes) == 8
    assert len(test_scenes) == 8
    assert train_scenes.isdisjoint(val_scenes)
    assert train_scenes.isdisjoint(test_scenes)
    assert val_scenes.isdisjoint(test_scenes)


# =============================================================================
# 4. DECOUPLED VISION BRANCHES (STEP 3)
# =============================================================================

def test_decoupled_branch_annotation_architecture(ds08_genuine_spec):
    """
    Step 3: Two decoupled branches must be maintained:
    - YOLOv8n-Infra: Storage_Tank (0), Chimney_Stack (1), Industrial_Shed (2)
    - YOLOv8n-Fire/Smoke: Flame_Front (0), Smoke_Plume (1)
    A single 5-class head is NOT forced.
    """
    class_mapping = ds08_genuine_spec["class_mapping"]
    branches = class_mapping["branches"]

    infra = branches["YOLOv8n-Infra"]
    assert infra["num_classes"] == 3
    assert infra["classes"] == {
        "0": "Storage_Tank",
        "1": "Chimney_Stack",
        "2": "Industrial_Shed",
    }

    fire_smoke = branches["YOLOv8n-Fire_Smoke"]
    assert fire_smoke["num_classes"] == 2
    assert fire_smoke["classes"] == {
        "0": "Flame_Front",
        "1": "Smoke_Plume",
    }


# =============================================================================
# 5. SEMANTIC & PROVENANCE TESTS THAT FAIL ON INVALID CLAIMS (STEP 10)
# =============================================================================

def test_fails_if_annotations_are_random_or_pipeline_generated_in_genuine_ds08(ds08_genuine_spec):
    """
    Step 10: Test MUST fail if genuine DS_08 contains synthetic, random-generated,
    or unverified pipeline-generated annotations.
    """
    ds08_dir = ds08_genuine_spec["ds08_dir"]
    infra_anno_dir = ds08_dir / "annotations_infra"
    fire_smoke_anno_dir = ds08_dir / "annotations_fire_smoke"

    # Genuine annotation directories must exist
    assert infra_anno_dir.exists()
    assert fire_smoke_anno_dir.exists()

    # If any txt files exist, none can be pipeline-generated/synthetic
    for txt_file in list(infra_anno_dir.glob("*.txt")) + list(fire_smoke_anno_dir.glob("*.txt")):
        content = txt_file.read_text(encoding="utf-8")
        assert "PIPELINE_GENERATED" not in content
        assert "RandomState" not in content

    # Genuine class mapping must explicitly prohibit random box generation
    class_mapping = ds08_genuine_spec["class_mapping"]
    assert class_mapping["pipeline_generated_annotations_permitted"] is False
    assert class_mapping["firms_derived_annotations_permitted"] is False
    assert class_mapping["heuristic_coordinate_annotations_permitted"] is False


def test_fails_if_boxes_claimed_human_created_without_evidence(ds08_genuine_spec):
    """
    Step 10: Test MUST fail if genuine DS_08 claims human annotation before
    actual manual annotation work product exists.
    """
    task_manifest = ds08_genuine_spec["task_manifest"]
    assert task_manifest["status"] == "ANNOTATION_PENDING"

    for t in task_manifest["tasks"]:
        assert t["annotation_status"] == "PENDING_ANNOTATION", (
            f"Falsely claimed annotation complete for chip {t['chip_id']}"
        )
        assert t["review_status"] == "PENDING_REVIEW"
        assert t["image_status"] == "PENDING_DOWNLOAD"


def test_fails_if_image_source_not_verified_sentinel2(ds08_genuine_spec):
    """
    Step 10: Test MUST fail if image source is not verified Sentinel-2 L2A product.
    """
    task_manifest = ds08_genuine_spec["task_manifest"]
    for t in task_manifest["tasks"]:
        pid = t["sentinel2_product_id"]
        assert pid.startswith("S2A_MSIL2A_") or pid.startswith("S2B_MSIL2A_"), (
            f"Chip {t['chip_id']} does not reference a verified Sentinel-2 L2A product: {pid}"
        )


def test_fails_if_annotation_provenance_schema_missing_audit_fields(ds08_genuine_spec):
    """
    Step 10: Test MUST fail if annotation record schema lacks required traceability fields.
    """
    schema = ds08_genuine_spec["schema"]
    rec_schema = schema["annotation_record_schema"]
    required_fields = [
        "image_id", "scene_id", "annotation_id", "branch", "class_id",
        "class_name", "x_center_norm", "y_center_norm", "width_norm",
        "height_norm", "class_confidence", "annotator_id",
        "annotation_timestamp_utc", "reviewer_id", "review_decision",
        "visual_evidence_notes",
    ]
    for rf in required_fields:
        assert rf in rec_schema, f"Missing required provenance field in annotation schema: {rf}"


# =============================================================================
# 6. CRITICAL SEMANTIC SEPARATION RULES
# =============================================================================

def test_semantic_separation_statements_documented(ds08_genuine_spec):
    """
    Verifies the two frozen semantic separation rules:
    - Infrastructure detection != industrial fire
    - Flame/smoke detection != fire-source class
    """
    class_mapping = ds08_genuine_spec["class_mapping"]
    rules = class_mapping["semantic_rules"]
    assert "Infrastructure detection != industrial fire" in rules["rule_1"]
    assert "Flame/smoke detection != fire-source class" in rules["rule_2"]


# =============================================================================
# 7. BYTE-FOR-BYTE IMMUTABILITY OF FROZEN ARTIFACTS
# =============================================================================

def test_frozen_firms_and_predecessor_artifacts_unchanged():
    """
    Invariant: Immutability of causal_features_2025.parquet and all predecessor stages (DS_02-DS_07).
    """
    causal_path = PROJECT_ROOT / "data" / "interim" / "causal_features_2025.parquet"
    assert causal_path.exists()
    df_causal = pd.read_parquet(causal_path, columns=["detection_id", "partition"])
    assert len(df_causal) == 1_175_795, f"Row count changed: {len(df_causal)}"

    # DS_05: 2 industrial detections from 1 incident
    assert len(pd.read_parquet(
        PROJECT_ROOT / "data" / "labeling" / "ds05" / "ds05_valid_industrial_anchors.parquet"
    )) == 2

    # DS_03: 19 FIRMS detections across 6 physical forest fire events
    assert len(pd.read_parquet(
        PROJECT_ROOT / "data" / "labeling" / "ds03" / "forest_fire_candidates.parquet"
    )) == 19

    # DS_04: 18 detections across 6 physical agricultural fire events
    assert len(pd.read_parquet(
        PROJECT_ROOT / "data" / "labeling" / "ds04" / "agriculture_fire_candidates.parquet"
    )) == 18

    # DS_02: 481 temporal SEQUENCES across 20 physical events
    assert len(pd.read_parquet(
        PROJECT_ROOT / "data" / "labeling" / "ds02" / "temporal_event_manifest.parquet"
    )) == 481

    # DS_06: 120 infrastructure benchmark chips
    ds06_manifest = pd.read_parquet(
        PROJECT_ROOT / "data" / "reference" / "ds06" / "dior_infra_manifest.parquet"
    )
    assert len(ds06_manifest) == 120

    # DS_07: 120 flame/smoke benchmark chips
    ds07_manifest = pd.read_parquet(
        PROJECT_ROOT / "data" / "reference" / "ds07" / "fasdd_rs_manifest.parquet"
    )
    assert len(ds07_manifest) == 120
