"""Stage 8.37 Production Inference Schemas.

Pydantic schemas for data validation, API input/output, and feature representation.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

CLASS_NAMES = [
    "Industrial Fire",
    "Forest Fire",
    "Agricultural Fire",
    "Other / Persistent Thermal Source"
]

CLASS_SHORT_NAMES = ["Industrial", "Forest", "Agricultural", "Persistent"]

class FirmsDetectionRecord(BaseModel):
    """Normalized NASA FIRMS detection point."""
    detection_id: Optional[str] = None
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    acq_date: str = Field(..., description="Acquisition date YYYY-MM-DD")
    acq_time: str = Field(..., description="Acquisition time HHMM")
    acq_datetime_utc: str = Field(..., description="ISO 8601 acquisition timestamp in UTC")
    bright_ti4: float = Field(..., gt=0.0, description="VIIRS/MODIS channel 4 brightness temperature (K)")
    bright_ti5: float = Field(..., gt=0.0, description="VIIRS/MODIS channel 5 brightness temperature (K)")
    frp: float = Field(..., ge=0.0, description="Fire Radiative Power (MW)")
    confidence: str = Field(default="nominal", description="Detection confidence (nominal/high/low/numeric)")
    satellite: str = Field(default="N", description="Satellite platform (N=Suomi NPP, 20=NOAA-20, 1=Aqua, 2=Terra)")
    sensor: str = Field(default="VIIRS", description="Sensor instrument (VIIRS, MODIS)")
    daynight: str = Field(default="D", description="D=Day, N=Night")

class ThermalEventInput(BaseModel):
    """Spatiotemporal cluster of FIRMS thermal detections representing an event."""
    event_id: str
    centroid_lat: float = Field(..., ge=-90.0, le=90.0)
    centroid_lon: float = Field(..., ge=-180.0, le=180.0)
    event_start_time: str = Field(..., description="Timestamp of first detection (t0) in UTC")
    event_detection_count: int = Field(default=1, ge=1)
    detections: List[FirmsDetectionRecord] = Field(default_factory=list)

class IndustrialContext(BaseModel):
    """Industrial geographic proximity and facility baseline."""
    nearest_facility_name: Optional[str] = None
    nearest_facility_distance_km: float
    within_1km_fac: float
    within_5km_fac: float
    facility_baseline_frp: float
    facility_context_available: bool = True

class EcoregionContext(BaseModel):
    """Land cover and ecological biome indicators."""
    forest_biome_score: float
    agri_heartland_score: float
    s2_available: float = 0.0
    ecoregion_context_available: bool = True

class PersistenceEvidence(BaseModel):
    """Recurrence analysis from pre-alert historical FIRMS archive."""
    level: str = Field(..., description="LOW, MODERATE, or STRONG")
    historical_detection_count: float
    historical_active_days: float
    historical_active_months: float
    time_since_previous_detection_days: float
    historical_mean_frp: float
    historical_night_ratio: float
    distinct_calendar_months: float

class ExplanationRecord(BaseModel):
    """Feature-grounded structured explanation."""
    prediction_summary: str
    thermal_evidence: List[str]
    recurrence_evidence: List[str]
    ecological_evidence: List[str]
    industrial_evidence: List[str]

class PredictionOutput(BaseModel):
    """Official 4-class attribution prediction response."""
    event_id: str
    centroid_lat: float
    centroid_lon: float
    alert_time: str
    predicted_class: str
    class_id: int
    confidence: float
    probability_industrial: float
    probability_forest: float
    probability_agricultural: float
    probability_persistent: float
    persistence_evidence: PersistenceEvidence
    industrial_context: IndustrialContext
    ecoregion_context: EcoregionContext
    explanation: ExplanationRecord
    model_version: str = "8.36_final"
    model_checkpoint_hash: str
    feature_schema_version: str = "8.35_expanded"
    prediction_timestamp: str

class BatchPredictionResponse(BaseModel):
    """Batch prediction results."""
    total_events: int
    predictions: List[PredictionOutput]
    processing_time_ms: float
