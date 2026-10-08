# Satellite Thermal Anomaly Classification: Research & Preprocessing Specification

## 1. Project Overview & Scientific Scope
This research project develops an AI-based methodology for the classification of satellite thermal anomalies, with a primary objective of discriminating **industrial fires** (e.g., petrochemical accidents, refinery fires, factory blazes, metallurgical incidents) from other thermal signatures (e.g., wildfires, prescribed burns, agricultural residue clearing, continuous gas flaring, and sensor noise/false alarms).

### Foundational Principles & Invariants:
1. **Raw Data Preservation**: Raw FIRMS observations remain immutable. Raw CSV files are never modified, renamed, moved, or deleted.
2. **Immutable Master Detection Table**: Raw detections are ingested into an immutable master table with full-digest deterministic, collision-resistant identifiers and canonical temporal types.
3. **Causal Spatiotemporal Semantics**: A detection at time $t_i$ may only be enriched with historical observations occurring strictly before $t_i$ ($t_j < t_i$). Future observations ($t_j > t_i$) are strictly prohibited in causal features to prevent temporal leakage.
4. **Primary Local Causal Context Scale**:
   - Spatial scale: Approximately **2 km local causal context radius**.
     *(Invariant: This radius is strictly a local causal context radius for neighborhood calculation; it must NOT be described or used as an event, source, or physical fire radius).*
   - Temporal scales: Trailing **6-hour** and **24-hour** lookback windows.
   - Multi-scale (1/3/5 km) and intermediate multi-horizon (7d/30d) production feature sets are eliminated.
   - The **90-day** horizon is reserved exclusively for the TCN historical sequence model.
5. **Context-Only Historical Burn-in Dataset**:
   - A dedicated historical context dataset (VIIRS NOAA-20 SP, India, 2024-10-01 through 2024-12-31) stored under `data/raw_context/` provides the required 90-day causal history for early 2025 observations.
   - It retains the exact same 16-attribute schema as the 2025 data.
   - It must **never** be used as test or evaluation data.
6. **No Permanent Physical Entity Assumptions**:
   - The pipeline does **NOT** assign permanent physical fire/source IDs.
   - The pipeline does **NOT** use global DBSCAN graphs or hard-coded persistence heuristics (e.g., "7 days = industrial").
   - Uber H3 resolution 8 is used strictly as a **geographic context index only**, and never as a physical fire or source identifier.
7. **Architectural Decoupling**:
   - **TCN Branch**: Operates on time-ordered historical observation sequences over a 90-day horizon within the local causal context radius.
   - **Deep SAD Branch**: Operates on instantaneous thermal features and 6h/24h causal spatiotemporal feature embeddings.
   - **YOLOv8 & Industrial GIS Branch**: Operates as a separate external-context branch interfacing downstream during multi-modal feature fusion.
8. **Strict Label Decoupling & Auditability**:
   - Preprocessing does not generate pseudo-labels. Proximity to industrial facilities does **NOT** define a fire as industrial. Ground truth must derive from independent reference evidence.
   - Raw FIRMS `type` is retained in the master table for provenance, but **excluded from the initial predictive feature set** until independently audited.
9. **Partitioning Precedes Learned Scaling (No Data Leakage)**:
   - Train/validation/test partitions must be assigned **before** any learned scaling or normalization.
   - Any derived features requiring fitted parameters must fit those parameters **strictly on the TRAIN partition only**.
   - Preserves spatial blocking ($\ge 25\text{ km}$ buffer) and forward temporal hold-outs.
10. **Memory-Safe Partitioned Processing**: Full-scale processing is chunked/partitioned and written directly to Parquet. The pipeline never loads or duplicates the 1,024,996 India-region NOAA-20 SP detections for 2025 into memory simultaneously.

---

## 2. Dataset Definition & Invariants

### 2.1 Sensor & Product Specifications (Primary 2025 Corpus)
- **Sensor**: Visible Infrared Imaging Radiometer Suite (VIIRS)
- **Host Platform**: NOAA-20 (JPSS-1)
- **Processing Stream**: Standard Processing (Science Quality / Post-reprocessed)
- **Geographic Domain**: India Region
- **Temporal Span**: 2025-01-01 00:00:00 UTC through 2025-12-31 23:59:59 UTC
- **Input Corpus**: 73 CSV files totaling **1,024,996 India-region NOAA-20 SP detections for 2025**
- **Data Integrity**: 0 missing values, 0 exact duplicate rows across all original 16 columns

### 2.2 Historical Burn-In Context Dataset (Q4 2024)
- **Storage Location**: `data/raw_context/`
- **Coverage**: VIIRS NOAA-20 SP, India, 2024-10-01 through 2024-12-31 (Q4 2024)
- **Purpose**: Provides complete 90-day trailing causal lookback history for detections occurring in early 2025 (e.g., January–March 2025), preventing artificial cold-start distortion.
- **Invariants**:
  - Retains identical 16-column schema and data types.
  - Ingested with `is_burn_in_context = True`.
  - **Evaluation Invariant**: Must **never** be included in validation, test, or evaluation sets.

### 2.3 Original 16 FIRMS Attributes
| # | Attribute Name | Raw Data Type | Unit / Format | Description |
|---|---|---|---|---|
| 1 | `latitude` | Float64 | Decimal degrees | Center latitude of the nominal 375m fire pixel (WGS-84) |
| 2 | `longitude` | Float64 | Decimal degrees | Center longitude of the nominal 375m fire pixel (WGS-84) |
| 3 | `bright_ti4` | Float32 | Kelvin (K) | VIIRS I-4 band (3.74 µm) brightness temperature |
| 4 | `scan` | Float32 | Kilometers (km) | Spatial pixel size in the along-scan direction |
| 5 | `track` | Float32 | Kilometers (km) | Spatial pixel size in the along-track direction |
| 6 | `acq_date` | String | YYYY-MM-DD | Acquisition date in UTC |
| 7 | `acq_time` | String / Int | HHMM | Acquisition time in UTC (0000 to 2359) |
| 8 | `satellite` | String | Categorical | Platform identifier (e.g., 'N20' or '1') |
| 9 | `instrument` | String | Categorical | Sensor instrument ('VIIRS') |
| 10 | `confidence` | String | Categorical | Algorithm detection confidence flag ('low', 'nominal', 'high') |
| 11 | `version` | String | Categorical | Science processing collection version (e.g., '1.0' / '2.0') |
| 12 | `bright_ti5` | Float32 | Kelvin (K) | VIIRS I-5 band (11.45 µm) brightness temperature |
| 13 | `frp` | Float32 | Megawatts (MW) | Fire Radiative Power computed from MIR radiance |
| 14 | `daynight` | String | Categorical | Solar illumination flag: 'D' (Day) or 'N' (Night) |
| 15 | `type` | Int16 | Categorical | Inferred hotspot type: 0=vegetation, 1=active volcano, 2=other static land, 3=offshore. *(Preserved in master table; excluded from predictive models)* |
| 16 | `col_16` | String / Numeric | Auxiliary | Additional FIRMS standard field as present in archive export |

### 2.4 Credential & Security Invariants
- `FIRMS_MAP_KEY` is restricted strictly to local `.env` and system environment variables.
- It must never be committed to version control, hardcoded in scripts, logged, or printed.

---

## 3. Data Lineage & Stable Identifier Specification

To guarantee reproducibility, traceability, and deterministic joinability across all downstream models without modifying raw inputs, a deterministic, collision-resistant identifier is generated during ingestion.

### 3.1 Identifier Formulation (`detection_id`)
Every observation receives a **deterministic, collision-resistant full SHA-256 hexadecimal digest** (64 hex characters) computed from its provenance tuple:

$$\text{hash\_input} = \text{source\_file} \,\|\, \text{row\_idx} \,\|\, \text{lat} \,\|\, \text{lon} \,\|\, \text{acq\_date} \,\|\, \text{acq\_time} \,\|\, \text{ti4} \,\|\, \text{frp}$$

$$\text{detection\_id} = \text{SHA256}(\text{hash\_input}) \quad (\text{Full 64-character lowercase hex digest})$$

### 3.2 Uniqueness Assertion Invariant
During ingestion and master table validation, the pipeline must strictly assert:
$$\text{detection\_id.nunique}() == \text{row\_count}$$
For the 2025 corpus, exactly $1,024,996$ unique `detection_id` values must be present.

### 3.3 Provenance Tracking Columns
- `detection_id` (String, 64-char): Deterministic, collision-resistant full SHA-256 primary key.
- `source_file` (String / Categorical): Base filename of the raw CSV.
- `source_row_idx` (Int32): 0-indexed row position within the source file.
- `is_burn_in_context` (Boolean): Flag indicating whether record belongs to 2024 Q4 context burn-in (`True`) or 2025 primary study dataset (`False`).
- `ingestion_timestamp_utc` (Timestamp): Timestamp when the master record was materialized.

---

## 4. Master Detection Table Schema

The master detection table is partitioned and written to **Apache Parquet** format (`data/interim/master_detections.parquet/`), utilizing dictionary encoding for categoricals and Snappy/ZSTD compression. Rows are sorted deterministically by `(timestamp_utc, latitude, longitude)`.

| Column Name | Storage Type | Nullable | Description / Semantics |
|---|---|---|---|
| `detection_id` | String[64] | No | Full SHA-256 hexadecimal primary key |
| `source_file` | String | No | Source raw CSV filename |
| `source_row_idx` | Int32 | No | Original row index in source CSV |
| `is_burn_in_context` | Boolean | No | True if record is from 2024 Q4 context dataset; False if 2025 |
| `latitude` | Float64 | No | Pixel center latitude, EPSG:4326 ($[-90.0, 90.0]$) |
| `longitude` | Float64 | No | Pixel center longitude, EPSG:4326 ($[-180.0, 180.0]$) |
| `acq_datetime_utc` | Timestamp[us, UTC] | No | Full parsed timestamp in UTC: `YYYY-MM-DD HH:MM:00Z` |
| `timestamp_utc` | Int64 | No | Integer seconds since Unix epoch (1970-01-01 00:00:00 UTC) |
| `h3_res8` | String | No | Uber H3 resolution 8 index (geographic context only) |
| `bright_ti4` | Float32 | No | I-4 brightness temperature ($K$) |
| `bright_ti5` | Float32 | No | I-5 brightness temperature ($K$) |
| `frp` | Float32 | No | Fire Radiative Power ($MW$) |
| `scan` | Float32 | No | Along-scan resolution ($km$) |
| `track` | Float32 | No | Along-track resolution ($km$) |
| `acq_date` | String | No | Original YYYY-MM-DD |
| `acq_time` | String | No | Original HHMM string |
| `satellite` | Category | No | Satellite identifier |
| `instrument` | Category | No | Instrument identifier ('VIIRS') |
| `confidence` | Category | No | Detection confidence ('low', 'nominal', 'high') |
| `version` | Category | No | Product version string |
| `daynight` | Category | No | Solar illumination flag ('D', 'N') |
| `type` | Int16 | No | Raw FIRMS type flag (Retained; excluded from predictive models) |
| `col_16` | Dynamic | No | Retained 16th raw attribute |

---

## 5. Derived Features: Explicit Mathematical, Physical & Causal Specifications

Every derived feature retained in the production specification satisfies an **explicit mathematical formula** and an **explicit physical/radiometric interpretation**. All heuristic or ungrounded features (including background exceedance) are omitted.

### 5.1 Instantaneous Thermal & Geometric Features (Stateless)
For any detection $i$:

1. **Brightness Temperature Difference ($\Delta T_i$)**:
   $$\Delta T_i = T_{I4, i} - T_{I5, i} \quad (K)$$
   - *Physical Meaning*: Thermal contrast between middle-infrared (MIR, 3.74 µm) and thermal-infrared (TIR, 11.45 µm). By Planck’s Law, spectral radiance increases far more rapidly at 3.74 µm than at 11.45 µm as emitter temperature rises. High $\Delta T$ is the fundamental physical signature of sub-pixel combustion.

2. **Brightness Temperature Ratio ($R_{T, i}$)**:
   $$R_{T, i} = \frac{T_{I4, i}}{T_{I5, i}}$$
   - *Physical Meaning*: Dimensionless relative thermal excitation index, normalized against sensor calibration drift.

3. **Ground Instantaneous Field of View Area ($A_{\text{pixel}, i}$)**:
   $$A_{\text{pixel}, i} = \text{scan}_i \times \text{track}_i \quad (\text{km}^2)$$
   - *Physical Meaning*: Resolves the spatial area of the detector ground footprint. VIIRS applies a 3:1 aggregation scheme; nadir pixels are $\approx 0.375 \times 0.375 = 0.14\text{ km}^2$, expanding up to $\approx 0.8 \times 0.8 = 0.64\text{ km}^2$ at the scan edges.

4. **Fire Radiative Power Density ($\text{FRP\_density}_i$)**:
   $$\text{FRP\_density}_i = \frac{\text{frp}_i}{A_{\text{pixel}, i}} \quad (\text{MW}/\text{km}^2)$$
   - *Physical Meaning*: Normalizes total radiant heat output by the observed ground footprint area, preventing off-nadir pixel broadening from artificially inflating apparent fire intensity.

5. **Log-Stabilized FRP ($\text{frp\_log1p}_i$)**:
   $$\text{frp\_log1p}_i = \ln(1 + \text{frp}_i)$$
   - *Physical Meaning*: Fire Radiative Power follows an extreme power-law (heavy-tailed) distribution spanning 0.1 MW to thousands of MW. Log-transformation stabilizes variance for neural and metric-based learners (Deep SAD/TCN).

---

### 5.2 Diurnal, Solar & Seasonal Cyclical Features (Stateless)
Quantifies cyclic operational regimes (continuous 24/7 industrial production vs. daytime agricultural burning vs. afternoon wildfire peaks):

1. **Fractional UTC Hour ($h_{\text{frac}, i}$)**:
   $$h_{\text{frac}, i} = \text{hour}_i + \frac{\text{minute}_i}{60.0} \in [0.0, 24.0)$$

2. **Diurnal Cyclic Harmonics ($\text{sin\_diurnal}_i, \text{cos\_diurnal}_i$)**:
   $$\theta_{\text{diurnal}, i} = \frac{2\pi \cdot h_{\text{frac}, i}}{24.0}$$
   $$\text{sin\_diurnal}_i = \sin(\theta_{\text{diurnal}, i}), \quad \text{cos\_diurnal}_i = \cos(\theta_{\text{diurnal}, i})$$
   - *Physical Meaning*: Continuous cyclical coordinate mapping of daily observation time eliminating the artificial numerical discontinuity between 23:59 and 00:00.

3. **Estimated Local Solar Time ($\text{LST}_i$) & Harmonics**:
   $$\text{LST}_i = \left( h_{\text{frac}, i} + \frac{\text{longitude}_i}{15.0} \right) \pmod{24.0}$$
   $$\text{sin\_lst}_i = \sin\left(\frac{2\pi \cdot \text{LST}_i}{24.0}\right), \quad \text{cos\_lst}_i = \cos\left(\frac{2\pi \cdot \text{LST}_i}{24.0}\right)$$
   - *Physical Meaning*: Converts UTC time to solar position at the detection's longitude (15 degrees longitude per hour). Isolates local solar zenith to detect whether thermal anomalies occur during local midday solar heating peaks or nocturnal cooling.

4. **Annual Seasonal Harmonics ($\text{sin\_annual}_i, \text{cos\_annual}_i$)**:
   $$\text{doy}_i = \text{day\_of\_year}_i \in [1, 365]$$
   $$\theta_{\text{annual}, i} = \frac{2\pi \cdot (\text{doy}_i - 1)}{365.25}$$
   $$\text{sin\_annual}_i = \sin(\theta_{\text{annual}, i}), \quad \text{cos\_annual}_i = \cos(\theta_{\text{annual}, i})$$
   - *Physical Meaning*: Captures annual seasonality (e.g., dry-season wildfire windows, post-monsoon crop stubble burning cycles) versus aseasonal industrial facility emissions.

---

### 5.3 Categorization of Temporal Features

#### Group A: CAUSAL HISTORICAL FEATURES (Strictly $t_j < t_i$)
- **Spatial Scope**: Local causal context radius of $R \le 2.0\text{ km}$ ($2,000\text{ meters}$).
- **Temporal Windows**: Trailing 6 hours and 24 hours ($0 < t_i - t_j \le \Delta T$).
- **Strict Causality Invariant**: $\forall j \in \mathcal{H}_i: t_j < t_i$. Future observations ($t_j \ge t_i$) are strictly excluded.
- Evaluated seamlessly against the 2024 Q4 context burn-in dataset when $t_i$ falls in early 2025.

$$\mathcal{H}_i(\Delta T) = \left\{ j \;\middle|\; d(\mathbf{x}_i, \mathbf{x}_j) \le 2.0\text{ km} \;\;\land\;\; 0 < t_i - t_j \le \Delta T \right\}, \quad \Delta T \in \{6\text{h}, 24\text{h}\}$$

| Feature Name | Mathematical Formula | Physical & Operational Meaning |
|---|---|---|
| `hist_count_6h_2km` | $|\mathcal{H}_i(6\text{h})|$ | Detections within 2 km local causal context radius over the preceding 6 hours. Measures short-term sub-diurnal persistence. |
| `hist_count_24h_2km` | $|\mathcal{H}_i(24\text{h})|$ | Detections within 2 km local causal context radius over the preceding 24 hours. Measures diurnal persistence across consecutive daytime and nighttime overpasses. |
| `time_since_last_det_2km` | $t_i - \max_{j \in \mathcal{H}_i(24\text{h})} t_j$ | Elapsed time (seconds) since the most recent previous detection within 2 km. Encoded with a large sentinel ($86,400\text{ s}$) if no prior detection exists within 24h. |
| `has_prior_24h_2km` | $\mathbb{I}(\|\mathcal{H}_i(24\text{h})\| > 0)$ | Binary flag indicating whether any historical detection occurred within 2 km in the prior 24 hours. Prevents imputation distortion. |
| `mean_frp_6h_2km` | $\frac{1}{\max(1, \|\mathcal{H}_i(6\text{h})\|)} \sum_{j \in \mathcal{H}_i(6\text{h})} \text{frp}_j$ | Average Fire Radiative Power of recent local detections over 6h. Measures short-term radiative intensity baseline. |
| `max_frp_6h_2km` | $\max_{j \in \mathcal{H}_i(6\text{h})} (\text{frp}_j) \text{ or } 0.0$ | Peak Fire Radiative Power observed within 2 km over the preceding 6 hours. |
| `mean_frp_24h_2km` | $\frac{1}{\max(1, \|\mathcal{H}_i(24\text{h})\|)} \sum_{j \in \mathcal{H}_i(24\text{h})} \text{frp}_j$ | Average Fire Radiative Power of local detections over the full preceding 24-hour cycle. |
| `max_frp_24h_2km` | $\max_{j \in \mathcal{H}_i(24\text{h})} (\text{frp}_j) \text{ or } 0.0$ | Peak Fire Radiative Power observed within 2 km over the preceding 24 hours. |
| `day_ratio_24h_2km` | $\frac{\sum_{j \in \mathcal{H}_i(24\text{h})} \mathbb{I}(\text{daynight}_j = 'D')}{\max(1, \|\mathcal{H}_i(24\text{h})\|)}$ | Fraction of daytime detections in the prior 24 hours. Industrial continuous operations burn day and night ($\approx 0.5$); agricultural burns concentrate heavily during daytime ($\approx 1.0$). |
| `spatial_dispersion_24h_2km` | $\sqrt{\frac{1}{\max(1, \|\mathcal{H}_i(24\text{h})\|)} \sum_{j \in \mathcal{H}_i(24\text{h})} d(\mathbf{x}_i, \mathbf{x}_j)^2}$ | Root-mean-square spatial distance (meters) between target detection and historical detections over 24h. Stationary emitters have low dispersion ($\le 400\text{ m}$ due to geolocation jitter); advancing wildfire perimeters exhibit large dispersion ($> 1000\text{ m}$). |

---

#### Group B: CONTEMPORANEOUS SNAPSHOT FEATURES (Non-Causal Overpass Context)
- **Spatial Scope**: Local context radius of $R \le 2.0\text{ km}$.
- **Temporal Window**: $|t_j - t_i| \le 15\text{ minutes}$ ($900\text{ seconds}$), $j \ne i$.
- **Explicit Non-Causal Nature**: Detections within $\pm 15$ minutes represent observations acquired during the **same satellite overpass** or adjacent overlapping scan swaths. Because this window may evaluate points occurring slightly after $t_i$ within the same swath, it is explicitly **NON-CAUSAL** across instantaneous time.
- **Architectural & Evaluation Constraints**:
  - Must be documented and tracked as **same-overpass / snapshot context**.
  - **Do NOT include future observations from this feature in any strictly causal TCN history or future-only forecasting evaluation.**
  - Primarily serves the static Deep SAD and YOLOv8 spatial branches to distinguish wide-area fire fronts from localized point emissions.

$$\mathcal{C}_i = \left\{ j \;\middle|\; d(\mathbf{x}_i, \mathbf{x}_j) \le 2.0\text{ km} \;\;\land\;\; |t_i - t_j| \le 900\text{ seconds} \;\;\land\;\; j \ne i \right\}$$

| Feature Name | Mathematical Formula | Physical & Operational Meaning |
|---|---|---|
| `snapshot_co_detect_count_2km` | $|\mathcal{C}_i|$ | Total count of active fire pixels detected during the same overpass window within 2 km. Distinguishes isolated single-point emitters (refinery flares, plant accidents) from wide-area multi-pixel fire complexes (forest wildfires). |

---

## 6. Spatial Indexing & Geographic Hotspot Context

### 6.1 Strict Invariants & Anti-Patterns
1. **NO Permanent Physical Fire/Source IDs**: Thermal anomaly pixels are point measurements of emitted radiance, not physical object entities. No entity clustering or persistent source IDs will be assigned.
2. **NO Global DBSCAN Graphs**: Global spatio-temporal clustering across the 1,024,996 records is strictly forbidden due to severe temporal chaining violations.
3. **NO Arbitrary Persistence Heuristics**: Persistence is not discretized by arbitrary thresholds (e.g. "active $>7$ days = industrial").
4. **2 km Radius Semantics**: The 2 km radius is strictly defined as a **local causal context radius**. It must **NEVER** be described or used as an event, source, or fire radius.

### 6.2 Uber H3 Resolution 8 Geographic Context Index
- **Primary Spatial Index**: Uber H3 Discrete Global Grid System at **Resolution 8**.
  - Average hexagon area: $\approx 0.737\text{ km}^2$
  - Average edge length: $\approx 461\text{ meters}$
  - Center-to-center distance between adjacent hexagons: $\approx 800\text{ meters}$
- **Sensory Match**: H3 Resolution 8 closely aligns with the VIIRS 375m active fire pixel footprint at nadir and moderate off-nadir angles.
- **Strict Ontological Clarification**: The H3 index (`h3_res8`) is **exclusively a spatial bin and geographic context index**. It is **NEVER** an assertion that an H3 cell represents a single physical industrial plant, chimney, or wildfire entity.
- **Efficient 2 km Local Causal Context Search Algorithm**:
  - For target coordinates $(\phi_i, \lambda_i)$ in cell $C_i$:
  - A 2 km radius covers an area contained within the 2-ring neighborhood ($\text{k\_ring}(C_i, 2)$).
  - Search candidates are retrieved instantly via the inverted index of the 2-ring cells.
  - Final candidate pruning applies the exact haversine distance metric: $d(\mathbf{x}_i, \mathbf{x}_j) \le 2000.0\text{ meters}$.
  - This guarantees $O(1)$ candidate retrieval per detection without boundary distortion or global $O(N^2)$ distance computations.

---

## 7. Planned Temporal Representation for TCN (Sequence Model)

*Note: Architectural specification only; implementation is deferred to subsequent modeling stages.*

### 7.1 Scope & 90-Day Sequence Formulation
- The **90-day lookback horizon** is reserved exclusively for the TCN sequence architecture.
- For target detection $i$ at time $t_i$:
  - The historical sequence $\mathbf{S}_i$ consists of up to $L$ prior detections within the 2 km local causal context radius over the preceding 90 days:
    $$\mathcal{H}_i(90\text{d}) = \left\{ j \;\middle|\; d(\mathbf{x}_i, \mathbf{x}_j) \le 2.0\text{ km} \;\;\land\;\; 0 < t_i - t_j \le 90\text{ days} \right\}$$
  - For detections in Q1 2025, $\mathcal{H}_i(90\text{d})$ is populated from the 2024 Q4 context burn-in dataset.
  - Sequence order: Strict causal chronological order:
    $$\mathbf{S}_i = \left[ \mathbf{v}_{i, -(K-1)}, \, \dots, \, \mathbf{v}_{i, -1}, \, \mathbf{v}_{i, 0} \right], \quad K = \min(|\mathcal{H}_i(90\text{d})| + 1, L)$$
    where $\mathbf{v}_{i, 0}$ is the instantaneous detection at $t_i$.

### 7.2 Per-Step Feature Vector ($\mathbf{v}_{i, -k} \in \mathbb{R}^d$)
1. $\Delta t_{-k} = t_i - t_{i, -k}$ (normalized elapsed seconds)
2. Geodesic distance: $d(\mathbf{x}_i, \mathbf{x}_{i, -k})$ (meters)
3. Brightness temperature: $\text{bright\_ti4}_{-k}$
4. Thermal contrast: $\Delta T_{-k} = \text{bright\_ti4}_{-k} - \text{bright\_ti5}_{-k}$
5. Fire Radiative Power: $\text{frp\_log1p}_{-k}$
6. Ground footprint area: $A_{\text{pixel}, -k}$
7. Day/Night indicator: $\mathbb{I}(\text{daynight}_{-k} = 'D')$
8. Detection confidence: One-hot encoded $\text{confidence}_{-k}$

### 7.3 Causality Guarantees
- Sequences with length $K < L$ are left-padded with zero vectors and tracked via a boolean mask $\mathbf{m}_i \in \{0, 1\}^L$.
- All temporal convolutional layers enforce causal (left-sided) dilated convolutions to guarantee zero future leakage.
- Contemporaneous snapshot features are strictly excluded from the TCN sequence history.

---

## 8. Deep SAD Feature Representation & Learned Scaling Isolation

*Note: Architectural specification only; implementation is deferred to subsequent modeling stages.*

### 8.1 Vector Formulation ($\mathbf{z}_i \in \mathbb{R}^D$)
Deep Semi-Supervised Anomaly Detection (Deep SAD) maps a static, fixed-dimensional feature vector $\mathbf{z}_i$ into a latent hypersphere space:

$$\mathbf{z}_i = \left[ \mathbf{f}_{\text{instantaneous}, i}, \, \mathbf{f}_{\text{diurnal}, i}, \, \mathbf{f}_{\text{causal\_2km}, i}, \, \mathbf{f}_{\text{snapshot}, i} \right]$$

### 8.2 Explicit Separation: Stateless Features vs. Fitted Parameters

#### A. Stateless Derived Features (Deterministic / No Learned Parameters)
The following features are computed via pure mathematical functions and require **zero training set statistics**:
- $\Delta T$, $R_T$, $A_{\text{pixel}}$, $\text{FRP\_density}$, $\text{frp\_log1p}$
- Fractional hour, diurnal $\sin/\cos$, LST $\sin/\cos$, annual $\sin/\cos$
- Causal historical counts, elapsed times, raw mean/max FRP, day ratio, spatial dispersion
- Snapshot contemporaneous co-detection count

#### B. Stateful Features (Require Learned / Fitted Parameters)
The following operations require statistics estimated from data distributions and **MUST be fitted strictly on the TRAIN partition only**:
1. **Continuous Normalization Scalers**:
   - Robust Scaler: Median $\tilde{x}_{\text{train}}$ and Interquartile Range $\text{IQR}_{\text{train}}$ for heavy-tailed continuous variables (`frp_log1p`, `FRP_density`, `time_since_last_det_2km`, `spatial_dispersion_24h_2km`).
   - Standard Scaler: Mean $\mu_{\text{train}}$ and standard deviation $\sigma_{\text{train}}$ for bounded/pseudo-normal variables ($\Delta T$, $R_T$, `bright_ti4`, `bright_ti5`).
2. **Missing/Sentinel Imputation Encoders**:
   - Imputation baselines for cold starts (e.g. median of `time_since_last_det_2km` when `has_prior_24h_2km == 0`).
3. **Categorical Encoders**:
   - Frequency / target / one-hot encodings for `confidence` and `daynight`.

**Leakage Prevention Invariant**:
$$\text{Scaler.fit}(\mathbf{X}_{\text{train}}) \implies \mathbf{X}_{\text{train\_scaled}} = \text{Scaler.transform}(\mathbf{X}_{\text{train}})$$
$$\mathbf{X}_{\text{val\_scaled}} = \text{Scaler.transform}(\mathbf{X}_{\text{val}}), \quad \mathbf{X}_{\text{test\_scaled}} = \text{Scaler.transform}(\mathbf{X}_{\text{test}})$$
Under no circumstances may validation, test, or context burn-in data be seen by `Scaler.fit()`.

---

## 9. External Context Branches (YOLOv8 & Industrial GIS)

*Note: Decoupled from the base tabular preprocessing pipeline.*

### 9.1 YOLOv8 Spatial Image/Raster Branch
- Generates localized multi-channel spatial raster patches ($64 \times 64$ pixels centered on thermal hotspot coordinates) combining thermal channels with contextual optical imagery or digital elevation models.
- Preprocessing requirement: The master Parquet output provides exact coordinates, scan/track angles, and detection IDs for downstream raster tiling.

### 9.2 Industrial GIS Branch
- Interfaces with external GIS data layers:
  - Global Gas Flaring Tracker / VIIRS Nightfire databases.
  - OpenStreetMap (OSM) industrial polygons (`landuse=industrial`, `industrial=refinery/chemical`).
  - Cadastral / facility boundary registries.
- **Strict Independence Principle**: GIS layers serve strictly as **external feature inputs** during feature fusion, NOT as ground-truth labeling rules during preprocessing.

---

## 10. Ground Truth & Labeling Protocol

### 10.1 Prohibited Pseudo-Labeling
- **Spatial Proximity Fallacy**: Preprocessing will **NEVER** assign an "industrial fire" label simply because a detection falls inside or near an industrial facility polygon.
- **FIRMS Type Fallacy**: The raw FIRMS `type` variable is a sensor-derived heuristic, not ground truth. It is preserved for auditing, never converted into a ground-truth label.

### 10.2 Independent Reference Ground Truth Sources
Labels ($y_i \in \{-1, 0, +1\}$) must be acquired from authoritative independent evidence:
1. **$y_i = +1$ (Confirmed Industrial Fire Incident)**:
   - Official industrial accident investigation reports (e.g., state disaster management logs, regulatory pollution control board records).
   - High-resolution optical satellite validation (Sentinel-2 / PlanetScope imagery showing smoke plumes emanating from destroyed industrial infrastructure).
2. **$y_i = -1$ (Confirmed Non-Industrial Thermal Anomaly)**:
   - Officially recorded wildfires (e.g., forest survey/wildfire perimeters).
   - Documented agricultural residue burning permits.
   - Known continuous operational gas flares (validated via multi-year nightfire baselines).
3. **$y_i = 0$ (Unlabelled Thermal Detections)**:
   - All remaining detections ($>99\%$ of the dataset) remain unlabelled and serve as the unlabelled training distribution for Deep SAD semi-supervised representation learning.

---

## 11. Train / Validation / Test Splitting Strategy

Partitioning is executed **prior to any feature normalization or learned parameter fitting**.

### 11.1 Leakage Prevention Protocols
1. **Spatial Blocking with Buffer Zone**:
   - The India study domain is partitioned into disjoint spatial blocks (e.g., $1.0^\circ \times 1.0^\circ$ spatial grid cells or administrative provinces).
   - A spatial exclusion buffer ($\ge 25\text{ km}$) is enforced along split boundaries to eliminate cross-border plume contamination and spatial autocorrelation leakage.
2. **Temporal Blocking**:
   - Partitions enforce forward-chaining temporal hold-outs (e.g., Train: 2025-01-01 to 2025-08-31; Validation: 2025-09-01 to 2025-10-31; Test: 2025-11-01 to 2025-12-31).
3. **Context Burn-In Exclusion**:
   - The 2024 Q4 context burn-in dataset is strictly barred from all validation, test, and evaluation sets.

---

## 12. Memory-Safe Chunked Processing & Expected Outputs

### 12.1 Chunked / Partitioned Processing Protocol
To safely process the **1,024,996 India-region NOAA-20 SP detections for 2025** without exhausting system memory:
1. **Stream Ingestion**: CSV files are read sequentially or in bounded chunks (50,000–100,000 rows), appending to partitioned Parquet files via `pyarrow.dataset.write_dataset`.
2. **Partitioning Scheme**: Partitioned on disk by `acq_year` and `acq_month`:
   `data/interim/master_detections.parquet/acq_year=YYYY/acq_month=MM/`
3. **Spatial Neighborhood Indexing**:
   - Detections are indexed by H3 resolution 8 cells.
   - An inverted spatial-temporal index maps each H3 cell to its temporal detection IDs and timestamps.
   - Neighborhood aggregation queries use sliding time windows within 2-ring H3 cells, eliminating full matrix $O(N^2)$ distance evaluations.

### 12.2 Output Files
```text
data/
├── raw/                                  # 73 raw CSV files (read-only, immutable)
├── raw_context/                          # 2024 Q4 India burn-in CSVs (read-only, immutable)
├── interim/
│   ├── master_detections.parquet/        # Partitioned master table with deterministic full SHA-256 IDs
│   │   ├── acq_year=2024/acq_month=...  # Context burn-in partition
│   │   └── acq_year=2025/acq_month=...  # Primary 2025 India study partitions
│   └── causal_features_2025.parquet     # Master table joined with 2km causal features
└── processed/
    ├── dataset_metadata.json            # Exact row counts, schema hashes, and column profiles
    └── splits/
        ├── train_ids.parquet            # Deterministic split ID assignments (Spatial buffer + temporal)
        ├── val_ids.parquet
        └── test_ids.parquet
```
