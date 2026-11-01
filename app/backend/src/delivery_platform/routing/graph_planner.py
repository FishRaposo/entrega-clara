"""Graph-backed DeliveryRoutePlanner: snaps coordinates to nodes, solves on streets.

Static planning uses plain A* (no preprocessing). When a traffic profile is
configured **and** the caller supplies a departure time, the planner switches to
the time-dependent A*: every edge is priced at the moment the courier reaches
it, the second leg departs when the first one lands, and the resulting plan
carries ``departure_at``/``arrival_at`` so the product can compare promise and
delivery.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from delivery_platform.application.ports import (
    BatchRouteRequest,
    BatchStopRequest,
    DeliveryRouteRequest,
)
from delivery_platform.core.metrics import METRICS
from delivery_platform.domain.entities import (
    RoutePlan,
    RouteSegment,
    RouteStop,
    StopKind,
)
from delivery_platform.domain.errors import BatchInfeasibleError, RouteUnavailableError
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
        METRICS.inc(
            "entrega_routing_queries_total", {"kind": "route", "solver": result.solver_name}
        )
        METRICS.observe(
            "entrega_routing_seconds", result.computation_time_ns / 1e9, {"kind": "route"}
        )
        METRICS.inc(
            "entrega_routing_nodes_expanded_total", {"kind": "route"}, result.nodes_expanded
        )
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
        """Windowed multi-stop tour: cost matrix + capacitated VRP with precedence.

        The optimizer now knows what dispatch actually promises: each drop-off
        carries a window, each order a volume, the courier a capacity, and a
        pickup must precede its drop-off. Windows are soft inside the solver
        (lateness is priced) and hard at acceptance (``max_lateness_seconds``),
        so an infeasible batch is rejected with a typed reason instead of being
        silently planned late.

        With a profile and a departure time, matrix cells and legs are priced by
        the time-dependent solver; matrix cells start at the batch departure
        (no accumulation), while the legs are scheduled from the VRP times.
        """
        from delivery_platform.routing.matrix import build_cost_matrix
        from delivery_platform.routing.vrp import (
            EXACT_STOP_LIMIT,
            ExactWindowSolver,
            InsertionWindowSolver,
            VrpProblem,
            VrpStop,
            evaluate,
        )

        graph = self._graph
        profile = self._profile
        departure = _epoch(request.departure_at)
        time_dependent = profile is not None and departure is not None
        path_solver: AStarPathSolver | TimeDependentAStarPathSolver
        path_solver = TimeDependentAStarPathSolver() if time_dependent else AStarPathSolver()

        if len(request.deliveries) < 2:
            raise ValueError("a batch needs at least two deliveries")
        courier_node = graph.nearest_node(request.courier_location)

        # Matrix rows and stop indices are built together; an order picked up
        # before a re-plan contributes only its drop-off, and its volume starts
        # on board.
        nodes: list[str] = [courier_node]
        specs: list[tuple[BatchStopRequest, StopKind]] = []
        initial_load = 0
        for delivery in request.deliveries:
            if delivery.picked_up:
                initial_load += delivery.volume
            else:
                nodes.append(graph.nearest_node(delivery.pickup_point))
                specs.append((delivery, "pickup"))
            nodes.append(graph.nearest_node(delivery.dropoff_point))
            specs.append((delivery, "dropoff"))

        labels = ("courier", *(f"stop-{position}" for position in range(1, len(nodes))))
        node_tuple = tuple(nodes)
        if time_dependent:
            assert departure is not None and profile is not None

            def price(problem: PathProblem) -> PathResult:
                return path_solver.solve(
                    replace(problem, departure_at=departure, profile=profile)
                )

            matrix = build_cost_matrix(
                graph,
                labels=labels,
                nodes=node_tuple,
                objective="time",
                origin_index=0,
                solver=price,
            )
        else:
            matrix = build_cost_matrix(
                graph,
                labels=labels,
                nodes=node_tuple,
                objective="time",
                origin_index=0,
            )
        costs = tuple(tuple(float(cell) for cell in row) for row in matrix.costs)

        stops: list[VrpStop] = []
        for position, (delivery, kind) in enumerate(specs, start=1):
            window_start: float | None = None
            window_end: float | None = None
            if kind == "dropoff" and (
                delivery.promise_start_at is not None or delivery.promise_end_at is not None
            ):
                if departure is None:
                    raise ValueError("promise windows require a batch departure time")
                if delivery.promise_start_at is not None:
                    window_start = delivery.promise_start_at.timestamp() - departure
                if delivery.promise_end_at is not None:
                    window_end = delivery.promise_end_at.timestamp() - departure
            stops.append(
                VrpStop(
                    index=position,
                    label=delivery.pickup_label
                    if kind == "pickup"
                    else delivery.dropoff_label,
                    kind=kind,
                    delivery_id=delivery.delivery_id,
                    volume=delivery.volume if kind == "pickup" else -delivery.volume,
                    window_start=window_start,
                    window_end=window_end,
                )
            )
        problem = VrpProblem(
            costs=costs,
            stops=tuple(stops),
            capacity=request.capacity,
            max_lateness=request.max_lateness_seconds,
            initial_load=initial_load,
        )
        solver = ExactWindowSolver() if problem.size <= EXACT_STOP_LIMIT else InsertionWindowSolver()
        result = solver.solve(problem)
        if not result.order or not result.schedule.feasible:
            METRICS.inc(
                "entrega_routing_queries_total", {"kind": "batch", "solver": "infeasible"}
            )
            raise BatchInfeasibleError(result.schedule.violations)

        legs: list[PathResult] = []
        previous_node = courier_node
        for position, index in enumerate(result.order):
            offset = result.schedule.visits[position - 1].finish if position else 0.0
            current = departure + offset if departure is not None else None
            leg = path_solver.solve(
                PathProblem(
                    graph,
                    previous_node,
                    nodes[index],
                    "time",
                    current,
                    profile if time_dependent else None,
                )
            )
            legs.append(leg)
            previous_node = nodes[index]

        planned: list[RouteStop] = []
        for position, index in enumerate(result.order, start=1):
            delivery, kind = specs[index - 1]
            visit = result.schedule.visits[position - 1]
            planned.append(
                RouteStop(
                    kind=kind,
                    ref_id=delivery.delivery_id,
                    label=delivery.pickup_label
                    if kind == "pickup"
                    else delivery.dropoff_label,
                    location=graph.nodes[nodes[index]],
                    sequence=position,
                    planned_arrival_at=(
                        _datetime(departure + visit.start) if departure is not None else None
                    ),
                    promised_until=(
                        delivery.promise_end_at if kind == "dropoff" else None
                    ),
                )
            )
        segments = [
            RouteSegment(
                from_label="entregador" if i == 0 else planned[i - 1].label,
                to_label=planned[i].label,
                node_path=leg.node_path,
                distance_meters=leg.distance_meters,
                estimated_seconds=leg.estimated_seconds,
            )
            for i, leg in enumerate(legs)
        ]
        all_nodes: list[str] = []
        for leg in legs:
            all_nodes.extend(leg.node_path if not all_nodes else leg.node_path[1:])
        # Baseline: the order the deliveries were offered in, priced on the same
        # matrix. Waiting and lateness stay out of it, so the comparison is
        # travel against travel.
        offered = evaluate(problem, tuple(range(1, problem.size + 1)), require_complete=False)
        total_seconds = result.schedule.visits[-1].finish
        METRICS.inc(
            "entrega_routing_queries_total", {"kind": "batch", "solver": result.solver_name}
        )
        METRICS.observe(
            "entrega_routing_seconds", result.execution_time_ns / 1e9, {"kind": "batch"}
        )
        return RoutePlan(
            id=route_id,
            delivery_id=planned[0].ref_id,
            batch_id=request.batch_id,
            graph_id=graph.graph_id,
            graph_version=graph.version,
            stops=planned,
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
            + result.execution_time_ns,
            nodes_expanded=sum(leg.nodes_expanded for leg in legs),
            warnings=[],
            objective="time",
            departure_at=_datetime(departure),
            arrival_at=(
                _datetime(departure + total_seconds) if departure is not None else None
            ),
            traffic_profile_id=(
                profile.profile_id if time_dependent and profile is not None else None
            ),
            wait_seconds=result.schedule.wait_seconds,
            lateness_seconds=result.schedule.lateness_seconds,
            capacity_used=max(
                (visit.load for visit in result.schedule.visits), default=0
            ),
            baseline_solver_name="offered-order",
            baseline_cost=offered.travel_seconds,
        )
