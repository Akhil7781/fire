"""Stage 8.37 Production Operational Cutoff & Causality Test.

Verifies the strict operational causality invariant:
Given an event with alert timestamp t0:
Injecting future observations at:
- t0 + 1 hour
- t0 + 6 hours
- t0 + 24 hours
- t0 + 7 days
- t0 + 30 days
MUST NOT alter:
- The predicted class
- The predicted probabilities
- The extracted causal feature values
- The historical recurrence statistics
"""

import copy
import logging
import sys
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.stage8_37.inference.schemas import ThermalEventInput, FirmsDetectionRecord
from src.stage8_37.inference.feature_builder import CausalFeatureBuilder
from src.stage8_37.inference.predictor import OperationalPredictor

logger = logging.getLogger(__name__)

def run_production_causality_test() -> dict:
    """Injects synthetic future observations and asserts complete feature and prediction invariance."""
    builder = CausalFeatureBuilder()
    predictor = OperationalPredictor()

    t0_str = "2026-05-10T12:00:00Z"
    t0 = pd.to_datetime(t0_str)

    # Base alert event with 2 detections at/before t0
    base_detections = [
        FirmsDetectionRecord(
            detection_id="DET_BASE_01",
            latitude=21.25,
            longitude=81.63,
            acq_date="2026-05-10",
            acq_time="1130",
            acq_datetime_utc="2026-05-10T11:30:00Z",
            bright_ti4=345.2,
            bright_ti5=298.4,
            frp=28.5,
            confidence="high",
            daynight="D"
        ),
        FirmsDetectionRecord(
            detection_id="DET_BASE_02",
            latitude=21.26,
            longitude=81.64,
            acq_date="2026-05-10",
            acq_time="1200",
            acq_datetime_utc="2026-05-10T12:00:00Z",
            bright_ti4=348.0,
            bright_ti5=300.1,
            frp=32.0,
            confidence="high",
            daynight="D"
        )
    ]

    base_event = ThermalEventInput(
        event_id="EVT_CAUSAL_TEST_BASE",
        centroid_lat=21.255,
        centroid_lon=81.635,
        event_start_time=t0_str,
        event_detection_count=2,
        detections=base_detections
    )

    # 1. Baseline feature extraction & prediction
    base_feats, base_meta = builder.build_features_for_event(base_event)
    base_pred = predictor.predict_event(base_event)

    # 2. Synthetic future injections
    future_offsets = [
        ("1h", pd.Timedelta(hours=1)),
        ("6h", pd.Timedelta(hours=6)),
        ("24h", pd.Timedelta(hours=24)),
        ("7d", pd.Timedelta(days=7)),
        ("30d", pd.Timedelta(days=30))
    ]

    injected_detections = copy.deepcopy(base_detections)
    test_results = []

    for name, offset in future_offsets:
        fut_dt = t0 + offset
        fut_det = FirmsDetectionRecord(
            detection_id=f"DET_FUT_{name}",
            latitude=21.255,
            longitude=81.635,
            acq_date=str(fut_dt.date()),
            acq_time=fut_dt.strftime("%H%M"),
            acq_datetime_utc=fut_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            bright_ti4=390.0,  # Extreme future reading
            bright_ti5=310.0,
            frp=150.0,         # Massive future FRP
            confidence="high",
            daynight="N"
        )
        injected_detections.append(fut_det)

        injected_event = ThermalEventInput(
            event_id=f"EVT_CAUSAL_TEST_{name}",
            centroid_lat=21.255,
            centroid_lon=81.635,
            event_start_time=t0_str,  # Alert time remains t0
            event_detection_count=len(injected_detections),
            detections=copy.deepcopy(injected_detections)
        )

        inj_feats, inj_meta = builder.build_features_for_event(injected_event)
        inj_pred = predictor.predict_event(injected_event)

        # Assertions
        # Prediction class must match exactly
        assert inj_pred.predicted_class == base_pred.predicted_class, (
            f"Class mismatch after future injection at {name}! Base: {base_pred.predicted_class}, Inj: {inj_pred.predicted_class}"
        )
        # Probabilities must match within floating precision
        np.testing.assert_allclose(
            [inj_pred.probability_industrial, inj_pred.probability_forest, inj_pred.probability_agricultural, inj_pred.probability_persistent],
            [base_pred.probability_industrial, base_pred.probability_forest, base_pred.probability_agricultural, base_pred.probability_persistent],
            atol=1e-5,
            err_msg=f"Probability shift detected after future injection at {name}!"
        )
        # Thermal features must match
        for grp in ["thermal", "industrial", "ecoregion", "historical"]:
            np.testing.assert_allclose(
                inj_feats[grp], base_feats[grp], atol=1e-5,
                err_msg=f"Feature group '{grp}' mutated after future injection at {name}!"
            )

        test_results.append({
            "future_injection": name,
            "future_timestamp": str(fut_dt),
            "status": "PASS",
            "prediction_invariant": True,
            "probabilities_invariant": True,
            "features_invariant": True
        })

    logger.info("All 5 operational future-injection tests PASSED.")
    return {
        "status": "PASS",
        "injections_tested": len(future_offsets),
        "results": test_results
    }

if __name__ == "__main__":
    res = run_production_causality_test()
    print("Production Causality Invariant Test Result:")
    print(res)
