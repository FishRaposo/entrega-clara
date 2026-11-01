"""Time-dependent planning through the product planner and the lab API."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from delivery_platform.api.main import create_app
from delivery_platform.application.ports import (
    BatchRouteRequest,
    BatchStopRequest,
    DeliveryRouteRequest,
)
from delivery_platform.domain.entities import GeoPoint
from delivery_platform.routing.graph import load_graph
from delivery_platform.routing.graph_planner import GraphRoutePlanner
from delivery_platform.routing.time_profile import load_profile
from fastapi.testclient import TestClient

GRAPH = load_graph(Path("data/graph/sao-paulo-centro-osm.json"))
PROFILE = load_profile(Path("data/graph/traffic-profile.json"))
NOON = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
HEADERS = {"x-demo-identity": "demo-operations"}

COURIER = GeoPoint(latitude=-23.5495, longitude=-46.6345)
RESTAURANT = GeoPoint(latitude=-23.5482, longitude=-46.6371)
CUSTOMER_A = GeoPoint(latitude=-23.5515, longitude=-46.632)
CUSTOMER_B = GeoPoint(latitude=-23.5477, longitude=-46.6389)


def _request(departure: datetime | None) -> DeliveryRouteRequest:
    return DeliveryRouteRequest(
        delivery_id="del-1",
        courier_location=COURIER,
        pickup_point=RESTAURANT,
        pickup_label="Cantina",
        dropoff_point=CUSTOMER_A,
        dropoff_label="Rua A, 100",
        departure_at=departure,
    )


def _batch(departure: datetime | None) -> BatchRouteRequest:
    return BatchRouteRequest(
        batch_id="bat-1",
        courier_location=COURIER,
        departure_at=departure,
        deliveries=(
            BatchStopRequest(
                delivery_id="del-1",
                pickup_point=RESTAURANT,
                pickup_label="Cantina",
                dropoff_point=CUSTOMER_A,
                dropoff_label="Rua A, 100",
            ),
            BatchStopRequest(
                delivery_id="del-2",
                pickup_point=GeoPoint(latitude=-23.5477, longitude=-46.6389),
                pickup_label="Padaria",
                dropoff_point=CUSTOMER_B,
                dropoff_label="Rua B, 200",
            ),
        ),
    )


def test_plan_prices_travel_with_the_profile_when_a_departure_is_given():
    planner = GraphRoutePlanner(GRAPH, PROFILE)
    timed = planner.plan(_request(NOON), route_id="rpl-1")
    static = GraphRoutePlanner(GRAPH).plan(_request(None), route_id="rpl-2")

    assert timed.solver_name == "td-astar"
    assert timed.traffic_profile_id == "sao-paulo-lunch-rush"
    assert timed.departure_at == NOON.replace(tzinfo=UTC) or timed.arrival_at is not None
    assert timed.arrival_at is not None and timed.departure_at is not None
    assert timed.arrival_at > timed.departure_at
    assert timed.estimated_seconds > static.estimated_seconds

    assert static.solver_name == "astar-haversine"
    assert static.traffic_profile_id is None
    assert static.departure_at is None
    assert static.arrival_at is None


def test_batch_plan_accumulates_arrivals_across_legs():
    planner = GraphRoutePlanner(GRAPH, PROFILE)
    plan = planner.plan_batch(_batch(NOON), route_id="rpl-3")

    assert plan.solver_name.endswith("+td-astar")
    assert plan.traffic_profile_id == "sao-paulo-lunch-rush"
    assert plan.departure_at is not None and plan.arrival_at is not None
    assert plan.arrival_at > plan.departure_at
    assert len(plan.stops) == 4
    # Legs accumulate: every segment starts after the previous one lands.
    elapsed = 0.0
    for segment in plan.segments:
        elapsed += segment.estimated_seconds
    assert plan.estimated_seconds == pytest.approx(elapsed)
    assert plan.baseline_cost is not None


def test_plan_without_a_profile_stays_static():
    planner = GraphRoutePlanner(GRAPH, None)
    plan = planner.plan(_request(NOON), route_id="rpl-4")
    assert plan.solver_name == "astar-haversine"
    assert plan.traffic_profile_id is None


def test_lab_traffic_returns_the_whole_day():
    client = TestClient(create_app())
    response = client.get(
        "/api/v1/lab/traffic?origin=n-00-00&destination=n-06-10&graph=synthetic",
        headers=HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == "sao-paulo-lunch-rush"
    assert len(body["points"]) == 24
    assert [point["hour"] for point in body["points"]] == list(range(24))
    assert body["peak_seconds"] > body["night_seconds"]
    assert body["static_seconds"] > 0
    assert body["peak_hour"] in range(24)


def test_lab_time_dependent_path_needs_a_departure_hour():
    client = TestClient(create_app())
    payload = {
        "origin": "n-00-00",
        "destination": "n-06-10",
        "solver": "td-astar",
        "objective": "time",
        "graph": "synthetic",
    }
    missing = client.post("/api/v1/lab/path", headers=HEADERS, json=payload)
    assert missing.status_code == 400

    payload["departure_hour"] = 12
    noon = client.post("/api/v1/lab/path", headers=HEADERS, json=payload)
    assert noon.status_code == 200
    noon_body = noon.json()
    assert noon_body["solver_name"] == "td-astar"
    assert noon_body["arrival_at"] > noon_body["departure_at"]

    payload["solver"] = "dijkstra"
    payload.pop("departure_hour")
    static = client.post("/api/v1/lab/path", headers=HEADERS, json=payload).json()
    assert noon_body["estimated_seconds"] > static["estimated_seconds"]
