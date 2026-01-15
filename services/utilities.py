import numpy as np
import math
from config import DASHBOARDS


def get_page_note(path):
    """
    Look up the note for a given page path from DASHBOARDS config.
    Returns the note string if found, or None if no note is configured.
    """
    for section in DASHBOARDS.values():
        for item in section.get("items", {}).values():
            if item.get("path") == path:
                return item.get("note")
    return None

def calculate_center(coords):
    """Calculate geographic center properly across 180 meridian."""
    if not coords:
        return 0, 0

    x = 0
    y = 0
    z = 0

    for lat, lon in coords:
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        x += math.cos(lat_rad) * math.cos(lon_rad)
        y += math.cos(lat_rad) * math.sin(lon_rad)
        z += math.sin(lat_rad)

    total = len(coords)
    x /= total
    y /= total
    z /= total

    center_lon = math.atan2(y, x)
    hyp = math.sqrt(x * x + y * y)
    center_lat = math.atan2(z, hyp)

    return math.degrees(center_lat), math.degrees(center_lon)

def calculate_zoom(coords):
    """
    Estimate zoom level based on geographic spread of coordinates.
    """
    if not coords:
        return 5  # fallback default zoom

    lats = [lat for lat, _ in coords]
    lons = [lon if lon >= 0 else lon + 360 for _, lon in coords]  # wrap longitudes to 0–360

    lat_range = max(lats) - min(lats)
    lon_range = max(lons) - min(lons)

    spread = max(lat_range, lon_range)

    # Tune these thresholds as needed
    if spread < 0.05:
        return 12
    elif spread < 0.2:
        return 10
    elif spread < 1:
        return 8
    elif spread < 5:
        return 5
    elif spread < 20:
        return 3
    else:
        return 2  # very spread out
