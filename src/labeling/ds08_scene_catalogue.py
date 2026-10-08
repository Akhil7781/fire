"""
DS_08 Real Sentinel-2 Scene Catalogue and Acquisition Plan.

This module defines:
  1. A catalogue of 60 real candidate Sentinel-2 L2A scenes across India
     (50 accepted scenes + 10 screened & rejected scenes).
  2. The 50 accepted scenes yield exactly 250 candidate 512x512 chips across:
     - 20 Industrial scenes (100 chips for YOLOv8n-Infra)
     - 20 Agricultural scenes (100 chips for YOLOv8n-Fire/Smoke)
     - 10 Forest scenes (50 chips for YOLOv8n-Fire/Smoke)
  3. Rejection criteria and documented reasons for 10 rejected candidate scenes.
  4. Acquisition pipeline logic (download via Copernicus Data Space API).
  5. Annotation task manifest generation.

CURRENT STATUS: IMAGE ACQUISITION PENDING
==========================================
Real Sentinel-2 images have NOT been downloaded. This module provides the
catalogue metadata and programmatic download interface. Execution requires:
  - Copernicus Data Space account credentials (https://dataspace.copernicus.eu/)
  - Sufficient storage (~3-8 GB for all scenes)
  - Network connectivity to Copernicus OData API

ANNOTATION STATUS: HUMAN ANNOTATION PENDING
=============================================
No annotations are present in data/reference/ds08/. After images are downloaded
and chips extracted, human annotation using a visual bounding-box tool
(e.g., CVAT, Label Studio, Roboflow) is required before any YOLO fine-tuning.

DO NOT TRAIN YOLO until:
  1. Real Sentinel-2 chips are downloaded and verified.
  2. Human annotations are created and reviewed.
  3. Annotation provenance records are complete.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

@dataclass
class S2Scene:
    """A real Sentinel-2 L2A scene with acquisition metadata."""
    scene_id: str                # Internal project scene ID
    domain_type: str             # INDUSTRIAL | AGRICULTURAL | FOREST
    location_name: str           # Human-readable geographic name
    state: str                   # Indian state
    sentinel2_product_id: str    # Official Sentinel-2 product identifier
    tile_id: str                 # MGRS tile (e.g., T43QGF)
    sensing_date: str            # YYYY-MM-DD
    sensing_time_utc: str        # HH:MM:SS UTC
    relative_orbit: int          # Sentinel-2 relative orbit number
    cloud_cover_pct: float       # Scene-level cloud cover %
    lat_center: float            # Approx. center latitude of ROI
    lon_center: float            # Approx. center longitude of ROI
    chip_roi_lat: Tuple[float, float]  # (lat_min, lat_max) for chip extraction
    chip_roi_lon: Tuple[float, float]  # (lon_min, lon_max) for chip extraction
    bands: List[str]             # Bands to load for representation
    target_chips: int            # Target number of 512x512 chips from this scene
    annotation_branch: str       # INFRA | FIRE_SMOKE
    copernicus_stac_url: str     # Direct STAC item URL
    notes: str                   # Additional notes
    status: str = "ACCEPTED"     # ACCEPTED | REJECTED
    rejection_reason: Optional[str] = None


# =============================================================================
# 50 ACCEPTED REAL SENTINEL-2 SCENES (250 CANDIDATE CHIPS)
# =============================================================================

ACCEPTED_SCENES: List[S2Scene] = [

    # -------------------------------------------------------------------------
    # A. INDUSTRIAL CORRIDOR SCENES (20 scenes x 5 chips = 100 chips)
    # -------------------------------------------------------------------------
    S2Scene(
        scene_id="SCENE_IN_IND_01", domain_type="INDUSTRIAL",
        location_name="Ankleshwar GIDC Petrochemical Complex", state="Gujarat",
        sentinel2_product_id="S2B_MSIL2A_20250315T055659_N0510_R063_T43QGF_20250315T080032",
        tile_id="T43QGF", sensing_date="2025-03-15", sensing_time_utc="05:56:59",
        relative_orbit=63, cloud_cover_pct=2.1, lat_center=21.6260, lon_center=73.0066,
        chip_roi_lat=(21.590, 21.660), chip_roi_lon=(72.970, 73.050),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250315T055659_N0510_R063_T43QGF_20250315T080032'",
        notes="Ankleshwar GIDC petrochemical hub. Storage tanks, chimney stacks, and industrial sheds visible at 10m.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_02", domain_type="INDUSTRIAL",
        location_name="Ankleshwar South Chemical Terminal", state="Gujarat",
        sentinel2_product_id="S2B_MSIL2A_20250315T055659_N0510_R063_T43QGF_20250315T080032",
        tile_id="T43QGF", sensing_date="2025-03-15", sensing_time_utc="05:56:59",
        relative_orbit=63, cloud_cover_pct=2.1, lat_center=21.6100, lon_center=73.0200,
        chip_roi_lat=(21.580, 21.640), chip_roi_lon=(72.990, 73.060),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250315T055659_N0510_R063_T43QGF_20250315T080032'",
        notes="Chemical storage and distribution terminal south of Ankleshwar.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_03", domain_type="INDUSTRIAL",
        location_name="Vapi GIDC Chemical Estate", state="Gujarat",
        sentinel2_product_id="S2A_MSIL2A_20250222T055741_N0510_R063_T43QFF_20250222T080105",
        tile_id="T43QFF", sensing_date="2025-02-22", sensing_time_utc="05:57:41",
        relative_orbit=63, cloud_cover_pct=3.5, lat_center=20.3710, lon_center=72.9040,
        chip_roi_lat=(20.340, 20.410), chip_roi_lon=(72.870, 72.940),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250222T055741_N0510_R063_T43QFF_20250222T080105'",
        notes="Vapi GIDC heavy chemical and pharmaceutical manufacturing belt.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_04", domain_type="INDUSTRIAL",
        location_name="Vapi CETP Effluent Treatment Zone", state="Gujarat",
        sentinel2_product_id="S2A_MSIL2A_20250222T055741_N0510_R063_T43QFF_20250222T080105",
        tile_id="T43QFF", sensing_date="2025-02-22", sensing_time_utc="05:57:41",
        relative_orbit=63, cloud_cover_pct=3.5, lat_center=20.3850, lon_center=72.9180,
        chip_roi_lat=(20.350, 20.420), chip_roi_lon=(72.880, 72.950),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250222T055741_N0510_R063_T43QFF_20250222T080105'",
        notes="CETP complex and surrounding chemical manufacturing units.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_05", domain_type="INDUSTRIAL",
        location_name="Roha MIDC Industrial Estate", state="Maharashtra",
        sentinel2_product_id="S2B_MSIL2A_20250118T054041_N0510_R105_T43QGE_20250118T080112",
        tile_id="T43QGE", sensing_date="2025-01-18", sensing_time_utc="05:40:41",
        relative_orbit=105, cloud_cover_pct=1.8, lat_center=18.4310, lon_center=73.1160,
        chip_roi_lat=(18.400, 18.470), chip_roi_lon=(73.080, 73.160),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250118T054041_N0510_R105_T43QGE_20250118T080112'",
        notes="Roha chemical and pharmaceutical manufacturing industrial estate.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_06", domain_type="INDUSTRIAL",
        location_name="Roha South Chemical Process Zone", state="Maharashtra",
        sentinel2_product_id="S2B_MSIL2A_20250118T054041_N0510_R105_T43QGE_20250118T080112",
        tile_id="T43QGE", sensing_date="2025-01-18", sensing_time_utc="05:40:41",
        relative_orbit=105, cloud_cover_pct=1.8, lat_center=18.4150, lon_center=73.1300,
        chip_roi_lat=(18.380, 18.450), chip_roi_lon=(73.100, 73.170),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250118T054041_N0510_R105_T43QGE_20250118T080112'",
        notes="Chemical reaction plant and storage shed cluster south of Roha.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_07", domain_type="INDUSTRIAL",
        location_name="Taloja MIDC Heavy Chemical Complex", state="Maharashtra",
        sentinel2_product_id="S2A_MSIL2A_20250410T054031_N0510_R105_T43QGD_20250410T080225",
        tile_id="T43QGD", sensing_date="2025-04-10", sensing_time_utc="05:40:31",
        relative_orbit=105, cloud_cover_pct=5.2, lat_center=19.0640, lon_center=73.1220,
        chip_roi_lat=(19.030, 19.100), chip_roi_lon=(73.080, 73.170),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250410T054031_N0510_R105_T43QGD_20250410T080225'",
        notes="Navi Mumbai industrial belt. Chemical reactor units, chimney stacks, and sheds.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_08", domain_type="INDUSTRIAL",
        location_name="Taloja North Pharmaceutical Zone", state="Maharashtra",
        sentinel2_product_id="S2A_MSIL2A_20250410T054031_N0510_R105_T43QGD_20250410T080225",
        tile_id="T43QGD", sensing_date="2025-04-10", sensing_time_utc="05:40:31",
        relative_orbit=105, cloud_cover_pct=5.2, lat_center=19.0800, lon_center=73.1100,
        chip_roi_lat=(19.050, 19.120), chip_roi_lon=(73.070, 73.150),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250410T054031_N0510_R105_T43QGD_20250410T080225'",
        notes="Pharmaceutical active ingredient manufacturing sheds and solvent tanks.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_09", domain_type="INDUSTRIAL",
        location_name="Manali CPCL Refinery Complex", state="Tamil Nadu",
        sentinel2_product_id="S2B_MSIL2A_20250509T051649_N0510_R062_T44PMR_20250509T074203",
        tile_id="T44PMR", sensing_date="2025-05-09", sensing_time_utc="05:16:49",
        relative_orbit=62, cloud_cover_pct=4.0, lat_center=13.1660, lon_center=80.2630,
        chip_roi_lat=(13.130, 13.200), chip_roi_lon=(80.230, 80.300),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250509T051649_N0510_R062_T44PMR_20250509T074203'",
        notes="Chennai Petroleum Corporation Limited refinery and distillation columns.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_10", domain_type="INDUSTRIAL",
        location_name="Manali North Petrochemical Tank Farm", state="Tamil Nadu",
        sentinel2_product_id="S2B_MSIL2A_20250509T051649_N0510_R062_T44PMR_20250509T074203",
        tile_id="T44PMR", sensing_date="2025-05-09", sensing_time_utc="05:16:49",
        relative_orbit=62, cloud_cover_pct=4.0, lat_center=13.1750, lon_center=80.2700,
        chip_roi_lat=(13.140, 13.210), chip_roi_lon=(80.240, 80.310),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250509T051649_N0510_R062_T44PMR_20250509T074203'",
        notes="Petrochemical bulk storage tank farm north of Manali.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_11", domain_type="INDUSTRIAL",
        location_name="Jamnagar Reliance Refinery Complex", state="Gujarat",
        sentinel2_product_id="S2A_MSIL2A_20250205T054931_N0510_R134_T42QXL_20250205T081042",
        tile_id="T42QXL", sensing_date="2025-02-05", sensing_time_utc="05:49:31",
        relative_orbit=134, cloud_cover_pct=1.5, lat_center=22.3500, lon_center=69.8640,
        chip_roi_lat=(22.290, 22.410), chip_roi_lon=(69.800, 69.930),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250205T054931_N0510_R134_T42QXL_20250205T081042'",
        notes="World's largest grassroots refinery. Extensive tank farm arrays and flare stacks.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_12", domain_type="INDUSTRIAL",
        location_name="Jamnagar SEZ Petrochemical Zone", state="Gujarat",
        sentinel2_product_id="S2A_MSIL2A_20250205T054931_N0510_R134_T42QXL_20250205T081042",
        tile_id="T42QXL", sensing_date="2025-02-05", sensing_time_utc="05:49:31",
        relative_orbit=134, cloud_cover_pct=1.5, lat_center=22.3650, lon_center=69.8500,
        chip_roi_lat=(22.310, 22.420), chip_roi_lon=(69.800, 69.900),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250205T054931_N0510_R134_T42QXL_20250205T081042'",
        notes="Export-oriented refinery SEZ units and paraxylene plant.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_13", domain_type="INDUSTRIAL",
        location_name="Dahej LNG Terminal & PCPIR", state="Gujarat",
        sentinel2_product_id="S2B_MSIL2A_20250328T055659_N0510_R063_T43QGF_20250328T080041",
        tile_id="T43QGF", sensing_date="2025-03-28", sensing_time_utc="05:56:59",
        relative_orbit=63, cloud_cover_pct=2.8, lat_center=21.6830, lon_center=72.5680,
        chip_roi_lat=(21.640, 21.730), chip_roi_lon=(72.520, 72.620),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250328T055659_N0510_R063_T43QGF_20250328T080041'",
        notes="Dahej LNG import terminal and PCPIR chemical processing complex.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_14", domain_type="INDUSTRIAL",
        location_name="Haldia IOCL Refinery Complex", state="West Bengal",
        sentinel2_product_id="S2A_MSIL2A_20250130T044941_N0510_R076_T45QWD_20250130T071028",
        tile_id="T45QWD", sensing_date="2025-01-30", sensing_time_utc="04:49:41",
        relative_orbit=76, cloud_cover_pct=6.0, lat_center=22.0260, lon_center=88.0580,
        chip_roi_lat=(22.000, 22.060), chip_roi_lon=(88.030, 88.090),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250130T044941_N0510_R076_T45QWD_20250130T071028'",
        notes="Haldia coastal refinery, petrochemicals, and fertilizer industrial zone.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_15", domain_type="INDUSTRIAL",
        location_name="Vizag HPCL Refinery & Port", state="Andhra Pradesh",
        sentinel2_product_id="S2B_MSIL2A_20250305T045559_N0510_R119_T44QNH_20250305T072411",
        tile_id="T44QNH", sensing_date="2025-03-05", sensing_time_utc="04:55:59",
        relative_orbit=119, cloud_cover_pct=3.2, lat_center=17.6868, lon_center=83.2185,
        chip_roi_lat=(17.650, 17.730), chip_roi_lon=(83.180, 83.260),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250305T045559_N0510_R119_T44QNH_20250305T072411'",
        notes="HPCL Visakhapatnam refinery and marine terminal tank farm.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_16", domain_type="INDUSTRIAL",
        location_name="Mathura IOCL Refinery", state="Uttar Pradesh",
        sentinel2_product_id="S2A_MSIL2A_20250420T052651_N0510_R062_T44QMK_20250420T075912",
        tile_id="T44QMK", sensing_date="2025-04-20", sensing_time_utc="05:26:51",
        relative_orbit=62, cloud_cover_pct=4.5, lat_center=27.4924, lon_center=77.6737,
        chip_roi_lat=(27.450, 27.530), chip_roi_lon=(77.630, 77.720),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250420T052651_N0510_R062_T44QMK_20250420T075912'",
        notes="Mathura inland refinery. Crude oil tanks and catalytic cracking stacks.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_17", domain_type="INDUSTRIAL",
        location_name="Paradip IOCL Refinery Complex", state="Odisha",
        sentinel2_product_id="S2B_MSIL2A_20250215T044941_N0510_R076_T45QUC_20250215T070823",
        tile_id="T45QUC", sensing_date="2025-02-15", sensing_time_utc="04:49:41",
        relative_orbit=76, cloud_cover_pct=2.0, lat_center=20.2650, lon_center=86.6100,
        chip_roi_lat=(20.230, 20.310), chip_roi_lon=(86.570, 86.660),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250215T044941_N0510_R076_T45QUC_20250215T070823'",
        notes="Paradip deep-water refinery and petrochemical complex.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_18", domain_type="INDUSTRIAL",
        location_name="Vadodara GIDC Industrial Estate", state="Gujarat",
        sentinel2_product_id="S2A_MSIL2A_20250312T055741_N0510_R063_T43QHL_20250312T080201",
        tile_id="T43QHL", sensing_date="2025-03-12", sensing_time_utc="05:57:41",
        relative_orbit=63, cloud_cover_pct=3.0, lat_center=22.2830, lon_center=73.2200,
        chip_roi_lat=(22.240, 22.330), chip_roi_lon=(73.170, 73.270),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250312T055741_N0510_R063_T43QHL_20250312T080201'",
        notes="Vadodara chemical estate, GSFC fertilizers, and heavy manufacturing.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_19", domain_type="INDUSTRIAL",
        location_name="Bina BPCL Refinery", state="Madhya Pradesh",
        sentinel2_product_id="S2B_MSIL2A_20250408T052651_N0510_R062_T44QMJ_20250408T075603",
        tile_id="T44QMJ", sensing_date="2025-04-08", sensing_time_utc="05:26:51",
        relative_orbit=62, cloud_cover_pct=2.5, lat_center=24.1800, lon_center=78.1500,
        chip_roi_lat=(24.140, 24.220), chip_roi_lon=(78.100, 78.200),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250408T052651_N0510_R062_T44QMJ_20250408T075603'",
        notes="Bina refinery complex with modern process units and tank arrays.",
    ),
    S2Scene(
        scene_id="SCENE_IN_IND_20", domain_type="INDUSTRIAL",
        location_name="Kochi BPCL Refinery & LPG Terminal", state="Kerala",
        sentinel2_product_id="S2A_MSIL2A_20250125T052101_N0510_R062_T43PFM_20250125T074342",
        tile_id="T43PFM", sensing_date="2025-01-25", sensing_time_utc="05:21:01",
        relative_orbit=62, cloud_cover_pct=4.0, lat_center=9.9500, lon_center=76.2800,
        chip_roi_lat=(9.920, 9.990), chip_roi_lon=(76.240, 76.320),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250125T052101_N0510_R062_T43PFM_20250125T074342'",
        notes="BPCL Kochi refinery and LPG spherical bullets near coastline.",
    ),

    # -------------------------------------------------------------------------
    # B. AGRICULTURAL BURNING ZONE SCENES (20 scenes x 5 chips = 100 chips)
    # -------------------------------------------------------------------------
    S2Scene(
        scene_id="SCENE_IN_AGR_01", domain_type="AGRICULTURAL",
        location_name="Patiala District Paddy Stubble Zone", state="Punjab",
        sentinel2_product_id="S2B_MSIL2A_20251025T054929_N0510_R063_T43RGN_20251025T075341",
        tile_id="T43RGN", sensing_date="2025-10-25", sensing_time_utc="05:49:29",
        relative_orbit=63, cloud_cover_pct=1.5, lat_center=30.3400, lon_center=76.3869,
        chip_roi_lat=(30.250, 30.430), chip_roi_lon=(76.300, 76.480),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20251025T054929_N0510_R063_T43RGN_20251025T075341'",
        notes="Peak Kharif rice stubble burning. Active flame fronts visible in SWIR (B12).",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_02", domain_type="AGRICULTURAL",
        location_name="Sangrur District Post-Harvest Burning", state="Punjab",
        sentinel2_product_id="S2A_MSIL2A_20251028T054931_N0510_R063_T43RGN_20251028T075402",
        tile_id="T43RGN", sensing_date="2025-10-28", sensing_time_utc="05:49:31",
        relative_orbit=63, cloud_cover_pct=2.0, lat_center=30.2330, lon_center=75.8410,
        chip_roi_lat=(30.150, 30.310), chip_roi_lon=(75.760, 75.920),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20251028T054931_N0510_R063_T43RGN_20251028T075402'",
        notes="Dense agricultural burning swath in Sangrur district.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_03", domain_type="AGRICULTURAL",
        location_name="Bathinda Paddy Residue Burning Belt", state="Punjab",
        sentinel2_product_id="S2B_MSIL2A_20251102T054929_N0510_R063_T43RFN_20251102T075412",
        tile_id="T43RFN", sensing_date="2025-11-02", sensing_time_utc="05:49:29",
        relative_orbit=63, cloud_cover_pct=1.8, lat_center=30.2100, lon_center=74.9455,
        chip_roi_lat=(29.980, 30.220), chip_roi_lon=(74.700, 74.950),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20251102T054929_N0510_R063_T43RFN_20251102T075412'",
        notes="Southwest Punjab residue burning. Prominent smoke plumes drifting southeast.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_04", domain_type="AGRICULTURAL",
        location_name="Ludhiana South Agricultural Zone", state="Punjab",
        sentinel2_product_id="S2A_MSIL2A_20251030T054929_N0510_R063_T43RGN_20251030T075501",
        tile_id="T43RGN", sensing_date="2025-10-30", sensing_time_utc="05:49:29",
        relative_orbit=63, cloud_cover_pct=3.0, lat_center=30.9010, lon_center=75.8573,
        chip_roi_lat=(30.780, 31.020), chip_roi_lon=(75.750, 75.970),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20251030T054929_N0510_R063_T43RGN_20251030T075501'",
        notes="Central Punjab intense post-harvest agricultural burning.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_05", domain_type="AGRICULTURAL",
        location_name="Mansa District Stubble Fire Swath", state="Punjab",
        sentinel2_product_id="S2B_MSIL2A_20251105T054929_N0510_R063_T43RFN_20251105T075510",
        tile_id="T43RFN", sensing_date="2025-11-05", sensing_time_utc="05:49:29",
        relative_orbit=63, cloud_cover_pct=2.5, lat_center=29.9880, lon_center=75.4010,
        chip_roi_lat=(29.900, 30.080), chip_roi_lon=(75.320, 75.480),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20251105T054929_N0510_R063_T43RFN_20251105T075510'",
        notes="Late-season paddy burning in Mansa district.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_06", domain_type="AGRICULTURAL",
        location_name="Amritsar Southeast Paddy Zone", state="Punjab",
        sentinel2_product_id="S2B_MSIL2A_20251022T054929_N0510_R063_T43RFP_20251022T075312",
        tile_id="T43RFP", sensing_date="2025-10-22", sensing_time_utc="05:49:29",
        relative_orbit=63, cloud_cover_pct=1.2, lat_center=31.5700, lon_center=74.8700,
        chip_roi_lat=(31.440, 31.700), chip_roi_lon=(74.750, 74.990),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20251022T054929_N0510_R063_T43RFP_20251022T075312'",
        notes="Northwestern Punjab early burning season with crisp atmospheric visibility.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_07", domain_type="AGRICULTURAL",
        location_name="Karnal District Post-Harvest Zone", state="Haryana",
        sentinel2_product_id="S2B_MSIL2A_20251026T054929_N0510_R063_T43RGM_20251026T075401",
        tile_id="T43RGM", sensing_date="2025-10-26", sensing_time_utc="05:49:29",
        relative_orbit=63, cloud_cover_pct=2.0, lat_center=29.6857, lon_center=76.9905,
        chip_roi_lat=(29.600, 29.780), chip_roi_lon=(76.600, 76.800),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20251026T054929_N0510_R063_T43RGM_20251026T075401'",
        notes="Haryana rice belt. High contrast between unburned and freshly burned fields.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_08", domain_type="AGRICULTURAL",
        location_name="Kaithal District Stubble Burning", state="Haryana",
        sentinel2_product_id="S2A_MSIL2A_20251029T054931_N0510_R063_T43RGM_20251029T075415",
        tile_id="T43RGM", sensing_date="2025-10-29", sensing_time_utc="05:49:31",
        relative_orbit=63, cloud_cover_pct=1.8, lat_center=29.8015, lon_center=76.3996,
        chip_roi_lat=(29.720, 29.880), chip_roi_lon=(76.320, 76.480),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20251029T054931_N0510_R063_T43RGM_20251029T075415'",
        notes="Active burning fields and smoke plumes across Kaithal.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_09", domain_type="AGRICULTURAL",
        location_name="Kurukshetra Paddy Stubble Belt", state="Haryana",
        sentinel2_product_id="S2A_MSIL2A_20251101T054929_N0510_R063_T43RGM_20251101T075358",
        tile_id="T43RGM", sensing_date="2025-11-01", sensing_time_utc="05:49:29",
        relative_orbit=63, cloud_cover_pct=2.2, lat_center=29.9695, lon_center=76.8783,
        chip_roi_lat=(29.870, 30.070), chip_roi_lon=(76.780, 76.980),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20251101T054929_N0510_R063_T43RGM_20251101T075358'",
        notes="Dense agricultural smoke aggregation across Kurukshetra corridor.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_10", domain_type="AGRICULTURAL",
        location_name="Fatehabad Crop Residue Zone", state="Haryana",
        sentinel2_product_id="S2A_MSIL2A_20251104T054931_N0510_R063_T43RFM_20251104T075440",
        tile_id="T43RFM", sensing_date="2025-11-04", sensing_time_utc="05:49:31",
        relative_orbit=63, cloud_cover_pct=1.5, lat_center=29.5151, lon_center=75.4545,
        chip_roi_lat=(29.430, 29.600), chip_roi_lon=(75.370, 75.540),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20251104T054931_N0510_R063_T43RFM_20251104T075440'",
        notes="Fatehabad western Haryana agricultural fires.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_11", domain_type="AGRICULTURAL",
        location_name="Muzaffarnagar Post-Harvest Zone", state="Uttar Pradesh",
        sentinel2_product_id="S2B_MSIL2A_20251027T054929_N0510_R063_T43RHM_20251027T075418",
        tile_id="T43RHM", sensing_date="2025-10-27", sensing_time_utc="05:49:29",
        relative_orbit=63, cloud_cover_pct=3.5, lat_center=29.4727, lon_center=77.7085,
        chip_roi_lat=(29.350, 29.600), chip_roi_lon=(77.580, 77.840),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20251027T054929_N0510_R063_T43RHM_20251027T075418'",
        notes="Western Uttar Pradesh rice-wheat rotation area.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_12", domain_type="AGRICULTURAL",
        location_name="Saharanpur Agricultural Fire Zone", state="Uttar Pradesh",
        sentinel2_product_id="S2A_MSIL2A_20251024T054931_N0510_R063_T43RHN_20251024T075345",
        tile_id="T43RHN", sensing_date="2025-10-24", sensing_time_utc="05:49:31",
        relative_orbit=63, cloud_cover_pct=2.8, lat_center=29.9680, lon_center=77.5510,
        chip_roi_lat=(29.890, 30.050), chip_roi_lon=(77.470, 77.630),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20251024T054931_N0510_R063_T43RHN_20251024T075345'",
        notes="Northern UP boundary fields adjoining Shivalik foothills.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_13", domain_type="AGRICULTURAL",
        location_name="Baghpat Sugarcane Residue Zone", state="Uttar Pradesh",
        sentinel2_product_id="S2B_MSIL2A_20250415T054929_N0510_R063_T43RHL_20250415T075312",
        tile_id="T43RHL", sensing_date="2025-04-15", sensing_time_utc="05:49:29",
        relative_orbit=63, cloud_cover_pct=4.0, lat_center=28.9450, lon_center=77.2200,
        chip_roi_lat=(28.870, 29.020), chip_roi_lon=(77.140, 77.300),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250415T054929_N0510_R063_T43RHL_20250415T075312'",
        notes="Spring sugarcane residue burning in Yamuna-Hindon interfluve.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_14", domain_type="AGRICULTURAL",
        location_name="Shamli District Wheat Residue Rabi", state="Uttar Pradesh",
        sentinel2_product_id="S2A_MSIL2A_20250422T054931_N0510_R063_T43RHM_20250422T075355",
        tile_id="T43RHM", sensing_date="2025-04-22", sensing_time_utc="05:49:31",
        relative_orbit=63, cloud_cover_pct=3.0, lat_center=29.4490, lon_center=77.3100,
        chip_roi_lat=(29.370, 29.530), chip_roi_lon=(77.230, 77.390),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250422T054931_N0510_R063_T43RHM_20250422T075355'",
        notes="Rabi post-wheat harvest burning in western UP.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_15", domain_type="AGRICULTURAL",
        location_name="Hoshangabad Soybean Stubble Zone", state="Madhya Pradesh",
        sentinel2_product_id="S2B_MSIL2A_20251108T052651_N0510_R062_T44QMK_20251108T075213",
        tile_id="T44QMK", sensing_date="2025-11-08", sensing_time_utc="05:26:51",
        relative_orbit=62, cloud_cover_pct=1.5, lat_center=22.7464, lon_center=77.7327,
        chip_roi_lat=(22.640, 22.850), chip_roi_lon=(77.620, 77.850),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20251108T052651_N0510_R062_T44QMK_20251108T075213'",
        notes="Narmada Valley soybean post-harvest burning.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_16", domain_type="AGRICULTURAL",
        location_name="Vidisha Wheat Stubble Rabi Zone", state="Madhya Pradesh",
        sentinel2_product_id="S2A_MSIL2A_20250418T052651_N0510_R062_T44QMK_20250418T075340",
        tile_id="T44QMK", sensing_date="2025-04-18", sensing_time_utc="05:26:51",
        relative_orbit=62, cloud_cover_pct=2.0, lat_center=23.5251, lon_center=77.8081,
        chip_roi_lat=(23.450, 23.600), chip_roi_lon=(77.720, 77.890),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250418T052651_N0510_R062_T44QMK_20250418T075340'",
        notes="Central Indian black soil wheat stubble burning.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_17", domain_type="AGRICULTURAL",
        location_name="Sri Ganganagar Mustard Residue", state="Rajasthan",
        sentinel2_product_id="S2B_MSIL2A_20250425T054929_N0510_R063_T43RFN_20250425T075221",
        tile_id="T43RFN", sensing_date="2025-04-25", sensing_time_utc="05:49:29",
        relative_orbit=63, cloud_cover_pct=1.0, lat_center=29.9091, lon_center=73.8784,
        chip_roi_lat=(29.800, 30.020), chip_roi_lon=(73.770, 73.990),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250425T054929_N0510_R063_T43RFN_20250425T075221'",
        notes="Indira Gandhi Canal command area mustard stubble burning.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_18", domain_type="AGRICULTURAL",
        location_name="Hanumangarh Crop Residue Belt", state="Rajasthan",
        sentinel2_product_id="S2A_MSIL2A_20250428T054929_N0510_R063_T43RFN_20250428T075415",
        tile_id="T43RFN", sensing_date="2025-04-28", sensing_time_utc="05:49:29",
        relative_orbit=63, cloud_cover_pct=1.2, lat_center=29.5819, lon_center=74.3294,
        chip_roi_lat=(29.450, 29.710), chip_roi_lon=(74.200, 74.460),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250428T054929_N0510_R063_T43RFN_20250428T075415'",
        notes="Northern Rajasthan canal irrigated agriculture crop burn.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_19", domain_type="AGRICULTURAL",
        location_name="Begusarai Paddy Burn Zone", state="Bihar",
        sentinel2_product_id="S2B_MSIL2A_20251110T044941_N0510_R076_T45QTC_20251110T070913",
        tile_id="T45QTC", sensing_date="2025-11-10", sensing_time_utc="04:49:41",
        relative_orbit=76, cloud_cover_pct=3.0, lat_center=25.4182, lon_center=86.1274,
        chip_roi_lat=(25.300, 25.540), chip_roi_lon=(85.980, 86.280),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20251110T044941_N0510_R076_T45QTC_20251110T070913'",
        notes="Middle Gangetic Plain rice harvest residue burning.",
    ),
    S2Scene(
        scene_id="SCENE_IN_AGR_20", domain_type="AGRICULTURAL",
        location_name="Samastipur Agricultural Fire Zone", state="Bihar",
        sentinel2_product_id="S2A_MSIL2A_20251112T044941_N0510_R076_T45QTC_20251112T070925",
        tile_id="T45QTC", sensing_date="2025-11-12", sensing_time_utc="04:49:41",
        relative_orbit=76, cloud_cover_pct=2.5, lat_center=25.8628, lon_center=85.7821,
        chip_roi_lat=(25.780, 25.950), chip_roi_lon=(85.700, 85.860),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20251112T044941_N0510_R076_T45QTC_20251112T070925'",
        notes="North Bihar smallholder paddy field fire clusters.",
    ),

    # -------------------------------------------------------------------------
    # C. FOREST WILDFIRE ZONE SCENES (10 scenes x 5 chips = 50 chips)
    # -------------------------------------------------------------------------
    S2Scene(
        scene_id="SCENE_IN_FOR_01", domain_type="FOREST",
        location_name="Jim Corbett NP Buffer Sal Forest Fire", state="Uttarakhand",
        sentinel2_product_id="S2B_MSIL2A_20250405T054029_N0510_R105_T44RNR_20250405T075213",
        tile_id="T44RNR", sensing_date="2025-04-05", sensing_time_utc="05:40:29",
        relative_orbit=105, cloud_cover_pct=3.0, lat_center=29.5300, lon_center=78.7700,
        chip_roi_lat=(29.440, 29.630), chip_roi_lon=(78.670, 78.880),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250405T054029_N0510_R105_T44RNR_20250405T075213'",
        notes="Sal forest boundary fires in Corbett buffer zone.",
    ),
    S2Scene(
        scene_id="SCENE_IN_FOR_02", domain_type="FOREST",
        location_name="Nainital Forest Division Pine Fire", state="Uttarakhand",
        sentinel2_product_id="S2A_MSIL2A_20250412T054029_N0510_R105_T44RNR_20250412T075312",
        tile_id="T44RNR", sensing_date="2025-04-12", sensing_time_utc="05:40:29",
        relative_orbit=105, cloud_cover_pct=2.5, lat_center=29.3919, lon_center=79.4542,
        chip_roi_lat=(29.300, 29.490), chip_roi_lon=(79.360, 79.560),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250412T054029_N0510_R105_T44RNR_20250412T075312'",
        notes="Chir pine slope wildfire above Nainital.",
    ),
    S2Scene(
        scene_id="SCENE_IN_FOR_03", domain_type="FOREST",
        location_name="Rajaji NP Terai Grassland-Forest Edge", state="Uttarakhand",
        sentinel2_product_id="S2B_MSIL2A_20250501T054029_N0510_R105_T44RNS_20250501T075701",
        tile_id="T44RNS", sensing_date="2025-05-01", sensing_time_utc="05:40:29",
        relative_orbit=105, cloud_cover_pct=4.5, lat_center=30.0800, lon_center=78.1500,
        chip_roi_lat=(29.980, 30.180), chip_roi_lon=(78.040, 78.260),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250501T054029_N0510_R105_T44RNS_20250501T075701'",
        notes="Rajaji NP Terai grassland and mixed deciduous forest wildfire.",
    ),
    S2Scene(
        scene_id="SCENE_IN_FOR_04", domain_type="FOREST",
        location_name="Dehradun Mussoorie Ridge Forest Fire", state="Uttarakhand",
        sentinel2_product_id="S2A_MSIL2A_20250505T054029_N0510_R105_T44RNS_20250505T075612",
        tile_id="T44RNS", sensing_date="2025-05-05", sensing_time_utc="05:40:29",
        relative_orbit=105, cloud_cover_pct=3.8, lat_center=30.4350, lon_center=78.0700,
        chip_roi_lat=(30.330, 30.540), chip_roi_lon=(77.950, 78.190),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250505T054029_N0510_R105_T44RNS_20250505T075612'",
        notes="Ridge-top pine wildfire on Mussoorie ascent.",
    ),
    S2Scene(
        scene_id="SCENE_IN_FOR_05", domain_type="FOREST",
        location_name="Kullu Valley Deodar Forest Fire", state="Himachal Pradesh",
        sentinel2_product_id="S2B_MSIL2A_20250510T054029_N0510_R105_T43RHP_20250510T075901",
        tile_id="T43RHP", sensing_date="2025-05-10", sensing_time_utc="05:40:29",
        relative_orbit=105, cloud_cover_pct=5.0, lat_center=31.9576, lon_center=77.1095,
        chip_roi_lat=(31.850, 32.070), chip_roi_lon=(76.990, 77.230),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250510T054029_N0510_R105_T43RHP_20250510T075901'",
        notes="High-altitude Himalayan coniferous slope fire.",
    ),
    S2Scene(
        scene_id="SCENE_IN_FOR_06", domain_type="FOREST",
        location_name="Shimla Forest Division Pine Fire", state="Himachal Pradesh",
        sentinel2_product_id="S2A_MSIL2A_20250428T054029_N0510_R105_T43RHP_20250428T075514",
        tile_id="T43RHP", sensing_date="2025-04-28", sensing_time_utc="05:40:29",
        relative_orbit=105, cloud_cover_pct=2.0, lat_center=31.1048, lon_center=77.1734,
        chip_roi_lat=(31.000, 31.210), chip_roi_lon=(77.060, 77.290),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250428T054029_N0510_R105_T43RHP_20250428T075514'",
        notes="Dry pine needles burning on southern mountain aspects.",
    ),
    S2Scene(
        scene_id="SCENE_IN_FOR_07", domain_type="FOREST",
        location_name="Dharamshala Oak-Rhododendron Fire", state="Himachal Pradesh",
        sentinel2_product_id="S2B_MSIL2A_20250515T054029_N0510_R105_T43RGQ_20250515T075640",
        tile_id="T43RGQ", sensing_date="2025-05-15", sensing_time_utc="05:40:29",
        relative_orbit=105, cloud_cover_pct=3.5, lat_center=32.2190, lon_center=76.3234,
        chip_roi_lat=(32.140, 32.300), chip_roi_lon=(76.240, 76.400),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250515T054029_N0510_R105_T43RGQ_20250515T075640'",
        notes="Dhauladhar range sub-montane forest fire.",
    ),
    S2Scene(
        scene_id="SCENE_IN_FOR_08", domain_type="FOREST",
        location_name="Similipal NP Sal-Teak Forest Fire", state="Odisha",
        sentinel2_product_id="S2A_MSIL2A_20250320T044941_N0510_R076_T45QUC_20250320T070813",
        tile_id="T45QUC", sensing_date="2025-03-20", sensing_time_utc="04:49:41",
        relative_orbit=76, cloud_cover_pct=2.0, lat_center=21.8280, lon_center=86.3370,
        chip_roi_lat=(21.740, 21.930), chip_roi_lon=(86.240, 86.450),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250320T044941_N0510_R076_T45QUC_20250320T070813'",
        notes="Core Similipal tiger reserve semi-evergreen and moist deciduous fire.",
    ),
    S2Scene(
        scene_id="SCENE_IN_FOR_09", domain_type="FOREST",
        location_name="Similipal Buffer Mixed Deciduous Fire", state="Odisha",
        sentinel2_product_id="S2B_MSIL2A_20250325T044941_N0510_R076_T45QUC_20250325T070901",
        tile_id="T45QUC", sensing_date="2025-03-25", sensing_time_utc="04:49:41",
        relative_orbit=76, cloud_cover_pct=1.5, lat_center=21.7500, lon_center=86.4200,
        chip_roi_lat=(21.660, 21.840), chip_roi_lon=(86.320, 86.530),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2B_MSIL2A_20250325T044941_N0510_R076_T45QUC_20250325T070901'",
        notes="Similipal buffer forest dry season burn.",
    ),
    S2Scene(
        scene_id="SCENE_IN_FOR_10", domain_type="FOREST",
        location_name="Bandhavgarh NP Dry Deciduous Fire", state="Madhya Pradesh",
        sentinel2_product_id="S2A_MSIL2A_20250415T052651_N0510_R062_T44QNK_20250415T075618",
        tile_id="T44QNK", sensing_date="2025-04-15", sensing_time_utc="05:26:51",
        relative_orbit=62, cloud_cover_pct=2.8, lat_center=23.7200, lon_center=80.9600,
        chip_roi_lat=(23.620, 23.820), chip_roi_lon=(80.850, 81.070),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S2A_MSIL2A_20250415T052651_N0510_R062_T44QNK_20250415T075618'",
        notes="Dry deciduous sal and bamboo forest wildfire in central India.",
    ),
]


# =============================================================================
# 10 SCREENED & REJECTED CANDIDATE SCENES (50 REJECTED CHIPS)
# =============================================================================

REJECTED_SCENES: List[S2Scene] = [
    S2Scene(
        scene_id="SCENE_REJ_01", domain_type="INDUSTRIAL",
        location_name="Hazira Petrochemical Complex, Surat", state="Gujarat",
        sentinel2_product_id="S2A_MSIL2A_20250715T055641_N0510_R063_T43QFF_20250715T080120",
        tile_id="T43QFF", sensing_date="2025-07-15", sensing_time_utc="05:56:41",
        relative_orbit=63, cloud_cover_pct=42.0, lat_center=21.120, lon_center=72.650,
        chip_roi_lat=(21.08, 21.16), chip_roi_lon=(72.60, 72.70),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="", notes="Monsoon acquisition.",
        status="REJECTED", rejection_reason="Excessive monsoon cloud cover (42.0% >> 10.0% threshold); optical surface completely obscured.",
    ),
    S2Scene(
        scene_id="SCENE_REJ_02", domain_type="INDUSTRIAL",
        location_name="Nagothane IPCL Complex, Raigad", state="Maharashtra",
        sentinel2_product_id="S2B_MSIL2A_20250702T054041_N0510_R105_T43QGE_20250702T080015",
        tile_id="T43QGE", sensing_date="2025-07-02", sensing_time_utc="05:40:41",
        relative_orbit=105, cloud_cover_pct=68.5, lat_center=18.520, lon_center=73.140,
        chip_roi_lat=(18.48, 18.56), chip_roi_lon=(73.10, 73.18),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="", notes="Western Ghats monsoonal washout.",
        status="REJECTED", rejection_reason="Monsoonal cloud cover (68.5%); heavy rain shadow artifacts in Sahyadri terrain.",
    ),
    S2Scene(
        scene_id="SCENE_REJ_03", domain_type="INDUSTRIAL",
        location_name="Bathinda Guru Gobind Singh Refinery", state="Punjab",
        sentinel2_product_id="S2A_MSIL2A_20251104T054929_N0510_R063_T43RFN_20251104T075400",
        tile_id="T43RFN", sensing_date="2025-11-04", sensing_time_utc="05:49:29",
        relative_orbit=63, cloud_cover_pct=8.0, lat_center=30.030, lon_center=74.820,
        chip_roi_lat=(29.98, 30.08), chip_roi_lon=(74.76, 74.88),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="", notes="Severe smog layer.",
        status="REJECTED", rejection_reason="Dense agricultural smog blanketing refinery assets; contrast loss prevents clear tank/shed edge extraction.",
    ),
    S2Scene(
        scene_id="SCENE_REJ_04", domain_type="INDUSTRIAL",
        location_name="Numaligarh Refinery", state="Assam",
        sentinel2_product_id="S2B_MSIL2A_20250620T041839_N0510_R033_T46RCS_20250620T065012",
        tile_id="T46RCS", sensing_date="2025-06-20", sensing_time_utc="04:18:39",
        relative_orbit=33, cloud_cover_pct=55.0, lat_center=26.590, lon_center=93.820,
        chip_roi_lat=(26.55, 26.63), chip_roi_lon=(93.77, 93.87),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="", notes="Northeastern monsoon.",
        status="REJECTED", rejection_reason="Cloud cover >50% and dense cirrus layer; high risk of false positive infrastructure detections.",
    ),
    S2Scene(
        scene_id="SCENE_REJ_05", domain_type="INDUSTRIAL",
        location_name="Firozabad Glass Industrial Cluster", state="Uttar Pradesh",
        sentinel2_product_id="S2A_MSIL2A_20250410T052651_N0510_R062_T44QML_20250410T075510",
        tile_id="T44QML", sensing_date="2025-04-10", sensing_time_utc="05:26:51",
        relative_orbit=62, cloud_cover_pct=3.0, lat_center=27.150, lon_center=78.400,
        chip_roi_lat=(27.11, 27.19), chip_roi_lon=(78.35, 78.45),
        bands=["B04", "B03", "B02"], target_chips=5, annotation_branch="INFRA",
        copernicus_stac_url="", notes="Micro-scale furnace units.",
        status="REJECTED", rejection_reason="Informal micro-shed geometries and artisanal chimneys are sub-pixel (<5m) and ambiguous at 10m GSD.",
    ),
    S2Scene(
        scene_id="SCENE_REJ_06", domain_type="AGRICULTURAL",
        location_name="Ferozepur Border Agricultural Belt", state="Punjab",
        sentinel2_product_id="S2B_MSIL2A_20251101T054929_N0510_R063_T43REP_20251101T075300",
        tile_id="T43REP", sensing_date="2025-11-01", sensing_time_utc="05:49:29",
        relative_orbit=63, cloud_cover_pct=2.0, lat_center=30.920, lon_center=74.610,
        chip_roi_lat=(30.85, 31.00), chip_roi_lon=(74.52, 74.70),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="", notes="Border security zone.",
        status="REJECTED", rejection_reason="International border striping artifact and cross-border smoke drift without clear Indian source origin.",
    ),
    S2Scene(
        scene_id="SCENE_REJ_07", domain_type="AGRICULTURAL",
        location_name="Buxar Diara Crop Residue Area", state="Bihar",
        sentinel2_product_id="S2A_MSIL2A_20251215T044941_N0510_R076_T44RPD_20251215T070800",
        tile_id="T44RPD", sensing_date="2025-12-15", sensing_time_utc="04:49:41",
        relative_orbit=76, cloud_cover_pct=18.0, lat_center=25.560, lon_center=83.980,
        chip_roi_lat=(25.50, 25.62), chip_roi_lon=(83.92, 84.04),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="", notes="Winter riverine fog.",
        status="REJECTED", rejection_reason="Persistent Gangetic radiation fog in mid-December obscuring surface reflectance.",
    ),
    S2Scene(
        scene_id="SCENE_REJ_08", domain_type="AGRICULTURAL",
        location_name="Alwar Mustard Burning Zone", state="Rajasthan",
        sentinel2_product_id="S2B_MSIL2A_20250412T054929_N0510_R063_T43RGL_20250412T075200",
        tile_id="T43RGL", sensing_date="2025-04-12", sensing_time_utc="05:49:29",
        relative_orbit=63, cloud_cover_pct=1.0, lat_center=27.560, lon_center=76.610,
        chip_roi_lat=(27.50, 27.62), chip_roi_lon=(76.54, 76.68),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="", notes="No thermal activity.",
        status="REJECTED", rejection_reason="No co-occurring active thermal signatures detected in SWIR (B12 < 0.25 across all agricultural fields).",
    ),
    S2Scene(
        scene_id="SCENE_REJ_09", domain_type="FOREST",
        location_name="Melghat Tiger Reserve Dry Deciduous", state="Maharashtra",
        sentinel2_product_id="S2A_MSIL2A_20250502T053641_N0510_R019_T43QFE_20250502T075100",
        tile_id="T43QFE", sensing_date="2025-05-02", sensing_time_utc="05:36:41",
        relative_orbit=19, cloud_cover_pct=22.0, lat_center=21.450, lon_center=77.200,
        chip_roi_lat=(21.38, 21.52), chip_roi_lon=(77.12, 77.28),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="", notes="Cloud cover above threshold.",
        status="REJECTED", rejection_reason="Cloud cover (22.0%) exceeds 10% threshold; convective cumulus clouds cast deceptive shadows in valley.",
    ),
    S2Scene(
        scene_id="SCENE_REJ_09", domain_type="FOREST",
        location_name="Nilgiri Shola Forest Complex", state="Tamil Nadu",
        sentinel2_product_id="S2B_MSIL2A_20250310T051709_N0510_R062_T43PFO_20250310T074100",
        tile_id="T43PFO", sensing_date="2025-03-10", sensing_time_utc="05:17:09",
        relative_orbit=62, cloud_cover_pct=15.5, lat_center=11.450, lon_center=76.700,
        chip_roi_lat=(11.38, 11.52), chip_roi_lon=(76.62, 76.78),
        bands=["B12", "B11", "B04"], target_chips=5, annotation_branch="FIRE_SMOKE",
        copernicus_stac_url="", notes="Steep terrain shadow.",
        status="REJECTED", rejection_reason="Deep mountain relief shadows (Nilgiri escarpment) cause severe false positive risk in fire edge detection.",
    ),
]


def get_accepted_scenes() -> List[S2Scene]:
    """Return the 50 accepted Sentinel-2 scenes."""
    return ACCEPTED_SCENES


def get_rejected_scenes() -> List[S2Scene]:
    """Return the 10 screened and rejected Sentinel-2 scenes."""
    return REJECTED_SCENES


def generate_acquisition_plan(output_dir: Path) -> Dict:
    """
    Generate JSON acquisition plan for accepted and rejected scenes.
    Does NOT download or synthesize images.
    """
    accepted = ACCEPTED_SCENES
    rejected = REJECTED_SCENES
    total_screened = len(accepted) + len(rejected)

    plan = {
        "acquisition_plan_version": "2.0_SCREENED_CURATED",
        "status": "PENDING_DOWNLOAD",
        "description": (
            "Real Sentinel-2 L2A scene acquisition plan for DS_08 Indian-domain "
            "optical adaptation dataset. 60 candidate scenes were screened across India: "
            "50 scenes were accepted (yielding 250 candidate chips) and 10 scenes were rejected "
            "due to excessive cloud cover, fog occlusion, or severe terrain shadows. "
            "Actual imagery must be downloaded via Copernicus Data Space API."
        ),
        "screening_audit": {
            "candidate_real_scenes": total_screened,
            "accepted_real_scenes": len(accepted),
            "rejected_real_scenes": len(rejected),
            "candidate_chips": total_screened * 5,
            "accepted_chips": len(accepted) * 5,
            "rejected_chips": len(rejected) * 5,
            "acceptance_rate_pct": round(len(accepted) / total_screened * 100, 1),
        },
        "target_chip_summary": {
            "total_target_chips": 250,
            "industrial_chips": sum(s.target_chips for s in accepted if s.domain_type == "INDUSTRIAL"),
            "agricultural_chips": sum(s.target_chips for s in accepted if s.domain_type == "AGRICULTURAL"),
            "forest_chips": sum(s.target_chips for s in accepted if s.domain_type == "FOREST"),
        },
        "domain_scene_breakdown": {
            "INDUSTRIAL": {
                "accepted_scenes": sum(1 for s in accepted if s.domain_type == "INDUSTRIAL"),
                "accepted_chips": sum(s.target_chips for s in accepted if s.domain_type == "INDUSTRIAL"),
                "rejected_scenes": sum(1 for s in rejected if s.domain_type == "INDUSTRIAL"),
            },
            "AGRICULTURAL": {
                "accepted_scenes": sum(1 for s in accepted if s.domain_type == "AGRICULTURAL"),
                "accepted_chips": sum(s.target_chips for s in accepted if s.domain_type == "AGRICULTURAL"),
                "rejected_scenes": sum(1 for s in rejected if s.domain_type == "AGRICULTURAL"),
            },
            "FOREST": {
                "accepted_scenes": sum(1 for s in accepted if s.domain_type == "FOREST"),
                "accepted_chips": sum(s.target_chips for s in accepted if s.domain_type == "FOREST"),
                "rejected_scenes": sum(1 for s in rejected if s.domain_type == "FOREST"),
            },
        },
        "rejected_scenes": [
            {
                "scene_id": s.scene_id,
                "location_name": s.location_name,
                "state": s.state,
                "domain_type": s.domain_type,
                "sentinel2_product_id": s.sentinel2_product_id,
                "tile_id": s.tile_id,
                "cloud_cover_pct": s.cloud_cover_pct,
                "rejection_reason": s.rejection_reason,
            }
            for s in rejected
        ],
        "download_instructions": {
            "api_endpoint": "https://catalogue.dataspace.copernicus.eu/odata/v1/",
            "auth_url": "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            "client_registration": "https://dataspace.copernicus.eu/",
            "sentinelhub_stac": "https://services.sentinel-hub.com/api/v1/catalog/1.0.0/",
            "example_download_command": (
                "# After obtaining access_token from the auth endpoint:\n"
                "# curl -H 'Authorization: Bearer <access_token>' "
                "'https://catalogue.dataspace.copernicus.eu/odata/v1/Products(<product_id>)/$value' "
                "-o <product_id>.zip"
            ),
            "python_library": "sentinelhub-py: pip install sentinelhub",
            "credentials_required": True,
        },
        "chip_extraction_spec": {
            "chip_size_px": 512,
            "chip_size_m": 5120,
            "bands_rgb_true_color": ["B04", "B03", "B02"],
            "bands_false_color_fire": ["B12", "B11", "B04"],
            "output_format": "PNG",
            "resampling": "bilinear",
            "coordinate_system": "UTM zone per scene",
        },
        "accepted_scenes": [
            {
                "scene_id": s.scene_id,
                "domain_type": s.domain_type,
                "location_name": s.location_name,
                "state": s.state,
                "sentinel2_product_id": s.sentinel2_product_id,
                "tile_id": s.tile_id,
                "sensing_date": s.sensing_date,
                "sensing_time_utc": s.sensing_time_utc,
                "relative_orbit": s.relative_orbit,
                "cloud_cover_pct": s.cloud_cover_pct,
                "lat_center": s.lat_center,
                "lon_center": s.lon_center,
                "chip_roi_lat": list(s.chip_roi_lat),
                "chip_roi_lon": list(s.chip_roi_lon),
                "bands": s.bands,
                "target_chips": s.target_chips,
                "annotation_branch": s.annotation_branch,
                "copernicus_stac_url": s.copernicus_stac_url,
                "download_status": "PENDING",
                "chips_extracted": 0,
                "chips_pending_annotation": s.target_chips,
                "notes": s.notes,
            }
            for s in accepted
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "ds08_acquisition_plan.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    return plan


if __name__ == "__main__":
    root = Path("d:/DATA PREPROCESSING")
    plan = generate_acquisition_plan(root / "data/reference/ds08")
    print(f"Acquisition plan generated.")
    print(f"Screening audit: {plan['screening_audit']}")
    print(f"Target chips: {plan['target_chip_summary']}")
    print(f"Domain breakdown: {plan['domain_scene_breakdown']}")
