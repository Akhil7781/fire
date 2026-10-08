"""Stage 8.37 Production Attribution Explainer.

Generates feature-grounded, non-hallucinated explanations for 4-class attribution.
Uses exact input values from thermal, recurrence, ecological, and industrial feature groups.
Enforces calibrated evidential language ("consistent with", "supports", "contributes to").
"""

from typing import Dict, Any, List
from src.stage8_37.inference.schemas import ExplanationRecord, CLASS_NAMES

def generate_explanation(
    predicted_class_id: int,
    confidence: float,
    probabilities: Dict[str, float],
    metadata: Dict[str, Any]
) -> ExplanationRecord:
    """Generates structured explanation from model inputs."""
    pred_name = CLASS_NAMES[predicted_class_id]
    thermal = metadata["thermal_dict"]
    industrial = metadata["industrial_dict"]
    ecoregion = metadata["ecoregion_dict"]
    historical = metadata["historical_dict"]
    pers_evidence = metadata["persistence_evidence"]
    ind_context = metadata["industrial_context"]

    thermal_ev: List[str] = []
    recurrence_ev: List[str] = []
    ecological_ev: List[str] = []
    industrial_ev: List[str] = []

    # 1. Thermal Evidence
    curr_frp = thermal["current_frp"]
    is_night = thermal["current_is_night"] > 0.5
    ti4 = thermal["current_bright_ti4"]
    delta_ti = thermal["current_delta_ti"]

    if curr_frp >= 30.0:
        thermal_ev.append(f"Elevated fire radiative power ({curr_frp:.1f} MW) indicates intense active combustion.")
    elif curr_frp >= 10.0:
        thermal_ev.append(f"Moderate fire radiative power ({curr_frp:.1f} MW) observed at alert timestamp.")
    else:
        thermal_ev.append(f"Low fire radiative power ({curr_frp:.1f} MW) typical of localized or smoldering thermal source.")

    if is_night:
        thermal_ev.append("Nighttime detection supports continuous combustion process or nocturnal fire activity.")
    else:
        thermal_ev.append("Daytime detection is consistent with diurnal burning schedules.")

    if delta_ti >= 30.0:
        thermal_ev.append(f"High channel brightness differential (\u0394TI = {delta_ti:.1f} K) indicates strong sub-pixel thermal anomaly.")

    # 2. Recurrence / Temporal Evidence
    hist_count = historical["hist_count_full"]
    distinct_months = historical["hist_distinct_calendar_months"]
    days_since = historical["hist_days_since_latest"]

    if pers_evidence.level == "STRONG":
        recurrence_ev.append(
            f"Strong multi-year recurrence ({hist_count:.0f} pre-alert detections across {distinct_months:.0f} distinct calendar months) "
            "strongly supports persistent/industrial thermal anomaly."
        )
    elif pers_evidence.level == "MODERATE":
        recurrence_ev.append(
            f"Moderate historical recurrence ({hist_count:.0f} detections across {distinct_months:.0f} months) "
            "indicates periodic recurrence."
        )
    else:
        recurrence_ev.append(
            f"Sparse or absent pre-alert recurrence ({hist_count:.0f} historical detections) "
            "supports acute, non-persistent event."
        )

    if days_since < 60.0:
        recurrence_ev.append(f"Recent pre-alert activity within {days_since:.0f} days supports ongoing localized activity.")
    elif days_since < 9999.0:
        recurrence_ev.append(f"Last pre-alert detection occurred {days_since:.0f} days prior to alert cutoff.")

    # 3. Ecological Evidence
    forest_score = ecoregion["forest_biome_score"]
    agri_score = ecoregion["agri_heartland_score"]

    if forest_score > 0.5:
        ecological_ev.append("Located within recognized Indian forest biome (Western Ghats / Central Highlands / NE / Himalayas / Odisha).")
    if agri_score > 0.5:
        ecological_ev.append("Located within prime agricultural heartland (Indo-Gangetic Plain / Krishna-Godavari / Cauvery / Malwa).")
    if forest_score <= 0.5 and agri_score <= 0.5:
        ecological_ev.append("Located in non-forest, non-prime-agricultural transitional terrain.")

    # 4. Industrial Evidence
    dist_km = industrial["dist_to_fac_km"]
    within_1km = industrial["within_1km_fac"] > 0.5
    within_5km = industrial["within_5km_fac"] > 0.5

    if within_1km:
        industrial_ev.append(
            f"Close proximity ({dist_km:.2f} km) to registered facility ({ind_context.nearest_facility_name}) "
            "strongly contributes to industrial attribution."
        )
    elif within_5km:
        industrial_ev.append(
            f"Within 5 km radius ({dist_km:.2f} km) of industrial facility ({ind_context.nearest_facility_name})."
        )
    else:
        industrial_ev.append(
            f"Distant from known industrial facilities ({dist_km:.1f} km to nearest facility), "
            "rendering industrial facility source unlikely."
        )

    summary = (
        f"Model classifies event as '{pred_name}' with {confidence*100:.1f}% confidence "
        f"(probabilities: Ind={probabilities['industrial']*100:.1f}%, For={probabilities['forest']*100:.1f}%, "
        f"Agr={probabilities['agricultural']*100:.1f}%, Pers={probabilities['persistent']*100:.1f}%)."
    )

    return ExplanationRecord(
        prediction_summary=summary,
        thermal_evidence=thermal_ev,
        recurrence_evidence=recurrence_ev,
        ecological_evidence=ecological_ev,
        industrial_evidence=industrial_ev
    )
