# GROUND TRUTH REFERENCE DATASETS & METHODOLOGY FOR INDUSTRIAL FIRES IN INDIA (2025)

## 1. Executive Summary & Ground-Truthing Architecture

Industrial fires represent the most difficult category of thermal anomalies to validate independently. The fundamental obstacle is **spatial false-correlation**:
> **CRITICAL RULE**: Spatial co-location or proximity to an industrial polygon/boundary alone is **NOT** evidence of an industrial fire. 

Industrial parks in India (MIDCs in Maharashtra, GIDCs in Gujarat, SIPCOTs in Tamil Nadu, RIICOs in Rajasthan) routinely exhibit high thermal signatures, large metallic structures, and unpaved surrounding scrub. A naive spatial join between satellite thermal detections (MODIS/VIIRS) and industrial land parcels creates catastrophic false positives due to:
1. **Routine Operational Combustion**: Flare stacks, cupola furnaces, blast furnaces, rotary cement kilns, asphalt batching plants, and glass tanks emitting persistent infrared radiances ($1,200\text{–}2,000\text{ K}$).
2. **Peripheral Vegetation & Waste Burning**: Clearing dry brush, municipal solid waste heaps, or packaging debris in open vacant plots located *inside* industrial estates.
3. **Sensor Artifacts**: High solar reflectance off shiny corrugated tin/galvanized sheet factory roofs triggering false mid-infrared brightness temperatures.

To establish **irrefutable ground truth** for an industrial fire event in India for the year 2025, an event must be verified through a **Multi-Pillar Evidence Fusion Architecture**:
* **Pillar 1: Spatial Asset Prior** (OSM, IILB/DPIIT, PPAC) $\rightarrow$ Defines the facility boundary and operational sector.
* **Pillar 2: Confounder Filtering** (VIIRS Nightfire persistence, World Bank GGFR) $\rightarrow$ Subtracts persistent operational heat sources (flares, furnaces).
* **Pillar 3: Physical Event Corroboration** (VIIRS transient hotspot, Sentinel-2 SWIR/dNBR burn scar, SkySat/WorldView structural collapse/soot plumes) $\rightarrow$ Confirms physical fire dynamics.
* **Pillar 4: Statutory & Observational Ground Truth** (SEBI LODR Reg 30 disclosures, NGT Joint Committee reports, State DISH Form 24, SPCB show-cause notices, OISD/PNGRB alerts, verified news aggregators) $\rightarrow$ Confirms date, time, cause, and facility identity.

---

## 2. In-Depth Evaluation of the 14 Target Data Sources

---

### Source 1: National Disaster Management Authority (NDMA) / National Institute of Disaster Management (NIDM)
* **Provider**: National Disaster Management Authority (NDMA) & National Institute of Disaster Management (NIDM), Ministry of Home Affairs, Government of India.
* **Dataset / Product Name**: Chemical & Industrial Disaster Incident Case Studies, Post-Disaster Need Assessments (PDNA), and National Chemical Disaster Guidelines.
* **Geographic Coverage**: Pan-India.
* **Temporal Coverage & Reporting Latency**: Irregular / Ad-hoc. Latency is very high (6 to 24 months post-incident). Only catastrophic, multi-casualty events trigger dedicated reports.
* **Spatial Precision**: Site/facility-level in published case studies; broad district/state-level in policy reviews.
* **Access Method**: Public web download via `ndma.gov.in` and `nidm.gov.in` under "Publications / Case Studies / Knowledge Repository".
* **Licensing / Restrictions**: Open Government Data License (India); freely accessible for public research.
* **Incident Reports vs. Facility Locations**: Confirmed incident reports, but **only for major catastrophic incidents** (e.g., LG Polymers Vizag, Harda firecracker explosion).
* **Data Format**: Unstructured PDF reports, case study monographs, and training manuals.
* **Expected Events per Year in India**: 1 to 5 major events per year.
* **Ground-Truth Suitability**: **Very Low for broad 2025 pipeline labeling; High for forensic deep-dives of marquee disasters.** NDMA does not maintain a continuous operational registry of day-to-day industrial fires.

---

### Source 2: Ministry of Labour – Directorate General Factory Advice Service & Labour Institutes (DGFASLI)
* **Provider**: DGFASLI, Ministry of Labour and Employment, Government of India.
* **Dataset / Product Name**: Standard Reference Book on Occupational Safety and Health (OSH) in Factories, Docks, and Ports; Annual Returns on Fatal and Non-Fatal Factory Accidents.
* **Geographic Coverage**: Pan-India (compiled across 28 States and 8 UTs via Chief Inspectorates of Factories [CIF] / State DISH).
* **Temporal Coverage & Reporting Latency**: Annual historical statistics. **Severe latency of 18 to 36 months** (official consolidated data for 2024–2025 is not published until late 2026/2027; interim figures appear only via Lok Sabha/Rajya Sabha unstarred questions).
* **Spatial Precision**: State-level and broad industry sector-level (NIC codes) in published reports; establishment-level exists only in raw State CIF Form 24 filings.
* **Access Method**: `dgfasli.gov.in` and Parliament of India Q&A portal (`sansad.in/ls` / `sansad.in/rs`).
* **Licensing / Restrictions**: Public government data; free to cite.
* **Incident Reports vs. Facility Locations**: Confirmed incident aggregates (fatal and reportable non-fatal industrial injuries, explosions, and fires).
* **Data Format**: PDF annual statistical compendiums and tabular parliamentary responses.
* **Expected Events per Year in India**: ~800 to 1,200 fatal factory accidents across registered factories per year; approximately 150 to 250 involve fire, boiler explosions, or chemical deflagrations.
* **Ground-Truth Suitability**: **Moderate-to-Low for near-real-time 2025 labeling** due to latency and lack of publicly accessible GPS coordinates in the national release.

---

### Source 3: State Pollution Control Boards (SPCBs) / Central Pollution Control Board (CPCB)
* **Provider**: CPCB (Central) and 28 State PCBs (notably MPCB - Maharashtra, GPCB - Gujarat, TNPCB - Tamil Nadu, APPCB - Andhra Pradesh, UPPCB - Uttar Pradesh).
* **Dataset / Product Name**: Industrial Incident Investigation Reports, Show-Cause Notices, Directions under Section 31A of Air Act / Section 33A of Water Act, and Major Accident Hazard (MAH) Compliance Logs under MSIHC Rules 1989 / CAEPPR Rules 1996.
* **Geographic Coverage**: Pan-India (state-specific jurisdiction).
* **Temporal Coverage & Reporting Latency**: Continuous regulatory enforcement; latency of 3 days to 4 weeks after an incident occurs.
* **Spatial Precision**: Specific plant address, survey number, industrial estate phase, and frequently exact boundary geo-coordinates.
* **Access Method**: Regulatory board portals (e.g., MPCB `mpcb.gov.in`, GPCB `gpcb.gujarat.gov.in`), RTI applications, and submissions made to the National Green Tribunal (NGT) legal repository.
* **Licensing / Restrictions**: Public domain statutory notices / quasi-judicial administrative orders.
* **Incident Reports vs. Facility Locations**: **Confirmed incident reports.** Orders specify exact dates of fire, containment failures, environmental damage, and closure directions.
* **Data Format**: PDF administrative orders, minutes of board consent appraisal meetings, and inspection dossiers.
* **Expected Events per Year in India**: ~300 to 600 environmentally significant industrial fire/leak incidents per year nationwide.
* **Ground-Truth Suitability**: **High (Gold Standard for regulatory confirmation)**, especially for chemical, pharmaceutical, and hazardous waste processing hubs in Gujarat and Maharashtra.

---

### Source 4: CSIR-National Environmental Engineering Research Institute (NEERI)
* **Provider**: CSIR-NEERI, Ministry of Science and Technology, Government of India.
* **Dataset / Product Name**: Environmental Forensic Damage Assessment Reports, NGT Joint Expert Committee Technical Filings, and Site Remediation Studies.
* **Geographic Coverage**: Pan-India.
* **Temporal Coverage & Reporting Latency**: Commission-driven. Latency of 2 to 9 months post-incident.
* **Spatial Precision**: Sub-meter coordinate-level GIS mapping of facility footprint, chemical storage tanks, and contaminated soil/water perimeter.
* **Access Method**: Published in NGT court proceedings (`greentribunal.gov.in`) where NEERI scientists serve on court-mandated inquiry committees; select public executive summaries on `neeri.res.in`.
* **Licensing / Restrictions**: Judicial public record when filed in court; confidential commercial IP when undertaken as proprietary industrial consultancy.
* **Incident Reports vs. Facility Locations**: Confirmed incident investigations containing root-cause analysis, pre- and post-disaster satellite imagery, and chemical inventory burn estimates.
* **Data Format**: Highly detailed forensic PDF reports, multispectral maps, and chemical analytical tables.
* **Expected Events per Year in India**: 10 to 25 major industrial disaster investigations per year.
* **Ground-Truth Suitability**: **Extremely High quality, but low volume.** Indispensable for establishing indisputable forensic ground truth on major industrial catastrophes.

---

### Source 5: Indian News Aggregators & Real-Time Event Detectors
* **Provider**: GDELT Project (GDELT 2.0 Event Database / Translingual GKG), Event Registry, Google News RSS, Meltwater, and Indian national wire services (PTI, ANI, UNI).
* **Dataset / Product Name**: GDELT Global Knowledge Graph (`GKG 2.0`), Event Registry `event-stream`, and automated regional fire monitoring scrapers.
* **Geographic Coverage**: Pan-India across English, Hindi, Marathi, Gujarati, Tamil, Telugu, and other regional language sources.
* **Temporal Coverage & Reporting Latency**: Near-real-time (15 minutes to 3 hours from news break).
* **Spatial Precision**: Varies: Facility name + industrial estate name (e.g., "Amber Chemical, MIDC Phase II, Dombivli, Thane") $\rightarrow$ geocodable to polygon/building level ($<50\text{ m}$).
* **Access Method**: BigQuery (`gdelt-bq.gdeltv2.gkg`), Event Registry REST API (`eventregistry.org`), RSS feeds, Python scrapers.
* **Licensing / Restrictions**: GDELT is open data (CC-BY); Event Registry is commercial/freemium API; Google News RSS is free for non-automated bulk use.
* **Incident Reports vs. Facility Locations**: **Confirmed incident reports.** Provides timestamp, operational impact, casualties, fire tender counts, and structural collapse descriptions.
* **Data Format**: JSON, BigQuery SQL records, CSV.
* **Expected Events per Year in India**: 1,200 to 2,500 reported industrial, chemical, factory, and commercial warehouse fires per year.
* **Ground-Truth Suitability**: **The single most scalable pipeline for temporal and nominal ground-truth generation in 2025.** Must be filtered using strict Named Entity Recognition (NER) to isolate facility names from generic municipal fire reports.

---

### Source 6: Insurance & Catastrophe Loss Databases (Munich Re NatCatSERVICE / Swiss Re Sigma / FM Global)
* **Provider**: Munich Re, Swiss Re Institute, FM Global (Factory Mutual).
* **Dataset / Product Name**: Munich Re NatCatSERVICE (Technological & Man-Made Disasters Module), Swiss Re *sigma* Large Loss Database, FM Global Large Industrial Property Loss Data.
* **Geographic Coverage**: Global, including India.
* **Temporal Coverage & Reporting Latency**: Quarterly to annual release cycles; proprietary claims data updated internally within weeks.
* **Spatial Precision**: City or Industrial Cluster level in published aggregations; facility coordinate-level in proprietary reinsurance underwriting ledgers.
* **Access Method**: Aggregated reports available publicly via `swissre.com/institute` and `munichre.com`; raw underlying transactional loss databases require corporate institutional subscription or reinsurance partnership.
* **Licensing / Restrictions**: Highly proprietary / commercial license; strict confidentiality agreements on client loss records.
* **Incident Reports vs. Facility Locations**: Confirmed major industrial fire loss events.
* **Data Format**: Proprietary relational databases, PDF annual benchmark reports, CSV extracts for commercial subscribers.
* **Expected Events per Year in India**: 15 to 40 "large loss" events per year (events exceeding insurance thresholds of $\$10\text{M}$ to $\$20\text{M}$ in property damage and business interruption).
* **Ground-Truth Suitability**: **Medium for public researchers** due to proprietary paywalls and aggregated public reporting; **High for validating macro financial severity of major industrial explosions.**

---

### Source 7: EM-DAT (The International Disaster Database)
* **Provider**: Centre for Research on the Epidemiology of Disasters (CRED), UC Louvain, Belgium.
* **Dataset / Product Name**: EM-DAT Technological Disasters – Industrial Accidents (Sub-disaster types: *Industrial Fire, Industrial Explosion, Chemical Spill, Gas Leak*).
* **Geographic Coverage**: Global, comprehensive for India.
* **Temporal Coverage & Reporting Latency**: 1900 to present (updated continuously); latency of 1 to 4 weeks post-event.
* **Spatial Precision**: City / District / State level with specific facility named in the event description text.
* **Access Method**: Public web query and API via `public.emdat.be` (free registration required).
* **Licensing / Restrictions**: Free for academic, non-commercial, and research use (attribution required).
* **Incident Reports vs. Facility Locations**: **Confirmed incident reports.** Every entry represents an actual event that fulfilled strict criteria:
  * $\ge 10$ fatalities, OR
  * $\ge 100$ people affected / injured / evacuated, OR
  * Declaration of a state of emergency, OR
  * Appeal for international assistance.
* **Data Format**: CSV, XLSX, JSON.
* **Expected Events per Year in India**: 4 to 12 events per year (due to the high casualty/impact threshold).
* **Ground-Truth Suitability**: **Gold Standard for High-Severity Benchmark Events**, but misses smaller fires that do not cause $\ge 10$ deaths or $\ge 100$ casualties.

---

### Source 8: Global Flaring Tracker / VIIRS Nightfire (VNF)
* **Provider**: Earth Observation Group (EOG) at Colorado School of Mines / World Bank Global Flaring and Methane Reduction (GFMR) Partnership / NOAA.
* **Dataset / Product Name**: VIIRS Nightfire (VNF) Nighttime Combustion Source Product & World Bank Global Flaring Database.
* **Geographic Coverage**: Global (coverage of all Indian onshore/offshore oil & gas, refinery, petrochemical, and steel clusters).
* **Temporal Coverage & Reporting Latency**: VNF is processed daily from Suomi-NPP, NOAA-20, and NOAA-21 satellite overpasses (latency: $<12\text{ hours}$). World Bank Flaring Tracker is an annual consolidated product.
* **Spatial Precision**: Individual flare stack / emission point coordinate level ($<15\text{ m}$ localization via multi-pass subpixel Planck fitting).
* **Access Method**: EOG open portal (`payneinstitute.mines.edu/eog/viirs-nightfire-vnf/`) and World Bank open data portal.
* **Licensing / Restrictions**: Open Data / Creative Commons.
* **Incident Reports vs. Facility Locations**: **CRITICAL CONVOLUTION FILTER.** VNF detects sub-pixel combustion sources, yielding:
  * Estimated Temperature ($T\text{ in Kelvin}$)
  * Radiant Output ($W/\text{m}^2$)
  * Source Footprint Area ($m^2$)
  * **Persistence Metric** (detections per month/year at exact coordinate).
* **Data Format**: CSV, KMZ, GeoTIFF, daily ASCII tables.
* **Expected Events per Year in India**: Hundreds of active flare points tracked continuously across India (Assam, Gujarat, KG Basin, Mumbai High, refineries).
* **Ground-Truth Suitability**: **The Primary Tool for False-Positive Rejection.** 
  * *Gas Flare Signature*: $T = 1,600\text{–}2,100\text{ K}$, persistent across dozens/hundreds of overpasses, tiny source area ($<20\text{ m}^2$).
  * *Accidental Industrial Fire Signature*: $T = 800\text{–}1,400\text{ K}$, transient (present for 1–3 overpasses then disappears), large radiant footprint ($>100\text{ m}^2$).

---

### Source 9: OpenStreetMap (OSM) Industrial Polygons
* **Provider**: OpenStreetMap Foundation, Geofabrik, Overture Maps Foundation.
* **Dataset / Product Name**: OSM Landuse Vector Layers (`landuse=industrial`, `man_made=works`, `building=industrial`, `amenity=oil_refinery`, `industrial=*`).
* **Geographic Coverage**: Pan-India.
* **Temporal Coverage & Reporting Latency**: Continuously updated crowd-sourced geospatial vectors.
* **Spatial Precision**: Meter-accurate polygon boundaries of industrial estates, individual factory plots, and chemical storage yards.
* **Access Method**: Overpass API (`overpass-turbo.eu`), Geofabrik regional extracts (`download.geofabrik.de/asia/india.html`), Overture Maps GeoParquet datasets via AWS S3 / Azure.
* **Licensing / Restrictions**: Open Database License (ODbL).
* **Incident Reports vs. Facility Locations**: **FACILITY LOCATIONS / SPATIAL BOUNDARIES ONLY.** Provides ZERO incident evidence.
* **Data Format**: `.osm.pbf`, GeoJSON, Shapefile, GeoParquet.
* **Expected Events per Year in India**: N/A (Static/dynamic infrastructure layer containing over 150,000 industrial polygons across India).
* **Ground-Truth Suitability**: **Essential Spatial Mask / Prior.** Serves as the spatial containment boundary to intersect with physical thermal anomalies and news event locations.

---

### Source 10: India Ministry of Commerce & Petroleum Ministry Refinery & Industrial Registries
* **Provider**: Department for Promotion of Industry and Internal Trade (DPIIT) & Petroleum Planning & Analysis Cell (PPAC), Ministry of Petroleum and Natural Gas (MoPNG).
* **Dataset / Product Name**: 
  1. **India Industrial Land Bank (IILB)** / Industrial Information System (IIS) under PM GatiShakti.
  2. **PPAC Installed Refinery Capacity and Infrastructure Database**.
* **Geographic Coverage**: Pan-India (covers 4,500+ industrial parks, SEZs, node corridors, and all 23+ operational petroleum refineries).
* **Temporal Coverage & Reporting Latency**: Updated quarterly / bi-annually by State Industrial Development Corporations (GIDC, MIDC, RIICO, etc.).
* **Spatial Precision**: Authoritative plot-level GIS polygons, cadastral surveys, and GPS coordinates of central administrative gates.
* **Access Method**: `industrialchild.bi.gov.in` / `iis.ncog.gov.in/parks`, `ppac.gov.in`, and PM GatiShakti National Master Plan portal.
* **Licensing / Restrictions**: Public government portal; web GIS accessible; bulk download restricted (requires API access or institutional clearance).
* **Incident Reports vs. Facility Locations**: **FACILITY LOCATIONS ONLY.** Provides zero incident or fire records.
* **Data Format**: Web GIS feature services (WMS/WFS), ESRI MapServer, PDF capacity tables.
* **Expected Events per Year in India**: N/A (Tracks ~23 crude refineries and ~4,500 industrial parks).
* **Ground-Truth Suitability**: **Authoritative Baseline Reference.** Prevents false attribution of non-industrial structures (e.g. agricultural barns or brick kilns) as industrial plants.

---

### Source 11: High-Resolution Commercial Satellite Imagery (Planet Labs & Maxar)
* **Provider**: Planet Labs PBC & Maxar Technologies.
* **Dataset / Product Name**: 
  * PlanetScope (3 m multispectral, daily global cadence)
  * Planet SkySat (50 cm tasked optical / video)
  * Maxar WorldView-2/3 & WorldView Legion (30 cm optical, 8-band VNIR, SWIR).
* **Geographic Coverage**: Global, full targeted coverage of Indian subcontinent.
* **Temporal Coverage & Reporting Latency**: Daily monitoring (PlanetScope); On-demand tasking delivery within 6 to 24 hours (SkySat/WorldView).
* **Spatial Precision**: Sub-meter (30 cm to 50 cm). Resolves individual refinery tanks, factory roof spans, internal roads, and scorched storage drums.
* **Access Method**: Planet API (`api.planet.com`), Maxar SecureWatch / GBDX / EarthWatch portals; AWS commercial satellite marketplaces.
* **Licensing / Restrictions**: Commercial proprietary license (per-sq-km cost model; academic research discounts available).
* **Incident Reports vs. Facility Locations**: **PHYSICAL DAMAGE VERIFICATION.** Directly validates:
  * Plumes of black carbon smoke actively trailing from specific stacks or roof breaches.
  * Collapsed roof trusses, blown-out wall cladding, and scorched debris fields.
  * Water spray foam patterns and burnt storage tanks (e.g., floating roof collapses).
* **Data Format**: Orthorectified GeoTIFF, multispectral surface reflectance products.
* **Expected Events per Year in India**: Taskable over any coordinates in India; PlanetScope captures daily changes across all Indian industrial corridors.
* **Ground-Truth Suitability**: **The Supreme Visual Court of Evidence.** The ultimate verification tool to confirm whether a fire incident actually destroyed equipment at a specific facility.

---

### Source 12: Sentinel-2 MultiSpectral Instrument (MSI) Imagery
* **Provider**: European Space Agency (ESA) / Copernicus Programme (European Commission).
* **Dataset / Product Name**: Sentinel-2 MSI Level-2A (Bottom-Of-Atmosphere Surface Reflectance).
* **Geographic Coverage**: Pan-India.
* **Temporal Coverage & Reporting Latency**: 5-day revisit cadence at the equator (combining Sentinel-2A, 2B, and 2C); data latency is **2 to 4 hours** from satellite pass.
* **Spatial Precision**: 10 m (B2, B3, B4, B8 visible/NIR), 20 m (B11, B12 SWIR, Red-Edge).
* **Access Method**: Free and open via Copernicus Data Space Ecosystem (`dataspace.copernicus.eu`), Google Earth Engine (`ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")`), AWS Open Data.
* **Licensing / Restrictions**: Free, full, and open access under EU Copernicus legal policy.
* **Incident Reports vs. Facility Locations**: **PHYSICAL EVENT AND BURN-SCAR EVIDENCE.** Detects:
  1. *Active Fire Front*: Severe saturation in SWIR Band 12 ($2.19\ \mu\text{m}$) and Band 11 ($1.61\ \mu\text{m}$).
  2. *Post-Fire Structural Burn Scar*: Evaluated via Normalized Burn Ratio:
     $$\text{NBR} = \frac{B08 - B12}{B08 + B12}, \quad \Delta\text{NBR} = \text{NBR}_{\text{pre}} - \text{NBR}_{\text{post}}$$
     Industrial roof destruction and charred compounds show sharp positive $\Delta\text{NBR}$ spikes.
* **Data Format**: GeoTIFF / JPEG2000 (SAFE format).
* **Expected Events per Year in India**: Detects virtually any industrial fire with a burn footprint $>400\text{ m}^2$ that coincides with cloud-free overpasses.
* **Ground-Truth Suitability**: **Exceptional Open-Access Tool.** Best suited for systematic automated change-detection pipelines across large industrial zones.

---

### Source 13: Indian Oil & Gas PSUs (IOCL, ONGC, GAIL) & Regulatory Safety Oversight (OISD / PNGRB)
* **Provider**: Indian Oil Corporation Ltd (IOCL), Oil and Natural Gas Corporation (ONGC), GAIL (India) Ltd; Oil Industry Safety Directorate (OISD); Petroleum and Natural Gas Regulatory Board (PNGRB).
* **Dataset / Product Name**: 
  * OISD Safety Alerts & Root Cause Investigation Reports.
  * PNGRB "Incident Analysis" Investigation Dossiers.
  * SEBI Business Responsibility and Sustainability Reporting (BRSR) - Principles 3 & 6 Disclosures.
* **Geographic Coverage**: Pan-India (all refineries, onshore exploration assets, cross-country pipelines, LPG bottling plants).
* **Temporal Coverage & Reporting Latency**: 
  * OISD/PNGRB alerts: 1 to 4 months post-incident.
  * BRSR / Integrated Annual Reports: Published annually post-fiscal year.
  * Material event disclosures: Disclosed within 24 hours on stock exchanges.
* **Spatial Precision**: Exact plant name, processing unit (e.g. "Benzene storage tank, Koyali Refinery, Vadodara"), and geo-coordinates.
* **Access Method**: `oisd.gov.in` ("Safety Alerts"), `pngrb.gov.in` ("Incident Analysis"), and PSU investor relations portals.
* **Licensing / Restrictions**: Public regulatory information.
* **Incident Reports vs. Facility Locations**: **CONFIRMED INCIDENT INVESTIGATIONS.** Mandatorily includes root-cause analysis, fuel inventories consumed, sequence of explosions, and fatalities.
* **Data Format**: PDF technical reports and XBRL financial filings.
* **Expected Events per Year in India**: 15 to 35 reportable fire/explosion incidents across the hydrocarbon PSU sector annually.
* **Ground-Truth Suitability**: **Gold Standard for the Hydrocarbon Sector.** Completely authoritative, highly detailed technical autopsy of incidents.

---

### Source 14: Indian Insurance & Reinsurance Bureau Databases (IIB & GIC Re)
* **Provider**: Insurance Information Bureau of India (IIB, promoted by IRDAI) & General Insurance Corporation of India (GIC Re).
* **Dataset / Product Name**: IIB Commercial Fire Claims Registry, IIB Property Risk Analyzer, and GIC Re Large Fire Loss Portfolios.
* **Geographic Coverage**: Pan-India.
* **Temporal Coverage & Reporting Latency**: Aggregated annual and multi-year actuarial releases; transaction data enters claims systems within 7 to 30 days of preliminary survey report.
* **Spatial Precision**: Pin code, district, and occupancy occupancy code (e.g., chemical works, plastic fabrication, cotton godown); establishment names are redacted in public actuarial files.
* **Access Method**: `iib.gov.in` (public summaries, burning cost reports); full claims-level database is restricted to IRDAI-licensed insurers and reinsurers.
* **Licensing / Restrictions**: Restricted commercial / statutory industry data.
* **Incident Reports vs. Facility Locations**: **CONFIRMED PROPERTY DAMAGE CLAIMS.** Represents genuine fire losses that incurred financial payouts.
* **Data Format**: Tabular relational formats, PDF actuarial compendiums.
* **Expected Events per Year in India**: 15,000 to 25,000 commercial and industrial fire insurance claims filed annually across all tiers of Indian industry.
* **Ground-Truth Suitability**: **High Actuarial Validity, but Severely Constrained by Privacy Access Barriers.** Ideal for macro calibration of industrial fire frequency, but challenging to map directly to specific satellite pixels without insurer access.

---

## 3. High-Value Supplemental Ground-Truth Sources in India

In addition to the 14 prompted sources, three Indian statutory data channels provide immediate, unassailable ground-truth events:

### A. SEBI LODR Regulation 30 Corporate Announcements (BSE & NSE)
* **Mechanism**: Under Regulation 30 of the *SEBI (Listing Obligations and Disclosure Requirements) Regulations, 2015*, all listed companies in India are **statutorily mandated to notify stock exchanges within 24 hours** of any "disruption of operations due to fire, natural calamities, or force majeure".
* **Precision**: Address of the specific plant, date/time fire broke out, whether it was extinguished, human casualties, loss of machinery, and insurance status.
* **Access**: Free real-time scraping via BSE Corporate Announcements (`bseindia.com/corporates/ann.html`) and NSE Corporate Announcements (`nseindia.com/companies-listing/corporate-filings-announcements`).
* **Yield**: ~100 to 200 confirmed industrial fire events per year from listed industrial companies.

### B. National Green Tribunal (NGT) Legal Repository & Suo Motu Proceedings
* **Mechanism**: NGT regularly initiates *suo motu* proceedings or responds to petitions following major industrial fires (e.g. chemical blasts, hazardous waste dump fires, battery recycling plant infernos).
* **Precision**: The NGT mandates "Joint Inspection Committees" (CPCB + SPCB + NEERI + District Magistrate) who submit unredacted inspection reports with GPS coordinates, site plans, photographic proof, and satellite imagery.
* **Access**: Fully open and searchable via `greentribunal.gov.in`.
* **Yield**: ~40 to 80 exhaustive forensic dossiers per year.

### C. State DISH Dangerous Occurrences Registers (Form 24 / 24-A)
* **Mechanism**: Under Section 88A of the *Factories Act, 1948*, any fire or explosion in a factory causing cessation of work for $>24\text{ hours}$ must be reported on Form 24-A ("Notice of Dangerous Occurrence") regardless of whether bodily injury occurred.
* **Precision**: Exact plot number, plant unit, machine involved, and date.
* **Access**: State labor departments (e.g., Maharashtra `mahadish.in`, Gujarat `gujfiresafetycop.in`).

---

## 4. Comprehensive Comparison & Verification Matrix

| Source # | Source / Platform | Primary Role | Confirms Fire Event? | Spatial Precision | Reporting Latency | Expected Annual Events (India) | Access Barrier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **NDMA / NIDM** | Catastrophic Reviews | Yes (Select) | Facility / District | 6–24 Months | 1–5 | Open / Free |
| **2** | **DGFASLI / CIF** | Labour OSH Stats | Yes (Aggregated) | State / NIC Code | 18–36 Months | 150–250 | Open / Lagged |
| **3** | **SPCB / CPCB** | Regulatory Enforcement | Yes | Address / Coordinates | 1–4 Weeks | 300–600 | Open / Fragmented |
| **4** | **CSIR-NEERI** | Environmental Forensic | Yes | Sub-meter Coordinates | 2–9 Months | 10–25 | Court Portals |
| **5** | **GDELT / News APIs** | Real-Time News Event | Yes | Facility / Local Area | $<3$ Hours | 1,200–2,500 | Free / Paid APIs |
| **6** | **Munich Re / Swiss Re** | Catastrophe Loss Claims | Yes | City / Regional | 3–12 Months | 15–40 | High / Proprietary |
| **7** | **EM-DAT (CRED)** | International Disaster Registry | Yes ($\ge 10$ dead/100 aff.) | Facility / City | 1–4 Weeks | 4–12 | Open (Registration) |
| **8** | **VIIRS Nightfire / GGFR**| Flare / Heat Discrimination | **Confounder Filter** | Sub-pixel ($<15\text{ m}$) | Daily ($<12\text{ h}$) | Hundreds of Flares | Open / Free |
| **9** | **OpenStreetMap (OSM)** | Asset Footprint Mask | **Facility Mask Only** | Parcel Boundary | Continuous | N/A (Static Vectors) | Open / ODbL |
| **10** | **IILB / DPIIT / PPAC** | Authoritative Facility Cadastre| **Facility Mask Only** | Plot / Survey Cadastre | Quarterly | N/A (Static Infrastructure)| Open Web GIS |
| **11** | **Planet / Maxar** | High-Res Visual Forensic | Yes (Physical Damage) | 30 cm – 50 cm | 6–24 Hours | Taskable on Demand | High / Commercial |
| **12** | **Sentinel-2 MSI (ESA)**| Satellite Burn-Scar / SWIR | Yes (Spectral Signal) | 10 m – 20 m | 2–4 Hours | Hundreds | Open / Free |
| **13** | **OISD / PNGRB / PSUs** | Hydrocarbon Incident Dossier| Yes | Facility / Unit Level | 1–6 Months | 15–35 | Open / Web Reports |
| **14** | **IIB / GIC Re** | Insurance Loss Portfolios | Yes (Claims Paid) | Pin code / Occupancy | 6–18 Months | 15,000–25,000 | Industry Restricted|

---

## 5. Decision Matrix: Operational Labeling Pipeline for 2025

To construct a benchmark-quality ground truth dataset of 2025 Indian Industrial Fires, apply the following **Multi-Source Evidence Fusion Protocol**:

```
[Candidate Thermal Detection / VIIRS / MODIS / S2]
                       │
                       ▼
       [Check VIIRS Nightfire (Source 8)]
        Is it a persistent flare? (Temp > 1600K, >20 obs/yr)
              ├─── YES ───► CLASSIFY AS "ROUTINE GAS FLARING" (Discard as Fire Accident)
              └─── NO
                       │
                       ▼
       [Spatial Intersection (Sources 9 & 10)]
        Does point fall inside OSM Industrial / IILB Industrial Polygon?
              ├─── NO  ───► CLASSIFY AS "NON-INDUSTRIAL FIRE" (Vegetation / Agriculture / Landfill)
              └─── YES
                       │
                       ▼
       [Event Corroboration Engine (Tier Scoring)]
```

### Classification Confidence Levels:

* **TIER A (Definitive Ground Truth - Confidence = 1.00)**:
  * Corroborated by **at least one statutory/legal source** (SEBI LODR Reg 30 disclosure, SPCB closure order, NGT report, OISD alert, or EM-DAT entry) with matching date, facility name, and coordinates.
  * Verified by **high-resolution satellite imagery** (Maxar/PlanetScope or Sentinel-2 $\Delta\text{NBR} > 0.25$ / SWIR Band 12 saturation).
* **TIER B (High-Confidence Cross-Validated - Confidence $\ge 0.80$)**:
  * Multi-source **news aggregator confirmation** (GDELT / PTI / regional news) detailing facility name, fire brigade response, and date.
  * Located within an **OSM/IILB industrial polygon** AND non-persistent in VIIRS Nightfire.
  * Coincident Sentinel-2 SWIR anomaly or transient VIIRS Day-Night Band / I4 thermal detection.
* **TIER C (Ambiguous / Disqualified - Confidence $< 0.40$)**:
  * Thermal anomaly falls inside an industrial polygon, but **no news report, no regulatory notice, and no optical burn scar** can be found. 
  * *Action*: Reject from ground truth. (High likelihood of controlled waste burning, scrap furnace operation, or metal roof reflection).

### Practical Workflow Recommendation for 2025:
1. **Automate GDELT BigQuery & BSE/NSE Reg 30 scrapers** with keywords `("fire" OR "blast" OR "explosion") AND ("factory" OR "plant" OR "unit" OR "chemical" OR "refinery" OR "MIDC" OR "GIDC" OR "SIPCOT")`.
2. Geocode the extracted entity names against the **OpenStreetMap / India Industrial Land Bank (IILB)** boundaries.
3. Automatically retrieve **Sentinel-2 L2A** imagery pre- and post-event from the Copernicus Data Space Ecosystem to compute structural $\Delta\text{NBR}$ and inspect Band 12 SWIR reflectance.
4. Filter out any candidate that overlaps with the **VIIRS Nightfire Gas Flaring Atlas**.
This eliminates false spatial correlations and generates an airtight, peer-review-grade dataset.