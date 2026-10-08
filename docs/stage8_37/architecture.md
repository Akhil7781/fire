# System Architecture: DS08 Real-Time Thermal-Source Attribution

## 1. High-Level Overview
The DS08 Operational System integrates real-time NASA FIRMS satellite thermal observations with static ecoregion data, industrial facility databases, and multi-year historical thermal recurrence to perform **source-type attribution** across 4 operational classes:
- `0 = Industrial Fire` (acute industrial emergencies)
- `1 = Forest Fire` (wildfires and canopy burns)
- `2 = Agricultural Fire` (crop residue burning)
- `3 = Other / Persistent Thermal Source` (routine high-temperature industrial processes, gas flaring, brick kilns)

```
                    NASA FIRMS
                       |
                       v
                FIRMS Ingestion
                       |
                       v
                 Event Builder
                       |
             +---------+---------+
             |                   |
             v                   v
     Current Thermal       Historical FIRMS
             |                   |
             +---------+---------+
                       |
                       v
               Causal Features
                       |
             +---------+---------+
             |                   |
             v                   v
      Context Features      Recurrence
             |                   |
             +---------+---------+
                       |
                       v
              Frozen Static MLP
                       |
                       v
             4-Class Attribution
                       |
          +------------+------------+
          |            |            |
          v            v            v
        GIS DB       API        Explanation
                       |
                       v
                  Web Dashboard
```

---

## 2. Ingestion & Preprocessing
- **Upstream Sensor Ingestion:** NASA FIRMS (VIIRS on Suomi-NPP / NOAA-20 / NOAA-21, MODIS on Aqua / Terra).
- **Validation:** Enforces coordinate bounds, non-negative FRP, valid UTC acquisition timestamps, channel 4 and channel 5 brightness temperatures, and spatial-temporal deduplication.
- **Event Construction:** Groups discrete detection points within a $\le 3.0$ km spatial radius and $\le 24$ hour temporal window into discrete thermal events with computed centroids.

---

## 3. Causal Feature Architecture (41 Features)
1. **Thermal Dynamics (14 features, $t \le t_0$):**
   - Alert FRP, channel 4 & 5 brightness temperatures, Delta-TI, night flag, cumulative detection count, elapsed hours, running FRP statistics (mean, max, std), night ratio, spatial extent, FRP trend, inter-pass interval.
2. **Industrial Proximity (6 features):**
   - Great-circle distance to nearest facility (MIDC / GIDC / SIPCOT / refineries), 1km and 5km proximity indicators, facility baseline FRP, deviation, z-score.
3. **Ecoregion Cartography (3 features):**
   - Forest biome score (Western Ghats, Himalayas, Central Highlands, Northeast, Odisha), agricultural heartland score (Indo-Gangetic Plain, Krishna-Godavari, Cauvery, Malwa), Sentinel-2 flag.
4. **Pre-Alert Historical Recurrence (18 features, $t \le t_0 - 7$ days):**
   - Historical counts (1km, 2km, 5km), multi-year active days, active months, mean/max/std/CV FRP, dispersion, distinct calendar months, days since latest pre-alert detection, windowed counts (30d, 90d, 365d), night ratio, mean Delta-TI.

---

## 4. Frozen Neural Inference Engine
- **Architecture:** `Architecture1_StaticMLP`
- **Framework:** Pure PyTorch 2.x (< 50k parameters; exact count: 3,244)
- **Checkpoint SHA-256:** `5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2`
- **Execution:** Zero retraining, zero threshold tuning, deterministic inference.

---

## 5. Storage & Delivery
- **Geospatial Database:** SQLite (embedded local) or PostgreSQL + PostGIS (production container).
- **REST API:** FastAPI application providing real-time inference, batch processing, statistics, and GeoJSON export.
- **Web Dashboard:** Interactive Leaflet GIS frontend with class-encoded markers, confidence filtering, and event detail inspector.
