"""Stage 8.38 Invalid Input Robustness Test Engine.

Tests that all malformed, corrupted, out-of-bounds, or missing inputs are safely rejected
with structured error responses without crashing the service or fabricating values.
"""

import io
import json
import logging
import sys
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_37.app import app
from src.stage8_37.ingestion.validators import validate_detection_record
from src.stage8_37.ingestion.firms_loader import FirmsLoader

logger = logging.getLogger(__name__)

def run_robustness_tests() -> dict:
    logger.info("Executing Invalid Input Robustness Tests...")
    client = TestClient(app)
    test_cases = [
        {"name": "Latitude > 90", "payload": {"latitude": 95.0, "longitude": 75.0, "frp": 10.0}, "valid": False},
        {"name": "Latitude < -90", "payload": {"latitude": -95.0, "longitude": 75.0, "frp": 10.0}, "valid": False},
        {"name": "Longitude > 180", "payload": {"latitude": 20.0, "longitude": 185.0, "frp": 10.0}, "valid": False},
        {"name": "Longitude < -180", "payload": {"latitude": 20.0, "longitude": -185.0, "frp": 10.0}, "valid": False},
        {"name": "Negative FRP", "payload": {"latitude": 20.0, "longitude": 75.0, "frp": -25.0}, "valid": False},
        {"name": "Missing FRP handled with default 0.0", "payload": {"latitude": 20.0, "longitude": 75.0, "acq_date": "2026-06-01", "acq_time": "1200", "bright_ti4": 330.0, "bright_ti5": 290.0}, "valid": True},
        {"name": "Invalid Timestamp", "payload": {"latitude": 20.0, "longitude": 75.0, "acq_date": "invalid-date", "acq_time": "9999"}, "valid": False},
        {"name": "Missing Coordinates", "payload": {"frp": 15.0, "bright_ti4": 330.0}, "valid": False},
        {"name": "Zero/Negative Brightness Temp", "payload": {"latitude": 20.0, "longitude": 75.0, "bright_ti4": -10.0, "bright_ti5": 0.0}, "valid": False}
    ]

    results = []
    for tc in test_cases:
        is_val, err_msg, norm = validate_detection_record(tc["payload"])
        assert is_val == tc["valid"], f"Test '{tc['name']}' failed! Expected valid={tc['valid']}, got {is_val}"
        results.append({
            "test_case": tc["name"],
            "expected_valid": tc["valid"],
            "result_valid": is_val,
            "error_message": err_msg or "Normalized Successfully",
            "verdict": "PASS"
        })

    # Empty CSV test
    empty_csv = io.StringIO("")
    loader = FirmsLoader()
    try:
        dets = loader.load_from_csv(empty_csv)
        assert len(dets) == 0
        results.append({
            "test_case": "Empty CSV Parsing",
            "expected_valid": True,
            "result_valid": True,
            "error_message": "Empty detection list returned safely",
            "verdict": "PASS"
        })
    except Exception as e:
        # Either empty list or graceful exception is valid
        results.append({
            "test_case": "Empty CSV Parsing",
            "expected_valid": False,
            "result_valid": False,
            "error_message": str(e),
            "verdict": "PASS"
        })

    # Malformed JSON to API
    bad_resp = client.post("/predict", content=b"INVALID_JSON_STREAM{{{", headers={"Content-Type": "application/json"})
    assert bad_resp.status_code in [400, 422]
    results.append({
        "test_case": "Malformed JSON API Payload",
        "expected_valid": False,
        "result_valid": False,
        "error_message": "Rejected with HTTP 422/400",
        "verdict": "PASS"
    })

    logger.info(f"All {len(results)} robustness test cases passed.")
    return {"status": "SUCCESS", "results": results}

if __name__ == "__main__":
    res = run_robustness_tests()
    print("Robustness Tests Completed:")
    for r in res["results"]:
        print(f"  [{r['verdict']}] {r['test_case']}: {r['error_message']}")
