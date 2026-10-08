"""
Spatiotemporal matching engine between FIRMS thermal detections and independent reference evidence.
Computes exact geodesic distances and temporal interval differences.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from src.labeling.config import LabelConfig
from src.labeling.schemas import (
    ConfidenceTier,
    EvidenceCategory,
    EvidenceMatch,
    LocationPrecision,
    NormalizedEvidence,
    OfficialnessLevel,
    SourceType,
    TargetClass,
)

EARTH_RADIUS_KM = 6371.0


def geodesic_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes exact great-circle distance between two coordinates in kilometers using Haversine formula.
    """
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
) -> float:
    """
    Computes temporal difference in hours between a detection timestamp and an evidence event interval.
    If the detection falls within [start_time, end_time], returns 0.0.
    Otherwise returns distance to the closest interval boundary.
    """
    if start_time <= det_time <= end_time:
        return 0.0
    elif det_time < start_time:
        diff_sec = (start_time - det_time).total_seconds()
        return diff_sec / 3600.0
    else:
        diff_sec = (det_time - end_time).total_seconds()
        return diff_sec / 3600.0


def get_source_tolerances(
    evidence: NormalizedEvidence,
    config: LabelConfig,
) -> Tuple[float, float]:
    """
    Retrieves the parameterized spatial tolerance (km) and temporal tolerance (hours)
    for a given evidence record based on its source type and target class.
    """
    cls = evidence.class_candidate

    if cls == TargetClass.INDUSTRIAL_FIRE:
        if evidence.location_precision == LocationPrecision.EXACT_POINT:
            s_tol = config.spatial_tol_industrial_exact
        else:
            s_tol = config.spatial_tol_industrial_polygon

        if evidence.source_type == SourceType.STATUTORY_DISCLOSURE:
            t_tol = config.temporal_tol_sebi_disclosure
        elif evidence.source_type == SourceType.REGULATORY_ORDER:
            t_tol = config.temporal_tol_spcb_order
        else:
            t_tol = config.temporal_tol_news_incident

    elif cls == TargetClass.FOREST_FIRE:
        s_tol = config.spatial_tol_forest_cluster
        if evidence.source_type == SourceType.SATELLITE_BURN_PRODUCT:
            t_tol = config.temporal_tol_mcd64a1
        else:
            t_tol = config.temporal_tol_fsi_alert

    elif cls == TargetClass.AGRICULTURAL_FIRE:
        if evidence.source_type == SourceType.OPTICAL_VERIFICATION:
            s_tol = 0.5  # 500m parcel precision per specification
            t_tol = 48.0
        else:
            s_tol = config.spatial_tol_agri_field
            t_tol = config.temporal_tol_iari_bulletin

    elif cls == TargetClass.OTHER_THERMAL_SOURCE:
        rec_id = ((evidence.source_record_id or "") + "_" + evidence.evidence_id).upper()
        if "VOLCANO" in rec_id:
            s_tol = config.spatial_tol_volcano
            t_tol = config.temporal_tol_static_infra
        elif "FLARE" in rec_id:
            s_tol = config.spatial_tol_flaring_stack
            t_tol = config.temporal_tol_static_infra
        elif "KILN" in rec_id:
            s_tol = config.spatial_tol_brick_kiln
            t_tol = config.temporal_tol_static_infra
        elif "COAL" in rec_id:
            s_tol = config.spatial_tol_coal_fire
            t_tol = config.temporal_tol_static_infra
        else:
            s_tol = config.spatial_tol_power_plant
            t_tol = config.temporal_tol_static_infra
    else:
        s_tol = 0.5
        t_tol = 24.0

    return s_tol, t_tol


def match_evidence_to_firms(
    firms_df: pd.DataFrame,
    evidence_records: List[NormalizedEvidence],
    config: LabelConfig,
) -> List[EvidenceMatch]:
    """
    Performs high-performance geodesic and temporal interval matching between
    FIRMS detections and normalized independent reference evidence.
    """
    if firms_df.empty or not evidence_records:
        return []

    # Build 3D Cartesian KD-Tree for FIRMS detections
    # Converts (lat, lon) in degrees to 3D unit coordinates on Earth sphere
    firms_lats = np.radians(firms_df["latitude"].to_numpy())
    firms_lons = np.radians(firms_df["longitude"].to_numpy())
    xs = np.cos(firms_lats) * np.cos(firms_lons)
    ys = np.cos(firms_lats) * np.sin(firms_lons)
    zs = np.sin(firms_lats)
    coords_3d = np.column_stack([xs, ys, zs])
    kdtree = cKDTree(coords_3d)

    # Extract timestamps and detection IDs
    det_ids = firms_df["detection_id"].to_numpy()
    # Ensure UTC datetime series
    if pd.api.types.is_datetime64_any_dtype(firms_df["acq_datetime_utc"]):
        det_times = firms_df["acq_datetime_utc"].dt.to_pydatetime()
    else:
        det_times = pd.to_datetime(firms_df["acq_datetime_utc"], utc=True).dt.to_pydatetime()

    raw_lats = firms_df["latitude"].to_numpy()
    raw_lons = firms_df["longitude"].to_numpy()

    matches: List[EvidenceMatch] = []

    for evi in evidence_records:
        s_tol_km, t_tol_hours = get_source_tolerances(evi, config)

        # 3D Euclidean chord distance corresponding to spherical arc distance s_tol_km:
        # chord_dist = 2 * sin(arc_dist / (2 * R))
        angular_dist = s_tol_km / EARTH_RADIUS_KM
        chord_dist = 2.0 * math.sin(angular_dist / 2.0)

        # Evidence coordinate in 3D
        e_lat_rad = math.radians(evi.latitude)
        e_lon_rad = math.radians(evi.longitude)
        ex = math.cos(e_lat_rad) * math.cos(e_lon_rad)
        ey = math.cos(e_lat_rad) * math.sin(e_lon_rad)
        ez = math.sin(e_lat_rad)

        candidate_indices = kdtree.query_ball_point([ex, ey, ez], r=chord_dist)

        for idx in candidate_indices:
            # 1. Exact geodesic distance check
            dist_km = geodesic_distance_km(
                raw_lats[idx], raw_lons[idx],
                evi.latitude, evi.longitude,
            )
            if dist_km > s_tol_km:
                continue

            # 2. Exact temporal interval check
            det_dt = det_times[idx]
            dt_hours = temporal_difference_hours(
                det_dt,
                evi.event_datetime_start,
                evi.event_datetime_end,
            )
            if dt_hours > t_tol_hours:
                continue

            # 3. Base confidence calculation
            if evi.evidence_category == EvidenceCategory.STATIC_SOURCE_EVIDENCE:
                # Static source inventories are NEVER Tier A
                tier = ConfidenceTier.TIER_B
                rec_id = ((evi.source_record_id or "") + "_" + evi.evidence_id).upper()
                if "VOLCANO" in rec_id:
                    base_conf = 0.80
                elif "FLARE" in rec_id:
                    base_conf = 0.75
                elif "COAL" in rec_id:
                    base_conf = 0.70
                elif "POWER" in rec_id:
                    base_conf = 0.70
                else:
                    base_conf = 0.70
            elif evi.evidence_category == EvidenceCategory.CONTEXT_ONLY:
                # Context only - administrative/regional bulletins without parcel-level proof
                tier = ConfidenceTier.TIER_C
                base_conf = 0.50
            elif evi.evidence_category == EvidenceCategory.REMOTE_SENSING_CORROBORATION:
                tier = ConfidenceTier.TIER_A
                base_conf = config.weight_optical_scar
            else:
                # EVENT_EVIDENCE: in absence of direct optical burn scar verification,
                # confirmed disaster reports remain Tier B (Probable Event)
                if evi.source_type == SourceType.OPTICAL_VERIFICATION:
                    tier = ConfidenceTier.TIER_A
                    base_conf = config.weight_optical_scar
                elif evi.officialness_level == OfficialnessLevel.STATUTORY_GOVERNMENT:
                    tier = ConfidenceTier.TIER_B
                    base_conf = 0.85
                elif evi.officialness_level == OfficialnessLevel.SCIENTIFIC_AGENCY:
                    tier = ConfidenceTier.TIER_B
                    base_conf = 0.80
                elif evi.source_type == SourceType.NEWS_EVENT:
                    tier = ConfidenceTier.TIER_B
                    base_conf = config.weight_news_corroborated
                else:
                    tier = ConfidenceTier.TIER_B
                    base_conf = config.weight_single_news

            match = EvidenceMatch(
                detection_id=str(det_ids[idx]),
                evidence_id=evi.evidence_id,
                source_name=evi.source_name,
                evidence_category=evi.evidence_category,
                candidate_class=evi.class_candidate,
                spatial_distance_km=dist_km,
                temporal_difference_hours=dt_hours,
                matching_method="GEODESIC_AND_TEMPORAL_INTERVAL",
                base_confidence=base_conf,
                evidence_tier=tier,
                evidence_ref=evi,
            )
            matches.append(match)

    return matches
