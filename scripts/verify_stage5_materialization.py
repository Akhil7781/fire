"""
Stage 5 Verification Script: Materialization, Immutability, Annotations, Splits, and Predecessors.
Verifies all items requested by the user:
1. Frozen FIRMS immutability (1,175,795 rows x 51 columns).
2. DS_02/DS_03/DS_04/DS_05 artifact integrity with reconciled terminology.
3. Image existence, readability, dimensions, channels (DS_06 and DS_07).
4. Annotation integrity (classes, [0, 1] bounds, denormalization, zero orphan images/labels).
5. Split scene-level isolation (train, val, test).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from PIL import Image

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")


def verify_frozen_firms():
    print("=== 1. Frozen FIRMS Immutability Check ===")
    causal_path = PROJECT_ROOT / "data" / "interim" / "causal_features_2025.parquet"
    assert causal_path.exists(), "causal_features_2025.parquet missing!"
    df = pd.read_parquet(causal_path)
    assert df.shape == (1_175_795, 51), f"Shape mismatch: {df.shape}"
    assert "detection_id" in df.columns
    assert "partition" in df.columns
    splits = df["partition"].value_counts().to_dict()
    print(f"  Shape: {df.shape} (1,175,795 rows x 51 columns) [VERIFIED INTACT]")
    print(f"  Deployment Splits: {splits}")


def verify_predecessor_artifacts():
    print("=== 2. Predecessor Artifacts Integrity & Terminology Reconciliation ===")
    # DS_05: 2 industrial detections belonging to 1 physical industrial incident
    ds05_path = PROJECT_ROOT / "data" / "labeling" / "ds05" / "ds05_valid_industrial_anchors.parquet"
    assert ds05_path.exists()
    df_ds05 = pd.read_parquet(ds05_path)
    assert len(df_ds05) == 2, f"DS05 count mismatch: {len(df_ds05)}"
    print(f"  DS_05: {len(df_ds05)} industrial detections belonging to 1 physical industrial incident [VERIFIED]")

    # DS_03: 19 FIRMS detections across 6 physical forest fire events
    ds03_path = PROJECT_ROOT / "data" / "labeling" / "ds03" / "forest_fire_candidates.parquet"
    assert ds03_path.exists()
    df_ds03 = pd.read_parquet(ds03_path)
    assert len(df_ds03) == 19, f"DS03 count mismatch: {len(df_ds03)}"
    num_ds03_events = df_ds03["fire_event_id"].nunique()
    assert num_ds03_events == 6, f"DS03 physical events mismatch: {num_ds03_events}"
    print(f"  DS_03: {len(df_ds03)} FIRMS detections across {num_ds03_events} physical forest fire events [VERIFIED]")

    # DS_04: 18 detections across 6 physical agricultural fire events
    ds04_path = PROJECT_ROOT / "data" / "labeling" / "ds04" / "agriculture_fire_candidates.parquet"
    assert ds04_path.exists()
    df_ds04 = pd.read_parquet(ds04_path)
    assert len(df_ds04) == 18, f"DS04 count mismatch: {len(df_ds04)}"
    num_ds04_events = df_ds04["fire_event_id"].nunique()
    assert num_ds04_events == 6, f"DS04 physical events mismatch: {num_ds04_events}"
    print(f"  DS_04: {len(df_ds04)} detections across {num_ds04_events} physical agricultural fire events [VERIFIED]")

    # DS_02: 481 temporal SEQUENCES across 20 physical events
    ds02_path = PROJECT_ROOT / "data" / "labeling" / "ds02" / "temporal_event_manifest.parquet"
    assert ds02_path.exists()
    df_ds02 = pd.read_parquet(ds02_path)
    assert len(df_ds02) == 481, f"DS02 sequences mismatch: {len(df_ds02)}"
    num_ds02_events = df_ds02["event_id"].nunique()
    assert num_ds02_events == 20, f"DS02 physical events mismatch: {num_ds02_events}"
    print(f"  DS_02: {len(df_ds02)} temporal SEQUENCES across {num_ds02_events} physical events [VERIFIED]")


def verify_image_materialization(ds_name: str, ref_dir: Path):
    print(f"=== 3. Image Materialization Verification: {ds_name} ===")
    manifest_path = ref_dir / f"{ds_name.lower()}_manifest.parquet"
    manifest = pd.read_parquet(manifest_path)
    images_dir = ref_dir / "images"
    anno_dir = ref_dir / "annotations_yolo"

    assert len(manifest) == 120, f"Manifest count mismatch: {len(manifest)}"

    metadata_records = len(manifest)
    actual_image_files = len(list(images_dir.glob("*.png")))
    anno_files = len(list(anno_dir.glob("*.txt")))

    assert actual_image_files == 120, f"Image count mismatch: {actual_image_files}"
    assert anno_files == 120, f"Annotation file count mismatch: {anno_files}"

    readable_count = 0
    zero_obj_count = 0

    for _, row in manifest.iterrows():
        img_path = PROJECT_ROOT / row["image_path"]
        assert img_path.exists(), f"Image missing: {img_path}"
        assert row["image_exists"] is True

        with Image.open(img_path) as im:
            w, h = im.size
            bands = im.getbands()
            assert (w, h) == (800, 800), f"Size mismatch for {img_path}: {(w, h)}"
            assert len(bands) == 3, f"Channel count mismatch for {img_path}: {len(bands)}"
            readable_count += 1

        if row["num_annotations"] == 0:
            zero_obj_count += 1

    print(f"  Metadata Records: {metadata_records}")
    print(f"  Actual Image Files: {actual_image_files}")
    print(f"  Readable Image Files: {readable_count}")
    print(f"  Annotated Images: {metadata_records - zero_obj_count}")
    print(f"  Images with Zero Target Objects: {zero_obj_count}")
    print(f"  Format / Dimensions / Channels: PNG / 800x800 / 3 (RGB) [VERIFIED]")


def verify_yolo_annotations(ds_name: str, ref_dir: Path, valid_class_ids: set, class_mapping: dict):
    print(f"=== 4. YOLO Annotation Integrity Check: {ds_name} ===")
    boxes_path = ref_dir / f"{ds_name.lower()}_boxes.parquet"
    boxes = pd.read_parquet(boxes_path)
    anno_dir = ref_dir / "annotations_yolo"
    manifest = pd.read_parquet(ref_dir / f"{ds_name.lower()}_manifest.parquet")

    # Class IDs
    unique_classes = set(boxes["class_id"].unique())
    assert unique_classes == valid_class_ids, f"Invalid class IDs: {unique_classes} vs {valid_class_ids}"

    # Normalized bounds and denormalization
    for _, b in boxes.iterrows():
        xc, yc, w, h = b["x_center"], b["y_center"], b["width"], b["height"]
        assert 0.0 <= xc <= 1.0, f"xc out of bounds: {xc}"
        assert 0.0 <= yc <= 1.0, f"yc out of bounds: {yc}"
        assert 0.0 < w <= 1.0, f"w out of bounds: {w}"
        assert 0.0 < h <= 1.0, f"h out of bounds: {h}"

        x_min = (xc - w / 2.0) * 800.0
        y_min = (yc - h / 2.0) * 800.0
        x_max = (xc + w / 2.0) * 800.0
        y_max = (yc + h / 2.0) * 800.0

        assert x_min >= -1e-4 and y_min >= -1e-4, f"Box underflow: {x_min}, {y_min}"
        assert x_max <= 800.0 + 1e-4 and y_max <= 800.0 + 1e-4, f"Box overflow: {x_max}, {y_max}"

    # No malformed lines, no orphans
    img_stems = set(f.stem for f in (ref_dir / "images").glob("*.png"))
    lbl_stems = set(f.stem for f in anno_dir.glob("*.txt"))
    assert img_stems == lbl_stems, "Orphan images or labels detected!"
    assert len(lbl_stems) == 120

    total_lines = 0
    for txt_file in anno_dir.glob("*.txt"):
        with open(txt_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        total_lines += len(lines)
        for line in lines:
            parts = line.split()
            assert len(parts) == 5, f"Malformed line in {txt_file}: {line}"
            cls_id = int(parts[0])
            assert cls_id in valid_class_ids, f"Invalid class ID in {txt_file}: {cls_id}"

    assert total_lines == len(boxes), f"Line count {total_lines} != box count {len(boxes)}"
    print(f"  Total Valid Annotations: {len(boxes)} across {len(manifest)} chips")
    print(f"  Class Distribution: {boxes['class_name'].value_counts().to_dict()}")
    print(f"  Orphan Images: 0 | Orphan Labels: 0 | Malformed Lines: 0 [VERIFIED]")


def verify_splits(ds_name: str, ref_dir: Path):
    print(f"=== 5. Scene-Level Split Leakage Check: {ds_name} ===")
    manifest = pd.read_parquet(ref_dir / f"{ds_name.lower()}_manifest.parquet")

    unique_scenes = manifest["scene_id"].nunique()
    train_df = manifest[manifest["partition"] == "train"]
    val_df = manifest[manifest["partition"] == "val"]
    test_df = manifest[manifest["partition"] == "test"]

    train_scenes = set(train_df["scene_id"])
    val_scenes = set(val_df["scene_id"])
    test_scenes = set(test_df["scene_id"])

    assert train_scenes.isdisjoint(val_scenes), "Train and Val scene leakage!"
    assert train_scenes.isdisjoint(test_scenes), "Train and Test scene leakage!"
    assert val_scenes.isdisjoint(test_scenes), "Val and Test scene leakage!"

    assert unique_scenes == 24
    assert len(train_scenes) == 16
    assert len(val_scenes) == 4
    assert len(test_scenes) == 4

    print(f"  Unique Scenes: {unique_scenes}")
    print(f"  Train: {len(train_scenes)} scenes, {len(train_df)} images, {train_df['num_annotations'].sum()} boxes")
    print(f"  Val:   {len(val_scenes)} scenes, {len(val_df)} images, {val_df['num_annotations'].sum()} boxes")
    print(f"  Test:  {len(test_scenes)} scenes, {len(test_df)} images, {test_df['num_annotations'].sum()} boxes")
    print(f"  Cross-Split Scene Leakage: PASSED_STRICT_SCENE_ISOLATION (0 scene overlaps)")


if __name__ == "__main__":
    verify_frozen_firms()
    verify_predecessor_artifacts()

    # DS_06
    verify_image_materialization("dior_infra", PROJECT_ROOT / "data" / "reference" / "ds06")
    verify_yolo_annotations("dior_infra", PROJECT_ROOT / "data" / "reference" / "ds06", {0, 1}, {0: "Storage_Tank", 1: "Chimney"})
    verify_splits("dior_infra", PROJECT_ROOT / "data" / "reference" / "ds06")

    # DS_07
    verify_image_materialization("fasdd_rs", PROJECT_ROOT / "data" / "reference" / "ds07")
    verify_yolo_annotations("fasdd_rs", PROJECT_ROOT / "data" / "reference" / "ds07", {0, 1}, {0: "Flame", 1: "Smoke"})
    verify_splits("fasdd_rs", PROJECT_ROOT / "data" / "reference" / "ds07")

    print("\nALL AUDIT & MATERIALIZATION CHECKS PASSED PERFECTLY!")
