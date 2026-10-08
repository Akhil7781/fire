# Independent Reference Data Source Comparison Matrix (India 2025 Focus)

This document provides a comprehensive evaluation of candidate independent reference datasets capable of providing ground-truth evidence for satellite thermal anomaly classification in India for 2025.

---

## 1. Class 1: Industrial Fire Reference Sources

### 1.1 SEBI LODR Regulation 30 Corporate Disclosures
- **Provider**: Bombay Stock Exchange (BSE) & National Stock Exchange of India (NSE).
- **Product Name**: Corporate Material Event Disclosures (Regulation 30).
- **Geographic Coverage**: Pan-India (All listed industrial facilities).
- **Temporal Coverage & Latency**: Continuous / 24-hour statutory disclosure requirement.
- **Spatial Resolution**: Facility name, city, industrial estate name (Geocodable to $\le 50\text{ m}$).
- **Supported Classes**: Class 1 (Industrial Fire).
- **Access Method**: Public web search & RSS scraping via BSE (`bseindia.com`) and NSE (`nseindia.com`).
- **Licensing**: Open public corporate registry.
- **Evidence Type**: **Event-level confirmed incident report** (legal disclosure of facility fire, damage, and operational disruption).
- **Matching Uncertainty**: Low ($\pm 100\text{ m}$, $\pm 1$ day).

### 1.2 State Pollution Control Board (SPCB) & NGT Inspection Reports
- **Provider**: State PCBs (MPCB, GPCB, TNPCB, UPPCB, APPCB) & National Green Tribunal.
- **Product Name**: Hazardous Industrial Incident Investigation Dossiers & Show-Cause Orders.
- **Geographic Coverage**: Pan-India across major industrial hubs (MIDC, GIDC, SIPCOT, RIICO).
- **Temporal Coverage & Latency**: 3 days to 4 weeks post-incident.
- **Spatial Resolution**: Site survey number, plant unit, and GPS coordinates ($\le 20\text{ m}$).
- **Supported Classes**: Class 1 (Industrial Fire).
- **Access Method**: Regulatory portals (`greentribunal.gov.in`, state SPCB web portals).
- **Licensing**: Statutory public documents / Quasi-judicial records.
- **Evidence Type**: **Event-level confirmed incident investigation** (detailed chemical damage, burnt area).
- **Matching Uncertainty**: Very Low ($\pm 20\text{ m}$, exact date).

### 1.3 GDELT & News Aggregator Incident Stream
- **Provider**: GDELT Project 2.0 (Global Knowledge Graph) / Event Registry.
- **Product Name**: GDELT GKG 2.0 Translingual News Stream / Regional Wire News.
- **Geographic Coverage**: Pan-India across English and 10 regional Indian languages.
- **Temporal Coverage & Latency**: Real-time ($< 3\text{ hours}$ from news publication).
- **Spatial Resolution**: District / Town / Named Industrial Estate.
- **Supported Classes**: Class 1 (Industrial Fire), Class 2 (Forest Fire), Class 3 (Agri Fire - macro).
- **Access Method**: Google BigQuery (`gdelt-bq.gdeltv2.gkg`) / Event Registry REST API.
- **Licensing**: Open Data (CC-BY 4.0) / Commercial API.
- **Evidence Type**: **Event-level media incident reports**.
- **Matching Uncertainty**: Moderate ($\pm 500\text{ m}$ to $2\text{ km}$, $\pm 12\text{ hours}$).

### 1.4 High-Resolution Optical Satellite Imagery (Sentinel-2 / PlanetScope)
- **Provider**: ESA Copernicus & Planet Labs PBC.
- **Product Name**: Sentinel-2 MSI Level-2A / PlanetScope 3m Ortho-Scene.
- **Geographic Coverage**: Pan-India wall-to-wall.
- **Temporal Coverage & Latency**: 5-day revisit (Sentinel-2) / Daily (PlanetScope); latency $< 12\text{ hours}$.
- **Spatial Resolution**: 10 m – 20 m (Sentinel-2) / 3 m (PlanetScope).
- **Supported Classes**: Class 1 (Industrial Fire), Class 2 (Forest Fire), Class 3 (Agri Fire).
- **Access Method**: Copernicus Data Space Ecosystem API / Google Earth Engine / Planet API.
- **Licensing**: Open & Free (Copernicus) / Commercial (Planet).
- **Evidence Type**: **Physical event burn-scar & structural damage evidence** ($\Delta\text{NBR}$ / SWIR reflectance).
- **Matching Uncertainty**: Very Low ($\le 10\text{ m}$, $\pm 2.5\text{ days}$).

---

## 2. Class 2: Forest Fire Reference Sources

### 2.1 Forest Survey of India (FSI) FAST 3.0 & Van Agni
- **Provider**: Forest Survey of India (FSI), MoEF&CC, Dehradun.
- **Product Name**: FAST 3.0 Large Forest Fire (LFF) Monitoring & Van Agni Geo-Portal.
- **Geographic Coverage**: Pan-India (All forest beats and compartments).
- **Temporal Coverage & Latency**: 20 minutes from satellite overpass; complete 2025 archive.
- **Spatial Resolution**: 375 m (VIIRS) / 1 km (MODIS), mapped to forest compartment vectors.
- **Supported Classes**: Class 2 (Forest Fire).
- **Access Method**: Public portal `vanagniportal.fsiforestfire.gov.in`.
- **Licensing**: Free Open Public Access.
- **Evidence Type**: **Event-level clustered forest fire perimeters** ($\ge 40\text{ ha}$) and point alerts.
- **Matching Uncertainty**: Low ($\pm 375\text{ m}$, exact timestamp).

### 2.2 MODIS Burned Area Product (MCD64A1 v6.1) & Global Fire Atlas
- **Provider**: NASA LP DAAC / Zenodo (Andela et al.).
- **Product Name**: MCD64A1 Burned Area Monthly 500m / Global Fire Atlas 2025 Extended Edition.
- **Geographic Coverage**: Global / Pan-India.
- **Temporal Coverage & Latency**: Monthly / 1–2 months lag post-observation.
- **Spatial Resolution**: 500 m sinusoidal grid / Vector polygon perimeters.
- **Supported Classes**: Class 2 (Forest Fire), Class 3 (Agri Fire).
- **Access Method**: NASA Earthdata Search / Google Earth Engine / Zenodo DOI download.
- **Licensing**: Public Domain (NASA) / CC-BY 4.0 (Zenodo).
- **Evidence Type**: **Physical per-pixel day-of-year burn dates & vector event perimeters**.
- **Matching Uncertainty**: Moderate ($\pm 500\text{ m}$, $\pm 2\text{ days}$).

### 2.3 State Forest Department Portals (Himachal Pradesh & Uttarakhand)
- **Provider**: HPFD & UKFD Master Control Rooms.
- **Product Name**: HP Forest Fire Incident Reporting Engine (FIRE) & UK FFRMS Bulletins.
- **Geographic Coverage**: State-level (Himachal Pradesh, Uttarakhand).
- **Temporal Coverage & Latency**: Daily during fire season (Feb–June).
- **Spatial Resolution**: Forest Compartment / Beat boundary ($\le 100\text{ m}$).
- **Supported Classes**: Class 2 (Forest Fire).
- **Access Method**: Public web dashboards (`forestfire.hp.gov.in`, `forest.uk.gov.in`).
- **Licensing**: Open State Government Data.
- **Evidence Type**: **Field-verified ground incident reports** (hectares burned, damage, cause).
- **Matching Uncertainty**: Low ($\pm 200\text{ m}$, exact date).

---

## 3. Class 3: Agricultural Fire Reference Sources

### 3.1 ICAR-IARI CREAMS Daily Agricultural Fire Bulletins
- **Provider**: Indian Agricultural Research Institute (ICAR-IARI), New Delhi.
- **Product Name**: CREAMS Satellite-Based Active Fire Event (AFE) Monitoring System.
- **Geographic Coverage**: Punjab, Haryana, Uttar Pradesh, Rajasthan, Madhya Pradesh, Delhi.
- **Temporal Coverage & Latency**: Daily published reports during burning seasons (Sept–Nov, Apr–May).
- **Spatial Resolution**: 375 m (VIIRS) / 1 km (MODIS), mapped to district and block vectors.
- **Supported Classes**: Class 3 (Agricultural Fire).
- **Access Method**: Public web download `creams.iari.res.in` / `iari.res.in`.
- **Licensing**: Free Open Access.
- **Evidence Type**: **Event-level point coordinate maps & district-level daily counts**.
- **Matching Uncertainty**: Low ($\pm 375\text{ m}$, exact timestamp).

### 3.2 Punjab & Haryana Remote Sensing Centres (PRSC & HARSAC)
- **Provider**: PRSC (Ludhiana) & HARSAC (Hisar).
- **Product Name**: PRSC CRBIMS / HARSAC Active Fire Location (AFL) Mobile Verification System.
- **Geographic Coverage**: State-wide coverage of Punjab (23 districts) and Haryana (22 districts).
- **Temporal Coverage & Latency**: Daily updates during burning seasons.
- **Spatial Resolution**: 375 m satellite points overlaid on 1:4,000 scale revenue village Khasra maps.
- **Supported Classes**: Class 3 (Agricultural Fire).
- **Access Method**: WebGIS dashboards (`gis-prsc.punjab.gov.in`, `hsac.org.in`) / Institutional MoU.
- **Licensing**: State Government Data (Public dashboards open; raw parcel lists restricted).
- **Evidence Type**: **Field-verified parcel-level burn records & challan logs**.
- **Matching Uncertainty**: Very Low ($\pm 30\text{ m}$, exact date).

### 3.3 Sentinel-2 / Landsat HLS Parcel Burn Scar Pipeline
- **Provider**: ESA Copernicus / NASA HLSS30.
- **Product Name**: Sentinel-2 Level-2A Surface Reflectance (10m MIRBI / NBR2 burn index).
- **Geographic Coverage**: Pan-India agricultural belts.
- **Temporal Coverage & Latency**: 5-day revisit cycle.
- **Spatial Resolution**: 10 m (B4, B8) / 20 m (B11, B12).
- **Supported Classes**: Class 3 (Agricultural Fire).
- **Access Method**: Google Earth Engine / Copernicus Data Space Ecosystem API.
- **Licensing**: Open & Free (Copernicus / NASA).
- **Evidence Type**: **Physical parcel-level post-harvest burn scars**.
- **Matching Uncertainty**: Very Low ($\pm 10\text{ m}$, $\pm 2.5\text{ days}$).

---

## 4. Class 4: Other Thermal Source Reference Sources

### 4.1 VIIRS Nightfire (VNF) & World Bank Flaring Tracker
- **Provider**: Earth Observation Group (Payne Institute / Colorado School of Mines) & World Bank GGFR.
- **Product Name**: VIIRS Nightfire Daily Catalog / World Bank Individual Flare Location Database.
- **Geographic Coverage**: Pan-India onshore & offshore EEZ.
- **Temporal Coverage & Latency**: Daily nightly overpasses / 2012–2025 multi-year series.
- **Spatial Resolution**: Sub-pixel flare centroiding ($\approx 50\text{ m}$).
- **Supported Classes**: Class 4 (Other Thermal Source - Gas Flaring).
- **Access Method**: Open EOG portal `eogdata.mines.edu/products/vnf/` & World Bank data portal.
- **Licensing**: Free for research (CC BY 4.0 / Open Data).
- **Evidence Type**: **Continuous operational flaring coordinates & Planck temperatures** ($T = 1600\text{--}2200\text{ K}$).
- **Matching Uncertainty**: Very Low ($\pm 50\text{ m}$, multi-year persistence).

### 4.2 SentinelKilnDB (NeurIPS 2025 Benchmark) & UNDP GeoAI
- **Provider**: Sustainability Lab (IIT Gandhinagar) & UNDP India.
- **Product Name**: SentinelKilnDB (62,671 brick kilns mapped via 10m Sentinel-2).
- **Geographic Coverage**: Indo-Gangetic Plain and Central India ($> 2.8\text{ million km}^2$).
- **Temporal Coverage**: 2020–2025 contemporary operational inventory (Firing season: Dec–May).
- **Spatial Resolution**: 10 m Oriented Bounding Boxes (OBBs).
- **Supported Classes**: Class 4 (Other Thermal Source - Brick Kilns).
- **Access Method**: GitHub `sustainability-lab.github.io` / Zenodo repository.
- **Licensing**: CC BY-NC 4.0.
- **Evidence Type**: **Hand-validated brick kiln structural polygons & point centroids**.
- **Matching Uncertainty**: Very Low ($\pm 10\text{ m}$).

### 4.3 CMPDI / ISRO Coal Fire Shapefiles (Jharia & Raniganj)
- **Provider**: Central Mine Planning & Design Institute (CMPDI) & ISRO NRSC.
- **Product Name**: Jharia & Raniganj Surface Coal Fire Delineation Vector Shapefiles.
- **Geographic Coverage**: Jharia Coalfield ($450\text{ km}^2$), Raniganj, Singrauli.
- **Temporal Coverage**: Smoldering subsurface fires active continuously through 2025.
- **Spatial Resolution**: Colliery lease boundary shapefiles ($\pm 10\text{ m}$).
- **Supported Classes**: Class 4 (Other Thermal Source - Coal Fires).
- **Access Method**: Open Figshare repositories / ISRO Bhuvan coal mining portals.
- **Licensing**: CC BY 4.0 / Public Government Records.
- **Evidence Type**: **Polygon boundaries of chronic smoldering coal mining leases**.
- **Matching Uncertainty**: Low ($\pm 50\text{ m}$).

### 4.4 Global Energy Monitor (GEM) & CEA Power Plant Trackers
- **Provider**: Global Energy Monitor & Central Electricity Authority (CEA), Ministry of Power.
- **Product Name**: GEM Global Coal/Gas Plant Trackers & CEA CO2 Baseline Database (v21.0).
- **Geographic Coverage**: All utility-scale thermal power stations in India.
- **Temporal Coverage**: Continuous operational registry through 2025.
- **Spatial Resolution**: Unit-level boiler/generator coordinates ($\pm 20\text{ m}$).
- **Supported Classes**: Class 4 (Other Thermal Source - Power Plant Heat).
- **Access Method**: GEM portal `globalenergymonitor.org` & CEA portal `cea.nic.in`.
- **Licensing**: CC BY 4.0 / Open Government Data India.
- **Evidence Type**: **Authoritative point locations of operating thermal power stations**.
- **Matching Uncertainty**: Very Low ($\pm 20\text{ m}$).

### 4.5 GSI & MIROVA Barren Island Volcanic Database
- **Provider**: Geological Survey of India (GSI) & MIROVA (Univ. of Turin).
- **Product Name**: Barren Island Volcanic Radiative Power (VRP) Time Series.
- **Geographic Coverage**: Barren Island vent ($12.278^\circ\text{N}, 93.858^\circ\text{E}$).
- **Temporal Coverage**: Continuous monitoring; active eruptive phases in 2025.
- **Spatial Resolution**: Island vent area ($\pm 50\text{ m}$).
- **Supported Classes**: Class 4 (Other Thermal Source - Volcanic Activity).
- **Access Method**: MIROVA web portal `mirovaweb.it` & GSI publications.
- **Licensing**: Open Access / Public Domain.
- **Evidence Type**: **Continuous volcanic radiative flux logs**.
- **Matching Uncertainty**: Zero (Isolated island vent).

---

## 5. Summary Matrix Across All 4 Target Classes

| Class | Primary Reference Sources | Coverage in India | Label Yield Potential | Matching Latency / Uncertainty |
|---|---|---|---|---|
| **Class 1: Industrial Fire** | SEBI Reg 30 disclosures, SPCB/NGT orders, GDELT news stream, Sentinel-2/PlanetScope imagery | High in industrial corridors | 200–500 confirmed events/yr | $\pm 100\text{ m}$, $\pm 1\text{ day}$ |
| **Class 2: Forest Fire** | FSI FAST 3.0 / Van Agni, MODIS MCD64A1, HP/UK State Forest portals, Global Fire Atlas | 100% of Indian forest cover | $> 50,000$ confirmed fire clusters/yr | $\pm 375\text{ m}$, $\pm 1\text{ day}$ |
| **Class 3: Agricultural Fire** | ICAR-IARI CREAMS, PRSC CRBIMS, HARSAC, Sentinel-2 10m MIRBI burn scar pipeline | Indo-Gangetic Plain & Central India | $> 200,000$ burned field parcels/yr | $\pm 30\text{ m}$, $\pm 2.5\text{ days}$ |
| **Class 4: Other Thermal** | SentinelKilnDB (62k kilns), World Bank GGFR flaring, GEM power plants, CMPDI coal fires, GSI Barren Island | Pan-India | $> 80,000$ persistent thermal features | $\pm 20\text{ m}$ (Static coordinates) |
