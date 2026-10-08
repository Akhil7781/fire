# Label Construction Specification: Satellite Thermal Anomaly Classification

## 1. Executive Summary & Design Principles

This specification defines the ground-truth label architecture, reference data integration, spatial-temporal matching protocol, and confidence hierarchy for AI-based classification of satellite thermal anomalies in India for 2025.

### Foundational Labeling Invariants
1. **Strict Data Decoupling**: Ground-truth labels ($y_i$) must be derived exclusively from independent reference evidence. Under no circumstances may labels be derived from FIRMS predictive attributes ($\text{bright\_ti4}$, $\Delta T$, $\text{frp}$, $\text{frp\_log1p}$, sensor heuristics `type`, or model predictions).
2. **Anti-Proximity Rule**: Spatial proximity to an industrial park, refinery, or factory polygon does **NOT** constitute an industrial fire label. Proximity without incident confirmation yields an *unlabelled* or *ambiguous* designation.
3. **No Unjustified Hard Thresholds**: All spatial tolerances, temporal windows, and confidence weights are declared as explicit, parameteric configuration variables requiring empirical sensitivity validation.
4. **Hierarchy-Based Supervised Inclusion**: Only Tier A (*Confirmed*) and Tier B (*Probable*) labels enter the supervised / semi-supervised learning targets (e.g. Deep SAD, TCN). Tier C (*Ambiguous*) and Tier D (*Unlabelled*) remain in the unlabelled background distribution ($y_i = 0$).

---

## 2. Target Class Definitions

| Class Code | Class Name | Definition & Inclusion Criteria | Exclusion Criteria |
|---|---|---|---|
| **Class 1** | **Industrial Fire** | Unintended, accidental fires, explosions, or thermal runaway events occurring within industrial facilities, chemical plants, petroleum refineries, manufacturing units, warehouses, or hazardous waste sites. | Routine operational gas flaring, normal furnace/kiln heat emissions, surrounding vegetation burns. |
| **Class 2** | **Forest Fire** | Wildfires, forest surface fires, and uncontained canopy blazes occurring in natural or reserved forest lands, national parks, and wildlife sanctuaries. | Controlled agricultural residue burning on adjacent farmland, permanent deforestation clearing. |
| **Class 3** | **Agricultural Fire** | Open-field burning of post-harvest crop residue (e.g., paddy stubble in Oct–Nov, wheat stubble in Apr–May) on cultivated agricultural parcels. | Forest fires, industrial waste burning, brick kiln firing. |
| **Class 4** | **Other Thermal Source** | Non-disaster thermal phenomena: persistent operational gas flaring, continuous coal seam smoldering, active brick kilns, volcanic activity (Barren Island), and normal thermal power plant cooling/flue heat. | Accidental industrial fires, agricultural stubble burns, forest fires. |

---

## 3. Label Hierarchy & Supervised Inclusion Policy

Every detection $i$ in the master corpus is assigned a label record $(y_i, c_i, s_i)$ where $y_i \in \{1, 2, 3, 4, 0\}$, $c_i \in \{\text{Tier A}, \text{Tier B}, \text{Tier C}, \text{Tier D}\}$, and $s_i$ records the provenance source string.

```
                  ┌────────────────────────────────────────┐
                  │ Candidate Thermal Anomaly (FIRMS 2025) │
                  └───────────────────┬────────────────────┘
                                      │
           ┌──────────────────────────┴──────────────────────────┐
           ▼                                                     ▼
┌───────────────────────────┐                         ┌────────────────────┐
│ Independent Match Found   │                         │ No Match Found     │
└──────────┬────────────────┘                         └─────────┬──────────┘
           │                                                    │
     ┌─────┴────────────────────────────────┐                   │
     ▼                                      ▼                   ▼
┌──────────────┐                     ┌──────────────┐   ┌──────────────┐
│  Tier A      │                     │  Tier B      │   │  Tier D      │
│  Confirmed   │                     │  Probable    │   │  Unlabelled  │
│  (c_i = 1.0) │                     │  (c_i >= 0.7)│   │  (y_i = 0)   │
└──────┬───────┘                     └──────┬───────┘   └──────────────┘
       │                                    │
       └──────────────────┬─────────────────┘
                          │
                          ▼
            ┌───────────────────────────┐
            │ Supervised Target Pool    │
            │ (Deep SAD / TCN Learning) │
            └───────────────────────────┘
```

### Hierarchy Tiers:
- **Tier A: Confirmed Label ($c_i = 1.00$)**:
  - Direct statutory, official regulatory, or multi-spectral optical imagery confirmation of a specific event at the exact location and date.
  - *Action*: Included in supervised training/evaluation target pool.
- **Tier B: Probable / Weak Label ($0.70 \le c_i < 1.00$)**:
  - Independent corroboration from regional news aggregators, high-density cluster patterns, or spatial-temporal overlay with validated domain masks (e.g. SentinelKilnDB, World Bank Flaring Tracker).
  - *Action*: Included in weak-supervision / semi-supervised loss functions with instance weighting $c_i$.
- **Tier C: Ambiguous ($0.30 \le c_i < 0.70$)**:
  - Conflicting evidence between multiple reference sources (e.g., news reports industrial fire but satellite shows agricultural burn scar on adjacent field).
  - *Action*: Excluded from supervised targets; held out in an audit pool.
- **Tier D: Unlabelled ($y_i = 0, c_i = 0.00$)**:
  - Detections with no matching independent reference evidence.
  - *Action*: Constitutes the unlabelled background distribution for Deep SAD semi-supervised anomaly detection.

---

## 4. Ground-Truth Data Sourcing Strategy for Industrial Fires

Because industrial fires are rare (~150 to 300 major reportable incidents/year in India) and spatially confounded by industrial estate operations, a **4-Pillar Evidence Fusion Protocol** is required:

1. **Statutory Corporate Announcements (SEBI Regulation 30)**: Listed Indian industrial firms are legally required to disclose material operational disruptions from fires within 24 hours on BSE/NSE exchanges.
2. **Quasi-Judicial & Environmental Orders (NGT & SPCBs)**: Public closure directions, show-cause notices, and joint inspection committee reports from State Pollution Control Boards and National Green Tribunal proceedings.
3. **Multi-Source News Event Mining (GDELT & Regional News APIs)**: Automated extraction of industrial incident reports with geocodable facility names, district names, and timestamps.
4. **Optical Satellite Damage Verification (Sentinel-2 / PlanetScope)**: Differenced Normalized Burn Ratio ($\Delta\text{NBR}$) and Short-Wave Infrared (SWIR) reflectance anomalies before and after reported incident dates to confirm physical structural burn scars.

---

## 5. Feasibility Assessment of the Four-Class Problem

Based on independent reference data availability in India for 2025:

- **Class 2 (Forest Fire)**: **Fully Supportable** via FSI FAST 3.0, Van Agni, MODIS MCD64A1 v6.1, and Sentinel-2 dNBR. High volume of Tier A labels.
- **Class 3 (Agricultural Fire)**: **Fully Supportable** via ICAR-IARI CREAMS daily bulletins, PRSC CRBIMS, HARSAC, and Sentinel-2 HLS 10m burn scars. High volume of Tier A/B labels.
- **Class 4 (Other Thermal Source)**: **Fully Supportable** via SentinelKilnDB (62,671 brick kilns), World Bank GGFR gas flaring catalog, GSI Barren Island volcanic reports, CMPDI coal fire shapefiles, and GEM power plant databases. High volume of Tier A/B labels.
- **Class 1 (Industrial Fire)**: **Requires Weak Supervision & Human-in-the-Loop Validation**. While statutory and news-mined records yield ~200–500 confirmed events/year, automated matching alone carries spatial precision risk.

### Implementation Readiness Verdict:
**READY FOR LABEL CONSTRUCTION WITH WEAK SUPERVISION FOR INDUSTRIAL CLASS**
