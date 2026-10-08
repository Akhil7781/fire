"""Stage 8.42 Geoapify Places API Client.

Queries nearest schools, hospitals, villages, and infrastructure POIs
using Geoapify Places API v2 with proximity bias.
"""

import logging
import os
from typing import Dict, Any, Optional, Tuple
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GEOAPIFY_PLACES_URL = "https://api.geoapify.com/v2/places"

class GeoapifyPlacesClient:
    """Client for Geoapify Places API v2 with proximity ordering."""

    def __init__(self, api_key: Optional[str] = None, timeout_seconds: float = 6.0):
        self.api_key = api_key if api_key is not None else os.getenv("GEOAPIFY_API_KEY", "")
        self.timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        """Returns True if an API key is available."""
        return bool(self.api_key and len(self.api_key.strip()) > 0)

    def query_nearest(
        self,
        lat: float,
        lon: float,
        category: str,
        limit: int = 1
    ) -> Optional[Dict[str, Any]]:
        """Queries nearest POI in a given category using proximity bias.

        Args:
            lat: Query latitude.
            lon: Query longitude.
            category: Geoapify category (e.g. 'education.school', 'healthcare.hospital').
            limit: Maximum items (default 1).

        Returns:
            Dict with POI details, or None if no result or unavailable.
        """
        if not self.is_configured:
            logger.warning("GEOAPIFY_API_KEY not configured. Places lookup unavailable.")
            return None

        params = {
            "categories": category,
            "bias": f"proximity:{lon:.5f},{lat:.5f}",
            "limit": limit,
            "apiKey": self.api_key.strip()
        }

        try:
            resp = requests.get(GEOAPIFY_PLACES_URL, params=params, timeout=self.timeout_seconds)
            if resp.status_code == 401:
                logger.error("Geoapify API key is invalid or unauthorized.")
                return None
            if resp.status_code != 200:
                logger.warning(f"Geoapify Places API error {resp.status_code}: {resp.text[:150]}")
                return None

            data = resp.json()
            features = data.get("features", [])
            if not features:
                return None

            feat = features[0]
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", [])

            poi_lon = coords[0] if len(coords) >= 2 else props.get("lon")
            poi_lat = coords[1] if len(coords) >= 2 else props.get("lat")
            name = props.get("name") or props.get("address_line1") or props.get("formatted") or f"{category.split('.')[-1].capitalize()}"
            provider_dist = props.get("distance")
            place_id = props.get("place_id") or props.get("osm_id")

            return {
                "name": str(name).strip(),
                "lat": float(poi_lat) if poi_lat is not None else None,
                "lon": float(poi_lon) if poi_lon is not None else None,
                "provider_distance_m": float(provider_dist) if provider_dist is not None else None,
                "place_id": str(place_id) if place_id else None,
                "category": category,
                "raw_properties": props
            }

        except requests.exceptions.Timeout:
            logger.warning(f"Geoapify Places API timeout after {self.timeout_seconds}s for {category}.")
            return None
        except Exception as e:
            logger.warning(f"Geoapify Places API query error: {str(e)}")
            return None

    def query_nearest_village(
        self,
        lat: float,
        lon: float
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """Queries nearest village, falling back to hamlet if no village is found.

        Returns:
            (poi_dict, match_type): match_type in ('village', 'hamlet', 'NOT_FOUND').
        """
        # 1. Primary query: populated_place.village
        res = self.query_nearest(lat, lon, category="populated_place.village")
        if res:
            res["match_type"] = "village"
            return res, "village"

        # 2. Fallback query: populated_place.hamlet
        res_hamlet = self.query_nearest(lat, lon, category="populated_place.hamlet")
        if res_hamlet:
            res_hamlet["match_type"] = "hamlet"
            return res_hamlet, "hamlet"

        return None, "NOT_FOUND"
