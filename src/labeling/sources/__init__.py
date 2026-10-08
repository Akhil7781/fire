"""
Package initializing all reference evidence source adapters.
Includes statutory industrial disclosures, FSI Van Agni LFF, MODIS MCD64A1 burned area,
Global Fire Atlas perimeters, ICAR-IARI agricultural context, Sentinel-2 dNBR pilot scars,
and stationary thermal infrastructure catalogs.
"""

from src.labeling.sources.agriculture import AgriculturalFireAdapter
from src.labeling.sources.base import BaseEvidenceAdapter
from src.labeling.sources.forest import ForestFireAdapter
from src.labeling.sources.global_fire_atlas import GlobalFireAtlasAdapter
from src.labeling.sources.industrial import IndustrialFireAdapter
from src.labeling.sources.mcd64a1 import MCD64A1Adapter
from src.labeling.sources.other_thermal import OtherThermalSourceAdapter
from src.labeling.sources.sentinel2_burn_scar import Sentinel2AgriculturalPilotAdapter

__all__ = [
    "BaseEvidenceAdapter",
    "IndustrialFireAdapter",
    "ForestFireAdapter",
    "MCD64A1Adapter",
    "GlobalFireAtlasAdapter",
    "AgriculturalFireAdapter",
    "Sentinel2AgriculturalPilotAdapter",
    "OtherThermalSourceAdapter",
]
