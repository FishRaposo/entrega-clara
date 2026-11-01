"""Informed search variants: ALT, balanced bidirectional, weighted A*.

These extend the base ladder in ``routing/path.py`` behind the same
``PathSolver`` contract. The product route keeps the plain A*; the lab and the
benchmark harness pick whichever solver demonstrates the point.

Correctness gate: on sampled origin/destination pairs every exact solver must
return the same optimal cost as ``DijkstraPathSolver`` — enforced by
``tests/routing/test_informed_solvers.py`` on both the synthetic fixture graph
and the real street graph.
"""

from __future__ import annotations

import heapq
import time

from delivery_platform.routing.graph import GraphEdge
from delivery_platform.routing.landmarks import DEFAULT_LANDMARK_COUNT, landmark_table
from delivery_platform.routing.path import (
    PathProblem,
    PathResult,
    astar_search,
    edge_weight,
    geometry_for,
    path_totals,
    straight_line_heuristic,
)


class WeightedAStarSolver:
    """ε-admissible A*: ``f = g + ε·h``.

    Deliberately inadmissible once ε > 1, in exchange for expanding far fewer
    nodes: the returned path costs at most ε × the optimum. It exists to *show*
    the work/quality trade-off — the lab labels it as inexact and the benchmark
    records the overshoot.
    """

    solver_name = "weighted-astar"
    solver_version = "1.0.0"

    def __init__(self, epsilon: float = 2.0) -> None:
        if epsilon < 1.0:
            raise ValueError("epsilon must be at least 1.0")
        self.epsilon = float(epsilon)

    def solve(self, problem: PathProblem, *, trace: bool = False) -> PathResult:
        started = time.perf_counter_ns()
        admissible = straight_line_heuristic(
            problem.graph, problem.destination, problem.objective
        )
        epsilon = self.epsilon

        def heuristic(node: str) -> float:
            return epsilon * admissible(node)

        return astar_search(
            problem,
            heuristic,
            solver_name=f"{self.solver_name}-eps{epsilon:g}",
            solver_version=self.solver_version,
            started_ns=started,
            trace=trace,
        )


class AltPathSolver:
    """A* using ALT landmark bounds instead of the straight line."""

    solver_name = "astar-alt"
    solver_version = "1.0.0"

    def __init__(self, *, landmarks: int = DEFAULT_LANDMARK_COUNT) -> None:
        self._landmark_count = landmarks

    def solve(self, problem: PathProblem, *, trace: bool = False) -> PathResult:
        started = time.perf_counter_ns()
        table = landmark_table(
            problem.graph, objective=problem.objective, count=self._landmark_count
        )
        return astar_search(
            problem,
            table.bound_for(problem.destination),
            solver_name=self.solver_name,
            solver_version=self.solver_version,
            started_ns=started,
            trace=trace,
            preprocessing_time_ns=table.preprocessing_time_ns,
        )


class BidirectionalPathSolver:
    """Balanced two-sided search on ALT-reduced costs.

    Both searches minimise the reduced cost ``c(u, v) + π(v) − π(u)``, which is
    non-negative because the ALT bound is consistent. Every origin→destination
    path has reduced length ``real − π(origin)``, a constant, so minimising one
    minimises the other and the classical bidirectional stopping rule applies:
    stop once ``top_forward + top_backward >= best``, where ``best`` is the
    cheapest meeting so far over every node discovered by both searches.

    ``nodes_expanded`` counts settlements in both directions and
    ``expanded_order`` interleaves them — the work actually done.
    """

    solver_name = "bidirectional-alt"
    solver_version = "1.0.0"

    def __init__(self, *, landmarks: int = DEFAULT_LANDMARK_COUNT) -> None:
        self._landmark_count = landmarks

    def solve(self, problem: PathProblem, *, trace: bool = False) -> PathResult:
        started = time.perf_counter_ns()
        graph = problem.graph
        objective = problem.objective
        table = landmark_table(graph, objective=objective, count=self._landmark_count)
        bound = table.bound_for(problem.destination)
        origin, destination = problem.origin, problem.destination

        if origin == destination:
            distance, seconds = path_totals(graph, (origin,))
            return PathResult(
                node_path=(origin,),
                geometry=geometry_for(graph, (origin,)),
                distance_meters=distance,
                estimated_seconds=seconds,
                solver_name=self.solver_name,
                solver_version=self.solver_version,
                computation_time_ns=time.perf_counter_ns() - started,
                nodes_expanded=0,
                objective=objective,
                preprocessing_time_ns=table.preprocessing_time_ns,
            )

        def forward_step(edge: GraphEdge, node: str) -> float:
            return edge_weight(edge, objective) + bound(edge.to_node) - bound(node)

        def backward_step(edge: GraphEdge, node: str) -> float:
            # ``edge`` is a reverse edge: node → edge.to_node stands in for the
            # real edge edge.to_node → node.
            return edge_weight(edge, objective) + bound(node) - bound(edge.to_node)

        dist_f: dict[str, float] = {origin: 0.0}
        dist_b: dict[str, float] = {destination: 0.0}
        parent_f: dict[str, str] = {}
        parent_b: dict[str, str] = {}
        heap_f: list[tuple[float, str]] = [(0.0, origin)]
        heap_b: list[tuple[float, str]] = [(0.0, destination)]
        settled_f: set[str] = set()
        settled_b: set[str] = set()
        expanded_list: list[str] = []
        frontier_series: list[int] = []
        cost_series: list[float] = []
        expanded = 0
        best = float("inf")
        meeting: str | None = None

        def record(node: str) -> None:
            """Best meeting candidate: any node both searches have discovered."""
            nonlocal best, meeting
            if node in dist_f and node in dist_b:
                candidate = dist_f[node] + dist_b[node]
                if candidate < best:
                    best = candidate
                    meeting = node

        while heap_f and heap_b:
            if heap_f[0][0] + heap_b[0][0] >= best:
                break
            if heap_f[0][0] <= heap_b[0][0]:
                _, node = heapq.heappop(heap_f)
                if node in settled_f:
                    continue
                settled_f.add(node)
                expanded += 1
                if trace:
                    expanded_list.append(node)
                    frontier_series.append(len(heap_f) + len(heap_b))
                    cost_series.append(dist_f[node])
                record(node)
                for edge in graph.neighbors(node):
                    tentative = dist_f[node] + forward_step(edge, node)
                    if tentative < dist_f.get(edge.to_node, float("inf")):
                        dist_f[edge.to_node] = tentative
                        parent_f[edge.to_node] = node
                        heapq.heappush(heap_f, (tentative, edge.to_node))
                        record(edge.to_node)
            else:
                _, node = heapq.heappop(heap_b)
                if node in settled_b:
                    continue
                settled_b.add(node)
                expanded += 1
                if trace:
                    expanded_list.append(node)
                    frontier_series.append(len(heap_f) + len(heap_b))
                    cost_series.append(dist_b[node])
                record(node)
                for edge in graph.reverse_neighbors(node):
                    tentative = dist_b[node] + backward_step(edge, node)
                    if tentative < dist_b.get(edge.to_node, float("inf")):
                        dist_b[edge.to_node] = tentative
                        parent_b[edge.to_node] = node
                        heapq.heappush(heap_b, (tentative, edge.to_node))
                        record(edge.to_node)

        if meeting is None:
            raise ValueError(f"No path from {origin} to {destination}")
        node_path = _stitch(parent_f, parent_b, origin, meeting, destination)
        distance, seconds = path_totals(graph, node_path)
        return PathResult(
            node_path=node_path,
            geometry=geometry_for(graph, node_path),
            distance_meters=distance,
            estimated_seconds=seconds,
            solver_name=self.solver_name,
            solver_version=self.solver_version,
            computation_time_ns=time.perf_counter_ns() - started,
            nodes_expanded=expanded,
            objective=objective,
            expanded_order=tuple(expanded_list) if trace else (),
            frontier_sizes=tuple(frontier_series) if trace else (),
            expansion_costs=tuple(cost_series) if trace else (),
            preprocessing_time_ns=table.preprocessing_time_ns,
        )


def _stitch(
    parent_f: dict[str, str],
    parent_b: dict[str, str],
    origin: str,
    meeting: str,
    destination: str,
) -> tuple[str, ...]:
    """Join the forward half (origin → meeting) with the backward half."""
    forward = [meeting]
    while forward[-1] != origin:
        parent = parent_f.get(forward[-1])
        if parent is None:
            raise ValueError("Forward half of the path is incomplete")
        forward.append(parent)
    forward.reverse()
    backward = [meeting]
    while backward[-1] != destination:
        successor = parent_b.get(backward[-1])
        if successor is None:
            raise ValueError("Backward half of the path is incomplete")
        backward.append(successor)
    return tuple(forward + backward[1:])
