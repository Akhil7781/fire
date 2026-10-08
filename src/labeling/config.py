"""
Configuration loader and validator for the label construction pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict
import yaml

# Project root resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class LabelConfig:
    project_root: Path = PROJECT_ROOT
    config_dict: Dict[str, Any] = field(default_factory=dict)

    # Paths
    frozen_features_path: Path = field(init=False)
    split_dir: Path = field(init=False)
    reference_dir: Path = field(init=False)
    candidates_dir: Path = field(init=False)
    matches_dir: Path = field(init=False)
    output_labels_dir: Path = field(init=False)
    audits_dir: Path = field(init=False)

    # Spatial tolerances (km)
    spatial_tol_industrial_exact: float = 0.250
    spatial_tol_industrial_polygon: float = 0.050
    spatial_tol_forest_cluster: float = 1.000
    spatial_tol_agri_field: float = 0.100
    spatial_tol_flaring_stack: float = 0.300
    spatial_tol_brick_kiln: float = 0.150
    spatial_tol_power_plant: float = 0.300
    spatial_tol_coal_fire: float = 1.000
    spatial_tol_volcano: float = 5.000

    # Temporal tolerances (hours)
    temporal_tol_sebi_disclosure: float = 48.0
    temporal_tol_spcb_order: float = 72.0
    temporal_tol_news_incident: float = 48.0
    temporal_tol_fsi_alert: float = 12.0
    temporal_tol_mcd64a1: float = 48.0
    temporal_tol_iari_bulletin: float = 24.0
    temporal_tol_sentinel2: float = 72.0
    temporal_tol_static_infra: float = 8760.0

    # Confidence weights
    weight_statutory: float = 1.00
    weight_optical_scar: float = 0.90
    weight_news_corroborated: float = 0.85
    weight_catalog_verified: float = 0.80
    weight_single_news: float = 0.60
    weight_spatial_context_only: float = 0.30

    def __post_init__(self) -> None:
        yaml_path = self.project_root / "configs" / "label_config.yaml"
        if yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                self.config_dict = yaml.safe_load(f) or {}

        paths_cfg = self.config_dict.get("paths", {})
        self.frozen_features_path = (self.project_root / paths_cfg.get("frozen_features", "data/interim/causal_features_2025.parquet")).resolve()
        self.split_dir = (self.project_root / paths_cfg.get("split_dir", "data/processed/splits")).resolve()
        self.reference_dir = (self.project_root / paths_cfg.get("reference_dir", "data/reference")).resolve()
        self.candidates_dir = (self.project_root / paths_cfg.get("candidates_dir", "data/labeling/candidates")).resolve()
        self.matches_dir = (self.project_root / paths_cfg.get("matches_dir", "data/labeling/matches")).resolve()
        self.output_labels_dir = (self.project_root / paths_cfg.get("output_labels_dir", "data/processed/labels")).resolve()
        self.audits_dir = (self.project_root / paths_cfg.get("audits_dir", "data/labeling/audits")).resolve()

        # Parse tolerances if present
        m_params = self.config_dict.get("matching_parameters", {})
        s_tols = m_params.get("spatial_tolerances_km", {})
        self.spatial_tol_industrial_exact = float(s_tols.get("industrial_exact_point", self.spatial_tol_industrial_exact))
        self.spatial_tol_industrial_polygon = float(s_tols.get("industrial_polygon_buffer", self.spatial_tol_industrial_polygon))
        self.spatial_tol_forest_cluster = float(s_tols.get("forest_cluster_radius", self.spatial_tol_forest_cluster))
        self.spatial_tol_agri_field = float(s_tols.get("agri_field_parcel", self.spatial_tol_agri_field))
        self.spatial_tol_flaring_stack = float(s_tols.get("flaring_stack", self.spatial_tol_flaring_stack))
        self.spatial_tol_brick_kiln = float(s_tols.get("brick_kiln", self.spatial_tol_brick_kiln))
        self.spatial_tol_power_plant = float(s_tols.get("power_plant_stack", self.spatial_tol_power_plant))
        self.spatial_tol_coal_fire = float(s_tols.get("coal_fire_colliery", self.spatial_tol_coal_fire))
        self.spatial_tol_volcano = float(s_tols.get("volcano_vent", self.spatial_tol_volcano))

        t_tols = m_params.get("temporal_tolerances_hours", {})
        self.temporal_tol_sebi_disclosure = float(t_tols.get("sebi_reg30_disclosure", self.temporal_tol_sebi_disclosure))
        self.temporal_tol_spcb_order = float(t_tols.get("spcb_regulatory_order", self.temporal_tol_spcb_order))
        self.temporal_tol_news_incident = float(t_tols.get("news_incident_report", self.temporal_tol_news_incident))
        self.temporal_tol_fsi_alert = float(t_tols.get("fsi_forest_fire_alert", self.temporal_tol_fsi_alert))
        self.temporal_tol_mcd64a1 = float(t_tols.get("mcd64a1_burned_date", self.temporal_tol_mcd64a1))
        self.temporal_tol_iari_bulletin = float(t_tols.get("iari_agri_fire_bulletin", self.temporal_tol_iari_bulletin))
        self.temporal_tol_sentinel2 = float(t_tols.get("sentinel2_optical_scar", self.temporal_tol_sentinel2))
        self.temporal_tol_static_infra = float(t_tols.get("static_infrastructure", self.temporal_tol_static_infra))

        weights = self.config_dict.get("confidence_weights", {})
        self.weight_statutory = float(weights.get("statutory_regulatory_order", self.weight_statutory))
        self.weight_optical_scar = float(weights.get("direct_optical_burn_scar", self.weight_optical_scar))
        self.weight_news_corroborated = float(weights.get("multi_source_news_incident", self.weight_news_corroborated))
        self.weight_catalog_verified = float(weights.get("scientific_catalog_verified", self.weight_catalog_verified))
        self.weight_single_news = float(weights.get("single_news_report", self.weight_single_news))
        self.weight_spatial_context_only = float(weights.get("spatial_mask_context_only", self.weight_spatial_context_only))


def get_label_config() -> LabelConfig:
    return LabelConfig()
