"""Graph-backed DeliveryRoutePlanner: snaps coordinates to nodes, runs A*."""

from __future__ import annotations

import itertools

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

    def plan_batch(self, request: BatchRouteRequest, *, route_id: str) -> RoutePlan:
        """Open multi-stop tour: cost-matrix + Held-Karp with precedence.

        Leg costs come from A* on the time objective; the tour order from the
        exact solver under pickup-before-dropoff constraints.
        """
        from delivery_platform.routing.matrix import build_cost_matrix
        from delivery_platform.routing.tsp import HeldKarpSolver

        graph = self._graph
        count = len(request.deliveries)
        courier_node = graph.nearest_node(request.courier_location)
        pickup_nodes = [
            graph.nearest_node(d.pickup_point) for d in request.deliveries
        ]
        dropoff_nodes = [
            graph.nearest_node(d.dropoff_point) for d in request.deliveries
        ]

        labels = ["courier"] + [f"pickup-{i}" for i in range(count)] + [
            f"dropoff-{i}" for i in range(count)
        ]
        nodes = (courier_node, *pickup_nodes, *dropoff_nodes)
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

        ordered = [labels.index(label) for label in tour.route[1:]]
        node_seq = [nodes[i] for i in ordered]
        path_solver = AStarPathSolver()
        legs = [
            path_solver.solve(
                PathProblem(graph, a, b, "time")
            )
            for a, b in itertools.pairwise((courier_node, *node_seq))
        ]

        stops: list[RouteStop] = []
        for position, idx in enumerate(ordered, start=1):
            delivery = request.deliveries[
                (idx - 1) % count
            ]
            kind: StopKind = "pickup" if idx <= count else "dropoff"
            stops.append(
                RouteStop(
                    kind=kind,
                    ref_id=delivery.delivery_id,
                    label=delivery.pickup_label
                    if kind == "pickup"
                    else delivery.dropoff_label,
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
                    [graph.nodes[n].longitude, graph.nodes[n].latitude]
                    for n in all_nodes
                ],
            },
            distance_meters=sum(leg.distance_meters for leg in legs),
            estimated_seconds=sum(leg.estimated_seconds for leg in legs),
            solver_name=f"{solver.solver_name}+astar-synthetic-graph",
            solver_version=legs[0].solver_version,
            computation_time_ns=sum(leg.computation_time_ns for leg in legs)
            + tour.execution_time_ns,
            nodes_expanded=sum(leg.nodes_expanded for leg in legs),
            warnings=[],
            objective="time",
        )
