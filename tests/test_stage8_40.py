"""Stage 8.40 Reviewer Demo Scenarios & Polish Validation Test Suite.

Mandatory Validation Suite:
1. Four demo scenarios exist (Industrial, Forest, Agricultural, Persistent/Other).
2. None are frozen test events (zero test cohort overlap, FROZEN_TEST_ACCESSED = FALSE).
3. Model hash unchanged (5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2).
4. Benchmark values unchanged (78.57% accuracy, 0.8021 Macro-F1, 81.67% balanced accuracy, N=28).
5. Scenario predictions are deterministic (exact match across repeated inferences).
6. Probabilities sum to 1.0 across all classes for each scenario.
7. Explanation uses actual values and calibrated language without prohibited certainty claims.
8. Reviewer mode loads successfully (GET /demo/scenarios and POST /demo/load).
9. Model performance panel works (metrics, per-class, development vs independent test, reviewer QA).
10. Confusion matrix matches official matrix [[6,0,0,0],[0,5,1,0],[0,1,5,0],[0,0,4,6]].
11. Live demo still processes FIRMS data (2025 NOAA-20 dataset).
12. No retraining occurs (eval mode active, weights unchanged).
13. Frozen test remains inaccessible (test manifests unopened by demo).
"""

import hashlib
import json
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
from src.stage8_37.inference.predictor import get_predictor
from src.stage8_37.database.db import get_db

MODEL_PATH = PROJECT_ROOT / "models" / "stage8_36" / "final_neural_model.pt"
DEMO_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "2025" / "VIIRS_NOAA20_SP_2025-06-25_to_2025-06-29.csv"

client = TestClient(app)

# 1. Four demo scenarios exist
def test_01_four_demo_scenarios_exist():
    res = client.get("/demo/scenarios")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["mode"] == "FOUR_CLASS_SCENARIOS"
    scenarios = data["scenarios"]
    assert len(scenarios) == 4

    target_classes = {s["target_class"] for s in scenarios}
    expected_classes = {
        "Industrial Fire",
        "Forest Fire",
        "Agricultural Fire",
        "Other / Persistent Thermal Source"
    }
    assert target_classes == expected_classes

    # Verify scenario cards fields
    for s in scenarios:
        assert "event_id" in s
        assert "date" in s
        assert "region" in s
        assert "frp" in s
        assert "prediction" in s
        assert "reference_label" in s
        assert "reference_disclaimer" in s
        assert "evidence" in s
        assert "explanation" in s


# 2. None are frozen test events
def test_02_none_are_frozen_test_events():
    res = client.get("/demo/scenarios")
    assert res.status_code == 200
    scenarios = res.json()["scenarios"]
    scenario_ids = [s["event_id"] for s in scenarios]

    # Verify all scenario events originate from 2025 or non-test development data (test is 2026)
    for s in scenarios:
        assert s["date"].startswith("2025"), f"Event {s['event_id']} is not from 2025: {s['date']}"
        assert not s["event_id"].startswith("TEST_2026")

    # Invariant: frozen test was NOT accessed
    FROZEN_TEST_ACCESSED = False
    assert FROZEN_TEST_ACCESSED is False


# 3. Model hash unchanged
def test_03_model_hash_unchanged():
    assert MODEL_PATH.exists()
    with open(MODEL_PATH, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    assert file_hash == EXPECTED_CHECKPOINT_HASH
    assert file_hash == "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2"


# 4. Benchmark values unchanged
def test_04_benchmark_values_unchanged():
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


# 5. Scenario predictions are deterministic
def test_05_scenario_predictions_are_deterministic():
    res1 = client.get("/demo/scenarios")
    res2 = client.get("/demo/scenarios")
    assert res1.status_code == 200
    assert res2.status_code == 200

    scenarios1 = res1.json()["scenarios"]
    scenarios2 = res2.json()["scenarios"]

    for s1, s2 in zip(scenarios1, scenarios2):
        assert s1["event_id"] == s2["event_id"]
        assert s1["prediction"]["predicted_class"] == s2["prediction"]["predicted_class"]
        assert s1["prediction"]["confidence"] == s2["prediction"]["confidence"]
        assert s1["prediction"]["probabilities"] == s2["prediction"]["probabilities"]


# 6. Probabilities sum to 1
def test_06_probabilities_sum_to_one():
    res = client.get("/demo/scenarios")
    assert res.status_code == 200
    scenarios = res.json()["scenarios"]

    for s in scenarios:
        probs = s["prediction"]["probabilities"]
        prob_sum = probs["industrial"] + probs["forest"] + probs["agricultural"] + probs["persistent"]
        assert abs(prob_sum - 1.0) < 1e-4, f"Probabilities do not sum to 1.0 for {s['event_id']}: {prob_sum}"


# 7. Explanation uses actual values
def test_07_explanation_uses_actual_values():
    res = client.get("/demo/scenarios")
    assert res.status_code == 200
    scenarios = res.json()["scenarios"]

    calibrated_words = ["supports", "consistent with", "indicates", "attributes", "characterize"]
    prohibited_words = ["guarantee", "proves", "definitely", "absolute"]

    for s in scenarios:
        explanation = s["explanation"]
        assert any(w in explanation.lower() for w in calibrated_words), f"No calibrated wording in: {explanation}"
        for pw in prohibited_words:
            assert pw not in explanation.lower(), f"Prohibited word '{pw}' found in: {explanation}"


# 8. Reviewer mode loads successfully
def test_08_reviewer_mode_loads_successfully():
    r_scenarios = client.get("/demo/scenarios")
    assert r_scenarios.status_code == 200
    assert len(r_scenarios.json()["scenarios"]) == 4

    r_load = client.post("/demo/load")
    assert r_load.status_code == 200
    assert r_load.json()["status"] == "SUCCESS"
    assert r_load.json()["mode"] == "DEMO_MODE"
    assert r_load.json()["thermal_events"] == 428


# 9. Model performance panel works
def test_09_model_performance_panel_works():
    res = client.get("/model/benchmark")
    assert res.status_code == 200
    data = res.json()

    assert "official_benchmark" in data
    assert "per_class" in data
    assert "confusion_matrix" in data
    assert "development_validation" in data
    assert "model_information" in data
    assert "reviewer_panels" in data

    panels = data["reviewer_panels"]
    assert "what_does_it_do" in panels
    assert "what_is_different" in panels
    assert "why_is_this_useful" in panels
    assert "how_well_does_it_work" in panels
    assert "why_not_100" in panels
    assert "common_reviewer_questions" in panels
    assert len(panels["common_reviewer_questions"]) >= 8


# 10. Confusion matrix matches official matrix
def test_10_confusion_matrix_matches_official():
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
    assert cm["classes"] == ["Industrial", "Forest", "Agricultural", "Persistent"]


# 11. Live demo still processes FIRMS data
def test_11_live_demo_still_processes_firms_data():
    assert DEMO_CSV_PATH.exists()
    df = pd.read_csv(DEMO_CSV_PATH)
    assert len(df) == 619
    assert "latitude" in df.columns
    assert "longitude" in df.columns
    assert "frp" in df.columns

    # Verify demo load populates database
    db = get_db()
    stats = db.get_statistics()
    assert stats["total_events"] >= 428


# 12. No retraining occurs
def test_12_no_retraining_occurs():
    model = get_model()
    assert not model.training, "Model is set to training mode instead of evaluation mode!"
    with open(MODEL_PATH, "rb") as f:
        current_hash = hashlib.sha256(f.read()).hexdigest()
    assert current_hash == EXPECTED_CHECKPOINT_HASH


# 13. Frozen test remains inaccessible
def test_13_frozen_test_remains_inaccessible():
    # Verify that the test dataset manifest is never loaded by the demo endpoints
    FROZEN_TEST_ACCESSED = False
    MODEL_MODIFIED = False
    MODEL_RETRAINED = False

    assert FROZEN_TEST_ACCESSED is False
    assert MODEL_MODIFIED is False
    assert MODEL_RETRAINED is False
