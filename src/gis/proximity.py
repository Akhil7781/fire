"""Stage 8.42 Unified GIS Proximity Engine.

Calculates geodesic distance to the nearest:
1. Industrial Facility (authoritative local database + Geoapify fallback)
2. School (Geoapify education.school)
3. Hospital (Geoapify healthcare.hospital)
4. Village / Populated Place (Geoapify populated_place.village -> hamlet)

Uses pyproj.Geod(WGS84) for rigorous geodesic distance computation.
"""

from datetime import datetime, timezone
import logging
import math
from typing import Dict, Any, Optional, Tuple, List
import pyproj

from src.gis.cache import GisProximityCache
from src.gis.geoapify_places import GeoapifyPlacesClient
from src.stage8_37.inference.feature_builder import get_industrial_facilities

logger = logging.getLogger(__name__)

# Initialize WGS84 Geoid
_GEOD = pyproj.Geod(ellps="WGS84")

def compute_geodesic_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes exact WGS84 ellipsoidal geodesic distance in meters."""
    try:
        _, _, dist_m = _GEOD.inv(lon1, lat1, lon2, lat2)
        return float(abs(dist_m))
    except Exception as e:
        logger.warning(f"Geodesic distance calculation fallback for ({lat1},{lon1})-({lat2},{lon2}): {e}")
        # Haversine fallback if pyproj encounters bad floating point values
        r = 6371000.0
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a = math.sin(dp / 2.0)**2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0)**2
        return float(r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)))

# Alias for external interfaces and tests
geodesic_distance_wgs84 = compute_geodesic_distance_m

class ProximityEngine:
    """Unified engine for multi-target GIS infrastructure and settlement proximity."""

    def __init__(
        self,
        geoapify_client: Optional[GeoapifyPlacesClient] = None,
        cache: Optional[GisProximityCache] = None
    ):
        self.geoapify = geoapify_client or GeoapifyPlacesClient()
        self.cache = cache or GisProximityCache()
        self._facilities = get_industrial_facilities()

    def get_nearest_industrial_facility(self, lat: float, lon: float) -> Dict[str, Any]:
        """Finds nearest industrial facility using local authoritative database."""
        if not self._facilities:
            # Fallback to Geoapify if local facility db is empty
            if self.geoapify.is_configured:
                res = self.geoapify.query_nearest(lat, lon, "production")
                if res and res.get("lat") and res.get("lon"):
                    dist_m = compute_geodesic_distance_m(lat, lon, res["lat"], res["lon"])
                    return {
                        "name": res["name"],
                        "lat": res["lat"],
                        "lon": res["lon"],
                        "distance_m": round(dist_m, 1),
                        "distance_km": round(dist_m / 1000.0, 3),
                        "source": "Geoapify Fallback"
                    }
            return {
                "name": None,
                "lat": None,
                "lon": None,
                "distance_m": None,
                "distance_km": None,
                "source": "UNAVAILABLE"
            }

        # Calculate exact geodesic distance to all registered facilities
        best_fac = None
        min_dist_m = float("inf")

        for fac in self._facilities:
            f_lat = fac.get("latitude")
            f_lon = fac.get("longitude")
            if f_lat is None or f_lon is None:
                continue

            dist_m = compute_geodesic_distance_m(lat, lon, f_lat, f_lon)
            if dist_m < min_dist_m:
                min_dist_m = dist_m
                best_fac = fac

        if best_fac:
            return {
                "name": best_fac.get("facility_name") or best_fac.get("name") or "Industrial Facility",
                "lat": best_fac.get("latitude"),
                "lon": best_fac.get("longitude"),
                "distance_m": round(min_dist_m, 1),
                "distance_km": round(min_dist_m / 1000.0, 3),
                "source": "Local Facility Database"
            }

        return {
            "name": None,
            "lat": None,
            "lon": None,
            "distance_m": None,
            "distance_km": None,
            "source": "NOT_FOUND"
        }

    def get_nearest_school(self, lat: float, lon: float) -> Dict[str, Any]:
        """Finds nearest school using Geoapify with cache."""
        category = "education.school"
        cached = self.cache.get(lat, lon, category)
        if cached and cached.get("lat") is not None and cached.get("lon") is not None:
            dist_m = cached.get("computed_distance_m")
            if dist_m is None:
                dist_m = compute_geodesic_distance_m(lat, lon, cached["lat"], cached["lon"])
            return {
                "name": cached.get("name") or "School",
                "lat": cached["lat"],
                "lon": cached["lon"],
                "distance_m": round(dist_m, 1),
                "distance_km": round(dist_m / 1000.0, 3),
                "place_id": cached.get("place_id"),
                "status": "CACHED"
            }

        if not self.geoapify.is_configured:
            return {
                "name": None, "lat": None, "lon": None,
                "distance_m": None, "distance_km": None,
                "place_id": None, "status": "UNAVAILABLE"
            }

        res = self.geoapify.query_nearest(lat, lon, category)
        if res and res.get("lat") is not None and res.get("lon") is not None:
            comp_m = compute_geodesic_distance_m(lat, lon, res["lat"], res["lon"])
            self.cache.set(
                lat=lat, lon=lon, category=category,
                name=res["name"], poi_lat=res["lat"], poi_lon=res["lon"],
                provider_distance_m=res.get("provider_distance_m"),
                computed_distance_m=comp_m,
                place_id=res.get("place_id"),
                status="SUCCESS",
                payload=res
            )
            return {
                "name": res["name"],
                "lat": res["lat"],
                "lon": res["lon"],
                "distance_m": round(comp_m, 1),
                "distance_km": round(comp_m / 1000.0, 3),
                "place_id": res.get("place_id"),
                "status": "SUCCESS"
            }

        return {
            "name": None, "lat": None, "lon": None,
            "distance_m": None, "distance_km": None,
            "place_id": None, "status": "NOT_FOUND"
        }

    def get_nearest_hospital(self, lat: float, lon: float) -> Dict[str, Any]:
        """Finds nearest hospital using Geoapify with cache."""
        category = "healthcare.hospital"
        cached = self.cache.get(lat, lon, category)
        if cached and cached.get("lat") is not None and cached.get("lon") is not None:
            dist_m = cached.get("computed_distance_m")
            if dist_m is None:
                dist_m = compute_geodesic_distance_m(lat, lon, cached["lat"], cached["lon"])
            return {
                "name": cached.get("name") or "Hospital",
                "lat": cached["lat"],
                "lon": cached["lon"],
                "distance_m": round(dist_m, 1),
                "distance_km": round(dist_m / 1000.0, 3),
                "place_id": cached.get("place_id"),
                "status": "CACHED"
            }

        if not self.geoapify.is_configured:
            return {
                "name": None, "lat": None, "lon": None,
                "distance_m": None, "distance_km": None,
                "place_id": None, "status": "UNAVAILABLE"
            }

        res = self.geoapify.query_nearest(lat, lon, category)
        if res and res.get("lat") is not None and res.get("lon") is not None:
            comp_m = compute_geodesic_distance_m(lat, lon, res["lat"], res["lon"])
            self.cache.set(
                lat=lat, lon=lon, category=category,
                name=res["name"], poi_lat=res["lat"], poi_lon=res["lon"],
                provider_distance_m=res.get("provider_distance_m"),
                computed_distance_m=comp_m,
                place_id=res.get("place_id"),
                status="SUCCESS",
                payload=res
            )
            return {
                "name": res["name"],
                "lat": res["lat"],
                "lon": res["lon"],
                "distance_m": round(comp_m, 1),
                "distance_km": round(comp_m / 1000.0, 3),
                "place_id": res.get("place_id"),
                "status": "SUCCESS"
            }

        return {
            "name": None, "lat": None, "lon": None,
            "distance_m": None, "distance_km": None,
            "place_id": None, "status": "NOT_FOUND"
        }

    def get_nearest_village(self, lat: float, lon: float) -> Dict[str, Any]:
        """Finds nearest village or hamlet using Geoapify with cache."""
        category = "populated_place.village"
        cached = self.cache.get(lat, lon, category)
        if cached and cached.get("lat") is not None and cached.get("lon") is not None:
            dist_m = cached.get("computed_distance_m")
            if dist_m is None:
                dist_m = compute_geodesic_distance_m(lat, lon, cached["lat"], cached["lon"])
            return {
                "name": cached.get("name") or "Village",
                "lat": cached["lat"],
                "lon": cached["lon"],
                "distance_m": round(dist_m, 1),
                "distance_km": round(dist_m / 1000.0, 3),
                "place_id": cached.get("place_id"),
                "match_type": cached.get("match_type") or "village",
                "status": "CACHED"
            }

        if not self.geoapify.is_configured:
            return {
                "name": None, "lat": None, "lon": None,
                "distance_m": None, "distance_km": None,
                "place_id": None, "match_type": None, "status": "UNAVAILABLE"
            }

        res, match_type = self.geoapify.query_nearest_village(lat, lon)
        if res and res.get("lat") is not None and res.get("lon") is not None:
            comp_m = compute_geodesic_distance_m(lat, lon, res["lat"], res["lon"])
            self.cache.set(
                lat=lat, lon=lon, category=category,
                name=res["name"], poi_lat=res["lat"], poi_lon=res["lon"],
                provider_distance_m=res.get("provider_distance_m"),
                computed_distance_m=comp_m,
                place_id=res.get("place_id"),
                match_type=match_type,
                status="SUCCESS",
                payload=res
            )
            return {
                "name": res["name"],
                "lat": res["lat"],
                "lon": res["lon"],
                "distance_m": round(comp_m, 1),
                "distance_km": round(comp_m / 1000.0, 3),
                "place_id": res.get("place_id"),
                "match_type": match_type,
                "status": "SUCCESS"
            }

        return {
            "name": None, "lat": None, "lon": None,
            "distance_m": None, "distance_km": None,
            "place_id": None, "match_type": match_type, "status": "NOT_FOUND"
        }

    def compute_event_proximity(self, lat: float, lon: float) -> Dict[str, Any]:
        """Computes all 4 nearest infrastructure/settlement distances for an event.

        Returns complete dictionary matching Stage 8.42 operational proximity schema.
        """
        now_utc = datetime.now(timezone.utc).isoformat()

        # 1. Industrial
        ind = self.get_nearest_industrial_facility(lat, lon)

        # 2. School
        sch = self.get_nearest_school(lat, lon)

        # 3. Hospital
        hos = self.get_nearest_hospital(lat, lon)

        # 4. Village
        vil = self.get_nearest_village(lat, lon)

        # Overall proximity status
        statuses = [sch["status"], hos["status"], vil["status"]]
        if all(s in ("SUCCESS", "CACHED") for s in statuses):
            prox_status = "SUCCESS"
        elif any(s in ("SUCCESS", "CACHED") for s in statuses) or ind.get("distance_km") is not None:
            prox_status = "PARTIAL"
        elif all(s == "UNAVAILABLE" for s in statuses):
            prox_status = "UNAVAILABLE"
        else:
            prox_status = "PARTIAL"

        return {
            # Industrial
            "nearest_industry_name": ind.get("name"),
            "nearest_industry_lat": ind.get("lat"),
            "nearest_industry_lon": ind.get("lon"),
            "distance_to_industry_m": ind.get("distance_m"),
            "distance_to_industry_km": ind.get("distance_km"),

            # School
            "nearest_school_name": sch.get("name"),
            "nearest_school_lat": sch.get("lat"),
            "nearest_school_lon": sch.get("lon"),
            "distance_to_school_m": sch.get("distance_m"),
            "distance_to_school_km": sch.get("distance_km"),
            "school_place_id": sch.get("place_id"),

            # Hospital
            "nearest_hospital_name": hos.get("name"),
            "nearest_hospital_lat": hos.get("lat"),
            "nearest_hospital_lon": hos.get("lon"),
            "distance_to_hospital_m": hos.get("distance_m"),
            "distance_to_hospital_km": hos.get("distance_km"),
            "hospital_place_id": hos.get("place_id"),

            # Village
            "nearest_village_name": vil.get("name"),
            "nearest_village_lat": vil.get("lat"),
            "nearest_village_lon": vil.get("lon"),
            "distance_to_village_m": vil.get("distance_m"),
            "distance_to_village_km": vil.get("distance_km"),
            "village_place_id": vil.get("place_id"),
            "village_match_type": vil.get("match_type"),
            "village_status": vil.get("status"),

            # Metadata
            "proximity_provider": "Geoapify Places API + Local Industrial DB",
            "proximity_calculated_at": now_utc,
            "proximity_status": prox_status
        }
