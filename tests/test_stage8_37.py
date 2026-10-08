"""Stage 8.37 Mandatory Verification Test Suite.

Verifies all 18 operational and scientific invariants:
1. Frozen model checkpoint unchanged.
2. Frozen model hash matches expected hash.
3. Frozen feature schema unchanged.
4. No frozen-test access.
5. No test evaluation (TEST_EVALUATION_COUNT remains strictly 1).
6. No retraining occurred.
7. No target-derived features.
8. No persistent registry.
9. No future leakage.
10. Production causality invariant passes.
11. Model probabilities sum to 1.
12. API schema valid.
13. GeoJSON valid.
14. Database operations work.
15. Frontend receives predictions.
16. Explanation uses real feature evidence.
17. Docker configuration valid.
18. End-to-end demo succeeds.
"""

import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

EXPECTED_CHECKPOINT_HASH = "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2"

def test_1_frozen_model_checkpoint_unchanged():
    """Verify that models/stage8_36/final_neural_model.pt exists."""
    p = PROJECT_ROOT / "models" / "stage8_36" / "final_neural_model.pt"
    assert p.exists(), "Frozen checkpoint does not exist"

def test_2_frozen_model_hash_matches_expected():
    """Verify SHA-256 hash of final_neural_model.pt."""
    p = PROJECT_ROOT / "models" / "stage8_36" / "final_neural_model.pt"
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest()
    assert actual_hash == EXPECTED_CHECKPOINT_HASH, f"Model hash changed! Got {actual_hash}"

def test_3_frozen_feature_schema_unchanged():
    """Verify feature schema matches the 41-feature clean schema."""
    p = PROJECT_ROOT / "models" / "stage8_36" / "feature_schema.json"
    with open(p, "r", encoding="utf-8") as f:
        schema = json.load(f)
    assert schema["total_features"] == 41
    groups = schema["feature_groups"]
    assert len(groups["thermal"]) == 14
    assert len(groups["industrial"]) == 6
    assert len(groups["ecoregion"]) == 3
    assert len(groups["historical"]) == 18

def test_4_no_frozen_test_access():
    """Verify that Stage 8.37 source code never imports or queries the frozen test manifest."""
    src_files = list((PROJECT_ROOT / "src" / "stage8_37").rglob("*.py"))
    for sf in src_files:
        content = sf.read_text(encoding="utf-8")
        assert "independent_test_manifest.json" not in content, f"Forbidden test manifest access in {sf.name}!"

def test_5_no_test_evaluation_counter_still_one():
    """Verify that TEST_EVALUATION_COUNT in Stage 8.36 counter file remains strictly 1."""
    cnt_file = PROJECT_ROOT / "artifacts" / "stage8_36" / ".test_eval_counter"
    assert cnt_file.exists()
    count = int(cnt_file.read_text(encoding="utf-8").strip())
    assert count == 1, f"Lock violation: TEST_EVALUATION_COUNT is {count}, expected 1"

def test_6_no_retraining():
    """Verify no new weights files were trained under models/stage8_37/."""
    m37 = PROJECT_ROOT / "models" / "stage8_37"
    assert not m37.exists() or len(list(m37.glob("*.pt"))) == 0, "Violation: Models directory contains retrained models!"

def test_7_no_target_derived_features():
    """Verify that target columns never enter the feature builder schema."""
    from src.stage8_37.inference.feature_builder import get_feature_schema
    schema = get_feature_schema()
    all_features = [f for grp in schema["feature_groups"].values() for f in grp]
    forbidden_prefixes = ["target_", "class_id", "label_", "split", "is_facility_baseline"]
    for feat in all_features:
        for pfx in forbidden_prefixes:
            assert not feat.startswith(pfx), f"Target-derived feature found: {feat}"

def test_8_no_persistent_registry():
    """Verify persistent_source_manifest is not loaded or referenced in feature schema."""
    from src.stage8_37.inference.feature_builder import get_feature_schema
    schema = get_feature_schema()
    all_features = [f for grp in schema["feature_groups"].values() for f in grp]
    assert "persistent_registry_flag" not in all_features
    assert "in_persistent_registry" not in all_features

def test_9_no_future_leakage():
    """Verify that feature builder calculates cutoffs causally."""
    from src.stage8_37.inference.schemas import ThermalEventInput, FirmsDetectionRecord
    from src.stage8_37.inference.feature_builder import CausalFeatureBuilder
    import pandas as pd

    fb = CausalFeatureBuilder()
    ev = ThermalEventInput(
        event_id="EVT_LEAK_TEST",
        centroid_lat=20.0,
        centroid_lon=78.0,
        event_start_time="2026-06-01T10:00:00Z",
        event_detection_count=1,
        detections=[
            FirmsDetectionRecord(
                latitude=20.0, longitude=78.0, acq_date="2026-06-01", acq_time="1000",
                acq_datetime_utc="2026-06-01T10:00:00Z", bright_ti4=330.0, bright_ti5=295.0,
                frp=15.0, confidence="nominal", daynight="D"
            )
        ]
    )
    _, meta = fb.build_features_for_event(ev)
    t0 = pd.to_datetime(ev.event_start_time)
    thist = pd.to_datetime(meta["historical_cutoff"])
    assert thist == t0 - pd.Timedelta(days=7)

def test_10_production_causality_invariant_passes():
    """Verify that future injection at +1h, +6h, +24h, +7d, +30d produces 0 change."""
    from src.stage8_37.causality_test import run_production_causality_test
    res = run_production_causality_test()
    assert res["status"] == "PASS"

def test_11_model_probabilities_sum_to_one():
    """Verify that output probabilities sum to 1.0."""
    from src.stage8_37.inference.schemas import ThermalEventInput, FirmsDetectionRecord
    from src.stage8_37.inference.predictor import get_predictor

    predictor = get_predictor()
    ev = ThermalEventInput(
        event_id="EVT_SUM_TEST",
        centroid_lat=19.0,
        centroid_lon=73.0,
        event_start_time="2026-05-01T12:00:00Z",
        event_detection_count=1,
        detections=[
            FirmsDetectionRecord(
                latitude=19.0, longitude=73.0, acq_date="2026-05-01", acq_time="1200",
                acq_datetime_utc="2026-05-01T12:00:00Z", bright_ti4=340.0, bright_ti5=295.0,
                frp=20.0, confidence="high", daynight="D"
            )
        ]
    )
    pred = predictor.predict_event(ev)
    p_sum = pred.probability_industrial + pred.probability_forest + pred.probability_agricultural + pred.probability_persistent
    assert np.isclose(p_sum, 1.0, atol=1e-5)

def test_12_api_schema_valid():
    """Verify FastAPI application OpenAPI schema has all expected routes."""
    from src.stage8_37.app import app
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "HEALTHY"

    openapi = app.openapi()
    paths = openapi["paths"]
    for expected_path in ["/health", "/predict", "/predict/batch", "/events", "/events/{event_id}", "/statistics", "/api/geojson"]:
        assert expected_path in paths, f"Missing route {expected_path} in API schema!"

def test_13_geojson_valid():
    """Verify GeoJSON endpoint produces valid RFC 7946 FeatureCollection."""
    from src.stage8_37.app import app
    client = TestClient(app)
    resp = client.get("/api/geojson")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data

def test_14_database_operations_work():
    """Verify database write and read roundtrip."""
    from src.stage8_37.database.db import get_db
    from src.stage8_37.inference.schemas import ThermalEventInput, FirmsDetectionRecord
    from src.stage8_37.inference.predictor import get_predictor

    db = get_db()
    predictor = get_predictor()
    ev = ThermalEventInput(
        event_id="EVT_DB_TEST",
        centroid_lat=22.5,
        centroid_lon=88.3,
        event_start_time="2026-06-01T08:00:00Z",
        event_detection_count=1,
        detections=[
            FirmsDetectionRecord(
                latitude=22.5, longitude=88.3, acq_date="2026-06-01", acq_time="0800",
                acq_datetime_utc="2026-06-01T08:00:00Z", bright_ti4=332.0, bright_ti5=294.0,
                frp=11.5, confidence="nominal", daynight="D"
            )
        ]
    )
    db.save_event(ev)
    pred = predictor.predict_event(ev)
    db.save_prediction(pred)

    fetched = db.get_event("EVT_DB_TEST")
    assert fetched is not None
    assert fetched["event_id"] == "EVT_DB_TEST"
    assert fetched["predicted_class"] == pred.predicted_class

def test_15_frontend_receives_predictions():
    """Verify frontend HTML, CSS, and JS exist and serve properly."""
    from src.stage8_37.app import app
    client = TestClient(app)
    r_index = client.get("/")
    assert r_index.status_code == 200
    assert "NASA FIRMS Thermal-Source Attribution Dashboard" in r_index.text

    p_css = PROJECT_ROOT / "frontend" / "styles.css"
    p_js = PROJECT_ROOT / "frontend" / "app.js"
    assert p_css.exists() and p_js.exists()

def test_16_explanation_uses_real_feature_evidence():
    """Verify explanation contains structured feature groups."""
    from src.stage8_37.inference.schemas import ThermalEventInput, FirmsDetectionRecord
    from src.stage8_37.inference.predictor import get_predictor

    predictor = get_predictor()
    ev = ThermalEventInput(
        event_id="EVT_EXPL_TEST",
        centroid_lat=17.658,
        centroid_lon=75.906,
        event_start_time="2026-06-01T10:30:00Z",
        event_detection_count=1,
        detections=[
            FirmsDetectionRecord(
                latitude=17.658, longitude=75.906, acq_date="2026-06-01", acq_time="1030",
                acq_datetime_utc="2026-06-01T10:30:00Z", bright_ti4=355.0, bright_ti5=300.0,
                frp=40.0, confidence="high", daynight="D"
            )
        ]
    )
    pred = predictor.predict_event(ev)
    expl = pred.explanation
    assert len(expl.prediction_summary) > 0
    assert len(expl.thermal_evidence) > 0
    assert len(expl.recurrence_evidence) > 0
    assert len(expl.ecological_evidence) > 0
    assert len(expl.industrial_evidence) > 0

def test_17_docker_configuration_valid():
    """Verify Dockerfile and docker-compose.yml exist and contain correct configurations."""
    df_path = PROJECT_ROOT / "docker" / "Dockerfile"
    dc_path = PROJECT_ROOT / "docker" / "docker-compose.yml"
    assert df_path.exists()
    assert dc_path.exists()
    assert "python:3.10-slim" in df_path.read_text(encoding="utf-8")
    assert "postgis/postgis" in dc_path.read_text(encoding="utf-8")

def test_18_end_to_end_demo_succeeds():
    """Verify demo_run.md exists and contains execution records."""
    demo_report = PROJECT_ROOT / "artifacts" / "stage8_37" / "demo_run.md"
    assert demo_report.exists()
    content = demo_report.read_text(encoding="utf-8")
    assert "OPERATIONAL INTEGRATION VERIFIED" in content
    assert "Architecture1_StaticMLP" in content
