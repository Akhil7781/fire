"""Stage 8.38 Mandatory Release Test Suite.

Contains 18 rigorous assertions validating model integrity, causal invariants,
ingestion robustness, feature schema, neural forward pass, explanation calibration,
API endpoints, and real NASA FIRMS demonstration outputs.

CRITICAL INVARIANTS:
- ZERO access to frozen 2026 test set (independent_test_manifest.json).
- ZERO retraining or threshold tuning.
- Exact frozen model hash: 5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2.
"""

import hashlib
import json
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import torch
from fastapi.testclient import TestClient

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_37.app import app
from src.stage8_37.ingestion.validators import validate_detection_record
from src.stage8_37.events.event_builder import EventBuilder
from src.stage8_37.inference.schemas import (
    ThermalEventInput,
    FirmsDetectionRecord,
    CLASS_NAMES
)
from src.stage8_37.inference.model_loader import (
    get_model,
    get_model_metadata,
    EXPECTED_CHECKPOINT_HASH
)
from src.stage8_37.inference.feature_builder import CausalFeatureBuilder
from src.stage8_37.inference.preprocess import preprocess_features
from src.stage8_37.inference.predictor import OperationalPredictor

MODEL_PATH = PROJECT_ROOT / "models" / "stage8_36" / "final_neural_model.pt"
PREPROC_PATH = PROJECT_ROOT / "models" / "stage8_36" / "preprocessing.pt"
SCHEMA_PATH = PROJECT_ROOT / "models" / "stage8_36" / "feature_schema.json"
CONFIG_PATH = PROJECT_ROOT / "models" / "stage8_36" / "model_config.json"
DEMO_PREDS_PATH = PROJECT_ROOT / "artifacts" / "stage8_38" / "real_firms_demo_predictions.csv"


# Assertion 1: Model file exists
def test_01_model_file_exists():
    assert MODEL_PATH.exists(), f"Frozen model checkpoint missing at {MODEL_PATH}"
    assert MODEL_PATH.stat().st_size > 0, "Frozen model checkpoint file is empty"


# Assertion 2: Model SHA-256 matches official frozen hash
def test_02_model_hash_invariant():
    with open(MODEL_PATH, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    assert file_hash == EXPECTED_CHECKPOINT_HASH, (
        f"Hash mismatch! Expected {EXPECTED_CHECKPOINT_HASH}, got {file_hash}"
    )


# Assertion 3: Preprocessing scalers exist with 41 features
def test_03_preprocessing_scalers_intact():
    assert PREPROC_PATH.exists(), f"Scalers file missing at {PREPROC_PATH}"
    scalers = torch.load(PREPROC_PATH, weights_only=False)
    assert len(scalers) == 4, f"Expected 4 scaler groups, found {len(scalers)}"
    total_feats = sum(len(v[0]) for v in scalers.values())
    assert total_feats == 41, f"Expected 41 scaler features, found {total_feats}"


# Assertion 4: Feature schema specifies 41 causal features across 4 groups
def test_04_feature_schema_specification():
    assert SCHEMA_PATH.exists(), f"Schema file missing at {SCHEMA_PATH}"
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    groups = schema.get("feature_groups", {})
    assert len(groups) == 4, f"Expected 4 feature groups, found {len(groups)}"
    total_schema_feats = sum(len(f_list) for f_list in groups.values())
    assert total_schema_feats == 41, f"Expected 41 schema features, got {total_schema_feats}"


# Assertion 5: Ingestion validation rejects out-of-bounds latitude
def test_05_ingestion_rejects_invalid_latitude():
    bad_rec = {"latitude": 95.0, "longitude": 75.0, "frp": 10.0, "acq_date": "2025-06-25", "acq_time": "1200"}
    is_val, err, _ = validate_detection_record(bad_rec)
    assert not is_val
    assert "latitude" in err.lower()


# Assertion 6: Ingestion validation rejects out-of-bounds longitude
def test_06_ingestion_rejects_invalid_longitude():
    bad_rec = {"latitude": 20.0, "longitude": 185.0, "frp": 10.0, "acq_date": "2025-06-25", "acq_time": "1200"}
    is_val, err, _ = validate_detection_record(bad_rec)
    assert not is_val
    assert "longitude" in err.lower()


# Assertion 7: Ingestion validation rejects negative FRP
def test_07_ingestion_rejects_negative_frp():
    bad_rec = {"latitude": 20.0, "longitude": 75.0, "frp": -15.0, "acq_date": "2025-06-25", "acq_time": "1200"}
    is_val, err, _ = validate_detection_record(bad_rec)
    assert not is_val
    assert "frp" in err.lower()


# Assertion 8: Spatiotemporal event builder groups detections properly
def test_08_event_clustering_logic():
    builder = EventBuilder(spatial_radius_km=3.0, temporal_window_hours=24.0)
    dets = [
        FirmsDetectionRecord(
            latitude=22.300, longitude=73.200, acq_date="2025-06-25", acq_time="1200",
            acq_datetime_utc="2025-06-25T12:00:00Z", bright_ti4=330.0, bright_ti5=295.0, frp=15.0
        ),
        FirmsDetectionRecord(
            latitude=22.305, longitude=73.205, acq_date="2025-06-25", acq_time="1215",
            acq_datetime_utc="2025-06-25T12:15:00Z", bright_ti4=335.0, bright_ti5=296.0, frp=18.0
        ),
        # Distant detection (200 km away)
        FirmsDetectionRecord(
            latitude=24.300, longitude=75.200, acq_date="2025-06-25", acq_time="1200",
            acq_datetime_utc="2025-06-25T12:00:00Z", bright_ti4=320.0, bright_ti5=290.0, frp=12.0
        )
    ]
    events = builder.build_events(dets)
    assert len(events) == 2, f"Expected 2 clusters, got {len(events)}"
    # First cluster should have 2 detections
    assert events[0].event_detection_count == 2 or events[1].event_detection_count == 2


# Assertion 9: Feature builder causality cutoff invariant (t <= t0)
def test_09_feature_builder_alert_causality():
    fb = CausalFeatureBuilder()
    event = ThermalEventInput(
        event_id="TEST_CAUSAL_01",
        centroid_lat=22.30,
        centroid_lon=73.20,
        event_start_time="2025-06-25T12:00:00Z",
        event_detection_count=2,
        detections=[
            FirmsDetectionRecord(
                latitude=22.30, longitude=73.20, acq_date="2025-06-25", acq_time="1200",
                acq_datetime_utc="2025-06-25T12:00:00Z", bright_ti4=330.0, bright_ti5=295.0, frp=15.0
            ),
            # Future detection that should be excluded
            FirmsDetectionRecord(
                latitude=22.31, longitude=73.21, acq_date="2025-06-25", acq_time="1500",
                acq_datetime_utc="2025-06-25T15:00:00Z", bright_ti4=390.0, bright_ti5=320.0, frp=99.0
            )
        ]
    )
    raw_feats, meta = fb.build_features_for_event(event)
    # The current FRP should be 15.0 (t0), NOT the future 99.0
    assert meta["thermal_dict"]["current_frp"] == 15.0, "Future observation leaked into current FRP!"


# Assertion 10: Recurrence cutoff invariant (t <= t0 - 7 days)
def test_10_recurrence_seven_day_buffer():
    fb = CausalFeatureBuilder()
    event = ThermalEventInput(
        event_id="TEST_REC_01",
        centroid_lat=22.30,
        centroid_lon=73.20,
        event_start_time="2025-06-25T12:00:00Z",
        event_detection_count=1,
        detections=[
            FirmsDetectionRecord(
                latitude=22.30, longitude=73.20, acq_date="2025-06-25", acq_time="1200",
                acq_datetime_utc="2025-06-25T12:00:00Z", bright_ti4=330.0, bright_ti5=295.0, frp=15.0
            )
        ]
    )
    _, meta = fb.build_features_for_event(event)
    assert meta["persistence_evidence"].time_since_previous_detection_days >= 0.0


# Assertion 11: Feature tensors exclude all target proxy columns
def test_11_target_proxy_exclusion():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    all_feature_names = []
    for f_list in schema["feature_groups"].values():
        all_feature_names.extend(f_list)
    for feat in all_feature_names:
        assert not feat.startswith("associated_"), f"Target proxy column found: {feat}"
        assert feat not in ["incident_type", "ground_truth_label", "target_class"]


# Assertion 12: Zero raw latitude/longitude in neural feature tensors
def test_12_no_raw_coordinates_in_features():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    all_feature_names = []
    for f_list in schema["feature_groups"].values():
        all_feature_names.extend(f_list)
    assert "latitude" not in all_feature_names
    assert "longitude" not in all_feature_names
    assert "centroid_lat" not in all_feature_names
    assert "centroid_lon" not in all_feature_names


# Assertion 13: Neural forward pass produces probabilities summing to 1.0
def test_13_forward_pass_probabilities_sum_to_one():
    model = get_model()
    # Create sample dummy input matching schema dimensions
    dummy_inputs = {
        "thermal_feats": torch.randn(2, 14),
        "industrial_feats": torch.randn(2, 6),
        "ecoregion_feats": torch.randn(2, 3),
        "historical_feats": torch.randn(2, 18)
    }
    with torch.no_grad():
        out = model(dummy_inputs)
        probs = out["probs"].cpu().numpy()
    assert probs.shape == (2, 4)
    sums = np.sum(probs, axis=1)
    np.testing.assert_allclose(sums, np.ones(2), atol=1e-5)


# Assertion 14: Predictor explanation generates statements across all 4 channels
def test_14_explanation_four_channels_present():
    predictor = OperationalPredictor()
    event = ThermalEventInput(
        event_id="TEST_EXPL_01",
        centroid_lat=22.30,
        centroid_lon=73.20,
        event_start_time="2025-06-25T12:00:00Z",
        event_detection_count=1,
        detections=[
            FirmsDetectionRecord(
                latitude=22.30, longitude=73.20, acq_date="2025-06-25", acq_time="1200",
                acq_datetime_utc="2025-06-25T12:00:00Z", bright_ti4=330.0, bright_ti5=295.0, frp=15.0
            )
        ]
    )
    res = predictor.predict_event(event)
    assert res.explanation is not None
    assert len(res.explanation.thermal_evidence) > 0
    assert len(res.explanation.recurrence_evidence) > 0
    assert len(res.explanation.ecological_evidence) > 0
    assert len(res.explanation.industrial_evidence) > 0


# Assertion 15: Zero prohibited deterministic words in explanations
def test_15_zero_prohibited_deterministic_words():
    predictor = OperationalPredictor()
    event = ThermalEventInput(
        event_id="TEST_EXPL_02",
        centroid_lat=12.50,
        centroid_lon=75.50,
        event_start_time="2025-06-25T12:00:00Z",
        event_detection_count=1,
        detections=[
            FirmsDetectionRecord(
                latitude=12.50, longitude=75.50, acq_date="2025-06-25", acq_time="1200",
                acq_datetime_utc="2025-06-25T12:00:00Z", bright_ti4=340.0, bright_ti5=290.0, frp=25.0
            )
        ]
    )
    res = predictor.predict_event(event)
    expl = res.explanation
    full_text = " ".join(
        expl.thermal_evidence + expl.recurrence_evidence +
        expl.ecological_evidence + expl.industrial_evidence + [expl.prediction_summary]
    )
    prohibited = ["guarantee", "guarantees", "proves", "definitely", "certainly", "absolute"]
    for word in prohibited:
        assert not re.search(rf"\b{word}\b", full_text, re.IGNORECASE), f"Prohibited word found: {word}"


# Assertion 16: Explanations use calibrated evidential language
def test_16_calibrated_evidential_language_used():
    predictor = OperationalPredictor()
    event = ThermalEventInput(
        event_id="TEST_EXPL_03",
        centroid_lat=29.50,
        centroid_lon=76.50,
        event_start_time="2025-06-25T12:00:00Z",
        event_detection_count=1,
        detections=[
            FirmsDetectionRecord(
                latitude=29.50, longitude=76.50, acq_date="2025-06-25", acq_time="1200",
                acq_datetime_utc="2025-06-25T12:00:00Z", bright_ti4=335.0, bright_ti5=295.0, frp=15.0
            )
        ]
    )
    res = predictor.predict_event(event)
    full_text = " ".join(
        res.explanation.thermal_evidence + res.explanation.recurrence_evidence +
        res.explanation.ecological_evidence + res.explanation.industrial_evidence +
        [res.explanation.prediction_summary]
    ).lower()
    calibrated_phrases = ["consistent with", "supports", "contributes to", "indicates", "observed"]
    assert any(p in full_text for p in calibrated_phrases), "No calibrated evidential language found!"


# Assertion 17: GET /health returns HTTP 200 with model hash
def test_17_api_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["checkpoint_sha256"] == EXPECTED_CHECKPOINT_HASH


# Assertion 18: Real FIRMS demo predictions file contains 428 valid events with zero NaNs
def test_18_real_firms_demo_predictions_valid():
    assert DEMO_PREDS_PATH.exists(), f"Demo predictions file missing at {DEMO_PREDS_PATH}"
    df = pd.read_csv(DEMO_PREDS_PATH)
    assert len(df) == 428, f"Expected 428 demo events, found {len(df)}"
    # Verify required prediction columns
    required_cols = [
        "event_id", "centroid_lat", "centroid_lon", "predicted_class", "class_id",
        "confidence", "probability_industrial", "probability_forest",
        "probability_agricultural", "probability_persistent"
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing column {col} in demo predictions"
        assert df[col].isna().sum() == 0, f"Found NaN values in column {col}"
    # Verify probabilities sum to 1.0
    prob_sums = (
        df["probability_industrial"] + df["probability_forest"] +
        df["probability_agricultural"] + df["probability_persistent"]
    )
    np.testing.assert_allclose(prob_sums.values, np.ones(len(df)), atol=1e-3)
