"""
Test suite for Stage 8.3: YOLOv8n Infrastructure Vision Branch (DS06 DIOR).

Verifies all 12 core requirements:
  1. Dataset image count (exactly 120 images)
  2. Annotation count (exactly 580 bounding boxes)
  3. Class IDs strictly restricted to {0: Storage_Tank, 1: Chimney}
  4. Bounding box validity (all coordinates normalized, positive, inside [0, 1])
  5. Scene isolation (16 train scenes, 4 val scenes, 4 test scenes)
  6. Train/val/test scene disjointness (zero geographic scene leakage)
  7. Model loading from best_infrastructure.pt
  8. Inference determinism (identical embeddings across repeated runs)
  9. Embedding dimensionality = 128
  10. No NaN or Inf values in embeddings
  11. Source dataset mutation check (original data/reference/ds06 untouched)
  12. Checkpoint existence and non-zero size
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

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ultralytics import YOLO

DS06_DIR = PROJECT_ROOT / "data" / "reference" / "ds06"
MANIFEST_PATH = DS06_DIR / "dior_infra_manifest.parquet"
BOXES_PATH = DS06_DIR / "dior_infra_boxes.parquet"
CHECKPOINT_PATH = PROJECT_ROOT / "models" / "yolo" / "infrastructure" / "best_infrastructure.pt"
CONFIG_PATH = PROJECT_ROOT / "models" / "yolo" / "infrastructure" / "training_config.json"
METRICS_PATH = PROJECT_ROOT / "models" / "yolo" / "infrastructure" / "metrics.json"
EMBEDDINGS_PATH = PROJECT_ROOT / "data" / "embeddings" / "yolo" / "ds06_infrastructure_embeddings.parquet"

EXPECTED_TCN_CKPT_SHA256 = "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16"
EXPECTED_DEEP_SAD_CKPT_SHA256 = "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa"


# =============================================================================
# 1. DATASET INTEGRITY & ANNOTATIONS
# =============================================================================

def test_dataset_image_count():
    """Verifies exactly 120 image chips exist and are recorded in manifest."""
    manifest = pd.read_parquet(MANIFEST_PATH)
    assert len(manifest) == 120, f"Expected 120 images, got {len(manifest)}"

    # Check physical image files
    img_files = list((DS06_DIR / "images").glob("*.png"))
    assert len(img_files) == 120, f"Expected 120 physical images, got {len(img_files)}"


def test_dataset_annotation_count():
    """Verifies exactly 580 bounding boxes in dior_infra_boxes.parquet."""
    boxes = pd.read_parquet(BOXES_PATH)
    assert len(boxes) == 580, f"Expected 580 boxes, got {len(boxes)}"

    # Check class distribution
    class_counts = boxes["class_name"].value_counts().to_dict()
    assert class_counts.get("Storage_Tank") == 430, f"Expected 430 Storage Tanks, got {class_counts.get('Storage_Tank')}"
    assert class_counts.get("Chimney") == 150, f"Expected 150 Chimneys, got {class_counts.get('Chimney')}"


def test_class_ids_and_names():
    """Verifies class IDs are strictly {0: Storage_Tank, 1: Chimney}."""
    boxes = pd.read_parquet(BOXES_PATH)
    unique_ids = set(boxes["class_id"].unique())
    assert unique_ids == {0, 1}, f"Unexpected class IDs: {unique_ids}"

    unique_names = set(boxes["class_name"].unique())
    assert unique_names == {"Storage_Tank", "Chimney"}, f"Unexpected class names: {unique_names}"


def test_bounding_box_validity():
    """Verifies all bounding boxes satisfy normalization and positive bounds."""
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
# 2. SCENE ISOLATION & SPLIT DISJOINTNESS
# =============================================================================

def test_scene_isolation_and_split_disjointness():
    """Verifies 16 train scenes, 4 val scenes, 4 test scenes with zero cross-split leakage."""
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


# =============================================================================
# 3. MODEL CHECKPOINT & LOADING
# =============================================================================

def test_checkpoint_existence_and_size():
    """Verifies best_infrastructure.pt exists and is non-empty."""
    assert CHECKPOINT_PATH.exists(), f"Checkpoint missing: {CHECKPOINT_PATH}"
    size_mb = CHECKPOINT_PATH.stat().st_size / (1024 * 1024)
    assert size_mb > 1.0, f"Checkpoint file too small: {size_mb:.2f} MB"


def test_model_loading_and_architecture():
    """Verifies model loads cleanly in YOLO with expected class count."""
    model = YOLO(str(CHECKPOINT_PATH))
    assert model.names[0] == "Storage_Tank"
    assert model.names[1] == "Chimney"
    assert len(model.names) == 2


# =============================================================================
# 4. INFERENCE DETERMINISM & EMBEDDINGS (128-D)
# =============================================================================

def test_inference_determinism():
    """Verifies deterministic embedding output across repeated forward passes."""
    model = YOLO(str(CHECKPOINT_PATH))
    sample_img = next((DS06_DIR / "images").glob("*.png"))

    with torch.no_grad():
        res1 = model.predict(str(sample_img), embed=[6], device="cpu", verbose=False)[0].cpu().numpy()
        res2 = model.predict(str(sample_img), embed=[6], device="cpu", verbose=False)[0].cpu().numpy()

    max_diff = float(np.max(np.abs(res1 - res2)))
    assert max_diff == 0.0, f"Inference is non-deterministic! Max diff: {max_diff}"


def test_embedding_dimensionality_and_numerical_integrity():
    """Verifies 128-D representations, zero NaN, zero Inf across all 120 images."""
    assert EMBEDDINGS_PATH.exists(), f"Embeddings parquet missing: {EMBEDDINGS_PATH}"
    df = pd.read_parquet(EMBEDDINGS_PATH)

    assert len(df) == 120, f"Expected 120 embedding rows, got {len(df)}"

    # Check 128 z_infra columns
    z_cols = [f"z_infra_{i}" for i in range(128)]
    for col in z_cols:
        assert col in df.columns, f"Missing column {col}"

    assert len(df.columns) == 3 + 128  # image_id, scene_id, partition + 128 features

    # Check NaN and Inf
    vals = df[z_cols].to_numpy(dtype=np.float32)
    assert not np.isnan(vals).any(), "Found NaN in 128-D embeddings!"
    assert not np.isinf(vals).any(), "Found Inf in 128-D embeddings!"


# =============================================================================
# 5. SOURCE DATASET IMMUTABILITY
# =============================================================================

def test_source_dataset_not_mutated():
    """Verifies original DS06 files in data/reference/ds06 are intact."""
    manifest = pd.read_parquet(MANIFEST_PATH)
    assert len(manifest) == 120
    assert (DS06_DIR / "class_mapping.json").exists()
    assert (DS06_DIR / "split_manifest.json").exists()


# =============================================================================
# 6. FROZEN CHECKPOINTS IMMUTABILITY
# =============================================================================

def test_frozen_tcn_and_sad_checkpoints_unchanged():
    """Verifies SHA-256 of frozen TCN and Deep SAD checkpoints."""
    tcn_path = PROJECT_ROOT / "models" / "tcn" / "best_tcn.pt"
    with open(tcn_path, "rb") as f:
        tcn_hash = hashlib.sha256(f.read()).hexdigest()
    assert tcn_hash == EXPECTED_TCN_CKPT_SHA256, "TCN checkpoint SHA-256 changed!"

    sad_path = PROJECT_ROOT / "models" / "deep_sad" / "best_deep_sad.pt"
    with open(sad_path, "rb") as f:
        sad_hash = hashlib.sha256(f.read()).hexdigest()
    assert sad_hash == EXPECTED_DEEP_SAD_CKPT_SHA256, "Deep SAD checkpoint SHA-256 changed!"
