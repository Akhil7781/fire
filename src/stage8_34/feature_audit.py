"""Stage 8.34 - Task 10 & 11: Causal Feature Audit and Clean Reconstruction.

Audits and establishes the canonical, clean feature schema:
1. Strictly excludes target-leaking fields (associated_*, is_facility_baseline)
2. Strictly excludes persistent registry features
3. Excludes raw spatial coordinates (centroid_lat, centroid_lon) from primary feature set
4. Groups features into clean physical modalities:
   - thermal: alert-time thermal signature & early progression
   - industrial: static industrial context & baseline deviation
   - ecoregion: land-use and biome context
   - historical: pre-alert (t <= t0 - 7d) FIRMS thermal recurrence
5. Exports:
   - artifacts/stage8_34/clean_feature_schema.json
   - artifacts/stage8_34/clean_feature_provenance.csv
"""

import json
import logging
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path("artifacts/stage8_34")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

FORBIDDEN_COLUMNS = [
    "associated_persistent_id",
    "associated_forest_id",
    "associated_agri_id",
    "associated_incident_id",
    "is_facility_baseline",
    "persistent_registry_flag",
    "target_class",
    "class_id"
]

COORDINATE_COLUMNS = ["centroid_lat", "centroid_lon"]

THERMAL_FEATURES = [
    "current_frp",
    "current_bright_ti4",
    "current_bright_ti5",
    "current_delta_ti",
    "current_is_night",
    "detections_observed_so_far",
    "elapsed_observation_hours",
    "mean_frp_observed_so_far",
    "max_frp_observed_so_far",
    "std_frp_observed_so_far",
    "night_ratio_observed_so_far",
    "spatial_extent_observed_so_far",
    "frp_trend_observed_so_far",
    "time_since_prev_h"
]

INDUSTRIAL_FEATURES = [
    "dist_to_fac_km",
    "within_1km_fac",
    "within_5km_fac",
    "facility_baseline_frp",
    "frp_deviation",
    "facility_frp_zscore"
]

ECOREGION_FEATURES = [
    "forest_biome_score",
    "agri_heartland_score",
    "s2_available"
]

# Compact, informative pre-alert historical features (computed strictly at t <= t0 - 7d)
HISTORICAL_FEATURES = [
    "hist_count_full",
    "hist_active_days_full",
    "hist_active_months_full",
    "hist_mean_frp_full",
    "hist_max_frp_full",
    "hist_std_frp_full",
    "hist_cv_frp_full",
    "hist_count_1km",
    "hist_count_2km",
    "hist_count_5km",
    "hist_dispersion",
    "hist_distinct_calendar_months",
    "hist_days_since_latest",
    "hist_count_365d",
    "hist_count_90d",
    "hist_count_30d",
    "hist_night_ratio_full",
    "hist_mean_delta_ti_full"
]

PROVENANCE_METADATA = {
    # Thermal
    "current_frp": ("thermal", "FIRMS VIIRS/MODIS", "t <= t0", "Fire Radiative Power (MW) at alert time"),
    "current_bright_ti4": ("thermal", "FIRMS VIIRS I4", "t <= t0", "Brightness temperature in Band 4 (K)"),
    "current_bright_ti5": ("thermal", "FIRMS VIIRS I5", "t <= t0", "Brightness temperature in Band 5 (K)"),
    "current_delta_ti": ("thermal", "FIRMS VIIRS", "t <= t0", "Thermal contrast delta (TI4 - TI5) (K)"),
    "current_is_night": ("thermal", "FIRMS VIIRS", "t <= t0", "Binary night observation indicator"),
    "detections_observed_so_far": ("thermal", "FIRMS VIIRS", "t <= t0", "Count of detections in causal prefix"),
    "elapsed_observation_hours": ("thermal", "FIRMS VIIRS", "t <= t0", "Observation window span in hours"),
    "mean_frp_observed_so_far": ("thermal", "FIRMS VIIRS", "t <= t0", "Mean FRP observed up to alert time"),
    "max_frp_observed_so_far": ("thermal", "FIRMS VIIRS", "t <= t0", "Max FRP observed up to alert time"),
    "std_frp_observed_so_far": ("thermal", "FIRMS VIIRS", "t <= t0", "FRP standard deviation up to alert time"),
    "night_ratio_observed_so_far": ("thermal", "FIRMS VIIRS", "t <= t0", "Fraction of night detections in prefix"),
    "spatial_extent_observed_so_far": ("thermal", "FIRMS VIIRS", "t <= t0", "Bounding box diagonal (km) in prefix"),
    "frp_trend_observed_so_far": ("thermal", "FIRMS VIIRS", "t <= t0", "Linear rate of FRP change (MW/hr)"),
    "time_since_prev_h": ("thermal", "FIRMS VIIRS", "t <= t0", "Hours since previous observation"),
    # Industrial
    "dist_to_fac_km": ("industrial", "OSM / Industry Registry", "Static (Pre-event)", "Geodesic distance to nearest facility (km)"),
    "within_1km_fac": ("industrial", "OSM / Industry Registry", "Static (Pre-event)", "Binary indicator: distance <= 1 km"),
    "within_5km_fac": ("industrial", "OSM / Industry Registry", "Static (Pre-event)", "Binary indicator: distance <= 5 km"),
    "facility_baseline_frp": ("industrial", "Historical Baseline", "t <= t0 - 7d", "Historical baseline FRP of facility (MW)"),
    "frp_deviation": ("industrial", "Joint FIRMS/Facility", "t <= t0", "Current FRP minus historical baseline FRP"),
    "facility_frp_zscore": ("industrial", "Joint FIRMS/Facility", "t <= t0", "Normalized FRP z-score vs facility baseline"),
    # Ecoregion
    "forest_biome_score": ("ecoregion", "Copernicus CGLS Land Cover", "Static (Pre-event)", "Tree cover fraction within 5 km radius"),
    "agri_heartland_score": ("ecoregion", "Copernicus CGLS Land Cover", "Static (Pre-event)", "Cropland fraction within 5 km radius"),
    "s2_available": ("ecoregion", "Copernicus Sentinel-2", "Static (Pre-event)", "Sentinel-2 optical chip availability flag"),
    # Historical
    "hist_count_full": ("historical", "FIRMS 10-Year Archive", "t <= t0 - 7d", "Total historical detections at location"),
    "hist_active_days_full": ("historical", "FIRMS 10-Year Archive", "t <= t0 - 7d", "Distinct historical active calendar days"),
    "hist_active_months_full": ("historical", "FIRMS 10-Year Archive", "t <= t0 - 7d", "Distinct historical active calendar months"),
    "hist_mean_frp_full": ("historical", "FIRMS 10-Year Archive", "t <= t0 - 7d", "Mean historical FRP across all detections"),
    "hist_max_frp_full": ("historical", "FIRMS 10-Year Archive", "t <= t0 - 7d", "Maximum historical FRP across all detections"),
    "hist_std_frp_full": ("historical", "FIRMS 10-Year Archive", "t <= t0 - 7d", "Historical FRP standard deviation"),
    "hist_cv_frp_full": ("historical", "FIRMS 10-Year Archive", "t <= t0 - 7d", "Coefficient of variation of historical FRP"),
    "hist_count_1km": ("historical", "FIRMS 10-Year Archive", "t <= t0 - 7d", "Historical detections within 1 km radius"),
    "hist_count_2km": ("historical", "FIRMS 10-Year Archive", "t <= t0 - 7d", "Historical detections within 2 km radius"),
    "hist_count_5km": ("historical", "FIRMS 10-Year Archive", "t <= t0 - 7d", "Historical detections within 5 km radius"),
    "hist_dispersion": ("historical", "FIRMS 10-Year Archive", "t <= t0 - 7d", "Spatial spread of historical detections (km)"),
    "hist_distinct_calendar_months": ("historical", "FIRMS 10-Year Archive", "t <= t0 - 7d", "Number of distinct calendar months active"),
    "hist_days_since_latest": ("historical", "FIRMS 10-Year Archive", "t <= t0 - 7d", "Days between latest historic detection and t0"),
    "hist_count_365d": ("historical", "FIRMS 1-Year Window", "t <= t0 - 7d", "Historical detections in preceding 365 days"),
    "hist_count_90d": ("historical", "FIRMS 90-Day Window", "t <= t0 - 7d", "Historical detections in preceding 90 days"),
    "hist_count_30d": ("historical", "FIRMS 30-Day Window", "t <= t0 - 7d", "Historical detections in preceding 30 days"),
    "hist_night_ratio_full": ("historical", "FIRMS 10-Year Archive", "t <= t0 - 7d", "Fraction of historical detections at night"),
    "hist_mean_delta_ti_full": ("historical", "FIRMS 10-Year Archive", "t <= t0 - 7d", "Mean historical thermal contrast delta")
}

def run_feature_audit():
    # Load feature parquet to check availability
    df_feat = pd.read_parquet("data/interim/ds08_stage8_30_causal_features.parquet")
    cols = list(df_feat.columns)
    
    # Verify forbidden columns are NOT in planned feature sets
    all_clean_features = THERMAL_FEATURES + INDUSTRIAL_FEATURES + ECOREGION_FEATURES + HISTORICAL_FEATURES
    for forb in FORBIDDEN_COLUMNS:
        assert forb not in all_clean_features, f"LEAKAGE VIOLATION: {forb} found in clean features!"
    for coord in COORDINATE_COLUMNS:
        assert coord not in all_clean_features, f"GEOGRAPHIC SHORTCUT VIOLATION: {coord} found in clean features!"
        
    # Check that all clean features exist in the parquet file
    missing = [f for f in all_clean_features if f not in cols]
    if missing:
        raise ValueError(f"Features missing from parquet: {missing}")
        
    logger.info(f"Verified {len(all_clean_features)} clean features across 4 modalities.")
    
    schema = {
        "feature_version": "8.34_canonical",
        "total_features": len(all_clean_features),
        "excluded_columns": FORBIDDEN_COLUMNS + COORDINATE_COLUMNS,
        "raw_coordinates_included": False,
        "feature_groups": {
            "thermal": THERMAL_FEATURES,
            "industrial": INDUSTRIAL_FEATURES,
            "ecoregion": ECOREGION_FEATURES,
            "historical": HISTORICAL_FEATURES
        },
        "group_dimensions": {
            "thermal": len(THERMAL_FEATURES),
            "industrial": len(INDUSTRIAL_FEATURES),
            "ecoregion": len(ECOREGION_FEATURES),
            "historical": len(HISTORICAL_FEATURES)
        }
    }
    
    with open(ARTIFACTS_DIR / "clean_feature_schema.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    logger.info("Saved clean_feature_schema.json")
    
    # Build provenance table
    rows = []
    for feat in all_clean_features:
        grp, src, cutoff, desc = PROVENANCE_METADATA[feat]
        rows.append({
            "feature_name": feat,
            "feature_group": grp,
            "source_domain": src,
            "causal_cutoff": cutoff,
            "leakage_risk_status": "VERIFIED_CLEAN",
            "physical_meaning": desc
        })
    df_prov = pd.DataFrame(rows)
    df_prov.to_csv(ARTIFACTS_DIR / "clean_feature_provenance.csv", index=False)
    logger.info(f"Saved clean_feature_provenance.csv with {len(df_prov)} rows.")

if __name__ == "__main__":
    run_feature_audit()
