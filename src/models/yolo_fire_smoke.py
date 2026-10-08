"""
Stage 8.4: YOLOv8n Fire/Smoke Vision Branch (DS07 FASDD_RS).

Detects active combustion optical evidence (Flame, Smoke)
from satellite remote sensing optical chips.

CRITICAL SEMANTIC PRINCIPLE:
  Flame/smoke detection IS NOT fire-source class classification.
  Plume / combustion presence proves active burning dynamics, but DOES NOT
  by itself determine whether the fire is Industrial, Forest, or Agricultural.
  The detector answers strictly: "Is visible flame or smoke present in this optical chip?"
  It does NOT answer: "What economic sector or land-cover class is burning?"
  Source attribution is strictly a downstream multimodal fusion decision.

Invariants strictly enforced:
  1. Operates on real DS07 FASDD_RS benchmark (120 images, 24 scenes, 377 boxes).
  2. Scene-level split isolation: 16 train scenes (80 images), 4 val scenes (20 images),
     4 test scenes (20 images). Zero scene leakage across splits.
  3. Bounding box coordinates validated for [0, 1] normalization and positive dimensions.
  4. Original reference data in data/reference/ds07/ is preserved and untouched.
  5. Derived YOLO dataset created in data/derived/ds07_yolo/.
  6. Model architecture: YOLOv8n (3.16M params).
  7. Deterministic 128-D representation extraction: Layer 6 (C2f bottleneck, 128 channels)
     via native Ultralytics feature embedding.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import torch
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


CLASS_MAPPING = {
    0: "Flame",
    1: "Smoke",
}

EXPECTED_TRAIN_IMAGES = 80
EXPECTED_VAL_IMAGES = 20
EXPECTED_TEST_IMAGES = 20
EXPECTED_TOTAL_IMAGES = 120
EXPECTED_TOTAL_BOXES = 377


class YOLOFireSmokePipeline:
    """
    End-to-end pipeline for dataset conversion, training, evaluation,
    and 128-D latent representation extraction for DS07 Fire/Smoke YOLO.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root) if project_root else Path("d:/DATA PREPROCESSING")
        self.ds07_dir = self.project_root / "data" / "reference" / "ds07"
        self.derived_dir = self.project_root / "data" / "derived" / "ds07_yolo"
        self.models_dir = self.project_root / "models" / "yolo" / "fire_smoke"
        self.embeddings_dir = self.project_root / "data" / "embeddings" / "yolo"

        self.manifest_path = self.ds07_dir / "fasdd_rs_manifest.parquet"
        self.boxes_path = self.ds07_dir / "fasdd_rs_boxes.parquet"
        self.best_checkpoint_path = self.models_dir / "best_fire_smoke.pt"
        self.config_json_path = self.models_dir / "training_config.json"
        self.metrics_json_path = self.models_dir / "metrics.json"
        self.embeddings_parquet_path = self.embeddings_dir / "ds07_fire_smoke_embeddings.parquet"
        self.embeddings_summary_path = self.embeddings_dir / "ds07_fire_smoke_embeddings_summary.json"

    def audit_source_dataset(self) -> Dict[str, Any]:
        """
        Exhaustively audits DS07 against the frozen specification.
        """
        logger.info("Auditing DS07 source dataset...")
        assert self.manifest_path.exists(), f"Missing manifest: {self.manifest_path}"
        assert self.boxes_path.exists(), f"Missing boxes: {self.boxes_path}"

        manifest = pd.read_parquet(self.manifest_path)
        boxes = pd.read_parquet(self.boxes_path)

        # 1. Image and annotation counts
        num_images = len(manifest)
        num_boxes = len(boxes)
        assert num_images == EXPECTED_TOTAL_IMAGES, f"Expected {EXPECTED_TOTAL_IMAGES} images, got {num_images}"
        assert num_boxes == EXPECTED_TOTAL_BOXES, f"Expected {EXPECTED_TOTAL_BOXES} boxes, got {num_boxes}"

        # 2. Check classes
        class_counts = boxes["class_name"].value_counts().to_dict()
        assert class_counts.get("Flame") == 209, f"Expected 209 Flames, got {class_counts.get('Flame')}"
        assert class_counts.get("Smoke") == 168, f"Expected 168 Smokes, got {class_counts.get('Smoke')}"

        # 3. Scene isolation
        train_scenes = set(manifest[manifest["partition"] == "train"]["scene_id"])
        val_scenes = set(manifest[manifest["partition"] == "val"]["scene_id"])
        test_scenes = set(manifest[manifest["partition"] == "test"]["scene_id"])

        assert len(train_scenes) == 16, f"Expected 16 train scenes, got {len(train_scenes)}"
        assert len(val_scenes) == 4, f"Expected 4 val scenes, got {len(val_scenes)}"
        assert len(test_scenes) == 4, f"Expected 4 test scenes, got {len(test_scenes)}"

        assert not (train_scenes & val_scenes), "Train and Val scenes overlap!"
        assert not (train_scenes & test_scenes), "Train and Test scenes overlap!"
        assert not (val_scenes & test_scenes), "Val and Test scenes overlap!"

        # 4. Box coordinate validity
        invalid_coords = (
            (boxes["x_center"] < 0) | (boxes["x_center"] > 1) |
            (boxes["y_center"] < 0) | (boxes["y_center"] > 1) |
            (boxes["width"] <= 0) | (boxes["width"] > 1) |
            (boxes["height"] <= 0) | (boxes["height"] > 1)
        ).sum()
        assert invalid_coords == 0, f"Found {invalid_coords} out-of-bounds bounding boxes!"

        audit_summary = {
            "num_images": num_images,
            "num_boxes": num_boxes,
            "class_distribution": class_counts,
            "train_scenes": len(train_scenes),
            "val_scenes": len(val_scenes),
            "test_scenes": len(test_scenes),
            "scene_isolation_verified": True,
            "bounding_boxes_valid": True,
        }
        logger.info(f"DS07 audit successful: {audit_summary}")
        return audit_summary

    def prepare_yolo_dataset(self) -> Path:
        """
        Creates standard YOLOv8 directory structure in data/derived/ds07_yolo/
        without altering any original source files.
        """
        logger.info("Preparing derived YOLO dataset in data/derived/ds07_yolo/...")
        self.derived_dir.mkdir(parents=True, exist_ok=True)

        for split in ("train", "val", "test"):
            (self.derived_dir / "images" / split).mkdir(parents=True, exist_ok=True)
            (self.derived_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

        manifest = pd.read_parquet(self.manifest_path)

        for _, row in manifest.iterrows():
            img_id = row["image_id"]
            partition = row["partition"]

            src_img = self.ds07_dir / "images" / f"{img_id}.png"
            src_lbl = self.ds07_dir / "annotations_yolo" / f"{img_id}.txt"

            dst_img = self.derived_dir / "images" / partition / f"{img_id}.png"
            dst_lbl = self.derived_dir / "labels" / partition / f"{img_id}.txt"

            if not dst_img.exists() or dst_img.stat().st_size != src_img.stat().st_size:
                shutil.copy2(src_img, dst_img)
            if not dst_lbl.exists() or dst_lbl.stat().st_size != src_lbl.stat().st_size:
                shutil.copy2(src_lbl, dst_lbl)

        yaml_path = self.derived_dir / "ds07_yolo.yaml"
        yaml_content = (
            f"path: {self.derived_dir.resolve().as_posix()}\n"
            f"train: images/train\n"
            f"val: images/val\n"
            f"test: images/test\n"
            f"names:\n"
            f"  0: Flame\n"
            f"  1: Smoke\n"
        )
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        logger.info(f"Derived YOLO dataset prepared with YAML at {yaml_path}")
        return yaml_path

    def train_model(
        self,
        epochs: int = 15,
        imgsz: int = 640,
        batch: int = 8,
        seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Trains YOLOv8n on DS07 train split and selects best checkpoint on val split.
        """
        yaml_path = self.prepare_yolo_dataset()
        self.models_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing YOLOv8n for Fire/Smoke training ({epochs} epochs, batch {batch}, imgsz {imgsz})...")
        model = YOLO("yolov8n.pt")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Hardware execution device: {device} (PyTorch {torch.__version__})")

        start_time = time.time()
        train_results = model.train(
            data=yaml_path.as_posix(),
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            seed=seed,
            deterministic=True,
            device=device,
            project=str(self.models_dir / "runs"),
            name="train_run",
            exist_ok=True,
            verbose=False,
            val=True,
            plots=False,
        )
        training_duration = time.time() - start_time
        logger.info(f"Training completed in {training_duration:.2f} seconds.")

        # Locate best checkpoint produced by ultralytics
        run_best_ckpt = self.models_dir / "runs" / "train_run" / "weights" / "best.pt"
        if not run_best_ckpt.exists():
            run_best_ckpt = self.models_dir / "runs" / "train_run" / "weights" / "last.pt"

        shutil.copy2(run_best_ckpt, self.best_checkpoint_path)
        logger.info(f"Best checkpoint saved to {self.best_checkpoint_path}")

        # Record training configuration
        config_record = {
            "model_architecture": "YOLOv8n-Fire/Smoke (Ultralytics)",
            "base_weights": "yolov8n.pt",
            "epochs": epochs,
            "batch_size": batch,
            "image_size": imgsz,
            "random_seed": seed,
            "device": device,
            "pytorch_version": torch.__version__,
            "ultralytics_version": "8.4.163",
            "training_duration_seconds": round(training_duration, 2),
            "num_classes": 2,
            "classes": CLASS_MAPPING,
            "train_images": EXPECTED_TRAIN_IMAGES,
            "val_images": EXPECTED_VAL_IMAGES,
            "test_images": EXPECTED_TEST_IMAGES,
            "dataset_yaml": yaml_path.as_posix(),
        }
        with open(self.config_json_path, "w", encoding="utf-8") as f:
            json.dump(config_record, f, indent=2)

        return config_record

    def evaluate_model(self) -> Dict[str, Any]:
        """
        Evaluates best model separately on TRAIN, VAL, and TEST splits.
        Computes Precision, Recall, mAP50, and mAP50-95 overall and per class.
        """
        logger.info(f"Evaluating {self.best_checkpoint_path} across train, val, test splits...")
        model = YOLO(self.best_checkpoint_path)
        yaml_path = self.derived_dir / "ds07_yolo.yaml"

        splits_metrics: Dict[str, Any] = {}

        for split in ("train", "val", "test"):
            logger.info(f"Running validation on split: {split}...")
            val_res = model.val(
                data=yaml_path.as_posix(),
                split=split,
                imgsz=640,
                device="cpu",
                verbose=False,
                plots=False,
            )

            # Extract metrics
            p = float(val_res.results_dict.get("metrics/precision(B)", 0.0))
            r = float(val_res.results_dict.get("metrics/recall(B)", 0.0))
            map50 = float(val_res.results_dict.get("metrics/mAP50(B)", 0.0))
            map50_95 = float(val_res.results_dict.get("metrics/mAP50-95(B)", 0.0))

            # Per-class metrics
            per_class_map50 = val_res.box.ap50.tolist() if hasattr(val_res.box, "ap50") else []
            per_class_map50_95 = val_res.box.ap.tolist() if hasattr(val_res.box, "ap") else []

            splits_metrics[split] = {
                "precision": round(p, 4),
                "recall": round(r, 4),
                "mAP50": round(map50, 4),
                "mAP50_95": round(map50_95, 4),
                "per_class": {
                    "Flame": {
                        "mAP50": round(float(per_class_map50[0]), 4) if len(per_class_map50) > 0 else 0.0,
                        "mAP50_95": round(float(per_class_map50_95[0]), 4) if len(per_class_map50_95) > 0 else 0.0,
                    },
                    "Smoke": {
                        "mAP50": round(float(per_class_map50[1]), 4) if len(per_class_map50) > 1 else 0.0,
                        "mAP50_95": round(float(per_class_map50_95[1]), 4) if len(per_class_map50_95) > 1 else 0.0,
                    },
                },
            }
            logger.info(f"  {split.upper()}: Precision={p:.4f}, Recall={r:.4f}, mAP50={map50:.4f}, mAP50-95={map50_95:.4f}")

        eval_summary = {
            "status": "COMPLETED",
            "checkpoint": str(self.best_checkpoint_path),
            "metrics_by_split": splits_metrics,
        }

        with open(self.metrics_json_path, "w", encoding="utf-8") as f:
            json.dump(eval_summary, f, indent=2)
        logger.info(f"Saved evaluation metrics to {self.metrics_json_path}")
        return eval_summary

    def extract_128d_embeddings(self) -> pd.DataFrame:
        """
        Extracts deterministic 128-D fire/smoke representation z_Fire_Smoke
        from Layer 6 (C2f bottleneck, 128 channels) for all 120 DS07 images.
        """
        logger.info(f"Extracting 128-D visual representations using {self.best_checkpoint_path}...")
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        model = YOLO(self.best_checkpoint_path)

        manifest = pd.read_parquet(self.manifest_path)
        records = []

        for _, row in manifest.iterrows():
            img_id = row["image_id"]
            scene_id = row["scene_id"]
            partition = row["partition"]
            img_path = self.ds07_dir / "images" / f"{img_id}.png"

            # Predict with embed=[6] (Layer 6 C2f bottleneck in YOLOv8n has 128 channels)
            with torch.no_grad():
                res = model.predict(img_path.as_posix(), embed=[6], device="cpu", verbose=False)
                emb = res[0].cpu().numpy().astype(np.float32)

            assert emb.shape == (128,), f"Expected shape (128,), got {emb.shape}"
            assert not np.isnan(emb).any(), f"NaN in embedding for {img_id}"
            assert not np.isinf(emb).any(), f"Inf in embedding for {img_id}"

            rec = {
                "image_id": img_id,
                "scene_id": scene_id,
                "partition": partition,
            }
            for i in range(128):
                rec[f"z_fire_smoke_{i}"] = float(emb[i])
            records.append(rec)

        emb_df = pd.DataFrame(records)
        assert len(emb_df) == EXPECTED_TOTAL_IMAGES, f"Expected {EXPECTED_TOTAL_IMAGES} rows, got {len(emb_df)}"
        assert len(emb_df.columns) == 3 + 128, f"Expected 131 columns, got {len(emb_df.columns)}"

        table = pa.Table.from_pandas(emb_df, preserve_index=False)
        pq.write_table(table, self.embeddings_parquet_path, compression="zstd", compression_level=7)
        file_size_mb = self.embeddings_parquet_path.stat().st_size / (1024 * 1024)
        logger.info(f"Saved 128-D embeddings to {self.embeddings_parquet_path} ({file_size_mb:.2f} MB)")

        summary = {
            "status": "COMPLETED",
            "artifact_path": str(self.embeddings_parquet_path),
            "file_size_mb": round(file_size_mb, 2),
            "total_images": len(emb_df),
            "embedding_dimensions": 128,
            "layer_index": 6,
            "layer_type": "C2f (CSP Bottleneck with 2 convolutions, 128 channels)",
            "pooling_method": "Global Average Pooling (native Ultralytics embed)",
            "nan_inf_count": 0,
            "partition_counts": emb_df["partition"].value_counts().to_dict(),
        }
        with open(self.embeddings_summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        return emb_df

    def run_full_pipeline(self) -> Dict[str, Any]:
        """
        Executes audit, dataset prep, training, evaluation, and embedding extraction.
        """
        audit_res = self.audit_source_dataset()
        train_res = self.train_model(epochs=15, imgsz=640, batch=8, seed=42)
        eval_res = self.evaluate_model()
        emb_df = self.extract_128d_embeddings()

        return {
            "audit": audit_res,
            "training": train_res,
            "evaluation": eval_res,
            "embedding_rows": len(emb_df),
            "embedding_cols": len(emb_df.columns),
        }
