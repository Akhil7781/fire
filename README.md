# AI-Based Classification of Satellite Thermal Anomalies (Industrial Fires)

A research-grade framework for detecting and classifying satellite thermal anomalies, with a focus on discriminating **industrial fires** from other thermal phenomena using NOAA-20 VIIRS data.

---

## 1. Dataset Overview

- **Source**: NASA FIRMS (Fire Information for Resource Management System)
- **Sensor**: VIIRS (Visible Infrared Imaging Radiometer Suite)
- **Platform**: NOAA-20 (JPSS-1)
- **Processing Stream**: Standard Processing (Science Quality)
- **Geographic Domain**: India Region
- **Temporal Span**: 2025-01-01 to 2025-12-31 (Full Year 2025)
- **Primary Corpus**: 73 CSV files, **1,024,996 India-region NOAA-20 SP detections for 2025**
- **Context Burn-In Corpus**: 2024-10-01 to 2024-12-31 India-region NOAA-20 SP (under `data/raw_context/`, context-only, never evaluated)
- **Features**: 16 original FIRMS attributes
- **Data Quality**: 0 missing values, 0 duplicate rows

---

## 2. Directory Structure

```text
.
├── .env.example              # Environment configuration template (never commit real .env)
├── .gitignore                # Rules ignoring .env, raw data, checkpoints, and logs
├── PROJECT_SPEC.md           # Research specification and methodology placeholders
├── README.md                 # Project overview and setup instructions
├── requirements.txt          # Python project dependencies (uninstalled initially)
├── configs/
│   └── config.yaml           # Base parameters, paths, and model settings
├── data/
│   ├── raw/                  # Destination for 73 FIRMS VIIRS CSV files (untracked)
│   ├── raw_context/          # Destination for 2024 Q4 India context burn-in CSVs (untracked)
│   ├── interim/              # Filtered, clustered, or intermediate representations (untracked)
│   └── processed/            # Final tensors, features, and train/val/test splits (untracked)
├── notebooks/                # Exploratory research notebooks (untracked outputs)
├── checkpoints/              # Model weights and training checkpoints (untracked)
├── logs/                     # Experiment logs and metrics (untracked)
├── scripts/
│   └── verify_environment.py # Non-destructive setup & security verification test
└── src/
    ├── __init__.py           # Root package initializer
    ├── data/                 # Data loading and pipeline stubs
    │   ├── __init__.py
    │   ├── dataset.py        # Dataset class placeholder
    │   ├── preprocessing.py  # Cleaning and scaling placeholder
    │   ├── spatial.py        # Spatial indexing & clustering placeholder
    │   └── temporal.py       # Time-series & recurrence placeholder
    ├── models/               # Model architecture stubs
    │   ├── __init__.py
    │   ├── tcn.py            # Temporal Convolutional Network placeholder
    │   ├── deep_sad.py       # Deep Semi-Supervised Anomaly Detection placeholder
    │   ├── yolov8.py         # YOLOv8 spatial thermal anomaly placeholder
    │   └── fusion.py         # Spatio-temporal feature fusion placeholder
    ├── training/             # Training routines and loss functions
    │   └── __init__.py
    ├── evaluation/           # Evaluation metrics and validation
    │   └── __init__.py
    └── utils/                # Configuration and secure credential helpers
        ├── __init__.py
        └── config.py         # Safe config loader with masked key protection
```

---

## 3. Security Policy & Environment Configuration

### NASA FIRMS MAP_KEY Security Rules
- **NEVER** hard-code the `FIRMS_MAP_KEY` into code.
- **NEVER** print, log, or echo the key value.
- **NEVER** commit `.env` or any credential files to Git.

### Setup Instructions
1. Copy the template to `.env`:
   ```bash
   cp .env.example .env
   # or on Windows PowerShell:
   Copy-Item .env.example .env
   ```
2. Open `.env` and set your key:
   ```env
   FIRMS_MAP_KEY=your_actual_key_here
   RAW_DATA_DIR=data/raw
   RAW_CONTEXT_DIR=data/raw_context
   ```
3. Place the 73 FIRMS CSV files for 2025 in `data/raw/` and the 2024 Q4 India context burn-in files in `data/raw_context/`.

---

## 4. Verification

Run the non-destructive environment verification script to check your setup:

```bash
python scripts/verify_environment.py
```

This script safely verifies:
- Python version and platform architecture
- Input data directory presence and CSV file counts (without reading/loading rows)
- FIRMS MAP_KEY presence in `.env`/environment (without printing the secret)
- Dependency status against `requirements.txt`

---

## 5. Specification & Methodology

Refer to [PROJECT_SPEC.md](file:///D:/DATA%20PREPROCESSING/PROJECT_SPEC.md) for architectural and scientific details regarding:
- 1,024,996 India-region NOAA-20 SP detections for 2025
- Causal historical features (6h and 24h within 2 km local causal context radius)
- Contemporaneous snapshot features (within $\pm 15$ min, explicitly non-causal)
- Temporal Convolutional Networks (TCN 90-day sequence modeling)
- Deep Semi-Supervised Anomaly Detection (Deep SAD)
- Leakage-free train/validation/test splitting (spatial blocking + temporal holdout)
- State isolation (fitting scalers strictly on TRAIN)

---

## 6. Label Construction Pipeline (Phase 2)

The label construction pipeline derives ground truth exclusively from independent reference datasets without using FIRMS predictive attributes or sensor heuristics (`type`).

### Target Classes
- `0`: **UNLABELED** (Explicit baseline for Deep SAD semi-supervised anomaly detection)
- `1`: **Industrial Fire** (Statutory corporate filings, SPCB/NGT orders, corroborated news incidents)
- `2`: **Forest Fire** (Forest Survey of India FAST 3.0 LFF perimeters, state forest reports)
- `3`: **Agricultural Fire** (ICAR-IARI CREAMS daily bulletins, PRSC/HARSAC monitoring logs)
- `4`: **Other Thermal Source** (Gas flares, brick kilns, Barren Island volcano, coal fires, power stations)

### Reproducing Label Construction

1. **Run Unit and Regression Tests**:
   ```bash
   python tests/test_labeling_pipeline.py
   ```
2. **Run Empirical Parameter Sensitivity Sweep** (TRAIN partition only):
   ```bash
   python scripts/calibrate_matching_parameters.py
   ```
3. **Execute Full-Scale Label Construction**:
   ```bash
   python scripts/build_labels.py
   ```
4. **Execute 18-Point Quality Audit**:
   ```bash
   python scripts/audit_labels.py
   ```

Output tables and audit dossiers are stored in:
- `data/processed/labels/master_labels_2025.parquet`
- `data/labeling/audits/label_audit_report.json`
- `data/labeling/audits/label_audit_report.md`
- `data/labeling/audits/label_pipeline_summary.json`
- `data/labeling/audits/parameter_sensitivity_sweep.md`
