# Comprehensive Investigation of Ground Truth Reference Datasets for Forest Fires in India (2025)

This report provides a systematic evaluation of independent reference datasets and sources capable of providing ground-truth or reference evidence for **forest fires in India for the calendar year 2025**. Every source has been vetted for operational status, portal accessibility, and practical utility (event-level perimeter vs. pixel/aggregated proxy).

---

### Executive Summary & Feasibility Matrix (2025 Forest Fires in India)

| # | Source / Dataset | Primary Provider | Coverage in India | Spatial Resolution | Event-Level Labels? | Actual 2025 Accessibility Status |
|---|---|---|---|---|---|---|
| **1** | **FSI FAST 3.0 / Van Agni Geo-Portal** | Forest Survey of India (MoEF&CC) | Pan-India | 375 m (VIIRS) / 1 km (MODIS) | Point alerts + LFF Event Clusters | **Fully Operational & Publicly Queryable** |
| **2** | **MODIS Burned Area (MCD64A1 v6.1)** | NASA LP DAAC / USGS / UMD | Pan-India | 500 m sinusoidal grid | Per-pixel Burn DOY (Requires clustering for event ID) | **Fully Operational & Accessible (Archived for all 2025)** |
| **3** | **Copernicus EMS (CEMS) Activations** | European Commission / JRC | None for fires in India | N/A (Satellite VHR) | Would be event polygons if activated | **Zero Activations for Fires in India (Theoretical/Unavailable)** |
| **4** | **GWIS / EFFIS (incl. GlobFire)** | EC JRC / GEO | Pan-India | 500 m / 375 m / 1 km | Yes (GlobFire vector perimeters) + Gridded/Stats | **Fully Accessible (Perimeters up to late 2024/2025 lag)** |
| **5** | **NDMA Fire Reports / SACHET** | NDMA (Govt of India) | Pan-India | Admin / Polygon warning zones | Contextual / Early warning only (No perimeters) | **Publicly Visible Alerts; No Event Ground-Truth Database** |
| **6** | **State Forest Depts (HP FIRE, UK FFRMS)** | HPFD / UKFD / OFMS | State-level (HP, UK, Odisha, KA) | Beat / Compartment ground reports | **Yes (Field ground truth: ha burned, damage, cause)** | **HP & UK Public Dashboards Live; Raw apps departmental** |
| **7** | **Sentinel-2 Burned Area Products** | ESA / Copernicus CLMS | Pan-India | 300 m (CLMS v4) / 10–20 m (Custom S2) | 300 m gridded (Custom S2 dNBR yields high-res polygons) | **CLMS v4.0 Live; No wall-to-wall operational S2 20m product (must process via GEE/CDSE)** |
| **8** | **LANDFIRE Equivalents (FSI FFRZ/FFDRS)** | FSI Dehradun / FRI / IIRS | Pan-India | 5 km x 5 km (Risk) / 1:50k (Types) | Static baseline / Fire danger (No fire event labels) | **Reports and Web Layers Accessible; No direct dynamic clone** |
| **9** | **Global Fire Emissions Database (GFED5)** | GFED Consortium / NASA GSFC | Pan-India | 0.25° x 0.25° (~25 km) | Macro aggregated emissions & burned area | **GFED5.1NRT Fully Accessible via SFTP and Web** |
| **10** | **Global Fire Atlas (GFA) & NRSC INFFRAS** | Zenodo / NRSC ISRO Bhuvan | Pan-India | 500 m (GFA) / 56 m–23.5 m (ISRO) | **Yes (Individual fire polygons with start/end date, spread)** | **GFA 2025 Zenodo Live; Bhuvan Active points live / Burnt Area on-demand** |

---

## Detailed Investigation by Source

### 1. Forest Survey of India (FSI) Fire Alerts & Databases (FAST 3.0 & Van Agni)
* **Provider Organization:** Forest Survey of India (FSI), Ministry of Environment, Forest and Climate Change (MoEF&CC), Government of India, Dehradun.
* **Exact Dataset/Product Name:** 
  1. *Forest Fire Alert System version 3.0 (FAST 3.0)* (Near-Real-Time NRT active fire alerts)
  2. *Large Forest Fire (LFF) Monitoring Programme*
  3. *Van Agni Geo-Portal* (Interactive spatial portal & archival query)
* **Geographic Coverage:** Pan-India (covers all reserved, protected, and unclassed forests across all States and Union Territories down to Forest Beat and Compartment level).
* **Temporal Coverage & Latency:** Operational continuous monitoring. Latency is ~20 to 30 minutes from satellite overpass (data ingested via NRSC Earth Station at Shadnagar). Archival data spans 2004–present, fully covering 2025.
* **Spatial Resolution:** 
  - SNPP-VIIRS: 375 m × 375 m
  - Terra/Aqua MODIS: 1 km × 1 km
  - Delineated down to administrative Forest Division, Range, Beat, and Compartment.
* **Access Method:** 
  - Web portal search: [https://fsiforestfire.gov.in/](https://fsiforestfire.gov.in/)
  - Spatial viewer: [https://vanagniportal.fsiforestfire.gov.in/](https://vanagniportal.fsiforestfire.gov.in/)
  - Filterable search tool for "Archived NRT Data" and "Archived LFF Data" by State/District/Date.
  - Automated SMS and Email notification system for registered nodal officers and public users.
* **Licensing / Access Restrictions:** Free public access for online visualization, statistical queries, and daily bulletins. Automated API endpoints require departmental credentials.
* **Event-Level Labels vs. Aggregated:** 
  - *NRT Alerts:* Point-level thermal anomaly detections (active fire pixels) with metadata (coordinates, sensor, acquisition timestamp, forest type, canopy density class, beat name).
  - *Large Forest Fire (LFF):* **Event-level clustering**. Defined by an algorithm triggering on ≥3 contiguous SNPP-VIIRS fire pixels (representing an affected footprint of ≥40 hectares). Continuously tracked across successive orbits with dynamic perimeter estimates until extinguished, followed by 3 days of dormant burn scanning.
* **Data Format:** CSV, KML/KMZ (Google Earth compatible), WMS (Web Map Service) on Van Agni, and periodic PDF summary bulletins.
* **Actual vs. Theoretical Accessibility:** **Actually Accessible.** Any researcher can query 2025 daily or monthly active fire points and LFF records directly through the Van Agni archival interface without payment or clearance.

---

### 2. MODIS Burned Area Product (MCD64A1 Version 6.1) for India
* **Provider Organization:** NASA Land Processes Distributed Active Archive Center (LP DAAC) / USGS / University of Maryland.
* **Exact Dataset/Product Name:** `MCD64A1`: MODIS/Terra+Aqua Burned Area Monthly L3 Global 500m SIN Grid V061.
* **Geographic Coverage:** Global wall-to-wall. All India is covered by MODIS Sinusoidal projection tiles: `h24v05`, `h24v06`, `h24v07`, `h25v05`, `h25v06`, `h25v07`, `h26v06`, `h26v07`.
* **Temporal Coverage & Latency:** November 2000 to present. Complete 2025 calendar year observations are fully processed. Production latency is 1 to 3 months following the end of each calendar month (due to temporal forward-backward validation).
* **Spatial Resolution:** 500 meters (gridded sinusoidal projection).
* **Access Method:**
  - NASA Earthdata Search: `search.earthdata.nasa.gov`
  - Google Earth Engine (Asset: `MODIS/061/MCD64A1`)
  - Microsoft Planetary Computer (`modis-64A1-061`)
  - LP DAAC Data Pool / AppEEARS API
* **Licensing / Access Restrictions:** Open and completely free under NASA's Earth Science Data & Information System (ESDIS) policy (Public Domain / CC0 equivalent).
* **Event-Level Labels vs. Aggregated:** **Pixel-level physical ground truth.** Contains bands:
  - `Burn Date` (Day of Year 1–366 when burn occurred; 0 = unburned)
  - `Burn Date Uncertainty` (temporal uncertainty in days)
  - `QA` (Quality Assurance flags)
  - `First Day` and `Last Day` of valid composite window.
  *Note:* While it provides pixel-level burn timing, it does not natively label discrete individual fire events with a single unique Event ID unless clustered via post-processing algorithms (e.g., GlobFire or Global Fire Atlas).
* **Data Format:** Native HDF4-EOS; Cloud-Optimized GeoTIFF (Planetary Computer / Harmony); GeoTIFF and NetCDF via GEE / AppEEARS.
* **Actual vs. Theoretical Accessibility:** **Actually Accessible.** 100% available and immediate to clip, analyze, and download for India for the full year 2025.

---

### 3. Copernicus Emergency Management Service (CEMS) Activations for India
* **Provider Organization:** European Commission / Copernicus Emergency Management Service (operated via European Commission Joint Research Centre - JRC).
* **Exact Dataset/Product Name:** CEMS On-Demand Mapping (Rapid Mapping and Risk & Recovery Mapping).
* **Geographic Coverage:** Global potential, but strictly activated on-demand.
* **Temporal Coverage & Latency for 2025:** Rapid mapping produces VHR post-fire perimeters within 24–48 hours of activation.
* **Spatial Resolution:** Very High Resolution (VHR optical/radar: 0.5 m to 10 m).
* **Access Method:** Web portal: [https://emergency.copernicus.eu/](https://emergency.copernicus.eu/)
* **Licensing / Access Restrictions:** Creative Commons CC-BY 4.0 when activations exist.
* **Event-Level Labels vs. Aggregated:** Detailed vector delineation of burnt area perimeters, fire grading (damage levels), and affected infrastructure.
* **Actual vs. Theoretical Accessibility:** **THEORETICAL ONLY / NOT ACCESSIBLE FOR INDIA FIRES.**
  - *Critical Finding:* There are **ZERO CEMS activations (Rapid Mapping or Risk & Recovery) for forest fires or wildfires in India for 2025 or any previous year**.
  - All past CEMS activations for India have been triggered exclusively for floods, tropical cyclones (e.g., Cyclone Fani, Hudhud), and landslides (e.g., Wayanad, Kerala in July 2024). 
  - Indian disaster response protocols rely on domestic remote sensing (ISRO NRSC DMSD / FSI) and do not request DG ECHO / CEMS activations for forest fires.

---

### 4. Global Wildfire Information System (GWIS / EFFIS) Coverage for India
* **Provider Organization:** European Commission Joint Research Centre (JRC) and Group on Earth Observations (GEO) under Copernicus Early Warning and Monitoring.
* **Exact Dataset/Product Name:**
  1. *GWIS Country Profile for India*
  2. *GlobFire Fire Perimeters* (derived from MCD64A1)
  3. *GWIS Near Real-Time Active Fires* (MODIS & VIIRS)
  4. *GWIS Monthly Burned Area Statistics*
* **Geographic Coverage:** Full pan-India coverage (national and GADM Level-1 State-wise boundaries).
* **Temporal Coverage & Latency:** 
  - Active fires: daily NRT (3–6 hours latency).
  - Burned area & GlobFire: updated based on MCD64A1 (monthly frequency, ~1–2 months latency).
* **Spatial Resolution:** 
  - GlobFire perimeters: 500 m native grid geometry.
  - Active fires: 375 m (VIIRS) and 1 km (MODIS).
  - Monthly tabular statistics: Administrative Level 0 (India) and Level 1 (States).
* **Access Method:**
  - Interactive portal: [https://gwis.jrc.ec.europa.eu/apps/country.profile/](https://gwis.jrc.ec.europa.eu/apps/country.profile/)
  - Direct downloads: GWIS Data Downloads page (`gwis.jrc.ec.europa.eu`)
  - Google Earth Engine catalog: `JRC/GWIS/GlobFire/v2/FinalPerimeters`
* **Licensing / Access Restrictions:** Free and open access under the Copernicus open data license.
* **Event-Level Labels vs. Aggregated:** 
  - *GlobFire:* **TRUE EVENT-LEVEL LABELS.** Delineates individual fire events as polygon perimeters with unique Fire ID, start date, final date, duration in days, and total burned area in hectares.
  - *Country Statistics:* Aggregated tabular data (monthly burned area in ha broken down by land cover class).
* **Data Format:** ESRI Shapefiles (zipped), CSV tables, and GeoTIFFs.
* **Actual vs. Theoretical Accessibility:** **Actually Accessible.** Country-level charts and statistics for India are downloadable directly. GlobFire perimeters are accessible up to late 2024 / early 2025 archive releases.

---

### 5. India's National Disaster Management Authority (NDMA) Fire Reports
* **Provider Organization:** National Disaster Management Authority (NDMA), Ministry of Home Affairs, Government of India.
* **Exact Dataset/Product Name:** 
  1. *SACHET Integrated Early Warning Portal* ([https://sachet.ndma.gov.in/](https://sachet.ndma.gov.in/))
  2. *NDMA Annual Reports & Daily Disaster Situation Bulletins*
  3. *National Disaster Management Guidelines on Forest Fires*
* **Geographic Coverage:** All India.
* **Temporal Coverage & Latency:** SACHET provides NRT warnings. Situation reports are published daily during declared national emergency periods.
* **Spatial Resolution:** Coarse administrative boundaries (State, District, Block level polygons).
* **Access Method:** Web download: `ndma.gov.in` and `sachet.ndma.gov.in`.
* **Licensing / Access Restrictions:** Public domain / Government Open Access.
* **Event-Level Labels vs. Aggregated:** **AGGREGATED / CONTEXTUAL ONLY.** 
  - NDMA does **not** maintain or release a spatial ground-truth burned area perimeter or fire incident database.
  - NDMA acts as a disaster coordination and alerting authority; it ingests alerts from FSI and ISRO and routes CAP (Common Alerting Protocol) SMS/mobile warnings.
* **Data Format:** PDF bulletins, CAP XML/JSON feeds on SACHET.
* **Actual vs. Theoretical Accessibility:** Accessible for high-level situation reports and warnings, but **unsuitable as an independent spatial ground-truth reference dataset**.

---

### 6. State Forest Department Fire Reports (Public Portals)
State Forest Departments maintain the most authoritative ground-truth records because forest guards and range officers physically inspect and record burnt patches on the ground. Several states offer public-facing reporting systems:

#### A. Himachal Pradesh Forest Department: FIRE Portal
- **Dataset / System Name:** *Fire Incident Reporting Engine (FIRE)* ([https://forestfire.hp.gov.in/](https://forestfire.hp.gov.in/))
- **Coverage:** Entire state of Himachal Pradesh (Forest Circles, Divisions, Ranges, Beats).
- **Temporal Coverage:** Multi-year archival covering 2024, 2025, and 2026 fire seasons.
- **Granularity / Resolution:** Ground-verified beat and compartment level. Records incident ID, date/time, exact compartment, area burnt (in hectares), estimated financial loss, young plantation/regeneration mortality, and fire cause.
- **Access Method:** Public web dashboard for division-wise and circle-wise summary queries; field staff login for raw incident logs.
- **Format:** Web tables, CSV/PDF exports.
- **Ground Truth Status:** **High-quality event-level ground truth.**

#### B. Uttarakhand Forest Department: FFRMS & Daily Fire Bulletins
- **Dataset / System Name:** *Forest Fire Reporting and Management System (FFRMS)* / *Daily Forest Fire Bulletins* ([https://forest.uk.gov.in/](https://forest.uk.gov.in/) & `ukforest.in`).
- **Coverage:** Entire state of Uttarakhand (Garhwal and Kumaon forest circles, protected areas).
- **Temporal Coverage:** Active fire season bulletins (annually Feb 15 – June 30) for 2024 and 2025.
- **Granularity / Resolution:** Divisional level reports compiled daily by Master Control Rooms (MCR). Delineates daily fire occurrences, cumulative hectares burnt, human/wildlife casualties, and firefighting resources deployed.
- **Access Method:** Public download of daily PDF bulletins; departmental intranet for field-level incident logs.
- **Format:** PDF bulletins and annual statistical tables.
- **Ground Truth Status:** Authoritative ground-verified counts and area estimates (often highlights discrepancies with satellite detection).

#### C. Odisha Forest Department: OFMS 2.0
- **Dataset / System Name:** *Odisha Forest Management System (OFMS 2.0)* (developed with ORSAC).
- **Coverage:** Odisha State.
- **Granularity / Resolution:** Mobile GPS-enabled field validation of satellite fire points by beat guards.
- **Access Method:** Mobile app / web system. Aggregated statistics published in departmental annual activity reports.
- **Actual Accessibility:** Public can access annual reports; live event-level GPS verification logs require departmental login.

#### D. Karnataka Forest Department: KFD Fire Portal (NRSC Bhuvan)
- **Dataset / System Name:** *Karnataka Forest Fire Monitoring & Management System* ([https://bhuvan-app1.nrsc.gov.in/ka_forest/](https://bhuvan-app1.nrsc.gov.in/ka_forest/)).
- **Coverage:** Karnataka Forest Divisions.
- **Access / Format:** Web GIS viewer on Bhuvan; alerts and historical hotspot density.

---

### 7. Sentinel-2 Burned Area Mapping Products
* **Provider Organization:** European Space Agency (ESA) / Copernicus Land Monitoring Service (CLMS) / University of Alcala (FireCCI).
* **Exact Dataset/Product Name:**
  1. *CLMS Global Burnt Area 300m Collection Version 4.0* (Operational 2025–present, derived from Sentinel-3 OLCI/SLSTR).
  2. *ESA FireCCIS2 Version 1.0* (Sentinel-2 MSI 20 m experimental/pilot burned area product).
  3. *Event-specific dNBR / BAIS2 Sentinel-2 Level-2A Analysis* (Copernicus Data Space Ecosystem / GEE).
* **Geographic Coverage:** 
  - CLMS v4.0: Global wall-to-wall (includes India).
  - FireCCIS2: Pilot regions (primarily Africa/sub-Saharan; not operationally produced wall-to-wall for India in 2025).
  - Sentinel-2 L2A raw imagery: Pan-India (10–20 m).
* **Temporal Coverage & Latency:** 
  - CLMS Burnt Area v4.0: Daily updates for 2025 (latency 24–48 hours).
  - Sentinel-2 MSI overpasses: 5-day constellation revisit frequency (latency 2–12 hours for L2A surface reflectance).
* **Spatial Resolution:** 
  - CLMS v4.0: 300 meters.
  - Custom Sentinel-2 derived products: 10 m (VNIR) to 20 m (SWIR - Bands 11 & 12).
* **Access Method:**
  - Copernicus Data Space Ecosystem (CDSE): [https://dataspace.copernicus.eu/](https://dataspace.copernicus.eu/)
  - CLMS Portal: [https://land.copernicus.eu/](https://land.copernicus.eu/)
  - Google Earth Engine (`COPERNICUS/S2_SR_HARMONIZED`)
* **Licensing / Access Restrictions:** Free and open access under the EU Copernicus Data Policy.
* **Event-Level Labels vs. Aggregated:** 
  - CLMS v4.0: Gridded pixel-level daily burn date and burn fraction (300 m).
  - Custom Sentinel-2 Workflows: **True decametric (10–20 m) event-level fire perimeters**. By computing Differenced Normalized Burn Ratio ($dNBR = \frac{NIR - SWIR2}{NIR + SWIR2}_{pre} - \frac{NIR - SWIR2}{NIR + SWIR2}_{post}$) or the Burned Area Index for Sentinel-2 ($BAIS2$), discrete event polygons can be mapped with high fidelity.
* **Actual vs. Theoretical Accessibility:** **Partially Accessible as Pre-Packaged / Fully Accessible via Cloud Workflow.**
  - *Reality Check:* There is **no pre-packaged, operational, daily 20 m Sentinel-2 burned area polygon dataset for India** published by Copernicus for 2025. 
  - However, researchers routinely generate this ground truth on-demand in Google Earth Engine or CDSE by masking clouds and running dNBR thresholding against known FSI active fire point coordinates.

---

### 8. LANDFIRE or Equivalent India Products
* **Provider Organization:** In the US, LANDFIRE is an interagency program (USGS/USFS). In India, there is no single multi-agency LANDFIRE program. The functional equivalents are maintained by the **Forest Survey of India (FSI)**, **Forest Research Institute (FRI)**, and the **Indian Institute of Remote Sensing (IIRS - ISRO)**.
* **Exact Dataset/Product Name:**
  1. *Forest Fire Risk Zonation (FFRZ) of India* (FSI)
  2. *Forest Fire Danger Rating System (FFDRS) / Fire Weather Index (FWI)* (FSI)
  3. *Forest Type and Canopy Density Maps* (FSI biennial India State of Forest Report - ISFR)
  4. *Surface Fuel Load Mapping* (FSI Technical Information Series)
* **Geographic Coverage:** All India.
* **Temporal Coverage & Latency:** 
  - FFRZ & Forest Types: Updated biennially/periodically (ISFR 2021, 2023, 2025).
  - FFDRS/FWI: Daily operational modeling during the peak fire season (January–June).
* **Spatial Resolution:** 
  - FFRZ: 5 km × 5 km gridded zonation (categorized as Extremely Fire Prone, Very High, High, Moderate, Less Prone).
  - Forest Type / Canopy Density: 1:50,000 mapping scale (~23.5 m to 30 m effective).
* **Access Method:** FSI portal ([https://fsi.nic.in](https://fsi.nic.in)) and Van Agni viewer. Technical publications and maps downloadable in PDF format.
* **Licensing / Access Restrictions:** Publicly accessible for reports and web view; raw spatial GIS shapefiles are restricted to government and academic research upon formal application.
* **Event-Level Labels vs. Aggregated:** **STATIC BASELINE / HAZARD RISK ONLY.** These products do not record individual fire events or burn perimeters; they provide the antecedent fuel model, forest classification, and susceptibility backdrop.
* **Actual vs. Theoretical Accessibility:** **Accessible as contextual risk layers, but not as dynamic 2025 fire event ground truth.**

---

### 9. Global Fire Emissions Database (GFED)
* **Provider Organization:** GFED Consortium (Vrije Universiteit Amsterdam, NASA Goddard Space Flight Center, UC Irvine, Colorado State University).
* **Exact Dataset/Product Name:** *GFED5* and *GFED5.1NRT (Near-Real-Time extension)* (superseding GFED4 and GFED4.1s).
* **Geographic Coverage:** Global gridded coverage, with pre-computed national profiles for India.
* **Temporal Coverage & Latency:** 1997 through 2025. GFED5.1NRT provides daily emissions and burned area estimates using VIIRS active fire observations (latency: days to weeks).
* **Spatial Resolution:** 0.25° × 0.25° latitude/longitude (~25 km × 25 km grid).
* **Access Method:**
  - Official Portal: [https://www.globalfiredata.org/](https://www.globalfiredata.org/)
  - Interactive "Current Fire Situation" country tool: `globalfiredata.org/data.html`
  - Automated download via SFTP (credentials provided publicly on the website).
* **Licensing / Access Restrictions:** Free and open for scientific research and educational use.
* **Event-Level Labels vs. Aggregated:** **MACRO AGGREGATED EVIDENCE ONLY.** 
  - Provides gridded daily/monthly burned area ($km^2$), dry matter burned, and trace gas/aerosol emissions ($C, CO_2, CH_4, PM_{2.5}, NO_x$) partitioned by fire type (boreal, temperate, tropical deforestation, savanna, agriculture).
  - Does **not** delineate individual fire polygons or event boundaries.
* **Data Format:** NetCDF-4 / HDF5 files; tabular CSV for country-level summaries.
* **Actual vs. Theoretical Accessibility:** **Actually Accessible.** GFED5.1NRT is online and fully accessible for downloading India's 2025 monthly and daily aggregate fire activity.

---

### 10. India-Specific Burned Area & Fire Perimeter Datasets

#### A. Global Fire Atlas (GFA) 2025 Extended Edition (Andela & Jones)
* **Provider / Authors:** Niels Andela (Cardiff Univ / NASA GSFC) & Matthew Jones (UEA).
* **Exact Dataset Name:** *The Global Fire Atlas of individual fire size, duration, speed and direction (v20250411)*.
* **DOI / Repository:** Zenodo (DOI: [10.5281/zenodo.14065246](https://doi.org/10.5281/zenodo.14065246)).
* **Coverage:** Global, including complete coverage of India.
* **Temporal Coverage:** 2003 through early 2025 (regularly extended with new MODIS MCD64A1 releases).
* **Spatial Resolution:** 500 m underlying resolution, polygon vector geometry.
* **Event-Level Labels:** **YES.** Contains vector shapefiles of **individual fire perimeters** with unique Fire ID, ignition point, start date, extinction date, duration (days), expansion speed ($km/day$), and final burned area.
* **Format & Access:** Direct download of zipped ESRI Shapefiles and GeoTIFFs from Zenodo. CC-BY 4.0 license.
* **Practical Status:** **Best available global open-access vector perimeter dataset covering India.**

#### B. ISRO / NRSC Indian Forest Fire Response and Assessment System (INFFRAS) & Bhuvan
* **Provider:** National Remote Sensing Centre (NRSC), ISRO, Hyderabad (Disaster Management Support Division - DMSD).
* **Exact Dataset Name:** *INFFRAS Active Fire Points and Post-Fire Burnt Area Assessments* (served on Bhuvan NOEDA and NICES).
* **Coverage:** Pan-India; state-specific forestry applications (e.g., Karnataka, Himachal Pradesh, Uttarakhand).
* **Temporal Coverage & Latency:** Active fire points within 30 minutes; periodic post-fire assessments for major fire events.
* **Spatial Resolution:** 
  - Active fires: 375 m (VIIRS) / 1 km (MODIS).
  - Burnt Area Assessments: 56 m (Resourcesat-2/2A AWiFS) and 23.5 m (LISS-III).
* **Access Method:** [https://bhuvan.nrsc.gov.in](https://bhuvan.nrsc.gov.in) and Bhuvan Open EO Data Archive (NOEDA).
* **Event-Level Labels:** Burnt area products are event-focused for major fire crises; active fires are point hotspots.
* **Actual Accessibility:** Active fire layers and 5 km fire regime grids are open on Bhuvan. Raw high-resolution vector burnt area shapefiles for specific 2025 fires are treated as disaster project outputs and typically require formal institutional requests via NRSC DMSD.

#### C. NASA FIRMS India Active Fire Archive (MODIS & VIIRS)
* **Provider:** NASA Earth Science Data and Information System (ESDIS) / LANCE FIRMS.
* **Dataset Name:** *FIRMS NRT and Ultra-Real-Time Active Fire Detections (VIIRS 375m VNP14IMGTDL / VJ114IMGTDL & MODIS MCD14DL)*.
* **Access Portal:** [https://firms.modaps.eosdis.nasa.gov/download/](https://firms.modaps.eosdis.nasa.gov/download/)
* **Format:** Shapefile, CSV, KML, and direct REST API.
* **Significance for 2025 Ground Truth:** Provides the exact coordinates, UTC timestamp, confidence score, and Fire Radiative Power (FRP in MW) for every active fire pixel in India throughout 2025. Frequently used to spatio-temporally filter and validate burned area scars.

---

## Synthesis & Recommended Ground-Truth Validation Workflow for India 2025

If you are constructing a ground-truth dataset for 2025 forest fires in India, the recommended integration strategy is:

1. **For Event Detection & Ground Verification:**
   - Use **FSI FAST 3.0 / Van Agni LFF records** for national candidate fire event clusters ($\ge 40$ ha).
   - In cross-validation states (particularly Himachal Pradesh and Uttarakhand), cross-reference with the **HP Forest Department FIRE portal** (`forestfire.hp.gov.in`) and **UK Forest Department FFRMS bulletins** to extract field-verified hectares and dates.
2. **For High-Resolution Burnt Perimeters (10–20 m):**
   - Query **NASA FIRMS (VIIRS 375 m)** to obtain ignition centroids and peak fire dates for 2025.
   - Run an automated pre/post-fire **differenced Normalized Burn Ratio ($dNBR$)** workflow over **Sentinel-2 Level-2A** imagery in Google Earth Engine or Copernicus Data Space for the target fire window to delineate accurate 10–20 m polygon perimeters.
3. **For Operational 500 m Standard Wall-to-Wall Perimeters:**
   - Ingest **MODIS MCD64A1 v6.1** (available across all 2025 months) or download the pre-clustered event perimeters from the **Global Fire Atlas (Zenodo v20250411)** and **GWIS GlobFire**.
4. **Sources to Exclude:**
   - **Exclude CEMS Rapid Mapping** (no activations exist for Indian fires).
   - **Exclude NDMA** as a spatial ground-truth source (provides text/SMS warnings only).
   - **Exclude GFED5** for local perimeter work (designed solely for 25 km macro emissions accounting).