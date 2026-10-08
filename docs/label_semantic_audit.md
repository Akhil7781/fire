# Scientific Label Semantic Audit Report

**Audit Execution Timestamp**: 2026-09-23T18:27:10.842471+00:00

**Total Records Evaluated**: 1,175,795 FIRMS NOAA-20 SP Detections (2024 Q4 + 2025)

---

## 1. Executive Summary & Semantic Realignment

Following the scientific quality review, the label construction engine was re-engineered to strictly enforce the invariant:

> **`EVENT_EVIDENCE != STATIC_SOURCE_EVIDENCE`**

Proximity to a stationary infrastructure asset (coalfield, power plant, gas flare, volcano) over a 15-month observation window indicates background operational heat or chronic combustion—**it does not confirm an acute, discrete fire disaster event**.

- **Total Confirmed Event Labels (Tier A)**: **0** (100% false Tier A promotions stripped).
- **Total Probable Event Labels (Tier B)**: **4** (2 Industrial Fire + 2 Forest Fire).
- **Persistent Thermal Source Records**: **1,870** (all classified as Class 4 with status `PERSISTENT_THERMAL_SOURCE`).
- **Context-Only Downgrades**: **1** (Patiala village centroid match excluded from positive training targets).
- **Supervised Fire Event Targets**: **4** (Only the 4 probable event records qualify for supervised training).

## 2. Before vs. After Class Distribution

| Target Class | Before Count | After Count | Net Change | Status Interpretation |
|---|---|---|---|---|
| **Class 0: UNLABELED** | 1,173,920 | 1,173,921 | +1 | Unmatched background + contextual exclusions |
| **Class 1: INDUSTRIAL_FIRE** | 2 | 2 | 0 | Acute chemical solvent fires (Manali Petrochem) |
| **Class 2: FOREST_FIRE** | 2 | 2 | 0 | Documented Large Forest Fires (Nainital LFF) |
| **Class 3: AGRICULTURAL_FIRE** | 1 | 0 | -1 | 3.47 km village centroid downgraded to UNLABELED |
| **Class 4: OTHER_THERMAL_SOURCE** | 1,870 | 1,870 | 0 | Stationary emitters (Jharia, Barren Island, Flares) |

## 3. Before vs. After Confidence Tiers

| Confidence Tier | Before Count | After Count | Net Change | Scientific Rationale |
|---|---|---|---|---|
| **Tier A (Confirmed)** | 1,357 | 0 | -1,357 | Stripped from static coalfield and power plant proximity |
| **Tier B (Probable)** | 518 | 1,874 | +1,356 | Persistent sources reclassified to Tier B; 4 acute events |
| **Tier C (Ambiguous)** | 0 | 0 | 0 | Conflicts/ties default to Class 0 Tier C |
| **Tier D (Unlabeled)** | 1,173,920 | 1,173,921 | +1 | 1,173,920 unmatched + 1 Patiala context exclusion |

## 4. Evidence Category & Semantic Status Breakdown

### 4.1 Evidence Categories Matched

- **`EVENT_EVIDENCE`**: **4** detections (Manali Petrochem: 2, Nainital LFF: 2)
- **`STATIC_SOURCE_EVIDENCE`**: **1,870** detections (Jharia: 1,299, Barren Island: 477, Raniganj: 56, Hazira: 26, Duliajan: 10, Mundra: 2)
- **`REMOTE_SENSING_CORROBORATION`**: **0** detections (None in baseline; requires Sentinel-2 dNBR)
- **`CONTEXT_ONLY`**: **1** detections (Patiala IARI bulletin)

### 4.2 Semantic Resolution Statuses

- **`CONFIRMED_EVENT`**: **0**
- **`PROBABLE_EVENT`**: **4**
- **`PERSISTENT_THERMAL_SOURCE`**: **1,870**
- **`CONTEXT_ONLY`**: **1**
- **`UNLABELED`**: **1,173,920**
- **`CONFLICTED`**: **0**

## 5. Source-Level Diagnostics

| Reference Source Name | Matched Detections | Primary Category | Final Classes Assigned | Assigned Statuses |
|---|---|---|---|---|
| `INDIA_INDUSTRIAL_INCIDENTS_2025` | 2 | `EVENT_EVIDENCE` | Class 1 (2) | `PROBABLE_EVENT` (2) |
| `FSI_VAN_AGNI_LFF_2025` | 2 | `EVENT_EVIDENCE` | Class 2 (2) | `PROBABLE_EVENT` (2) |
| `ICAR_IARI_CREAMS_2025` | 1 | `CONTEXT_ONLY` | Class 0 (1) | `CONTEXT_ONLY` (1) |
| `INDIA_OTHER_THERMAL_SOURCES_2025` | 1,870 | `STATIC_SOURCE_EVIDENCE` | Class 4 (1,870) | `PERSISTENT_THERMAL_SOURCE` (1,870) |

## 6. Partition Distributions (Train / Val / Test / Burn-In)

| Partition | Total Detections | Class 0 (Unlabeled) | Class 1 (Industrial) | Class 2 (Forest) | Class 3 (Agri) | Class 4 (Other) | Supervised Targets |
|---|---|---|---|---|---|---|---|
| **`context_burn_in`** | 150,799 | 150,469 | 0 | 0 | 0 | 330 | 0 |
| **`test`** | 47,881 | 47,567 | 0 | 0 | 0 | 314 | 0 |
| **`test_seen_spatial`** | 91,846 | 91,518 | 0 | 0 | 0 | 328 | 0 |
| **`train`** | 578,465 | 577,861 | 0 | 0 | 0 | 604 | 0 |
| **`train_heldout_spatial`** | 277,395 | 277,257 | 2 | 2 | 0 | 134 | 4 |
| **`val`** | 29,409 | 29,249 | 0 | 0 | 0 | 160 | 0 |

## 7. Exact Downgrade Log & Rationale

A total of **1,358 detections** were downgraded or reclassified during this audit:

1. **1,299 Jharia Coalfield Detections** (`COAL_JHARIA_KUSUNDA_06`):
   - *Previous*: Class 4, Tier A Confirmed (1.00), Status `CONFIRMED`.
   - *Corrected*: Class 4, Tier B Probable (0.70), Status `PERSISTENT_THERMAL_SOURCE`.
   - *Rationale*: Proximity to colliery boundary indicates chronic background coal seam heating, not a verified acute disaster event. Stripped of Tier A.

2. **56 Raniganj Coalfield Detections** (`COAL_RANIGANJ_SEARSOLE_07`):
   - *Previous*: Class 4, Tier A Confirmed (1.00), Status `CONFIRMED`.
   - *Corrected*: Class 4, Tier B Probable (0.70), Status `PERSISTENT_THERMAL_SOURCE`.
   - *Rationale*: Chronic subsurface smoldering colliery boundary, not an acute emergency incident. Stripped of Tier A.

3. **2 Mundra Thermal Power Station Detections** (`POWER_TATA_MUNDRA_11`):
   - *Previous*: Class 4, Tier A Confirmed (1.00), Status `CONFIRMED`.
   - *Corrected*: Class 4, Tier B Probable (0.70), Status `PERSISTENT_THERMAL_SOURCE`.
   - *Rationale*: Operational heat dissipation / cooling flue warmth from a supercritical generating station, not a structural fire disaster. Stripped of Tier A.

4. **1 Patiala Agricultural Centroid Detection** (`IARI_2025_PUNJAB_PATIALA_01`):
   - *Previous*: Class 3, Tier B Probable (0.80), Status `PROBABLE`.
   - *Corrected*: Class 0, Tier D Unlabeled (0.00), Status `CONTEXT_ONLY`.
   - *Rationale*: Centroid distance of 3.474 km represents coarse regional administrative context only; does not prove an active stubble fire on a specific farm parcel. Downgraded to UNLABELED / CONTEXT_ONLY with full provenance preserved.

5. **477 Barren Island Volcanic Detections** (`VOLCANO_BARREN_ISLAND_05`):
   - *Preserved*: Class 4 (`OTHER_THERMAL_SOURCE`), Tier B (0.80).
   - *Reclassified*: Status updated from `PROBABLE` to `PERSISTENT_THERMAL_SOURCE`.
   - *Rationale*: Active basaltic volcanic vent produces continuous thermal emissions; clearly distinguished from acute disaster events.

6. **36 Industrial Flare Detections** (Hazira: 26, Duliajan: 10):
   - *Preserved*: Class 4 (`OTHER_THERMAL_SOURCE`), Tier B (0.75).
   - *Reclassified*: Status updated from `PROBABLE` to `PERSISTENT_THERMAL_SOURCE`.
   - *Rationale*: Routine operational flaring combustion at hydrocarbon facilities; clearly distinguished from uncontained industrial fire events.

### Sample Downgraded Record Details

| Detection ID | Lat | Lon | Primary Source | Dist (km) | Prev Tier | New Tier | New Status | Downgrade Reason |
|---|---|---|---|---|---|---|---|---|
| `1e8552c94eb7eea6...` | 23.7802 | 86.3952 | `INDIA_OTHER_THERMAL_SOURCES_2025` | 1.77 | `Tier A` | `Tier B` | `PERSISTENT_THERMAL_SOURCE` | STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indi... |
| `f1696f740a228d68...` | 23.7657 | 86.4013 | `INDIA_OTHER_THERMAL_SOURCES_2025` | 1.86 | `Tier A` | `Tier B` | `PERSISTENT_THERMAL_SOURCE` | STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indi... |
| `cda8f0a507d39338...` | 23.7817 | 86.3939 | `INDIA_OTHER_THERMAL_SOURCES_2025` | 1.92 | `Tier A` | `Tier B` | `PERSISTENT_THERMAL_SOURCE` | STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indi... |
| `22f39bc5b21e1cfb...` | 23.7631 | 86.4040 | `INDIA_OTHER_THERMAL_SOURCES_2025` | 1.96 | `Tier A` | `Tier B` | `PERSISTENT_THERMAL_SOURCE` | STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indi... |
| `f37222e6afd8be27...` | 23.7666 | 86.4046 | `INDIA_OTHER_THERMAL_SOURCES_2025` | 1.59 | `Tier A` | `Tier B` | `PERSISTENT_THERMAL_SOURCE` | STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indi... |
| `1acf7ef0b5a03882...` | 23.7824 | 86.3941 | `INDIA_OTHER_THERMAL_SOURCES_2025` | 1.91 | `Tier A` | `Tier B` | `PERSISTENT_THERMAL_SOURCE` | STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indi... |
| `3d54e39ed7d6a65e...` | 23.7687 | 86.4014 | `INDIA_OTHER_THERMAL_SOURCES_2025` | 1.60 | `Tier A` | `Tier B` | `PERSISTENT_THERMAL_SOURCE` | STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indi... |
| `8ef862a8b10809b7...` | 23.6131 | 87.1429 | `INDIA_OTHER_THERMAL_SOURCES_2025` | 1.88 | `Tier A` | `Tier B` | `PERSISTENT_THERMAL_SOURCE` | STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indi... |
| `440dbfe0a27f0f2a...` | 23.7782 | 86.3962 | `INDIA_OTHER_THERMAL_SOURCES_2025` | 1.66 | `Tier A` | `Tier B` | `PERSISTENT_THERMAL_SOURCE` | STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indi... |
| `ebe09d45cf35bd3e...` | 23.7796 | 86.3951 | `INDIA_OTHER_THERMAL_SOURCES_2025` | 1.77 | `Tier A` | `Tier B` | `PERSISTENT_THERMAL_SOURCE` | STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indi... |
| `dbfb2b7feaae8ff1...` | 23.7644 | 86.4010 | `INDIA_OTHER_THERMAL_SOURCES_2025` | 1.99 | `Tier A` | `Tier B` | `PERSISTENT_THERMAL_SOURCE` | STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indi... |
| `fadc23f1a389946a...` | 23.7809 | 86.3933 | `INDIA_OTHER_THERMAL_SOURCES_2025` | 1.97 | `Tier A` | `Tier B` | `PERSISTENT_THERMAL_SOURCE` | STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indi... |
| `b3eb081293064a18...` | 23.7812 | 86.3955 | `INDIA_OTHER_THERMAL_SOURCES_2025` | 1.74 | `Tier A` | `Tier B` | `PERSISTENT_THERMAL_SOURCE` | STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indi... |
| `80345a4326442e2f...` | 23.7807 | 86.3935 | `INDIA_OTHER_THERMAL_SOURCES_2025` | 1.94 | `Tier A` | `Tier B` | `PERSISTENT_THERMAL_SOURCE` | STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indi... |
| `2fe718883ca0e83d...` | 23.7637 | 86.4030 | `INDIA_OTHER_THERMAL_SOURCES_2025` | 1.95 | `Tier A` | `Tier B` | `PERSISTENT_THERMAL_SOURCE` | STATIC_SOURCE_PROXIMITY: Proximity to colliery boundary indi... |
