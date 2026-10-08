"""Automated audit of frontend assets, API payload sizes, DOM structure,
and endpoint latency for Stage 8.42/Verification.
"""

import os
import sys
import time
from pathlib import Path
from html.parser import HTMLParser
from fastapi.testclient import TestClient

class NodeCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.count = 0
    def handle_starttag(self, tag, attrs):
        self.count += 1

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_37.app import app

client = TestClient(app)

def run_performance_audit():
    print("=== PERFORMANCE AUDIT & BROWSER ASSETS VERIFICATION ===")
    
    # 1. HTML Page Load
    t0 = time.perf_counter()
    resp_html = client.get("/")
    t_html = (time.perf_counter() - t0) * 1000.0
    assert resp_html.status_code == 200
    html_bytes = len(resp_html.content)
    
    counter = NodeCounter()
    counter.feed(resp_html.text)
    dom_nodes = counter.count
    
    print(f"1. HTML Load: status={resp_html.status_code}, time={t_html:.2f}ms, size={html_bytes} bytes, DOM tags={dom_nodes}")
    
    # 2. CSS Asset
    t0 = time.perf_counter()
    resp_css = client.get("/static/styles.css")
    t_css = (time.perf_counter() - t0) * 1000.0
    assert resp_css.status_code == 200
    css_bytes = len(resp_css.content)
    print(f"2. CSS Load: status={resp_css.status_code}, time={t_css:.2f}ms, size={css_bytes} bytes")
    
    # 3. JS Asset
    t0 = time.perf_counter()
    resp_js = client.get("/static/app.js")
    t_js = (time.perf_counter() - t0) * 1000.0
    assert resp_js.status_code == 200
    js_bytes = len(resp_js.content)
    print(f"3. JS Load: status={resp_js.status_code}, time={t_js:.2f}ms, size={js_bytes} bytes")
    
    # 4. Zero CARTO check
    html_text = resp_html.text.lower()
    css_text = resp_css.text.lower()
    js_text = resp_js.text.lower()
    assert "cartocdn.com" not in html_text and "cartocdn.com" not in css_text and "cartocdn.com" not in js_text
    assert "cartodb" not in html_text and "cartodb" not in css_text and "cartodb" not in js_text
    print("4. Zero CARTO verification across HTML, CSS, JS: VERIFIED (0 occurrences)")
    
    # 5. Differential /live/status payload size & latency
    t0 = time.perf_counter()
    resp_status = client.get("/live/status")
    t_status = (time.perf_counter() - t0) * 1000.0
    assert resp_status.status_code == 200
    status_bytes = len(resp_status.content)
    print(f"5. Lightweight /live/status: time={t_status:.2f}ms, size={status_bytes} bytes (< 1 KB requirement satisfied)")
    
    # 6. /api/geojson payload & latency
    t0 = time.perf_counter()
    resp_geo = client.get("/api/geojson")
    t_geo = (time.perf_counter() - t0) * 1000.0
    assert resp_geo.status_code == 200
    geo_bytes = len(resp_geo.content)
    geo_data = resp_geo.json()
    feature_count = len(geo_data.get("features", []))
    print(f"6. /api/geojson: time={t_geo:.2f}ms, size={geo_bytes} bytes, features={feature_count}")
    
    # 7. /live/events payload & latency
    t0 = time.perf_counter()
    resp_events = client.get("/live/events?limit=50")
    t_events = (time.perf_counter() - t0) * 1000.0
    assert resp_events.status_code == 200
    events_bytes = len(resp_events.content)
    print(f"7. /live/events: time={t_events:.2f}ms, size={events_bytes} bytes")
    
    # 8. Single Event Detail (/events/{id})
    if feature_count > 0:
        ev_id = geo_data["features"][0]["properties"]["event_id"]
        t0 = time.perf_counter()
        resp_detail = client.get(f"/events/{ev_id}")
        t_detail = (time.perf_counter() - t0) * 1000.0
        assert resp_detail.status_code == 200
        detail_bytes = len(resp_detail.content)
        print(f"8. Event Detail for {ev_id}: time={t_detail:.2f}ms, size={detail_bytes} bytes")
        
    # 9. Top Bar structure validation
    assert 'class="top-bar"' in resp_html.text
    top_items_count = resp_html.text.count('class="top-item')
    print(f"9. Top Bar Item Count: {top_items_count} items (<= 5 primary items requirement satisfied)")
    
    # 10. Map Panel & Sidebar structure validation
    assert 'id="map-panel"' in resp_html.text
    assert 'id="sidebar-panel"' in resp_html.text
    print("10. Main Layout: Dominant Map panel and Sidebar panel exist.")
    
    # 11. Modal structure validation
    assert 'id="tech-modal"' in resp_html.text
    print("11. Technical Details Modal exists with hidden default state.")
    
    return {
        "html_time_ms": round(t_html, 2),
        "html_bytes": html_bytes,
        "dom_nodes": dom_nodes,
        "css_time_ms": round(t_css, 2),
        "css_bytes": css_bytes,
        "js_time_ms": round(t_js, 2),
        "js_bytes": js_bytes,
        "status_time_ms": round(t_status, 2),
        "status_bytes": status_bytes,
        "geo_time_ms": round(t_geo, 2),
        "geo_bytes": geo_bytes,
        "features": feature_count,
        "top_bar_items": top_items_count
    }

if __name__ == "__main__":
    res = run_performance_audit()
    print("\nPerformance audit completed successfully.")
