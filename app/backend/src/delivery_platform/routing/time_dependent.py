"""Time-dependent least-arrival-time routing under a FIFO speed profile.

Two solvers share one core:

    TimeDependentDijkstraPathSolver   exact oracle for time-dependent costs
    TimeDependentAStarPathSolver      the same search with a straight-line bound

The search state is arrival time, not distance travelled: each relaxation asks
the profile how long the edge takes *at the moment the courier reaches it*. When
the profile satisfies FIFO (validated at load time), settling a node the first
time is optimal and waiting at a node is never useful — the standard
time-dependent Dijkstra argument, in the simplest form that the data supports.

The A* variant uses ``distance · min_multiplier / max_speed`` as its bound: the
network can never be faster than its fastest multiplier, so the estimate stays
admissible and consistent.
"""

from __future__ import annotations

import heapq
import time
from collections.abc import Callable

from delivery_platform.domain.geo import haversine_m
from delivery_platform.routing.graph import StreetGraph
from delivery_platform.routing.path import (
    PathProblem,
    PathResult,
    geometry_for,
    path_distance,
    reconstruct_path,
)
from delivery_platform.routing.time_profile import TravelTimeProfile


def _require_time_dependent(problem: PathProblem) -> tuple[float, TravelTimeProfile]:
    if problem.objective != "time":
        raise ValueError("Time-dependent routing supports the time objective only")
    if problem.departure_at is None:
        raise ValueError("Time-dependent routing requires departure_at")
    if problem.profile is None:
        raise ValueError("Time-dependent routing requires a traffic profile")
    return float(problem.departure_at), problem.profile


def time_dependent_heuristic(
    graph: StreetGraph, goal: str, profile: TravelTimeProfile
) -> Callable[[str], float]:
    """Admissible bound: straight-line meters over the fastest possible speed."""
    fastest_mps = (graph.max_speed_mps or 1.0) / profile.fastest_speed_factor

    def heuristic(node: str) -> float:
        return haversine_m(graph.nodes[node], graph.nodes[goal]) / fastest_mps

    return heuristic


def time_dependent_search(
    problem: PathProblem,
    *,
    heuristic: Callable[[str], float] | None,
    solver_name: str,
    solver_version: str,
    started_ns: int,
    trace: bool = False,
) -> PathResult:
    departure, profile = _require_time_dependent(problem)
    graph = problem.graph
    goal = problem.destination
    arrivals: dict[str, float] = {problem.origin: departure}
    came_from: dict[str, str] = {}
    estimate = heuristic or (lambda _node: 0.0)
    frontier: list[tuple[float, str]] = [
        (departure + estimate(problem.origin), problem.origin)
    ]
    closed: set[str] = set()
    expanded = 0
    order: list[str] = []
    series: list[int] = []
    costs: list[float] = []

    while frontier:
        _, current = heapq.heappop(frontier)
        if current in closed:
            continue
        closed.add(current)
        expanded += 1
        now = arrivals[current]
        if trace:
            order.append(current)
            series.append(len(frontier))
            costs.append(now - departure)
        if current == goal:
            node_path = reconstruct_path(came_from, goal)
            return PathResult(
                node_path=node_path,
                geometry=geometry_for(graph, node_path),
                distance_meters=path_distance(graph, node_path),
                estimated_seconds=now - departure,
                solver_name=solver_name,
                solver_version=solver_version,
                computation_time_ns=time.perf_counter_ns() - started_ns,
                nodes_expanded=expanded,
                objective=problem.objective,
                expanded_order=tuple(order) if trace else (),
                frontier_sizes=tuple(series) if trace else (),
                expansion_costs=tuple(costs) if trace else (),
                departure_at=departure,
                arrival_at=now,
            )
        for edge in graph.neighbors(current):
            arrive = now + profile.edge_seconds(edge, now)
            if arrive < arrivals.get(edge.to_node, float("inf")):
                arrivals[edge.to_node] = arrive
                came_from[edge.to_node] = current
                heapq.heappush(frontier, (arrive + estimate(edge.to_node), edge.to_node))
    raise ValueError(f"No path from {problem.origin} to {problem.destination}")


class TimeDependentDijkstraPathSolver:
    """Exact least-arrival-time search: the oracle for time-dependent costs."""

    solver_name = "td-dijkstra"
    solver_version = "1.0.0"

    def solve(self, problem: PathProblem, *, trace: bool = False) -> PathResult:
        started = time.perf_counter_ns()
        return time_dependent_search(
            problem,
            heuristic=None,
            solver_name=self.solver_name,
            solver_version=self.solver_version,
            started_ns=started,
            trace=trace,
        )


class TimeDependentAStarPathSolver:
    """A* over arrival time with an admissible straight-line bound."""

    solver_name = "td-astar"
    solver_version = "1.0.0"

    def solve(self, problem: PathProblem, *, trace: bool = False) -> PathResult:
        started = time.perf_counter_ns()
        _, profile = _require_time_dependent(problem)
        return time_dependent_search(
            problem,
            heuristic=time_dependent_heuristic(problem.graph, problem.destination, profile),
            solver_name=self.solver_name,
            solver_version=self.solver_version,
            started_ns=started,
            trace=trace,
        )
