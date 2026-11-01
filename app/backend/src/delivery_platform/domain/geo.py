"""Geographic primitives shared by domain, routing, and adapters."""

from __future__ import annotations

import itertools
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


def point_along_polyline(coords: list[list[float]], fraction: float) -> GeoPoint:
    """Interpolate a point along a ``[lon, lat]`` polyline at a distance fraction.

    Every returned point lies on a polyline segment (vertices at the ends).
    Fraction is clamped to [0, 1].
    """
    if not coords:
        raise ValueError("polyline needs at least one coordinate")
    if len(coords) == 1:
        lon, lat = coords[0]
        return GeoPoint(latitude=lat, longitude=lon)
    points = [GeoPoint(latitude=c[1], longitude=c[0]) for c in coords]
    total = sum(haversine_m(a, b) for a, b in itertools.pairwise(points))
    if total <= 0:
        return points[-1]
    target = max(0.0, min(1.0, fraction)) * total
    walked = 0.0
    for a, b in itertools.pairwise(points):
        leg = haversine_m(a, b)
        if walked + leg >= target:
            t = 0.0 if leg <= 0 else (target - walked) / leg
            return GeoPoint(
                latitude=a.latitude + (b.latitude - a.latitude) * t,
                longitude=a.longitude + (b.longitude - a.longitude) * t,
            )
        walked += leg
    return points[-1]
