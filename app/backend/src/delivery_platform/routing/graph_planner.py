"""Graph-backed DeliveryRoutePlanner: snaps coordinates to nodes, runs A*."""

from __future__ import annotations

from delivery_platform.application.ports import DeliveryRouteRequest
from delivery_platform.domain.entities import RoutePlan
from delivery_platform.domain.errors import RouteUnavailableError
from delivery_platform.routing.graph import StreetGraph
from delivery_platform.routing.path import (
    AStarPathSolver,
    DeliveryRouteProblem,
    DeliveryRouteSolver,
)


class GraphRoutePlanner:
    """Two-leg A* planner over the versioned synthetic graph."""

    def __init__(self, graph: StreetGraph) -> None:
        self._graph = graph
        self._solver = DeliveryRouteSolver(AStarPathSolver())

    @property
    def graph(self) -> StreetGraph:
        return self._graph

    def plan(self, request: DeliveryRouteRequest, *, route_id: str) -> RoutePlan:
        try:
            result = self._solver.solve(
                DeliveryRouteProblem(
                    graph=self._graph,
                    courier_origin=self._graph.nearest_node(request.courier_location),
                    pickup_node=self._graph.nearest_node(request.pickup_point),
                    dropoff_node=self._graph.nearest_node(request.dropoff_point),
                    pickup_label=request.pickup_label,
                    dropoff_label=request.dropoff_label,
                    delivery_id=request.delivery_id,
                    objective="time",
                )
            )
        except ValueError as error:
            raise RouteUnavailableError() from error
        return RoutePlan(
            id=route_id,
            delivery_id=request.delivery_id,
            graph_id=result.graph_id,
            graph_version=result.graph_version,
            stops=result.stops,
            segments=result.segments,
            geometry=result.geometry,
            distance_meters=result.distance_meters,
            estimated_seconds=result.estimated_seconds,
            solver_name=result.solver_name,
            solver_version=result.solver_version,
            computation_time_ns=result.computation_time_ns,
            nodes_expanded=result.nodes_expanded,
            warnings=list(result.warnings),
            objective=result.objective,
        )
