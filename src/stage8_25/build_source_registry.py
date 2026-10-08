"""
Stage 8.25 Source Registry Builder.
Constructs authoritative multi-tier evidence source registry across:
A. Industrial Fires
B. Forest Fires
C. Agricultural Fires
D. Persistent Thermal Sources
E. Industrial Facility Locations
"""

import json
from pathlib import Path

def build_source_registry() -> dict:
    registry = {
        "metadata": {
            "version": "1.0.0",
            "stage": "8.25",
            "date": "2026-10-03",
            "description": "Comprehensive evidence source registry for multi-year industrial thermal-source attribution benchmark.",
            "total_sources": 22
        },
        "sources": [
            # ==========================================
            # Domain A: INDUSTRIAL FIRES
            # ==========================================
            {
                "source_id": "SRC_IND_01",
                "source_name": "SEBI Regulation 30 Material Event Disclosures",
                "organization": "Securities and Exchange Board of India / BSE / NSE",
                "tier": "Tier 1",
                "target_domain": "Industrial Fires",
                "coverage_period": "2015-present",
                "geographic_coverage": "Pan-India (Listed corporate industrial assets)",
                "download_access_method": "Statutory corporate filings portal / Exchange API / Manual dossier download",
                "license_usage_restrictions": "Public statutory disclosure / Open for research and transparency",
                "fields_available": ["company_name", "exchange_symbol", "filing_datetime", "incident_nature", "plant_location", "unit_affected", "operational_impact", "fatalities_injuries"],
                "event_information_available": "Official statutory confirmation of catastrophic plant fires, explosions, operational shutdown dates, exact facility address.",
                "spatial_precision": "Facility level (geocoded address within 100m to 500m precision)",
                "temporal_precision": "Hours to exact day of event announcement",
                "verification_method": "Legal/statutory filing under penalty of perjury; corporate director sign-off."
            },
            {
                "source_id": "SRC_IND_02",
                "source_name": "State Pollution Control Board Incident Inspection Dossiers",
                "organization": "State Pollution Control Boards (GPCB, MPCB, TNPCB, WBPCB, RSPCB)",
                "tier": "Tier 1",
                "target_domain": "Industrial Fires",
                "coverage_period": "2012-present",
                "geographic_coverage": "State-specific industrial estates (Dahej, Dombivli, Ankleshwar, Tarapur, Ranipet, Haldia)",
                "download_access_method": "Statutory environmental notices, closure orders, post-incident show-cause notices",
                "license_usage_restrictions": "Right to Information / Public environmental regulatory orders",
                "fields_available": ["industry_name", "consent_no", "site_address", "accident_date_time", "root_cause", "hazardous_chemicals_involved", "air_water_pollution_impact"],
                "event_information_available": "Official environmental inspection reports detailing chemical fire origin, factory plot number, and fire containment duration.",
                "spatial_precision": "Plot/Plant level (exact industrial estate survey numbers and GPS coords)",
                "temporal_precision": "Hour of occurrence documented by factory inspectors and fire officers",
                "verification_method": "On-site physical inspection by State Pollution Control Board environmental engineers."
            },
            {
                "source_id": "SRC_IND_03",
                "source_name": "National Green Tribunal (NGT) Industrial Accident Proceedings",
                "organization": "National Green Tribunal (Principal Bench, Western Zone, Southern Zone)",
                "tier": "Tier 1",
                "target_domain": "Industrial Fires",
                "coverage_period": "2013-present",
                "geographic_coverage": "Pan-India major industrial chemical/refinery disasters",
                "download_access_method": "NGT judgment and order portal (case law search)",
                "license_usage_restrictions": "Public judicial records",
                "fields_available": ["original_application_no", "unit_name", "date_of_incident", "location_details", "expert_committee_findings", "environmental_compensation"],
                "event_information_available": "Independent court-appointed committee investigations detailing thermal conflagration timelines, facility coordinates, and blast perimeters.",
                "spatial_precision": "Facility perimeter geocoded from technical committee reports (sub-100m)",
                "temporal_precision": "Exact hour and minute of blast/ignition recorded in evidentiary submissions",
                "verification_method": "Judicial decrees and multi-agency expert committee forensic reports (CPCB + NEERI + IITs)."
            },
            {
                "source_id": "SRC_IND_04",
                "source_name": "DGFASLI & State Directorate of Industrial Safety and Health (DISH)",
                "organization": "Ministry of Labour & Employment / State Labour Departments",
                "tier": "Tier 1",
                "target_domain": "Industrial Fires",
                "coverage_period": "2012-present",
                "geographic_coverage": "Pan-India Major Accident Hazard (MAH) registered factories",
                "download_access_method": "Annual factory statistics, enquiry commission gazettes, statutory accident dossiers",
                "license_usage_restrictions": "Government public reports",
                "fields_available": ["factory_registration_no", "industry_sector", "date_of_accident", "fatalities", "equipment_involved", "inspection_findings"],
                "event_information_available": "Statutory reporting under the Factories Act 1948 of major boiler explosions, chemical runaways, and industrial structural fires.",
                "spatial_precision": "Factory site location (PIN code and industrial estate coordinates)",
                "temporal_precision": "Exact date and shift timing of the accident",
                "verification_method": "Statutory inspector of factories audit and formal inquiry."
            },
            {
                "source_id": "SRC_IND_05",
                "source_name": "EM-DAT International Disaster Database (Technological Disasters)",
                "organization": "Centre for Research on the Epidemiology of Disasters (CRED), UCLouvain",
                "tier": "Tier 2",
                "target_domain": "Industrial Fires",
                "coverage_period": "1900-present (Filtered 2012-2026 for India)",
                "geographic_coverage": "Pan-India",
                "download_access_method": "EM-DAT portal query / academic research access",
                "license_usage_restrictions": "Academic research license (non-commercial attribution)",
                "fields_available": ["dis_no", "disaster_sub_type", "event_name", "country", "location", "start_date", "end_date", "total_deaths", "injuries"],
                "event_information_available": "Curated catalog of major industrial explosions and refinery/chemical fires exceeding humanitarian severity thresholds.",
                "spatial_precision": "City/District level with specific facility name",
                "temporal_precision": "Daily start and end dates",
                "verification_method": "Multi-source institutional cross-validation (UN, reinsurance, government reports)."
            },
            {
                "source_id": "SRC_IND_06",
                "source_name": "Corroborated Multi-Source Industrial Incident News Registry",
                "organization": "Curated national news wires (PTI, ANI, The Hindu, Indian Express, Times of India)",
                "tier": "Tier 4",
                "target_domain": "Industrial Fires",
                "coverage_period": "2012-present",
                "geographic_coverage": "Pan-India",
                "download_access_method": "Timestamped news wire archives and verified press releases",
                "license_usage_restrictions": "Public news documentation / Fair use research reference",
                "fields_available": ["headline", "publication_timestamp", "facility_name", "location_named", "fire_department_attendance", "tenders_deployed", "injuries"],
                "event_information_available": "Real-time dispatch records (e.g. '15 fire tenders rushed to MIDC chemical unit') with exact hour of fire outbreak.",
                "spatial_precision": "Industrial area / MIDC / GIDC plot level (geocoded to 500m)",
                "temporal_precision": "Timestamped to within 1-2 hours of ignition",
                "verification_method": "Corroboration required across at least 2 independent news organizations and verification against local fire services."
            },

            # ==========================================
            # Domain B: FOREST FIRES
            # ==========================================
            {
                "source_id": "SRC_FOR_01",
                "source_name": "Forest Survey of India (FSI FAST 3.0 / Van Agni Geo-Portal)",
                "organization": "Forest Survey of India (FSI), MoEFCC",
                "tier": "Tier 1",
                "target_domain": "Forest Fires",
                "coverage_period": "2004-present",
                "geographic_coverage": "Pan-India forest cover and protected area estate",
                "download_access_method": "FSI Van Agni web portal / Forest fire daily bulletins / Large Forest Fire (LFF) alerts",
                "license_usage_restrictions": "Official Government of India portal / Open scientific use",
                "fields_available": ["fire_id", "state", "district", "forest_division", "range", "beat", "latitude", "longitude", "sensor", "datetime", "is_large_forest_fire"],
                "event_information_available": "Official Large Forest Fire (LFF) tracking tracking continuous wildfire clusters burning >3 contiguous satellite passes.",
                "spatial_precision": "Point detections within registered forest beat boundaries (sub-1km)",
                "temporal_precision": "Satellite overpass time and ground field ranger validation timestamp",
                "verification_method": "Statutory forestry personnel ground verification through FAST 3.0 feedback system."
            },
            {
                "source_id": "SRC_FOR_02",
                "source_name": "NASA MODIS Burned Area Product (MCD64A1 Version 6.1)",
                "organization": "NASA Land Processes Distributed Active Archive Center (LP DAAC) / USGS",
                "tier": "Tier 2",
                "target_domain": "Forest Fires",
                "coverage_period": "2000-present",
                "geographic_coverage": "Global (Filtered to India forest biome tiles h24v06, h25v06, h24v07, h25v07)",
                "download_access_method": "NASA Earthdata Search / LP DAAC DAX / Google Earth Engine",
                "license_usage_restrictions": "Open science data policy (NASA EOSDIS)",
                "fields_available": ["burn_date", "burn_date_uncertainty", "qa_score", "first_day", "last_day"],
                "event_information_available": "Standard science-quality 500m gridded daily post-fire burn scar materialization based on multi-temporal surface reflectance changes.",
                "spatial_precision": "500m raster grid cells",
                "temporal_precision": "Day of burn detection (Julian day of year 1-365)",
                "verification_method": "Peer-reviewed algorithm combining active-fire spatial priors with 500m surface reflectance change metrics."
            },
            {
                "source_id": "SRC_FOR_03",
                "source_name": "Global Fire Atlas (GFA) Individual Fire Event & Perimeter Database",
                "organization": "Andela et al. / NASA GSFC / University of East Anglia (Zenodo repository)",
                "tier": "Tier 2",
                "target_domain": "Forest Fires",
                "coverage_period": "2003-present",
                "geographic_coverage": "Global (India national clip)",
                "download_access_method": "Zenodo open dataset repository (DOI: 10.5281/zenodo.17669692)",
                "license_usage_restrictions": "Creative Commons Attribution 4.0 International (CC-BY 4.0)",
                "fields_available": ["fire_id", "ignition_date", "extinction_date", "duration_days", "expansion_km2_day", "fire_line_km", "speed_km_day", "direction", "perimeter_geometry"],
                "event_information_available": "Physically reconstructed continuous wildfire perimeters tracking multi-day ignition, propagation, and extinction.",
                "spatial_precision": "500m vector perimeter boundary polygons",
                "temporal_precision": "Daily boundary progression over multi-day wildfire lifecycles",
                "verification_method": "Spatially continuous connected-component tracking over MCD64A1 daily raster grids."
            },
            {
                "source_id": "SRC_FOR_04",
                "source_name": "State Forest Department Fire Incident Records (Uttarakhand / Himachal / Odisha / MP)",
                "organization": "State Forest Departments (Uttarakhand FFRMS, HP Forest FIRE, Odisha OFMS)",
                "tier": "Tier 1",
                "target_domain": "Forest Fires",
                "coverage_period": "2015-present",
                "geographic_coverage": "State forest divisions and tiger reserves",
                "download_access_method": "State departmental portals, disaster management bulletins, annual administrative reports",
                "license_usage_restrictions": "Official state government documents",
                "fields_available": ["incident_id", "reserve_forest_name", "compartment_no", "fire_type_ground_crown", "start_time", "control_time", "estimated_area_ha"],
                "event_information_available": "Ground-ranger logged wildfire incidents, suppression logs, and burned compartment numbers.",
                "spatial_precision": "Forest beat / compartment polygons (sub-500m)",
                "temporal_precision": "Hours of fire report and suppression completion",
                "verification_method": "Field inspection reports filed by Range Forest Officers (RFOs)."
            },

            # ==========================================
            # Domain C: AGRICULTURAL FIRES
            # ==========================================
            {
                "source_id": "SRC_AGR_01",
                "source_name": "ICAR-IARI CREAMS Crop Residue Burning Monitoring Bulletins",
                "organization": "Consortium for Research on Agroecosystem Monitoring and Modeling from Space, ICAR-IARI, New Delhi",
                "tier": "Tier 2",
                "target_domain": "Agricultural Fires",
                "coverage_period": "2016-present (Intensive Kharif & Rabi seasons)",
                "geographic_coverage": "Northern and Central India (Punjab, Haryana, UP, Rajasthan, MP, Bihar)",
                "download_access_method": "ICAR-IARI daily crop residue monitoring bulletins / Web geo-portal",
                "license_usage_restrictions": "Government agricultural research institute publication / Open research use",
                "fields_available": ["bulletin_no", "monitoring_date", "state", "district", "village_tehsil", "active_events_count", "sensor_used", "cumulative_season_count"],
                "event_information_available": "Official daily scientific monitoring of paddy and wheat stubble burning events verified against agricultural season calendars.",
                "spatial_precision": "District and block-level summaries with geo-referenced point lists",
                "temporal_precision": "Daily tracking with day-of-overpass resolution",
                "verification_method": "IARI satellite remote sensing division verification cross-referenced with field crop calendars."
            },
            {
                "source_id": "SRC_AGR_02",
                "source_name": "Commission for Air Quality Management (CAQM) Stubble Burning Compliance Registry",
                "organization": "CAQM in NCR and Adjoining Areas, Ministry of Environment, Forest and Climate Change",
                "tier": "Tier 1",
                "target_domain": "Agricultural Fires",
                "coverage_period": "2021-present",
                "geographic_coverage": "National Capital Region (NCR), Punjab, Haryana, Rajasthan, Uttar Pradesh",
                "download_access_method": "CAQM daily press bulletins, enforcement directives, Supreme Court compliance submissions",
                "license_usage_restrictions": "Statutory body public disclosures",
                "fields_available": ["report_date", "district", "verified_farm_fires", "environmental_compensation_levied", "red_entry_land_records"],
                "event_information_available": "Official statutory ground-truthed stubble burning citations verified by district flying squads and revenue patwaris.",
                "spatial_precision": "Khasra / Revenue survey number level (sub-500m parcel precision)",
                "temporal_precision": "Daily verification records",
                "verification_method": "Physical site inspection by District Nodal Officers and flying squads."
            },
            {
                "source_id": "SRC_AGR_03",
                "source_name": "Punjab Remote Sensing Centre (PRSC) Crop Residue Burning Verification",
                "organization": "Punjab Remote Sensing Centre (PRSC), Ludhiana / PEDA",
                "tier": "Tier 1",
                "target_domain": "Agricultural Fires",
                "coverage_period": "2016-present",
                "geographic_coverage": "State of Punjab (all agricultural districts)",
                "download_access_method": "PRSC web application / Punjab Stubble Monitoring Dashboard",
                "license_usage_restrictions": "State autonomous organization portal / Research reference",
                "fields_available": ["fire_point_id", "district", "block", "village", "latitude", "longitude", "satellite", "date_time", "field_verification_status"],
                "event_information_available": "State-level remote sensing monitoring linked directly to agricultural field land-record boundaries.",
                "spatial_precision": "Agricultural field parcel (10m to 50m precision)",
                "temporal_precision": "Daily satellite passes (VIIRS NOAA-20 / S-NPP / Aqua)",
                "verification_method": "Ground truthing coordinated with Punjab Department of Agriculture field officers."
            },
            {
                "source_id": "SRC_AGR_04",
                "source_name": "Sentinel-2 MSI Normalized Burn Ratio (Delta-NBR) Agricultural Parcel Scars",
                "organization": "Copernicus Sentinel-2 / ESA / Scientific Remote Sensing Spectral Indexing",
                "tier": "Tier 2",
                "target_domain": "Agricultural Fires",
                "coverage_period": "2015-present",
                "geographic_coverage": "Intensive agricultural basins across India (Indo-Gangetic Plain, Malwa Plateau, Kaveri Delta)",
                "download_access_method": "Copernicus Data Space Ecosystem (CDSE) / S2 L2A BOA Reflectance Bands B08 & B12",
                "license_usage_restrictions": "Open Access under Copernicus Legal Notice",
                "fields_available": ["tile_id", "parcel_centroid_lat", "parcel_centroid_lon", "pre_fire_nbr", "post_fire_nbr", "delta_nbr", "burn_scar_area_ha"],
                "event_information_available": "High-resolution (10m-20m) optical confirmation of fresh post-harvest ash deposit and chlorophyll destruction (Delta-NBR >= 0.10).",
                "spatial_precision": "10m to 20m field-scale resolution",
                "temporal_precision": "5-day Sentinel-2 revisit window",
                "verification_method": "Spectral analysis comparing pre-fire and post-fire SWIR/NIR reflectance ratios."
            },

            # ==========================================
            # Domain D: PERSISTENT THERMAL SOURCES
            # ==========================================
            {
                "source_id": "SRC_PER_01",
                "source_name": "VIIRS Nightfire (VNF) Nighttime Gas Flaring & Thermal Combustion Product",
                "organization": "Earth Observation Group (EOG), Colorado School of Mines / NOAA",
                "tier": "Tier 2",
                "target_domain": "Persistent Thermal Sources",
                "coverage_period": "2012-present",
                "geographic_coverage": "Pan-India offshore and onshore petroleum infrastructure (Mumbai High, Cambay, Assam, Krishna-Godavari)",
                "download_access_method": "EOG VNF Data Portal / Annual global gas flaring shapefiles and CSVs",
                "license_usage_restrictions": "Open scientific research product",
                "fields_available": ["flare_id", "latitude", "longitude", "temperature_k", "source_area_m2", "radiant_heat_mw", "gas_volume_bcm", "detection_frequency"],
                "event_information_available": "Planck curve-fitted persistent sub-pixel combustion detections (1000K-1800K) documenting continuous industrial flare stacks.",
                "spatial_precision": "Sub-pixel centroid (750m VIIRS footprint geocoded within 200m)",
                "temporal_precision": "Nightly overpass observations across multi-year timeline",
                "verification_method": "Bi-spectral infrared Planck temperature retrieval from M10/M12/M13 bands."
            },
            {
                "source_id": "SRC_PER_02",
                "source_name": "World Bank Global Gas Flaring Reduction (GGFR) Global Flaring Tracker",
                "organization": "World Bank Group / NOAA / EOG",
                "tier": "Tier 2",
                "target_domain": "Persistent Thermal Sources",
                "coverage_period": "2012-present",
                "geographic_coverage": "Pan-India oil and gas extraction sites and refineries",
                "download_access_method": "World Bank Open Data / GGFR annual flaring reports and GIS shapefiles",
                "license_usage_restrictions": "Open Data Commons / CC-BY 4.0",
                "fields_available": ["site_id", "country", "latitude", "longitude", "upstream_downstream", "flared_volume_mcm", "flare_count"],
                "event_information_available": "Curated annual inventory of active gas flares across Indian oil refineries and offshore exploration platforms.",
                "spatial_precision": "Facility centroid coordinates (within 300m)",
                "temporal_precision": "Annual aggregation of nightly persistent observations",
                "verification_method": "Cross-calibrated satellite flaring volume estimation vetted by international energy ministries."
            },
            {
                "source_id": "SRC_PER_03",
                "source_name": "Smithsonian Global Volcanism Program (Barren Island Volcanic Registry)",
                "organization": "Smithsonian Institution, National Museum of Natural History / Geological Survey of India (GSI)",
                "tier": "Tier 2",
                "target_domain": "Persistent Thermal Sources",
                "coverage_period": "Historical to present (Active cycles 2012-2026)",
                "geographic_coverage": "Barren Island, Andaman Sea, India (12.278 deg N, 93.858 deg E)",
                "download_access_method": "Smithsonian GVP Volcano Database / Weekly volcanic activity reports",
                "license_usage_restrictions": "Open scientific catalog",
                "fields_available": ["volcano_id", "volcano_name", "subaerial_lat", "subaerial_lon", "summit_elevation_m", "eruption_category", "thermal_anomaly_reports"],
                "event_information_available": "Authoritative geological ground truth for India's sole active volcano; continuous thermal anomaly benchmark.",
                "spatial_precision": "Island summit and caldera coordinates (sub-100m)",
                "temporal_precision": "Continuous geological event records",
                "verification_method": "Geological Survey of India airborne surveys, Indian Coast Guard observations, and MIROVA/MODVOLC."
            },
            {
                "source_id": "SRC_PER_04",
                "source_name": "CMPDI / Coal India Limited Surface Coal Seam Fire Inventories",
                "organization": "Central Mine Planning & Design Institute (CMPDI) / Coal India Limited / CIMFR",
                "tier": "Tier 1",
                "target_domain": "Persistent Thermal Sources",
                "coverage_period": "2012-present",
                "geographic_coverage": "Jharia Coalfield (BCCL), Raniganj (ECL), Singrauli (NCL), Bokaro (CCL)",
                "download_access_method": "Coal fire master plan status reports, Ministry of Coal parliamentary replies, remote sensing thermal maps",
                "license_usage_restrictions": "Government public reports / Parliamentary disclosures",
                "fields_available": ["fire_site_id", "colliery_name", "area_ha", "depth_seam", "surface_temperature_c", "latitude", "longitude", "status_active_dormant"],
                "event_information_available": "Official geological and colliery ground truth for persistent subsurface and opencast burning coal seams.",
                "spatial_precision": "Colliery seam polygon boundaries (within 200m)",
                "temporal_precision": "Multi-decadal persistent thermal emission",
                "verification_method": "Ground thermal infrared thermography and bore-hole temperature logs by CIMFR scientists."
            },
            {
                "source_id": "SRC_PER_05",
                "source_name": "South Asia Brick Kiln High-Resolution Benchmark Dataset",
                "organization": "Stanford University / TERI / International Centre for Integrated Mountain Development (ICIMOD)",
                "tier": "Tier 2",
                "target_domain": "Persistent Thermal Sources",
                "coverage_period": "2015-present",
                "geographic_coverage": "Indo-Gangetic Plain and Central India brick kiln clusters",
                "download_access_method": "Zenodo open geospatial repository / Peer-reviewed study repositories",
                "license_usage_restrictions": "Creative Commons Attribution (CC-BY 4.0)",
                "fields_available": ["kiln_id", "kiln_type_fcbtk_zigzag", "latitude", "longitude", "operational_season_winter_spring", "bounding_box"],
                "event_information_available": "Centroid and bounding polygons of registered and unregistered seasonal Fixed Chimney Bull's Trench Kilns (FCBTKs).",
                "spatial_precision": "Kiln chimney and kiln body exact coordinates (sub-20m precision)",
                "temporal_precision": "Seasonal operational cycles (October through June)",
                "verification_method": "Deep learning object detection on sub-meter DigitalGlobe/Google imagery with visual human expert audit."
            },
            {
                "source_id": "SRC_PER_06",
                "source_name": "Central Electricity Authority (CEA) Thermal Power Station Registry",
                "organization": "Central Electricity Authority, Ministry of Power, Government of India",
                "tier": "Tier 1",
                "target_domain": "Persistent Thermal Sources",
                "coverage_period": "2010-present",
                "geographic_coverage": "Pan-India coal, lignite, and gas thermal power utilities",
                "download_access_method": "CEA Monthly Generation Reports / National Power Portal (NPP)",
                "license_usage_restrictions": "Government open data",
                "fields_available": ["station_id", "station_name", "sector_state_central_private", "installed_capacity_mw", "fuel_type", "latitude", "longitude", "plf_percentage"],
                "event_information_available": "Complete coordinates and operational load of major thermal power boilers, cooling systems, and chimney complexes.",
                "spatial_precision": "Power station boundary and boiler house coordinates (sub-200m)",
                "temporal_precision": "Daily and monthly generation tracking",
                "verification_method": "Statutory operational generation telemetry reported to national load dispatch centres."
            },

            # ==========================================
            # Domain E: INDUSTRIAL FACILITY LOCATIONS
            # ==========================================
            {
                "source_id": "SRC_FAC_01",
                "source_name": "Global Energy Monitor (GEM) Global Asset Trackers",
                "organization": "Global Energy Monitor (GEM)",
                "tier": "Tier 2",
                "target_domain": "Industrial Facility Locations",
                "coverage_period": "2018-present (Updated quarterly)",
                "geographic_coverage": "Pan-India industrial infrastructure (Steel plants, Oil/Gas pipelines, Petrochemicals, Coal plants)",
                "download_access_method": "Global Energy Monitor open download portal",
                "license_usage_restrictions": "Creative Commons Attribution 4.0 International (CC-BY 4.0)",
                "fields_available": ["gem_id", "facility_name", "subsector", "status_operating_announced_retired", "capacity", "latitude", "longitude", "owner", "parent_company"],
                "event_information_available": "Verified global coordinates, industrial sub-sectors, operational statuses, and facility ownership.",
                "spatial_precision": "Facility centroid coordinates verified via satellite imagery (sub-100m)",
                "temporal_precision": "Quarterly operational status auditing",
                "verification_method": "Rigorous investigative research citing permits, company filings, and satellite imagery cross-checks."
            },
            {
                "source_id": "SRC_FAC_02",
                "source_name": "OpenStreetMap (OSM) India Industrial Landuse & Manufacturing Infrastructure",
                "organization": "OpenStreetMap Contributors / Geofabrik India Extracts",
                "tier": "Tier 3",
                "target_domain": "Industrial Facility Locations",
                "coverage_period": "2008-present",
                "geographic_coverage": "Pan-India",
                "download_access_method": "Geofabrik download server / Overpass API queries (`landuse=industrial`, `industrial=*`)",
                "license_usage_restrictions": "Open Database License (ODbL) 1.0",
                "fields_available": ["osm_id", "name", "landuse", "industrial", "operator", "geometry"],
                "event_information_available": "Vector polygons and point geometries covering manufacturing parks, chemical estates, industrial godowns, and refineries.",
                "spatial_precision": "Meter-scale vector polygons",
                "temporal_precision": "Continuously updated crowdsourced and surveyed edits",
                "verification_method": "Community consensus, local mapping surveys, and high-resolution aerial tracing."
            }
        ]
    }
    return registry

def main():
    out_dir = Path("data/reference/ds08/manifests/stage8_25")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "source_registry.json"
    data = build_source_registry()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[SUCCESS] Wrote source registry with {len(data['sources'])} sources to {out_path}")

if __name__ == "__main__":
    main()
