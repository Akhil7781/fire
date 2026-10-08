# Stage 8.34 Task 1: Complete DS08 Dataset Lineage & Inventory Report

**Auditor:** Autonomous Agentic AI (Advanced Coding & Scientific Audit Team)  
**Scope:** Development Data Lineage ($N=131$: Train $N=107$, Val $N=24$)  
**Status:** COMPLETE & VERIFIED  
**Frozen 2026 Test Set:** ZERO Access (`FROZEN_TEST_ACCESSED = FALSE`)  

---

## 1. End-to-End Data Lineage Flow

```
Raw NASA VIIRS FIRMS (2,583 detections)
            │
            ▼
Physical Spatiotemporal Clustering (131 Dev Events)
   └───► ds08_stage8_25_physical_events.parquet
            │
            ▼
Statutory Ground-Truth Association (Tier 1 Evidence)
   └───► ds08_stage8_25_multiyear_labels.parquet
            │
            ▼
Cohort Partition Assignment (Train 2018-2024 N=107, Val 2025 N=24)
   └───► ds08_stage8_25_multimodal_event_cohort.parquet
            │
            ▼
Causal Feature Extraction Engine
   ├───► Alert Time (t0) Prefix Features (14-D)
   ├───► Historical FIRMS Recurrence Features (t <= t0 - 7d) (104-D)
   ├───► Industrial Facility Proximity (6-D)
   └───► Ecoregion Heartland Priors (3-D)
            │
            ▼
   └───► ds08_stage8_30_causal_features.parquet (127 Active Features)
```

---

## 2. Comprehensive Artifact Inventory Table

| Artifact Name | Purpose | Rows | Cols | Years | Target Labels? | Participates in Model? |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| `ds08_stage8_25_multiyear_firms.parquet` | Clean multi-year NASA VIIRS FIRMS thermal detections associated with events | 2583 | 21 | 2016-2026 | NO | NO (Lineage/Meta) |
| `ds08_stage8_25_physical_events.parquet` | Canonical spatiotemporally clustered physical events with duration and extent | 131 | 21 | 2016-2025 | YES | NO (Lineage/Meta) |
| `ds08_stage8_25_multiyear_labels.parquet` | Ground truth event-level multiyear labels and statutory adjudication evidence | 131 | 15 | 2016-2025 | YES | NO (Lineage/Meta) |
| `ds08_stage8_25_multimodal_event_cohort.parquet` | Multimodal event cohort with split assignments and optical availability flags | 131 | 23 | 2016-2025 | YES | NO (Lineage/Meta) |
| `ds08_stage8_30_causal_features.parquet` | Strictly causal H0 prefix features and multi-scale historical recurrence statistics | 131 | 137 | 2016-2025 | YES | **YES (Features)** |
| `ds08_stage8_30_historical_sequences.parquet` | Sequential FIRMS observations <= t0 - 7 days within 2km for temporal encoders | 131 | 10 | N/A | YES | **YES (Features)** |
| `industrial_facility_database.json` | Static coordinates and baseline FRP for registered factories/refineries | 2 | 0 | N/A | NO | NO (Lineage/Meta) |
| `agricultural_event_manifest.json` | Crop burning incident universe with harvest season dates | 2 | 0 | N/A | NO | NO (Lineage/Meta) |
| `forest_event_manifest.json` | Forest fire perimeter events and state forest records | 2 | 0 | N/A | NO | NO (Lineage/Meta) |
| `persistent_source_manifest.json` | Continuous thermal anomaly locations (FORBIDDEN FROM PRIMARY MODEL) | 2 | 0 | N/A | NO | NO (Lineage/Meta) |

---

## 3. Lineage Findings & Verification

1. **Deterministic Development Cohort Size:** Exactly 131 development events across all pipeline stages (107 training events from 2016–2024, 24 validation events from 2025).
2. **Causal Horizon Separation:** Alert-time features (`horizon == 'H0'`) use only detections available at or before $t_0$.
3. **Historical Recurrence Separation:** Historical recurrence features use only detections $\le t_0 - 7$ days, ensuring zero contamination from current event progression.
4. **Target Metadata Isolation:** Target-linked columns (`incident_id`, `evidence_source`, `label_tier`) are confined to reference/lineage tables and are never passed as model input tensors.

---
*Generated autonomously under Stage 8.34 strict test-lock constraints.*
