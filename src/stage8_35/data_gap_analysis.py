"""Stage 8.35 - Task 1: Formal Data Acquisition Plan & Gap Analysis.

Quantifies existing data gaps across:
- Class counts
- Class counts by geographic region
- Class counts by year (chronological gaps)
- Class counts by month (seasonality)
- Class counts by ecoregion

Answers:
1. Which class is geographically underrepresented?
2. Which class is temporally underrepresented?
3. Which class is absent from important regions?
4. Which year ranges lack Persistent examples?
5. Which spatial regions require additional samples?
6. How many additional events would materially improve each gap?

Outputs:
- artifacts/stage8_35/data_gap_analysis.json
- artifacts/stage8_35/data_gap_analysis.md
"""

import json
import logging
from pathlib import Path
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path("artifacts/stage8_35")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def run_gap_analysis():
    cohort_path = Path("artifacts/stage8_34/trusted_development_cohort.parquet")
    df = pd.read_parquet(cohort_path)
    
    # Load feature timestamps for month breakdown
    df_feat = pd.read_parquet("data/interim/ds08_stage8_30_causal_features.parquet")
    h0_feat = df_feat[(df_feat["horizon"] == "H0") & (df_feat["event_id"].isin(df["event_id"]))].copy()
    time_map = dict(zip(h0_feat["event_id"], h0_feat["feature_cutoff_time"]))
    df["event_time"] = df["event_id"].map(time_map)
    df["month"] = pd.to_datetime(df["event_time"]).dt.month
    
    # Cross-tabulations
    class_counts = df["target_class"].value_counts().to_dict()
    region_class = pd.crosstab(df["spatial_region"], df["target_class"])
    year_class = pd.crosstab(df["year"], df["target_class"])
    month_class = pd.crosstab(df["month"], df["target_class"])
    
    # Gap 1: Agricultural regional imbalance
    agri_total = class_counts["Agricultural Fire"]
    agri_north = int(region_class.loc["North", "Agricultural Fire"])
    agri_south = int(region_class.loc["South", "Agricultural Fire"])
    agri_cwest = int(region_class.loc["Central_West", "Agricultural Fire"])
    agri_ceast = int(region_class.loc["Central_East", "Agricultural Fire"])
    
    # Gap 2: Persistent temporal imbalance
    pers_col = "Other Thermal Source/Persistent Non-Biomass Thermal Source"
    pers_pre_2024 = int(df[(df["year"] < 2024) & (df["target_class"] == pers_col)]["event_id"].count())
    pers_2024 = int(df[(df["year"] == 2024) & (df["target_class"] == pers_col)]["event_id"].count())
    pers_2025 = int(df[(df["year"] == 2025) & (df["target_class"] == pers_col)]["event_id"].count())
    
    # Analysis payload
    analysis_data = {
        "baseline_cohort_size": len(df),
        "class_counts": class_counts,
        "region_by_class": region_class.to_dict(),
        "year_by_class": year_class.to_dict(),
        "month_by_class": month_class.to_dict(),
        "identified_gaps": {
            "gap_1_agricultural_geography": {
                "description": "Extreme concentration of Agricultural fires in North (Punjab/Haryana). Complete absence in South.",
                "current_north_count": agri_north,
                "current_north_percentage": round(agri_north / agri_total * 100, 2),
                "current_south_count": agri_south,
                "current_central_west_count": agri_cwest,
                "current_central_east_count": agri_ceast,
                "target_expansion": "Acquire 15-20 independent agricultural fire events across South (AP, TN, Karnataka) and Central/West (Maharashtra, Gujarat, MP)."
            },
            "gap_2_persistent_chronology": {
                "description": "Zero Persistent source events logged in 2016-2023. All 42 persistent events clustered in 2024-2025.",
                "current_pre_2024_count": pers_pre_2024,
                "current_2024_count": pers_2024,
                "current_2025_count": pers_2025,
                "target_expansion": "Retrospectively annotate 15-20 historical persistent source events across 2018, 2020, and 2022 from known physical facilities (refineries, coalfields, power stations) using historical FIRMS detections."
            },
            "gap_3_sample_size_per_spatial_fold": {
                "description": "Certain folds have minority classes with as few as 0-1 training events.",
                "target_expansion": "Raise total development cohort from N=131 to N >= 165 events, ensuring >= 5 examples per class in every outer spatial fold."
            }
        },
        "acquisition_targets": {
            "new_agricultural_events": 16,
            "new_persistent_events": 18,
            "target_total_events": 165
        }
    }
    
    with open(ARTIFACTS_DIR / "data_gap_analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis_data, f, indent=2)
    logger.info("Saved data_gap_analysis.json")
    
    # Generate Markdown Report
    md_content = f"""# Stage 8.35 - Formal Data Acquisition Plan & Gap Analysis

## Executive Summary
Following the Stage 8.34 forensic reconciliation, model performance limitations were conclusively shown to stem from **dataset distribution pathologies** rather than neural network capacity. 

This document details the quantitative gap analysis across the $N=131$ development cohort and defines the formal acquisition and annotation targets for Stage 8.35.

---

## 1. Class Distribution Across Geographic Regions ($N=131$)

| Region | Agricultural Fire | Forest Fire | Industrial Fire | Persistent / Other | Total Events | % Agri | % Persistent |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **North** | **23** (85.2%) | 9 (33.3%) | 6 (17.1%) | 7 (16.7%) | 45 | **51.1%** | 15.6% |
| **Central_East** | 1 (3.7%) | 8 (29.6%) | 4 (11.4%) | **22** (52.4%) | 35 | 2.9% | **62.9%** |
| **Central_West** | 3 (11.1%) | 2 (7.4%) | 8 (22.9%) | 6 (14.3%) | 19 | 15.8% | 31.6% |
| **South** | **0** (0.0%) | 8 (29.6%) | **17** (48.6%) | 7 (16.7%) | 32 | **0.0%** | 21.9% |
| **Total** | **27** | **27** | **35** | **42** | **131** | - | - |

### Core Vulnerabilities Identified:
1. **The Southern Agricultural Void:** Southern India has **zero** agricultural fire records in the development dataset, despite extensive paddy stubble burning in the Cauvery delta (Tamil Nadu), Krishna-Godavari delta (Andhra Pradesh), and sugarcane residue burning in Karnataka/Maharashtra.
2. **The Central_East Persistent Sink:** 52.4% of persistent sources are clustered in Central_East (Jharia coalfields).
3. **Severe Spatial CV Degradation:** When North is held out in spatial CV, outer training has only 4 agricultural fires, collapsing North Agricultural recall and causing North to be the worst spatial fold (Macro-F1 = 0.6358).

---

## 2. Chronological Distribution Across Years

| Year | Agricultural Fire | Forest Fire | Industrial Fire | Persistent / Other | Total Events |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 2016–2023 | 16 | 16 | 26 | **0** | 58 |
| **2024** | 4 | 4 | 5 | **36** | 49 |
| **2025** | 7 | 7 | 4 | **6** | 24 |
| **Total** | 27 | 27 | 35 | **42** | **131** |

### Core Vulnerabilities Identified:
1. **The 2016–2023 Persistent Void:** Prior to 2024, the dataset contains **zero** persistent source records.
2. **Consequence:** Forward-chaining evaluation prior to 2024 collapsed because models trained on $\le 2023$ were evaluated on 2024 where 73.5% of labels were Class 3.
3. **Opportunity:** Physical persistent thermal sources (refinery flare stacks, coalfield smoldering, steel mills) were active continuously across 2018–2023. Historical FIRMS observations from 2018, 2020, and 2022 can be retrospectively annotated without any target leakage.

---

## 3. Formal Acquisition Targets for Stage 8.35

| Acquisition Dimension | Current Support | Target Additions | Post-Expansion Target | Target Regions / Years |
|:---|:---:|:---:|:---:|:---|
| **Agricultural Fire Expansion** | 27 events (0 in South) | **+16 events** | **43 events** | South (AP, TN, Karnataka: +8), West/Central (MH, GJ, MP: +8) |
| **Persistent Historical Expansion** | 42 events (0 pre-2024) | **+18 events** | **60 events** | 2018 (+6), 2020 (+6), 2022 (+6) from documented persistent sites |
| **Total Development Cohort** | **131 events** | **+34 events** | **165 events** | Nationwide balanced representation |

---

## 4. Key Questions Answered
1. **Which class is geographically underrepresented?** Agricultural Fire (0 in South, only 1 in Central_East).
2. **Which class is temporally underrepresented?** Persistent / Other Thermal Source (0 in 2016–2023).
3. **Which class is absent from important regions?** Agricultural Fire is completely absent from Southern India.
4. **Which year ranges lack Persistent examples?** Years 2016 through 2023 lack Persistent events.
5. **Which spatial regions require additional samples?** South (Agricultural) and Central_West (Agricultural, Forest).
6. **How many additional events would materially improve each gap?** +16 Agricultural events and +18 Historical Persistent events (+34 events total) will provide genuine 4-class representation across all 4 macro-regions and multiple chronological eras.
"""
    with open(ARTIFACTS_DIR / "data_gap_analysis.md", "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info("Saved data_gap_analysis.md")

if __name__ == "__main__":
    run_gap_analysis()
