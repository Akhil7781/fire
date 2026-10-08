# Empirical Parameter Sensitivity & Calibration Report

**Evaluation Partition**: `train` (578,465 detections, strictly isolated from test)

## 1. Spatial Tolerance Sensitivity Sweep

| Spatial Tolerance (km) | Total Candidate Matches | Class Breakdown |
|---|---|---|
| 0.25 km | 0 | None |
| 0.50 km | 1 | `OTHER_THERMAL_SOURCE`: 1 |
| 1.00 km | 32 | `OTHER_THERMAL_SOURCE`: 32 |
| 1.50 km | 123 | `OTHER_THERMAL_SOURCE`: 123 |
| 2.00 km | 604 | `OTHER_THERMAL_SOURCE`: 604 |
| 3.00 km | 2,470 | `OTHER_THERMAL_SOURCE`: 2470 |
| 5.00 km | 3,354 | `FOREST_FIRE`: 6, `AGRICULTURAL_FIRE`: 1, `OTHER_THERMAL_SOURCE`: 3347 |

## 2. Temporal Tolerance Sensitivity Sweep

| Temporal Tolerance (hours) | Total Candidate Matches | Class Breakdown |
|---|---|---|
| 12.0 h | 30 | `OTHER_THERMAL_SOURCE`: 30 |
| 24.0 h | 30 | `OTHER_THERMAL_SOURCE`: 30 |
| 48.0 h | 30 | `OTHER_THERMAL_SOURCE`: 30 |
| 72.0 h | 30 | `OTHER_THERMAL_SOURCE`: 30 |
| 96.0 h | 30 | `OTHER_THERMAL_SOURCE`: 30 |
