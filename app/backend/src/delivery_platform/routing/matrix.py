"""Build a ``RouteProblem`` cost matrix from graph path solving.

This is the bridge between the two contracts: point-to-point pathfinding
produces the real travel costs; the matrix then lets any ``RouteSolver``
optimize the stop order on identical numbers.

The default builder runs one-to-all Dijkstra from each distinct stop (n runs)
instead of A* for every ordered pair (n² runs). A* wins when a single
destination is asked for; Dijkstra wins when every destination is needed at
once — a batch matrix asks for all of them. Passing ``solver`` restores the
pairwise behaviour, which the tests use to prove both builders agree.
"""

from __future__ import annotations

from collections.abc import Callable
from numbers import Real
from typing import cast

from delivery_platform.routing.graph import StreetGraph
from delivery_platform.routing.models import RouteProblem
from delivery_platform.routing.path import (
    Objective,
    PathProblem,
    PathResult,
    distances_from,
)

PathSolverFn = Callable[[PathProblem], PathResult]


def build_cost_matrix(
    graph: StreetGraph,
    labels: tuple[str, ...],
    nodes: tuple[str, ...],
    *,
    objective: str = "time",
    origin_index: int = 0,
    solver: PathSolverFn | None = None,
) -> RouteProblem:
    """Solve every pair path on ``objective`` cost and return a RouteProblem.

    ``labels[i]`` names stop ``nodes[i]`` (usually the snapped graph node for a
    real location). The caller's ``origin_index`` marks the courier start.
    """

    if len(labels) != len(nodes):
        raise ValueError("labels and nodes must have the same length")
    if len(nodes) < 2:
        raise ValueError("cost matrix needs at least two nodes")
    if objective not in ("time", "distance"):
        raise ValueError(f"Unknown objective {objective}")

    metric = cast("Objective", objective)
    if solver is None:
        costs = _dijkstra_costs(graph, nodes, metric)
    else:
        costs = _pairwise_costs(graph, nodes, metric, solver)

    return RouteProblem(
        labels=labels,
        costs=cast("tuple[tuple[Real, ...], ...]", tuple(tuple(row) for row in costs)),
        origin_index=origin_index,
        objective=objective,
    )


def _dijkstra_costs(
    graph: StreetGraph, nodes: tuple[str, ...], objective: Objective
) -> list[list[float]]:
    """n one-to-all searches instead of n² point-to-point searches."""
    tables: dict[str, dict[str, float]] = {}
    rows: list[list[float]] = []
    for source in nodes:
        table = tables.get(source)
        if table is None:
            table = distances_from(graph, source, objective)
            tables[source] = table
        row: list[float] = []
        for target in nodes:
            cost = table.get(target)
            if cost is None:
                raise ValueError(f"No path from {source} to {target}")
            row.append(float(cost))
        rows.append(row)
    return rows


def _pairwise_costs(
    graph: StreetGraph,
    nodes: tuple[str, ...],
    objective: Objective,
    solver: PathSolverFn,
) -> list[list[float]]:
    metric = "estimated_seconds" if objective == "time" else "distance_meters"

    def cell(a: int, b: int) -> float:
        if a == b:
            return 0.0
        return float(getattr(solver(PathProblem(graph, nodes[a], nodes[b], objective)), metric))

    return [[cell(a, b) for b in range(len(nodes))] for a in range(len(nodes))]
