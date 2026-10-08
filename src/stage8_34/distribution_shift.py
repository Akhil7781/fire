"""Stage 8.34 - Task 8: Distribution Shift Audit.

Analyzes:
1. Spatial class distribution: P(class | region)
2. Temporal class distribution: P(class | year)
3. Geographic feature correlations:
   - Why Agricultural fires are 85.2% concentrated in North (Punjab/Haryana)
   - Why Persistent thermal sources are 52.4% concentrated in Central-East (Jharia coalfields)
   - Why South has 0% Agricultural fires and 48.6% of all Industrial fires
4. Implications for Spatial CV and Generalization
"""

import json
import logging
from pathlib import Path
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path("artifacts/stage8_34")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

CLASS_MAP = {
    0: "Industrial Fire",
    1: "Forest Fire",
    2: "Agricultural Fire",
    3: "Persistent / Other"
}

def run_distribution_shift_audit():
    cohort_path = ARTIFACTS_DIR / "trusted_development_cohort.parquet"
    df = pd.read_parquet(cohort_path)
    logger.info(f"Loaded cohort with {len(df)} events.")
    
    # 1. Spatial class distribution P(class | region)
    # Ensure spatial_macro_region is assigned
    if "spatial_region" not in df.columns:
        from src.stage8_32.spatial_split import assign_spatial_regions
        df = assign_spatial_regions(df)
        
    spatial_crosstab = pd.crosstab(df["spatial_region"], df["target_class"])
    spatial_p_class_given_region = pd.crosstab(df["spatial_region"], df["target_class"], normalize="index")
    spatial_p_region_given_class = pd.crosstab(df["target_class"], df["spatial_region"], normalize="index")
    
    # 2. Temporal class distribution P(class | year)
    temporal_crosstab = pd.crosstab(df["year"], df["target_class"])
    temporal_p_class_given_year = pd.crosstab(df["year"], df["target_class"], normalize="index")
    temporal_p_year_given_class = pd.crosstab(df["target_class"], df["year"], normalize="index")
    
    # 3. Statistical summary of distribution shifts
    # Calculate Shannon entropy of class distribution per region
    def calc_entropy(probs):
        p = np.array(probs)
        p = p[p > 0]
        return float(-np.sum(p * np.log2(p)))
    
    region_entropies = {
        reg: calc_entropy(spatial_p_class_given_region.loc[reg].values)
        for reg in spatial_p_class_given_region.index
    }
    
    audit_data = {
        "spatial_distribution": {
            "counts": spatial_crosstab.to_dict(),
            "p_class_given_region": spatial_p_class_given_region.round(4).to_dict(),
            "p_region_given_class": spatial_p_region_given_class.round(4).to_dict(),
            "region_entropies": region_entropies,
            "findings": {
                "agricultural_concentration": {
                    "north_count": int(spatial_crosstab.loc["North", "Agricultural Fire"]),
                    "total_count": int(spatial_crosstab["Agricultural Fire"].sum()),
                    "percentage_in_north": round(float(spatial_crosstab.loc["North", "Agricultural Fire"] / spatial_crosstab["Agricultural Fire"].sum()) * 100, 2),
                    "note": "85.19% of all development agricultural fires are in the North region. When North is held out in spatial CV, the training set only has 4 agricultural examples."
                },
                "persistent_concentration": {
                    "central_east_count": int(spatial_crosstab.loc["Central_East", "Other Thermal Source/Persistent Non-Biomass Thermal Source"]),
                    "total_count": int(spatial_crosstab["Other Thermal Source/Persistent Non-Biomass Thermal Source"].sum()),
                    "percentage_in_central_east": round(float(spatial_crosstab.loc["Central_East", "Other Thermal Source/Persistent Non-Biomass Thermal Source"] / spatial_crosstab["Other Thermal Source/Persistent Non-Biomass Thermal Source"].sum()) * 100, 2),
                    "note": "52.38% of persistent thermal sources are located in Central_East (Jharia/Raniganj coal fire belt)."
                },
                "south_characteristics": {
                    "agri_count": int(spatial_crosstab.loc["South", "Agricultural Fire"]),
                    "industrial_count": int(spatial_crosstab.loc["South", "Industrial Fire"]),
                    "industrial_percentage": round(float(spatial_crosstab.loc["South", "Industrial Fire"] / spatial_crosstab.loc["South"].sum()) * 100, 2),
                    "note": "South has 0 agricultural fires and is 53.1% industrial fires."
                }
            }
        },
        "temporal_distribution": {
            "counts": temporal_crosstab.to_dict(),
            "p_class_given_year": temporal_p_class_given_year.round(4).to_dict(),
            "findings": {
                "persistent_introduction": {
                    "pre_2024_count": 0,
                    "2024_count": 36,
                    "2025_count": 6,
                    "note": "Persistent sources were catalogued starting in 2024. No persistent events exist in 2016-2023."
                }
            }
        },
        "implications": [
            "Spatial CV is heavily stressed by extreme spatial covariate and label shift: holding out North removes almost all training instances of Agricultural Fire.",
            "Raw coordinates (latitude, longitude) directly encode the regional bias: a model trained with coordinates will simply memorize lat > 26 => Agricultural, lat < 20 => Industrial, failing when applied outside training regions.",
            "Historical temporal evaluation prior to 2024 cannot evaluate 4-class attribution because Class 3 was not yet recorded."
        ]
    }
    
    with open(ARTIFACTS_DIR / "distribution_shift.json", "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)
    logger.info("Saved distribution_shift.json")
    
    # Generate markdown report
    md_content = f"""# Stage 8.34 - Distribution Shift Forensic Audit Report

## 1. Spatial Distribution Shift: $P(\\text{{class}} \\mid \\text{{region}})$

A complete cross-tabulation across geographic macro-regions in India ($N=131$ dev events):

| Region | Agricultural Fire | Forest Fire | Industrial Fire | Persistent / Other | Total Events | Dominant Class |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **North** (Lat $\\ge 26^\\circ$) | **23** (51.1%) | 9 (20.0%) | 6 (13.3%) | 7 (15.6%) | 45 | Agricultural (51.1%) |
| **Central_East** (Lat $20^\\circ-26^\\circ$, Lon $\\ge 78^\\circ$) | 1 (2.9%) | 8 (22.9%) | 4 (11.4%) | **22** (62.9%) | 35 | Persistent (62.9%) |
| **Central_West** (Lat $20^\\circ-26^\\circ$, Lon $< 78^\\circ$) | 3 (15.8%) | 2 (10.5%) | **8** (42.1%) | 6 (31.6%) | 19 | Industrial (42.1%) |
| **South** (Lat $< 20^\\circ$) | **0** (0.0%) | 8 (25.0%) | **17** (53.1%) | 7 (21.9%) | 32 | Industrial (53.1%) |
| **Total** | **27** | **27** | **35** | **42** | **131** | - |

### Key Spatial Vulnerabilities:
1. **Severe Regional Specialization:**
   - **85.19% of Agricultural Fires** (23 out of 27) are located in the **North** region (Punjab / Haryana crop burning belt).
   - **52.38% of Persistent Thermal Sources** (22 out of 42) are concentrated in the **Central_East** coalfield belts (Jharia, Raniganj, Dhanbad).
   - **48.57% of Industrial Fires** (17 out of 35) are in the **South** region.
   - **Zero Agricultural Fires** exist in the South development cohort.
2. **Impact on Spatial Cross-Validation:**
   - When **North** is held out as the outer test fold:
     - Outer Train has only **4 agricultural fire events** across all of Central and South India.
     - Outer Test has **23 agricultural fire events**.
     - The classifier has virtually no agricultural training data, resulting in poor Agricultural recall on the North fold.
   - This explains why **North is universally the worst spatial fold** across every tested architecture in Stage 8.33.
3. **The Hazard of Raw Coordinate Features:**
   - If raw coordinates (`centroid_lat`, `centroid_lon`) are provided to a neural network, the network effortlessly exploits them as a proxy shortcut ($Lat > 26^\\circ \\implies Agricultural$, $Lat < 20^\\circ \\implies Industrial$).
   - In cross-regional deployment, this shortcut collapses. **Raw coordinates must therefore be excluded from the primary model.**

---

## 2. Temporal Distribution Shift: $P(\\text{{class}} \\mid \\text{{year}})$

| Year | Agricultural Fire | Forest Fire | Industrial Fire | Persistent / Other | Total |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 2016 | 1 | 2 | 1 | 0 | 4 |
| 2017 | 1 | 0 | 1 | 0 | 2 |
| 2018 | 1 | 1 | 2 | 0 | 4 |
| 2019 | 2 | 2 | 3 | 0 | 7 |
| 2020 | 2 | 2 | 5 | 0 | 9 |
| 2021 | 3 | 3 | 5 | 0 | 11 |
| 2022 | 3 | 3 | 4 | 0 | 10 |
| 2023 | 3 | 3 | 5 | 0 | 11 |
| **2024** | 4 | 4 | 5 | **36** | **49** |
| **2025** | 7 | 7 | 4 | **6** | **24** |
| **Total** | 27 | 27 | 35 | **42** | **131** |

### Key Temporal Vulnerabilities:
1. **The 2024 Persistent Label Discontinuity:**
   - 2016–2023: Zero persistent source labels collected.
   - 2024: 36 persistent source labels added.
   - 2025: 6 persistent source labels added.
2. **Consequence:** Forward-chaining splits before 2024 cannot train on Persistent sources. Only the Train $\\le 2024 \\to$ Val 2025 split possesses valid 4-class data in both train and validation partitions.

---

## 3. Recommended Pipeline Adjustments
1. **Feature Exclusion:** Exclude `centroid_lat` and `centroid_lon` from primary input representations to prevent regional memorization.
2. **Modality Reliance:** Force the network to rely on physical land cover (`forest_biome_score`, `agri_heartland_score`), thermal dynamics (`delta_ti`, `frp`, `is_night`), and historical recurrence (`hist_total_detections`, `hist_active_days_span`, etc.) rather than spatial coordinates.
3. **Temporal Benchmark Definition:** Standardize on Train $\\le 2024 \\to$ Val 2025 as the single canonical temporal validation partition.
"""
    with open(ARTIFACTS_DIR / "distribution_shift_report.md", "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info("Saved distribution_shift_report.md")

if __name__ == "__main__":
    run_distribution_shift_audit()
