# Stage 8.38 — Operational System Demonstration Guide

This guide walks through reproducing the real NASA FIRMS demonstration, running the operational API server, and interacting with the GIS dashboard.

---

## 1. Prerequisites & Environment Setup

Ensure Python 3.10+ is active and dependencies are installed:

```bash
# Clone or navigate to repository root
cd "d:/DATA PREPROCESSING"

# Install core dependencies
pip install -r requirements.txt
pip install fastapi uvicorn pydantic python-multipart httpx pytest
```

Copy the environment template:
```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

---

## 2. Model Integrity Verification

Verify that the frozen neural model checkpoint matches the official SHA-256 hash:

```bash
python -c "import hashlib; h = hashlib.sha256(open('models/stage8_36/final_neural_model.pt', 'rb').read()).hexdigest(); print('SHA-256:', h); assert h == '5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2'"
```
Expected output:
```
SHA-256: 5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2
```

---

## 3. Running the Real NASA FIRMS Batch Demonstration

Process genuine 2025 satellite detections (`data/raw/2025/VIIRS_NOAA20_SP_2025-06-25_to_2025-06-29.csv`, N=619 detections, strictly non-test):

```bash
python src/stage8_38/run_real_firms_demo.py
```

This script:
1. Validates and ingests raw FIRMS satellite detections.
2. Clusters them into 428 discrete thermal events.
3. Extracts 41 causal features without lookahead or target proxies.
4. Executes the frozen `Architecture1_StaticMLP` PyTorch neural model.
5. Ingests all events and predictions into the operational database (`data/operational.db`).
6. Generates:
   - `artifacts/stage8_38/real_firms_demo_input_summary.md`
   - `artifacts/stage8_38/real_firms_demo_predictions.csv`
   - `artifacts/stage8_38/final_demo_report.md`

---

## 4. Starting the Operational Server & GIS Dashboard

Start the FastAPI application:

```bash
python -m src.stage8_37.app
```
Or with custom host and port:
```bash
python -c "import uvicorn; uvicorn.run('src.stage8_37.app:app', host='127.0.0.1', port=8000)"
```

Once running:
- **Interactive GIS Dashboard:** Open `http://localhost:8000/dashboard` or `http://localhost:8000/` in any browser.
- **Interactive API Documentation:** Open `http://localhost:8000/docs` (Swagger UI) or `http://localhost:8000/redoc`.

---

## 5. Querying the API via cURL or Python

### Check Health & Model Hash
```bash
curl http://localhost:8000/health
```

### Fetch All Clustered Events as GeoJSON
```bash
curl http://localhost:8000/api/geojson
```

### Attribution for a Single Thermal Event
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "DEMO_TEST_01",
    "centroid_lat": 22.30,
    "centroid_lon": 73.20,
    "event_start_time": "2025-06-25T14:00:00Z",
    "event_detection_count": 2,
    "detections": [
      {
        "latitude": 22.30,
        "longitude": 73.20,
        "acq_date": "2025-06-25",
        "acq_time": "1400",
        "acq_datetime_utc": "2025-06-25T14:00:00Z",
        "bright_ti4": 345.5,
        "bright_ti5": 298.2,
        "frp": 28.4,
        "confidence": "high",
        "daynight": "D"
      }
    ]
  }'
```

### Retrieve Structured Explanation for an Ingested Event
```bash
curl http://localhost:8000/events/EVT_20250625_6AEF88BE/explanation
```

---

## 6. Running Scientific & Operational Tests

Run the complete automated test suite:

```bash
pytest tests/test_stage8_38.py -v
```

Run causality invariance verification:
```bash
python src/stage8_37/causality_test.py
```
Expected output:
```
ALL 5 FUTURE-INJECTION CAUSALITY TESTS PASSED: CAUSALITY_INVARIANT = PASS
```
