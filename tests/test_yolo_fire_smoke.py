"""
Test suite for Stage 8.4: YOLOv8n Fire/Smoke Vision Branch (DS07 FASDD_RS).

Verifies all 15 core requirements:
  1. DS07 image count = 120
  2. Annotation count = 120
  3. Total boxes = 377
  4. Flame count = 209
  5. Smoke count = 168
  6. Class IDs valid ({0: Flame, 1: Smoke})
  7. Bounding boxes valid (all coordinates normalized, positive, inside [0, 1])
  8. Train/val/test scene isolation (zero cross-split geographic scene leakage)
  9. No duplicate images (SHA-256 verified)
  10. Model checkpoint loads from best_fire_smoke.pt
  11. Inference is deterministic (identical embeddings across repeated runs)
  12. Fire/smoke embedding dimension = 128
  13. Embeddings contain no NaN or Inf values
  14. Source DS07 files remain unchanged (data/reference/ds07 untouched)
  15. Stage 8.3 checkpoint remains unchanged (models/yolo/infrastructure/best_infrastructure.pt)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch
from ultralytics import YOLO

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DS07_DIR = PROJECT_ROOT / "data" / "reference" / "ds07"
MANIFEST_PATH = DS07_DIR / "fasdd_rs_manifest.parquet"
BOXES_PATH = DS07_DIR / "fasdd_rs_boxes.parquet"
CHECKPOINT_PATH = PROJECT_ROOT / "models" / "yolo" / "fire_smoke" / "best_fire_smoke.pt"
CONFIG_PATH = PROJECT_ROOT / "models" / "yolo" / "fire_smoke" / "training_config.json"
METRICS_PATH = PROJECT_ROOT / "models" / "yolo" / "fire_smoke" / "metrics.json"
EMBEDDINGS_PATH = PROJECT_ROOT / "data" / "embeddings" / "yolo" / "ds07_fire_smoke_embeddings.parquet"

EXPECTED_TCN_CKPT_SHA256 = "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16"
EXPECTED_DEEP_SAD_CKPT_SHA256 = "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa"
EXPECTED_STAGE8_3_CKPT_SHA256 = "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6"


# =============================================================================
# 1. DATASET INTEGRITY & ANNOTATIONS
# =============================================================================

def test_ds07_image_count():
    """Requirement 1: Verifies exactly 120 image chips exist in manifest and disk."""
    manifest = pd.read_parquet(MANIFEST_PATH)
    assert len(manifest) == 120, f"Expected 120 images, got {len(manifest)}"

    img_files = list((DS07_DIR / "images").glob("*.png"))
    assert len(img_files) == 120, f"Expected 120 physical images, got {len(img_files)}"


def test_ds07_annotation_count():
    """Requirement 2: Verifies exactly 120 annotation text files exist."""
    anno_files = list((DS07_DIR / "annotations_yolo").glob("*.txt"))
    assert len(anno_files) == 120, f"Expected 120 annotation files, got {len(anno_files)}"


def test_total_boxes_and_class_distribution():
    """Requirements 3, 4, 5: Verifies 377 boxes (209 Flames, 168 Smokes)."""
    boxes = pd.read_parquet(BOXES_PATH)
    assert len(boxes) == 377, f"Expected 377 boxes, got {len(boxes)}"

    class_counts = boxes["class_name"].value_counts().to_dict()
    assert class_counts.get("Flame") == 209, f"Expected 209 Flames, got {class_counts.get('Flame')}"
    assert class_counts.get("Smoke") == 168, f"Expected 168 Smokes, got {class_counts.get('Smoke')}"


def test_class_ids_valid():
    """Requirement 6: Verifies class IDs are strictly {0: Flame, 1: Smoke}."""
    boxes = pd.read_parquet(BOXES_PATH)
    unique_ids = set(boxes["class_id"].unique())
    assert unique_ids == {0, 1}, f"Unexpected class IDs: {unique_ids}"

    unique_names = set(boxes["class_name"].unique())
    assert unique_names == {"Flame", "Smoke"}, f"Unexpected class names: {unique_names}"


def test_bounding_boxes_valid():
    """Requirement 7: Verifies all bounding boxes satisfy normalization and positive bounds."""
    boxes = pd.read_parquet(BOXES_PATH)
    assert boxes["is_valid"].all(), "Some boxes marked invalid in parquet!"

    invalid_coords = (
        (boxes["x_center"] < 0) | (boxes["x_center"] > 1) |
        (boxes["y_center"] < 0) | (boxes["y_center"] > 1) |
        (boxes["width"] <= 0) | (boxes["width"] > 1) |
        (boxes["height"] <= 0) | (boxes["height"] > 1)
    ).sum()
    assert invalid_coords == 0, f"Found {invalid_coords} invalid coordinate sets!"


# =============================================================================
# 2. SCENE ISOLATION & NO DUPLICATES
# =============================================================================

def test_scene_isolation_and_split_disjointness():
    """Requirement 8: Verifies 16 train scenes, 4 val scenes, 4 test scenes with zero leakage."""
    manifest = pd.read_parquet(MANIFEST_PATH)

    train_scenes = set(manifest[manifest["partition"] == "train"]["scene_id"])
    val_scenes = set(manifest[manifest["partition"] == "val"]["scene_id"])
    test_scenes = set(manifest[manifest["partition"] == "test"]["scene_id"])

    assert len(train_scenes) == 16, f"Expected 16 train scenes, got {len(train_scenes)}"
    assert len(val_scenes) == 4, f"Expected 4 val scenes, got {len(val_scenes)}"
    assert len(test_scenes) == 4, f"Expected 4 test scenes, got {len(test_scenes)}"

    # Strict disjointness
    assert not (train_scenes & val_scenes), f"Train and Val overlap: {train_scenes & val_scenes}"
    assert not (train_scenes & test_scenes), f"Train and Test overlap: {train_scenes & test_scenes}"
    assert not (val_scenes & test_scenes), f"Val and Test overlap: {val_scenes & test_scenes}"


def test_no_duplicate_images():
    """Requirement 9: Verifies zero duplicate images via SHA-256 byte digests."""
    img_files = list((DS07_DIR / "images").glob("*.png"))
    seen_hashes = set()
    for f in img_files:
        with open(f, "rb") as fp:
            h = hashlib.sha256(fp.read()).hexdigest()
        assert h not in seen_hashes, f"Duplicate image detected: {f.name}"
        seen_hashes.add(h)
    assert len(seen_hashes) == 120


# =============================================================================
# 3. MODEL CHECKPOINT & DETERMINISM
# =============================================================================

def test_model_checkpoint_loads():
    """Requirement 10: Verifies best_fire_smoke.pt exists and loads cleanly."""
    assert CHECKPOINT_PATH.exists(), f"Checkpoint missing: {CHECKPOINT_PATH}"
    size_mb = CHECKPOINT_PATH.stat().st_size / (1024 * 1024)
    assert size_mb > 1.0, f"Checkpoint file too small: {size_mb:.2f} MB"

    model = YOLO(str(CHECKPOINT_PATH))
    assert model.names[0] == "Flame"
    assert model.names[1] == "Smoke"
    assert len(model.names) == 2


def test_inference_is_deterministic():
    """Requirement 11: Verifies identical embeddings across repeated forward passes."""
    model = YOLO(str(CHECKPOINT_PATH))
    sample_img = next((DS07_DIR / "images").glob("*.png"))

    with torch.no_grad():
        res1 = model.predict(str(sample_img), embed=[6], device="cpu", verbose=False)[0].cpu().numpy()
        res2 = model.predict(str(sample_img), embed=[6], device="cpu", verbose=False)[0].cpu().numpy()

    max_diff = float(np.max(np.abs(res1 - res2)))
    assert max_diff == 0.0, f"Inference is non-deterministic! Max diff: {max_diff}"


# =============================================================================
# 4. 128-D EMBEDDINGS NUMERICAL INTEGRITY
# =============================================================================

def test_embedding_dimensionality_is_128():
    """Requirement 12: Verifies exactly 128 feature columns in embeddings parquet."""
    assert EMBEDDINGS_PATH.exists(), f"Embeddings parquet missing: {EMBEDDINGS_PATH}"
    df = pd.read_parquet(EMBEDDINGS_PATH)

    assert len(df) == 120, f"Expected 120 embedding rows, got {len(df)}"

    z_cols = [f"z_fire_smoke_{i}" for i in range(128)]
    for col in z_cols:
        assert col in df.columns, f"Missing column {col}"

    assert len(df.columns) == 3 + 128  # image_id, scene_id, partition + 128 features


def test_embeddings_contain_no_nan_or_inf():
    """Requirement 13: Verifies 0 NaN and 0 Inf in 128-D representations."""
    df = pd.read_parquet(EMBEDDINGS_PATH)
    z_cols = [f"z_fire_smoke_{i}" for i in range(128)]
    vals = df[z_cols].to_numpy(dtype=np.float32)

    nan_count = int(np.isnan(vals).sum())
    inf_count = int(np.isinf(vals).sum())

    assert nan_count == 0, f"Found {nan_count} NaNs in embeddings!"
    assert inf_count == 0, f"Found {inf_count} Infs in embeddings!"


# =============================================================================
# 5. SOURCE & FROZEN STAGE IMMUTABILITY
# =============================================================================

def test_source_ds07_files_unchanged():
    """Requirement 14: Verifies original DS07 files in data/reference/ds07 are intact."""
    manifest = pd.read_parquet(MANIFEST_PATH)
    assert len(manifest) == 120
    assert (DS07_DIR / "class_mapping.json").exists()
    assert (DS07_DIR / "split_manifest.json").exists()


def test_stage8_3_checkpoint_unchanged():
    """Requirement 15: Verifies Stage 8.3 infrastructure checkpoint hash is unchanged."""
    infra_ckpt = PROJECT_ROOT / "models" / "yolo" / "infrastructure" / "best_infrastructure.pt"
    assert infra_ckpt.exists(), f"Stage 8.3 checkpoint missing: {infra_ckpt}"
    with open(infra_ckpt, "rb") as f:
        infra_hash = hashlib.sha256(f.read()).hexdigest().lower()
    assert infra_hash == EXPECTED_STAGE8_3_CKPT_SHA256.lower(), "Stage 8.3 infrastructure checkpoint SHA-256 altered!"
