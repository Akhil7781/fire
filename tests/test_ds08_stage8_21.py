"""
Stage 8.21 Test Suite
Validates all 18 requirements from Phase I:
1. SCL policy resolution
2. Chip dimensions
3. Five-channel ordering
4. Dtype/range
5. Candidate-point centering
6. Replacement-manifest separation from frozen manifest
7. No synthetic labels entering training
8. Annotation schema validity
9. Class-label validity
10. Spatial split integrity
11. Encoder input shape
12. Encoder output shape = 128
13. Checkpoint save/load equivalence
14. Deterministic embedding extraction
15. No NaN/Inf
16. Sample_id uniqueness
17. Embedding row-count consistency
18. No accidental modification of frozen Stage 7/8 artifacts
"""

import hashlib
import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import torch

from src.stage8_21.quality_policy import (
    AOI_CONTAMINATION_THRESHOLD_PCT,
    CENTRAL_1KM_CONTAMINATION_PASS_PCT,
    CENTRAL_1KM_CONTAMINATION_CONDITIONAL_PCT,
    SCL_CLASSES,
    SCL_VALID_CLASSES,
    SCL_INVALID_CLASSES,
    SCL_CONTAMINATED_CLASSES,
    BAND_ORDER_ML,
    CHIP_SIZE_PIXELS,
    PIXEL_RESOLUTION_M,
    evaluate_scl_quality,
)
from src.stage8_21.human_review import (
    VALID_PRIMARY_CLASSES,
    VALID_CONFIDENCES,
    VALID_DECISIONS,
    VALID_EVIDENCE_TYPES,
    validate_annotation_record,
)
from src.stage8_21.s2_encoder import Sentinel2Encoder

PROJECT_ROOT = Path(__file__).resolve().parent.parent

V3_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b" / "ds08_expansion_candidates_v3.json"
V4_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19e" / "ds08_expansion_candidates_v4.json"
TCN_CHECKPOINT = PROJECT_ROOT / "models" / "tcn" / "best_tcn.pt"
CAUSAL_FEATURES = PROJECT_ROOT / "data" / "interim" / "causal_features_2025.parquet"

INVENTORY_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_chip_inventory.parquet"
REPLACEMENT_MANIFEST_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_21" / "ds08_stage8_21_replacement_manifest.json"
REPLACEMENTS_PROCESSED_MANIFEST = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_21" / "ds08_stage8_21_replacements_processed.json"
ANNOTATIONS_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_review_annotations.parquet"
EMBEDDINGS_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_21_s2_embeddings.parquet"
ENCODER_CHECKPOINT = PROJECT_ROOT / "models" / "s2_encoder" / "best_s2_encoder.pt"

EXPECTED_V3_HASH = "dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848"
EXPECTED_V4_HASH = "54154edcd0189545c2d03615827f834be91d2452767cef0a1d8978d3b4d9d62c"


def test_01_scl_policy_resolution():
    assert AOI_CONTAMINATION_THRESHOLD_PCT == 5.0
    assert CENTRAL_1KM_CONTAMINATION_PASS_PCT == 5.0
    assert CENTRAL_1KM_CONTAMINATION_CONDITIONAL_PCT == 10.0
    assert len(SCL_VALID_CLASSES) == 12
    assert SCL_INVALID_CLASSES == {0, 1}
    assert SCL_CONTAMINATED_CLASSES == {3, 8, 9, 10}
    assert evaluate_scl_quality(0.0, 0.0) == "PASS"
    assert evaluate_scl_quality(53.3, 100.0, cloud_exception_applied=True) == "REJECT"
    assert evaluate_scl_quality(40.9, 29.7, cloud_exception_applied=True) == "REJECT"


def test_02_chip_dimensions():
    df_ann = pd.read_parquet(ANNOTATIONS_PATH)
    for _, row in df_ann.iterrows():
        arr = np.load(PROJECT_ROOT / row["raw_path"])
        assert arr.shape == (5, 512, 512)
        assert CHIP_SIZE_PIXELS == 512
        assert PIXEL_RESOLUTION_M == 10.0


def test_03_five_channel_ordering():
    assert BAND_ORDER_ML == ["B02", "B03", "B04", "B11", "B12"]
    with open(REPLACEMENTS_PROCESSED_MANIFEST, "r", encoding="utf-8") as f:
        rep_manifest = json.load(f)
    for rec in rep_manifest["records"]:
        assert rec["band_order_ml"] == ["B02", "B03", "B04", "B11", "B12"]


def test_04_dtype_and_range():
    df_ann = pd.read_parquet(ANNOTATIONS_PATH)
    for _, row in df_ann.iterrows():
        raw = np.load(PROJECT_ROOT / row["raw_path"])
        norm = np.load(PROJECT_ROOT / row["normalized_path"])
        scl = np.load(PROJECT_ROOT / row["scl_path"])
        assert raw.dtype == np.uint16
        assert norm.dtype == np.float32
        assert scl.dtype == np.uint8
        assert norm.min() >= 0.0
        assert norm.max() <= 1.0


def test_05_candidate_point_centering():
    with open(REPLACEMENTS_PROCESSED_MANIFEST, "r", encoding="utf-8") as f:
        rep_manifest = json.load(f)
    for rec in rep_manifest["records"]:
        col = rec["chip_pixel_col"]
        row = rec["chip_pixel_row"]
        assert 255.0 <= col <= 257.0, f"Pixel col {col} out of center range"
        assert 255.0 <= row <= 257.0, f"Pixel row {row} out of center range"
        b = rec["chip_bounds_utm"]
        assert b["x_min"] <= rec["projected_x"] <= b["x_max"]
        assert b["y_min"] <= rec["projected_y"] <= b["y_max"]


def test_06_replacement_manifest_separation():
    assert REPLACEMENT_MANIFEST_PATH.exists()
    assert REPLACEMENT_MANIFEST_PATH != V3_PATH
    assert REPLACEMENT_MANIFEST_PATH != V4_PATH
    with open(REPLACEMENT_MANIFEST_PATH, "r", encoding="utf-8") as f:
        rep_data = json.load(f)
    assert len(rep_data["rejected_samples"]) == 2
    assert len(rep_data["replacement_records"]) == 2
    assert rep_data["replacement_records"][0]["replacement_sample_id"] == "S8_001"
    assert rep_data["replacement_records"][1]["replacement_sample_id"] == "S8_002"


def test_07_no_synthetic_labels():
    with open(REPLACEMENT_MANIFEST_PATH, "r", encoding="utf-8") as f:
        rep_data = json.load(f)
    for rec in rep_data["replacement_records"]:
        assert rec["human_confirmed_label"] is None


def test_08_annotation_schema_validity():
    df_ann = pd.read_parquet(ANNOTATIONS_PATH)
    assert len(df_ann) == 8
    for _, row in df_ann.iterrows():
        rec = row.to_dict()
        rec["evidence_notes"] = [x.strip() for x in rec["evidence_notes"].split(";")]
        assert validate_annotation_record(rec)


def test_09_class_label_validity():
    df_ann = pd.read_parquet(ANNOTATIONS_PATH)
    for _, row in df_ann.iterrows():
        assert row["human_observed_class"] in VALID_PRIMARY_CLASSES
        assert row["expected_target_class"] is not None
        assert row["reviewer_decision"] in VALID_DECISIONS


def test_10_spatial_split_integrity():
    from scripts.train_ds08_stage8_21_encoder import train_representation_encoder
    metrics_path = PROJECT_ROOT / "models" / "s2_encoder" / "training_metrics.json"
    assert metrics_path.exists()
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    train_chips = set(metrics["train_chips"])
    val_chips = set(metrics["val_chips"])
    assert len(train_chips.intersection(val_chips)) == 0
    assert len(train_chips) + len(val_chips) == 8


def test_11_encoder_input_shape():
    model = Sentinel2Encoder(embedding_dim=128, backbone_name="efficientnet_b0", pretrained=False)
    x_valid = torch.randn(2, 5, 512, 512)
    out = model(x_valid)
    assert out.shape == (2, 128)
    with pytest.raises(ValueError):
        x_invalid = torch.randn(2, 3, 512, 512)
        model(x_invalid)


def test_12_encoder_output_shape_128():
    model = Sentinel2Encoder(embedding_dim=128, backbone_name="efficientnet_b0", pretrained=False)
    model.eval()
    x = torch.randn(1, 5, 512, 512)
    out = model(x, normalize=True)
    assert out.shape == (1, 128)
    assert torch.allclose(torch.norm(out, dim=1), torch.tensor([1.0]), atol=1e-5)


def test_13_checkpoint_save_and_load_equivalence(tmp_path):
    model = Sentinel2Encoder(embedding_dim=128, backbone_name="efficientnet_b0", pretrained=False)
    model.eval()
    x = torch.randn(2, 5, 512, 512)
    out1 = model(x)
    save_file = tmp_path / "test_enc.pt"
    model.save_checkpoint(save_file)
    loaded_model = Sentinel2Encoder.load_checkpoint(save_file)
    loaded_model.eval()
    out2 = loaded_model(x)
    assert torch.allclose(out1, out2, atol=1e-6)


def test_14_deterministic_embedding_extraction():
    model = Sentinel2Encoder.load_checkpoint(ENCODER_CHECKPOINT)
    model.eval()
    df_ann = pd.read_parquet(ANNOTATIONS_PATH)
    first_row = df_ann.iloc[0]
    arr = np.load(PROJECT_ROOT / first_row["normalized_path"]).astype(np.float32)
    t = torch.from_numpy(arr).unsqueeze(0)
    with torch.no_grad():
        out1 = model(t, normalize=True).squeeze(0).numpy()
        out2 = model(t, normalize=True).squeeze(0).numpy()
    assert np.allclose(out1, out2)


def test_15_no_nan_or_inf_in_embeddings():
    df_emb = pd.read_parquet(EMBEDDINGS_PATH)
    dim_cols = [f"dim_{i:03d}" for i in range(128)]
    for col in dim_cols:
        assert not df_emb[col].isna().any(), f"NaN found in {col}"
        assert not np.isinf(df_emb[col].values).any(), f"Inf found in {col}"


def test_16_sample_id_uniqueness():
    df_inv = pd.read_parquet(INVENTORY_PATH)
    df_ann = pd.read_parquet(ANNOTATIONS_PATH)
    df_emb = pd.read_parquet(EMBEDDINGS_PATH)
    assert len(df_inv["sample_id"].unique()) == len(df_inv)
    assert len(df_ann["sample_id"].unique()) == len(df_ann)
    assert len(df_emb["sample_id"].unique()) == len(df_emb)


def test_17_embedding_row_count_consistency():
    df_ann = pd.read_parquet(ANNOTATIONS_PATH)
    df_emb = pd.read_parquet(EMBEDDINGS_PATH)
    assert len(df_emb) == len(df_ann) == 8


def test_18_no_accidental_modification_of_frozen_artifacts():
    # V3 manifest
    h_v3 = hashlib.sha256(open(V3_PATH, "rb").read()).hexdigest()
    assert h_v3 == EXPECTED_V3_HASH, f"V3 manifest altered: got {h_v3}"

    # V4 manifest
    h_v4 = hashlib.sha256(open(V4_PATH, "rb").read()).hexdigest()
    assert h_v4 == EXPECTED_V4_HASH, f"V4 manifest altered: got {h_v4}"

    # Check existence of frozen TCN and Causal Features
    assert TCN_CHECKPOINT.exists()
    assert CAUSAL_FEATURES.exists()
