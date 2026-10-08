# Stage 8.41: Final Demo Timing Report

This report records empirical timing measurements for the DS08 operational reviewer demonstration system.

---

## 1. System Latency & Performance Measurements

| Operation | Target Budget | Measured Latency | Status | Notes |
|:---|:---:|:---:|:---:|:---|
| **Backend Startup Time** | < 10.0 s | **3.89 s** | PASSED | Includes PyTorch initialization, model weights loading & SHA-256 verification, and SQLite table checks. |
| **Demo Data Ingestion & Inference** | < 10.0 s | **4.93 s** | PASSED | Ingests 619 VIIRS detections, clusters 428 thermal events, executes 41-feature extraction + PyTorch inference on all 428 events, and persists to SQLite in a single transaction. |
| **Map Layer Load (GeoJSON Fetch)** | < 1.0 s | **0.16 s** (163 ms) | PASSED | GeoJSON serialization of 428 clustered events with full properties and predictions. |
| **Average Event Selection & Drawer Load** | < 50.0 ms | **18.1 ms** | PASSED | Querying full telemetry, detection history, and rule-grounded explanation for individual events. |
| **Accordion Navigation & FAQ Filter** | < 10.0 ms | **< 2.0 ms** | PASSED | Instant client-side DOM expansion and smooth scrolling. |

---

## 2. Full Guided Reviewer Walkthrough Duration

The live reviewer demo consists of a standardized 11-to-12 step presentation sequence:

| Walkthrough Phase | Actions & Content Covered | Estimated Duration |
|:---|:---|:---:|
| **Phase 1: Ingestion & Pipeline** | System overview, "What Does It Do?" flowchart, 1-click FIRMS loading (619 soundings $\to$ 428 events). | 45 s |
| **Phase 2: Nationwide Geospatial Attribution** | Map pan/zoom, visual 4-class distribution, confidence slider filtering. | 35 s |
| **Phase 3: Scenario 1 — Industrial Fire** | Event `EVT_20250627_05B3B989`, Jamnagar Refinery (4.36 km), nocturnal timing, drawer telemetry, uncertainty badge. | 30 s |
| **Phase 4: Scenario 2 — Forest Fire** | Event `EVT_20250625_70A2651C`, Himalayan biome score 1.0, 4 soundings, drawer telemetry. | 25 s |
| **Phase 5: Scenario 3 — Agricultural Fire** | Event `EVT_20250628_96ABE7CB`, Salem cropland score 1.0, daytime burn, 51.0% confidence. | 25 s |
| **Phase 6: Scenario 4 — Persistent Source** | Event `EVT_825_PER_PER_SRC_05`, Hazira flaring corridor, 8 historical detections over 4 months, calibrated explanation. | 35 s |
| **Phase 7: Official Frozen Benchmark** | Frozen 2026 test results (78.57% Acc, 0.8021 Macro-F1, 81.67% Bal Acc, $N=28$). Dev vs Test separation. | 30 s |
| **Phase 8: Confusion Matrix Breakdown** | Per-class breakdown (Ind 100%, For 83.3%, Agri 83.3%, Pers 60.0%), discussion of 6 error cases. | 30 s |
| **Phase 9: Limitations & Reviewer Q&A** | Side-by-side comparison, honest limitations, clicking 2-3 quick-answer buttons. | 35 s |
| **Total Rehearsal Duration** | **Full End-to-End Walkthrough** | **~4 minutes 50 seconds** |

**Conclusion:** The full live demonstration fits cleanly within the target **3–5 minute window**, providing ample time for technical explanation without lag or dead air.
