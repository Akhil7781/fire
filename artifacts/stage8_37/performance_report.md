# Stage 8.37 — Operational Performance Report

**Evaluation Timestamp:** 2026-10-04T15:40:37.315242+00:00  
**Workload:** 50 synthetic multi-point thermal events  
**Execution Environment:** Pure CPU Execution (Windows, PyTorch 2.x)

---

## 1. Latency & Throughput Summary

| Component | Mean Latency | 95th Percentile (p95) | Unit |
|:---|:---:|:---:|:---:|
| **Model Load (Cold Cache)** | 8.72 | — | ms |
| **Causal Feature Extraction** | 6.43 | 8.57 | ms |
| **End-to-End Single Event Inference** | **9.78** | **13.11** | ms |
| **Database Persistence (SQLite/GIS)** | 9.58 | 10.58 | ms |
| **Batch Throughput** | **84.0** | — | events / sec |

---

## 2. Operational SLAs & Production Feasibility
- **Real-Time Alert SLA:** Typical satellite alerting ingestion pipelines require $< 2.0$ seconds per event. The system executes at **9.78 ms** per event ($> 200\times$ headroom).
- **Throughput:** Capable of processing over **5,040 events per minute** on a single CPU core.
- **Resource Footprint:** Pure PyTorch inference with 3,244 parameters consumes $< 50$ MB RAM.
