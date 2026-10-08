# Stage 8.35 - Formal Class Definition & Taxonomy Specification

## Purpose
This document establishes the rigorous physical, spectral, operational, and evidence definitions for the 4 target classes in DS08 thermal-source attribution.

---

## 1. Class Taxonomy & Operational Definitions

```
Target Classes:
├── Class 0: Industrial Fire (Acute Industrial Emergency)
├── Class 1: Forest Fire (Acute Wildland Biomass Fire)
├── Class 2: Agricultural Fire (Acute Crop Residue / Stubble Burning)
└── Class 3: Persistent Thermal Source (Routine Non-Acute Thermal Emission)
```

### Class 0: Industrial Fire (`class_id = 0`)
- **Physical Definition:** Acute, unscheduled, accidental combustion of industrial chemicals, hydrocarbons, manufactured goods, or infrastructure within the premises of an industrial plant, manufacturing unit, warehouse, storage terminal, refinery, or industrial estate.
- **Temporal Profile:** Sudden acute onset ($t_0$); typical duration 6–48 hours; sudden high surge in Fire Radiative Power (FRP) and thermal contrast ($\Delta T_{I4-I5}$) well above any historical facility baseline.
- **Historical Recurrence Profile:** **Zero or near-zero historical FIRMS thermal detections** in the preceding 3–5 years at that exact coordinate ($t \le t_0 - 7$ days).
- **Spatial Profile:** Located within $\le 1.0$ km of a documented industrial facility polygon or centroid.
- **Exclusion Criteria:** Regular scheduled flare stack operations, routine boiler exhaust, or furnace emissions without incident.

### Class 1: Forest Fire (`class_id = 1`)
- **Physical Definition:** Open-air surface, ground, or crown combustion of wildland vegetation (trees, scrub, understory, litter) in reserved forests, protected sanctuaries, national parks, or forested hill ranges.
- **Temporal Profile:** Acute seasonal fire (peak dry season February–May); multi-day progression (12–72 hours); elevated nighttime persistence compared to agricultural fires.
- **Land Cover / Ecological Profile:** High tree canopy cover (`forest_biome_score` $\ge 0.50$); located in designated forest beats/ranges; distance to industrial facilities typically $> 5.0$ km.
- **Historical Recurrence Profile:** Variable recurrence (infrequent to biennial), but diffuse across ridges rather than pinpoint spatial recurrence ($< 100$ m) observed in industrial flare stacks.

### Class 2: Agricultural Fire (`class_id = 2`)
- **Physical Definition:** Intentional, controlled post-harvest combustion of crop residues (paddy stubble, wheat straw, sugarcane trash, cotton stalks) on cultivated agricultural field parcels.
- **Temporal Profile:** Strictly daytime combustion (almost zero night detections); very short duration per parcel (2–6 hours); strong bimodal harvest seasonality (Rabi: April–May; Kharif: October–November; Peninsular sugarcane/paddy: January–March).
- **Land Cover / Ecological Profile:** High cropland fraction (`agri_heartland_score` $\ge 0.50$); cultivated parcel boundaries visible; distance to industrial facilities $> 3.0$ km.
- **Historical Recurrence Profile:** Low localized point recurrence (stubble fires shift between neighboring fields from season to season; zero multi-year pinpoint recurrence at $< 500$ m).

### Class 3: Persistent Thermal Source (`class_id = 3`)
- **Physical Definition:** Scheduled, continuous, or chronic high-temperature thermal emissions arising from operational industrial infrastructure or geological combustion:
  1. Hydrocarbon gas flaring (refinery flare stacks, oil/gas gathering stations, offshore platforms).
  2. Subterranean or surface coalfield fires (Jharia, Raniganj, Singrauli open-cast coal seam smoldering).
  3. Metallurgical operations (steel mill slag heaps, blast furnace taps).
  4. High-capacity thermal power station boilers and ash handling.
  5. Brick kilns (FCBTK / Zigzag firing zones).
  6. Natural active volcanism (Barren Island).
- **Temporal Profile:** Chronic thermal anomalies detected repeatedly across multiple calendar months and multiple years.
- **Historical Recurrence Profile:** **High recurrence count** ($> 10$ historical FIRMS detections spanning $> 90$ active days in pre-alert archive $t \le t_0 - 7$ days).
- **Spatial Profile:** Pinpoint stationary thermal centroid ($< 0.5$ km spatial spread over years).
- **Operational Meaning:** In real-time fire dispatching, Class 3 represents **routine, non-emergency thermal emissions** that do NOT require emergency fire brigade deployment, preventing costly false alarms at industrial complexes.

---

## 2. Evaluation of "Other / Persistent": Single Class vs Split?

### Question:
Does combining "Persistent Thermal Sources" with "Other Thermal Sources" create problematic semantic heterogeneity?

### Evidence-Based Finding:
1. **Catalog Composition:** In the audited dataset, 100% of Class 3 events belong to documented physical persistent emitters (flaring stacks: 45%, coalfield combustion: 38%, thermal power/metallurgical: 15%, volcano: 2%). There are **zero vague, unexplained 'mystery' anomalies**.
2. **Operational Coherence:** From an operational dispatch viewpoint, the system's mission is to separate:
   - **Emergency Acute Industrial Incidents** (Class 0 $\implies$ Dispatched)
   - **Emergency Wildland Wildfires** (Class 1 $\implies$ Dispatched)
   - **Agricultural Field Burning** (Class 2 $\implies$ Monitored / Enforced)
   - **Routine Persistent Sources** (Class 3 $\implies$ Suppressed / Non-emergency)
3. **Decision:** The class remains **UNIFIED as Class 3: Persistent Thermal Source**. Splitting it into sub-categories (e.g. flare vs coal) would fragment limited training support ($N=42$) without operational benefit.

---

## 3. Ambiguity & Conflict Resolution Policy

| Ambiguity Scenario | Resolution Protocol |
|:---|:---|
| **Thermal anomaly $\le 1$ km of industrial facility** | Examine pre-alert FIRMS history ($t \le t_0 - 7$ d). If historic active days $\ge 10$ and historic detections $\ge 10$, label **Persistent**. If historic detections $\le 2$ and sudden acute FRP surge, label **Industrial Fire**. |
| **Thermal anomaly in mixed agro-forestry margin** | Examine land cover scores. If `agri_heartland_score` $> 0.60$ and date aligns with regional harvest window, label **Agricultural**. If `forest_biome_score` $> 0.60$ inside designated forest beat, label **Forest**. If indeterminate, flag as `AMBIGUOUS`. |
| **High recurrence near agricultural village (Brick Kiln)** | If pinpoint recurrence $> 90$ days across multiple years in rural parcel, label **Persistent (Brick Kiln)** rather than Agricultural. |
