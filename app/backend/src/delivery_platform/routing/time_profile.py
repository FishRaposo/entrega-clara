"""Deterministic time-of-day speed profile for time-dependent routing.

The profile multiplies free-flow speed per hour of the local day. It is
**synthetic and deterministic** — a lunch-and-rush-hour shape, not measured
traffic — and it is committed as data (``data/graph/traffic-profile.json``) so a
reader can see exactly what the demo assumes.

Two correctness rules matter here:

* **FIFO.** Departing later must never arrive earlier. Travel time on an edge is
  ``distance / (speed · m(t))`` with ``m`` linearly interpolated between hourly
  buckets, so the arrival function is ``t + T·m(t)`` and its derivative is
  ``1 + T·m'(t)``. The profile is rejected at load time when
  ``max_edge_seconds · |m'| > 1`` for any decreasing segment, which is what keeps
  the time-dependent Dijkstra valid.
* **Bands, not classes.** The committed graph stores an edge's free-flow speed,
  not its OSM highway class, so the profile groups roads by free-flow speed. A
  reader who wants class-accurate profiles needs the class in the graph schema
  first; that trade-off is recorded in ADR 0010.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from delivery_platform.routing.graph import GraphEdge

HOURS_PER_DAY = 24
SECONDS_PER_HOUR = 3600.0
DEFAULT_MAX_EDGE_SECONDS = 900.0


class TrafficProfileError(ValueError):
    """The profile is malformed or breaks the FIFO property."""


@dataclass(frozen=True)
class SpeedBand:
    band_id: str
    up_to_kmh: float
    hourly: tuple[float, ...]

    def multiplier(self, hour: float) -> float:
        """Linear interpolation between hourly buckets, wrapping at midnight."""
        position = hour % HOURS_PER_DAY
        low = int(position)
        high = (low + 1) % HOURS_PER_DAY
        weight = position - low
        return self.hourly[low] * (1.0 - weight) + self.hourly[high] * weight

    def slope_per_second(self) -> float:
        """Largest magnitude of change per second between consecutive buckets."""
        worst = 0.0
        for low in range(HOURS_PER_DAY):
            high = (low + 1) % HOURS_PER_DAY
            worst = max(worst, abs(self.hourly[high] - self.hourly[low]) / SECONDS_PER_HOUR)
        return worst


@dataclass(frozen=True)
class TravelTimeProfile:
    profile_id: str
    version: str
    source: str
    tz_offset_hours: float
    bands: tuple[SpeedBand, ...]

    def band_for(self, speed_kmh: float) -> SpeedBand:
        for band in self.bands:
            if speed_kmh <= band.up_to_kmh:
                return band
        return self.bands[-1]

    def local_hour(self, epoch_seconds: float) -> float:
        shifted = epoch_seconds + self.tz_offset_hours * SECONDS_PER_HOUR
        return (shifted / SECONDS_PER_HOUR) % HOURS_PER_DAY

    def multiplier(self, speed_kmh: float, epoch_seconds: float) -> float:
        return self.band_for(speed_kmh).multiplier(self.local_hour(epoch_seconds))

    def edge_seconds(self, edge: GraphEdge, departure: float) -> float:
        speed = edge.speed_kmh / self.multiplier(edge.speed_kmh, departure)
        return edge.distance_meters / (speed * 1000 / 3600)

    @property
    def fastest_speed_factor(self) -> float:
        """Smallest multiplier seen anywhere: the fastest the network can be."""
        return min(min(band.hourly) for band in self.bands)

    def validate_fifo(self, max_edge_seconds: float = DEFAULT_MAX_EDGE_SECONDS) -> None:
        """Reject a profile where departing later could arrive earlier."""
        for band in self.bands:
            slack = max_edge_seconds * band.slope_per_second()
            if slack > 1.0:
                raise TrafficProfileError(
                    f"band {band.band_id} violates FIFO: a {max_edge_seconds:.0f}s edge "
                    f"could gain {slack:.2f}s per departing second"
                )
        if self.fastest_speed_factor <= 0:
            raise TrafficProfileError("speed multipliers must be positive")


def _band(document: dict[str, Any], position: int) -> SpeedBand:
    band_id = document.get("id")
    up_to = document.get("up_to_kmh")
    hourly = document.get("hourly")
    if not isinstance(band_id, str) or not band_id:
        raise TrafficProfileError(f"band {position} requires an id")
    if not isinstance(up_to, int | float) or up_to <= 0:
        raise TrafficProfileError(f"band {band_id} requires a positive up_to_kmh")
    if not isinstance(hourly, list) or len(hourly) != HOURS_PER_DAY:
        raise TrafficProfileError(f"band {band_id} requires exactly {HOURS_PER_DAY} hourly values")
    values: list[float] = []
    for value in hourly:
        if not isinstance(value, int | float) or not 0.2 <= float(value) <= 5.0:
            raise TrafficProfileError(
                f"band {band_id} has a multiplier outside [0.2, 5.0]: {value!r}"
            )
        values.append(float(value))
    return SpeedBand(band_id=band_id, up_to_kmh=float(up_to), hourly=tuple(values))


def parse_profile(document: dict[str, Any]) -> TravelTimeProfile:
    if not isinstance(document, dict):
        raise TrafficProfileError("profile must be a JSON object")
    profile_id = document.get("profile_id")
    version = document.get("version")
    bands = document.get("bands")
    if not isinstance(profile_id, str) or not profile_id:
        raise TrafficProfileError("profile requires a profile_id")
    if not isinstance(version, str) or not version:
        raise TrafficProfileError("profile requires a version")
    if not isinstance(bands, list) or not bands:
        raise TrafficProfileError("profile requires at least one speed band")
    parsed = tuple(_band(band, position) for position, band in enumerate(bands))
    ordered = tuple(sorted(parsed, key=lambda band: band.up_to_kmh))
    offset = document.get("timezone_offset_hours", 0.0)
    if not isinstance(offset, int | float) or not -12 <= float(offset) <= 14:
        raise TrafficProfileError("timezone_offset_hours must be between -12 and 14")
    profile = TravelTimeProfile(
        profile_id=profile_id,
        version=version,
        source=str(document.get("source", "")),
        tz_offset_hours=float(offset),
        bands=ordered,
    )
    profile.validate_fifo()
    return profile


def load_profile(path: str | Path) -> TravelTimeProfile:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_profile(document)
