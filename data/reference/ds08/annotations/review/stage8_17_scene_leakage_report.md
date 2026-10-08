# STAGE 8.17 — SCENE LEAKAGE & SPATIAL GROUPING AUDIT REPORT
**Spatial, Temporal, and Scene Overlap Analysis for the 15-Chip DS08 Pilot Cohort**

- **Execution Timestamp:** `2026-10-02T06:47:44.781291+00:00`
- **Package Version:** `ds08_pilot_v1 (v1.0.0)`
- **Total Chips Analyzed:** 15
- **Status:** **COMPLETE — FORMAL SPLIT STRATEGY RECOMMENDATION DELIVERED**

---

## 1. Executive Summary & Core Findings

An exhaustive spatial, temporal, and acquisition metadata audit was conducted across all 15 chips in the DS08 pilot cohort to evaluate data leakage risks.

### Key Findings:
1. **Unique Sentinel-2 Tiles:** All 15 chips originate from **15 distinct MGRS tiles** ($100\times 100\text{ km}$ UTM grid zones). Zero chips share the same tile footprint.
2. **Spatial Clustering:** Three chip pairs are located within $150\text{ km}$ in adjacent tiles:
   - `PILOT_02_NORTH` $\leftrightarrow$ `PILOT_04_NORTH_REPLACEMENT`: $114.1\text{ km}$ (Northern Indo-Gangetic plain)
   - `PILOT_11_SOUTH` $\leftrightarrow$ `PILOT_12_SOUTH`: $109.4\text{ km}$ (Southern peninsula plateau)
   - `PILOT_06_CENTRAL` $\leftrightarrow$ `PILOT_08_CENTRAL`: $139.2\text{ km}$ (Central plateau/forest region)
3. **Pilot Cohort Size Limitation ($n = 15$):**
   - The 15-chip pilot cohort is **statistically too small for a meaningful train / validation / test split**.
   - Splitting 15 chips (e.g. 10 train / 2 val / 3 test) would leave validation or test splits with 0 or 1 positive fire chip, and zero instances of `Agricultural Fire` (only 1 chip in the entire cohort has agricultural fire).
   - **Authoritative Recommendation:** The 15 pilot chips must **NOT** be partitioned into train/val/test splits. They must be maintained as a unified pilot calibration and benchmark evaluation cohort.
   - For future dataset scaling (e.g., Stage 8.18+ full cohort of 250 chips), a **spatial block / MGRS tile grouping strategy** must be enforced to prevent spatial autocorrelation leakage.

---

## 2. Chip Scene & Spatial Inventory ($n = 15$)

| Chip ID | Tile ID | Region | S2 Acquisition (UTC) | Latitude | Longitude | FRP (MW) | Target Status | Consensus Class |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`PILOT_02_NORTH`** | `T43RGM` | NORTH | `2025-03-24 05:41:06` | `28.8048` | `77.2603` | 4.07 | `NO_VISIBLE_TARGET` | `NO_VISIBLE_TARGET` |
| **`PILOT_03_NORTH`** | `T45RWL` | NORTH | `2025-03-29 04:51:06` | `27.1999` | `87.7278` | 8.67 | `HAS_ANNOTATIONS` | `Forest Fire` |
| **`PILOT_04_NORTH_REPLACEMENT`** | `T43RGP` | NORTH | `2025-03-19 05:40:58` | `29.7674` | `77.6690` | 3.05 | `NO_VISIBLE_TARGET` | `NO_VISIBLE_TARGET` |
| **`PILOT_06_CENTRAL`** | `T44QPM` | CENTRAL | `2025-04-01 05:12:22` | `23.6408` | `82.8587` | 0.43 | `HAS_ANNOTATIONS` | `Forest Fire` |
| **`PILOT_07_CENTRAL`** | `T43QHG` | CENTRAL | `2025-03-26 05:32:38` | `24.1562` | `78.7799` | 10.16 | `NO_VISIBLE_TARGET` | `NO_VISIBLE_TARGET` |
| **`PILOT_08_CENTRAL`** | `T44QNL` | CENTRAL | `2025-03-15 05:22:37` | `22.7613` | `81.8892` | 4.58 | `HAS_ANNOTATIONS` | `Agricultural Fire` |
| **`PILOT_10_SOUTH`** | `T44PKC` | SOUTH | `2025-03-15 05:24:44` | `15.9814` | `79.0726` | 0.77 | `NO_VISIBLE_TARGET` | `NO_VISIBLE_TARGET` |
| **`PILOT_11_SOUTH`** | `T43PHR` | SOUTH | `2025-03-28 05:25:04` | `13.5126` | `78.4120` | 6.07 | `NO_VISIBLE_TARGET` | `NO_VISIBLE_TARGET` |
| **`PILOT_12_SOUTH`** | `T43PGR` | SOUTH | `2025-03-18 05:25:07` | `14.3064` | `77.8128` | 20.16 | `NO_VISIBLE_TARGET` | `NO_VISIBLE_TARGET` |
| **`PILOT_14_EAST`** | `T46QGF` | EAST | `2025-03-17 04:23:29` | `18.6276` | `95.6783` | 4.86 | `NO_VISIBLE_TARGET` | `NO_VISIBLE_TARGET` |
| **`PILOT_15_EAST`** | `T47QLB` | EAST | `2025-03-17 04:13:01` | `19.7597` | `97.6930` | 2.28 | `HAS_ANNOTATIONS` | `Forest Fire` |
| **`PILOT_16_EAST`** | `T47QKD` | EAST | `2025-04-01 04:12:56` | `21.6311` | `97.1508` | 1.15 | `HAS_ANNOTATIONS` | `Forest Fire` |
| **`PILOT_18_WEST`** | `T42QWL` | WEST | `2025-03-05 06:03:13` | `23.4181` | `69.7863` | 5.40 | `HAS_ANNOTATIONS` | `Forest Fire` |
| **`PILOT_19_WEST`** | `T43QCU` | WEST | `2025-03-19 05:44:49` | `16.9849` | `73.8607` | 5.89 | `NO_VISIBLE_TARGET` | `NO_VISIBLE_TARGET` |
| **`PILOT_20_WEST`** | `T43QCD` | WEST | `2025-03-14 05:53:20` | `21.3993` | `73.6459` | 5.70 | `NO_VISIBLE_TARGET` | `NO_VISIBLE_TARGET` |

---

## 3. Spatial Proximity Matrix & Potential Leakage Clusters

To detect potential spatial autocorrelation leakage, geodesic distances between all $\binom{15}{2} = 105$ chip pairs were computed via the Haversine formula.

### Pairs with Geodesic Separation $< 200\text{ km}$:

| Pair | Distance | Region | Tile 1 | Tile 2 | Overlap / Leakage Risk Assessment |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `PILOT_11_SOUTH` $\leftrightarrow$ `PILOT_12_SOUTH` | **109.4 km** | SOUTH | `T43PHR` | `T43PGR` | Moderate spatial proximity; in future full splits, keep in same partition |
| `PILOT_02_NORTH` $\leftrightarrow$ `PILOT_04_NORTH_REPLACEMENT` | **114.1 km** | NORTH | `T43RGM` | `T43RGP` | Moderate spatial proximity; in future full splits, keep in same partition |
| `PILOT_06_CENTRAL` $\leftrightarrow$ `PILOT_08_CENTRAL` | **139.2 km** | CENTRAL | `T44QPM` | `T44QNL` | Moderate spatial proximity; in future full splits, keep in same partition |

All remaining 101 chip pairs exhibit geodesic distances between **$246\text{ km}$ and $2,425\text{ km}$**, ensuring broad geographical diversity across India.

---

## 4. Temporal Distribution & Same-Day Acquisitions

Acquisition timestamps span **2025-03-05 to 2025-04-01** (27-day temporal window during peak Indian pre-monsoon fire season):

| Acquisition Date | Chips Acquired | Geographic Regions | Spatial Separation | Temporal Leakage Assessment |
| :---: | :--- | :--- | :---: | :--- |
| `2025-03-15` | `PILOT_08_CENTRAL, PILOT_10_SOUTH` | CENTRAL, SOUTH | **809.6 km** | Zero leakage: chips in widely separated orbits/regions |
| `2025-03-17` | `PILOT_14_EAST, PILOT_15_EAST` | EAST, EAST | **246.2 km** | Zero leakage: chips in widely separated orbits/regions |
| `2025-03-19` | `PILOT_04_NORTH_REPLACEMENT, PILOT_19_WEST` | NORTH, WEST | **1473.2 km** | Zero leakage: chips in widely separated orbits/regions |
| `2025-04-01` | `PILOT_06_CENTRAL, PILOT_16_EAST` | CENTRAL, EAST | **1483.0 km** | Zero leakage: chips in widely separated orbits/regions |

---

## 5. Recommended Split Strategy for Downstream Scaling

### A. Immediate Pilot Policy ($n = 15$ chips):
- **DO NOT SPLIT:** Do not partition the 15-chip pilot cohort into train/validation/test sets.
- **Role:** Serves strictly as a calibrated human ground-truth benchmark cohort for model evaluation, baseline verification, and label consistency audits.

### B. Production Scaling Policy (Full $n = 250$ Chips):
When the full 250-chip dataset is ingested in Stage 8.18+, enforce the following split rules:
1. **Spatial Grouping (Tile-Level Blocking):** Split by Sentinel-2 MGRS Tile ID or geographic UTM blocks, ensuring all chips within the same $100\times 100\text{ km}$ tile or within $150\text{ km}$ reside in the same split partition.
2. **Class-Stratified Proportions:** Stratify by fire type (`Forest Fire`, `Agricultural Fire`, `Industrial Fire`, `Other Thermal Source`, `NO_VISIBLE_TARGET`) across splits.
3. **Region-Level Holdout:** Hold out at least one geographic region (e.g. Western or Southern Ghats) for zero-shot geographic transfer validation.
