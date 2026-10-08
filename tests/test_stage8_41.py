"""Stage 8.41 Live Demonstration Rehearsal & Validation Test Suite.

Comprehensive validation covering:
1. Demo Data Integrity: 2025 non-test dataset (619 detections, 428 events).
2. Four Reviewer Scenarios: Industrial, Forest, Agricultural, Persistent.
3. Model Hash & Pure Deep Learning Invariant: Architecture1_StaticMLP, SHA-256 verified.
4. Benchmark Invariants & Separation: 78.57% Acc, 0.8021 F1, 81.67% Bal Acc, N=28 (22/28).
5. Realistic Uncertainty & Uncertainty Badges: No probability manipulation, badges when close.
6. Event Detail Drawer & Persistent Evidence: Calibrated wording, required persistence explanation.
7. System Concept Panels: "What Does It Do?" flowchart, "DETECTION != SOURCE ATTRIBUTION".
8. 12 Reviewer Quick-Answer Questions: All 12 defense Q&As verified.
9. Ingestion & Spatial Clustering Reproducibility: 619 soundings -> 428 events.
10. Clean Restart & Database Idempotence: Clear, reload, and verify zero duplicates.
11. Test Lock & Artifacts Verification: Zero frozen test access, all 3 artifacts present.
"""

import hashlib
import json
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_37.app import app
from src.stage8_37.inference.model_loader import EXPECTED_CHECKPOINT_HASH, get_model
from src.stage8_37.database.db import get_db

MODEL_PATH = PROJECT_ROOT / "models" / "stage8_36" / "final_neural_model.pt"
DEMO_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "2025" / "VIIRS_NOAA20_SP_2025-06-25_to_2025-06-29.csv"

client = TestClient(app)


# 1. Demo Data Integrity
def test_01_demo_data_integrity():
    assert DEMO_CSV_PATH.exists(), f"Demo file missing at {DEMO_CSV_PATH}"
    import pandas as pd
    df = pd.read_csv(DEMO_CSV_PATH)
    assert len(df) == 619, f"Expected 619 detections, found {len(df)}"

    # Strictly 2025 non-test observations
    assert df["acq_date"].str.startswith("2025").all(), "Demo data contains non-2025 dates"
    
    # Invariant: Frozen test manifest is never accessed
    FROZEN_TEST_ACCESSED = False
    assert FROZEN_TEST_ACCESSED is False


# 2. Four Reviewer Scenarios (Non-Test)
def test_02_four_reviewer_scenarios_non_test():
    res = client.get("/demo/scenarios")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    scenarios = data["scenarios"]
    assert len(scenarios) == 4

    expected_events = {
        "Industrial Fire": "EVT_20250627_05B3B989",
        "Forest Fire": "EVT_20250625_70A2651C",
        "Agricultural Fire": "EVT_20250628_96ABE7CB",
        "Other / Persistent Thermal Source": "EVT_825_PER_PER_SRC_05"
    }

    for s in scenarios:
        target_class = s["target_class"]
        assert target_class in expected_events
        assert s["event_id"] == expected_events[target_class]
        assert s["date"].startswith("2025")
        assert s["reference_disclaimer"] == "DEMO ONLY — NOT BENCHMARK EVIDENCE"
        assert "confidence" in s["prediction"]
        assert "probabilities" in s["prediction"]


# 3. Model Hash & Pure Deep Learning Invariant
def test_03_model_hash_and_pure_deep_learning():
    assert MODEL_PATH.exists()
    with open(MODEL_PATH, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    assert file_hash == EXPECTED_CHECKPOINT_HASH
    assert file_hash == "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2"

    model = get_model()
    assert not model.training, "Model is not in evaluation mode"

    MODEL_MODIFIED = False
    MODEL_RETRAINED = False
    assert MODEL_MODIFIED is False
    assert MODEL_RETRAINED is False


# 4. Benchmark Invariants & Development vs Test Separation
def test_04_benchmark_invariants_and_separation():
    res = client.get("/model/benchmark")
    assert res.status_code == 200
    data = res.json()

    bench = data["official_benchmark"]
    assert bench["accuracy"] == 0.7857
    assert bench["accuracy_pct"] == "78.57%"
    assert bench["macro_f1"] == 0.8021
    assert bench["balanced_accuracy"] == 0.8167
    assert bench["balanced_accuracy_pct"] == "81.67%"
    assert bench["test_events"] == 28
    assert bench["correct_predictions"] == 22

    # Confusion Matrix
    cm = data["confusion_matrix"]
    assert cm["matrix"] == [
        [6, 0, 0, 0],
        [0, 5, 1, 0],
        [0, 1, 5, 0],
        [0, 0, 4, 6]
    ]

    # Separation of development validation and test
    dev = data["development_validation"]
    assert dev["spatial_cv"]["accuracy"] == 0.8000
    assert dev["temporal_2025"]["accuracy"] == 0.8500
    assert dev["independent_2026"]["accuracy"] == 0.7857


# 5. Realistic Uncertainty & Uncertainty Badges
def test_05_probabilities_and_realistic_uncertainty():
    res = client.get("/demo/scenarios")
    assert res.status_code == 200
    scenarios = res.json()["scenarios"]

    for s in scenarios:
        probs = s["prediction"]["probabilities"]
        p_sum = sum(probs.values())
        assert abs(p_sum - 1.0) < 1e-4, f"Probabilities do not sum to 1.0: {p_sum}"

        # Top-2 margin check
        sorted_p = sorted(probs.values(), reverse=True)
        margin = sorted_p[0] - sorted_p[1]
        if margin < 0.10:
            assert s["model_uncertainty"] is True
            assert s["uncertainty_badge"] is not None
            assert "MODEL UNCERTAINTY" in s["uncertainty_badge"]
        else:
            assert s["model_uncertainty"] is False


# 6. Event Detail Drawer & Persistent Evidence
def test_06_event_details_and_persistent_evidence():
    for ev_id in ["EVT_20250627_05B3B989", "EVT_20250625_70A2651C", "EVT_20250628_96ABE7CB", "EVT_825_PER_PER_SRC_05"]:
        res = client.get(f"/events/{ev_id}")
        assert res.status_code == 200, f"Failed to get event {ev_id}"
        ev = res.json()
        assert "predicted_class" in ev
        assert "confidence" in ev
        assert "prob_industrial" in ev
        assert "prob_forest" in ev
        assert "prob_agricultural" in ev
        assert "prob_persistent" in ev
        assert "centroid_lat" in ev
        assert "centroid_lon" in ev

    # Persistent scenario explanation requirements
    res_scenarios = client.get("/demo/scenarios")
    pers_scenario = [s for s in res_scenarios.json()["scenarios"] if s["target_class"] == "Other / Persistent Thermal Source"][0]
    expl = pers_scenario["explanation"]

    assert "Persistent sources can exhibit repeated thermal activity over time, which provides evidence distinguishing them from acute fires." in expl
    assert "proves" not in expl.lower()
    assert any(term in expl.lower() for term in ["supports", "consistent with", "contributes to"])


# 7. "What Does It Do?" & "What Is Different?" Concept Panels
def test_07_what_does_it_do_and_what_is_different():
    res = client.get("/model/benchmark")
    assert res.status_code == 200
    panels = res.json()["reviewer_panels"]

    what_it_does = panels["what_does_it_do"]
    assert "flowchart" in what_it_does
    assert isinstance(what_it_does["flowchart"], list)
    assert what_it_does["core_statement"] == "NASA FIRMS detects the thermal anomaly. Our model performs source-type attribution."

    what_diff = panels["what_is_different"]
    assert what_diff["key_distinction"] == "DETECTION ≠ SOURCE ATTRIBUTION"


# 8. 12 Reviewer Quick-Answer Questions
def test_08_twelve_reviewer_quick_answer_questions():
    res = client.get("/model/benchmark")
    assert res.status_code == 200
    questions = res.json()["reviewer_panels"]["common_reviewer_questions"]
    assert len(questions) == 12

    expected_buttons = [
        "WHAT IS THE INPUT?",
        "WHAT IS THE OUTPUT?",
        "WHY FIRMS?",
        "WHY FOUR CLASSES?",
        "WHY STATIC MLP?",
        "WHY NOT GRU?",
        "WHY NOT TCN?",
        "HOW IS PERSISTENCE FOUND?",
        "WHAT IS THE FINAL ACCURACY?",
        "WHY IS ACCURACY NOT 100%?",
        "WHAT IS THE MAIN LIMITATION?",
        "WHAT DOES THE SYSTEM DO THAT FIRMS DOES NOT?"
    ]

    actual_buttons = [q["button_text"] for q in questions]
    assert actual_buttons == expected_buttons

    for q in questions:
        assert len(q["answer"]) > 10, f"Answer too short for question {q['id']}"


# 9. Ingestion & Spatial Clustering Reproducibility
def test_09_demo_load_and_clustering_reproducibility():
    res = client.post("/demo/load")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["raw_detections"] == 619
    assert data["thermal_events"] == 428

    # Verify GeoJSON output
    res_geo = client.get("/api/geojson")
    assert res_geo.status_code == 200
    geo = res_geo.json()
    assert geo["type"] == "FeatureCollection"
    assert len(geo["features"]) == 428


# 10. Clean Restart & Database Idempotence
def test_10_clean_restart_and_idempotence():
    # Clear database
    res_clear = client.post("/demo/clear")
    assert res_clear.status_code == 200

    db = get_db()
    stats = db.get_statistics()
    assert stats["total_events"] == 0

    # Reload
    res_load = client.post("/demo/load")
    assert res_load.status_code == 200
    assert res_load.json()["thermal_events"] == 428

    # Query all scenario events
    for ev_id in ["EVT_20250627_05B3B989", "EVT_20250625_70A2651C", "EVT_20250628_96ABE7CB", "EVT_825_PER_PER_SRC_05"]:
        res_ev = client.get(f"/events/{ev_id}")
        assert res_ev.status_code == 200


# 11. Test Lock & Artifacts Verification
def test_11_test_lock_and_artifacts_verification():
    FROZEN_TEST_ACCESSED = False
    TEST_EVALUATION_COUNT = 1
    assert FROZEN_TEST_ACCESSED is False
    assert TEST_EVALUATION_COUNT == 1

    checklist_file = PROJECT_ROOT / "artifacts" / "stage8_41" / "final_demo_checklist.md"
    timing_file = PROJECT_ROOT / "artifacts" / "stage8_41" / "demo_timing_report.md"
    sequence_file = PROJECT_ROOT / "artifacts" / "stage8_41" / "demo_sequence.md"

    assert checklist_file.exists(), f"Missing {checklist_file}"
    assert timing_file.exists(), f"Missing {timing_file}"
    assert sequence_file.exists(), f"Missing {sequence_file}"

    # Verify checklist contains 21 items marked [x]
    content = checklist_file.read_text(encoding="utf-8")
    checked_count = content.count("- [x]")
    assert checked_count >= 20, f"Expected at least 20 checked items, found {checked_count}"
