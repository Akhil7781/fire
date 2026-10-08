# STAGE 8.18A — ACUTE INDUSTRIAL FIRE SAMPLING UNIT SPECIFICATION
**Hierarchical Entity Distinction: Incidents, Scenes, and Chips**

- **Document Version:** 2.0.0
- **Stage:** Stage 8.18A — Protocol Review & Sign-Off Preparation
- **Status:** **REVISED SPECIFICATION — LOCKED FOR HUMAN REVIEW**
- **Target Stratum:** Stratum 1 (Acute Industrial Fires, Target: $N = 35$ Primary Chips)

---

## 1. Problem Statement & Audit Finding

In Stage 8.18, the sampling protocol specified a target of 35 chips for Stratum 1 (Acute Industrial Fires), but lacked formal distinction between:
1. Physical fire disasters/events on the ground.
2. Sentinel-2 satellite overpass scenes.
3. Extracted image chips.

**Risk of Statistical Violation (Pseudo-Replication & Data Leakage):**
Treating multiple image chips extracted from the same physical industrial fire incident—either through spatial tiling, jittering, or multi-temporal revisits of the same facility disaster—as independent samples would artificially inflate dataset size and statistical power (pseudo-replication). Crucially, in machine learning evaluation (cross-validation or train/val/test splits), separating chips from the same incident across training and evaluation splits would cause catastrophic spatial-temporal data leakage.

---

## 2. Hierarchical Entity Architecture

Stage 8.18A establishes a strict three-tier entity hierarchy:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. INCIDENT (Primary Sampling Unit - PSU)                   │
│    Unique real-world industrial disaster event on ground     │
│    ID: incident_id (e.g., IND_2025_GUJ_ANAND_CHEM_01)        │
└──────────────────────────────┬──────────────────────────────┘
                               │ 1-to-Many
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. ACQUISITION SCENE (Observation Platform Unit)            │
│    Distinct Sentinel-2 L2A orbital overpass (MGRS tile)     │
│    ID: scene_id (e.g., S2A_MSIL2A_20250412T053641_T43QDA)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ 1-to-Many
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. IMAGE CHIP (Analytical & Model Input Unit)               │
│    Cropped spatial sub-window (e.g., 5.12 km x 5.12 km)     │
│    ID: chip_id (e.g., DS08_IND_001_ACTIVE)                  │
└─────────────────────────────────────────────────────────────┘
```

### Definitions:

1. **Incident (`incident_id`):**
   - The **Primary Sampling Unit (PSU)** for Stratum 1.
   - Defined as a discrete, verifiable, real-world industrial thermal/combustion event occurring at a specific geographic facility or industrial estate within a documented temporal start and end window.
   - Must be corroborated by external, non-FIRMS authoritative evidence (e.g., NDMA, State Disaster Management Authority, State Pollution Control Board, industrial safety inspectorate reports, or verified press/incident logs).
   - Invariant: **Each of the 35 target Stratum 1 allocations must originate from a distinct, unique `incident_id`**.

2. **Acquisition Scene (`scene_id`):**
   - The authoritative Sentinel-2 Level-2A product downloaded from Copernicus Data Space Ecosystem (CDSE).
   - Encapsulates exact sensing timestamp (UTC), orbit path, MGRS tile, sun angles, and atmospheric correction metadata.
   - A single incident may have multiple scenes (e.g., pre-fire baseline, active-combustion overpass, post-fire burn assessment).

3. **Image Chip (`chip_id`):**
   - The extracted $512 \times 512$ pixel ($5.12 \times 5.12\text{ km}$ at 10m Ground Sample Distance) or $1024 \times 1024$ pixel analytical window.
   - For each incident, exactly **one** canonical primary chip (`is_primary_chip = True`) represents the incident in the 250-chip benchmark dataset.
   - Secondary chips (e.g., multi-temporal sequences of the same incident) may be archived for supplementary research, but **do not count toward the 35 target incident quota**.

---

## 3. Invariants & Rules Against Pseudo-Replication

To preserve scientific rigor, the sampling pipeline enforces the following invariants:

### Rule 1: One Incident = One Primary Chip in Quota
- A dataset target of 35 acute industrial fires requires **35 distinct physical incidents** across unique facilities and dates.
- Extracting 5 chips from 7 industrial accidents is strictly prohibited as a fulfillment of the 35-sample quota.

### Rule 2: Multi-Temporal & Multi-Chip Grouping Invariant
- If secondary chips (e.g., baseline pre-event chips, post-event cooling chips, or adjacent spatial crops) are generated for a given incident, all such chips **must inherit the identical `incident_id` and `group_id`**.
- In cross-validation split generation (e.g., 5-fold CV), all chips sharing the same `incident_id` must be deterministically allocated to the **exact same fold**. Under no circumstances may chips from the same incident appear across both training and validation/test folds.

### Rule 3: Spatial Independence Distance
- Two candidate industrial fire incidents occurring at the same industrial park or facility cluster within 90 days must be evaluated for causal independence.
- If two thermal hotspots fall within **5 km** of each other and within **7 days**, they are classified as part of the **same physical incident** (`incident_id`) unless distinct facility operator accident reports prove independent causes.

---

## 4. Metadata Schema for Industrial Fire Records

Every candidate industrial fire entry must populate the following structured metadata fields before inclusion in the sampling manifest:

```json
{
  "chip_id": "DS08_IND_001_ACTIVE",
  "is_primary_chip": true,
  "incident_metadata": {
    "incident_id": "IND_2025_GUJ_ANAND_CHEM_01",
    "facility_name": "ABC Agro-Chemicals Ltd",
    "facility_type": "Chemical Manufacturing / Storage",
    "industrial_sector": "Chemical & Petrochemical",
    "latitude_center": 22.5641,
    "longitude_center": 72.9284,
    "incident_start_utc": "2025-04-12T02:30:00Z",
    "incident_containment_utc": "2025-04-12T18:00:00Z",
    "corroboration_source": "Gujarat State Disaster Management Authority / NDTV News / Local Fire Bureau Report",
    "corroboration_url_or_ref": "GSDMA-REP-2025-04-129"
  },
  "scene_metadata": {
    "scene_id": "S2A_MSIL2A_20250412T053641_N0500_R062_T43QDA_20250412T091522",
    "satellite": "Sentinel-2A",
    "mgrs_tile": "43QDA",
    "sensing_time_utc": "2025-04-12T05:36:41Z",
    "cloud_cover_percentage": 1.24
  },
  "temporal_relationship": {
    "temporal_phase": "ACTIVE_COMBUSTION",
    "delta_t_hours": 3.11,
    "matching_tier": "TIER_1_COINCIDENT"
  },
  "split_invariants": {
    "group_id": "GROUP_IND_2025_GUJ_ANAND_CHEM_01",
    "assigned_fold": null
  }
}
```

---

## 5. Summary of Protocol Enhancements

| Feature | Stage 8.18 (Original) | Stage 8.18A (Revised) |
| :--- | :--- | :--- |
| **Primary Unit** | Ambiguous ("35 chips") | Explicit: 35 Unique Ground Incidents (`incident_id`) |
| **Multi-Chip Rule** | Unspecified | Strictly prohibited from counting toward quota; secondary chips flagged `is_primary_chip = false` |
| **Split Grouping** | Spatial distance heuristic only | Strict incident grouping: all chips with same `incident_id` bound to identical CV fold |
| **Corroboration** | FIRMS detection encouraged | Mandatory external ground truth (regulatory, disaster authority, or news report) |
