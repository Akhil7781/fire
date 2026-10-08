# DS08 Quickstart Guide

This guide gets you up and running with the DS08 operational system in less than 5 minutes.

---

## 1. System Requirements

- **Operating System:** Windows, Linux, or macOS.
- **Python:** 3.10 or higher.
- **Hardware:** Standard multi-core CPU (GPU optional, CPU provides ~0.97ms forward pass latency).
- **RAM:** Minimum 4 GB recommended (operational RSS footprint is ~255 MB).

---

## 2. Installation

Clone or download the project and install dependencies:

```bash
cd "d:/DATA PREPROCESSING"

# Create a clean virtual environment (optional but recommended)
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux / macOS:
source venv/bin/activate

# Install required Python packages
pip install -r requirements.txt
pip install fastapi uvicorn pydantic python-multipart httpx pytest matplotlib psutil
```

Copy the environment template:
```bash
# Windows
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

---

## 3. Verify Model Integrity

Check that the frozen model weights and feature schemas have not been modified:

```bash
python -c "import hashlib; h = hashlib.sha256(open('models/stage8_36/final_neural_model.pt', 'rb').read()).hexdigest(); print('SHA-256:', h); assert h == '5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2', 'Checksum mismatch!'"
```

Expected output:
```
SHA-256: 5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2
```

---

## 4. Run the Real NASA FIRMS Batch Demonstration

Process genuine satellite observations from NASA FIRMS VIIRS NOAA-20 (`data/raw/2025/VIIRS_NOAA20_SP_2025-06-25_to_2025-06-29.csv`, N=619 detections, strictly non-test):

```bash
python src/stage8_38/run_real_firms_demo.py
```

This ingests raw detections, clusters them into 428 thermal events, runs causal neural inference, saves predictions to `artifacts/stage8_38/real_firms_demo_predictions.csv`, and populates `data/operational.db`.

---

## 5. Launch the Operational Server & Dashboard

Start the FastAPI backend with uvicorn:

```bash
python -m src.stage8_37.app
```

The system will start listening on `http://127.0.0.1:8000`.

- 🗺️ **GIS Dashboard:** Open `http://localhost:8000/dashboard` in your browser.
- 📖 **Interactive API Documentation:** Open `http://localhost:8000/docs` (Swagger UI).

---

## 6. Sample API Queries

### 1. System Health Check
```bash
curl http://localhost:8000/health
```

### 2. Fetch Spatial Events as GeoJSON
```bash
curl http://localhost:8000/api/geojson
```

### 3. Single Event Attribution
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "TEST_EVENT_001",
    "centroid_lat": 22.312,
    "centroid_lon": 73.195,
    "event_start_time": "2025-06-25T14:00:00Z",
    "event_detection_count": 2,
    "detections": [
      {
        "latitude": 22.312,
        "longitude": 73.195,
        "acq_date": "2025-06-25",
        "acq_time": "1400",
        "acq_datetime_utc": "2025-06-25T14:00:00Z",
        "bright_ti4": 345.2,
        "bright_ti5": 298.1,
        "frp": 25.4,
        "confidence": "high",
        "daynight": "D"
      }
    ]
  }'
```

---

## 7. Docker Deployment

Deploy with Docker Compose:

```bash
docker-compose -f docker/docker-compose.yml up -d
```

To stop:
```bash
docker-compose -f docker/docker-compose.yml down
```

---

## 8. Run Automated Test Suites

```bash
# Run the complete Stage 8.38 validation suite
pytest tests/test_stage8_38.py -v

# Run the Stage 8.37 operational pipeline tests
pytest tests/test_stage8_37.py -q

# Run causality invariance tests
python src/stage8_37/causality_test.py
```
