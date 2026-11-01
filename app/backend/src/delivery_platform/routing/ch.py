"""Contraction-hierarchy solver behind the same contract as every other rung.

The product deliberately keeps plain A*: it needs no preprocessing, and a
delivery dispatcher that plans one route at a time cannot amortize a minute of
contraction. CH is the answer when the same graph is queried thousands of times,
which is exactly what the benchmark's break-even table quantifies.
"""

from __future__ import annotations

import time

from delivery_platform.routing.contraction import (
    DEFAULT_SETTLE_LIMIT,
    CHGraph,
    preprocess,
)
from delivery_platform.routing.graph import StreetGraph
from delivery_platform.routing.path import (
    Objective,
    PathProblem,
    PathResult,
    geometry_for,
    path_totals,
)

_CACHE: dict[tuple[int, str, int], CHGraph] = {}
_GRAPH_REFS: dict[int, StreetGraph] = {}


def contraction_hierarchy(
    graph: StreetGraph,
    *,
    objective: Objective = "time",
    settle_limit: int = DEFAULT_SETTLE_LIMIT,
) -> CHGraph:
    """Cached hierarchy: preprocessing is paid once per graph, objective and limit."""
    key = (id(graph), objective, settle_limit)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    hierarchy = preprocess(graph, objective=objective, settle_limit=settle_limit)
    # Hold a reference so the cached id() cannot be reused by another object.
    _GRAPH_REFS[id(graph)] = graph
    _CACHE[key] = hierarchy
    return hierarchy


class ChPathSolver:
    """Exact queries over a contraction hierarchy (per objective)."""

    solver_name = "contraction-hierarchy"
    solver_version = "1.0.0"

    def __init__(self, *, settle_limit: int = DEFAULT_SETTLE_LIMIT) -> None:
        self._settle_limit = settle_limit

    def solve(self, problem: PathProblem, *, trace: bool = False) -> PathResult:
        started = time.perf_counter_ns()
        hierarchy = contraction_hierarchy(
            problem.graph,
            objective=problem.objective,
            settle_limit=self._settle_limit,
        )
        found = hierarchy.shortest_path(problem.origin, problem.destination, trace=trace)
        if found is None:
            raise ValueError(f"No path from {problem.origin} to {problem.destination}")
        node_path = tuple(found.nodes)
        distance, seconds = path_totals(problem.graph, node_path)
        return PathResult(
            node_path=node_path,
            geometry=geometry_for(problem.graph, node_path),
            distance_meters=distance,
            estimated_seconds=seconds,
            solver_name=self.solver_name,
            solver_version=self.solver_version,
            computation_time_ns=time.perf_counter_ns() - started,
            nodes_expanded=found.settled,
            objective=problem.objective,
            expanded_order=found.settle_order if trace else (),
            preprocessing_time_ns=hierarchy.stats.preprocessing_time_ns,
        )
