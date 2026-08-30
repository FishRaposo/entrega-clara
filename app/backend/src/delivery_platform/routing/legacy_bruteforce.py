"""The deliberately retained brute-force TSP legacy baseline."""

from itertools import pairwise, permutations
from time import perf_counter_ns

from .models import RouteHistoryEntry, RouteProblem, RouteResult


class LegacyBruteForceTSPSolver:
    """Exactly solve small complete matrices by the original permutation algorithm.

    This class is retained as a portfolio comparison baseline, not as a production
    dispatch strategy. It intentionally fixes the route origin at index zero.
    """

    solver_name = "legacy_bruteforce_tsp"

    def __init__(self, *, keep_history: bool = False) -> None:
        self._keep_history = keep_history

    def solve(self, problem: RouteProblem) -> RouteResult:
        """Evaluate every non-origin permutation and return the least-cost route."""
        if not isinstance(problem, RouteProblem):
            raise ValueError("Legacy solver requires a valid RouteProblem")  # noqa: TRY004
        if problem.origin_index != 0:
            raise ValueError("Legacy solver requires origin_index to be zero")

        origin = problem.origin_index
        non_origin_indices = tuple(index for index in range(len(problem.labels)) if index != origin)
        best_route: tuple[int, ...] | None = None
        best_cost: float | None = None
        route_history: list[RouteHistoryEntry] | None = [] if self._keep_history else None
        routes_evaluated = 0

        started_at = perf_counter_ns()
        for permutation in permutations(non_origin_indices):
            route_indices = (origin, *permutation, origin)
            route_cost = float(
                sum(problem.costs[start][end] for start, end in pairwise(route_indices))
            )
            routes_evaluated += 1

            if route_history is not None:
                route_history.append(
                    {
                        "route": tuple(problem.labels[index] for index in route_indices),
                        "cost": route_cost,
                    }
                )
            if best_cost is None or route_cost < best_cost:
                best_cost = route_cost
                best_route = route_indices
        execution_time_ns = perf_counter_ns() - started_at

        if best_route is None or best_cost is None:
            raise ValueError("Legacy solver could not evaluate a route")

        return RouteResult(
            route=tuple(problem.labels[index] for index in best_route),
            total_cost=best_cost,
            solver_name=self.solver_name,
            execution_time_ns=execution_time_ns,
            routes_evaluated=routes_evaluated,
            route_history=tuple(route_history) if route_history is not None else None,
        )
