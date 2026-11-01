"""Traffic profile: interpolation, banding and the FIFO guarantee."""

import json
from pathlib import Path

import pytest
from delivery_platform.routing.graph import GraphEdge, load_graph
from delivery_platform.routing.time_profile import (
    HOURS_PER_DAY,
    TrafficProfileError,
    load_profile,
    parse_profile,
)

PROFILE_PATH = Path("data/graph/traffic-profile.json")
GRAPH_PATH = Path("data/graph/sao-paulo-centro-osm.json")


@pytest.fixture(scope="module")
def profile():
    return load_profile(PROFILE_PATH)


def test_committed_profile_loads_and_is_fifo_safe(profile):
    assert profile.profile_id == "sao-paulo-lunch-rush"
    assert profile.tz_offset_hours == -3
    assert len(profile.bands) == 3
    profile.validate_fifo(max_edge_seconds=900)


def test_committed_profile_fits_the_committed_graph(profile):
    """The FIFO bound must hold for the slowest edge actually in the graph."""
    graph = load_graph(GRAPH_PATH)
    slowest = max(edge.seconds for edges in graph.adjacency.values() for edge in edges)
    profile.validate_fifo(max_edge_seconds=slowest)


def test_multiplier_interpolates_between_hours(profile):
    band = profile.bands[1]
    hour_12 = band.hourly[12]
    hour_13 = band.hourly[13]
    assert band.multiplier(12.0) == pytest.approx(hour_12)
    assert band.multiplier(12.5) == pytest.approx((hour_12 + hour_13) / 2)
    assert band.multiplier(23.5) == pytest.approx((band.hourly[23] + band.hourly[0]) / 2)
    assert band.multiplier(36.0) == pytest.approx(band.multiplier(12.0))


def test_bands_are_chosen_by_free_flow_speed(profile):
    assert profile.band_for(20).band_id == "local"
    assert profile.band_for(25).band_id == "local"
    assert profile.band_for(40).band_id == "arterial"
    assert profile.band_for(90).band_id == "express"
    assert profile.band_for(999).band_id == "express"


def test_edge_seconds_scale_with_the_multiplier(profile):
    edge = GraphEdge(to_node="x", distance_meters=1000.0, speed_kmh=20.0)
    # 1 km at 20 km/h is 180 s at free flow.
    noon = 12 * 3600.0
    midnight = 2 * 3600.0
    noon_seconds = profile.edge_seconds(edge, noon)
    midnight_seconds = profile.edge_seconds(edge, midnight)
    assert midnight_seconds < 180.0 < noon_seconds


def test_arrival_function_is_non_decreasing_for_typical_edges(profile):
    """The property the solver relies on: leaving later never arrives earlier."""
    for length, speed in ((300.0, 20.0), (800.0, 40.0), (2000.0, 60.0)):
        edge = GraphEdge(to_node="x", distance_meters=length, speed_kmh=speed)
        previous = float("-inf")
        for minute in range(24 * 60):
            departure = minute * 60.0
            arrival = departure + profile.edge_seconds(edge, departure)
            assert arrival >= previous - 1e-9, (length, speed, minute)
            previous = arrival


def test_rejects_wrong_bucket_count():
    document = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    document["bands"][0]["hourly"] = document["bands"][0]["hourly"][:12]
    with pytest.raises(TrafficProfileError, match="24 hourly values"):
        parse_profile(document)


def test_rejects_out_of_range_multiplier():
    document = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    document["bands"][0]["hourly"][0] = 40.0
    with pytest.raises(TrafficProfileError, match="outside"):
        parse_profile(document)


def test_rejects_a_profile_that_breaks_fifo():
    hourly = [1.0] * HOURS_PER_DAY
    hourly[12] = 5.0
    hourly[13] = 0.2  # a 4.8 drop in one hour: 900s edges would gain 1.2s/s
    document = {
        "profile_id": "broken",
        "version": "1",
        "bands": [{"id": "all", "up_to_kmh": 130, "hourly": hourly}],
    }
    with pytest.raises(TrafficProfileError, match="violates FIFO"):
        parse_profile(document)
