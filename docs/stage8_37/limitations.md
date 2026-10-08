# Operational Scope & System Limitations: DS08 Attribution System

## 1. System Capability Scope

### What the System Detects:
- **Source-Type Attribution:** Given an active thermal anomaly cluster detected by satellite radiometers (VIIRS / MODIS) at alert timestamp $t_0$, the neural model classifies whether the thermal anomaly corresponds to an industrial emergency, a forest wildfire, an agricultural stubble burn, or a routine persistent industrial process.

### What the System Does NOT Claim:
- **Universal Fire Detection:** The system does **not** discover fires directly from raw satellite imagery pixels. Upstream thermal anomaly discovery is performed by NASA FIRMS algorithms.
- **Universal Guarantee:** The model does not guarantee 100% detection of all ground-level fires (cloud cover, small sub-canopy fires below sensor resolution, or obstructed views are not captured by satellite radiometers).

---

## 2. Documented Operational Limitations

1. **Low-Recurrence Persistent Sources Without a Registry:**
   - In the absence of a hard-coded spatial registry, persistent thermal sources that have few pre-alert satellite detections ($< 10$ detections concentrated in a single calendar month) statistically resemble recurring seasonal agricultural burning.
2. **Ecotone Transition Ambiguity:**
   - Small fires ($< 5$ MW) occurring on transitional boundaries between scrub forest and agricultural fields can exhibit overlapping thermal and spatial signatures.
3. **Small-Sample Benchmark Granularity ($N=28$):**
   - The frozen independent test benchmark consists of 28 verified events. In this cohort, each single event represents 3.5714 percentage points of accuracy, yielding wide confidence intervals ([60.5%, 100.0%]).
4. **Geographic Domain Scope:**
   - The model was trained and standardized for the Indian subcontinent using Indian Agro-Ecological Zones and Indian industrial park databases. Deployment to other continental regions requires localized ecoregion and facility databases.
