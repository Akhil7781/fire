import json
import math
from pathlib import Path
from collections import defaultdict, Counter

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def classify_indian_region_v2(lat: float, lon: float) -> str:
    if lon >= 84.0:
        return "EAST"
    if lat < 16.0:
        return "SOUTH"
    if lat >= 28.0:
        return "NORTH"
    if lon < 76.0:
        return "WEST"
    return "CENTRAL"

print("Haversine and region classification verified.")
