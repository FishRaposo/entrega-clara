"""Fallback straight-line route planner.

Used when the versioned synthetic graph cannot be loaded — it connects stops
with great-circle legs so the delivery flow still produces a real
``RoutePlan`` record behind the same ``DeliveryRoutePlanner`` port.
"""

from __future__ import annotations

import time

from delivery_platform.application.ports import DeliveryRouteRequest
from delivery_platform.domain.entities import GeoPoint, RoutePlan, RouteSegment, RouteStop
from delivery_platform.domain.geo import haversine_m

_AVERAGE_SPEED_KMH = 25.0


class StraightLineRoutePlanner:
    """Fallback planner: connects stops with great-circle segments."""

    solver_name = "straight-line-haversine"
    solver_version = "1.0.0"

    def plan(self, request: DeliveryRouteRequest, *, route_id: str) -> RoutePlan:
        started = time.perf_counter_ns()
        meters_per_second = _AVERAGE_SPEED_KMH * 1000 / 3600

        def leg(from_point: GeoPoint, to_point: GeoPoint) -> tuple[float, float]:
            distance = haversine_m(from_point, to_point)
            return distance, distance / meters_per_second

        to_pickup_m, to_pickup_s = leg(request.courier_location, request.pickup_point)
        to_dropoff_m, to_dropoff_s = leg(request.pickup_point, request.dropoff_point)

        stops = [
            RouteStop(
                kind="pickup",
                ref_id=request.delivery_id,
                label=request.pickup_label,
                location=request.pickup_point,
                sequence=1,
            ),
            RouteStop(
                kind="dropoff",
                ref_id=request.delivery_id,
                label=request.dropoff_label,
                location=request.dropoff_point,
                sequence=2,
            ),
        ]
        segments = [
            RouteSegment(
                from_label="entregador",
                to_label=request.pickup_label,
                node_path=(),
                distance_meters=to_pickup_m,
                estimated_seconds=to_pickup_s,
            ),
            RouteSegment(
                from_label=request.pickup_label,
                to_label=request.dropoff_label,
                node_path=(),
                distance_meters=to_dropoff_m,
                estimated_seconds=to_dropoff_s,
            ),
        ]
        geometry = {
            "type": "LineString",
            "coordinates": [
                [request.courier_location.longitude, request.courier_location.latitude],
                [request.pickup_point.longitude, request.pickup_point.latitude],
                [request.dropoff_point.longitude, request.dropoff_point.latitude],
            ],
        }
        return RoutePlan(
            id=route_id,
            delivery_id=request.delivery_id,
            graph_id="none",
            graph_version="0",
            stops=stops,
            segments=segments,
            geometry=geometry,
            distance_meters=to_pickup_m + to_dropoff_m,
            estimated_seconds=to_pickup_s + to_dropoff_s,
            solver_name=self.solver_name,
            solver_version=self.solver_version,
            computation_time_ns=time.perf_counter_ns() - started,
            nodes_expanded=0,
            warnings=["Rota aproximada em linha reta; grafo de ruas ainda não integrado."],
            objective="distance",
        )
