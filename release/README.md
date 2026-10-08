# DS08 — Operational Satellite Thermal-Source Attribution System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Framework FastAPI](https://img.shields.io/badge/framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![Model PyTorch](https://img.shields.io/badge/model-PyTorch%20Neural-red.svg)](https://pytorch.org/)
[![Status Production-Ready](https://img.shields.io/badge/status-frozen%20release-success.svg)]()

The **DS08 Industrial & Thermal-Source Attribution System** is an end-to-end, scientifically validated, production-grade deep learning pipeline for real-time 4-class attribution of satellite thermal anomalies detected by NASA FIRMS (VIIRS NOAA-20 / Suomi-NPP / MODIS) across India.

---

## 🎯 Target Attribution Classes

1. **Class 0 — Industrial Fire:** Accidental chemical, refinery, factory, manufacturing plant, or fuel storage fires within or directly adjacent to industrial facility perimeters.
2. **Class 1 — Forest Fire:** Wildfires and biomass combustion across national parks, wildlife sanctuaries, and reserved forests (Western Ghats, Central Highlands, Northeast, Himalayas).
3. **Class 2 — Agricultural Fire:** Stubble/crop residue burning (e.g. paddy, wheat stubble) in agrarian heartlands (Indo-Gangetic Plain, Krishna-Godavari, Cauvery, Malwa).
4. **Class 3 — Other / Persistent Thermal Source:** Non-emergency continuous or semi-continuous heat sources, including gas flaring, steel mill blast furnaces, thermal power stations, and brick kiln clusters.

---

## 🏆 Key Scientific & Operational Highlights

- **Pure Deep Learning Model:** Powered by the frozen `Architecture1_StaticMLP` pure PyTorch neural network (`models/stage8_36/final_neural_model.pt`).
- **Official Frozen 2026 Blind Benchmark:**
  - **Accuracy:** **78.57%** (22/28 events)
  - **Macro-F1:** **0.8021**
  - **Balanced Accuracy:** **81.67%**
  - **Industrial Recall:** **100.0%** | **Forest Recall:** **83.3%** | **Agricultural Recall:** **83.3%** | **Persistent Recall:** **60.0%**
- **Strict Causality Invariants:**
  - $t \le t_0$ strict alert-time observation cutoff (no future leakage).
  - $t \le t_0 - 7\text{ days}$ pre-alert historical recurrence cutoff (prevents current-event self-counting).
  - Zero target proxies: Excludes all raw metadata label columns.
  - Zero raw coordinates in neural tensors: Eliminates spatial memorization artifacts.
- **Registry-Free Recurrence Learning:** Distinguishes acute vs persistent anomalies dynamically from pre-alert satellite history without depending on test-derived persistent manifests.
- **Sub-10ms CPU Latency & 130+ events/sec:** Designed for edge or cloud microservice deployment on standard CPUs.
- **Complete Operational Stack:** Includes FastAPI REST backend, SQLite / PostGIS geospatial storage, Leaflet.js interactive map dashboard, and Docker containerization.

---

## 📚 Release Documentation

- 🚀 [**QUICKSTART.md**](QUICKSTART.md) — 5-minute setup, demonstration run, and local server launch.
- 🧠 [**MODEL_CARD.md**](MODEL_CARD.md) — Detailed specifications, training methodology, frozen weights hash, and benchmark tables.
- 🏗️ [**ARCHITECTURE.md**](ARCHITECTURE.md) — Architectural layers from NASA FIRMS ingestion to GIS visualization.
- 🔌 [**API.md**](API.md) — REST API reference, request/response schemas, status codes, and code examples.
- ⚠️ [**LIMITATIONS.md**](LIMITATIONS.md) — Scientific scope, upstream sensor reliance, and operational boundaries.

---

## 📦 Directory Structure

```
DATA PREPROCESSING/
├── release/                        # Official release documentation package
│   ├── README.md                   # This document
│   ├── QUICKSTART.md               # Quickstart guide
│   ├── MODEL_CARD.md               # Model specifications and card
│   ├── ARCHITECTURE.md             # System architecture guide
│   ├── API.md                      # REST API documentation
│   └── LIMITATIONS.md              # Limitations & operational boundaries
├── models/
│   └── stage8_36/                  # FROZEN MODEL ARTIFACTS (DO NOT MODIFY)
│       ├── final_neural_model.pt   # PyTorch checkpoint (SHA-256: 5bdbfbd5...)
│       ├── feature_schema.json     # 41-feature causal schema
│       ├── preprocessing_scalers.json # Frozen standardization parameters
│       └── model_config.json       # Hyperparameters & layer dimensions
├── src/
│   ├── stage8_37/                  # Operational backend microservice
│   │   ├── app.py                  # FastAPI server entrypoint
│   │   ├── api/                    # REST routes & endpoints
│   │   ├── database/               # Database manager (SQLite & PostGIS)
│   │   ├── events/                 # Spatiotemporal event clustering
│   │   ├── explanation/            # Grounded explanation engine
│   │   ├── inference/              # Causal feature builder & neural predictor
│   │   └── ingestion/              # NASA FIRMS CSV / API loaders & validators
│   └── stage8_38/                  # QA, audit, and benchmark engines
│       ├── api_qa.py               # API route verification test
│       ├── audit_explanations.py   # Explanation calibration & grounding auditor
│       ├── audit_repository.py     # Codebase provenance and health audit
│       ├── run_real_firms_demo.py  # Real NASA FIRMS batch execution engine
│       ├── runtime_benchmark.py    # Latency, throughput, and memory profiler
│       └── test_robustness.py      # Malformed & invalid input stress tester
├── frontend/                       # Interactive Web GIS Dashboard
│   ├── index.html                  # Dashboard UI layout
│   ├── app.js                      # Leaflet GIS visualization logic
│   └── styles.css                  # Modern responsive stylesheet
├── docker/                         # Containerization assets
│   ├── Dockerfile                  # Python 3.10-slim PyTorch CPU container
│   └── docker-compose.yml          # FastAPI + PostGIS multi-service stack
└── tests/                          # Automated regression & integration test suite
    ├── test_stage8_38.py           # Comprehensive release validation suite
    ├── test_stage8_37.py           # Operational pipeline integration tests
    └── test_stage8_36.py           # Scientific freeze & invariance tests
```

---

## 🛡️ License & Disclaimers

The DS08 system is intended for research, wildfire attribution, environmental compliance, and emergency management decision-support. Satellite thermal anomalies provide indicative evidence and should be coupled with ground-truth verification and official dispatch protocols.
