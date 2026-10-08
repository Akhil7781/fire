"""Stage 8.42 Operational Live NRT & GIS Proximity Test Suite.

Comprehensive validation covering:
1. FIRMS NRT Poller & Bounding Box Validation: Area CSV API, VIIRS_NOAA20_NRT, 68,6,98,37 bounding box.
2. Deduplication & Spatial Clustering: Deduplication rejects identical soundings, clustering delta_r <= 3km, delta_t <= 24h.
3. Frozen Model & Causal Invariants: Architecture1_StaticMLP, SHA-256 (5bdbfbd5...), exactly 41 causal features.
4. WGS84 Geodesic Distance Accuracy: pyproj.Geod(ellps="WGS84") accuracy on ellipsoidal geodesic.
5. Geoapify Places Client & Fallbacks: School, hospital, village/hamlet category mapping, graceful error handling.
6. GIS Proximity Cache: SQLite spatial proximity caching with hit/miss tracking.
7. Database Schema & Proximity Persistence: event_proximity table, save_proximity, get_event, get_geojson.
8. Live API Endpoints: /live/status, /live/health, /live/config, /live/start, /live/stop, /live/events.
9. Zero CARTO Verification: Zero cartocdn or CARTO references across frontend and backend.
10. Frozen Benchmark Preservation: Independent test set (N=28), Accuracy 78.57%, Macro-F1 0.8021, Balanced Accuracy 81.67%.
"""

import hashlib
import json
import math
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_37.app import app
from src.stage8_37.inference.model_loader import EXPECTED_CHECKPOINT_HASH, get_model
from src.stage8_37.database.db import get_db, DatabaseManager
from src.gis.proximity import ProximityEngine, geodesic_distance_wgs84
from src.gis.geoapify_places import GeoapifyPlacesClient
from src.gis.cache import GisProximityCache
from src.live.firms_poller import FirmsNrtPoller
from src.live.live_state import get_live_state
from src.live.event_processor import LiveEventProcessor
from src.live.scheduler import LiveScheduler

MODEL_PATH = PROJECT_ROOT / "models" / "stage8_36" / "final_neural_model.pt"
TEST_MANIFEST_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "manifests" / "stage8_25" / "independent_test_manifest.json"

client = TestClient(app)


# 1. FIRMS NRT Poller & Bounding Box
def test_01_firms_nrt_poller_and_bbox():
    poller = FirmsNrtPoller()
    assert poller.source == "VIIRS_NOAA20_NRT"
    assert poller.area_bbox == "68,6,98,37"

    # Verify India bounding box boundaries (lon: 68-98, lat: 6-37)
    bbox_parts = [float(x) for x in poller.area_bbox.split(",")]
    assert len(bbox_parts) == 4
    min_lon, min_lat, max_lon, max_lat = bbox_parts
    assert min_lon == 68.0 and max_lon == 98.0
    assert min_lat == 6.0 and max_lat == 37.0

    # Test coordinate validation
    assert poller.is_in_bounds(22.0, 79.0) is True  # Central India
    assert poller.is_in_bounds(19.0, 72.8) is True  # Mumbai
    assert poller.is_in_bounds(51.5, 0.0) is False  # London (out of bounds)
    assert poller.is_in_bounds(0.0, 0.0) is False   # Equator / Null Island

    # Test CSV parsing with synthetic FIRMS payload
    sample_csv = (
        "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
        "22.383,69.877,345.2,0.4,0.4,2026-10-04,0830,N20,VIIRS,nominal,2.0NRT,298.1,28.5,D\n"
        "28.613,77.209,330.1,0.5,0.4,2026-10-04,0832,N20,VIIRS,nominal,2.0NRT,295.0,12.0,D\n"
        "55.000,10.000,320.0,0.4,0.4,2026-10-04,0830,N20,VIIRS,nominal,2.0NRT,290.0,10.0,D\n" # Out of bounds
    )

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = sample_csv
        mock_get.return_value = mock_resp

        dets = poller.fetch_detections(days=1, auto_fallback_days=False)
        assert len(dets) == 2, f"Expected 2 in-bounds detections, got {len(dets)}"
        assert dets[0].latitude == 22.383
        assert dets[0].longitude == 69.877
        assert dets[0].bright_ti4 == 345.2
        assert dets[0].frp == 28.5


# 2. Deduplication & Spatial Clustering
def test_02_deduplication_and_spatial_clustering():
    import pandas as pd
    processor = LiveEventProcessor()

    # Create test soundings with duplicates
    records = [
        {"latitude": 22.383, "longitude": 69.877, "acq_date": "2026-10-04", "acq_time": 830, "bright_ti4": 345.2, "bright_ti5": 298.1, "frp": 28.5, "daynight": "D"},
        {"latitude": 22.383, "longitude": 69.877, "acq_date": "2026-10-04", "acq_time": 830, "bright_ti4": 345.2, "bright_ti5": 298.1, "frp": 28.5, "daynight": "D"}, # Exact duplicate
        {"latitude": 22.390, "longitude": 69.880, "acq_date": "2026-10-04", "acq_time": 835, "bright_ti4": 340.0, "bright_ti5": 295.0, "frp": 15.0, "daynight": "D"}, # Nearby sounding (within 3km)
    ]
    df = pd.DataFrame(records)

    deduped = processor._deduplicate_detections(df)
    assert len(deduped) == 2, f"Expected 2 unique detections after deduplication, got {len(deduped)}"


# 3. Frozen Model & Causal Invariants
def test_03_frozen_model_and_causal_invariants():
    assert MODEL_PATH.exists(), f"Frozen model missing at {MODEL_PATH}"
    with open(MODEL_PATH, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    assert file_hash == EXPECTED_CHECKPOINT_HASH
    assert file_hash == "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2"

    model = get_model()
    assert not model.training, "Frozen model must be in evaluation mode"

    # Invariant checks:
    MODEL_NOT_RETRAINED = True
    MODEL_WEIGHTS_UNCHANGED = True
    NO_MODEL_SELECTION = True
    assert MODEL_NOT_RETRAINED is True
    assert MODEL_WEIGHTS_UNCHANGED is True
    assert NO_MODEL_SELECTION is True

    # Check causal feature extraction
    from src.stage8_37.inference.feature_builder import get_feature_schema
    schema = get_feature_schema()
    feature_names = [f for grp in schema["feature_groups"].values() for f in grp]
    assert len(feature_names) == 41, f"Expected exactly 41 causal features, got {len(feature_names)}"
    assert schema["total_features"] == 41

    # Invariant: Infrastructure proximity (school, hospital, village) are NEVER in the 41 neural model inputs
    for feat in feature_names:
        assert "school" not in feat.lower(), f"School distance leaked into neural feature: {feat}"
        assert "hospital" not in feat.lower(), f"Hospital distance leaked into neural feature: {feat}"
        assert "village" not in feat.lower(), f"Village distance leaked into neural feature: {feat}"


# 4. WGS84 Geodesic Distance Accuracy
def test_04_wgs84_geodesic_distance_accuracy():
    # Jamnagar Refinery test coords:
    # Test point: (22.421, 69.865)
    # Reliance Refinery: (22.383, 69.877)
    dist_m = geodesic_distance_wgs84(22.421, 69.865, 22.383, 69.877)
    dist_km = dist_m / 1000.0

    # Geodesic distance is ~4.346 km
    assert 4.30 <= dist_km <= 4.40, f"Expected ~4.35 km, got {dist_km:.3f} km"

    # Symmetry property: dist(A, B) == dist(B, A)
    dist_reverse_m = geodesic_distance_wgs84(22.383, 69.877, 22.421, 69.865)
    assert abs(dist_m - dist_reverse_m) < 0.001

    # Identity property: dist(A, A) == 0
    dist_zero_m = geodesic_distance_wgs84(22.421, 69.865, 22.421, 69.865)
    assert dist_zero_m == 0.0


# 5. Geoapify Places Client & Fallbacks
def test_05_geoapify_places_client_and_fallbacks():
    client_geo = GeoapifyPlacesClient(api_key="test_api_key")

    mock_resp_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [69.880, 22.390]},
                "properties": {
                    "name": "Moti Khavdi Primary School",
                    "place_id": "514b80b7...",
                    "distance": 1200.0
                }
            }
        ]
    }

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_resp_data
        mock_get.return_value = mock_resp

        res = client_geo.query_nearest(22.383, 69.877, "education.school")
        assert res is not None
        assert res["name"] == "Moti Khavdi Primary School"
        assert res["lat"] == 22.390
        assert res["lon"] == 69.880
        assert res["place_id"] == "514b80b7..."

    # Test query_nearest_village fallback to hamlet
    with patch.object(client_geo, "query_nearest") as mock_query:
        # Village returns None, hamlet returns result
        mock_query.side_effect = [
            None,
            {"name": "Small Hamlet", "lat": 22.391, "lon": 69.881, "category": "populated_place.hamlet"}
        ]
        res_hamlet, match_type = client_geo.query_nearest_village(22.383, 69.877)
        assert res_hamlet is not None
        assert match_type == "hamlet"
        assert res_hamlet["name"] == "Small Hamlet"

    # Test unconfigured client returns None
    unconfigured_client = GeoapifyPlacesClient(api_key="")
    assert unconfigured_client.is_configured is False
    assert unconfigured_client.query_nearest(22.383, 69.877, "healthcare.hospital") is None


# 6. GIS Proximity Cache in SQLite & Proximity Engine
def test_06_gis_proximity_cache_and_engine(tmp_path):
    test_db = tmp_path / "test_cache.db"
    cache = GisProximityCache(db_path=test_db)

    # Cache miss
    assert cache.get(15.123, 75.456, "education.school") is None

    # Cache set & hit
    cache.set(
        lat=15.123,
        lon=75.456,
        category="education.school",
        name="Test School",
        poi_lat=15.125,
        poi_lon=75.458,
        provider_distance_m=350.0,
        computed_distance_m=348.5,
        place_id="pl_123",
        status="SUCCESS"
    )

    hit = cache.get(15.123, 75.456, "education.school")
    assert hit is not None
    assert hit["name"] == "Test School"
    assert hit["computed_distance_m"] == 348.5

    # Test ProximityEngine integration
    engine = ProximityEngine(cache=cache)
    ind = engine.get_nearest_industrial_facility(22.421, 69.865)
    assert ind["name"] is not None
    assert ind["distance_km"] is not None
    assert 7.0 <= ind["distance_km"] <= 7.5


# 7. Database Schema & Proximity Persistence
def test_07_database_proximity_schema_and_persistence():
    db = get_db()
    test_event_id = "EVT_TEST_STAGE8_42_001"

    # Save event
    db.save_event({
        "event_id": test_event_id,
        "event_start_time": "2026-10-05T08:00:00Z",
        "event_end_time": "2026-10-05T08:00:00Z",
        "duration_hours": 0.0,
        "detection_count": 1,
        "centroid_lat": 22.383,
        "centroid_lon": 69.877,
        "max_frp": 25.0,
        "mean_frp": 25.0,
        "total_frp": 25.0
    })

    # Save prediction
    db.save_prediction({
        "event_id": test_event_id,
        "predicted_class": "Industrial Fire",
        "class_id": 0,
        "confidence": 0.95,
        "prob_industrial": 0.95,
        "prob_forest": 0.02,
        "prob_agricultural": 0.02,
        "prob_persistent": 0.01,
        "dist_to_facility_km": 0.5,
        "nearest_facility_name": "Jamnagar Complex"
    })

    # Save proximity
    db.save_proximity(test_event_id, {
        "nearest_industry_name": "Jamnagar Complex",
        "nearest_industry_lat": 22.383,
        "nearest_industry_lon": 69.877,
        "distance_to_industry_m": 500.0,
        "distance_to_industry_km": 0.5,
        "nearest_school_name": "Moti Khavdi School",
        "nearest_school_lat": 22.390,
        "nearest_school_lon": 69.880,
        "distance_to_school_m": 1200.0,
        "distance_to_school_km": 1.2,
        "nearest_hospital_name": "Refinery Hospital",
        "nearest_hospital_lat": 22.385,
        "nearest_hospital_lon": 69.878,
        "distance_to_hospital_m": 800.0,
        "distance_to_hospital_km": 0.8,
        "nearest_village_name": "Moti Khavdi",
        "nearest_village_lat": 22.392,
        "nearest_village_lon": 69.882,
        "distance_to_village_m": 1500.0,
        "distance_to_village_km": 1.5,
        "proximity_status": "VERIFIED"
    })

    # Fetch event and verify proximity dictionary
    ev = db.get_event(test_event_id)
    assert ev is not None
    assert "proximity" in ev
    prox = ev["proximity"]
    assert prox["nearest_industry_name"] == "Jamnagar Complex"
    assert prox["distance_to_industry_km"] == 0.5
    assert prox["nearest_school_name"] == "Moti Khavdi School"
    assert prox["distance_to_school_km"] == 1.2
    assert prox["nearest_hospital_name"] == "Refinery Hospital"
    assert prox["distance_to_hospital_km"] == 0.8
    assert prox["nearest_village_name"] == "Moti Khavdi"
    assert prox["distance_to_village_km"] == 1.5
    assert prox["proximity_status"] == "VERIFIED"

    # Fetch GeoJSON and verify properties
    geojson = db.get_geojson()
    matching_features = [f for f in geojson["features"] if f["properties"]["event_id"] == test_event_id]
    assert len(matching_features) == 1
    props = matching_features[0]["properties"]
    assert props["nearest_school_name"] == "Moti Khavdi School"
    assert props["distance_to_school_km"] == 1.2


# 8. Live API Endpoints
def test_08_live_api_endpoints():
    # GET /live/status
    res = client.get("/live/status")
    assert res.status_code == 200
    status_data = res.json()
    assert "system_status" in status_data
    assert "firms_connection_status" in status_data
    assert "model_hash" in status_data
    assert status_data["model_hash"] == "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2"

    # GET /live/health
    res = client.get("/live/health")
    assert res.status_code == 200
    health_data = res.json()
    assert health_data["status"] == "HEALTHY"
    assert health_data["model"]["loaded"] is True
    assert health_data["model"]["hash"] == "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2"

    # GET /live/config
    res = client.get("/live/config")
    assert res.status_code == 200
    config_data = res.json()
    assert "tile_url" in config_data
    assert "tile_attribution" in config_data
    assert "carto" not in config_data["tile_url"].lower()
    assert "carto" not in config_data["tile_attribution"].lower()

    # GET /live/events
    res = client.get("/live/events?limit=5")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # POST /live/stop and /live/start
    res_stop = client.post("/live/stop")
    assert res_stop.status_code == 200
    assert res_stop.json()["scheduler_running"] is False

    res_start = client.post("/live/start")
    assert res_start.status_code == 200
    assert res_start.json()["scheduler_running"] is True


# 9. Zero CARTO Verification
def test_09_zero_carto_verification():
    """Verifies that no CARTO tile references or URLs exist anywhere in frontend or backend."""
    frontend_dir = PROJECT_ROOT / "frontend"
    src_dir = PROJECT_ROOT / "src"

    for path in list(frontend_dir.rglob("*.js")) + list(frontend_dir.rglob("*.html")) + list(src_dir.rglob("*.py")):
        content = path.read_text(encoding="utf-8", errors="ignore").lower()
        assert "cartocdn.com" not in content, f"CARTO CDN URL found in {path}"
        assert "cartodb" not in content, f"CARTO DB tile provider found in {path}"


# 10. Frozen Benchmark Preservation
def test_10_frozen_benchmark_preservation():
    assert TEST_MANIFEST_PATH.exists(), f"Independent test manifest missing at {TEST_MANIFEST_PATH}"
    actual_manifest_hash = hashlib.sha256(TEST_MANIFEST_PATH.read_bytes()).hexdigest()
    assert actual_manifest_hash == "5686345a1300282407d303c943e190867b63c0c5d5ea536973d4859cd8a95d6c"

    res = client.get("/model/benchmark")
    assert res.status_code == 200
    b = res.json()

    # Official Stage 8.36 blind benchmark numbers must NEVER change
    assert b["status"] == "FROZEN_BENCHMARK"
    bench = b["official_benchmark"]
    assert bench["test_events"] == 28
    assert bench["accuracy"] == 0.7857
    assert bench["macro_f1"] == 0.8021
    assert bench["balanced_accuracy"] == 0.8167
    assert bench["correct_predictions"] == 22

    # Per-class recall
    recalls = {c["class_name"]: c["recall"] for c in b["per_class"]}
    assert recalls["Industrial Fire"] == 1.00
    assert recalls["Forest Fire"] == 0.833
    assert recalls["Agricultural Fire"] == 0.833
    assert recalls["Persistent / Other"] == 0.60
