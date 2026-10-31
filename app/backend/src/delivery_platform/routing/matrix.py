"""Build a ``RouteProblem`` cost matrix from graph path solving.

This is the bridge between the two contracts: point-to-point pathfinding
produces the real travel costs; the matrix then lets any ``RouteSolver``
optimize the stop order on identical numbers.
"""

from __future__ import annotations

from collections.abc import Callable
from numbers import Real
from typing import cast

from delivery_platform.routing.graph import StreetGraph
from delivery_platform.routing.models import RouteProblem
from delivery_platform.routing.path import (
    AStarPathSolver,
    PathProblem,
    PathResult,
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
    solve = solver if solver is not None else AStarPathSolver().solve
    metric = "estimated_seconds" if objective == "time" else "distance_meters"
    def cell(a: int, b: int) -> float:
        if a == b:
            return 0.0
        return float(
            getattr(
                solve(PathProblem(graph, nodes[a], nodes[b], objective)),  # type: ignore[arg-type]
                metric,
            )
        )

    costs: list[list[float]] = [
        [cell(a, b) for b in range(len(nodes))]
        for a in range(len(nodes))
    ]
    return RouteProblem(
        labels=labels,
        costs=cast("tuple[tuple[Real, ...], ...]", tuple(tuple(r) for r in costs)),
        origin_index=origin_index,
        objective=objective,  # type: ignore[arg-type]
    )
