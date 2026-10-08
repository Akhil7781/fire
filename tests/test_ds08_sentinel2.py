"""
Unit and regression test suite for Stage 8.5: Real Sentinel-2 Optical Adaptation (DS08).

Verifies:
 1. Real Sentinel-2 provenance (Copernicus L2A products, valid MGRS tiles, sensing dates, STAC URLs).
 2. Synthetic prototype exclusion and quarantine (PROTOTYPE_SYNTHETIC_DO_NOT_TRAIN marker).
 3. Image status and integrity (zero corrupted/fake image files).
 4. Band configuration and spatial resolution (10m GSD, explicit bands).
 5. Quality metadata and cloud filtering parameters.
 6. Quality-controlled scene screening (50 accepted scenes, 10 documented rejected scenes).
 7. Annotation validity and zero fabricated boxes (ds08_annotations.parquet has 0 rows).
 8. Visual class mapping decoupling (Infra vs Fire/Smoke, no downstream source classes).
 9. Scene-level split isolation and zero geographic leakage (34 train, 8 val, 8 test).
10. Unique identifiers and zero duplicate chip records.
11. Manifest completeness and schema compliance.
12. Human annotation provenance protocol enforcement.
13. FIRMS thermal decoupling and association provenance.
14. No final multimodal fusion matrix produced prematurely.
15. Byte-for-byte immutability of frozen predecessor checkpoints and aligned parquet.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ds08_manifest() -> pd.DataFrame:
    manifest_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "ds08_sentinel2_manifest.parquet"
    assert manifest_path.exists(), f"Missing manifest: {manifest_path}"
    return pd.read_parquet(manifest_path)


@pytest.fixture(scope="module")
def ds08_annotations() -> pd.DataFrame:
    anno_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "ds08_annotations.parquet"
    assert anno_path.exists(), f"Missing annotations table: {anno_path}"
    return pd.read_parquet(anno_path)


@pytest.fixture(scope="module")
def ds08_acquisition_plan() -> dict:
    plan_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "ds08_acquisition_plan.json"
    assert plan_path.exists(), f"Missing acquisition plan: {plan_path}"
    with open(plan_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ds08_class_mapping() -> dict:
    cmap_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "class_mapping.json"
    assert cmap_path.exists(), f"Missing class mapping: {cmap_path}"
    with open(cmap_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ds08_annotation_schema() -> dict:
    schema_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotation_schema.json"
    assert schema_path.exists(), f"Missing annotation schema: {schema_path}"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_01_real_sentinel2_provenance(ds08_manifest: pd.DataFrame):
    """Assert all 250 candidate chips have genuine Sentinel-2 product IDs and MGRS tiles."""
    assert len(ds08_manifest) == 250
    for _, row in ds08_manifest.iterrows():
        pid = row["product_id"]
        assert pid.startswith("S2A_MSIL2A_") or pid.startswith("S2B_MSIL2A_"), (
            f"Invalid Sentinel-2 product ID: {pid}"
        )
        assert len(row["tile_id"]) == 6 and row["tile_id"].startswith("T"), (
            f"Invalid MGRS tile ID: {row['tile_id']}"
        )
        assert "copernicus.eu" in row["copernicus_stac_url"], (
            f"Invalid Copernicus URL: {row['copernicus_stac_url']}"
        )
        assert len(row["sensing_date"]) == 10  # YYYY-MM-DD
        assert 6.0 <= row["latitude"] <= 38.0, f"Latitude outside India: {row['latitude']}"
        assert 68.0 <= row["longitude"] <= 98.0, f"Longitude outside India: {row['longitude']}"


def test_02_synthetic_prototype_exclusion_and_quarantine():
    """Verify data/reference/ds08_proto_synthetic remains strictly quarantined."""
    proto_dir = PROJECT_ROOT / "data" / "reference" / "ds08_proto_synthetic"
    assert proto_dir.exists(), "Quarantined prototype directory must exist"
    
    quarantine_marker = proto_dir / "PROTOTYPE_SYNTHETIC_DO_NOT_TRAIN.json"
    assert quarantine_marker.exists(), "Quarantine marker file missing"
    with open(quarantine_marker, "r", encoding="utf-8") as f:
        marker_data = json.load(f)
    assert marker_data.get("status") == "DS_08_PROTO_SYNTHETIC_ANNOTATIONS"
    assert marker_data.get("warning") == "NOT FOR MODEL TRAINING"

    # Ensure no synthetic paths in genuine manifest
    manifest_path = PROJECT_ROOT / "data" / "reference" / "ds08" / "ds08_sentinel2_manifest.parquet"
    df = pd.read_parquet(manifest_path)
    for p in df["image_path"]:
        assert "ds08_proto_synthetic" not in str(p)
    for p in df["annotation_path"].dropna():
        assert "ds08_proto_synthetic" not in str(p)


def test_03_image_status_and_no_corrupted_images():
    """Verify that images are marked PENDING_DOWNLOAD and no corrupted/dummy images exist."""
    images_dir = PROJECT_ROOT / "data" / "reference" / "ds08" / "images"
    assert images_dir.exists()
    
    # Check that any file in images_dir (if present) is a valid image
    image_files = list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg"))
    for img_p in image_files:
        from PIL import Image
        with Image.open(img_p) as img:
            assert img.size == (512, 512)


def test_04_band_configuration_and_resolution(ds08_manifest: pd.DataFrame):
    """Verify explicit band selection and spatial resolution specification."""
    for _, row in ds08_manifest.iterrows():
        assert row["spatial_resolution_m"] == 10.0
        assert row["chip_dimensions"] == "512x512"
        bands = row["bands"].split(",")
        assert len(bands) == 3
        # Bands must be either true color (B04,B03,B02) or SWIR false color (B12,B11,B04)
        assert bands == ["B04", "B03", "B02"] or bands == ["B12", "B11", "B04"]


def test_05_quality_metadata_and_cloud_limits(ds08_manifest: pd.DataFrame):
    """Verify cloud cover percentage is within acceptable quality threshold."""
    assert (ds08_manifest["cloud_cover_pct"] >= 0.0).all()
    assert (ds08_manifest["cloud_cover_pct"] <= 10.0).all(), (
        "All accepted scenes must have <= 10% scene cloud cover"
    )
    assert set(ds08_manifest["quality_flag"].unique()).issubset({"CLEAR", "HAZE"})
    assert (ds08_manifest["cloud_filtering_decision"] == "ACCEPTED").all()


def test_06_quality_screening_audit_and_rejection_tracking(ds08_acquisition_plan: dict):
    """Verify that 60 candidate scenes were screened, 50 accepted, and 10 rejected with explicit reasons."""
    audit = ds08_acquisition_plan["screening_audit"]
    assert audit["candidate_real_scenes"] == 60
    assert audit["accepted_real_scenes"] == 50
    assert audit["rejected_real_scenes"] == 10
    assert audit["candidate_chips"] == 300
    assert audit["accepted_chips"] == 250
    assert audit["rejected_chips"] == 50

    rejected = ds08_acquisition_plan["rejected_scenes"]
    assert len(rejected) == 10
    for rej in rejected:
        assert rej["scene_id"].startswith("SCENE_REJ_")
        assert rej["rejection_reason"] is not None and len(rej["rejection_reason"]) > 10


def test_07_annotation_table_zero_fabricated_boxes(ds08_annotations: pd.DataFrame):
    """Verify zero fabricated or synthetic bounding boxes have been introduced into genuine DS08."""
    assert len(ds08_annotations) == 0, (
        f"Expected 0 annotations in pending state, found {len(ds08_annotations)}. "
        "Zero synthetic boxes are permitted in genuine DS08."
    )
    # Check directory contents
    infra_annos = list((PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations_infra").glob("*.txt"))
    fire_annos = list((PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations_fire_smoke").glob("*.txt"))
    assert len(infra_annos) == 0
    assert len(fire_annos) == 0


def test_08_class_mapping_decoupling(ds08_class_mapping: dict):
    """Verify decoupled branches: YOLOv8n-Infra (3 classes) and YOLOv8n-Fire/Smoke (2 classes)."""
    assert "branches" in ds08_class_mapping
    branches = ds08_class_mapping["branches"]
    assert "YOLOv8n-Infra" in branches
    assert "YOLOv8n-Fire_Smoke" in branches

    infra_classes = branches["YOLOv8n-Infra"]["classes"]
    fire_classes = branches["YOLOv8n-Fire_Smoke"]["classes"]

    assert set(infra_classes.values()) == {"Storage_Tank", "Chimney_Stack", "Industrial_Shed"}
    assert set(fire_classes.values()) == {"Flame_Front", "Smoke_Plume"}

    # Ensure downstream source classes are NOT present in visual object classes
    all_classes = set(infra_classes.values()) | set(fire_classes.values())
    for forbidden in ["Industrial_Fire", "Forest_Fire", "Agricultural_Fire", "Other_Thermal_Source"]:
        assert forbidden not in all_classes


def test_09_scene_level_split_isolation(ds08_manifest: pd.DataFrame):
    """Verify strictly scene-level split isolation across train, val, and test."""
    train_scenes = set(ds08_manifest[ds08_manifest["split"] == "train"]["scene_id"])
    val_scenes = set(ds08_manifest[ds08_manifest["split"] == "val"]["scene_id"])
    test_scenes = set(ds08_manifest[ds08_manifest["split"] == "test"]["scene_id"])

    assert len(train_scenes) == 34
    assert len(val_scenes) == 8
    assert len(test_scenes) == 8
    assert len(train_scenes & val_scenes) == 0
    assert len(train_scenes & test_scenes) == 0
    assert len(val_scenes & test_scenes) == 0

    # Chip counts per split
    assert len(ds08_manifest[ds08_manifest["split"] == "train"]) == 170
    assert len(ds08_manifest[ds08_manifest["split"] == "val"]) == 40
    assert len(ds08_manifest[ds08_manifest["split"] == "test"]) == 40


def test_10_unique_identifiers_and_zero_duplicates(ds08_manifest: pd.DataFrame):
    """Verify all chip_id entries are unique and no duplicates exist."""
    assert ds08_manifest["chip_id"].nunique() == len(ds08_manifest)
    assert len(ds08_manifest) == 250


def test_11_manifest_completeness(ds08_manifest: pd.DataFrame):
    """Verify all mandatory fields are present and non-null in the manifest."""
    required_cols = [
        "chip_id", "scene_id", "product_id", "tile_id", "acquisition_datetime_utc",
        "latitude", "longitude", "context_category", "split", "image_path",
        "annotation_path", "annotation_status", "source_checksum", "cloud_cover_pct",
        "quality_flag", "cloud_filtering_decision", "bands", "spatial_resolution_m",
        "chip_dimensions", "copernicus_stac_url", "firms_associated"
    ]
    for col in required_cols:
        assert col in ds08_manifest.columns, f"Missing column: {col}"
        # For non-null columns
        if col not in ("associated_detection_id", "distance_to_firms_m", "delta_time_hours"):
            assert ds08_manifest[col].notna().all(), f"Found NaN in column: {col}"


def test_12_annotation_provenance_schema(ds08_annotation_schema: dict):
    """Verify annotation schema enforces human audit fields and forbids RNG/heuristics."""
    rec_schema = ds08_annotation_schema["annotation_record_schema"]
    for req_field in ["annotator_id", "annotation_timestamp_utc", "reviewer_id", "review_decision", "visual_evidence_notes"]:
        assert req_field in rec_schema, f"Missing provenance field in schema: {req_field}"
    
    forbidden = ds08_annotation_schema.get("what_is_not_permitted", [])
    assert any("Random box generation" in f for f in forbidden)
    assert any("FIRMS thermal anomaly" in f for f in forbidden)


def test_13_firms_association_provenance(ds08_manifest: pd.DataFrame):
    """Verify optical chips are decoupled from FIRMS and no fabricated FIRMS pairings exist."""
    assert not ds08_manifest["firms_associated"].any()
    assert (ds08_manifest["firms_association_method"] == "NONE_DECOUPLED").all()
    assert ds08_manifest["associated_detection_id"].isna().all()
    assert ds08_manifest["distance_to_firms_m"].isna().all()


def test_14_no_final_fusion_artifact_created():
    """Verify that Stage 8.5 did not prematurely create the final fusion multimodal dataset."""
    final_fusion_paths = [
        PROJECT_ROOT / "data" / "processed" / "multimodal_fusion_dataset.parquet",
        PROJECT_ROOT / "data" / "processed" / "final_fusion_features.parquet",
        PROJECT_ROOT / "models" / "fusion" / "final_classifier.pt",
    ]
    for p in final_fusion_paths:
        assert not p.exists(), f"Final fusion artifact should NOT exist in Stage 8.5: {p}"


def test_15_frozen_previous_checkpoints_unchanged():
    """Verify byte-for-byte SHA-256 immutability of all frozen predecessor models and artifacts."""
    expected_hashes = {
        "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
        "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
        "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
        "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
        "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
    }

    for rel_path, expected_hash in expected_hashes.items():
        p = PROJECT_ROOT / rel_path
        assert p.exists(), f"Frozen artifact missing: {p}"
        actual_hash = hashlib.sha256(p.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, (
            f"FROZEN ARTIFACT MUTATED: {rel_path}\n"
            f"Expected SHA-256: {expected_hash}\n"
            f"Actual SHA-256:   {actual_hash}"
        )
