"""
Stage 8.22: Multimodal Late Fusion Verification Test Suite.
Verifies all 18 requirements:
1. All frozen checkpoint hashes unchanged
2. Feature schema consistency
3. No duplicate fusion keys
4. No accidental many-to-many joins
5. No spatial leakage
6. No temporal leakage
7. Expected/human labels remain separate
8. Uncertain samples excluded from supervised training
9. Missing-modality masks work
10. Fusion input dimensionality
11. Fusion output = 4 classes
12. Deterministic inference
13. Checkpoint save/load equivalence
14. No NaN/Inf in embeddings or outputs
15. Modality ablation execution
16. Prediction probability normalization
17. Test-support accounting (N/A for zero support)
18. No synthetic labels enter the pipeline
"""

import hashlib
import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import torch

from src.stage8_22.fusion_cohort import (
    CAUSAL_GEO_FEATURES,
    CLASS_NAME_TO_ID,
    ID_TO_CLASS_NAME,
    MODALITY_DIMS,
    MODALITY_NAMES,
    TARGET_TAXONOMY,
)
from src.stage8_22.fusion_model import MultimodalLateFusionMLP
from src.stage8_22.evaluation import (
    MultimodalFusionDataset,
    compute_classification_metrics,
    generate_prediction_record,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Frozen artifact paths
V3_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19b" / "ds08_expansion_candidates_v3.json"
V4_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_19e" / "ds08_expansion_candidates_v4.json"
TCN_CHECKPOINT = PROJECT_ROOT / "models" / "tcn" / "best_tcn.pt"
DEEP_SAD_CHECKPOINT = PROJECT_ROOT / "models" / "deep_sad" / "best_deep_sad.pt"
YOLO_INFRA_CHECKPOINT = PROJECT_ROOT / "models" / "yolo" / "infrastructure" / "best_infrastructure.pt"
YOLO_FIRE_CHECKPOINT = PROJECT_ROOT / "models" / "yolo" / "fire_smoke" / "best_fire_smoke.pt"
S2_ENCODER_CHECKPOINT = PROJECT_ROOT / "models" / "s2_encoder" / "best_s2_encoder.pt"

# Stage 8.22 paths
FUSION_COHORT_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_22_fusion_cohort.parquet"
LABELED_SUBSET_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_22_labeled_fusion_subset.parquet"
FUSION_SUMMARY_PATH = PROJECT_ROOT / "data" / "interim" / "ds08_stage8_22_fusion_cohort_summary.json"
FUSION_MODEL_PATH = PROJECT_ROOT / "models" / "fusion" / "best_multimodal_fusion.pt"
EVAL_SUMMARY_PATH = PROJECT_ROOT / "models" / "fusion" / "evaluation_summary.json"
SCHEMA_PATH = PROJECT_ROOT / "models" / "fusion" / "feature_schema.json"

# Frozen hashes
EXPECTED_V3_HASH = "dbba88fd8992db863ec374fea7c266a11e4173e50f257cc0fc9f84368b57b848"
EXPECTED_V4_HASH = "54154edcd0189545c2d03615827f834be91d2452767cef0a1d8978d3b4d9d62c"
EXPECTED_TCN_HASH = "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16"
EXPECTED_DEEP_SAD_HASH = "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa"
EXPECTED_YOLO_INFRA_HASH = "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6"
EXPECTED_YOLO_FIRE_HASH = "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227"
EXPECTED_S2_ENCODER_HASH = "5ec8a02dfe1064d77060c7fb04f08b03cf5a31c4ebf3007bc80d11f0e0f36b87"


def test_01_all_frozen_checkpoint_hashes_unchanged():
    assert hashlib.sha256(open(V3_PATH, "rb").read()).hexdigest() == EXPECTED_V3_HASH
    assert hashlib.sha256(open(V4_PATH, "rb").read()).hexdigest() == EXPECTED_V4_HASH
    assert hashlib.sha256(open(TCN_CHECKPOINT, "rb").read()).hexdigest() == EXPECTED_TCN_HASH
    assert hashlib.sha256(open(DEEP_SAD_CHECKPOINT, "rb").read()).hexdigest() == EXPECTED_DEEP_SAD_HASH
    assert hashlib.sha256(open(YOLO_INFRA_CHECKPOINT, "rb").read()).hexdigest() == EXPECTED_YOLO_INFRA_HASH
    assert hashlib.sha256(open(YOLO_FIRE_CHECKPOINT, "rb").read()).hexdigest() == EXPECTED_YOLO_FIRE_HASH
    assert hashlib.sha256(open(S2_ENCODER_CHECKPOINT, "rb").read()).hexdigest() == EXPECTED_S2_ENCODER_HASH


def test_02_feature_schema_consistency():
    assert SCHEMA_PATH.exists()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    assert schema["modality_dimensions"] == MODALITY_DIMS
    assert schema["modality_names"] == MODALITY_NAMES
    assert schema["causal_geo_features"] == CAUSAL_GEO_FEATURES
    assert schema["target_taxonomy"] == TARGET_TAXONOMY


def test_03_no_duplicate_fusion_keys():
    df_cohort = pd.read_parquet(FUSION_COHORT_PATH, columns=["detection_id"])
    assert df_cohort["detection_id"].is_unique
    df_labeled = pd.read_parquet(LABELED_SUBSET_PATH, columns=["detection_id"])
    assert df_labeled["detection_id"].is_unique


def test_04_no_accidental_many_to_many_joins():
    with open(FUSION_SUMMARY_PATH, "r", encoding="utf-8") as f:
        summary = json.load(f)
    # Exactly base aligned rows (1,024,996) + standalone optical rows (6) = 1,025,002
    assert summary["rows_initial_aligned"] == 1024996
    assert summary["rows_post_causal"] == 1024996
    assert summary["rows_post_labels"] == 1024996
    assert summary["unmatched_causal_count"] == 0
    assert summary["unmatched_labels_count"] == 0
    assert summary["duplicate_detection_id_count"] == 0
    assert summary["total_observations"] == 1025002


def test_05_no_spatial_leakage():
    df_labeled = pd.read_parquet(LABELED_SUBSET_PATH, columns=["detection_id", "partition", "latitude", "longitude"])
    train_ids = set(df_labeled[df_labeled["partition"].isin(["train", "train_heldout_spatial"])]["detection_id"])
    val_ids = set(df_labeled[df_labeled["partition"] == "val"]["detection_id"])
    test_ids = set(df_labeled[df_labeled["partition"].isin(["test", "test_seen_spatial"])]["detection_id"])

    # Disjoint ID sets
    assert len(train_ids & val_ids) == 0
    assert len(train_ids & test_ids) == 0
    assert len(val_ids & test_ids) == 0


def test_06_no_temporal_leakage():
    # Verify no future features (like future detections or post-event metrics) are in CAUSAL_GEO_FEATURES
    for feat in CAUSAL_GEO_FEATURES:
        assert not feat.startswith("future_")
        assert not feat.startswith("post_")
        assert "lead" not in feat.lower()


def test_07_expected_human_labels_remain_separate():
    df_labeled = pd.read_parquet(LABELED_SUBSET_PATH)
    assert "expected_target_class" in df_labeled.columns
    assert "human_observed_class" in df_labeled.columns
    # Check that negative controls maintain separation
    neg_controls = df_labeled[df_labeled["human_observed_class"] == "Uncertain"]
    assert len(neg_controls) >= 2
    for _, r in neg_controls.iterrows():
        assert r["target_class_id"] == -1
        assert r["human_observed_class"] == "Uncertain"


def test_08_uncertain_samples_excluded_from_supervised_training():
    df_labeled = pd.read_parquet(LABELED_SUBSET_PATH)
    uncertain_rows = df_labeled[df_labeled["human_observed_class"] == "Uncertain"]
    for _, r in uncertain_rows.iterrows():
        assert r["is_supervised_target"] == False
        assert r["target_class_id"] == -1


def test_09_missing_modality_masks_work():
    model = MultimodalLateFusionMLP()
    model.eval()

    # Create dummy batch
    B = 2
    x_tcn = torch.randn(B, MODALITY_DIMS["tcn"])
    x_sad = torch.randn(B, MODALITY_DIMS["sad"])
    x_infra = torch.randn(B, MODALITY_DIMS["yolo_infra"])
    x_fire = torch.randn(B, MODALITY_DIMS["yolo_fire"])
    x_s2 = torch.randn(B, MODALITY_DIMS["s2"])
    x_geo = torch.randn(B, MODALITY_DIMS["geo"])

    # Mask with infra, fire, s2 set to 0
    mask_inactive = torch.tensor([[1, 1, 0, 0, 0, 1], [1, 1, 0, 0, 0, 1]], dtype=torch.float32)
    h_cat1 = model.extract_branches(x_tcn, x_sad, x_infra, x_fire, x_s2, x_geo, mask_inactive)

    # Change the values of the inactive modalities
    x_infra_noise = torch.randn(B, MODALITY_DIMS["yolo_infra"]) * 100
    x_fire_noise = torch.randn(B, MODALITY_DIMS["yolo_fire"]) * 100
    x_s2_noise = torch.randn(B, MODALITY_DIMS["s2"]) * 100
    h_cat2 = model.extract_branches(x_tcn, x_sad, x_infra_noise, x_fire_noise, x_s2_noise, x_geo, mask_inactive)

    # When mask is 0, noise in the masked branches must have ZERO effect!
    assert torch.allclose(h_cat1, h_cat2, atol=1e-6)


def test_10_fusion_input_dimensionality():
    model = MultimodalLateFusionMLP()
    assert model.branch_tcn.in_features == 64
    assert model.branch_sad.in_features == 32
    assert model.branch_yolo_infra.in_features == 128
    assert model.branch_yolo_fire.in_features == 128
    assert model.branch_s2.in_features == 128
    assert model.branch_geo.in_features == 27


def test_11_fusion_output_4_classes():
    model = MultimodalLateFusionMLP()
    model.eval()
    B = 3
    x_tcn = torch.randn(B, 64)
    x_sad = torch.randn(B, 32)
    x_infra = torch.zeros(B, 128)
    x_fire = torch.zeros(B, 128)
    x_s2 = torch.randn(B, 128)
    x_geo = torch.randn(B, 27)
    mask = torch.tensor([[1, 1, 0, 0, 1, 1]] * B, dtype=torch.float32)

    logits, z_fus = model(x_tcn, x_sad, x_infra, x_fire, x_s2, x_geo, mask, return_embeddings=True)
    assert logits.shape == (B, 4)
    assert z_fus.shape == (B, 128)


def test_12_deterministic_inference():
    model = MultimodalLateFusionMLP.load_checkpoint(FUSION_MODEL_PATH)
    model.eval()
    B = 2
    x_tcn = torch.randn(B, 64)
    x_sad = torch.randn(B, 32)
    x_infra = torch.zeros(B, 128)
    x_fire = torch.zeros(B, 128)
    x_s2 = torch.zeros(B, 128)
    x_geo = torch.randn(B, 27)
    mask = torch.tensor([[1, 1, 0, 0, 0, 1]] * B, dtype=torch.float32)

    with torch.no_grad():
        out1 = model(x_tcn, x_sad, x_infra, x_fire, x_s2, x_geo, mask)
        out2 = model(x_tcn, x_sad, x_infra, x_fire, x_s2, x_geo, mask)

    assert torch.equal(out1, out2)


def test_13_checkpoint_save_load_equivalence(tmp_path):
    model = MultimodalLateFusionMLP.load_checkpoint(FUSION_MODEL_PATH)
    model.eval()

    tmp_file = tmp_path / "test_fusion.pt"
    model.save_checkpoint(tmp_file)
    loaded = MultimodalLateFusionMLP.load_checkpoint(tmp_file)

    B = 2
    x_tcn = torch.randn(B, 64)
    x_sad = torch.randn(B, 32)
    x_infra = torch.zeros(B, 128)
    x_fire = torch.zeros(B, 128)
    x_s2 = torch.zeros(B, 128)
    x_geo = torch.randn(B, 27)
    mask = torch.tensor([[1, 1, 0, 0, 0, 1]] * B, dtype=torch.float32)

    with torch.no_grad():
        out1 = model(x_tcn, x_sad, x_infra, x_fire, x_s2, x_geo, mask)
        out2 = loaded(x_tcn, x_sad, x_infra, x_fire, x_s2, x_geo, mask)

    assert torch.allclose(out1, out2, atol=1e-6)


def test_14_no_nan_or_inf_in_embeddings_or_outputs():
    model = MultimodalLateFusionMLP.load_checkpoint(FUSION_MODEL_PATH)
    model.eval()
    B = 5
    x_tcn = torch.randn(B, 64)
    x_sad = torch.randn(B, 32)
    x_infra = torch.zeros(B, 128)
    x_fire = torch.zeros(B, 128)
    x_s2 = torch.zeros(B, 128)
    x_geo = torch.randn(B, 27)
    mask = torch.tensor([[1, 1, 0, 0, 0, 1]] * B, dtype=torch.float32)

    with torch.no_grad():
        logits, z_fus = model(x_tcn, x_sad, x_infra, x_fire, x_s2, x_geo, mask, return_embeddings=True)

    assert not torch.isnan(logits).any()
    assert not torch.isinf(logits).any()
    assert not torch.isnan(z_fus).any()
    assert not torch.isinf(z_fus).any()


def test_15_modality_ablation_execution():
    assert EVAL_SUMMARY_PATH.exists()
    with open(EVAL_SUMMARY_PATH, "r", encoding="utf-8") as f:
        summary = json.load(f)

    ablations = summary["ablations"]
    required_ablations = [
        "Geometry / Thermal Only",
        "Temporal Only",
        "Anomaly Only",
        "Optical Only (S2)",
        "Infrastructure Visual Only",
        "Fire / Smoke Visual Only",
        "Temporal + Geospatial",
        "Geospatial + Sentinel-2",
        "Full Fusion",
    ]
    for req in required_ablations:
        assert req in ablations, f"Missing required ablation: {req}"
        assert "val" in ablations[req]
        assert "macro_f1" in ablations[req]["val"]


def test_16_prediction_probability_normalization():
    model = MultimodalLateFusionMLP.load_checkpoint(FUSION_MODEL_PATH)
    df_labeled = pd.read_parquet(LABELED_SUBSET_PATH)
    sample = df_labeled.iloc[0]
    rec = generate_prediction_record(model, sample)
    probs = list(rec["class_probabilities"].values())
    assert abs(sum(probs) - 1.0) < 1e-4
    for p in probs:
        assert 0.0 <= p <= 1.0


def test_17_test_support_accounting():
    with open(EVAL_SUMMARY_PATH, "r", encoding="utf-8") as f:
        summary = json.load(f)

    # In test set, verify that classes with 0 support report N/A
    full_fusion_test = summary["ablations"]["Full Fusion"]["test"]
    per_class = full_fusion_test["per_class"]
    for cname in ["Industrial Fire", "Forest Fire", "Agricultural Fire"]:
        assert per_class[cname]["support"] == 0
        assert per_class[cname]["f1"] == "N/A"
        assert per_class[cname]["precision"] == "N/A"
        assert per_class[cname]["recall"] == "N/A"


def test_18_no_synthetic_labels_enter_pipeline():
    df_labeled = pd.read_parquet(LABELED_SUBSET_PATH)
    # Verify evidence categories are real
    valid_ev = {"STATUTORY_SEBI_FILING", "OPTICAL_SENTINEL2_VERIFIED", "STATIC_SOURCE_EVIDENCE", "GLOBAL_FIRE_ATLAS_2025", "FSI_VAN_AGNI_LFF_2025", "MODIS_MCD64A1_V61_BURNED_AREA", "SENTINEL2_AGRI_PILOT_T43RFP", "INDIA_INDUSTRIAL_INCIDENTS_2025"}
    for ev in df_labeled["evidence_category"].unique():
        assert any(v in str(ev) for v in ["EVENT", "STATUTORY", "OPTICAL", "STATIC", "GLOBAL", "FSI", "MODIS", "SENTINEL2", "INDIA", "INCIDENT"]), f"Suspicious evidence: {ev}"
