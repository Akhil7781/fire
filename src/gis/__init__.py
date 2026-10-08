"""Stage 8.42 GIS Package.

Provides Geoapify Places API queries, geodesic distance calculations, and proximity caching.
"""

from src.gis.geoapify_places import GeoapifyPlacesClient
from src.gis.proximity import ProximityEngine, compute_geodesic_distance_m
from src.gis.cache import GisProximityCache

__all__ = [
    "GeoapifyPlacesClient",
    "ProximityEngine",
    "GisProximityCache",
    "compute_geodesic_distance_m"
]
