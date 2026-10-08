# Label Construction Implementation Plan

## 1. System Overview & Invariants

This plan details the software architecture, data structures, algorithmic pipelines, and quality verification suite for the **Label Construction Phase** of the satellite thermal anomaly research project.

### Core Non-Negotiable Invariants
1. **Frozen Upstream State**: The preprocessing pipeline, causal features (`data/interim/causal_features_2025.parquet`), train/val/test split manifests (`data/processed/splits/*.parquet`), and H3 indexing are strictly read-only and immutable.
2. **Zero Self-Labeling**: Labels are derived solely from independent external reference evidence. NASA FIRMS predictive variables (`bright_ti4`, $\Delta T$, `frp`, `frp_log1p`, or sensor heuristic `type`) are strictly excluded from ground-truth assignment.
3. **Anti-Proximity Rule**: Spatial proximity to a facility or land use polygon is contextual evidence only, not automatic ground truth. An industrial fire requires affirmative proof of an accidental combustion event.
4. **Explicit UNLABELED State**: Unmatched detections are assigned `label_class = 0` (`UNLABELED`). An absence of evidence is never treated as a confirmed negative or mapped to Class 4.
5. **Full Provenance & Uncertainty**: Every assigned label carries its confidence weight, confidence tier, primary evidence ID, source dataset, spatial match distance, temporal offset, and matching method.

---

## 2. Normalized Evidence Model

To decouple heterogeneous reference sources from the downstream matching engine, all external reference datasets are ingested via dedicated adapters and transformed into a canonical, normalized evidence record:

```python
@dataclass(frozen=True)
class NormalizedEvidence:
    evidence_id: str                      # Globally unique deterministic hash (e.g., EVI_<source>_<hash>)
    source_name: str                      # Canonical source identifier (e.g., SEBI_REG30, FSI_LFF, etc.)
    source_type: str                      # Type: STATUTORY_DISCLOSURE, REGULATORY_ORDER, NEWS_EVENT,
                                          # SATELLITE_BURN_PRODUCT, INFRASTRUCTURE_CATALOG, GROUND_INSPECTION
    class_candidate: int                  # Target class candidate: 1=Industrial, 2=Forest, 3=Agri, 4=Other
    event_datetime_start: datetime        # Timezone-aware UTC start timestamp (or instant)
    event_datetime_end: datetime          # Timezone-aware UTC end timestamp (or instant)
    latitude: float                       # Centroid / location latitude in WGS-84 (EPSG:4326)
    longitude: float                      # Centroid / location longitude in WGS-84 (EPSG:4326)
    geometry_wkt: Optional[str]           # Optional WKT polygon / boundary representation
    location_precision: str               # EXACT_POINT, PLOT_POLYGON, FACILITY_CENTROID, DISTRICT_CENTROID
    event_description: str                # Human-readable incident summary or facility descriptor
    officialness_level: str               # STATUTORY_GOVERNMENT, SCIENTIFIC_AGENCY, COMMERCIAL_MEDIA, CROWDSOURCED
    source_url: str                       # Permlink / source record URL / DOI
    source_record_id: str                 # Native ID from provider dataset
    retrieval_timestamp: datetime         # Timestamp when record was ingested
    license_notes: str                    # Usage rights and license identifier
    confidence_basis: str                 # Technical justification for base confidence tier
```

Missing fields must be explicitly preserved as `None` / `null` rather than fabricated. Timestamps must be UTC timezone-aware.

---

## 3. Source Adapters Architecture

Source adapters are modular components under `src/labeling/sources/`. Each adapter implements a uniform interface:
1. `fetch_or_load()`: Loads raw reference data from cache/download or creates an adapter interface with documented API limitations.
2. `normalize()`: Maps raw schema to `NormalizedEvidence`.
3. `validate()`: Runs strict coordinate and timestamp sanity checks.
4. `save_normalized()`: Stores normalized Parquet under `data/reference/<class_name>/<source_name>.parquet`.
5. `diagnostics()`: Reports row count, date extent, spatial bbox, and missingness.

### Class-Specific Adapter Modules:
- **`src/labeling/sources/industrial.py`**:
  - `SEBIRegulation30Adapter`: Parses corporate filings from BSE/NSE.
  - `SPCBInvestigationAdapter`: Parses SPCB/NGT hazardous incident dossiers.
  - `GDELTNewsIncidentAdapter`: Ingests geocoded industrial fire news events.
  - `Sentinel2DamageCorroborator`: Checks optical $\Delta\text{NBR}$ / SWIR reflectance around incident candidates.
- **`src/labeling/sources/forest.py`**:
  - `FSIFastLFFAdapter`: Ingests FSI Large Forest Fire perimeters and alerts.
  - `MCD64A1BurnedAreaAdapter`: Ingests MODIS 500m day-of-burn perimeters.
  - `StateForestDeptAdapter`: Ingests ground-verified beat reports (HP FIRE, UK FFRMS).
- **`src/labeling/sources/agriculture.py`**:
  - `ICARIARICreamsAdapter`: Ingests daily agricultural active fire bulletins.
  - `PRSCHarsacAdapter`: Ingests state remote sensing centre agricultural burn logs.
  - `Sentinel2AgriBurnScarAdapter`: Ingests 10m parcel-level burn scar detections.
- **`src/labeling/sources/other_thermal.py`**:
  - `SentinelKilnDBAdapter`: Ingests 62,671 South Asia brick kiln polygons.
  - `WorldBankFlaringAdapter`: Ingests Global Gas Flaring Reduction Partnership flare stack coordinates.
  - `BarrenIslandVolcanoAdapter`: Encapsulates Barren Island volcanic coordinates and activity intervals.
  - `CMPDICoalFireAdapter`: Ingests Jharia and Raniganj coalfield colliery shapefiles.
  - `GEMPowerPlantAdapter`: Ingests Central Electricity Authority / GEM thermal power station coordinates.

---

## 4. Spatiotemporal Matching Engine

Matching operates detection-by-detection against candidate evidence collections using spatial indexing (KD-Tree / BallTree / H3 cell intersections) to avoid $O(N \times M)$ overhead:

### 4.1 Geodesic Spatial Matching
- Computes spherical Haversine distance:
  $$d(\mathbf{x}_i, \mathbf{x}_{\text{evi}}) = 2 R \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos\phi_i \cos\phi_{\text{evi}} \sin^2\left(\frac{\Delta\lambda}{2}\right)}\right)$$
- If evidence contains a polygon geometry, distance is calculated as the minimum distance from detection point to polygon boundary.
- An evidence candidate is spatially eligible if $d \le \text{spatial\_tol}(\text{source})$.

### 4.2 Temporal Interval Matching
- An evidence event covers an interval $[T_{\text{start}}, T_{\text{end}}]$.
- The temporal distance $\Delta t$ between detection timestamp $t_i$ and event interval is:
  $$\Delta t = \begin{cases} 0 & \text{if } T_{\text{start}} \le t_i \le T_{\text{end}} \\ t_i - T_{\text{end}} & \text{if } t_i > T_{\text{end}} \\ T_{\text{start}} - t_i & \text{if } t_i < T_{\text{start}} \end{cases}$$
- An evidence candidate is temporally eligible if $\Delta t \le \text{temporal\_tol}(\text{source})$.

---

## 5. Evidence Fusion & Confidence Assignment

For each FIRMS detection $i$, the fusion engine gathers all matching evidence candidates $\mathcal{M}_i$:

1. **Empty Match**: If $\mathcal{M}_i = \emptyset \implies y_i = 0$ (`UNLABELED`), `confidence = 0.0`, `tier = Tier D`.
2. **Single-Class Match**:
   - Determine highest tier among matching candidates:
     - Tier A: If any candidate has statutory or multi-pillar optical confirmation $\implies c_i = 1.00$.
     - Tier B: If candidates are verified news, high-density cluster, or curated infrastructure catalog $\implies c_i \in [0.70, 0.95]$.
     - Tier C: If evidence is purely a spatial boundary without event proof $\implies c_i \in [0.30, 0.69]$ (`AMBIGUOUS`).
3. **Multi-Class Conflict Handling**:
   - Apply conflict resolution protocol:
     - Rule 1 (Tier Superiority): Higher confidence tier overrides lower tier.
     - Rule 2 (Incident Proof Over Context): Specific disaster proof overrides general land cover masks.
     - Rule 3 (Persistent Confounder Priority): If coordinates match a permanent flare stack or brick kiln, default to Class 4 unless official documentation confirms a major explosion at that site.
     - Rule 4 (Unresolvable Tie): If conflicting sources have equal tier, assign `label_status = CONFLICTED`, $y_i = 0$, $c_i = 0.50$ (`Tier C Ambiguous`).

---

## 6. Output Artifacts & Data Split Safety

### Output Schema: `data/processed/labels/master_labels_2025.parquet`
Keyed 1:1 on `detection_id` (1,175,795 rows):
- `detection_id`: String[64] full SHA-256 digest
- `label_class`: Int16 (1=Industrial, 2=Forest, 3=Agri, 4=Other, 0=Unlabeled)
- `confidence_score`: Float32
- `confidence_tier`: String (`Tier A`, `Tier B`, `Tier C`, `Tier D`)
- `label_status`: String (`CONFIRMED`, `PROBABLE`, `AMBIGUOUS`, `UNLABELED`, `CONFLICTED`)
- `evidence_count`: Int32
- `primary_evidence_id`: String
- `primary_source`: String
- `secondary_evidence_ids`: List[String]
- `matching_method`: String
- `spatial_distance_km`: Float32
- `temporal_difference_hours`: Float32
- `is_supervised_target`: Boolean ($c_i \ge 0.70 \land y_i \in \{1, 2, 3, 4\}$)

### Split Independence
- Existing train, validation, and test partition IDs (`data/processed/splits/*.parquet`) are respected without modification.
- Parameter calibration is restricted to train/reference data; zero test leakage.

---

## 7. Verification & Audit Suite

A standalone quality auditor `scripts/audit_labels.py` will enforce the 18 quality criteria specified in Step 11, including:
1. Exact row preservation and uniqueness of `detection_id`.
2. 0 unlabelled rows mapped to Class 4.
3. 0 FIRMS `type` values used in labeling logic.
4. Complete provenance traceability for every labeled row.
5. Invariant checking on coordinate ranges and confidence scores.
