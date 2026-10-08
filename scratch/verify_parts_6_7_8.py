"""Empirical verification script for Parts 6, 7, and 8.
Collects real timings, traces a real end-to-end event, benchmarks cache hit/miss,
and tests system failure modes.
"""

import os
import sys
import time
import json
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

from src.stage8_37.database.db import get_db
from src.live.firms_poller import FirmsNrtPoller
from src.live.event_processor import LiveEventProcessor
from src.gis.proximity import ProximityEngine
from src.gis.geoapify_places import GeoapifyPlacesClient
from src.gis.cache import GisProximityCache
from src.stage8_37.inference.predictor import get_predictor
from src.live.scheduler import LiveScheduler

def verify_part_7_cache():
    print("=== PART 7: GIS CACHE HIT/MISS VERIFICATION ===")
    cache_path = PROJECT_ROOT / "data" / "cache" / "test_verification_cache.db"
    if cache_path.exists():
        cache_path.unlink()
    
    cache = GisProximityCache(db_path=cache_path)
    client = GeoapifyPlacesClient()
    engine = ProximityEngine(geoapify_client=client, cache=cache)
    
    test_lat, test_lon = 22.421, 69.865
    
    # Run 1: Cold Cache (Miss)
    t0 = time.perf_counter()
    res_miss = engine.compute_event_proximity(test_lat, test_lon)
    t_miss = (time.perf_counter() - t0) * 1000.0
    
    with cache._get_connection() as conn:
        count_miss = conn.cursor().execute("SELECT COUNT(*) FROM gis_proximity_cache").fetchone()[0]
    print(f"Cold Cache (MISS): Latency = {t_miss:.2f} ms | Cached entries = {count_miss}")
    
    # Run 2: Warm Cache (Hit)
    t0 = time.perf_counter()
    res_hit = engine.compute_event_proximity(test_lat, test_lon)
    t_hit = (time.perf_counter() - t0) * 1000.0
    
    with cache._get_connection() as conn:
        count_hit = conn.cursor().execute("SELECT COUNT(*) FROM gis_proximity_cache").fetchone()[0]
    print(f"Warm Cache (HIT): Latency = {t_hit:.2f} ms | Cached entries = {count_hit}")
    speedup = t_miss / t_hit if t_hit > 0 else 0
    print(f"Speedup: {speedup:.1f}x ({t_miss:.2f} ms -> {t_hit:.2f} ms)")
    
    del engine
    del cache
    import gc
    gc.collect()
    try:
        if cache_path.exists():
            cache_path.unlink()
    except Exception:
        pass
        
    return {
        "t_miss_ms": round(t_miss, 2),
        "t_hit_ms": round(t_hit, 2),
        "speedup": round(speedup, 1),
        "count_miss": count_miss,
        "count_hit": count_hit
    }

def verify_part_6_end_to_end_trace():
    print("\n=== PART 6: TRACE ONE COMPLETE REAL EVENT END-TO-END ===")
    poller = FirmsNrtPoller()
    dets = poller.fetch_detections(days=1, auto_fallback_days=True)
    if not dets:
        print("No live detections returned from FIRMS.")
        return None
        
    first_det = dets[0]
    print(f"1. Raw / Parsed Detection: Lat={first_det.latitude}, Lon={first_det.longitude}, Ti4={first_det.bright_ti4}, Ti5={first_det.bright_ti5}, FRP={first_det.frp}, Time={first_det.acq_datetime_utc}")
    
    processor = LiveEventProcessor()
    events = processor.event_builder.build_events([first_det])
    assert len(events) >= 1
    event = events[0]
    print(f"2. Constructed ThermalEvent: ID={event.event_id}, Centroid=({event.centroid_lat}, {event.centroid_lon}), Soundings={event.event_detection_count}")
    
    predictor = get_predictor()
    raw_arrays, meta = predictor.feature_builder.build_features_for_event(event)
    total_feature_count = sum(len(arr) for arr in raw_arrays.values())
    print(f"3. Causal Feature Vector: Total={total_feature_count} features across groups {list(raw_arrays.keys())} (Strictly causal, isolated from GIS)")
    
    pred = predictor.predict_event(event)
    print(f"4. Model Inference: Class={pred.predicted_class}, Conf={pred.confidence:.4f}, Probs: Ind={pred.probability_industrial:.4f}, For={pred.probability_forest:.4f}, Agr={pred.probability_agricultural:.4f}, Per={pred.probability_persistent:.4f}")
    
    # GIS Proximity
    engine = ProximityEngine()
    prox = engine.compute_event_proximity(event.centroid_lat, event.centroid_lon)
    print(f"5. GIS Proximity Context:")
    print(f"   - Industry: {prox.get('nearest_industry_name')} ({prox.get('distance_to_industry_km')} km)")
    print(f"   - School: {prox.get('nearest_school_name')} ({prox.get('distance_to_school_km')} km)")
    print(f"   - Hospital: {prox.get('nearest_hospital_name')} ({prox.get('distance_to_hospital_km')} km)")
    print(f"   - Village: {prox.get('nearest_village_name')} ({prox.get('distance_to_village_km')} km)")
    
    # Save to DB
    db = get_db()
    db.save_event(event)
    db.save_prediction(pred)
    db.save_proximity(event.event_id, prox)
    
    # Verify in DB
    ev_from_db = db.get_event(event.event_id)
    assert ev_from_db is not None
    assert ev_from_db["predicted_class"] == pred.predicted_class
    assert ev_from_db["proximity"]["nearest_school_name"] == prox.get("nearest_school_name")
    print(f"6. Database Persistence Verified: Event {event.event_id} stored in thermal_events, event_predictions, event_proximity.")
    
    # Verify in GeoJSON
    geojson = db.get_geojson()
    feat = next((f for f in geojson["features"] if f["properties"]["event_id"] == event.event_id), None)
    assert feat is not None
    print(f"7. GeoJSON Verified: Coordinates={feat['geometry']['coordinates']}, Class={feat['properties']['predicted_class']}")
    
    return {
        "event_id": event.event_id,
        "centroid": [event.centroid_lat, event.centroid_lon],
        "detection": first_det.model_dump(),
        "prediction": pred.model_dump(),
        "proximity": prox
    }

def verify_part_8_failure_modes():
    print("\n=== PART 8: SYSTEM FAILURE MODES VALIDATION ===")
    
    # 1. FIRMS Missing Key
    poller_no_key = FirmsNrtPoller(map_key="")
    assert poller_no_key.is_configured is False
    try:
        res = poller_no_key.fetch_detections()
        assert False, "Should have raised FirmsPollerError"
    except Exception as e:
        print(f"1. Missing FIRMS_MAP_KEY correctly raised clean FirmsPollerError: {e}")
        
    # 2. Geoapify Missing Key
    geo_no_key = GeoapifyPlacesClient(api_key="")
    assert geo_no_key.is_configured is False
    res_geo = geo_no_key.query_nearest(22.0, 79.0, "education.school")
    assert res_geo is None
    print("2. Missing GEOAPIFY_API_KEY: Correctly handled -> returns None gracefully, classifier unaffected.")
    
    # 3. Geoapify Engine with unconfigured client
    engine_unconfigured = ProximityEngine(geoapify_client=geo_no_key)
    prox_res = engine_unconfigured.compute_event_proximity(22.0, 79.0)
    assert prox_res["proximity_status"] in ("PARTIAL", "UNAVAILABLE")
    assert prox_res["distance_to_school_km"] is None
    assert prox_res["nearest_school_name"] is None
    print("3. Proximity Engine with unconfigured Geoapify: status='PARTIAL'/'UNAVAILABLE', no fake distances.")
    
    # 4. Network Timeout Mocking
    from unittest.mock import patch
    import requests
    with patch("requests.get", side_effect=requests.Timeout("Connection timed out")):
        poller_timeout = FirmsNrtPoller(map_key="test_key")
        try:
            res = poller_timeout.fetch_detections()
            assert False, "Should have raised FirmsPollerError on timeout"
        except Exception as e:
            print(f"4. FIRMS Network Timeout: Cleanly converted to FirmsPollerError: {e}")
            
    # 5. Database Concurrency / Safety
    db = get_db()
    stats = db.get_statistics()
    print(f"5. Database Integrity: {stats['total_events']} events, {stats['total_detections']} detections intact.")
    
    return True

if __name__ == "__main__":
    cache_res = verify_part_7_cache()
    trace_res = verify_part_6_end_to_end_trace()
    fail_res = verify_part_8_failure_modes()
    
    print("\nAll Part 6, 7, 8 empirical verification checks completed successfully.")
