"""Stage 8.37 Production Predictor Engine.

Connects FeatureBuilder -> Preprocessor -> Frozen Neural Model -> Explainer.
Produces deterministic 4-class attribution predictions.
Maintains structured audit logging in artifacts/stage8_37/audit_log.jsonl.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
import numpy as np
import torch

from src.stage8_37.inference.schemas import (
    ThermalEventInput,
    PredictionOutput,
    CLASS_NAMES
)
from src.stage8_37.inference.model_loader import get_model, get_model_metadata, EXPECTED_CHECKPOINT_HASH
from src.stage8_37.inference.preprocess import preprocess_features
from src.stage8_37.inference.feature_builder import CausalFeatureBuilder
from src.stage8_37.explanation.explainer import generate_explanation

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
AUDIT_LOG_PATH = PROJECT_ROOT / "artifacts" / "stage8_37" / "audit_log.jsonl"

class OperationalPredictor:
    """Production predictor service wrapping the frozen Stage 8.36 model."""

    def __init__(self):
        self.model = get_model()
        self.meta = get_model_metadata()
        self.feature_builder = CausalFeatureBuilder()
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    def _log_audit_entry(self, output: PredictionOutput):
        """Appends structured non-sensitive audit log entry."""
        entry = {
            "event_id": output.event_id,
            "inference_timestamp": output.prediction_timestamp,
            "model_version": output.model_version,
            "feature_schema": output.feature_schema_version,
            "prediction": output.predicted_class,
            "class_id": output.class_id,
            "confidence": output.confidence,
            "probabilities": {
                "industrial": output.probability_industrial,
                "forest": output.probability_forest,
                "agricultural": output.probability_agricultural,
                "persistent": output.probability_persistent
            }
        }
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def predict_event(self, event: ThermalEventInput) -> PredictionOutput:
        """Runs end-to-end causal inference for a single thermal event."""
        # 1. Generate clean causal features
        raw_grouped_arrays, metadata = self.feature_builder.build_features_for_event(event)

        # 2. Preprocess features using frozen training scalers
        batch_tensors = preprocess_features(raw_grouped_arrays)

        # 3. Model forward pass
        with torch.no_grad():
            out = self.model(batch_tensors)
            probs = out["probs"].cpu().numpy()[0]

        pred_id = int(np.argmax(probs))
        confidence = float(np.max(probs))
        pred_class = CLASS_NAMES[pred_id]

        prob_dict = {
            "industrial": float(round(probs[0], 6)),
            "forest": float(round(probs[1], 6)),
            "agricultural": float(round(probs[2], 6)),
            "persistent": float(round(probs[3], 6))
        }

        # 4. Generate structured explanation
        explanation = generate_explanation(
            predicted_class_id=pred_id,
            confidence=confidence,
            probabilities=prob_dict,
            metadata=metadata
        )

        now_utc = datetime.now(timezone.utc).isoformat()

        # 5. Build official PredictionOutput
        prediction = PredictionOutput(
            event_id=event.event_id,
            centroid_lat=event.centroid_lat,
            centroid_lon=event.centroid_lon,
            alert_time=metadata["alert_time"],
            predicted_class=pred_class,
            class_id=pred_id,
            confidence=float(round(confidence, 6)),
            probability_industrial=prob_dict["industrial"],
            probability_forest=prob_dict["forest"],
            probability_agricultural=prob_dict["agricultural"],
            probability_persistent=prob_dict["persistent"],
            persistence_evidence=metadata["persistence_evidence"],
            industrial_context=metadata["industrial_context"],
            ecoregion_context=metadata["ecoregion_context"],
            explanation=explanation,
            model_version=self.meta["model_version"],
            model_checkpoint_hash=EXPECTED_CHECKPOINT_HASH,
            feature_schema_version="8.35_expanded",
            prediction_timestamp=now_utc
        )

        # 6. Audit logging
        self._log_audit_entry(prediction)

        return prediction

    def predict_batch(self, events: List[ThermalEventInput]) -> List[PredictionOutput]:
        """Runs sequential or batched inference for a list of events."""
        return [self.predict_event(ev) for ev in events]

_GLOBAL_PREDICTOR: Optional[OperationalPredictor] = None

def get_predictor() -> OperationalPredictor:
    """Returns singleton instance of OperationalPredictor."""
    global _GLOBAL_PREDICTOR
    if _GLOBAL_PREDICTOR is None:
        _GLOBAL_PREDICTOR = OperationalPredictor()
    return _GLOBAL_PREDICTOR
