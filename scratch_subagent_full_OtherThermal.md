# Reference Datasets & Ground Truth Evidence for "Other Thermal Sources" in India (2025 Study Corpus)

This research report documents independent reference datasets and authoritative sources providing ground-truth evidence for **"Other Thermal Sources"** in India for 2025. In accordance with `PROJECT_SPEC.md`, "other" thermal sources encompass stationary, non-forest, non-agricultural, and non-industrial disaster phenomena: **gas flaring, volcanic activity, coal seam fires, brick kilns, persistent thermal infrastructure, oil/gas refineries, and thermal power stations**.

These datasets are critical for establishing audited ground-truth labels ($y_i = -1$: confirmed non-industrial thermal anomaly; $y_i = +1$: confirmed industrial disaster incident; $y_i = 0$: unlabelled background) and preventing the **FIRMS Type Fallacy** and **Spatial Proximity Fallacy**.

---

## Comparative Dataset Matrix

| # | Domain / Source Category | Primary Product Name | Lead Provider / Institution | Spatial Precision | Coverage (India) | Update Cadence / 2025 Status | License | Data Format |
|---|---|---|---|---|---|---|---|---|
| 1 | Gas Flaring (VIIRS) | VIIRS Nightfire (VNF) Daily & Multiyear Catalog | Earth Observation Group (EOG), Payne Institute, Colorado School of Mines | 750 m M-bands (sub-pixel centroid $\sim 100\text{ m}$) | All India (Onshore + EEZ) | Nightly + Annual 2025 catalog | Open Research / Free Reg. | CSV (ezCSV), KMZ |
| 2 | Gas Flaring Tracker | Global Gas Flaring Tracker (Individual Flare Locations) | World Bank (GGFR / GFMR) & Payne Institute | Point coordinates ($\pm 10\text{--}50\text{ m}$) | All India oil/gas basins | Annual (2012–2025 series) | CC BY 4.0 | XLSX, CSV |
| 3 | Volcanic Activity | Barren Island Volcanic Database & MIROVA VRP | Geological Survey of India (GSI) & Smithsonian GVP / Univ. Turin | Vent centroid ($\pm 50\text{ m}$) / 375 m VIIRS | Barren Island ($12.278^\circ\text{N}, 93.858^\circ\text{E}$) | Continuous / Active in 2025 | Public Domain / CC0 / Open | HTML, CSV, PDF |
| 4 | Coal Seam Fires | Delineated Surface Coal Fire & Colliery Shapefiles | NRSC / ISRO, CMPDI, BCCL & Figshare Benchmarks | Colliery polygons ($\pm 10\text{ m}$) & 30–100 m TIR | Jharia, Raniganj, Bokaro, Singrauli | Quarterly (2025–2027 MoU) | CC BY 4.0 / OGD India | Shapefile, GeoJSON, XLSX |
| 5 | Brick Kiln Inventory | SentinelKilnDB (NeurIPS 2025) | Sustainability Lab, IIT Gandhinagar (Prof. Nipun Batra) | 10 m Sentinel-2 Oriented Bounding Boxes (OBB) | Indo-Gangetic Plain ($>2.8\text{M km}^2$, 62,671 kilns) | 2020–2025 benchmark | CC BY-NC 4.0 | GeoJSON, YOLO OBB, CSV |
| 6 | Brick Kiln / AI Bench | SustainBench (`m-brick-kiln`) & UNDP GeoAI | Stanford SAIL / FSE & UNDP India / Univ. Nottingham | High-res & 10 m Sentinel-2 | IGP ($>47,000$ kilns mapped) | Multi-year baseline | CC BY 4.0 / Open Access | GeoJSON, Shapefile, Zenodo |
| 7 | Industrial Emissions | Catalogue of Indian Emission Inventories & AEIM-India | TERI (The Energy and Resources Institute) & EDF | $0.1^\circ \times 0.1^\circ$ to $1\text{ km}$ gridded / Point | Pan-India / NCR / Major airsheds | Updated under NCAP (2024–2025) | CC BY 4.0 / Open Reports | NetCDF, XLSX, PDF |
| 8 | Persistent Thermal Mask | MODIS/VIIRS Static Hotspot & Industrial Heat Sources | NASA LANCE/FIRMS & ScienceDB / Academic Consortia | 375 m / 750 m / 1 km pixel centroids | Pan-India and Maritime EEZ | Continuous archive (2000–2025) | NASA Public Domain | CSV, Shapefile, GeoTIFF |
| 9 | Oil & Gas Infrastructure | Global Gas & Oil Infrastructure Trackers (GGIT / GOIT) | Global Energy Monitor (GEM) & PNGRB | Point facilities & Pipeline routes ($\pm 10\text{--}30\text{ m}$) | All 23 Refineries, 7 LNG Terminals, Pipelines | Bi-annually (2025/2026 releases) | CC BY 4.0 | XLSX, GeoJSON, Shapefile |
| 10 | Thermal Power Stations | Global Coal & Gas Plant Trackers (GCPT / GOGPT) | Global Energy Monitor (GEM) & WRI (GPPD) | Unit-level coordinates ($\pm 10\text{--}30\text{ m}$) | All operating thermal power stations in India | Semi-annually (2025/2026 releases) | CC BY 4.0 | XLSX, CSV, GeoJSON |
| 11 | Thermal Power Stations | CO2 Baseline Database for the Indian Power Sector | Central Electricity Authority (CEA), Ministry of Power | Plant & Unit registry (100% grid capacity) | All grid-connected thermal stations in India | Version 21.0 (Dec 2025; FY 2024-25) | Open Gov Data (OGD) | XLSX, PDF |

---

## Detailed Profile for Each Reference Source

### 1. VIIRS Nightfire (VNF) Product (Gas Flaring in India)
- **Provider**: Earth Observation Group (EOG), Payne Institute for Public Policy, Colorado School of Mines, Golden, CO, USA (formerly NOAA National Geophysical Data Center / NCEI).
- **Dataset / Product Name**: 
  - VIIRS Nightfire (VNF) Daily / Nightly Detections (V3.0 Operational, V4.0 Experimental).
  - Global Gas Flare Catalog (Annual and Multi-Year compilations, 2012–2025).
  - Historical reference: ORNL DAAC Global Gas Flare Survey by Infrared Imaging (DOI: `10.3334/ORNLDAAC/1874`).
- **Geographic Coverage**: Global ($180^\circ\text{W}$ to $180^\circ\text{E}$, $65^\circ\text{S}$ to $75^\circ\text{N}$); includes onshore India and offshore Exclusive Economic Zone (EEZ).
- **Temporal Coverage**: March 2012 to present. Daily nightly overpasses; annual consolidated catalogs through 2025.
- **Spatial Resolution / Precision**: Moderate-resolution VIIRS M-bands ($750\text{ m}$ nominal at nadir). Sub-pixel combustion centroiding yields emitter geolocational precision of $\approx 50\text{--}150\text{ m}$ for stationary flare stacks.
- **Access Method**:
  - EOG Data Portal: `https://eogdata.mines.edu/products/vnf/` and `https://eogdata.mines.edu/products/vnf/global_gas_flare.html`
  - Bulk scripted download via HTTPS / curl / Wget with free registered user credentials.
  - NASA Earthdata ORNL DAAC archive: `https://doi.org/10.3334/ORNLDAAC/1874`.
- **Licensing / Restrictions**: Open access for research and education. Attribution required: "Earth Observation Group, Payne Institute for Public Policy, Colorado School of Mines" (citing Elvidge et al., *Remote Sensing*, 2013, 2016). Full CSV downloads require free account registration.
- **Data Primitives**: Point locations with sub-pixel emitter area calculations (`Area_bb` in $\text{m}^2$) and daily timestamped event records.
- **Data Format**: Tabular CSV (`ezCSV` and full CSV), Google Earth KMZ, ASCII.
- **Key Attributes**: `ID`, `Lat_Centroid`, `Lon_Centroid`, `Temp_BB` (Planck blackbody temperature in Kelvin), `Area_BB` (combustion area in $\text{m}^2$), `Radiant_Heat_MW` (radiant power in MW), `BCM` (annual flaring volume), `Cloud_Mask`.
- **Reliability Assessment**: Gold standard for high-temperature sub-pixel combustion. Uses simultaneous Planck curve fitting across shortwave infrared (M7 0.86 µm, M8 1.24 µm, M10 1.61 µm) and midwave infrared (M12 3.7 µm, M13 4.05 µm). Gas flares burn at $1600\text{--}2200\text{ K}$, whereas biomass and forest fires burn at $600\text{--}1000\text{ K}$, enabling unambiguous separation of gas flares from wildfires and crop burns.

---

### 2. Global Gas Flaring Tracker (World Bank GGFR) for India
- **Provider**: The World Bank — Global Gas Flaring Reduction Partnership (GGFR) / Global Flaring and Methane Reduction Partnership (GFMR), in technical execution with the Payne Institute for Public Policy (Colorado School of Mines) and NOAA.
- **Dataset / Product Name**:
  - `Flare-Volume-Estimates-by-individual-Flare-Location-2012-2025.xlsx` (Site-level granular tracker).
  - `Flare-volume-and-intensity-estimates-2012-2025.xlsx` (Economy-level aggregated time series).
- **Geographic Coverage**: Global, covering all hydrocarbon-producing nations. In India, covers onshore basins (Assam-Arakan, Cambay/Gujarat, Barmer/Rajasthan, KG Basin, Cauvery Basin) and offshore assets (Mumbai High, Bassein, KG offshore).
- **Temporal Coverage**: 2012 through 2025 (annualized historical baseline; June 2026 report release incorporates the complete 2025 calendar year).
- **Spatial Resolution / Precision**: Point coordinates (`Latitude`, `Longitude`) rounded to 4–5 decimal places ($\approx 10\text{--}100\text{ m}$ geodetic accuracy), representing the multi-year spatial centroid of the flaring installation.
- **Access Method**: Direct public download from the World Bank GGFR portal:
  `https://www.worldbank.org/en/programs/gasflaringreduction/global-flaring-data`
  (No API key, subscription, or login required).
- **Licensing / Restrictions**: Creative Commons Attribution 4.0 International (CC BY 4.0) / World Bank Open Data Policy.
- **Data Primitives**: Point locations with annual flaring volume and detection frequency records.
- **Data Format**: Microsoft Excel (`.xlsx`), easily convertible to CSV / GeoJSON / Parquet.
- **Key Attributes**: `Flare_ID`, `Country` ("India"), `ISO_Code` ("IND"), `Latitude`, `Longitude`, `Offshore_Flag` (0/1), `Volume_2012` ... `Volume_2025` (in million $\text{m}^3$ / BCM), `Detection_Count`.
- **Reliability Assessment**: Extremely High. Cross-calibrated across three operational NOAA satellites (Suomi-NPP, NOAA-20, NOAA-21) and reconciled against official production and flaring declarations from the Ministry of Petroleum and Natural Gas (MoPNG). Serves as an indisputable reference for continuous, non-accidental operational flaring ($y_i = -1$).

---

### 3. Geological Survey of India (GSI) & Associated Volcanic Repositories (Barren Island)
- **Provider**:
  - National Lead: Geological Survey of India (GSI) — Marine & Coastal Survey Division (MCSD, Kolkata / Mangalore).
  - International Volcanology Authorities: Smithsonian Institution — Global Volcanism Program (GVP, Washington DC) & MIROVA (Middle InfraRed Observation of Volcanic Activity, University of Turin & Florence, Italy).
- **Dataset / Product Name**:
  - GSI: Marine Geology Cruise Reports, Bulletins, and Monographs on the Barren Island Volcanic Arc.
  - Smithsonian GVP: Volcano Profile No. 260010 (Barren Island), Weekly Volcanic Activity Reports, and Bulletin of the Global Volcanism Network (BGVN).
  - MIROVA: Barren Island Near-Real-Time Thermal Monitoring (Volcanic Radiative Power - VRP in MW).
  - HIGP MODVOLC: Global MODIS Thermal Alert System.
- **Geographic Coverage**: Barren Island, Andaman Sea, India ($12.278^\circ\text{N}, 93.858^\circ\text{E}$, summit elev. 354 m, $\sim 135\text{ km}$ NE of Port Blair). Note: Narcondam Island ($13.43^\circ\text{N}, 94.28^\circ\text{E}$) is dormant/extinct with 0 thermal anomalies.
- **Temporal Coverage**: Continuous monitoring. Barren Island has been in an ongoing eruptive phase throughout 2024 and 2025 (thermal hotspots confirmed in April, September, and post-monsoon 2025).
- **Spatial Resolution / Precision**: Island vent coordinates ($12.278^\circ\text{N}, 93.858^\circ\text{E}$, $\pm 50\text{ m}$) and satellite pixel footprints (375 m VIIRS, 1 km MODIS).
- **Access Method**:
  - GSI: Official portal `https://www.gsi.gov.in` and *Journal of the Geological Society of India* (`https://www.journalgsi.org`).
  - Smithsonian GVP: `https://volcano.si.edu/volcano.cfm?vn=260010`.
  - MIROVA: Web portal and CSV time-series download `https://www.mirovaweb.it/?action=volcanoSub&superV=31`.
  - MODVOLC: Query system `http://modis.higp.hawaii.edu/cgi-bin/modis/modisnew.cgi`.
- **Licensing / Restrictions**: GVP is public domain / CC0; MIROVA is open research data (CC BY 4.0); GSI reports are Government of India publications.
- **Data Primitives**: Point locations (vent coordinates), chronological event logs, and timestamped VRP radiative flux time-series.
- **Data Format**: HTML, CSV (MIROVA), PDF, KML.
- **Reliability Assessment**: Ground Truth Absolute Standard. Barren Island is completely uninhabited; every single thermal anomaly detected within a 5 km buffer of $12.278^\circ\text{N}, 93.858^\circ\text{E}$ is 100% volcanic. In FIRMS NOAA-20 VIIRS data, these pixels carry `type=1`. Provides clean ground-truth evidence for non-industrial volcanic thermal anomalies ($y_i = -1$).

---

### 4. Coal Fire Databases (Jharia Coalfield, Raniganj, Singrauli)
- **Provider**:
  - Bharat Coking Coal Limited (BCCL), Central Mine Planning & Design Institute (CMPDI), and Coal India Limited (CIL).
  - National Remote Sensing Centre (NRSC) / Indian Space Research Organisation (ISRO).
  - Figshare Academic GIS Repository & Global Energy Monitor (GEM).
- **Dataset / Product Name**:
  - NRSC-CMPDI-BCCL: "Delineation of Surface Coal Fire and Associated Land Subsidence in Jharia Coalfield" (Tripartite MoU 2025–2027) & Bhuvan CIL Geospatial Dashboard.
  - Figshare GIS Data: "Study area shapefiles - Jharia coalfield and colliery boundaries" (DOI: `10.6084/m9.figshare.15181143.v1`).
  - GEM: Global Coal Mine Tracker (Mine perimeter centroids and operating attributes).
- **Geographic Coverage**: Major Damodar Valley and Gondwana coal basins:
  - Jharia Coalfield (Dhanbad, Jharkhand; bounding box $23.63^\circ\text{N}\text{--}23.88^\circ\text{N}$, $86.15^\circ\text{E}\text{--}86.55^\circ\text{E}$; $\sim 450\text{ km}^2$).
  - Raniganj Coalfield (West Bengal / Jharkhand; $23.55^\circ\text{N}\text{--}23.85^\circ\text{N}$, $86.75^\circ\text{E}\text{--}87.35^\circ\text{E}$).
  - Bokaro, North/South Karanpura, Singrauli (MP/UP), Korba (Chhattisgarh), Ib Valley (Odisha).
- **Temporal Coverage**: Smoldering subsurface/opencast fires active since 1916; quarterly satellite mapping under the 2025–2027 NRSC-CMPDI operational MoU; GEM updated semi-annually through 2025/2026.
- **Spatial Resolution / Precision**:
  - Colliery lease boundaries: Vector polygons ($\pm 10\text{--}30\text{ m}$ boundary precision).
  - Satellite thermal sensors: Landsat-8/9 TIRS (100 m resampled to 30 m), ASTER TIR (90 m), Sentinel-2 SWIR (20 m), VIIRS I-4 (375 m).
- **Access Method**:
  - Figshare Shapefiles: Open download `https://figshare.com/articles/dataset/Study_area_shapefiles/15181143`.
  - Global Energy Monitor: Open download `https://globalenergymonitor.org/projects/global-coal-mine-tracker/`.
  - ISRO Bhuvan Portal: `https://bhuvan-app1.nrsc.gov.in/` (Analytical mining dashboard).
  - BCCL Master Plan Reports: `https://www.bcclweb.in`.
- **Licensing / Restrictions**: Figshare and GEM are CC BY 4.0; CMPDI/BCCL internal operational layers are restricted, but published statutory master plans and administrative colliery boundaries are public government records.
- **Data Primitives**: Polygons (colliery lease areas, coalfield boundaries, mapped fire contours) and Point locations (mine centroids, active thermal hotspots).
- **Data Format**: ESRI Shapefile (`.shp`, `.shx`, `.dbf`, `.prj`), GeoJSON, KML, XLSX.
- **Reliability Assessment**: Very High for coalfield boundaries and chronic burning colliery zones (e.g. Kusunda, Lodna, Katras, Sijua, PB Project). Coal fires exhibit smoldering combustion with moderate temperatures ($T \approx 400\text{--}700\text{ K}$) and months-to-years spatial persistence, differentiating them from acute industrial facility blazes.

---

### 5 & 10. South Asia Brick Kiln Mapping Datasets (Remote Sensing Benchmarks)
- **Provider**:
  1. Sustainability Lab, Indian Institute of Technology Gandhinagar (IITGN) — Prof. Nipun Batra, Rishabh Mondal et al.
  2. Stanford University — Sustainability & Artificial Intelligence Lab (SAIL) & Center on Food Security and the Environment (FSE) — Jihyeon Lee, Stefano Ermon, David Lobell et al.
  3. United Nations Development Programme (UNDP) Accelerator Lab India & University of Nottingham Rights Lab.
  4. SustainBench Consortium & GEO-Bench (Zenodo).
- **Dataset / Product Name**:
  - **SentinelKilnDB** (NeurIPS 2025 Datasets and Benchmarks Track): "A Large-Scale Dataset and Benchmark for Brick Kiln Detection in South Asia".
  - **Stanford Brick Kiln Dataset / SustainBench `m-brick-kiln`**: "Scalable deep learning to identify brick kilns and aid regulatory capacity" (PNAS 2021 / SustainBench 2022).
  - **UNDP GeoAI Brick Kiln Registry**: AI & Citizen Science (Zooniverse) inventory of $>47,000$ brick kilns across 12 Indian states.
- **Geographic Coverage**: South Asia, with massive coverage across Northern, Central, and Eastern India:
  - Indo-Gangetic Plain (Punjab, Haryana, Uttar Pradesh, Bihar, West Bengal, Delhi-NCR, Rajasthan, MP).
  - Total mapped area in SentinelKilnDB covers $>2.8\text{ million km}^2$ across India, Pakistan, Bangladesh, and Afghanistan.
- **Temporal Coverage**:
  - SentinelKilnDB: Derived from Sentinel-2 L2A multispectral imagery (2020–2025), hand-validated for contemporary operations.
  - Operational Seasonality: Kilns in India fire strictly during the dry winter/spring season (**December/January to May/June**); operations cease completely during the summer monsoon (July to October).
- **Spatial Resolution / Precision**:
  - SentinelKilnDB: Oriented Bounding Boxes (OBBs) derived from Sentinel-2 10 m multispectral bands (B2, B3, B4, B8). Individual kiln footprints are $50\text{--}150\text{ m}$ in length.
  - Coordinate precision: Sub-pixel geodetic accuracy ($\pm 5\text{--}10\text{ m}$).
- **Access Method**:
  - SentinelKilnDB: Open GitHub repository `https://github.com/rishabh-mondal/SENTINELKILNDB_NeurIPS_2025` and project page `https://sustainability-lab.github.io/`.
  - SustainBench / GEO-Bench: GitHub `https://github.com/sustainlab-group/sustainbench` and Zenodo DOI (`10.5281/zenodo.5786018`).
  - UNDP India: GeoAI dashboard reports and Bihar State Pollution Control Board regulatory dashboard (`https://www.undp.org/india`).
- **Licensing / Restrictions**: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) or CC BY 4.0.
- **Data Primitives**:
  - Oriented Bounding Boxes (OBBs - polygon geometry with angle/orientation).
  - Point centroid coordinates (`latitude`, `longitude`).
  - Kiln structural classification:
    1. Fixed Chimney Bull's Trench Kiln (FCBK)
    2. Circular FCBK (CFCBK)
    3. Zigzag Kiln (induced draft and natural draft)
- **Data Format**: GeoJSON, ESRI Shapefile, YOLO OBB annotations (normalized format), PyTorch datasets, CSV tables.
- **Reliability Assessment**: Benchmark Gold Standard (NeurIPS 2025). SentinelKilnDB contains **62,671 hand-validated brick kilns**, making it the largest open ground-truth dataset in existence. Crucial for thermal anomaly classification: brick kilns operate at $800\text{--}1050\text{ K}$, creating strong nighttime VIIRS I-band detections that peak from February to May. Cross-referencing VIIRS detections against SentinelKilnDB coordinates enables positive confirmation of $y_i = -1$ (non-industrial accident thermal source).

---

### 6. TERI (The Energy and Resources Institute) Datasets & Emission Inventories
- **Provider**: The Energy and Resources Institute (TERI), New Delhi, India; often in collaboration with Environmental Defense Fund (EDF), Central Pollution Control Board (CPCB), and State Pollution Control Boards (SPCBs).
- **Dataset / Product Name**:
  - Catalogue of Indian Emission Inventory Reports (EDF & TERI open database).
  - Anthropogenic Emission Inventory for India (AEIM-India) (hosted on ECCAD).
  - TERI National Clean Air Programme (NCAP) Comprehensive City & Regional Emission Inventories (covering NCR, Surat, Patna, Bengaluru, Assam industrial clusters).
  - TERI Sectoral Emission Factor Reports for Industrial Stacks, Brick Kilns (FCBTK vs. Zigzag), and Thermal Power Plants.
- **Geographic Coverage**: Pan-India national inventories and high-resolution domain inventories covering major industrial airsheds (Delhi-NCR, Indo-Gangetic Plain, Gujarat industrial corridor, Damodar Valley).
- **Temporal Coverage**: 2010 through 2024/2025 (updated under NCAP five-year action plans).
- **Spatial Resolution / Precision**:
  - Gridded spatial emission inventories: $0.1^\circ \times 0.1^\circ$ (approx. $10\text{ km} \times 10\text{ km}$), $4\text{ km} \times 4\text{ km}$, and down to $1\text{ km} \times 1\text{ km}$ over urban/industrial non-attainment zones.
  - Surveyed industrial point sources: Facility-level coordinates ($\pm 50\text{ m}$).
- **Access Method**:
  - TERI Bookstore / Open Research: `https://bookstore.teriin.org/` and `https://www.teriin.org/`.
  - ECCAD Database: `https://eccad.aeris-data.fr/` (AEIM-India inventory).
  - CPCB / NCAP portal: `https://prana.cpcb.gov.in/`.
- **Licensing / Restrictions**: Open access for published reports and research catalogues; gridded NetCDF files available on ECCAD under CC BY 4.0; specialized industrial consulting datasets available on direct institutional request.
- **Data Primitives**: Gridded raster surfaces (flux rates of $\text{PM}_{2.5}$, $\text{PM}_{10}$, $\text{SO}_2$, $\text{NO}_x$, $\text{CO}$, Black Carbon), facility point lists, and technology-specific emission factor lookup tables.
- **Data Format**: NetCDF (`.nc`), Microsoft Excel (`.xlsx`), CSV, PDF reports.
- **Reliability Assessment**: Very High for emission apportionment and industrial technology baselines. Developed using ground stack monitoring, regulatory CPCB data, and localized fuel consumption statistics. Provides essential priors for expected continuous thermal/emissions loads from legitimate industrial activity.

---

### 7. Persistent Thermal Anomaly Databases & Static Mask Products
- **Provider**:
  - NASA LANCE / FIRMS (University of Maryland / NASA Goddard Space Flight Center).
  - Copernicus Atmosphere Monitoring Service (CAMS) / ECMWF — Global Fire Assimilation System (GFAS).
  - International Remote Sensing Research Consortiums (e.g. ScienceDB Global Industrial Heat Source datasets, Liu et al. 2021–2024).
- **Dataset / Product Name**:
  - NASA FIRMS Active Fire / Hotspot Type Attribute (in MODIS MCD14ML and VIIRS VNP14IMG / VJ114IMG / VJ214IMG):
    - `type = 0`: Presumed vegetation fire
    - `type = 1`: Active volcano
    - `type = 2`: Other static land source (industrial / flare / coal seam)
    - `type = 3`: Offshore detection
  - MODIS Static Hotspot Mask (derived from multi-year MCD14ML persistence filtering; Giglio et al. Collection 6 / 6.1).
  - Global Industrial Heat Sources (IHS) Dataset (VIIRS 375 m multi-temporal object-oriented clustering).
- **Geographic Coverage**: Global, comprehensive for all 3.287 million $\text{km}^2$ of India and surrounding maritime EEZ.
- **Temporal Coverage**: 2000–present (MODIS Terra/Aqua), 2012–present (VIIRS S-NPP), 2018–present (VIIRS NOAA-20), 2023–present (VIIRS NOAA-21).
- **Spatial Resolution / Precision**:
  - VIIRS 375 m pixel center coordinates (WGS-84 decimal degrees).
  - MODIS 1 km pixel center coordinates.
- **Access Method**:
  - NASA FIRMS Archive Download Tool: `https://firms.modaps.eosdis.nasa.gov/download/`
  - NASA Earthdata Search: `https://search.earthdata.nasa.gov/`
  - CAMS Atmospheric Data Store: `https://ads.atmosphere.copernicus.eu/`
  - ScienceDB: `https://www.scidb.cn/`
- **Licensing / Restrictions**: NASA Open Data Policy (public domain, unrestricted, completely free).
- **Data Primitives**: Event records (individual sensor pixel detections) and derived static spatial masks (point clusters or raster masks).
- **Data Format**: CSV, ESRI Shapefile, GeoTIFF masks, NetCDF.
- **Reliability Assessment**: High for spatial persistence detection; Moderate for semantic classification. As mandated by `PROJECT_SPEC.md` Section 10.1 ("FIRMS Type Fallacy"), raw `type` flags are sensor heuristics rather than audited ground truth. However, when aggregated causally (e.g., detecting persistent thermal recurrence at the exact same coordinate over multiple months with high brightness temperature), this dataset accurately pinpoints stationary, non-transient thermal infrastructure.

---

### 8. Oil & Gas Infrastructure Maps for India (Refineries, LNG Terminals, Pipelines)
- **Provider**:
  - Petroleum and Natural Gas Regulatory Board (PNGRB), Government of India.
  - Petroleum Planning & Analysis Cell (PPAC), Ministry of Petroleum and Natural Gas (MoPNG).
  - Global Energy Monitor (GEM) — Global Gas Infrastructure Tracker (GGIT) & Global Oil Infrastructure Tracker (GOIT).
  - OpenStreetMap (OSM) Contributors / Geofabrik.
- **Dataset / Product Name**:
  - GEM GGIT: Global Gas Infrastructure Tracker (LNG terminals and gas transmission pipelines).
  - GEM GOIT: Global Oil Infrastructure Tracker (Crude oil pipelines, petroleum product pipelines, refineries).
  - PNGRB: Natural Gas Pipeline Infrastructure Network Maps & National Hydrocarbons Infrastructure Monitoring System (NHIMS).
  - PPAC: Directory of Refineries in India & Monthly Petroleum Logistics Reports.
  - OpenStreetMap: Curated layers for `industrial=refinery`, `man_made=flare`, `pipeline=submersible/gas/oil`.
- **Geographic Coverage**: All of India (23 operating refineries, 7 operational LNG import terminals, $\sim 35,000\text{ km}$ of authorized gas pipelines, $\sim 20,000\text{ km}$ of product/crude pipelines).
- **Temporal Coverage**: Operational assets current through 2025/2026 (GEM updated semi-annually; PNGRB MIS published monthly; PPAC published monthly).
- **Spatial Resolution / Precision**:
  - GEM & OSM: High-precision point locations and polygon boundaries accurate to $\pm 10\text{--}30\text{ m}$, verified against high-resolution optical imagery.
  - PNGRB: Line strings and schematic nodal positions.
- **Access Method**:
  - Global Energy Monitor: Direct open download `https://globalenergymonitor.org/download-data/` (XLSX and GIS format).
  - OpenStreetMap: Overpass Turbo API (`https://overpass-turbo.eu/`) using Overpass QL, or Geofabrik India PBF extract (`https://download.geofabrik.de/asia/india.html`).
  - PNGRB: Official Portal `https://www.pngrb.gov.in` (Data Bank / Gas Infra Map).
  - PPAC: Official Portal `https://ppac.gov.in`.
- **Licensing / Restrictions**:
  - GEM: Creative Commons Attribution 4.0 International (CC BY 4.0).
  - OpenStreetMap: Open Database License (ODbL).
  - PNGRB & PPAC: Government of India Open Access / Public Record.
- **Data Primitives**:
  - Point locations: Refinery centroids, LNG jetty berths, compressor stations, metering stations.
  - Polygons: Industrial facility boundary perimeters in OpenStreetMap.
  - LineStrings: Pipeline transmission corridors.
- **Data Format**: ESRI Shapefile, GeoJSON, XLSX, KML, OSM XML/PBF.
- **Reliability Assessment**: Extremely High. Coordinates of every major refinery (e.g. Jamnagar, Vadinar, Panipat, Paradip, Koyali, Kochi, Visakhapatnam, Mumbai, Haldia) are definitively verifiable against optical satellite imagery (Sentinel-2, PlanetScope, Google Earth). Crucial GIS context for identifying whether a thermal detection falls within a permanent petrochemical perimeter.

---

### 9. Known Continuous Flaring Sites in India (Detailed Facility Inventory)
A rigorous inventory of known continuous and semi-continuous flaring sites across upstream extraction, midstream processing, and downstream refining in India:
1. **Upper Assam Onshore Basin (OIL & ONGC)**:
   - Primary Facilities: Duliajan Central Gas Gathering Station, Moran OCS, Lakwa GGS, Geleki GGS, Rudrasagar GGS, Borholla GGS, Naharkatiya Oilfield, Dikom EPF, Jorajan GGS, Hapjan, Makum.
   - Operating Environment: Dense evergreen tropical forest and agricultural tea estates.
   - Thermal Signature: Continuous low-to-medium volume flaring of associated petroleum gas (APG); high Planck temperatures ($T > 1600\text{ K}$).
2. **Western Offshore Basin (ONGC)**:
   - Primary Facilities: Mumbai High North (MHN), Mumbai High South (MHS), Bassein (BPA, BPB, B-193), Neelam, Heera, Ratna, Mukta, Panna.
   - Operating Environment: Arabian Sea ($\sim 160\text{ km}$ west of Mumbai coast).
   - Thermal Signature: Persistent offshore flaring tagged with FIRMS `type=3`; extreme radiant power (FRP often $> 50\text{ MW}$).
3. **Cambay Basin Onshore Gujarat (ONGC)**:
   - Primary Facilities: Ankleshwar GGS, Gandhar GGS, Mehsana Asset (Sobhasan, Santhal, Lanwa), Kalol, Nawagam, Sanand, Hazira Gas Processing Plant.
   - Operating Environment: Alluvial plains / heavy industrial belt.
   - Thermal Signature: Stationary continuous flare stacks with continuous nighttime detections.
4. **Barmer Basin Onshore Rajasthan (Cairn Oil & Gas / Vedanta)**:
   - Primary Facilities: Mangala Processing Terminal (MPT, Barmer), Bhagyam, Aishwarya, Raageshwari Deep Gas (RDG) Plant.
   - Operating Environment: Thar Desert arid terrain.
   - Thermal Signature: Stationary high-efficiency enclosed and elevated flare stacks.
5. **Krishna-Godavari (KG) Basin Onshore & Offshore (ONGC & Reliance)**:
   - Primary Facilities: Tatipaka Mini-Refinery & Gas Plant (East Godavari), Odalarevu Terminal (ONGC), Gadimoga Gas Terminal (Reliance KG-D6 onshore terminal), Ravva Offshore Platform (Cairn/ONGC), KG-DWN-98/2 FPSO Armada Sterling V (ONGC).
   - Operating Environment: Godavari Delta wetlands and Bay of Bengal deepwater.
6. **Cauvery Basin Onshore Tamil Nadu (ONGC)**:
   - Primary Facilities: Narimanam GGS, Kuttalam Gas Collection Station, Bhuvanagiri GGS.
7. **Downstream Refineries (Continuous Pilot / Process Flare Stacks)**:
   - Jamnagar Refinery (Reliance, Gujarat, $68.2\text{ MTPA}$) — multiple heavy flare stacks.
   - Vadinar Refinery (Nayara, Gujarat, $20\text{ MTPA}$).
   - Paradip Refinery (IOCL, Odisha, $15\text{ MTPA}$).
   - Panipat Refinery (IOCL, Haryana, $15\text{ MTPA}$).
   - Koyali / Gujarat Refinery (IOCL, Vadodara, $13.7\text{ MTPA}$).
   - Kochi Refinery (BPCL, Kerala, $15.5\text{ MTPA}$).
   - Mumbai Refineries (BPCL $12\text{ MTPA}$ & HPCL $9.5\text{ MTPA}$, Chembur/Trombay).
   - Mangalore Refinery (MRPL, Karnataka, $15\text{ MTPA}$).
   - Guru Gobind Singh Refinery (HMEL, Bathinda, Punjab, $11.3\text{ MTPA}$).
   - Bina Refinery (BPCL, Madhya Pradesh, $7.8\text{ MTPA}$).
   - Haldia Refinery (IOCL, West Bengal, $8.0\text{ MTPA}$).
   - Visakhapatnam Refinery (HPCL, Andhra Pradesh, $15\text{ MTPA}$).
   - Manali / Chennai Refinery (CPCL, Tamil Nadu, $10.5\text{ MTPA}$).
   - Assam Refineries: Digboi (India's oldest), Guwahati, Bongaigaon, Numaligarh.
- **Reliability Assessment**: Ground Truth Verified. The physical presence of elevated flare stacks at these exact coordinates is confirmed by satellite optical imagery and World Bank GGFR flaring catalogs. Crucial invariant: routine flaring at these sites represents operational non-accidental baseline ($y_i = -1$), not emergency industrial disasters ($y_i = +1$).

---

### 11. Thermal Power Plant Locations Databases
- **Provider**:
  1. Central Electricity Authority (CEA), Ministry of Power, Government of India.
  2. National Power Portal (NPP), Government of India.
  3. Global Energy Monitor (GEM) — Global Coal Plant Tracker (GCPT) & Global Oil and Gas Plant Tracker (GOGPT).
  4. World Resources Institute (WRI) — Global Power Plant Database (GPPD).
- **Dataset / Product Name**:
  - CEA: CO2 Baseline Database for the Indian Power Sector (Version 21.0 published Dec 2025; Version 20.0 published Dec 2024).
  - NPP: Daily Thermal Power Plant Generation & Status Database.
  - GEM GCPT: Global Coal Plant Tracker (comprehensive coal-fired power station unit catalog).
  - GEM GOGPT: Global Oil and Gas Plant Tracker (gas-turbine and combined-cycle power station unit catalog).
  - WRI GPPD: Global Power Plant Database (Version 1.3.0).
- **Geographic Coverage**: Complete Pan-India coverage. Encompasses all utility-scale grid-connected coal, lignite, gas, and liquid fuel thermal stations across India ($>215\text{ GW}$ coal/lignite, $>25\text{ GW}$ gas).
- **Temporal Coverage**:
  - CEA CO2 Database: Annual reports up to FY 2024-25 (published Dec 2025).
  - GEM GCPT/GOGPT: Semi-annually updated (current through 2025/2026).
  - NPP: Daily and monthly live updates.
  - WRI GPPD: Baseline through 2021 (v1.3.0).
- **Spatial Resolution / Precision**:
  - GEM & WRI: Exact geodetic latitude and longitude coordinates ($\pm 10\text{--}50\text{ m}$ accuracy, situated at the boiler/turbine hall or cooling tower cluster).
  - CEA: Plant, unit, district, and state identifiers.
- **Access Method**:
  - CEA Portal: `https://cea.nic.in/cdm-co2-baseline-database/` (Downloadable Excel `.xlsx` files and PDF User Guides).
  - Global Energy Monitor: `https://globalenergymonitor.org/download-data/` (Downloadable Excel `.xlsx` and GeoJSON files).
  - WRI GitHub: `https://github.com/wri/global-power-plant-database` (Direct download of `database_IND.csv`).
  - NPP Portal: `https://npp.gov.in`.
- **Licensing / Restrictions**:
  - CEA & NPP: Open Government Data (OGD) India / Government of India open access.
  - GEM: Creative Commons Attribution 4.0 International (CC BY 4.0).
  - WRI: Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Data Primitives**: Point locations for each power station, disaggregated by individual operating boiler/generator units.
- **Physical Parameter Schema**:
  - `Plant_Name`, `Unit_No`, `Utility_Owner` (e.g. NTPC, Adani Power, Tata Power, State Gencos).
  - `Latitude`, `Longitude` (WGS-84).
  - `Capacity_MW`: Installed electric capacity in Megawatts.
  - `Fuel_Type`: Sub-bituminous coal, Lignite, Natural Gas, Diesel/Heavy Fuel Oil.
  - `Boiler_Technology`: Subcritical, Supercritical, Ultra-Supercritical, Circulating Fluidized Bed Combustion (CFBC).
  - `Commissioning_Year`, `Operating_Status` (Operating, Construction, Retired, Shelved).
  - `Annual_Generation_GWh`, `Specific_CO2_Intensity` ($\text{tCO}_2/\text{MWh}$).
- **Reliability Assessment**: Absolute 100% Comprehensive Registry. Every single utility thermal power plant in India is tracked by the Central Electricity Authority. GEM adds high-resolution independent geospatial verification. In satellite thermal monitoring, operational thermal power plants emit intense cooling water/flue gas thermal plumes, creating chronic thermal anomalies that must be classified as normal operational thermal infrastructure ($y_i = -1$) unless an uncontained boiler explosion or coal stockyard fire occurs.

---

## Actionable Integration Protocol for the 2025 Study Corpus

1. **Stationary Background Exclusion ($y_i = -1$ Auditing)**:
   - Ingest `SentinelKilnDB` (62,671 kilns) and World Bank `Flare-Volume-Estimates-by-individual-Flare-Location-2012-2025.xlsx`.
   - Cross-reference with NOAA-20 VIIRS 2025 detections using an exact spatial radius ($R = 500\text{ m}$ for kilns; $R = 1000\text{ m}$ for flare stacks).
   - Observations matching known operating brick kilns (active Dec–May) or verified gas flares should be positively designated as $y_i = -1$ (non-industrial accident).
2. **Volcanic Filter**:
   - Detections within 5 km of Barren Island ($12.278^\circ\text{N}, 93.858^\circ\text{E}$) with `type=1` are confirmed volcanic emissions ($y_i = -1$).
3. **Coal Seam Fire Separation**:
   - Detections falling inside Jharia and Raniganj colliery polygons with multi-month spatial recurrence represent chronic coal seam smoldering, distinguishing them from sudden industrial chemical fires.
4. **Thermal Power Station Baselines**:
   - Use GEM GCPT/GOGPT and CEA Version 21.0 coordinates to identify legitimate power plant stacks and cooling units. Detections at these sites during continuous power dispatch reflect baseline operating heat ($y_i = -1$).
5. **Preserving Model Integrity**:
   - Maintain strict independence: GIS layers and external catalogs serve solely for independent label verification and external context fusion, never as pseudo-labeling spatial proximity heuristics during raw preprocessing.