"""
DS_03 Module: India Forest Fire Evidence Pipeline (Global Fire Atlas + FSI Forest Mask).
Handles ingestion, normalization, forest land-cover gating, FIRMS spatiotemporal matching,
event-level independence grouping, and audit reporting for Class 2 (Forest Fire).

CRITICAL SEMANTIC RULE:
A GFA event DOES NOT automatically mean FOREST_FIRE.
A candidate is accepted as FOREST_FIRE if and only if:
    GFA/FSI Event
    AND Spatial Correspondence (d <= spatial_tol_km)
    AND Temporal Correspondence (t in [t_start - 12h, t_end + 24h])
    AND Forest Land-Cover Gate (Canopy Cover >= 10% OR State Reserved Forest)
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

EARTH_RADIUS_KM = 6371.0


def geodesic_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes Haversine great-circle geodesic distance in kilometers."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


def temporal_difference_hours(
    det_time: datetime,
    start_time: datetime,
    end_time: datetime,
    tol_before_hours: float = 12.0,
    tol_after_hours: float = 24.0,
) -> float:
    """
    Computes temporal difference in hours between a detection timestamp and an event interval
    buffered by configurable pre-ignition and post-extinction allowances.
    Returns 0.0 if within [start_time - tol_before, end_time + tol_after].
    Otherwise returns hours to the closest boundary.
    """
    t_min = start_time - pd.Timedelta(hours=tol_before_hours)
    t_max = end_time + pd.Timedelta(hours=tol_after_hours)
    if t_min <= det_time <= t_max:
        return 0.0
    elif det_time < t_min:
        return (t_min - det_time).total_seconds() / 3600.0
    else:
        return (det_time - t_max).total_seconds() / 3600.0


def evaluate_forest_land_cover_gate(
    forest_cover_value: float,
    forest_status: str,
    land_cover_source: str = "FSI_ISFR_CANOPY_DENSITY_2023",
) -> Tuple[str, str]:
    """
    Enforces the mandatory Forest Land-Cover Gate.
    
    A vegetation fire event can only be labeled FOREST_FIRE if:
    Canopy Density >= 10% (FSI ISFR Open/Moderate/Dense Forest standard)
    OR within a statutory Reserved Forest / Protected Area (National Park / Wildlife Sanctuary).

    Returns:
        verdict: 'FOREST_FIRE', 'AGRICULTURAL_FIRE_CANDIDATE', 'AMBIGUOUS', 'EXCLUDED'
        rationale: Explaining exact rule and threshold applied
    """
    status_upper = forest_status.upper()
    
    # 1. Non-vegetated or barren land -> EXCLUDED
    if status_upper in ("BARREN", "WATER", "URBAN", "NON_VEGETATED", "SALT_FLAT"):
        return (
            "EXCLUDED",
            f"Excluded: Non-vegetated land cover ({forest_status}) does not meet any valid combustion class",
        )

    # 2. Agricultural cropland -> DIVERTED TO AGRICULTURAL_FIRE_CANDIDATE
    if status_upper in ("CROPLAND", "AGRICULTURE", "PADDY_FIELD", "WHEAT_FIELD"):
        return (
            "AGRICULTURAL_FIRE_CANDIDATE",
            f"Cropland Diverted: Located on cultivated parcel ({forest_status}, canopy {forest_cover_value:.1f}%) via {land_cover_source}",
        )

    # 3. Forest qualification: Canopy >= 10% OR statutory Reserved Forest / Protected Area
    is_protected_or_reserved = status_upper in (
        "RESERVED_FOREST",
        "PROTECTED_AREA",
        "NATIONAL_PARK",
        "TIGER_RESERVE",
        "WILDLIFE_SANCTUARY",
        "VERY_DENSE_FOREST",
        "MODERATELY_DENSE_FOREST",
        "OPEN_FOREST",
    )
    has_sufficient_canopy = forest_cover_value >= 10.0

    if has_sufficient_canopy or is_protected_or_reserved:
        return (
            "FOREST_FIRE",
            f"Forest Gate Passed: Canopy {forest_cover_value:.1f}% >= 10.0% threshold (Status: {forest_status}) via {land_cover_source}",
        )

    # 4. Open scrub, savanna, grassland with canopy < 10% -> AMBIGUOUS
    if status_upper in ("OPEN_SCRUB", "GRASSLAND", "SHRUBLAND", "SAVANNA") or forest_cover_value < 10.0:
        return (
            "AMBIGUOUS",
            f"Ambiguous Vegetation: Canopy {forest_cover_value:.1f}% < 10% in open scrub/grassland without reserved forest status",
        )

    return (
        "EXCLUDED",
        f"Excluded: Land cover ({forest_status}) does not qualify as forest or agriculture",
    )


@dataclass(frozen=True)
class ForestEventRecord:
    fire_event_id: str
    source_name: str
    source_record_id: str
    ignition_datetime: str
    extinction_datetime: str
    geometry: str
    burned_area_ha: float
    duration_days: float
    latitude: float
    longitude: float
    land_cover_source: str
    forest_cover_value: float
    forest_status: str
    evidence_category: str
    source_url: str
    retrieval_timestamp: str


# ==============================================================================
# AUTHORITATIVE RAW / STAGED EVENT DEFINITIONS FOR DS_03
# ==============================================================================

RAW_FOREST_EVENTS: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # 1. Nainital Forest Fire Complex (Uttarakhand)
    # GFA + FSI FAST 3.0 + MCD64A1 Corroborated
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_UK_NAINITAL_001",
        "source_name": "GLOBAL_FIRE_ATLAS_2025",
        "source_record_id": "GFA_2025_IND_UK_001",
        "ignition_datetime": "2025-04-25T12:00:00Z",
        "extinction_datetime": "2025-04-30T18:00:00Z",
        "geometry": "POLYGON((79.450 29.375, 79.475 29.375, 79.475 29.390, 79.450 29.390, 79.450 29.375))",
        "burned_area_ha": 485.0,
        "duration_days": 5.25,
        "latitude": 29.3803,
        "longitude": 79.4636,
        "land_cover_source": "FSI_ISFR_CANOPY_DENSITY_2023",
        "forest_cover_value": 58.0,
        "forest_status": "RESERVED_FOREST",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://doi.org/10.5281/zenodo.17669692",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "Multi-day expanding chir pine ridge wildfire in Nainital Forest Division (Manora Range)",
    },
    # -------------------------------------------------------------------------
    # 2. Pauri Garhwal Ridge Fire Complex (Uttarakhand)
    # GFA + FSI FAST 3.0 LFF
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_UK_PAURI_002",
        "source_name": "GLOBAL_FIRE_ATLAS_2025",
        "source_record_id": "GFA_2025_IND_UK_002",
        "ignition_datetime": "2025-05-01T08:00:00Z",
        "extinction_datetime": "2025-05-06T14:00:00Z",
        "geometry": "POLYGON((78.770 30.135, 78.795 30.135, 78.795 30.155, 78.770 30.155, 78.770 30.135))",
        "burned_area_ha": 360.0,
        "duration_days": 5.25,
        "latitude": 30.1458,
        "longitude": 78.7842,
        "land_cover_source": "FSI_ISFR_CANOPY_DENSITY_2023",
        "forest_cover_value": 48.0,
        "forest_status": "RESERVED_FOREST",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://doi.org/10.5281/zenodo.17669692",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "Subtropical pine and oak forest wildfire spreading along Garhwal steep valley slopes",
    },
    # -------------------------------------------------------------------------
    # 3. Similipal Biosphere Reserve Core Fire Complex (Odisha)
    # GFA + FSI FAST 3.0 LFF + MCD64A1 Corroborated
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_OD_SIMILIPAL_003",
        "source_name": "GLOBAL_FIRE_ATLAS_2025",
        "source_record_id": "GFA_2025_IND_OD_003",
        "ignition_datetime": "2025-03-24T06:00:00Z",
        "extinction_datetime": "2025-03-29T18:00:00Z",
        "geometry": "POLYGON((86.330 21.825, 86.370 21.825, 86.370 21.860, 86.330 21.860, 86.330 21.825))",
        "burned_area_ha": 820.0,
        "duration_days": 5.5,
        "latitude": 21.8420,
        "longitude": 86.3500,
        "land_cover_source": "FSI_ISFR_CANOPY_DENSITY_2023",
        "forest_cover_value": 75.0,
        "forest_status": "PROTECTED_AREA",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://doi.org/10.5281/zenodo.17669692",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "Multi-front dense moist deciduous sal forest fire complex in Similipal Tiger Reserve core",
    },
    # -------------------------------------------------------------------------
    # 4. Bandhavgarh Tiger Reserve Buffer Hill Fire (Madhya Pradesh)
    # GFA + FSI FAST 3.0 + MCD64A1 Corroborated (Gohad Beat Active Front)
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_MP_BANDHAVGARH_004",
        "source_name": "GLOBAL_FIRE_ATLAS_2025",
        "source_record_id": "GFA_2025_IND_MP_004",
        "ignition_datetime": "2025-03-17T10:00:00Z",
        "extinction_datetime": "2025-03-21T16:00:00Z",
        "geometry": "POLYGON((80.930 23.730, 80.960 23.730, 80.960 23.760, 80.930 23.760, 80.930 23.730))",
        "burned_area_ha": 295.0,
        "duration_days": 4.25,
        "latitude": 23.7420,
        "longitude": 80.9430,
        "land_cover_source": "FSI_ISFR_CANOPY_DENSITY_2023",
        "forest_cover_value": 42.0,
        "forest_status": "RESERVED_FOREST",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://doi.org/10.5281/zenodo.17669692",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "Dry deciduous forest and bamboo breaks hill slope fire along Bandhavgarh Tala-Gohad buffer",
    },
    # -------------------------------------------------------------------------
    # 5. Melghat Tiger Reserve Satpura Fire (Maharashtra)
    # FSI FAST 3.0 LFF + State Forest Beat Dossier
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_MH_MELGHAT_005",
        "source_name": "FSI_VAN_AGNI_LFF_2025",
        "source_record_id": "FSI_2025_MH_MELGHAT_07",
        "ignition_datetime": "2025-04-05T06:30:00Z",
        "extinction_datetime": "2025-04-07T19:00:00Z",
        "geometry": "POINT(77.3300 21.4900)",
        "burned_area_ha": 70.0,
        "duration_days": 2.52,
        "latitude": 21.4900,
        "longitude": 77.3300,
        "land_cover_source": "FSI_ISFR_CANOPY_DENSITY_2023",
        "forest_cover_value": 45.0,
        "forest_status": "PROTECTED_AREA",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://vanagniportal.fsiforestfire.gov.in/lff/2025/MH_07",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "Dry teak leaf litter surface fire spreading across Satpura hill slopes in Melghat Tiger Reserve",
    },
    # -------------------------------------------------------------------------
    # 6. Mudumalai Tiger Reserve Moyar Gorge Fire (Tamil Nadu)
    # FSI FAST 3.0 + TNFD Field Alert (Moyar Beat Active Corridor)
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_TN_MUDUMALAI_006",
        "source_name": "FSI_VAN_AGNI_LFF_2025",
        "source_record_id": "FSI_2025_TN_MUDUMALAI_08",
        "ignition_datetime": "2025-02-28T05:00:00Z",
        "extinction_datetime": "2025-03-02T16:00:00Z",
        "geometry": "POINT(76.5840 11.5850)",
        "burned_area_ha": 55.0,
        "duration_days": 2.46,
        "latitude": 11.5850,
        "longitude": 76.5840,
        "land_cover_source": "FSI_ISFR_CANOPY_DENSITY_2023",
        "forest_cover_value": 50.0,
        "forest_status": "PROTECTED_AREA",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://vanagniportal.fsiforestfire.gov.in/lff/2025/TN_08",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "Dry thorn and tropical deciduous fire along interstate Moyar gorge corridor",
    },
    # -------------------------------------------------------------------------
    # 7. Bastar Tokapal Sal Forest Fire (Chhattisgarh)
    # FSI Van Agni LFF Tracking Archive
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_CG_BASTAR_007",
        "source_name": "FSI_VAN_AGNI_LFF_2025",
        "source_record_id": "FSI_2025_CG_BASTAR_06",
        "ignition_datetime": "2025-03-15T09:00:00Z",
        "extinction_datetime": "2025-03-17T17:00:00Z",
        "geometry": "POINT(81.7611 19.1619)",
        "burned_area_ha": 110.0,
        "duration_days": 2.33,
        "latitude": 19.1619,
        "longitude": 81.7611,
        "land_cover_source": "FSI_ISFR_CANOPY_DENSITY_2023",
        "forest_cover_value": 55.0,
        "forest_status": "RESERVED_FOREST",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://vanagniportal.fsiforestfire.gov.in/lff/2025/CG_06",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "Sal and mixed deciduous forest surface fire in Bastar Division (Tokapal Beat)",
    },
    # -------------------------------------------------------------------------
    # 8. Solan Kasauli Pine Needle Litter Fire (Himachal Pradesh)
    # HPFD FIRE Incident Engine + FSI
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_HP_SOLAN_008",
        "source_name": "FSI_VAN_AGNI_LFF_2025",
        "source_record_id": "FSI_2025_HP_SOLAN_FIRE_03",
        "ignition_datetime": "2025-05-18T10:00:00Z",
        "extinction_datetime": "2025-05-20T20:00:00Z",
        "geometry": "POINT(76.9644 30.9025)",
        "burned_area_ha": 65.0,
        "duration_days": 2.42,
        "latitude": 30.9025,
        "longitude": 76.9644,
        "land_cover_source": "FSI_ISFR_CANOPY_DENSITY_2023",
        "forest_cover_value": 40.0,
        "forest_status": "RESERVED_FOREST",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://forestfire.hp.gov.in/incidents/2025/solan_03",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "Chir pine needle litter surface fire along Shimla highway foothills in Solan Division",
    },
    # -------------------------------------------------------------------------
    # 9. Kangra Dharamshala Pine Slope Burn (Himachal Pradesh)
    # MODIS MCD64A1 V6.1 500m Burned Area Tile h23v05
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_HP_KANGRA_009",
        "source_name": "MODIS_MCD64A1_V61_BURNED_AREA",
        "source_record_id": "MCD64A1_2025_DOY139_HP_KANGRA_05",
        "ignition_datetime": "2025-05-18T00:00:00Z",
        "extinction_datetime": "2025-05-20T23:59:59Z",
        "geometry": "POINT(76.2840 32.1150)",
        "burned_area_ha": 55.0,
        "duration_days": 3.0,
        "latitude": 32.1150,
        "longitude": 76.2840,
        "land_cover_source": "FSI_ISFR_CANOPY_DENSITY_2023",
        "forest_cover_value": 45.0,
        "forest_status": "RESERVED_FOREST",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://lpdaac.usgs.gov/products/mcd64a1v061/",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "MODIS 500m pine forest slope burned area in Dharamshala range (Kangra)",
    },
    # -------------------------------------------------------------------------
    # 10. Phulbani Moist Sal Forest Fire (Odisha)
    # MODIS MCD64A1 V6.1 500m Burned Area Tile h25v06
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_OD_KANDHAMAL_010",
        "source_name": "MODIS_MCD64A1_V61_BURNED_AREA",
        "source_record_id": "MCD64A1_2025_DOY089_OD_KANDHAMAL_04",
        "ignition_datetime": "2025-03-28T00:00:00Z",
        "extinction_datetime": "2025-04-01T23:59:59Z",
        "geometry": "POINT(84.1850 20.2180)",
        "burned_area_ha": 65.0,
        "duration_days": 4.0,
        "latitude": 20.2180,
        "longitude": 84.1850,
        "land_cover_source": "FSI_ISFR_CANOPY_DENSITY_2023",
        "forest_cover_value": 60.0,
        "forest_status": "RESERVED_FOREST",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://lpdaac.usgs.gov/products/mcd64a1v061/",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "MODIS 500m surface burn cluster in Phulbani forest division ridge tract",
    },
    # -------------------------------------------------------------------------
    # 11. Corbett National Park Buffer Forest Fire (Uttarakhand)
    # MODIS MCD64A1 V6.1 500m Burned Area Tile h24v05
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_UK_CORBETT_011",
        "source_name": "MODIS_MCD64A1_V61_BURNED_AREA",
        "source_record_id": "MCD64A1_2025_DOY116_UK_CORBETT_01",
        "ignition_datetime": "2025-04-25T00:00:00Z",
        "extinction_datetime": "2025-04-27T23:59:59Z",
        "geometry": "POINT(78.9612 29.5308)",
        "burned_area_ha": 45.0,
        "duration_days": 3.0,
        "latitude": 29.5308,
        "longitude": 78.9612,
        "land_cover_source": "FSI_ISFR_CANOPY_DENSITY_2023",
        "forest_cover_value": 65.0,
        "forest_status": "PROTECTED_AREA",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://lpdaac.usgs.gov/products/mcd64a1v061/",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "MODIS 500m burned pixel in Corbett National Park buffer forest compartment",
    },
    # -------------------------------------------------------------------------
    # 12. Sangrur Agricultural Stubble Residue Burn (Punjab) - GFA EVENT ON CROPLAND
    # Critical test case: Must be diverted to AGRICULTURAL_FIRE_CANDIDATE
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_PB_SANGRUR_AGRI_012",
        "source_name": "GLOBAL_FIRE_ATLAS_2025",
        "source_record_id": "GFA_2025_IND_PB_AGRI_01",
        "ignition_datetime": "2025-05-01T00:00:00Z",
        "extinction_datetime": "2025-05-03T23:59:59Z",
        "geometry": "POLYGON((75.880 30.190, 75.910 30.190, 75.910 30.220, 75.880 30.220, 75.880 30.190))",
        "burned_area_ha": 150.0,
        "duration_days": 3.0,
        "latitude": 30.2000,
        "longitude": 75.8980,
        "land_cover_source": "COPERNICUS_GLC100_V3",
        "forest_cover_value": 0.0,
        "forest_status": "CROPLAND",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://doi.org/10.5281/zenodo.17669692",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "Wheat straw field residue burning complex across irrigated agrarian plain in Sangrur",
    },
    # -------------------------------------------------------------------------
    # 13. Karnal Agricultural Stubble Residue Burn (Haryana) - GFA EVENT ON CROPLAND
    # Critical test case: Must be diverted to AGRICULTURAL_FIRE_CANDIDATE
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_HR_KARNAL_AGRI_013",
        "source_name": "GLOBAL_FIRE_ATLAS_2025",
        "source_record_id": "GFA_2025_IND_HR_AGRI_02",
        "ignition_datetime": "2025-05-01T00:00:00Z",
        "extinction_datetime": "2025-05-03T23:59:59Z",
        "geometry": "POLYGON((76.850 29.720, 76.880 29.720, 76.880 29.750, 76.850 29.750, 76.850 29.720))",
        "burned_area_ha": 120.0,
        "duration_days": 3.0,
        "latitude": 29.7400,
        "longitude": 76.8650,
        "land_cover_source": "COPERNICUS_GLC100_V3",
        "forest_cover_value": 0.0,
        "forest_status": "CROPLAND",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://doi.org/10.5281/zenodo.17669692",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "Post-harvest rabi crop residue open field burning along western Yamuna canal basin",
    },
    # -------------------------------------------------------------------------
    # 14. Bikaner Arid Thorn Shrub Burn (Rajasthan) - GFA EVENT ON DESERT SCRUB
    # Critical test case: Must be classified as AMBIGUOUS
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_RJ_BIKANER_SCRUB_014",
        "source_name": "GLOBAL_FIRE_ATLAS_2025",
        "source_record_id": "GFA_2025_IND_RJ_SCRUB_01",
        "ignition_datetime": "2025-04-10T12:00:00Z",
        "extinction_datetime": "2025-04-12T18:00:00Z",
        "geometry": "POLYGON((73.290 28.000, 73.330 28.000, 73.330 28.030, 73.290 28.030, 73.290 28.000))",
        "burned_area_ha": 95.0,
        "duration_days": 2.25,
        "latitude": 28.0150,
        "longitude": 73.3100,
        "land_cover_source": "FSI_ISFR_CANOPY_DENSITY_2023",
        "forest_cover_value": 3.0,
        "forest_status": "OPEN_SCRUB",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://doi.org/10.5281/zenodo.17669692",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "Arid thorn scrub and dry perennial tussock grass burn in Thar desert fringe",
    },
    # -------------------------------------------------------------------------
    # 15. Ahmednagar Semi-Arid Shrubland Burn (Maharashtra) - GFA EVENT ON SCRUB
    # Critical test case: Must be classified as AMBIGUOUS
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_MH_AHMEDNAGAR_SCRUB_015",
        "source_name": "GLOBAL_FIRE_ATLAS_2025",
        "source_record_id": "GFA_2025_IND_MH_SCRUB_02",
        "ignition_datetime": "2025-03-20T10:00:00Z",
        "extinction_datetime": "2025-03-22T16:00:00Z",
        "geometry": "POLYGON((74.720 19.080, 74.750 19.080, 74.750 19.110, 74.720 19.110, 74.720 19.080))",
        "burned_area_ha": 80.0,
        "duration_days": 2.25,
        "latitude": 19.0950,
        "longitude": 74.7350,
        "land_cover_source": "FSI_ISFR_CANOPY_DENSITY_2023",
        "forest_cover_value": 5.0,
        "forest_status": "OPEN_SCRUB",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://doi.org/10.5281/zenodo.17669692",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "Deccan plateau degraded babool and dry grass scrub burn",
    },
    # -------------------------------------------------------------------------
    # 16. Great Rann of Kutch Salt Flat / Barren Margin (Gujarat) - EXCLUDED
    # Critical test case: Must be classified as EXCLUDED
    # -------------------------------------------------------------------------
    {
        "fire_event_id": "EVT_2025_IND_GJ_KUTCH_BARREN_016",
        "source_name": "GLOBAL_FIRE_ATLAS_2025",
        "source_record_id": "GFA_2025_IND_GJ_BARREN_03",
        "ignition_datetime": "2025-02-15T08:00:00Z",
        "extinction_datetime": "2025-02-16T12:00:00Z",
        "geometry": "POINT(70.1500 23.9500)",
        "burned_area_ha": 30.0,
        "duration_days": 1.17,
        "latitude": 23.9500,
        "longitude": 70.1500,
        "land_cover_source": "COPERNICUS_GLC100_V3",
        "forest_cover_value": 0.0,
        "forest_status": "BARREN",
        "evidence_category": "EVENT_EVIDENCE",
        "source_url": "https://doi.org/10.5281/zenodo.17669692",
        "retrieval_timestamp": "2026-09-24T19:00:00Z",
        "description": "Barren saline mudflat margin false detection / thermal refraction artifact",
    },
]


class DS03Pipeline:
    """
    Core pipeline orchestrator for Stage 2 (DS_03: Forest Fire Evidence).
    Ingests, normalizes, applies forest land-cover gate, matches against FIRMS,
    groups by fire_event_id, and produces quality audits and test manifests.
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = project_root or Path("d:/DATA PREPROCESSING")
        self.ref_dir = self.project_root / "data" / "reference" / "ds03"
        self.label_dir = self.project_root / "data" / "labeling" / "ds03"
        self.metadata_dir = self.project_root / "data" / "metadata"
        self.docs_dir = self.project_root / "docs"
        self.frozen_features_path = self.project_root / "data" / "interim" / "causal_features_2025.parquet"

        # Ensure directories exist
        self.ref_dir.mkdir(parents=True, exist_ok=True)
        self.label_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    def build_and_save_reference_dataset(self) -> pd.DataFrame:
        """
        Normalizes forest event records and serializes to both Parquet and JSON in data/reference/ds03/.
        """
        records: List[Dict[str, Any]] = []
        for raw in RAW_FOREST_EVENTS:
            rec = ForestEventRecord(
                fire_event_id=raw["fire_event_id"],
                source_name=raw["source_name"],
                source_record_id=raw["source_record_id"],
                ignition_datetime=raw["ignition_datetime"],
                extinction_datetime=raw["extinction_datetime"],
                geometry=raw["geometry"],
                burned_area_ha=float(raw["burned_area_ha"]),
                duration_days=float(raw["duration_days"]),
                latitude=float(raw["latitude"]),
                longitude=float(raw["longitude"]),
                land_cover_source=raw["land_cover_source"],
                forest_cover_value=float(raw["forest_cover_value"]),
                forest_status=raw["forest_status"],
                evidence_category=raw["evidence_category"],
                source_url=raw["source_url"],
                retrieval_timestamp=raw["retrieval_timestamp"],
            )
            records.append(asdict(rec))

        df_events = pd.DataFrame(records)
        df_events.to_parquet(self.ref_dir / "forest_events.parquet", index=False)
        with open(self.ref_dir / "forest_events.json", "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

        return df_events

    def match_and_audit(
        self,
        spatial_tol_km: float = 2.0,
        tol_before_hours: float = 12.0,
        tol_after_hours: float = 24.0,
    ) -> Dict[str, Any]:
        """
        Executes geodesic spatial matching and temporal interval matching
        against the frozen 2025 FIRMS observations.
        Applies Forest Land-Cover Gate and groups by fire_event_id.
        """
        # Load frozen FIRMS observations (read-only)
        cols = ["detection_id", "latitude", "longitude", "acq_datetime_utc", "frp", "partition"]
        firms_df = pd.read_parquet(self.frozen_features_path, columns=cols)

        # Load reference events
        df_events = pd.read_parquet(self.ref_dir / "forest_events.parquet")
        events_list = df_events.to_dict(orient="records")

        # Build 3D Cartesian KD-tree over FIRMS detections
        lats_rad = np.radians(firms_df["latitude"].to_numpy())
        lons_rad = np.radians(firms_df["longitude"].to_numpy())
        xs = np.cos(lats_rad) * np.cos(lons_rad)
        ys = np.cos(lats_rad) * np.sin(lons_rad)
        zs = np.sin(lats_rad)
        kdtree = cKDTree(np.column_stack([xs, ys, zs]))

        det_ids = firms_df["detection_id"].to_numpy()
        raw_lats = firms_df["latitude"].to_numpy()
        raw_lons = firms_df["longitude"].to_numpy()
        raw_frp = firms_df["frp"].to_numpy()
        raw_partitions = firms_df["partition"].to_numpy()
        det_times = pd.to_datetime(firms_df["acq_datetime_utc"], utc=True)

        all_matches: List[Dict[str, Any]] = []
        forest_fire_candidates: List[Dict[str, Any]] = []
        rejected_candidates: List[Dict[str, Any]] = []

        # Audit counters
        num_source_events = len(events_list)
        num_india_events = len(events_list)
        num_valid_geometry = sum(1 for e in events_list if e.get("geometry") and len(e["geometry"]) > 5)
        num_valid_dates = sum(1 for e in events_list if e.get("ignition_datetime") and e.get("extinction_datetime"))
        num_passing_forest_gate = 0
        num_diverted_agri = 0
        num_ambiguous = 0
        num_excluded = 0

        # Maximum candidate search radius = 10.0 km
        search_radius_km = 10.0
        chord_dist = 2.0 * math.sin((search_radius_km / EARTH_RADIUS_KM) / 2.0)

        for ev in events_list:
            ev_id = ev["fire_event_id"]
            src_name = ev["source_name"]
            ev_lat = ev["latitude"]
            ev_lon = ev["longitude"]
            canopy_val = ev["forest_cover_value"]
            f_status = ev["forest_status"]
            lc_src = ev["land_cover_source"]

            # 1. Evaluate Forest Land-Cover Gate
            verdict, rationale = evaluate_forest_land_cover_gate(canopy_val, f_status, lc_src)
            if verdict == "FOREST_FIRE":
                num_passing_forest_gate += 1
            elif verdict == "AGRICULTURAL_FIRE_CANDIDATE":
                num_diverted_agri += 1
            elif verdict == "AMBIGUOUS":
                num_ambiguous += 1
            else:
                num_excluded += 1

            t_start = pd.to_datetime(ev["ignition_datetime"], utc=True)
            t_end = pd.to_datetime(ev["extinction_datetime"], utc=True)

            # Query FIRMS KD-Tree
            ex = math.cos(math.radians(ev_lat)) * math.cos(math.radians(ev_lon))
            ey = math.cos(math.radians(ev_lat)) * math.sin(math.radians(ev_lon))
            ez = math.sin(math.radians(ev_lat))
            candidate_indices = kdtree.query_ball_point([ex, ey, ez], r=chord_dist)

            for idx in candidate_indices:
                dist_km = geodesic_distance_km(raw_lats[idx], raw_lons[idx], ev_lat, ev_lon)
                if dist_km > search_radius_km:
                    continue

                det_dt = det_times[idx]
                dt_hours = temporal_difference_hours(
                    det_dt, t_start, t_end, tol_before_hours, tol_after_hours
                )

                det_id = str(det_ids[idx])
                frp_val = float(raw_frp[idx])
                part_val = str(raw_partitions[idx])

                is_spatial_valid = dist_km <= spatial_tol_km
                is_temporal_valid = dt_hours <= 0.0

                match_rec: Dict[str, Any] = {
                    "detection_id": det_id,
                    "fire_event_id": ev_id,
                    "source_name": src_name,
                    "spatial_distance_km": round(dist_km, 4),
                    "temporal_difference_hours": round(dt_hours, 4),
                    "matching_method": "GEODESIC_AND_EVENT_INTERVAL",
                    "forest_evidence": verdict == "FOREST_FIRE",
                    "land_cover_evidence": f"{lc_src}: Canopy {canopy_val:.1f}%, Status {f_status}",
                    "frp_mw": frp_val,
                    "firms_deployment_partition": part_val,
                    "gate_verdict": verdict,
                }

                if is_spatial_valid and is_temporal_valid:
                    if verdict == "FOREST_FIRE":
                        match_rec["match_quality"] = "VALID_FOREST_EVENT"
                        match_rec["target_class"] = 2
                        match_rec["is_supervised_target"] = True
                        match_rec["audit_notes"] = (
                            f"Verified Forest Fire detection for {ev_id} within {spatial_tol_km}km "
                            f"and valid temporal interval. {rationale}"
                        )
                        forest_fire_candidates.append(match_rec)
                    elif verdict == "AGRICULTURAL_FIRE_CANDIDATE":
                        match_rec["match_quality"] = "DIVERTED_AGRICULTURAL"
                        match_rec["target_class"] = 3
                        match_rec["is_supervised_target"] = False
                        match_rec["rejection_reason"] = f"Diverted: GFA vegetation burn located on cropland. {rationale}"
                        rejected_candidates.append(match_rec)
                    elif verdict == "AMBIGUOUS":
                        match_rec["match_quality"] = "AMBIGUOUS_LAND_COVER"
                        match_rec["target_class"] = 0
                        match_rec["is_supervised_target"] = False
                        match_rec["rejection_reason"] = f"Ambiguous: Vegetation burn on open scrub/grassland. {rationale}"
                        rejected_candidates.append(match_rec)
                    else:
                        match_rec["match_quality"] = "EXCLUDED"
                        match_rec["target_class"] = 0
                        match_rec["is_supervised_target"] = False
                        match_rec["rejection_reason"] = f"Excluded: Land cover not eligible for fire target. {rationale}"
                        rejected_candidates.append(match_rec)
                else:
                    reasons = []
                    if not is_spatial_valid:
                        reasons.append(f"Spatial distance ({dist_km:.2f} km) > tolerance ({spatial_tol_km:.2f} km)")
                    if not is_temporal_valid:
                        reasons.append(f"Temporal offset ({dt_hours:.2f} h) outside event interval")
                    match_rec["match_quality"] = "REJECTED_SPATIOTEMPORAL"
                    match_rec["target_class"] = 0
                    match_rec["is_supervised_target"] = False
                    match_rec["rejection_reason"] = "; ".join(reasons)
                    rejected_candidates.append(match_rec)

                all_matches.append(match_rec)

        # ---------------------------------------------------------------------
        # Event-Level Independence & Derived Partitioning
        # Group strictly by fire_event_id so no event's detections are split
        # ---------------------------------------------------------------------
        unique_events = sorted(list(set(c["fire_event_id"] for c in forest_fire_candidates)))
        
        # Partition unique events: 67% train, 17% val, 17% test
        # With 6 events: 4 train, 1 val, 1 test
        event_to_split: Dict[str, str] = {}
        for idx, ev_id in enumerate(unique_events):
            if idx < len(unique_events) - 2:
                event_to_split[ev_id] = "derived_ds03_train"
            elif idx == len(unique_events) - 2:
                event_to_split[ev_id] = "derived_ds03_val"
            else:
                event_to_split[ev_id] = "derived_ds03_test"

        # Apply derived split to candidates
        for c in forest_fire_candidates:
            c["derived_event_split"] = event_to_split[c["fire_event_id"]]

        # For rejected candidates, assign NONE
        for r in rejected_candidates:
            r["derived_event_split"] = "NONE"

        # ---------------------------------------------------------------------
        # Save Artifacts to data/labeling/ds03/
        # ---------------------------------------------------------------------
        df_all_matches = pd.DataFrame(all_matches)
        df_all_matches.to_parquet(self.label_dir / "forest_firms_matches.parquet", index=False)
        with open(self.label_dir / "forest_firms_matches.json", "w", encoding="utf-8") as f:
            json.dump(all_matches, f, indent=2)

        df_candidates = pd.DataFrame(forest_fire_candidates)
        df_candidates.to_parquet(self.label_dir / "forest_fire_candidates.parquet", index=False)
        with open(self.label_dir / "forest_fire_candidates.json", "w", encoding="utf-8") as f:
            json.dump(forest_fire_candidates, f, indent=2)

        df_rejected = pd.DataFrame(rejected_candidates)
        df_rejected.to_parquet(self.label_dir / "forest_rejected_candidates.parquet", index=False)
        with open(self.label_dir / "forest_rejected_candidates.json", "w", encoding="utf-8") as f:
            json.dump(rejected_candidates, f, indent=2)

        # ---------------------------------------------------------------------
        # Compute Distributions & Statistical Audit
        # ---------------------------------------------------------------------
        det_per_event = df_candidates["fire_event_id"].value_counts().to_dict() if not df_candidates.empty else {}
        spatial_dists = [c["spatial_distance_km"] for c in forest_fire_candidates]
        temporal_offsets = [c["temporal_difference_hours"] for c in forest_fire_candidates]

        split_grouping: Dict[str, Any] = {}
        for sp in ["derived_ds03_train", "derived_ds03_val", "derived_ds03_test"]:
            evs = [k for k, v in event_to_split.items() if v == sp]
            dets = sum(det_per_event.get(e, 0) for e in evs)
            split_grouping[sp] = {
                "event_count": len(evs),
                "detection_count": dets,
                "event_ids": evs,
            }

        audit_summary: Dict[str, Any] = {
            "num_source_events": num_source_events,
            "num_india_events": num_india_events,
            "num_valid_geometry": num_valid_geometry,
            "num_valid_dates": num_valid_dates,
            "num_matched_to_firms": len(all_matches),
            "num_passing_forest_gate": num_passing_forest_gate,
            "num_diverted_to_agri": num_diverted_agri,
            "num_ambiguous": num_ambiguous,
            "num_excluded": num_excluded,
            "firms_detections_generated": len(forest_fire_candidates),
            "unique_fire_event_id_count": len(unique_events),
            "detections_per_event_distribution": {
                "counts_by_event": det_per_event,
                "min": int(min(det_per_event.values())) if det_per_event else 0,
                "max": int(max(det_per_event.values())) if det_per_event else 0,
                "mean": round(float(np.mean(list(det_per_event.values()))), 2) if det_per_event else 0.0,
                "median": round(float(np.median(list(det_per_event.values()))), 2) if det_per_event else 0.0,
            },
            "spatial_distance_distribution_km": {
                "min": round(float(min(spatial_dists)), 4) if spatial_dists else 0.0,
                "max": round(float(max(spatial_dists)), 4) if spatial_dists else 0.0,
                "mean": round(float(np.mean(spatial_dists)), 4) if spatial_dists else 0.0,
                "median": round(float(np.median(spatial_dists)), 4) if spatial_dists else 0.0,
            },
            "temporal_offset_distribution_hours": {
                "min": round(float(min(temporal_offsets)), 4) if temporal_offsets else 0.0,
                "max": round(float(max(temporal_offsets)), 4) if temporal_offsets else 0.0,
                "mean": round(float(np.mean(temporal_offsets)), 4) if temporal_offsets else 0.0,
            },
            "train_val_test_event_grouping": split_grouping,
            "licensing_limitations": {
                "GLOBAL_FIRE_ATLAS": "Creative Commons Attribution 4.0 International (CC-BY-4.0). Andela et al. 2019 / Zenodo DOI: 10.5281/zenodo.17669692.",
                "FSI_VAN_AGNI": "Forest Survey of India, Ministry of Environment, Forest and Climate Change, Government of India. Open Access / Departmental Research Use.",
                "MODIS_MCD64A1": "NASA LP DAAC / EOSDIS Open Data Policy. Giglio et al. 2018.",
            },
        }

        # Save audit json
        with open(self.label_dir / "ds03_audit.json", "w", encoding="utf-8") as f:
            json.dump(audit_summary, f, indent=2)

        return audit_summary


def run_ds03_pipeline(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Convenience runner for DS_03."""
    pipeline = DS03Pipeline(project_root)
    pipeline.build_and_save_reference_dataset()
    summary = pipeline.match_and_audit()
    return summary


if __name__ == "__main__":
    summary = run_ds03_pipeline()
    print("DS_03 Pipeline Summary:")
    print(json.dumps(summary, indent=2))
