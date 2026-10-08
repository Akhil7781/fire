# Spatiotemporal Label Matching Protocol & Pipeline Plan

This document specifies the algorithmic protocol for matching FIRMS thermal detections (2025 corpus) against independent reference datasets to produce audited ground-truth labels without temporal or spatial leakage.

---

## 1. Matching Tolerances & Explicit Configuration Parameters

All spatial, temporal, and spectral matching limits are declared as **explicit configurable parameters**. These parameters must be validated via empirical sensitivity sweeps rather than hardcoded.

```python
@dataclass
class LabelMatchingConfig:
    # Spatial Tolerances (Meters)
    spatial_tol_industrial_exact: float = 250.0      # Exact match to verified industrial facility point
    spatial_tol_industrial_polygon: float = 50.0      # Buffer around industrial polygon boundary
    spatial_tol_forest_cluster: float = 1000.0        # Match radius to FSI/MCD64A1 burned centroid
    spatial_tol_agri_field: float = 100.0             # Match radius to Sentinel-2 10m burned parcel
    spatial_tol_flaring_stack: float = 300.0          # Match radius to World Bank GGFR flare stack
    spatial_tol_brick_kiln: float = 150.0             # Match radius to SentinelKilnDB OBB centroid
    spatial_tol_volcano: float = 5000.0               # Buffer around Barren Island vent

    # Temporal Tolerances (Seconds / Days)
    temporal_tol_news_event_sec: float = 172800.0     # +/- 48 hours for news/SEBI disclosure date
    temporal_tol_spcb_order_sec: float = 259200.0     # +/- 72 hours for statutory SPCB inspection
    temporal_tol_agri_burn_sec: float = 259200.0     # +/- 72 hours for Sentinel-2 dNBR pre/post pair
    temporal_tol_snapshot_sec: float = 900.0          # Same-overpass window (+/- 15 min)

    # Spectral / Physical Validation Parameters
    min_sentinel2_dnbr_industrial: float = 0.15       # Minimum dNBR for structural damage scar
    min_sentinel2_dnbr_agri: float = 0.20             # Minimum dNBR for crop residue burn scar
    max_flare_blackbody_temp_k: float = 1600.0        # Minimum Plank temperature for gas flare (VNF)

    # Confidence Weights
    weight_statutory_report: float = 1.00
    weight_news_corroborated: float = 0.85
    weight_optical_burn_scar: float = 0.90
    weight_spatial_mask_only: float = 0.30
```

---

## 2. Class-by-Class Matching Protocols

### 2.1 Class 1: Industrial Fire Matching Protocol
To prevent the *Spatial Proximity Fallacy*, an industrial detection $i$ at $(\phi_i, \lambda_i, t_i)$ is labeled **Class 1 (Industrial Fire)** ONLY if it passes the following 3-step pipeline:

1. **Spatial Filter**: Detection falls within `spatial_tol_industrial_polygon` of an OSM / IILB industrial polygon, OR within `spatial_tol_industrial_exact` of a SEBI/SPCB facility address.
2. **Confounder Rejection**: Point does NOT match a known gas flare stack (`spatial_tol_flaring_stack` in World Bank GGFR) or continuous operational furnace.
3. **Event Corroboration**:
   - *Tier A ($c_i = 1.00$)*: Matched to a SEBI Regulation 30 corporate disclosure, SPCB closure order, NGT report, or EM-DAT record within `temporal_tol_spcb_order_sec` AND confirmed by Sentinel-2 $\Delta\text{NBR} \ge \text{min\_sentinel2\_dnbr\_industrial}$.
   - *Tier B ($c_i = 0.85$)*: Matched to $\ge 2$ independent news aggregator reports (GDELT / Press Trust of India) naming the exact industrial unit within `temporal_tol_news_event_sec`.
   - *Tier C ($c_i = 0.30$)*: Falls inside industrial park polygon BUT has no news report, no regulatory order, and no optical burn scar. $\rightarrow$ **Marked Ambiguous; excluded from training target pool**.

---

### 2.2 Class 2: Forest Fire Matching Protocol
A detection $i$ is labeled **Class 2 (Forest Fire)** if:

1. **Primary Spatial Matching**: Falls inside FSI FAST 3.0 Large Forest Fire (LFF) polygon, OR within `spatial_tol_forest_cluster` of an MCD64A1 burned area pixel / Global Fire Atlas polygon.
2. **Land Cover Validation**: Coordinates intersect FSI Forest Canopy Density mask (Very Dense, Moderately Dense, Open Forest) or State Forest Department boundary.
3. **Confidence Scoring**:
   - *Tier A ($c_i = 1.00$)*: Matched to HP/UK State Forest Department ground-verified beat report OR FSI LFF event perimeter.
   - *Tier B ($c_i = 0.80$)*: Matched to MODIS MCD64A1 burn date within $\pm 2$ days AND located in reserved forest.
   - *Tier C ($c_i = 0.40$)*: Isolated single detection on forest edge near agricultural fields. $\rightarrow$ **Ambiguous**.

---

### 2.3 Class 3: Agricultural Fire Matching Protocol
A detection $i$ is labeled **Class 3 (Agricultural Fire)** if:

1. **Spatial & Temporal Window**: Occurs during peak Kharif (Sept 15 – Nov 30) or Rabi (Apr 1 – May 31) burning seasons in agricultural land cover zones (Indo-Gangetic Plain / MP / Rajasthan).
2. **Primary Match**: Matched to ICAR-IARI CREAMS daily active fire point within `spatial_tol_agri_field`, OR PRSC/HARSAC daily AFL point.
3. **Optical Scar Corroboration**:
   - *Tier A ($c_i = 1.00$)*: Sentinel-2 Level-2A 10m post-burn scar ($\Delta\text{NBR} \ge \text{min\_sentinel2\_dnbr\_agri}$) confirms field parcel combustion.
   - *Tier B ($c_i = 0.80$)*: Matched to IARI/PRSC daily active fire point on cropland without cloud-free Sentinel-2 overpass.
   - *Tier C ($c_i = 0.30$)*: Occurs off-season on mixed cropland/scrubland boundary. $\rightarrow$ **Ambiguous**.

---

### 2.4 Class 4: Other Thermal Source Matching Protocol
A detection $i$ is labeled **Class 4 (Other Thermal Source)** if it matches any of the following continuous non-disaster thermal categories:

1. **Gas Flaring**: Distance $\le \text{spatial\_tol\_flaring\_stack}$ from World Bank GGFR flare location OR VIIRS Nightfire Planck temperature $T \ge \text{max\_flare\_blackbody\_temp\_k}$ ($1600\text{--}2200\text{ K}$). $\rightarrow$ *Tier A ($c_i = 1.00$)*.
2. **Brick Kiln**: Distance $\le \text{spatial\_tol\_brick\_kiln}$ from SentinelKilnDB polygon centroid during active firing season (Dec–May). $\rightarrow$ *Tier A ($c_i = 1.00$)*.
3. **Volcanic Activity**: Distance $\le \text{spatial\_tol\_volcano}$ from Barren Island vent ($12.278^\circ\text{N}, 93.858^\circ\text{E}$). $\rightarrow$ *Tier A ($c_i = 1.00$)*.
4. **Coal Seam Smoldering**: Coordinates fall inside Jharia / Raniganj coalfield colliery shapefiles with persistent multi-month thermal detections. $\rightarrow$ *Tier A ($c_i = 1.00$)*.
5. **Thermal Power Station**: Distance $\le 300\text{ m}$ from GEM / CEA utility thermal power plant generator unit. $\rightarrow$ *Tier A ($c_i = 1.00$)*.

---

## 3. Conflict Resolution Protocol

When a single FIRMS detection matches criteria for multiple reference classes (e.g., agricultural land adjacent to an industrial park boundary):

1. **Tier Superiority**: Higher confidence tier overrides lower confidence tier ($\text{Tier A} > \text{Tier B} > \text{Tier C}$).
2. **Specific Incident Priority**: Statutory incident proof (SEBI Reg 30 disclosure, SPCB closure order, NGT report) overrides general spatial masks.
3. **Persistent Emitter Overrides Transient Event**: If coordinates match a verified gas flare stack (World Bank GGFR) or brick kiln (SentinelKilnDB), the detection is assigned **Class 4 (Other)** unless official disaster documentation proves an explosion occurred at the flare/kiln site.
4. **Unresolvable Conflict**: If two reference sources of equal confidence tier give conflicting classifications (e.g. Tier B news reports industrial factory fire vs. Tier B Sentinel-2 scar shows agricultural field burn), assign:
   $$y_i = 0 \quad (\text{Unlabelled}), \quad c_i = 0.50 \quad (\text{Tier C Ambiguous})$$
   and log in the audit trail.

---

## 4. Output Label Schema

The resulting label table is saved to `data/processed/labels/master_labels_2025.parquet`:

| Column Name | Type | Description |
|---|---|---|
| `detection_id` | `String[64]` | SHA-256 primary key (joins 1:1 with `causal_features_2025.parquet`) |
| `label_class` | `Int16` | Target class label: 1=Industrial, 2=Forest, 3=Agri, 4=Other, 0=Unlabelled |
| `label_tier` | `String` | Hierarchy tier: `Tier A`, `Tier B`, `Tier C`, `Tier D` |
| `confidence_score` | `Float32` | Calibrated confidence score $c_i \in [0.0, 1.0]$ |
| `evidence_source` | `String` | Primary reference dataset source string (e.g. `SEBI_REG30+SENTINEL2`) |
| `evidence_id` | `String` | Unique reference incident/record identifier |
| `is_supervised_target` | `Boolean` | `True` if $c_i \ge 0.70$ and $y_i \in \{1, 2, 3, 4\}$; `False` otherwise |

---

## 5. Execution Steps Required Before Implementation

1. **Build Reference Dataset Ingestion Parsers**:
   - Write automated parsers for SEBI Reg 30 BSE/NSE RSS feeds, GDELT BigQuery queries, FSI Van Agni LFF exports, ICAR-IARI CREAMS bulletins, SentinelKilnDB GeoJSON, and World Bank GGFR Excel catalogs.
2. **Empirical Sensitivity Sweeps**:
   - Run spatial/temporal sensitivity sweeps on a 5% validation slice to calibrate spatial tolerances ($\text{spatial\_tol}$) and evaluate label yield stability.
3. **Execute Labeling Engine**:
   - Apply matching logic to generate `master_labels_2025.parquet` without modifying existing feature parquet files.
