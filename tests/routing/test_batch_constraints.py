"""Dispatch-level window and capacity constraints on batch planning."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from delivery_platform.application.ports import BatchRouteRequest, BatchStopRequest
from delivery_platform.domain.entities import GeoPoint
from delivery_platform.domain.errors import BatchInfeasibleError
from delivery_platform.routing.graph import load_graph
from delivery_platform.routing.graph_planner import GraphRoutePlanner
from delivery_platform.routing.time_profile import load_profile

GRAPH = load_graph(Path("data/graph/sao-paulo-centro-osm.json"))
PROFILE = load_profile(Path("data/graph/traffic-profile.json"))
DEPARTURE = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

COURIER = GeoPoint(latitude=-23.5495, longitude=-46.6345)
RESTAURANT = GeoPoint(latitude=-23.5482, longitude=-46.6371)
CUSTOMER_A = GeoPoint(latitude=-23.5515, longitude=-46.632)
CUSTOMER_B = GeoPoint(latitude=-23.5477, longitude=-46.6389)


def _batch(
    *,
    window_end_offset: timedelta = timedelta(minutes=45),
    capacity: int = 3,
    volume_a: int = 1,
    volume_b: int = 1,
) -> BatchRouteRequest:
    return BatchRouteRequest(
        batch_id="bat-1",
        courier_location=COURIER,
        departure_at=DEPARTURE,
        capacity=capacity,
        deliveries=(
            BatchStopRequest(
                delivery_id="del-1",
                pickup_point=RESTAURANT,
                pickup_label="Cantina",
                dropoff_point=CUSTOMER_A,
                dropoff_label="Rua A",
                volume=volume_a,
                promise_start_at=DEPARTURE - timedelta(minutes=30),
                promise_end_at=DEPARTURE + window_end_offset,
            ),
            BatchStopRequest(
                delivery_id="del-2",
                pickup_point=GeoPoint(latitude=-23.5477, longitude=-46.6389),
                pickup_label="Padaria",
                dropoff_point=CUSTOMER_B,
                dropoff_label="Rua B",
                volume=volume_b,
                promise_start_at=DEPARTURE - timedelta(minutes=30),
                promise_end_at=DEPARTURE + window_end_offset,
            ),
        ),
    )


def test_wide_windows_produce_a_schedule_with_planned_arrivals():
    planner = GraphRoutePlanner(GRAPH, PROFILE)
    plan = planner.plan_batch(_batch(), route_id="rpl-1")

    assert plan.solver_name.startswith("exact-windows")
    assert plan.departure_at == DEPARTURE
    assert plan.arrival_at is not None and plan.arrival_at > plan.departure_at
    assert plan.wait_seconds >= 0
    assert plan.lateness_seconds == 0
    assert 1 <= plan.capacity_used <= 3
    dropoffs = [stop for stop in plan.stops if stop.kind == "dropoff"]
    assert len(dropoffs) == 2
    for stop in plan.stops:
        if stop.kind == "dropoff":
            assert stop.planned_arrival_at is not None
            assert stop.promised_until is not None
            assert stop.planned_arrival_at <= stop.promised_until


def test_expired_window_rejects_the_batch():
    planner = GraphRoutePlanner(GRAPH, PROFILE)
    with pytest.raises(BatchInfeasibleError) as error:
        planner.plan_batch(
            _batch(window_end_offset=timedelta(seconds=-60)), route_id="rpl-2"
        )
    assert error.value.code == "batch_infeasible"
    assert "janela" in error.value.message


def test_capacity_rejects_the_batch():
    planner = GraphRoutePlanner(GRAPH, PROFILE)
    with pytest.raises(BatchInfeasibleError) as error:
        planner.plan_batch(
            _batch(capacity=3, volume_a=4, volume_b=1), route_id="rpl-3"
        )
    assert error.value.code == "batch_infeasible"
    assert "capacidade" in error.value.message


def test_capacity_fits_when_the_courier_delivers_one_at_a_time():
    planner = GraphRoutePlanner(GRAPH, PROFILE)
    plan = planner.plan_batch(
        _batch(capacity=2, volume_a=2, volume_b=1), route_id="rpl-4"
    )
    assert plan.capacity_used <= 2
    kinds = [stop.kind for stop in plan.stops]
    assert kinds.index("pickup") < kinds.index("dropoff")
