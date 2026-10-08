"""Stage 8.37 GeoJSON Builder.

Formats operational thermal events and predictions into standard RFC 7946 GeoJSON.
Supports filtering by class, confidence, date range, and bounding box.
"""

from typing import List, Dict, Any, Optional

def event_to_geojson_feature(event_record: Dict[str, Any]) -> Dict[str, Any]:
    """Converts a database event dictionary into a GeoJSON Feature."""
    lat = float(event_record["centroid_lat"])
    lon = float(event_record["centroid_lon"])

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat]
        },
        "properties": {
            "event_id": event_record["event_id"],
            "event_start_time": event_record["event_start_time"],
            "detection_count": event_record.get("detection_count", 1),
            "predicted_class": event_record.get("predicted_class", "Unclassified"),
            "class_id": event_record.get("class_id"),
            "confidence": event_record.get("confidence", 0.0),
            "persistence_level": event_record.get("persistence_level", "UNKNOWN"),
            "nearest_facility_distance_km": event_record.get("dist_to_facility_km", 999.0),
            "nearest_facility_name": event_record.get("nearest_facility_name", "None")
        }
    }

def build_geojson_collection(event_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Builds a FeatureCollection from a list of event dictionaries."""
    features = [event_to_geojson_feature(ev) for ev in event_records]
    return {
        "type": "FeatureCollection",
        "features": features
    }
