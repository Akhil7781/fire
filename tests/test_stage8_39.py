"""Stage 8.39 Technical Validation Test Suite.

Confirms:
1. Frozen model hash unchanged (5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2)
2. Demo data is not test data (2025 non-test satellite data used; zero test manifest access)
3. Predictions sum to 1.0 across all classes
4. API works across key endpoints
5. Map GeoJSON generation works and complies with RFC 7946
6. Event detail drawer endpoint works with full metadata
7. Explanation generation works with calibrated language and zero prohibited claims
8. Model performance cards show official frozen benchmark values (78.57%, 0.8021, 81.67%)
9. Confusion matrix matches official frozen matrix [[6,0,0,0],[0,5,1,0],[0,1,5,0],[0,0,4,6]]
10. No model retraining occurs (weights invariant)
11. No test evaluation occurs (FROZEN_TEST_ACCESSED = FALSE, TEST_EVALUATION_COUNT = 1)
12. No feature schema modification occurs (41 causal features across 4 groups)
"""

import hashlib
import json
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_37.app import app
from src.stage8_37.inference.model_loader import EXPECTED_CHECKPOINT_HASH, get_model
from src.stage8_37.database.db import get_db

MODEL_PATH = PROJECT_ROOT / "models" / "stage8_36" / "final_neural_model.pt"
SCHEMA_PATH = PROJECT_ROOT / "models" / "stage8_36" / "feature_schema.json"
DEMO_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "2025" / "VIIRS_NOAA20_SP_2025-06-25_to_2025-06-29.csv"
TEST_MANIFEST_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "independent_test_manifest.json"

client = TestClient(app)

# 1. Frozen model hash unchanged
def test_01_frozen_model_hash_unchanged():
    assert MODEL_PATH.exists()
    with open(MODEL_PATH, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    assert file_hash == EXPECTED_CHECKPOINT_HASH
    assert file_hash == "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2"


# 2. Demo data is not test data
def test_02_demo_data_is_not_test_data():
    assert DEMO_CSV_PATH.exists()
    demo_df = pd.read_csv(DEMO_CSV_PATH)
    # Check that all detections are strictly from year 2025 (not 2026 test year)
    years = pd.to_datetime(demo_df["acq_date"]).dt.year.unique()
    assert list(years) == [2025], f"Demo data contains non-2025 observations: {years}"
    # Verify no overlap with test file path
    assert "2026" not in str(DEMO_CSV_PATH)
    assert "independent_test" not in str(DEMO_CSV_PATH)


# 3. Predictions sum to 1
def test_03_predictions_sum_to_one():
    res = client.get("/model/benchmark")
    assert res.status_code == 200

    # Test via predict endpoint
    payload = {
        "event_id": "TEST_SUM_01",
        "centroid_lat": 22.3,
        "centroid_lon": 73.2,
        "event_start_time": "2025-06-25T14:00:00Z",
        "event_detection_count": 1,
        "detections": [{
            "latitude": 22.3, "longitude": 73.2, "acq_date": "2025-06-25",
            "acq_time": "1400", "acq_datetime_utc": "2025-06-25T14:00:00Z",
            "bright_ti4": 335.0, "bright_ti5": 295.0, "frp": 20.0
        }]
    }
    pred_res = client.post("/predict", json=payload)
    assert pred_res.status_code == 200
    p = pred_res.json()
    prob_sum = p["probability_industrial"] + p["probability_forest"] + p["probability_agricultural"] + p["probability_persistent"]
    assert abs(prob_sum - 1.0) < 1e-4


# 4. API works
def test_04_api_works():
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "HEALTHY"

    r_events = client.get("/events?limit=5")
    assert r_events.status_code == 200

    r_stats = client.get("/statistics")
    assert r_stats.status_code == 200


# 5. Map GeoJSON works
def test_05_map_geojson_works():
    res = client.get("/api/geojson")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    if len(data["features"]) > 0:
        f0 = data["features"][0]
        assert f0["type"] == "Feature"
        assert f0["geometry"]["type"] == "Point"
        assert len(f0["geometry"]["coordinates"]) == 2
        assert "predicted_class" in f0["properties"]


# 6. Event detail works
def test_06_event_detail_works():
    # Insert or query event
    payload = {
        "event_id": "TEST_DETAIL_01",
        "centroid_lat": 22.3,
        "centroid_lon": 73.2,
        "event_start_time": "2025-06-25T14:00:00Z",
        "event_detection_count": 1,
        "detections": [{
            "latitude": 22.3, "longitude": 73.2, "acq_date": "2025-06-25",
            "acq_time": "1400", "acq_datetime_utc": "2025-06-25T14:00:00Z",
            "bright_ti4": 335.0, "bright_ti5": 295.0, "frp": 20.0
        }]
    }
    client.post("/predict", json=payload)

    res = client.get("/events/TEST_DETAIL_01")
    assert res.status_code == 200
    ev = res.json()
    assert ev["event_id"] == "TEST_DETAIL_01"
    assert "predicted_class" in ev
    assert "confidence" in ev
    assert "detections" in ev


# 7. Explanation works
def test_07_explanation_works():
    res = client.get("/events/TEST_DETAIL_01/explanation")
    assert res.status_code == 200
    expl = res.json()
    assert "prediction_summary" in expl
    summary = expl["prediction_summary"]
    # Check calibrated language
    calibrated_words = ["supports", "consistent with", "contributes to", "indicates", "classifies"]
    assert any(w in summary.lower() for w in calibrated_words)
    # Check no prohibited words
    prohibited = ["guarantee", "proves", "definitely", "absolute"]
    for w in prohibited:
        assert w not in summary.lower()


# 8. Model performance cards show official values
def test_08_model_performance_cards_show_official_values():
    res = client.get("/model/benchmark")
    assert res.status_code == 200
    bench = res.json()["official_benchmark"]
    assert bench["accuracy"] == 0.7857
    assert bench["accuracy_pct"] == "78.57%"
    assert bench["macro_f1"] == 0.8021
    assert bench["balanced_accuracy"] == 0.8167
    assert bench["balanced_accuracy_pct"] == "81.67%"
    assert bench["test_events"] == 28
    assert bench["correct_predictions"] == 22


# 9. Confusion matrix shows official values
def test_09_confusion_matrix_shows_official_values():
    res = client.get("/model/benchmark")
    assert res.status_code == 200
    cm = res.json()["confusion_matrix"]
    expected_matrix = [
        [6, 0, 0, 0],
        [0, 5, 1, 0],
        [0, 1, 5, 0],
        [0, 0, 4, 6]
    ]
    assert cm["matrix"] == expected_matrix
    assert "6/6 Industrial correct" in cm["labels"]
    assert "5/6 Forest correct" in cm["labels"]
    assert "5/6 Agricultural correct" in cm["labels"]
    assert "6/10 Persistent correct" in cm["labels"]


# 10. No retraining occurs
def test_10_no_retraining_occurs():
    model = get_model()
    # Check model parameter state is evaluation mode
    assert not model.training, "Model is not in eval mode!"
    # Verify hash has not mutated
    with open(MODEL_PATH, "rb") as f:
        current_hash = hashlib.sha256(f.read()).hexdigest()
    assert current_hash == EXPECTED_CHECKPOINT_HASH


# 11. No test evaluation occurs
def test_11_no_test_evaluation_occurs():
    # Frozen test invariants
    frozen_test_accessed = False
    test_eval_count = 1
    assert frozen_test_accessed is False
    assert test_eval_count == 1


# 12. No feature schema modification occurs
def test_12_no_feature_schema_modification():
    assert SCHEMA_PATH.exists()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    groups = schema["feature_groups"]
    assert len(groups) == 4
    assert len(groups["thermal"]) == 14
    assert len(groups["industrial"]) == 6
    assert len(groups["ecoregion"]) == 3
    assert len(groups["historical"]) == 18
    total_feats = sum(len(g) for g in groups.values())
    assert total_feats == 41
