# Stage 8.34 Task 2: Canonical Event Master Table & Lineage Audit Report

**Auditor:** Autonomous Agentic AI (Advanced Coding & Scientific Audit Team)  
**Scope:** Development Master Table ($N=131$: Train $N=107$, Val $N=24$)  
**Status:** COMPLETE & AUDITED  
**Frozen 2026 Test Set:** ZERO Access (`FROZEN_TEST_ACCESSED = FALSE`)  

---

## 1. Canonical Event Master Table Specification

The canonical development event table contains exactly **131 events** with complete physical spatiotemporal bounds and statutory provenance:

- `event_id`: Unique canonical event identifier (e.g. `EVT_825_IND_...`)
- `incident_id`: Underlying statutory incident record identifier
- `target_class` & `class_id`: 4-class attribution label (0=Industrial, 1=Forest, 2=Agricultural, 3=Persistent)
- `split`: Development partition (`train` vs `val`)
- `year`: Incident year (2016–2025)
- `centroid_lat`, `centroid_lon`: Physical spatial center of initial thermal alert
- `event_start_time`, `event_end_time`: Physical event bounding duration
- `detection_count`: Number of raw VIIRS detections associated with event
- `source_detection_ids`: Exact raw VIIRS detection IDs
- `evidence_source`, `evidence_strength`, `label_tier`: Independent statutory grounding

---

## 2. Target-Linked Column Lineage & Data-Flow Audit

Runtime tracing of the 5 candidate target-linked columns:

| Column | In FIRMS? | In Model Feats? | Dev Non-Null | Affects Labels? | Affects Model Features? | Runtime Data-Flow Role | Leakage Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---|:---:|
| `associated_persistent_id` | True | False | 252 | True | **False** | Originates from reference source catalogs during multiyear ground-truth compilation in Stage 8.25. Confined strictly to labels/provenance; NEVER passed to model feature tensors. | **SAFE (EXCLUDED FROM MODEL TENSORS)** |
| `associated_forest_id` | True | False | 473 | True | **False** | Originates from reference source catalogs during multiyear ground-truth compilation in Stage 8.25. Confined strictly to labels/provenance; NEVER passed to model feature tensors. | **SAFE (EXCLUDED FROM MODEL TENSORS)** |
| `associated_agri_id` | True | False | 470 | True | **False** | Originates from reference source catalogs during multiyear ground-truth compilation in Stage 8.25. Confined strictly to labels/provenance; NEVER passed to model feature tensors. | **SAFE (EXCLUDED FROM MODEL TENSORS)** |
| `associated_incident_id` | True | False | 67 | True | **False** | Used during dataset generation in Stage 8.25 to map raw FIRMS clusters to ground-truth statutory incident records (e.g. MPCB/DISH factory fire reports). | **SAFE (EXCLUDED FROM MODEL TENSORS)** |
| `is_facility_baseline` | True | False | 0 | False | **False** | Used exclusively to filter historical facility background FIRMS points strictly prior to t0. Target event detections are asserted to have zero overlap (len(target_overlap_fac) == 0). | **SAFE (EXCLUDED FROM MODEL TENSORS)** |

---

## 3. Key Findings

1. **Zero Model Feature Contamination:** None of the 5 candidate target-linked columns (`associated_persistent_id`, `associated_forest_id`, `associated_agri_id`, `associated_incident_id`, `is_facility_baseline`) appear in `ds08_stage8_30_causal_features.parquet` or any Stage 8.33/8.34 input tensor.
2. **Facility Baseline Independence:** `is_facility_baseline` is used strictly in `history_dataset.py` to identify historical background thermal detections near factories prior to $t_0$. Target event detections are asserted to have zero intersection, preventing target leakage.
3. **Statutory Integrity:** `incident_id` and `evidence_source` establish independent real-world ground truth (MPCB, DISH, State Forest Departments, CPCB stubble monitor) and are safely sequestered from feature tensors.

---
*Generated autonomously under Stage 8.34 strict test-lock constraints.*
