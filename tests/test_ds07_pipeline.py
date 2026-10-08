"""
Test suite for Stage 5B (DS_07): FASDD_RS Flame & Smoke Benchmark Pipeline (YOLOv8n-Fire/Smoke).
Verifies all 11 core invariants:
1. test_target_classes_strictly_restricted_to_flame_and_smoke
2. test_semantic_separation_flame_smoke_not_fire_source_class
3. test_bounding_boxes_strictly_normalized_and_valid
4. test_scene_level_partition_independence_zero_leakage
5. test_yolo_txt_annotation_files_exist_and_match_manifest
6. test_zero_exact_duplicates
7. test_external_benchmark_not_merged_into_india_ground_truth
8. test_frozen_firms_and_predecessor_artifacts_unchanged
9. test_actual_images_materialized_and_readable
10. test_annotation_image_one_to_one_mapping_no_orphans
11. test_denormalized_boxes_fit_within_image_boundaries
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

from src.labeling.ds07 import DS07Pipeline


@pytest.fixture(scope="module")
def ds07_data():
    """Runs DS07 pipeline and loads output artifacts."""
    pipeline = DS07Pipeline(PROJECT_ROOT)
    audit = pipeline.run_pipeline_and_audit()

    manifest = pd.read_parquet(PROJECT_ROOT / "data" / "reference" / "ds07" / "fasdd_rs_manifest.parquet")
    boxes = pd.read_parquet(PROJECT_ROOT / "data" / "reference" / "ds07" / "fasdd_rs_boxes.parquet")
    split_manifest = pd.read_parquet(PROJECT_ROOT / "data" / "reference" / "ds07" / "split_manifest.parquet")

    with open(PROJECT_ROOT / "data" / "reference" / "ds07" / "class_mapping.json", "r", encoding="utf-8") as f:
        class_mapping = json.load(f)

    with open(PROJECT_ROOT / "data" / "reference" / "ds07" / "ds07_audit.json", "r", encoding="utf-8") as f:
        audit_json = json.load(f)

    return {
        "audit": audit,
        "manifest": manifest,
        "boxes": boxes,
        "split_manifest": split_manifest,
        "class_mapping": class_mapping,
        "audit_json": audit_json,
    }


def test_target_classes_strictly_restricted_to_flame_and_smoke(ds07_data):
    """
    Invariant 1: Semantics strictly restricted to Flame (0) and Smoke (1).
    Zero other classes are present.
    """
    boxes = ds07_data["boxes"]
    class_mapping = ds07_data["class_mapping"]

    unique_classes = set(boxes["class_id"].unique())
    assert unique_classes == {0, 1}, f"Unexpected classes found in FASDD boxes: {unique_classes}"

    unique_names = set(boxes["class_name"].unique())
    assert unique_names == {"Flame", "Smoke"}

    assert class_mapping["num_classes"] == 2
    assert class_mapping["classes"] == {"0": "Flame", "1": "Smoke"}


def test_semantic_separation_flame_smoke_not_fire_source_class(ds07_data):
    """
    Invariant 2: Flame/smoke detection != fire-source class.
    Combustion plume presence is physical burning evidence, NOT sector attribution.
    """
    class_mapping = ds07_data["class_mapping"]
    audit_json = ds07_data["audit_json"]

    assert "Flame/smoke detection != fire-source class" in class_mapping["semantic_separation_statement"]
    assert "Flame/smoke detection != fire-source class" in audit_json["semantic_warning"]


def test_bounding_boxes_strictly_normalized_and_valid(ds07_data):
    """
    Invariant 3: Bounding boxes are strictly valid normalized coordinates in [0, 1].
    """
    boxes = ds07_data["boxes"]

    # All boxes must be marked valid
    assert boxes["is_valid"].all()

    xc = boxes["x_center"].to_numpy()
    yc = boxes["y_center"].to_numpy()
    w = boxes["width"].to_numpy()
    h = boxes["height"].to_numpy()

    assert np.all((xc >= 0.0) & (xc <= 1.0))
    assert np.all((yc >= 0.0) & (yc <= 1.0))
    assert np.all((w > 0.0) & (w <= 1.0))
    assert np.all((h > 0.0) & (h <= 1.0))

    # Corner checks
    assert np.all(xc - w / 2.0 >= 0.0)
    assert np.all(yc - h / 2.0 >= 0.0)
    assert np.all(xc + w / 2.0 <= 1.0)
    assert np.all(yc + h / 2.0 <= 1.0)


def test_scene_level_partition_independence_zero_leakage(ds07_data):
    """
    Invariant 4: Zero geographic scene leakage across train, val, and test splits.
    All images from a given scene_id reside strictly in one partition.
    """
    manifest = ds07_data["manifest"]
    scene_partitions = manifest.groupby("scene_id")["partition"].unique()

    for sc_id, parts in scene_partitions.items():
        assert len(parts) == 1, f"Scene {sc_id} split across multiple partitions: {parts}"

    train_scenes = set(manifest[manifest["partition"] == "train"]["scene_id"])
    val_scenes = set(manifest[manifest["partition"] == "val"]["scene_id"])
    test_scenes = set(manifest[manifest["partition"] == "test"]["scene_id"])

    assert train_scenes.isdisjoint(val_scenes), "Leakage between train and val scenes!"
    assert train_scenes.isdisjoint(test_scenes), "Leakage between train and test scenes!"
    assert val_scenes.isdisjoint(test_scenes), "Leakage between val and test scenes!"

    assert len(train_scenes) == 16
    assert len(val_scenes) == 4
    assert len(test_scenes) == 4


def test_yolo_txt_annotation_files_exist_and_match_manifest(ds07_data):
    """
    Invariant 5: For every image, a valid YOLO .txt file exists and matches box count.
    """
    manifest = ds07_data["manifest"]
    anno_dir = PROJECT_ROOT / "data" / "reference" / "ds07" / "annotations_yolo"

    for _, row in manifest.iterrows():
        img_id = row["image_id"]
        txt_path = anno_dir / f"{img_id}.txt"
        assert txt_path.exists(), f"Missing YOLO annotation file for {img_id}"

        with open(txt_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]

        assert len(lines) == row["num_annotations"]
        for line in lines:
            parts = line.split()
            assert len(parts) == 5, f"Malformed line in {txt_path}: {line}"
            cls_id = int(parts[0])
            assert cls_id in (0, 1)


def test_zero_exact_duplicates(ds07_data):
    """
    Invariant 6: Zero duplicate images based on SHA-256 digests.
    """
    manifest = ds07_data["manifest"]
    hashes = manifest["sha256_hash"].tolist()
    assert len(hashes) == len(set(hashes)), "Duplicate image hashes detected in DS_07!"


def test_external_benchmark_not_merged_into_india_ground_truth():
    """
    Invariant 7: External benchmark labels are not merged into India 2025 master labels.
    """
    ds07_dir = PROJECT_ROOT / "data" / "reference" / "ds07"
    assert ds07_dir.exists()

    master_label_path = PROJECT_ROOT / "data" / "processed" / "labels" / "master_labels_2025.parquet"
    if master_label_path.exists():
        df_master = pd.read_parquet(master_label_path)
        assert not df_master["detection_id"].str.startswith("FASDD_").any()


def test_frozen_firms_and_predecessor_artifacts_unchanged():
    """
    Invariant 8: Immutability of causal_features_2025.parquet and predecessor stages.
    """
    causal_path = PROJECT_ROOT / "data" / "interim" / "causal_features_2025.parquet"
    assert causal_path.exists()
    df_causal = pd.read_parquet(causal_path, columns=["detection_id", "partition"])
    assert len(df_causal) == 1_175_795, f"Row count changed: {len(df_causal)}"

    # Check DS_05: 2 industrial detections from 1 incident
    assert len(pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds05" / "ds05_valid_industrial_anchors.parquet")) == 2
    # Check DS_03: 19 FIRMS detections across 6 physical forest fire events
    assert len(pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds03" / "forest_fire_candidates.parquet")) == 19
    # Check DS_04: 18 detections across 6 physical agricultural fire events
    assert len(pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds04" / "agriculture_fire_candidates.parquet")) == 18
    # Check DS_02: 481 temporal SEQUENCES across 20 physical events
    assert len(pd.read_parquet(PROJECT_ROOT / "data" / "labeling" / "ds02" / "temporal_event_manifest.parquet")) == 481
    # Check DS_06: 120 images and 580 boxes
    assert len(pd.read_parquet(PROJECT_ROOT / "data" / "reference" / "ds06" / "dior_infra_manifest.parquet")) == 120
    assert len(pd.read_parquet(PROJECT_ROOT / "data" / "reference" / "ds06" / "dior_infra_boxes.parquet")) == 580


def test_actual_images_materialized_and_readable(ds07_data):
    """
    Invariant 9: All 120 image chips are physically materialized on disk,
    readable via PIL Image, with dimensions (800, 800) and 3 channels.
    """
    manifest = ds07_data["manifest"]
    assert len(manifest) == 120

    for _, row in manifest.iterrows():
        img_path = PROJECT_ROOT / row["image_path"]
        assert img_path.exists(), f"Image file missing on disk: {img_path}"
        assert row["image_exists"] is True
        assert row["image_is_readable"] is True

        with Image.open(img_path) as im:
            w, h = im.size
            bands = im.getbands()
            assert (w, h) == (800, 800), f"Incorrect dimensions for {img_path}: {(w, h)}"
            assert len(bands) == 3, f"Incorrect channel count for {img_path}: {len(bands)}"


def test_annotation_image_one_to_one_mapping_no_orphans(ds07_data):
    """
    Invariant 10: Annotation-to-image mapping is strictly 1:1.
    Zero orphan images and zero orphan annotation text files.
    """
    manifest = ds07_data["manifest"]
    images_dir = PROJECT_ROOT / "data" / "reference" / "ds07" / "images"
    anno_dir = PROJECT_ROOT / "data" / "reference" / "ds07" / "annotations_yolo"

    image_files = set(f.stem for f in images_dir.glob("*.png"))
    label_files = set(f.stem for f in anno_dir.glob("*.txt"))
    manifest_ids = set(manifest["image_id"])

    assert len(image_files) == 120
    assert len(label_files) == 120
    assert image_files == manifest_ids, "Image files do not match manifest IDs!"
    assert label_files == manifest_ids, "Label files do not match manifest IDs!"
    assert image_files == label_files, "Orphan images or labels detected!"


def test_denormalized_boxes_fit_within_image_boundaries(ds07_data):
    """
    Invariant 11: All bounding boxes fit strictly within [0, 800] after denormalization.
    """
    boxes = ds07_data["boxes"]
    w_px = 800
    h_px = 800

    for _, b in boxes.iterrows():
        x_min = (b["x_center"] - b["width"] / 2.0) * w_px
        y_min = (b["y_center"] - b["height"] / 2.0) * h_px
        x_max = (b["x_center"] + b["width"] / 2.0) * w_px
        y_max = (b["y_center"] + b["height"] / 2.0) * h_px

        assert x_min >= -1e-4, f"Box {b['box_id']} out of bounds left: {x_min}"
        assert y_min >= -1e-4, f"Box {b['box_id']} out of bounds top: {y_min}"
        assert x_max <= w_px + 1e-4, f"Box {b['box_id']} out of bounds right: {x_max}"
        assert y_max <= h_px + 1e-4, f"Box {b['box_id']} out of bounds bottom: {y_max}"
