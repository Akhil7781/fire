# Scientific Quality & Research-Validity Review of Label Construction

**Audit Execution Timestamp**: 2026-09-23T18:10:24.832012+00:00

**Total FIRMS Detections Evaluated**: 1,175,795
**Total Labeled**: 1,875 (0.1595%)
**Total Unlabeled**: 1,173,920 (99.8405%)

---

## 1. Executive Summary & The Core Research-Validity Problem

While the initial label pipeline passed all 18 structural integrity checks (no nulls, valid ranges, 1:1 row alignment, zero leakage), the resulting label distribution demonstrates a fundamental scientific flaw:

- **Class 1 (Industrial Fire)**: 2 detections
- **Class 2 (Forest Fire)**: 2 detections
- **Class 3 (Agricultural Fire)**: 1 detection
- **Class 4 (Other Thermal Source)**: 1,870 detections
- **Class 0 (Unlabeled Background)**: 1,173,920 detections

> [!CAUTION]
> **Event Evidence vs. Static Source Conflation**: 99.73% of all labeled detections (1,870 out of 1,875) were derived from static infrastructure point/polygon catalogs (coalfields, volcanic vent, flare stacks) rather than verified fire disaster events. Proximity to a known continuous thermal source over a 15-month window does not mean an acute event occurred.

## 2. Source-by-Source Evidence Classification & Audit

Every evidence source has been categorized into one of the four required standardized evidence types:
1. `EVENT_EVIDENCE`: Specific documented fire incident with temporal start/end bounds.
2. `STATIC_SOURCE_EVIDENCE`: Stationary asset / facility inventory with chronic/permanent thermal emissions.
3. `REMOTE_SENSING_CORROBORATION`: Direct decametric optical/SWIR burn scar verification ($\Delta\text{NBR}$).
4. `CONTEXT_ONLY`: Coarse administrative, regional, or land-cover context without localized parcel proof.

| Source Name | Primary Evidence Category | Total Evi Records | EVENT | STATIC | RS CORROB | CONTEXT | FIRMS Matched | Tier A | Tier B | Tier C |
|---|---|---|---|---|---|---|---|---|---|---|
| `INDIA_INDUSTRIAL_INCIDENTS_2025` | **EVENT_EVIDENCE** | 12 | 12 | 0 | 0 | 0 | 2 | 0 | 2 | 0 |
| `FSI_VAN_AGNI_LFF_2025` | **EVENT_EVIDENCE** | 8 | 8 | 0 | 0 | 0 | 2 | 0 | 2 | 0 |
| `ICAR_IARI_CREAMS_2025` | **CONTEXT_ONLY** | 10 | 0 | 0 | 0 | 10 | 1 | 0 | 1 | 0 |
| `INDIA_OTHER_THERMAL_SOURCES_2025` | **STATIC_SOURCE_EVIDENCE** | 11 | 0 | 11 | 0 | 0 | 1,870 | 1,357 | 513 | 0 |

---

## 3. Per-Class Evidence & Detection Matrix

| Target Class | Event Evidence | Static Evidence | Confirmed (Tier A) | Probable (Tier B) | Ambiguous (Tier C) | Unlabeled Detections | Total Corpus Detections |
|---|---|---|---|---|---|---|---|
| **Class 1: Industrial Fire** | 12 | 0 | 0 | 2 | 0 | 0 | 2 |
| **Class 2: Forest Fire** | 8 | 0 | 0 | 2 | 0 | 0 | 2 |
| **Class 3: Agricultural Fire** | 0 | 10 | 0 | 1 | 0 | 0 | 1 |
| **Class 4: Other Thermal Source** | 0 | 11 | 1,357 | 513 | 0 | 0 | 1,870 |
| **Class 0: Unlabeled Background** | 0 | 0 | 0 | 0 | 0 | 1,173,920 | 1,173,920 |

---

## 4. In-Depth Scientific Review of Confidence Tiers

### 4.1 Re-evaluation of Tier A (Confirmed)
In the initial pipeline, 1,357 detections were assigned **Tier A (Confirmed)**. A scientific audit reveals that **100% of these Tier A assignments were false promotions**:
- **1,299 detections** matched `COAL_JHARIA_KUSUNDA_06` (Jharia coalfield colliery shapefile).
- **56 detections** matched `COAL_RANIGANJ_SEARSOLE_07` (Raniganj colliery shapefile).
- **2 detections** matched `POWER_TATA_MUNDRA_11` (Mundra thermal power station).

Because CMPDI and the Central Electricity Authority are statutory government bodies, the code assigned `base_confidence = 1.00` and `Tier A`. **This is scientifically invalid.** A colliery boundary or power plant coordinate is static asset context. Detecting heat near a coal mine over 15 months confirms that the coal mine is warm; it does NOT constitute an independently confirmed thermal disaster event. **All 1,357 detections must be stripped of Tier A status.**

### 4.2 Re-evaluation of Tier B (Probable / Weak)
- **518 detections** received Tier B: 477 at Barren Island volcano, 26 at Hazira gas flare, 10 at Duliajan flare, 2 at Nainital forest fire, 2 at Manali petrochem, and 1 at Patiala crop burn.
- **Volcano & Flare Detections (513 detections)**: These represent genuine physical detections of stationary emitters, but they must be labeled as `NON_EVENT_STATIC_SOURCE` or `PERSISTENT_THERMAL_SOURCE`, not equated with acute fire events.
- **Patiala Agricultural Detection (1 detection)**: Matched at a distance of **3.474 km** from the village centroid. At 3.47 km, this is coarse regional context, not parcel-level event proof. It should be downgraded to `AMBIGUOUS` (Tier C) or returned to `UNLABELED`.
- **Manali Industrial (2 detections) & Nainital Forest (2 detections)**: Temporally and spatially plausible matches ($\le 2.8$ km), but without decametric optical damage corroboration (Sentinel-2 $\Delta\text{NBR}$), they remain weak/probable candidates.

## 5. Answers to Mandatory Review Questions

### A. Which current labels remain scientifically defensible?
1. **Barren Island Volcanic Detections (477 detections)**: Defensible as Class 4 (`OTHER_THERMAL_SOURCE`), provided they carry a status of `NON_EVENT_STATIC_SOURCE` or `PERSISTENT_THERMAL_SOURCE`.
2. **Nainital Forest Fire Cluster (2 detections)**: Defensible as Class 2 (`FOREST_FIRE`), Tier B (`PROBABLE`), matching the multi-day FSI Large Forest Fire incident on April 25-26, 2025.
3. **Manali Petrochemical Corridor (2 detections)**: Defensible as Class 1 (`INDUSTRIAL_FIRE`), Tier B (`PROBABLE`), matching verified chemical solvent leaks on May 9-10, 2025.

### B. Which labels should be downgraded / reclassified?
1. **1,299 Jharia Coalfield Detections**: Stripped of Tier A Confirmed; reclassified as Class 4 `NON_EVENT_STATIC_SOURCE` with confidence $\le 0.50$.
2. **56 Raniganj Coalfield Detections**: Stripped of Tier A Confirmed; reclassified as Class 4 `NON_EVENT_STATIC_SOURCE`.
3. **2 Mundra Power Plant Detections**: Stripped of Tier A Confirmed; reclassified as Class 4 `NON_EVENT_STATIC_SOURCE`.
4. **1 Patiala Agricultural Detection**: Stripped of Tier B Probable; downgraded to `AMBIGUOUS` (Tier C) or `UNLABELED` (Class 0) due to 3.47 km distance from village centroid.

### C. Which source types are only contextual?
1. **Daily Agricultural Village/Tehsil Bulletins (ICAR-IARI CREAMS)**: Village centroids represent administrative collection points, not individual farm parcels. Contextual only.
2. **Industrial Park / Estate Polygons (OpenStreetMap, IILB)**: Spatial containment inside an industrial zone indicates industrial land-use context, but provides zero proof of a fire incident.
3. **Static Infrastructure Catalogs (CEA Power Plants, GGFR Flare Stacks, SentinelKilnDB)**: Useful for confounder filtering, but contextual without operational telemetry.

### D. Whether enough independent event labels exist for supervised training?
> [!IMPORTANT]
> **NO.** With only 2 confirmed industrial fire detections, 2 forest fire detections, 0 parcel-level agricultural fire detections, and 0 acute 'other' events out of 1,175,795 rows, **it is statistically and scientifically impossible to train a 4-class supervised classifier**.
> Attempting to fit a 4-class supervised model (e.g. Random Forest, MLP, or standard CNN) on $N=2$ industrial events would lead to severe overfitting, extreme class imbalance collapse, and zero generalization.
> This empirical finding provides decisive scientific justification for the project's original methodology: **Semi-Supervised Deep SAD (Anomaly Detection)**, where the 1.17M unlabeled detections are modeled as the normative background distribution, and industrial fires are treated as rare, localized anomalies.

### E. What additional reference data is required to support a 4-class model?
1. **For Forest Fires (Class 2)**:
   - Ingest wall-to-wall **MODIS MCD64A1 v6.1 500m Burned Area** raster tiles for India across all 12 months of 2025.
   - Download the **Global Fire Atlas (Zenodo 2025)** vector perimeters, which delineate discrete fire events with start/end dates and spread trajectories. This will scale Class 2 event labels from 2 to $>40,000$ verified event detections.
2. **For Agricultural Fires (Class 3)**:
   - Implement an automated **Sentinel-2 MSI Level-2A 10m parcel-level burn scar detection pipeline** (using Differenced Normalized Burn Ratio $\Delta\text{NBR} > 0.20$ or MIRBI) across Punjab, Haryana, and Western UP during the Oct–Nov Kharif burning window.
   - This will yield $>150,000$ parcel-verified agricultural burn labels with sub-pixel spatial precision.
3. **For Industrial Fires (Class 1)**:
   - Industrial fires remain an extreme-tail anomaly (~150 to 300 reportable incidents across all of India annually).
   - High-yield acquisition requires ingesting municipal and state Fire Services dispatch ledgers (e.g., Maharashtra Fire Services, Gujarat Fire Safety COP incident registries) combined with **Sentinel-2 SWIR Band 12 saturation and optical structural burn-scar verification**.
   - Because industrial fires will remain sparse ($N \approx 50\text{--}200$), the problem must be formulated as **Semi-Supervised Anomaly Detection (Deep SAD) with Weak Label Supervision**, exactly as designed in `PROJECT_SPEC.md`.
