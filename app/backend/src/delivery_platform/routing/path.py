"""Shortest-path contracts and solvers for the live delivery route.

``AStarPathSolver`` is the production strategy; ``DijkstraPathSolver`` exists as
the bounded correctness oracle for tests. Both honor a routing ``objective`` —
``"time"`` minimizes estimated travel seconds (the product's ETA claim), while
``"distance"`` minimizes meters. The A* heuristic is admissible per objective:
straight-line meters for distance, straight-line meters divided by the graph's
fastest edge speed for time.

Consumers receive ``PathResult`` and ``DeliveryRouteResult`` — never a concrete
solver.
"""

from __future__ import annotations

import heapq
import itertools
import time
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from delivery_platform.domain.entities import RouteSegment, RouteStop
from delivery_platform.domain.geo import haversine_m
from delivery_platform.routing.graph import GraphEdge, StreetGraph

Objective = Literal["time", "distance"]


@dataclass(frozen=True)
class PathProblem:
    graph: StreetGraph
    origin: str
    destination: str
    objective: Objective = "time"

    def __post_init__(self) -> None:
        if self.origin not in self.graph.nodes:
            raise ValueError(f"Unknown origin node {self.origin}")
        if self.destination not in self.graph.nodes:
            raise ValueError(f"Unknown destination node {self.destination}")
        if self.objective not in ("time", "distance"):
            raise ValueError(f"Unknown objective {self.objective}")


@dataclass(frozen=True)
class PathResult:
    node_path: tuple[str, ...]
    geometry: dict[str, Any]
    distance_meters: float
    estimated_seconds: float
    solver_name: str
    solver_version: str
    computation_time_ns: int
    nodes_expanded: int
    objective: str = "time"
    expanded_order: tuple[str, ...] = ()


class PathSolver(Protocol):
    def solve(self, problem: PathProblem) -> PathResult: ...


def _edge_weight(edge: GraphEdge, objective: str) -> float:
    return edge.seconds if objective == "time" else edge.distance_meters


def _geometry(graph: StreetGraph, node_path: tuple[str, ...]) -> dict[str, Any]:
    return {
        "type": "LineString",
        "coordinates": [
            [graph.nodes[n].longitude, graph.nodes[n].latitude] for n in node_path
        ],
    }


def _reconstruct(came_from: dict[str, str], destination: str) -> tuple[str, ...]:
    path = [destination]
    while path[-1] in came_from:
        path.append(came_from[path[-1]])
    path.reverse()
    return tuple(path)


def _path_totals(graph: StreetGraph, node_path: tuple[str, ...]) -> tuple[float, float]:
    distance = 0.0
    seconds = 0.0
    for current, nxt in itertools.pairwise(node_path):
        edge = next(e for e in graph.neighbors(current) if e.to_node == nxt)
        distance += edge.distance_meters
        seconds += edge.seconds
    return distance, seconds


class AStarPathSolver:
    """A* over the synthetic graph with an admissible haversine heuristic."""

    solver_name = "astar-synthetic-graph"
    solver_version = "2.0.0"

    def solve(
        self, problem: PathProblem, *, trace: bool = False
    ) -> PathResult:
        started = time.perf_counter_ns()
        graph = problem.graph
        goal = problem.destination
        max_speed_mps = graph.max_speed_mps or 1.0

        if problem.objective == "time":

            def heuristic(node: str) -> float:
                return haversine_m(graph.nodes[node], graph.nodes[goal]) / max_speed_mps

        else:

            def heuristic(node: str) -> float:
                return haversine_m(graph.nodes[node], graph.nodes[goal])

        g_score: dict[str, float] = {problem.origin: 0.0}
        came_from: dict[str, str] = {}
        frontier: list[tuple[float, str]] = [(heuristic(problem.origin), problem.origin)]
        expanded = 0
        expanded_list: list[str] = []
        closed: set[str] = set()

        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal:
                node_path = _reconstruct(came_from, goal)
                distance, seconds = _path_totals(graph, node_path)
                return PathResult(
                    node_path=node_path,
                    geometry=_geometry(graph, node_path),
                    distance_meters=distance,
                    estimated_seconds=seconds,
                    solver_name=self.solver_name,
                    solver_version=self.solver_version,
                    computation_time_ns=time.perf_counter_ns() - started,
                    nodes_expanded=expanded,
                    objective=problem.objective,
                    expanded_order=tuple(expanded_list) if trace else (),
                )
            if current in closed:
                continue
            closed.add(current)
            expanded += 1
            if trace:
                expanded_list.append(current)
            for edge in graph.neighbors(current):
                tentative = g_score[current] + _edge_weight(edge, problem.objective)
                if tentative < g_score.get(edge.to_node, float("inf")):
                    came_from[edge.to_node] = current
                    g_score[edge.to_node] = tentative
                    heapq.heappush(
                        frontier, (tentative + heuristic(edge.to_node), edge.to_node)
                    )
        raise ValueError(f"No path from {problem.origin} to {problem.destination}")


class DijkstraPathSolver:
    """Bounded oracle: uniform-cost search used to verify A* in tests."""

    solver_name = "dijkstra-oracle"
    solver_version = "2.0.0"

    def solve(
        self, problem: PathProblem, *, trace: bool = False
    ) -> PathResult:
        started = time.perf_counter_ns()
        graph = problem.graph
        dist: dict[str, float] = {problem.origin: 0.0}
        came_from: dict[str, str] = {}
        frontier: list[tuple[float, str]] = [(0.0, problem.origin)]
        expanded = 0
        expanded_list: list[str] = []
        closed: set[str] = set()

        while frontier:
            cost, current = heapq.heappop(frontier)
            if current in closed:
                continue
            closed.add(current)
            expanded += 1
            if trace:
                expanded_list.append(current)
            if current == problem.destination:
                node_path = _reconstruct(came_from, current)
                distance, seconds = _path_totals(graph, node_path)
                return PathResult(
                    node_path=node_path,
                    geometry=_geometry(graph, node_path),
                    distance_meters=distance,
                    estimated_seconds=seconds,
                    solver_name=self.solver_name,
                    solver_version=self.solver_version,
                    computation_time_ns=time.perf_counter_ns() - started,
                    nodes_expanded=expanded,
                    objective=problem.objective,
                    expanded_order=tuple(expanded_list) if trace else (),
                )
            for edge in graph.neighbors(current):
                tentative = cost + _edge_weight(edge, problem.objective)
                if tentative < dist.get(edge.to_node, float("inf")):
                    dist[edge.to_node] = tentative
                    came_from[edge.to_node] = current
                    heapq.heappush(frontier, (tentative, edge.to_node))
        raise ValueError(f"No path from {problem.origin} to {problem.destination}")


@dataclass(frozen=True)
class DeliveryRouteProblem:
    """Two-leg delivery input: courier → pickup → dropoff on one graph."""

    graph: StreetGraph
    courier_origin: str
    pickup_node: str
    dropoff_node: str
    pickup_label: str
    dropoff_label: str
    delivery_id: str
    deterministic_seed: int = 0
    objective: Objective = "time"

    def __post_init__(self) -> None:
        for name, node in (
            ("courier_origin", self.courier_origin),
            ("pickup_node", self.pickup_node),
            ("dropoff_node", self.dropoff_node),
        ):
            if node not in self.graph.nodes:
                raise ValueError(f"Unknown {name} {node}")


@dataclass(frozen=True)
class DeliveryRouteResult:
    stops: list[RouteStop]
    segments: list[RouteSegment]
    geometry: dict[str, Any]
    distance_meters: float
    estimated_seconds: float
    solver_name: str
    solver_version: str
    computation_time_ns: int
    nodes_expanded: int
    graph_id: str
    graph_version: str
    warnings: list[str] = field(default_factory=list)
    objective: str = "time"


class DeliveryRouteSolver:
    """Composes two PathSolver legs into a provider-neutral delivery route."""

    def __init__(self, path_solver: PathSolver) -> None:
        self._solver = path_solver

    def solve(self, problem: DeliveryRouteProblem) -> DeliveryRouteResult:
        started = time.perf_counter_ns()
        graph = problem.graph
        leg_pickup = self._solver.solve(
            PathProblem(
                graph, problem.courier_origin, problem.pickup_node, problem.objective
            )
        )
        leg_dropoff = self._solver.solve(
            PathProblem(
                graph, problem.pickup_node, problem.dropoff_node, problem.objective
            )
        )
        stops = [
            RouteStop(
                kind="pickup",
                ref_id=problem.delivery_id,
                label=problem.pickup_label,
                location=graph.nodes[problem.pickup_node],
                sequence=1,
            ),
            RouteStop(
                kind="dropoff",
                ref_id=problem.delivery_id,
                label=problem.dropoff_label,
                location=graph.nodes[problem.dropoff_node],
                sequence=2,
            ),
        ]
        segments = [
            RouteSegment(
                from_label="entregador",
                to_label=problem.pickup_label,
                node_path=leg_pickup.node_path,
                distance_meters=leg_pickup.distance_meters,
                estimated_seconds=leg_pickup.estimated_seconds,
            ),
            RouteSegment(
                from_label=problem.pickup_label,
                to_label=problem.dropoff_label,
                node_path=leg_dropoff.node_path,
                distance_meters=leg_dropoff.distance_meters,
                estimated_seconds=leg_dropoff.estimated_seconds,
            ),
        ]
        all_nodes = leg_pickup.node_path + leg_dropoff.node_path[1:]
        return DeliveryRouteResult(
            stops=stops,
            segments=segments,
            geometry={
                "type": "LineString",
                "coordinates": [
                    [graph.nodes[n].longitude, graph.nodes[n].latitude]
                    for n in all_nodes
                ],
            },
            distance_meters=leg_pickup.distance_meters + leg_dropoff.distance_meters,
            estimated_seconds=leg_pickup.estimated_seconds
            + leg_dropoff.estimated_seconds,
            solver_name=leg_pickup.solver_name,
            solver_version=leg_pickup.solver_version,
            computation_time_ns=time.perf_counter_ns() - started,
            nodes_expanded=leg_pickup.nodes_expanded + leg_dropoff.nodes_expanded,
            graph_id=graph.graph_id,
            graph_version=graph.version,
            objective=problem.objective,
        )
