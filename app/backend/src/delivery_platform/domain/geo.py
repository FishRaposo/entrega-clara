"""Geographic primitives shared by domain, routing, and adapters."""

from __future__ import annotations

import math

from delivery_platform.domain.entities import GeoPoint

_EARTH_RADIUS_M = 6_371_000.0


def haversine_m(a: GeoPoint, b: GeoPoint) -> float:
    """Great-circle distance in meters between two points."""
    lat1, lat2 = math.radians(a.latitude), math.radians(b.latitude)
    dlat = lat2 - lat1
    dlon = math.radians(b.longitude - a.longitude)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(h))
