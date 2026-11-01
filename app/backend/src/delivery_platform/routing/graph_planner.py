"""Graph-backed DeliveryRoutePlanner: snaps coordinates to nodes, solves on streets.

Static planning uses plain A* (no preprocessing). When a traffic profile is
configured **and** the caller supplies a departure time, the planner switches to
the time-dependent A*: every edge is priced at the moment the courier reaches
it, the second leg departs when the first one lands, and the resulting plan
carries ``departure_at``/``arrival_at`` so the product can compare promise and
delivery.
"""

from __future__ import annotations

import itertools
from dataclasses import replace
from datetime import UTC, datetime

from delivery_platform.application.ports import (
    BatchRouteRequest,
    DeliveryRouteRequest,
)
from delivery_platform.domain.entities import (
    RoutePlan,
    RouteSegment,
    RouteStop,
    StopKind,
)
from delivery_platform.domain.errors import RouteUnavailableError
from delivery_platform.routing.graph import StreetGraph
from delivery_platform.routing.path import (
    AStarPathSolver,
    DeliveryRouteProblem,
    DeliveryRouteSolver,
    PathProblem,
    PathResult,
)
from delivery_platform.routing.time_dependent import TimeDependentAStarPathSolver
from delivery_platform.routing.time_profile import TravelTimeProfile


def _epoch(moment: datetime | None) -> float | None:
    return moment.timestamp() if moment is not None else None


def _datetime(seconds: float | None) -> datetime | None:
    return datetime.fromtimestamp(seconds, UTC) if seconds is not None else None


class GraphRoutePlanner:
    """Two-leg and multi-stop planner over the configured street graph."""

    def __init__(self, graph: StreetGraph, profile: TravelTimeProfile | None = None) -> None:
        self._graph = graph
        self._profile = profile
        self._static_route = DeliveryRouteSolver(AStarPathSolver())
        self._time_dependent_route = DeliveryRouteSolver(TimeDependentAStarPathSolver())

    @property
    def graph(self) -> StreetGraph:
        return self._graph

    @property
    def profile(self) -> TravelTimeProfile | None:
        return self._profile

    def plan(self, request: DeliveryRouteRequest, *, route_id: str) -> RoutePlan:
        departure = _epoch(request.departure_at)
        profile = self._profile
        time_dependent = profile is not None and departure is not None
        solver = self._time_dependent_route if time_dependent else self._static_route
        try:
            result = solver.solve(
                DeliveryRouteProblem(
                    graph=self._graph,
                    courier_origin=self._graph.nearest_node(request.courier_location),
                    pickup_node=self._graph.nearest_node(request.pickup_point),
                    dropoff_node=self._graph.nearest_node(request.dropoff_point),
                    pickup_label=request.pickup_label,
                    dropoff_label=request.dropoff_label,
                    delivery_id=request.delivery_id,
                    objective="time",
                    departure_at=departure if time_dependent else None,
                    profile=profile if time_dependent else None,
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
            departure_at=_datetime(result.departure_at),
            arrival_at=_datetime(result.arrival_at),
            traffic_profile_id=result.traffic_profile_id,
        )

    def plan_batch(self, request: BatchRouteRequest, *, route_id: str) -> RoutePlan:
        """Open multi-stop tour: cost matrix + Held-Karp with precedence.

        With a profile and a departure time, matrix cells and final legs are
        priced by the time-dependent solver. Matrix cells start at the batch
        departure (no accumulation across stops) — a first-order model that the
        ADR records; the legs themselves accumulate arrival times exactly.
        """
        from delivery_platform.routing.matrix import build_cost_matrix
        from delivery_platform.routing.tsp import HeldKarpSolver, NearestNeighborSolver

        graph = self._graph
        profile = self._profile
        departure = _epoch(request.departure_at)
        time_dependent = profile is not None and departure is not None
        path_solver: AStarPathSolver | TimeDependentAStarPathSolver
        path_solver = TimeDependentAStarPathSolver() if time_dependent else AStarPathSolver()

        count = len(request.deliveries)
        courier_node = graph.nearest_node(request.courier_location)
        pickup_nodes = [graph.nearest_node(d.pickup_point) for d in request.deliveries]
        dropoff_nodes = [graph.nearest_node(d.dropoff_point) for d in request.deliveries]

        labels = (
            ["courier"]
            + [f"pickup-{i}" for i in range(count)]
            + [f"dropoff-{i}" for i in range(count)]
        )
        nodes = (courier_node, *pickup_nodes, *dropoff_nodes)
        if time_dependent:
            assert departure is not None and profile is not None

            def price(problem: PathProblem) -> PathResult:
                return path_solver.solve(
                    replace(problem, departure_at=departure, profile=profile)
                )

            problem = build_cost_matrix(
                graph,
                labels=tuple(labels),
                nodes=nodes,
                objective="time",
                origin_index=0,
                solver=price,
            )
        else:
            problem = build_cost_matrix(
                graph,
                labels=tuple(labels),
                nodes=nodes,
                objective="time",
                origin_index=0,
            )
        precedence = {1 + count + i: 1 + i for i in range(count)}
        solver = HeldKarpSolver(precedence=precedence, closed=False)
        tour = solver.solve(problem)
        # Same matrix, cheap heuristic: the pair turns "we optimize the stop
        # order" into a number the courier console can show.
        baseline = NearestNeighborSolver(precedence=precedence, closed=False).solve(problem)

        ordered = [labels.index(label) for label in tour.route[1:]]
        node_seq = [nodes[i] for i in ordered]
        legs: list[PathResult] = []
        current = departure if time_dependent else None
        for origin, destination in itertools.pairwise((courier_node, *node_seq)):
            leg = path_solver.solve(
                PathProblem(
                    graph,
                    origin,
                    destination,
                    "time",
                    current,
                    profile if time_dependent else None,
                )
            )
            legs.append(leg)
            if time_dependent:
                current = leg.arrival_at

        stops: list[RouteStop] = []
        for position, idx in enumerate(ordered, start=1):
            delivery = request.deliveries[(idx - 1) % count]
            kind: StopKind = "pickup" if idx <= count else "dropoff"
            stops.append(
                RouteStop(
                    kind=kind,
                    ref_id=delivery.delivery_id,
                    label=delivery.pickup_label if kind == "pickup" else delivery.dropoff_label,
                    location=graph.nodes[nodes[idx]],
                    sequence=position,
                )
            )
        segments = [
            RouteSegment(
                from_label="entregador" if i == 0 else stops[i - 1].label,
                to_label=stops[i].label,
                node_path=leg.node_path,
                distance_meters=leg.distance_meters,
                estimated_seconds=leg.estimated_seconds,
            )
            for i, leg in enumerate(legs)
        ]
        all_nodes: list[str] = []
        for leg in legs:
            all_nodes.extend(leg.node_path if not all_nodes else leg.node_path[1:])
        return RoutePlan(
            id=route_id,
            delivery_id=stops[0].ref_id,
            batch_id=request.batch_id,
            graph_id=graph.graph_id,
            graph_version=graph.version,
            stops=stops,
            segments=segments,
            geometry={
                "type": "LineString",
                "coordinates": [
                    [graph.nodes[n].longitude, graph.nodes[n].latitude] for n in all_nodes
                ],
            },
            distance_meters=sum(leg.distance_meters for leg in legs),
            estimated_seconds=sum(leg.estimated_seconds for leg in legs),
            solver_name=f"{solver.solver_name}+{path_solver.solver_name}",
            solver_version=legs[0].solver_version,
            computation_time_ns=sum(leg.computation_time_ns for leg in legs)
            + tour.execution_time_ns,
            nodes_expanded=sum(leg.nodes_expanded for leg in legs),
            warnings=[],
            objective="time",
            departure_at=_datetime(departure if time_dependent else None),
            arrival_at=_datetime(legs[-1].arrival_at),
            traffic_profile_id=(
                profile.profile_id if time_dependent and profile is not None else None
            ),
            baseline_solver_name=baseline.solver_name,
            baseline_cost=baseline.total_cost,
        )
