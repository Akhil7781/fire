# STAGE 8.18 — DS08 DATASET EXPANSION: SAMPLING PROTOCOL
**Statistically Defensible Stratified Sampling Framework for Expanding DS08 Toward ~250 Sentinel-2 Chips**

- **Document Version:** 1.0.0
- **Stage:** Stage 8.18 — DS08 Dataset Expansion Planning
- **Status:** **DRAFT SPECIFICATION — LOCKED FOR HUMAN REVIEW (NO BULK ACQUISITION INITIATED)**
- **Target Dataset Size:** $N = 250$ Level-2A Sentinel-2 Chips ($512 \times 512$ pixels, 10m GSD)
- **Authoritative Baseline:** DS08 Pilot v1.0.0 ($n = 15$ audited chips, `ds08_pilot_v1`)

---

## 1. Executive Objectives & Core Scientific Principles

The objective of Stage 8.18 is to establish a rigorous, empirically grounded protocol for scaling the DS08 Sentinel-2 optical dataset from its 15-chip pilot cohort to approximately 250 real Sentinel-2 Level-2A chips across India for the calendar year 2025.

### Core Scientific Principles:
1. **Zero Synthetic Data:** All imagery must originate from actual Copernicus Sentinel-2 Level-2A acquisitions over India. No synthetic, diffusion-generated, or artificially blended imagery is permitted.
2. **Empirical Class Scarcity Realism:** Acute industrial fire disasters are inherently rare events in satellite imagery. The sampling framework must **NOT** fabricate an artificial 1:1:1:1 class balance by mislabeling routine non-fire industrial infrastructure or agricultural burns as "industrial fires."
3. **Multi-Axis Separation:**
   - **Target Class:** What type of combustion or thermal event is occurring (`Industrial Fire`, `Forest Fire`, `Agricultural Fire`, `Other Thermal Source`, `NO_VISIBLE_TARGET`).
   - **Land-Cover Context:** What surface features surround the area (`INDUSTRIAL_INFRASTRUCTURE`, `FOREST_CANOPY`, `CROPLAND_PARCEL`).
   - **Visual Evidence:** What physical features are directly observed (`DIRECT_FIRE_VISIBLE`, `SMOKE_VISIBLE`, `BURN_SCAR_VISIBLE`, `NO_CLEAR_VISUAL_EVIDENCE`).
4. **Benchmark Preservation:** The 15 audited pilot chips (`ds08_pilot_v1`) must remain frozen as a permanent calibration/benchmark cohort and must not be split into random training folds.

---

## 2. Target Classes & Semantic Definitions

The sampling protocol categorizes candidate chips across five mutually exclusive target observation statuses:

| Class ID | Target Class | Definition & Physical Criteria | Primary Confirmatory Evidence |
| :---: | :--- | :--- | :--- |
| **1** | **Industrial Fire** | Acute, destructive fire or explosion occurring within or directly impacting industrial facilities, chemical plants, refineries, warehouses, or storage tanks. | Co-occurrence of localized high-temperature flame/hotspot AND heavy industrial smoke plume emanating directly from industrial infrastructure. |
| **2** | **Forest Fire** | Wildfire, surface fire, or canopy blaze occurring within natural forests, woodlands, or scrubland reserves. | Diffuse or expansive burn scar in continuous woodland/tree canopy with active flaming front or drifting biomass smoke. |
| **3** | **Agricultural Fire** | Open-field crop residue or stubble burning occurring on cultivated cropland parcels. | Geometric, field-bounded blackening or localized low-intensity smoke plumes drifting over furrowed agricultural plots. |
| **4** | **Other Thermal Source** | Persistent, non-emergency, or non-biomass thermal sources (continuous gas flaring, coal seam fires, brick kilns, thermal power plant cooling discharge). | Known persistent thermal emitter infrastructure operating under planned conditions; distinct from acute accidental fires. |
| **0** | **Negative / No Visible Target** | Valid Sentinel-2 imagery where no active fire, smoke plume, fresh burn scar, or abnormal thermal emission is discernible. | Clear surface visibility with `NO_CLEAR_VISUAL_EVIDENCE`; essential for training false-positive rejection. |

> [!CRITICAL]
> **Proximity Attribution Ban:**  
> A fire located in an agricultural field or forest patch adjacent to a factory perimeter must **NEVER** be classified as an `Industrial Fire` unless physical origin within the facility is conclusively documented.

---

## 3. Sampling Strata & Proposed Allocation Table ($N = 250$)

To balance class representation, geographical diversity across India, and robust negative-control representation, the 250-chip target is partitioned into **seven explicit sampling strata**:

| Stratum ID | Stratum Name | Description | Proposed Allocation | Min. Required | Primary Selection Source |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **STR-1** | **Confirmed Acute Industrial Fires** | Rare industrial fire incidents with external official or multi-source news verification in 2025 | **15 chips** | 10 chips | `india_industrial_incidents_2025_normalized.parquet` & state disaster records |
| **STR-2** | **Persistent Non-Biomass Thermal Sources** | Continuous gas flaring, active coal seam fires, brick kiln clusters, thermal power stations | **30 chips** | 20 chips | `india_other_thermal_sources_2025_normalized.parquet`, World Bank GGFR, SentinelKilnDB |
| **STR-3** | **Active Forest Wildfires** | Confirmed forest fires across diverse biomes (Western Ghats, Central forests, Northeast, Himalayas) | **55 chips** | 45 chips | `fsi_van_agni_lff_2025_normalized.parquet`, Global Fire Atlas, MODIS MCD64A1 |
| **STR-4** | **Agricultural Crop Residue Burns** | Stubble burning across Rabi (March–April) and Kharif (October–November) agricultural cycles | **55 chips** | 45 chips | `icar_iari_creams_2025_normalized.parquet`, CREAMS Punjab/Haryana/UP registries |
| **STR-5** | **Industrial Negative Controls** | Major refineries, chemical zones, and power plants under normal, clear, non-burning operation | **40 chips** | 30 chips | OSM industrial polygons, CEA thermal catalog, verified non-incident days |
| **STR-6** | **Natural & Agricultural Negative Controls** | Clear forest tracts, fallow agricultural lands, and cloud-shadow edge cases with FIRMS noise | **40 chips** | 30 chips | FIRMS low-confidence detections, false alarm coordinates, cloud-edge scenes |
| **STR-7** | **Pilot Benchmark Cohort** | The frozen, audited 15-chip pilot dataset (`ds08_pilot_v1`) | **15 chips** | 15 chips | `data/reference/ds08/packages/ds08_pilot_v1/manifest.json` |
| **TOTAL** | **Comprehensive DS08 Dataset** | **Pan-India Optical Fire Adaptation Dataset** | **250 chips** | **195 chips** | **Fully Audited Multi-Source Pool** |

---

## 4. Geographic Stratification Across India

To prevent regional over-representation (e.g., Punjab agricultural dominance or Central India forest dominance), sampling across strata STR-2 through STR-6 must enforce regional minimum quotas across India's five major geographic zones:

| Geographic Region | Defining Latitude/Longitude | Target Allocation (%) | Target Count ($N=250$) | Key Landscape & Combustion Regimes |
| :--- | :--- | :---: | :---: | :--- |
| **NORTH** | $\text{Lat} \ge 27.0^\circ\text{N}$ | **22%** | **55 chips** | Indo-Gangetic stubble burning, Himalayan pine forest fires, NCR brick kilns |
| **CENTRAL** | $16.0^\circ \le \text{Lat} < 27.0^\circ\text{N}, 75.0^\circ \le \text{Lon} < 83.0^\circ\text{E}$ | **24%** | **60 chips** | Deciduous dry forest fires (MP/Chhattisgarh), Singrauli coal/thermal belt |
| **SOUTH** | $\text{Lat} < 16.0^\circ\text{N}$ | **18%** | **45 chips** | Western Ghats evergreen fires, Deccan plateau agriculture, coastal refineries |
| **EAST** | $\text{Lon} \ge 83.0^\circ\text{E}$ | **20%** | **50 chips** | Jharia/Raniganj coal seam fires, Northeast shifting cultivation (jhum), tea gardens |
| **WEST** | $\text{Lon} < 75.0^\circ\text{E}, \text{Lat} < 27.0^\circ\text{N}$ | **16%** | **40 chips** | Gujarat petrochemical corridor (Hazira, Jamnagar), arid scrub fires, coastal ports |

---

## 5. Temporal & Seasonal Stratification

To capture the physical variations in vegetation phenology, soil moisture, and atmospheric transparency across the Indian subcontinent:
1. **Pre-Monsoon Dry Season (March – May 2025):** $\approx 50\%$ ($125$ chips). Peak period for forest fires (Central/Northeast) and Rabi harvest burning (North/Central).
2. **Post-Monsoon Autumn Burning (October – November 2025):** $\approx 30\%$ ($75$ chips). Peak period for Northern India (Punjab/Haryana) paddy straw stubble burning.
3. **Winter Dry Window (December 2024 – February 2025):** $\approx 20\%$ ($50$ chips). Optimal atmospheric clarity for baseline industrial infrastructure, active brick kilns, and continuous flaring.
4. **Monsoon Cloud Outflow (June – September):** Excluded due to pervasive regional cloud cover ($> 80\%$) and minimal open fire activity.

---

## 6. Contingency Plans for Scarcity

### Contingency for Stratum 1 (Acute Industrial Fires):
- **Problem:** If fewer than 15 confirmed acute industrial fire events in India during 2025 yield cloud-free Sentinel-2 overpasses within $\pm 24\text{ hours}$.
- **Approved Protocol:**
  1. Exhaust all 12 verified events in `india_industrial_incidents_2025_normalized.parquet`.
  2. If clear S2 imagery is available for only $k < 15$ events (e.g., $k = 8$), **DO NOT FABRICATE** additional events or mislabel non-fire factories.
  3. Reallocate remaining $15 - k$ slots to **Stratum 2** (`Other Thermal Source` - high-temperature industrial flaring and coal seam fires) while clearly tagging them as `Other Thermal Source`.
  4. Document the exact industrial fire sample count in the dataset release notes as an empirical upper bound.

---

## 7. Next Actions Requiring Human Sign-Off

Before proceeding to chip acquisition:
- [ ] Review and approve the 7-stratum allocation table.
- [ ] Approve the regional minimum quotas (North 55, Central 60, South 45, East 50, West 40).
- [ ] Formalize the contingency reallocation rule for acute industrial fire scarcity.
