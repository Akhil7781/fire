# Comprehensive Research Report: Independent Reference Datasets and Ground Truth Sources for Agricultural Fires (Crop Residue / Stubble Burning) in India (2025 Focus)

---

## Executive Summary & Landscape Overview

In India, monitoring of agricultural fires—chiefly post-monsoon (Kharif) paddy stubble burning in October–November and pre-monsoon (Rabi) wheat stubble burning in April–May—is governed under a coordinated national protocol established by the **Commission for Air Quality Management (CAQM)**, **ISRO**, **ICAR-IARI**, and the respective State Remote Sensing Centres (**PRSC** in Punjab, **HARSAC** in Haryana). 

Independent validation and ground-truth evidence for 2025 exist at three distinct tiers:
1. **Publicly Downloadable Immediately:** IARI-CREAMS daily bulletins (2020–2025), NASA FIRMS VIIRS/MODIS active fire point archives, Sentinel-2/Landsat-8/9 surface reflectance imagery via Copernicus Data Space and Google Earth Engine (GEE), NGT judicial orders and judgments, and open academic datasets on Zenodo/Figshare/Kaggle.
2. **Viewable via Interactive WebGIS / Scrapable:** PRSC CRBIMS WebGIS portal, IARI CREAMS active fire dashboard, and IITM-SAFAR/DSS daily source-attribution dashboards.
3. **Requestable for Research (Institutional MOU or RTI):** Field-level ground verification logs (collected by flying squads, cluster nodal officers, and patwaris via mobile apps like *e-Prevent* and *HARSAC App*), cadastral parcel/khasra linkages, and official Environmental Compensation (EC) challan registers.

Below is the detailed documentation for all ten requested sources, evaluated across the required 10 attributes.

---

## Detailed Evaluation of Reference Sources

### 1. CPCB (Central Pollution Control Board) Crop Residue Burning Monitoring System
* **Provider Organization:** Central Pollution Control Board (CPCB), Ministry of Environment, Forest and Climate Change (MoEFCC), Government of India, in coordination with the Commission for Air Quality Management in NCR & Adjoining Areas (CAQM).
* **Dataset / Product Name:** Crop Residue Burning Flying Squad Ground Monitoring Dossiers & Inter-State Air Quality Inspection Reports / PRANA NCAP Monitoring System.
* **Geographic Coverage:** Hotspot agricultural districts across Punjab (16–18 districts including Sangrur, Bathinda, Firozpur, Ludhiana, Patiala, Amritsar, Tarn Taran) and Haryana (10–13 districts including Karnal, Kaithal, Kurukshetra, Fatehabad, Jind, Sirsa), plus Delhi-NCR.
* **Temporal Coverage:** Intensive daily deployment during the Kharif paddy burning window (September 15 – November 30) and Rabi wheat burning window (April 1 – May 15); operational through 2024 and fully active during 2025.
* **Spatial Resolution:** Field-level GPS coordinates collected during on-site physical inspections; aggregated to block, district, and state levels in published dossiers.
* **Access Method:**
  * Public portal: `https://cpcb.nic.in` and PRANA portal `https://prana.cpcb.gov.in/`.
  * Official daily reviews and press releases via the Press Information Bureau (PIB: `https://pib.gov.in`).
  * Raw ground inspection logs, geo-tagged photos, and flying squad registers are available for research upon formal request to Member Secretary, CPCB / CAQM, or via Right to Information (RTI) applications under the RTI Act, 2005.
* **Licensing / Restrictions:** Government of India Open Data Principles for summary statistics; raw inspection logs and enforcement files are restricted administrative documents.
* **Field-Level vs. Aggregated:** 
  * *Public outputs:* District-wise and state-wise aggregated counts, number of flying squads deployed, and compliance percentages.
  * *Internal data:* Individual field-level inspection logs with geo-tagged photographic evidence, date/time, farmer details, and ground verification status (true fire vs. false alarm).
* **Data Format:** PDF summary reports, press releases, tabular affidavits submitted to CAQM/Courts.
* **Temporal Precision:** Daily field inspections; reports compiled and communicated every evening to central control rooms.

---

### 2. Punjab Remote Sensing Centre (PRSC) Fire Count Data
* **Provider Organization:** Punjab Remote Sensing Centre (PRSC), Department of Agriculture & Farmers Welfare, Government of Punjab (PAU Campus, Ludhiana).
* **Dataset / Product Name:** Crop Residue Burning Information and Management System (CRBIMS) / *e-Prevent* Stubble Burning Surveillance System.
* **Geographic Coverage:** Complete coverage of all 23 districts in Punjab (Indo-Gangetic Plain).
* **Temporal Coverage:** Multi-year time series from 2016 to 2024; active and updated daily during 2025 burning seasons.
* **Spatial Resolution:**
  * Satellite input: 375 m (VIIRS I-band), 750 m (VIIRS M-band), 1 km (MODIS), 1 km (Sentinel-3 SLSTR).
  * Burn scar verification: 10 m / 20 m (Sentinel-2 MSI) and 30 m (Landsat 8/9).
  * Field verification: GPS point precision (~3–5 m).
* **Access Method:**
  * Official WebGIS Portal: `http://gis-prsc.punjab.gov.in/residue/Index.aspx` and `https://prsc.punjab.gov.in/`.
  * Automated SMS/app push alerts to Deputy Commissioners (DCs), Senior Superintendents of Police (SSPs), and Nodal Officers.
  * Research data requests: Written application to the Director, PRSC Ludhiana (`director@prsc.gov.in`).
  * Open mirror datasets: Daily district-wise CRBIMS fire counts are mirrored by researchers on platforms like Kaggle (e.g., *Punjab Stubble Burning Crop Fire Data 2022–2024/2025*).
* **Licensing / Restrictions:** State Government proprietary data. Public dashboard displays aggregate numbers; full coordinate-level datasets and cadastral boundary overlays require institutional authorization or formal data-sharing agreements (MoU).
* **Field-Level vs. Aggregated:** Both. The internal GIS database contains exact event-level point coordinates (lat/long, satellite pass, time, village, tehsil, district). The public web interface provides district and tehsil aggregated counts and interactive spatial density heatmaps.
* **Data Format:** Interactive WebGIS (GeoServer / Leaflet / OpenLayers), downloadable daily PDF bulletins, CSV/Excel summaries, ESRI Shapefiles (for internal/research use).
* **Temporal Precision:** Daily, pass-by-pass (multiple satellite overpasses per day: ~10:30 Terra, ~13:30 Aqua/SNPP, ~14:10 NOAA-20, plus night passes).

---

### 3. Haryana Space Applications Centre (HARSAC) Agricultural Fire Data
* **Provider Organization:** Haryana Space Applications Centre (HARSAC), Department of Science & Technology, Government of Haryana (CCS HAU Campus, Hisar).
* **Dataset / Product Name:** HARSAC Active Fire Locations (AFL) Monitoring System & HARSAC Crop Residue Mobile Verification App.
* **Geographic Coverage:** All 22 districts of Haryana state (special focus on high-intensity agricultural districts: Fatehabad, Kaithal, Jind, Karnal, Kurukshetra, Ambala, Sirsa).
* **Temporal Coverage:** Historical archives from 2016 through 2024; operational during 2025 Kharif (Sept 15 – Nov 30) and Rabi (April 1 – May 31).
* **Spatial Resolution:** 375 m (VIIRS) and 1 km (MODIS), overlaid on high-resolution cadastral (revenue) village maps (scale 1:4,000 to 1:10,000) linking fires to specific land parcels (Murabba/Khasra numbers).
* **Access Method:**
  * Official Portal: `https://hsac.org.in` and Agriculture Department Haryana (`https://agriharyana.gov.in`).
  * Real-time automated transmission to district control rooms, Sub-Divisional Magistrates (SDMs), and Village Patwaris.
  * Research access: Written petition to Director, HARSAC, CCS HAU Campus, Hisar, or state RTI portal.
* **Licensing / Restrictions:** Official government use. Dashboard summaries released to press; field-level khasra-linked lists are confidential enforcement records.
* **Field-Level vs. Aggregated:** 
  * *Operational level:* Individual event-level AFLs mapped to specific field parcels for ground-truthing and legal penalties (Environmental Compensation, FIRs, and "red entries" in land records).
  * *Public level:* District-level daily and cumulative fire counts.
* **Data Format:** GIS layers (Shapefile, GeoJSON), daily administrative PDF/Excel reports, internal mobile app database entries (PostgreSQL/PostGIS).
* **Temporal Precision:** Near-real-time (daily; alerts generated within 2 to 4 hours of satellite overpass).

---

### 4. IARI (Indian Agricultural Research Institute) Fire Monitoring
* **Provider Organization:** Division of Agricultural Physics, ICAR - Indian Agricultural Research Institute (IARI), New Delhi (under Indian Council of Agricultural Research, MoAFW).
* **Dataset / Product Name:** Satellite-Based Monitoring of Active Fire Events (AFEs) in Agriculture / Daily Crop Residue Burning Bulletins.
* **Geographic Coverage:** 6 Northern and Central Indian States/UTs: Punjab, Haryana, Uttar Pradesh, Rajasthan, Madhya Pradesh, and NCT of Delhi.
* **Temporal Coverage:** Multi-year archived bulletins (2020–2024) and continuously published daily throughout the 2025 burning seasons (Kharif: Sept 15 – Nov 30; Rabi: April 1 – May 31).
* **Spatial Resolution:** 375 m (VIIRS on Suomi-NPP and NOAA-20) and 1,000 m (MODIS on Terra and Aqua); Sentinel-3 SLSTR at 1 km.
* **Access Method:**
  * Freely downloadable directly from IARI website: `https://iari.res.in` (under "Crop Residue Burning Bulletins" / "CREAMS").
  * Also accessible via the ICAR KRISHI Geoportal (`http://krishi.icar.gov.in`).
  * No login, paywall, or credentials required to download daily PDF bulletins.
* **Licensing / Restrictions:** Open public access for non-commercial research, academic, and policy analysis purposes. Citing ICAR-IARI is required.
* **Field-Level vs. Aggregated:** 
  * *Bulletins:* Present district-wise daily counts, cumulative comparative tables (current year vs. prior 4 years), and state-level geographic scatter maps of detected fire points.
  * *Underlying archive:* Contains discrete event-level point coordinates (lat, long, acquisition time, satellite platform, sensor band, and Fire Radiative Power - FRP in MW).
* **Data Format:** Standardized multi-page PDF bulletins (published daily), high-resolution spatial distribution maps, and summary tables.
* **Temporal Precision:** Daily composite (published every evening by ~18:00 IST incorporating all day passes from 00:00 to ~16:00 IST).

---

### 5. CREAMS (Consortium for Research on Agroecosystem Monitoring and Modeling from Space) Data
* **Provider Organization:** CREAMS Laboratory, Division of Agricultural Physics, ICAR-IARI, New Delhi.
* **Dataset / Product Name:** CREAMS Geoportal & Active Fire Event (AFE) Dashboard / Burnt Area Assessment Database.
* **Geographic Coverage:** Northern and Central India (Punjab, Haryana, UP, Rajasthan, MP, Delhi), with pan-India expansion for major agricultural belts.
* **Temporal Coverage:** Archived records from 2016 through 2024, fully active for 2025.
* **Spatial Resolution:** Active thermal anomalies at 375 m (VIIRS) and 1 km (MODIS); Burnt Area Assessments utilizing 10 m / 20 m (Sentinel-2) and 23.5 m (ISRO Resourcesat LISS-III/AWiFS).
* **Access Method:**
  * Official Geoportal URL: `https://creams.iari.res.in` or `http://creams.iari.res.in/`.
  * Public interactive dashboard allows filtering by date range, state, district, and satellite platform.
  * Direct web access to the "List of All Bulletins" repository.
  * Geospatial vector layers (Shapefiles/GeoTIFFs) can be requested for academic research by contacting: In-charge, CREAMS, Division of Agricultural Physics, IARI, Pusa, New Delhi 110012.
* **Licensing / Restrictions:** Open access for web visualization, statistical dashboards, and PDF reports. Raw GIS shapefiles/rasters available for academic research upon formal request.
* **Field-Level vs. Aggregated:** Both. The geoportal plots discrete event-level point coordinates (exact latitude, longitude, satellite sensor, acquisition time, brightness temperature, and FRP) while providing automated district-level and state-level aggregations.
* **Data Format:** WebGIS dynamic layers (Mapbox/Leaflet), downloadable PDF bulletins, CSV/XLS data summaries.
* **Temporal Precision:** Daily, tagged with satellite overpass timestamps (~10:30 AM MODIS Terra, ~01:30 PM MODIS Aqua/VIIRS Suomi-NPP, ~02:10 PM VIIRS NOAA-20).

---

### 6. Ministry of Agriculture & Farmers Welfare Crop Residue Burning Records
* **Provider Organization:** Ministry of Agriculture & Farmers Welfare (MoAFW), Government of India, in joint partnership with the Department of Space (ISRO/NRSC).
* **Dataset / Product Name:**
  1. **Krishi-Decision Support System (Krishi-DSS)** – Crop Residue Burning & Harvest Watch Module (launched August 2024, operational 2025).
  2. **Crop Residue Management (CRM) Scheme Implementation Database** (`agrimachinery.nic.in`).
  3. **Parliamentary Unstarred Questions Database** (Lok Sabha / Rajya Sabha official records).
* **Geographic Coverage:** Pan-India; high-density operational focus on Punjab, Haryana, Uttar Pradesh, Rajasthan, and MP.
* **Temporal Coverage:** Historical CRM scheme tracking from 2018; Krishi-DSS operational throughout 2024–2025.
* **Spatial Resolution:** Cadastral parcel/field boundary level (Krishi-DSS uses automated parcel segmentation to detect individual field harvest status) up to village, CHC (Custom Hiring Centre), and district levels.
* **Access Method:**
  * Krishi-DSS portal: `https://krishi-dss.gov.in` (access managed via departmental/institutional credentials).
  * CRM Scheme Portal: `https://agrimachinery.nic.in/`.
  * Parliamentary question search: `https://sansad.in` (search "crop residue burning", "stubble burning", or "happy seeder").
  * PIB press archives: `https://pib.gov.in`.
* **Licensing / Restrictions:** Public access for aggregated scheme data, subsidy disbursements, machine registries, and parliamentary tables. Farmer-specific parcel identifiers and bank/subsidy registries are confidential.
* **Field-Level vs. Aggregated:**
  * *Krishi-DSS:* Field-parcel level identification of crop harvesting status and post-harvest residue burns.
  * *CRM/Parliamentary records:* Village-, CHC-, district-, and state-level aggregated statistics (number of machines distributed, bio-decomposer acreage, total expenditure, and validated burning counts).
* **Data Format:** Web dashboards, PDF operational guidelines and annual reports, CSV/Excel parliamentary statistical annexures.
* **Temporal Precision:** Krishi-DSS is updated in near-real-time / daily; CRM mechanization records are updated continuously/monthly.

---

### 7. National Green Tribunal (NGT) Agricultural Burning Enforcement Records
* **Provider Organization:** National Green Tribunal (Principal Bench, New Delhi), CAQM, and State Pollution Control Boards (PPCB, HSPCB, UPPCB, DPCC).
* **Dataset / Product Name:** Judicial Proceedings, State Action Taken Reports (ATRs), Compliance Affidavits, and Inquiries in *Original Application No. 21/2014 (Vardhaman Kaushik vs. Union of India)*, *O.A. No. 118/2013*, *O.A. No. 666/2018*, and related suomotu matters.
* **Geographic Coverage:** Punjab, Haryana, Uttar Pradesh, Rajasthan, and NCT of Delhi.
* **Temporal Coverage:** Continuous litigation and compliance reporting from 2014 through 2024, with active hearings, compliance orders, and state status filings in 2025.
* **Spatial Resolution:** District, tehsil, and revenue village level (often down to individual survey/khasra numbers in state enforcement affidavits).
* **Access Method:**
  * NGT Public Judicial Portal: `https://greentribunal.gov.in` (searchable under "Orders/Judgments" and "Case Status").
  * Case files contain State Action Taken Reports submitted by Chief Secretaries, Member Secretaries of PCBs, and DCs.
  * Certified copies of full paper books (including voluminous inspection lists) can be obtained via the NGT Registry or formal RTI applications to MoEFCC / CPCB.
* **Licensing / Restrictions:** Open public judicial records (free to download and cite under Indian judicial public domain rules).
* **Field-Level vs. Aggregated:** Both:
  * *Orders:* Summarize district-level and state-level totals: physical inspections conducted, ground-verified fire incidents, number of challans issued, Environmental Compensation (EC) levied vs. collected (e.g. ₹5,000 for <2 acres; ₹10,000 for 2–5 acres; ₹30,000 for >5 acres), FIRs registered, and "red entries" recorded in land records.
  * *Affidavits & ATR Annexures:* Contain village-level tables listing specific inspection instances, dates, farmer names, khasra numbers, and penalty details.
* **Data Format:** Searchable PDF files.
* **Temporal Precision:** Case-hearing basis (intensive fortnightly to monthly filings during October–December; quarterly during off-season).

---

### 8. SAFAR (System of Air Quality and Weather Forecasting And Research) Crop Burning Data
* **Provider Organization:** Indian Institute of Tropical Meteorology (IITM), Pune (Ministry of Earth Sciences - MoES), in collaboration with India Meteorological Department (IMD).
* **Dataset / Product Name:** SAFAR Stubble Burning Emission & Attribution System / IITM Decision Support System (DSS) for Air Quality Management in Delhi-NCR.
* **Geographic Coverage:** Regional Indo-Gangetic Plains source regions (Punjab, Haryana, Western UP, Eastern Rajasthan) and receptor regions (Delhi and 8 NCR districts).
* **Temporal Coverage:** Active daily throughout October 1 to November 30 every year; operational through 2024 and 2025.
* **Spatial Resolution:** Regional atmospheric chemistry grid at 10 km × 10 km down to 3 km × 3 km over the National Capital Region; driven by satellite active fire points (375 m VIIRS).
* **Access Method:**
  * Official SAFAR portal: `https://safar.tropmet.res.in`.
  * IITM Air Quality Early Warning System (AQEWS) & DSS portal: `https://ews.tropmet.res.in/dss/` and `https://ews.tropmet.res.in/`.
  * Daily public bulletins released during October and November.
  * Gridded NetCDF model output / emissions inventories requestable from Project Director, SAFAR, IITM Pune (`safar@tropmet.res.in`).
* **Licensing / Restrictions:** Open public access for daily web visualizations, bulletins, and press releases; academic research licensing for raw gridded model datasets upon institutional request.
* **Field-Level vs. Aggregated:** Aggregated regional / source-attribution metrics:
  * Daily estimated effective fire count in Punjab/Haryana.
  * Daily stubble burning biomass emissions (PM2.5, BC, OC, CO in Gg/day).
  * Daily percentage contribution of stubble burning to Delhi's PM2.5 (e.g., fluctuating from <2% to >40% depending on wind direction and fire intensity).
* **Data Format:** Web charts, daily PDF bulletins, PNG/JPEG spatial source-attribution maps; underlying modeling data in NetCDF / ASCII formats.
* **Temporal Precision:** Daily daily-average percentages, accompanied by hourly simulated PM2.5 forecasts (3- to 5-day lead times).

---

### 9. Sentinel-2 / Landsat Burned Field Detection Products
* **Provider Organization:** 
  * European Space Agency (ESA) / Copernicus Programme (Sentinel-2A, 2B, and recently launched 2C).
  * USGS / NASA (Landsat 8 and Landsat 9).
  * National Remote Sensing Centre (NRSC / ISRO) – Bhuvan Stubble Burnt Area Assessments.
* **Dataset / Product Name:**
  * NRSC Stubble Burnt Area Mapping (derived via Sentinel-2 MIRBI - Mid-Infrared Burn Index).
  * Harmonized Landsat-Sentinel (HLS) Surface Reflectance (HLSS30 / HLSL30).
  * ESA FireCCI / FireCCISFD (Small Fire Dataset) frameworks and Sentinel-2 Burned Area Index (BAIS2) / differenced Normalized Burn Ratio (dNBR / NBR2) parcel pipelines.
* **Geographic Coverage:** Pan-India / Global coverage (unrestricted coverage of Punjab, Haryana, UP, MP, and Bihar).
* **Temporal Coverage:** Continuous acquisition: Sentinel-2 from 2015 to present (active 2025); Landsat 8 from 2013, Landsat 9 from 2021 to present (active 2025). Revisit capability: 5 days for Sentinel-2 constellation, 8 days for Landsat 8/9 combined.
* **Spatial Resolution:**
  * **Sentinel-2 MSI:** 10 m (B2, B3, B4, B8) and 20 m (B8A, B11, B12 short-wave infrared - SWIR).
  * **Landsat 8/9 OLI:** 30 m multispectral, 15 m panchromatic.
* **Access Method:**
  * Copernicus Data Space Ecosystem: `https://dataspace.copernicus.eu`.
  * Google Earth Engine (GEE): `ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")` and `ee.ImageCollection("NASA/HLS/HLSL30/v002")`.
  * USGS EarthExplorer: `https://earthexplorer.usgs.gov`.
  * ISRO Bhoonidhi Geoportal: `https://bhoonidhi.nrsc.gov.in`.
* **Licensing / Restrictions:** Completely free and open data (CC-BY 4.0 / Copernicus Open Access / USGS Public Domain).
* **Field-Level vs. Aggregated:** **True field-level / parcel-level ground truth.** At 10 m resolution, individual agricultural fields (which in Punjab/Haryana typically average 1 to 5 acres / 4,000–20,000 m²) are resolved into 40 to 200 distinct pixels, allowing exact burn scar boundary delineation, internal unburnt patches, and edge discrimination.
* **Data Format:** Cloud-Optimized GeoTIFF (COG), SAFE containers, NetCDF, GeoJSON / Shapefile vector burn scars.
* **Temporal Precision:** 5-day orbital repeat (or 2–3 days in latitude overlap zones). Note: Does not capture the exact minute of fire ignition, but detects the permanent post-burn scar within days.

---

### 10. Peer-Reviewed India Crop Residue Burning Datasets & Studies
* **Key Published Datasets & Reference Studies:**
  1. **DARBE (District-level Agricultural Residue Burning Emissions in India):** High-resolution multi-pollutant emission inventory based on localized crop-specific biomass factors (indexed in scientific literature, *Atmospheric Environment*).
  2. **Zenodo Open Biomass Burning Collections:**
     * *Agricultural Residue Burning Emissions 2019 v1* (DOI: `10.5281/zenodo.5652524`).
     * *Crop Residue Burning Emission Coefficients Dataset* (Zenodo repository covering crop-to-residue ratios, combustion efficiencies, and emission factors for CO2, CO, PM2.5, NOx).
  3. **PlanetScope & Sentinel-2 Field-Level Benchmark (arXiv: 2209.10148 / Peer-Reviewed):**
     * Title: *"Detecting Crop Burning in India using Satellite Data"*. Combines 3 m daily PlanetScope imagery and 10 m Sentinel-2 imagery with manually verified field polygons in Punjab/Haryana to train Random Forest and U-Net segmentation models (benchmark validation accuracy ~82–88%).
  4. **Liu et al. (Atmospheric Environment: X, 2020):**
     * Title: *"Crop residue burning practices across north India inferred from household survey data: Bridging gaps in satellite observations"*. Provides ground-truth farmer survey data covering burning timing, reasons, and acreage across Punjab, Haryana, and UP.
  5. **Barrett et al. (Nature Communications, 2022):**
     * Title: *"Air quality impacts of crop residue burning in India and mitigation alternatives"*. District-level health and air pollution attribution dataset.
  6. **CEEW (Council on Energy, Environment and Water) Benchmark Datasets:**
     * Studies evaluating discrepancies between satellite active fire counts (MODIS/VIIRS) vs. high-resolution burnt area (Sentinel-2), revealing that afternoon burning avoidance and brief burns lead to active fire count undercounting by up to 2–3× relative to actual burnt field acreage.
  7. **Kaggle CRBIMS Mirror Dataset:**
     * Title: *"Punjab Stubble Burning Crop Fire Data (2022–2024/2025)"*. Curated daily district-wise counts scraped/mirrored from PRSC for machine learning forecasting.
* **Geographic Coverage:** Indo-Gangetic Plains (Punjab, Haryana, Western Uttar Pradesh, Bihar) and Central India (Madhya Pradesh).
* **Temporal Coverage:** Multi-year baseline (2010–2024) with methodologies, spectral threshold scripts, and code repositories fully applicable to 2025.
* **Spatial Resolution:** Field/parcel-level (3 m PlanetScope, 10 m Sentinel-2) to gridded emissions (0.1° × 0.1° and 0.25° × 0.25°).
* **Access Method:** Direct download via DOIs on Zenodo (`zenodo.org`), Figshare (`figshare.com`), Kaggle, GitHub, and journal supplementary data sections.
* **Licensing / Restrictions:** Open Access under Creative Commons licenses (CC-BY 4.0, CC0) or Open Data Commons (ODbL).
* **Field-Level vs. Aggregated:** 
  * Field-level polygons available in satellite benchmark datasets (PlanetScope/Sentinel-2 hand-annotated labels).
  * District-level and gridded tables in emissions datasets.
* **Data Format:** CSV, GeoJSON, Shapefiles, GeoTIFF, Python/Jupyter Notebooks, R scripts.
* **Temporal Precision:** Daily to seasonal composites.

---

## Synthesis: Accessibility & Ground Truth Verification Matrix

| Source / System | Provider | Field-Level vs. Aggregated | 2025 Active? | Primary Data Format | Immediate Accessibility Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. CPCB Monitoring** | CPCB / CAQM | Field (internal) / District (public) | Yes | PDF / Tables | Summary public; field dossiers via RTI / request |
| **2. PRSC CRBIMS** | PRSC Punjab | Event coordinates & District counts | Yes | WebGIS / PDF / CSV | Web dashboard open; raw GIS points requestable/MOU |
| **3. HARSAC AFL** | HARSAC Haryana | Field Khasra (internal) / District (public)| Yes | GIS / PDF / DB | Admin alerts internal; summaries public; research via request |
| **4. IARI Fire Monitoring**| ICAR-IARI | Event point maps & District tables | Yes | PDF bulletins | **Freely downloadable daily** (`iari.res.in`) |
| **5. CREAMS Portal** | IARI-CREAMS | Event points (lat/long) & District tables | Yes | WebGIS / PDF / CSV | **Freely accessible geoportal** (`creams.iari.res.in`) |
| **6. MoAFW Krishi-DSS** | MoAFW / ISRO | Parcel-level (DSS) / District (CRM) | Yes | WebGIS / PDF / Reports| General reports public; Krishi-DSS via dept. login |
| **7. NGT Enforcement** | NGT / State PCBs | Village inspection logs & District totals | Yes | Searchable PDF | **Freely downloadable court orders** (`greentribunal.gov.in`) |
| **8. SAFAR / IITM DSS** | IITM Pune / MoES| Regional source attribution (%) | Yes | Web charts / NetCDF | **Freely accessible daily bulletins/charts**; NetCDF on request |
| **9. Sentinel-2 / Landsat**| ESA / USGS / ISRO | **10 m Parcel-level burn scars** | Yes | GeoTIFF / NetCDF / COG | **100% Free & Open Data** (Copernicus / GEE / EarthExplorer) |
| **10. Peer-Reviewed Datasets**| Various / Zenodo | Field polygons & Gridded emissions | Yes (applicable)| CSV / GeoJSON / TIF | **Directly downloadable via DOIs** (Zenodo, Figshare, GitHub) |

---

## Actionable Recommendations for 2025 Research

1. **For Daily Ground Truth Fire Counts & Locations:**
   * Download the daily **ICAR-IARI CREAMS bulletins** (`creams.iari.res.in`). They represent the official, CAQM-standardized benchmark accepted by the Government of India and the Supreme Court.
   * Intersect with **NASA FIRMS NRT VIIRS 375m** (SNPP and NOAA-20) data for raw timestamped point coordinates across India.
2. **For Field-Level Burn Scar Ground Truth (Delineation & Area):**
   * Do not rely solely on thermal fire counts (which undercount due to farmers shifting burning to late afternoon after the ~14:00 satellite overpasses or cloudy days).
   * Process **Sentinel-2 MSI Level-2A surface reflectance** imagery (10 m / 20 m) on Google Earth Engine. Compute post-harvest burn indices (**MIRBI**, **NBR2**, **BAIS2**, or **dNBR**) over agricultural masks between October 1 and November 30 to extract unambiguous field-level ground truth burn perimeters.
3. **For Official Administrative & Legal Ground Truth (Challans, Inspections, Fines):**
   * Access the **NGT Portal** (`greentribunal.gov.in`) for Case No. OA 21/2014 and OA 666/2018 to obtain state compliance affidavits submitted by Punjab, Haryana, and UP containing exact physical inspection figures, FIR counts, and Environmental Compensation recoveries.