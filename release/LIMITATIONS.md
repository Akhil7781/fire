# DS08 System Limitations & Operational Boundaries

Scientific honesty and operational safety require transparent documentation of system boundaries, domain assumptions, and failure modes.

---

## 1. Upstream Satellite Detection Reliance

- **Thermal Source Attribution $\neq$ Active Fire Detection:**
  The DS08 system is strictly a **source attribution engine**, not an active fire detection model. It does not ingest raw multispectral imagery to detect thermal anomalies from scratch; it ingests detections flagged upstream by NASA FIRMS (VIIRS 375m and MODIS 1km active fire algorithms).
- **Missed Detections:**
  If a genuine fire is obscured by heavy cloud cover, thick convective storm clouds, dense smoke plumes, or heavy forest canopy during a satellite overpass, NASA FIRMS will generate no detection sounding, and DS08 will receive no alert to attribute.

---

## 2. Spatial Resolution & Facility Alignment

- **Satellite Nadir vs Off-Nadir Footprints:**
  VIIRS I-band sensors have an optimal nadir ground sampling distance of approximately 375 meters, stretching to ~750 meters towards orbit swath edges. MODIS pixels are 1 km at nadir.
- **Centroid Offsets:**
  The estimated thermal centroid of a large multi-point fire represents the radiance-weighted center of pixel soundings. In large petrochemical hubs or sprawling industrial parks (several km wide), a fire located at the eastern edge may register 1–2 km from the administrative centroid of the facility listed in the database.
- **Proximity Ambiguity:**
  An agricultural field fire burning adjacent to an industrial fence line may register high industrial proximity features. In such edge cases, the system relies on the balance of thermal radiative power, spatial spread rate, and land-cover biomes to disambiguate.

---

## 3. Temporal Latency & Orbital Passes

- **Overpass Frequency:**
  Sun-synchronous polar-orbiting satellites (NOAA-20, Suomi-NPP) provide 2 daytime and 2 nighttime overpasses per 24-hour cycle over equatorial and subtropical India.
- **Near-Real-Time (NRT) Latency:**
  The elapsed time from actual satellite ground overpass to NASA EOSDIS data delivery via FIRMS API is approximately 1 to 3 hours under standard operational conditions. The model itself adds $< 10$ milliseconds of processing time once data arrives.

---

## 4. Geographic & Domain Adaptation Boundaries

- **Tuned for Indian Subcontinent:**
  The ecoregion biome classifiers (Western Ghats, Central Highlands, Northeast, Himalayas, Indo-Gangetic Plain) and industrial facility registry (`industrial_facility_database.json`) are specific to India.
- **Transfer to Other Continents:**
  Deploying DS08 in North America, Europe, Australia, or Southeast Asia requires updating:
  1. The industrial facility registry to local industrial infrastructure databases.
  2. The ecoregion definitions to local ecological and agricultural fire regimes.
  3. Pre-alert historical FIRMS recurrence archives for that region.

---

## 5. Persistent Thermal Sources & Class Imbalance

- **Sample Scarcity in Validation:**
  In independent test sets, persistent thermal sources (continuous refinery flares, coal seam fires, brick kilns) have smaller sample sizes ($N=10$ in the frozen 2026 cohort) compared to widespread acute agricultural fires.
- **Sensitivity to Historical Depth:**
  The registry-free recurrence mechanism relies on having at least 6–12 months of pre-alert FIRMS history available in the local archive. If historical archives for a newly monitored coordinate are incomplete, persistent sources may be attributed as acute events due to lack of historical evidence.

---

## 6. Regulatory & Operational Disclaimer

The DS08 system is designed as an automated decision-support tool. Attribution outputs, probabilities, and generated explanations should be evaluated in conjunction with local fire service dispatches, ground inspections, and meteorological data before initiating regulatory penalties or major emergency responses.
