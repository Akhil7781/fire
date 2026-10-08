"""Stage 8.37 FastAPI Routes.

REST API routes for prediction, event querying, history, statistics, and GeoJSON export.
"""

from datetime import datetime, timezone
import io
import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
import pandas as pd

from src.stage8_37.inference.schemas import (
    ThermalEventInput,
    PredictionOutput,
    BatchPredictionResponse,
    FirmsDetectionRecord
)
from src.stage8_37.inference.predictor import get_predictor
from src.stage8_37.inference.model_loader import get_model_metadata, EXPECTED_CHECKPOINT_HASH
from src.stage8_37.database.db import get_db
from src.stage8_37.ingestion.firms_loader import FirmsLoader
from src.stage8_37.events.event_builder import EventBuilder

router = APIRouter()

@router.get("/health")
def health_check():
    """Returns system status, active model version, and verified checkpoint hash."""
    meta = get_model_metadata()
    return {
        "status": "HEALTHY",
        "service": "DS08 Operational Attribution API",
        "model_version": meta["model_version"],
        "architecture": meta["architecture_name"],
        "checkpoint_sha256": EXPECTED_CHECKPOINT_HASH,
        "pure_deep_learning": meta["pure_deep_learning"],
        "total_tabular_features": meta["total_tabular_features"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.post("/predict", response_model=PredictionOutput)
def predict_single_event(event: ThermalEventInput):
    """Performs 4-class attribution on an input thermal event."""
    try:
        predictor = get_predictor()
        db = get_db()
        # Save event to database
        db.save_event(event)
        # Run inference
        prediction = predictor.predict_event(event)
        # Save prediction
        db.save_prediction(prediction)
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")

@router.post("/predict/batch", response_model=BatchPredictionResponse)
def predict_batch_events(events: List[ThermalEventInput]):
    """Performs batch attribution on multiple thermal events."""
    t0 = time.time()
    predictor = get_predictor()
    db = get_db()
    predictions = []
    for ev in events:
        db.save_event(ev)
        p = predictor.predict_event(ev)
        db.save_prediction(p)
        predictions.append(p)

    elapsed_ms = (time.time() - t0) * 1000.0
    return BatchPredictionResponse(
        total_events=len(events),
        predictions=predictions,
        processing_time_ms=round(elapsed_ms, 2)
    )

@router.get("/events")
def list_events(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    class_filter: Optional[str] = None,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0)
):
    """Lists processed events with predictions and filtering."""
    db = get_db()
    return db.list_events(limit=limit, offset=offset, class_filter=class_filter, min_confidence=min_confidence)

def _ensure_persistent_demo_scenario(db):
    """Ensures the non-test persistent demonstration scenario event is present in the operational database."""
    pers_ev = db.get_event("EVT_825_PER_PER_SRC_05")
    if not pers_ev:
        det = FirmsDetectionRecord(
            latitude=21.12501,
            longitude=72.69479,
            acq_date="2025-03-08",
            acq_time="0800",
            acq_datetime_utc="2025-03-08T08:00:00Z",
            bright_ti4=340.5,
            bright_ti5=298.2,
            frp=28.4,
            confidence="nominal",
            satellite="N",
            sensor="VIIRS",
            daynight="D"
        )
        evt_input = ThermalEventInput(
            event_id="EVT_825_PER_PER_SRC_05",
            centroid_lat=21.12501,
            centroid_lon=72.69479,
            event_start_time="2025-03-08T08:00:00Z",
            event_detection_count=1,
            detections=[det]
        )
        db.save_event(evt_input)
        predictor = get_predictor()
        pred = predictor.predict_event(evt_input)
        db.save_prediction(pred)

@router.get("/events/{event_id}")
def get_event_detail(event_id: str):
    """Retrieves full details, predictions, and detections for an event."""
    db = get_db()
    ev = db.get_event(event_id)
    if not ev and event_id == "EVT_825_PER_PER_SRC_05":
        _ensure_persistent_demo_scenario(db)
        ev = db.get_event(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found.")
    return ev

@router.get("/events/{event_id}/explanation")
def get_event_explanation(event_id: str):
    """Retrieves feature-grounded attribution explanation for an event."""
    db = get_db()
    ev = db.get_event(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found.")
    return ev.get("explanation", {"message": "Explanation unavailable"})

@router.get("/events/{event_id}/history")
def get_event_history(event_id: str):
    """Retrieves chronological detection timeline for an event."""
    db = get_db()
    ev = db.get_event(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found.")
    return {
        "event_id": event_id,
        "detection_count": ev.get("detection_count", 0),
        "detections": ev.get("detections", [])
    }

@router.get("/statistics")
def get_operational_statistics():
    """Returns database summary statistics and class distribution breakdown."""
    db = get_db()
    return db.get_statistics()

@router.get("/api/geojson")
def get_map_geojson(
    class_filter: Optional[str] = None,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    since: Optional[str] = None
):
    """Returns RFC 7946 GeoJSON FeatureCollection for GIS map rendering."""
    db = get_db()
    return db.get_geojson(class_filter=class_filter, min_confidence=min_confidence, since=since)

@router.post("/ingest/csv")
async def ingest_csv_file(file: UploadFile = File(...)):
    """Uploads a NASA FIRMS CSV, clusters events, infers classes, and stores them in DB."""
    content = await file.read()
    loader = FirmsLoader()
    dets = loader.load_from_csv(io.BytesIO(content))
    if not dets:
        raise HTTPException(status_code=400, detail="No valid detections found in uploaded CSV.")

    builder = EventBuilder()
    events = builder.build_events(dets)

    predictor = get_predictor()
    db = get_db()
    results = []
    for ev in events:
        db.save_event(ev)
        p = predictor.predict_event(ev)
        db.save_prediction(p)
        results.append(p)

    return {
        "detections_ingested": len(dets),
        "events_created": len(events),
        "predictions": [r.model_dump() for r in results]
    }

@router.get("/model/benchmark")
def get_model_benchmark():
    """Returns official frozen 2026 benchmark metrics, confusion matrix, and model metadata."""
    return {
        "status": "FROZEN_BENCHMARK",
        "official_benchmark": {
            "accuracy": 0.7857,
            "accuracy_pct": "78.57%",
            "macro_f1": 0.8021,
            "balanced_accuracy": 0.8167,
            "balanced_accuracy_pct": "81.67%",
            "test_events": 28,
            "correct_predictions": 22
        },
        "per_class": [
            {"class_name": "Industrial Fire", "precision": 1.000, "recall": 1.000, "f1": 1.000, "support": 6, "correct": 6},
            {"class_name": "Forest Fire", "precision": 0.833, "recall": 0.833, "f1": 0.833, "support": 6, "correct": 5},
            {"class_name": "Agricultural Fire", "precision": 0.500, "recall": 0.833, "f1": 0.625, "support": 6, "correct": 5},
            {"class_name": "Persistent / Other", "precision": 1.000, "recall": 0.600, "f1": 0.750, "support": 10, "correct": 6}
        ],
        "confusion_matrix": {
            "classes": ["Industrial", "Forest", "Agricultural", "Persistent"],
            "matrix": [
                [6, 0, 0, 0],
                [0, 5, 1, 0],
                [0, 1, 5, 0],
                [0, 0, 4, 6]
            ],
            "labels": [
                "6/6 Industrial correct",
                "5/6 Forest correct",
                "5/6 Agricultural correct",
                "6/10 Persistent correct"
            ]
        },
        "development_validation": {
            "spatial_cv": {
                "label": "Spatial 4-Fold CV",
                "accuracy": 0.8000,
                "accuracy_pct": "80.00%",
                "macro_f1": 0.7689
            },
            "temporal_2025": {
                "label": "Temporal 2025 Validation",
                "accuracy": 0.8500,
                "accuracy_pct": "85.00%",
                "macro_f1": 0.8155
            },
            "independent_2026": {
                "label": "Independent Frozen 2026 Test",
                "accuracy": 0.7857,
                "accuracy_pct": "78.57%",
                "macro_f1": 0.8021,
                "balanced_accuracy": 0.8167,
                "balanced_accuracy_pct": "81.67%"
            }
        },
        "model_information": {
            "model_name": "Architecture1_StaticMLP",
            "framework": "PyTorch",
            "parameters": "3,244",
            "features_total": 41,
            "feature_groups": {
                "Thermal Dynamics": 14,
                "Industrial Context": 6,
                "Land Cover / Ecoregion": 3,
                "Historical Recurrence": 18
            },
            "raw_coordinates": "NOT USED",
            "persistent_registry": "NOT USED",
            "historical_recurrence": "USED",
            "checkpoint_sha256": EXPECTED_CHECKPOINT_HASH
        },
        "reviewer_panels": {
            "what_does_it_do": {
                "input": "NASA FIRMS thermal anomaly observations",
                "process": "The system converts detections into thermal events, extracts current thermal, historical recurrence, industrial-context and ecological features, and passes them through a frozen deep-learning model.",
                "output": "Industrial Fire, Forest Fire, Agricultural Fire, Persistent / Other Thermal Source",
                "flowchart": [
                    "NASA FIRMS",
                    "    ↓",
                    "Thermal anomaly",
                    "    ↓",
                    "Thermal event construction",
                    "    ↓",
                    "41 causal features",
                    "    ↓",
                    "Static MLP",
                    "    ↓",
                    "Four-class source attribution",
                    "    ↓",
                    "GIS + evidence + explanation"
                ],
                "core_statement": "NASA FIRMS detects the thermal anomaly. Our model performs source-type attribution."
            },
            "what_is_different": {
                "nasa_firms": "Thermal anomaly detected",
                "our_system": "Likely source category + confidence + class probabilities + historical recurrence + industrial context + ecological context + GIS visualization",
                "key_distinction": "DETECTION ≠ SOURCE ATTRIBUTION"
            },
            "how_well_does_it_work": [
                "On the frozen independent 2026 benchmark, the final model achieved 78.57% accuracy, 0.8021 Macro-F1 and 81.67% balanced accuracy.",
                "Industrial Fire attribution achieved 100% precision, 100% recall and F1 = 1.00.",
                "Forest Fire recall was 83.3%.",
                "Agricultural Fire recall was 83.3%.",
                "Persistent-source precision was 100%, with 60% recall."
            ],
            "why_is_this_useful": {
                "standard_alert": "Thermal anomaly detected",
                "system_output": "Thermal anomaly detected → likely source category → confidence → historical recurrence → industrial context → ecological context → GIS visualization",
                "operational_benefit": "Enables prioritized emergency response, distinguishing routine biomass clearing from critical industrial fires and persistent gas flaring."
            },
            "why_not_100": [
                "1. Agricultural and forest thermal signatures overlap in transitional vegetation.",
                "2. Sparse persistent sources may resemble seasonal agricultural burning.",
                "3. NASA FIRMS provides thermal anomalies rather than definitive ground-truth source labels.",
                "4. The official independent benchmark contains exactly 28 events (1 misclassification = 3.57%)."
            ],
            "common_reviewer_questions": [
                {
                    "id": "q1",
                    "button_text": "WHAT IS THE INPUT?",
                    "question": "What is the input?",
                    "answer": "NASA FIRMS VIIRS 375m and MODIS 1km satellite thermal anomaly observations, clustered into discrete physical events (Δr ≤ 3.0 km, Δt ≤ 24h)."
                },
                {
                    "id": "q2",
                    "button_text": "WHAT IS THE OUTPUT?",
                    "question": "What is the output?",
                    "answer": "Probabilistic attribution across four mutually exclusive classes: Industrial Fire, Forest Fire, Agricultural Fire, and Other / Persistent Thermal Source, with calibrated confidence and feature evidence."
                },
                {
                    "id": "q3",
                    "button_text": "WHY FIRMS?",
                    "question": "Why FIRMS?",
                    "answer": "NASA FIRMS provides continuous, operational, near-real-time satellite coverage across the entire Indian landmass with low latency and global sensor calibration."
                },
                {
                    "id": "q4",
                    "button_text": "WHY FOUR CLASSES?",
                    "question": "Why four classes?",
                    "answer": "Industrial, Forest, Agricultural, and Persistent / Other represent the four distinct operational intervention profiles required for emergency dispatch and environmental compliance."
                },
                {
                    "id": "q5",
                    "button_text": "WHY STATIC MLP?",
                    "question": "Why Static MLP?",
                    "answer": "Architecture1_StaticMLP (Pure PyTorch, 3,244 parameters) achieved superior spatial generalization (80.00% Spatial CV, 85.00% Temporal 2025, 78.57% Frozen 2026) while eliminating temporal overfitting and latency overhead."
                },
                {
                    "id": "q6",
                    "button_text": "WHY NOT GRU?",
                    "question": "Why not GRU?",
                    "answer": "Forensic evaluations in Stages 8.28–8.31 demonstrated that sequential GRUs suffered from temporal shortcut overfitting due to irregular satellite revisit cadences, adding 10x parameters without improving generalization."
                },
                {
                    "id": "q7",
                    "button_text": "WHY NOT TCN?",
                    "question": "Why not TCN?",
                    "answer": "TCN architectures proved overparameterized for sparse orbital soundings and exhibited temporal leakage on non-uniform overpass sequences, whereas engineered causal recurrence features provided robust tabular signals."
                },
                {
                    "id": "q8",
                    "button_text": "HOW IS PERSISTENCE FOUND?",
                    "question": "How is persistence found?",
                    "answer": "Through 18 causal historical recurrence features computed strictly from pre-alert satellite soundings (t <= t0 - 7 days), tracking multi-month recurrence density, active day counts, and observation frequencies without any lookahead or static registries."
                },
                {
                    "id": "q9",
                    "button_text": "WHAT IS THE FINAL ACCURACY?",
                    "question": "What is the final accuracy?",
                    "answer": "78.57% accuracy (22/28 events correct), 0.8021 Macro-F1, and 81.67% balanced accuracy on the strictly frozen, independent 2026 test benchmark."
                },
                {
                    "id": "q10",
                    "button_text": "WHY IS ACCURACY NOT 100%?",
                    "question": "Why is accuracy not 100%?",
                    "answer": "Biomass combustion exhibits spectral overlap between forest and agricultural fuels, sparse persistent sources have irregular historical observations, FIRMS provides thermal soundings rather than definitive ground-truth labels, and the test cohort has N=28 events (1 error = 3.57%)."
                },
                {
                    "id": "q11",
                    "button_text": "WHAT IS THE MAIN LIMITATION?",
                    "question": "What is the main limitation?",
                    "answer": "Persistent-source recall is 60.0% (due to sparse historical revisits) and Agricultural Fire precision is 50.0% (overlapping with transitional vegetation fires)."
                },
                {
                    "id": "q12",
                    "button_text": "WHAT DOES THE SYSTEM DO THAT FIRMS DOES NOT?",
                    "question": "What does the system do that FIRMS does not?",
                    "answer": "FIRMS only detects that a thermal anomaly exists; our system attributes the probable source category, quantifies uncertainty, links industrial and ecological geospatial context, checks historical recurrence, and generates human-auditable evidence."
                }
            ]
        }
    }

DEMO_SCENARIOS = [
    {
        "scenario_id": "scenario_industrial",
        "target_class": "Industrial Fire",
        "class_name": "Industrial Fire",
        "event_id": "EVT_20250627_05B3B989",
        "date": "2025-06-27",
        "timestamp": "2025-06-27T20:15:00Z",
        "region": "Jamnagar, Gujarat",
        "centroid_lat": 22.31722,
        "centroid_lon": 69.85356,
        "frp": 2.72,
        "bright_ti4": 300.61,
        "bright_ti5": 283.76,
        "daynight": "Night (N)",
        "detection_count": 1,
        "reference_label": "Industrial Facility Proximity Thermal Anomaly",
        "reference_disclaimer": "DEMO ONLY — NOT BENCHMARK EVIDENCE",
        "scenario_tag": "Industrial Fire demonstration example",
        "model_output": "Industrial Fire",
        "model_uncertainty": True,
        "uncertainty_badge": "MODEL UNCERTAINTY: Top-2 classes within 9.1% margin",
        "prediction": {
            "predicted_class": "Industrial Fire",
            "confidence": 0.3594,
            "probabilities": {
                "industrial": 0.3594,
                "forest": 0.2682,
                "agricultural": 0.2195,
                "persistent": 0.1529
            }
        },
        "evidence": {
            "thermal": "Single nocturnal observation (FRP: 2.72 MW, TI4: 300.61 K, TI5: 283.76 K).",
            "historical_recurrence": "0 prior alerts within 1.0 km radius (episodic thermal signature).",
            "industrial_context": "Located 4.36 km from RIL Jamnagar Refinery Complex (SEZ).",
            "ecological_context": "Urban/industrial zone with zero forest biome or agricultural heartland indicator."
        },
        "explanation": "Model attributes event to 'Industrial Fire' with 35.9% confidence. Strong industrial facility proximity (4.36 km to RIL Jamnagar Refinery Complex) and nocturnal timing support industrial attribution."
    },
    {
        "scenario_id": "scenario_forest",
        "target_class": "Forest Fire",
        "class_name": "Forest Fire",
        "event_id": "EVT_20250625_70A2651C",
        "date": "2025-06-25",
        "timestamp": "2025-06-25T06:45:00Z",
        "region": "Northern Himalayan Forest Biome",
        "centroid_lat": 29.27494,
        "centroid_lon": 88.90346,
        "frp": 4.43,
        "bright_ti4": 348.93,
        "bright_ti5": 308.95,
        "daynight": "Day (D)",
        "detection_count": 4,
        "reference_label": "Forested Biome Active Fire Cluster",
        "reference_disclaimer": "DEMO ONLY — NOT BENCHMARK EVIDENCE",
        "scenario_tag": "Forest Fire demonstration example",
        "model_output": "Forest Fire",
        "model_uncertainty": True,
        "uncertainty_badge": "MODEL UNCERTAINTY: Top-2 classes within 9.5% margin",
        "prediction": {
            "predicted_class": "Forest Fire",
            "confidence": 0.4277,
            "probabilities": {
                "industrial": 0.1236,
                "forest": 0.4277,
                "agricultural": 0.3323,
                "persistent": 0.1164
            }
        },
        "evidence": {
            "thermal": "Multi-pixel active cluster (4 detections, peak FRP: 4.43 MW, peak TI4: 348.93 K).",
            "historical_recurrence": "0 prior alerts within 1.0 km radius (isolated wildfire episode).",
            "industrial_context": "510.5 km from nearest major industrial facility.",
            "ecological_context": "Forest biome score: 1.0 (dense canopy forest cover)."
        },
        "explanation": "Model attributes event to 'Forest Fire' with 42.8% confidence. High forest biome index (1.0), multi-detection cluster spread, and absence of industrial infrastructure strongly indicate a forest fire."
    },
    {
        "scenario_id": "scenario_agricultural",
        "target_class": "Agricultural Fire",
        "class_name": "Agricultural Fire",
        "event_id": "EVT_20250628_96ABE7CB",
        "date": "2025-06-28",
        "timestamp": "2025-06-28T07:24:00Z",
        "region": "Salem / Tamil Nadu Cropland Plains",
        "centroid_lat": 11.69579,
        "centroid_lon": 78.66312,
        "frp": 8.75,
        "bright_ti4": 348.89,
        "bright_ti5": 292.57,
        "daynight": "Day (D)",
        "detection_count": 2,
        "reference_label": "Cropland / Agricultural Residue Thermal Anomaly",
        "reference_disclaimer": "DEMO ONLY — NOT BENCHMARK EVIDENCE",
        "scenario_tag": "Agricultural Fire demonstration example",
        "model_output": "Agricultural Fire",
        "model_uncertainty": False,
        "uncertainty_badge": None,
        "prediction": {
            "predicted_class": "Agricultural Fire",
            "confidence": 0.5095,
            "probabilities": {
                "industrial": 0.1048,
                "forest": 0.1970,
                "agricultural": 0.5095,
                "persistent": 0.1887
            }
        },
        "evidence": {
            "thermal": "Daytime field burn (2 detections, peak FRP: 8.75 MW, TI4: 348.89 K).",
            "historical_recurrence": "Seasonal agricultural burning rhythm with low annual persistence.",
            "industrial_context": "119.98 km from nearest industrial complex.",
            "ecological_context": "Agricultural heartland score: 1.0 (intensive cultivation zone)."
        },
        "explanation": "Model attributes event to 'Agricultural Fire' with 51.0% confidence. High cropland index (1.0), characteristic diurnal timing, and moderate FRP are consistent with crop residue combustion."
    },
    {
        "scenario_id": "scenario_persistent",
        "target_class": "Other / Persistent Thermal Source",
        "class_name": "Persistent / Other Thermal Source",
        "event_id": "EVT_825_PER_PER_SRC_05",
        "date": "2025-03-08",
        "timestamp": "2025-03-08T08:00:00Z",
        "region": "Hazira / Surat Industrial Belt, Gujarat",
        "centroid_lat": 21.12501,
        "centroid_lon": 72.69479,
        "frp": 28.40,
        "bright_ti4": 340.50,
        "bright_ti5": 298.20,
        "daynight": "Day (D)",
        "detection_count": 1,
        "reference_label": "Historical Recurring Flare / Industrial Thermal Source",
        "reference_disclaimer": "DEMO ONLY — NOT BENCHMARK EVIDENCE",
        "scenario_tag": "Persistent-source demonstration example",
        "model_output": "Other / Persistent Thermal Source",
        "model_uncertainty": True,
        "uncertainty_badge": "MODEL UNCERTAINTY: Top-2 classes within 0.15% margin",
        "historical_summary": {
            "pre_alert_detections": 8,
            "active_days": 4,
            "active_months": 4,
            "recurrence_pattern": "Multimonth recurring anomaly at petrochemical/port flaring zone"
        },
        "prediction": {
            "predicted_class": "Other / Persistent Thermal Source",
            "confidence": 0.3500,
            "probabilities": {
                "industrial": 0.1747,
                "forest": 0.1268,
                "agricultural": 0.3485,
                "persistent": 0.3500
            }
        },
        "evidence": {
            "thermal": "High-intensity anomaly (FRP: 28.40 MW, TI4: 340.50 K, TI5: 298.20 K).",
            "historical_recurrence": "8 historical detections across 4 calendar months at the exact coordinate (recurrence signature).",
            "industrial_context": "19.01 km from Sachin GIDC Industrial Area (Hazira coastal petrochemical flare corridor).",
            "ecological_context": "Coastal industrial zone; forest biome = 0.0, agricultural heartland = 0.0."
        },
        "explanation": "Model attributes event to 'Other / Persistent Thermal Source' with 35.0% confidence. Persistent sources can exhibit repeated thermal activity over time, which provides evidence distinguishing them from acute fires. Recurrent multi-month thermal detections at stationary coordinates supports identification of a stationary flare or persistent process rather than an acute biomass fire."
    }
]

@router.get("/demo/scenarios")
def get_demo_scenarios():
    """Returns the four non-test demonstration scenarios showcasing all four target classes."""
    # Ensure all four events are persisted in the operational database for interactive exploration
    db = get_db()
    _ensure_persistent_demo_scenario(db)

    return {
        "status": "SUCCESS",
        "mode": "FOUR_CLASS_SCENARIOS",
        "disclaimer": "DEMONSTRATION ONLY — NOT BENCHMARK EVIDENCE. All examples are historical non-test records evaluated with frozen production model Architecture1_StaticMLP.",
        "scenarios": DEMO_SCENARIOS
    }

@router.post("/demo/load")
def load_demo_data():
    """Loads the verified non-test 2025 NASA FIRMS dataset for live reviewer demonstration."""
    from pathlib import Path
    project_root = Path("d:/DATA PREPROCESSING")
    demo_file = project_root / "data" / "raw" / "2025" / "VIIRS_NOAA20_SP_2025-06-25_to_2025-06-29.csv"
    demo_preds_csv = project_root / "artifacts" / "stage8_38" / "real_firms_demo_predictions.csv"
    
    if not demo_file.exists():
        raise HTTPException(status_code=404, detail=f"Demo file not found at {demo_file}")
    
    loader = FirmsLoader()
    dets = loader.load_from_csv(demo_file)
    builder = EventBuilder()
    events = builder.build_events(dets)
    
    predictor = get_predictor()
    db = get_db()
    db.clear_database()
    
    predictions = []
    class_counts = {
        "Industrial Fire": 0,
        "Forest Fire": 0,
        "Agricultural Fire": 0,
        "Other / Persistent Thermal Source": 0
    }
    
    for ev in events:
        p = predictor.predict_event(ev)
        predictions.append(p)
        class_counts[p.predicted_class] = class_counts.get(p.predicted_class, 0) + 1
        
    db.save_batch(events, predictions)
        
    return {
        "status": "SUCCESS",
        "mode": "DEMO_MODE",
        "source": "VIIRS_NOAA20_SP_2025-06-25_to_2025-06-29.csv",
        "raw_detections": len(dets),
        "thermal_events": len(events),
        "model_predictions": class_counts
    }

@router.post("/demo/clear")
def clear_demo_data():
    """Clears all events and predictions from the operational database."""
    db = get_db()
    db.clear_database()
    return {"status": "SUCCESS", "message": "Operational database cleared."}

