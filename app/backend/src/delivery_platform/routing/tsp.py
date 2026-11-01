"""Multi-stop route solvers behind the shared ``RouteSolver`` contract.

Answers the project's origin question — what replaces the brute-force TSP the
college baseline used — with one exact and two heuristic strategies, all
bounded and comparable on the same ``RouteProblem`` input.

Work counters (``routes_evaluated``) mean different things per solver:
brute force counts permutations, Held-Karp counts DP states, nearest-neighbor
counts candidate evaluations, and 2-opt counts considered improving moves.
"""

from __future__ import annotations

from itertools import pairwise
from time import perf_counter_ns

from delivery_platform.domain.errors import DomainError
from delivery_platform.routing.models import RouteProblem, RouteResult


class RouteTooLargeError(DomainError):
    code = "route_too_large"
    http_status = 400

    def __init__(self, solver: str, limit: int) -> None:
        super().__init__(
            f"Esta rota excede o limite do solver {solver} ({limit} paradas)."
        )


def _tour_cost(problem: RouteProblem, order: tuple[int, ...]) -> float:
    cost = 0.0
    for a, b in pairwise(order):
        cost += float(problem.costs[a][b])
    return cost


def _labels(problem: RouteProblem, order: tuple[int, ...]) -> tuple[str, ...]:
    return tuple(problem.labels[i] for i in order)


def _closed(order: tuple[int, ...], origin: int) -> tuple[int, ...]:
    return (origin, *order, origin)


class HeldKarpSolver:
    """Exact TSP via bitmask dynamic programming — O(n²·2ⁿ) time, O(n·2ⁿ) memory.

    Optional ``precedence`` maps a stop index that must be visited to the index
    it must follow (e.g. drop-off → pickup); transitions violating it are
    skipped.
    """

    solver_name = "held-karp"
    MAX_STOPS = 18

    def __init__(
        self,
        *,
        precedence: dict[int, int] | None = None,
        closed: bool = True,
    ) -> None:
        self._precedence = precedence or {}
        self._closed = closed

    def solve(self, problem: RouteProblem) -> RouteResult:
        n = len(problem.labels)
        if n > self.MAX_STOPS:
            raise RouteTooLargeError(self.solver_name, self.MAX_STOPS)
        origin = problem.origin_index
        others = [i for i in range(n) if i != origin]
        m = len(others)
        idx = {city: pos for pos, city in enumerate(others)}
        precedence = {
            idx[after]: idx[before]
            for after, before in self._precedence.items()
            if after in idx and before in idx
        }
        costs = problem.costs
        size = 1 << m
        # dp[mask][j] = min cost from origin visiting mask ending at others[j]
        dp: list[list[float]] = [[float("inf")] * m for _ in range(size)]
        parent: list[list[int]] = [[-1] * m for _ in range(size)]
        evaluated = 0
        started = perf_counter_ns()
        for j in range(m):
            dp[1 << j][j] = float(costs[origin][others[j]])
        for mask in range(size):
            for j in range(m):
                if not (mask >> j) & 1 or dp[mask][j] == float("inf"):
                    continue
                for k in range(m):
                    if (mask >> k) & 1:
                        continue
                    # cannot visit k before its prerequisite is visited
                    if k in precedence and not (mask >> precedence[k]) & 1:
                        continue
                    evaluated += 1
                    candidate = dp[mask][j] + float(costs[others[j]][others[k]])
                    nmask = mask | (1 << k)
                    if candidate < dp[nmask][k]:
                        dp[nmask][k] = candidate
                        parent[nmask][k] = j
        full = size - 1
        best_end, best_cost = -1, float("inf")
        for j in range(m):
            if dp[full][j] == float("inf"):
                continue
            # closed tours return to the origin; open tours (delivery batches)
            # end at the last stop.
            candidate = dp[full][j]
            if self._closed:
                candidate += float(costs[others[j]][origin])
            evaluated += 1
            if candidate < best_cost:
                best_cost, best_end = candidate, j
        if best_end < 0:
            raise ValueError("Held-Karp could not complete a tour")
        order: list[int] = []
        mask, j = full, best_end
        while j >= 0:
            order.append(others[j])
            mask, j = mask ^ (1 << j), parent[mask][j]
        order.reverse()
        tour = _closed(tuple(order), origin) if self._closed else (origin, *order)
        return RouteResult(
            route=_labels(problem, tour),
            total_cost=best_cost,
            solver_name=self.solver_name,
            execution_time_ns=perf_counter_ns() - started,
            routes_evaluated=evaluated,
        )


class NearestNeighborSolver:
    """Greedy tour: always extend to the closest *eligible* unvisited stop.

    Optional ``precedence`` (stop index → required predecessor index) excludes
    candidates whose prerequisite has not been visited yet.
    """

    solver_name = "nearest-neighbor"

    def __init__(
        self,
        *,
        precedence: dict[int, int] | None = None,
        closed: bool = True,
    ) -> None:
        self._precedence = precedence or {}
        self._closed = closed

    def solve(self, problem: RouteProblem) -> RouteResult:
        n = len(problem.labels)
        started = perf_counter_ns()
        origin = problem.origin_index
        unvisited = set(range(n)) - {origin}
        order = [origin]
        evaluated = 0
        current = origin
        while unvisited:
            eligible = [
                c
                for c in unvisited
                if c not in self._precedence
                or self._precedence[c] in order
            ]
            if not eligible:
                raise ValueError("Precedence constraints left no valid next stop")
            nxt = min(
                eligible,
                key=lambda c: float(problem.costs[current][c]),
            )
            evaluated += len(eligible)
            unvisited.remove(nxt)
            order.append(nxt)
            current = nxt
        order.append(origin)
        return RouteResult(
            route=_labels(problem, tuple(order)),
            total_cost=_tour_cost(problem, tuple(order)),
            solver_name=self.solver_name,
            execution_time_ns=perf_counter_ns() - started,
            routes_evaluated=evaluated,
        )


class TwoOptSolver:
    """2-opt improvement over a nearest-neighbor seed to a local optimum.

    Optional ``precedence`` (drop-off → pickup index) rejects any move that
    would invert a required order pair.
    """

    solver_name = "two-opt"

    def __init__(
        self,
        *,
        seed: NearestNeighborSolver | None = None,
        precedence: dict[int, int] | None = None,
    ) -> None:
        self._seed = seed or NearestNeighborSolver(precedence=precedence)
        self._precedence = precedence or {}

    def solve(self, problem: RouteProblem) -> RouteResult:
        started = perf_counter_ns()
        seed_result = self._seed.solve(problem)
        label_index = {label: i for i, label in enumerate(problem.labels)}
        tour = [label_index[label] for label in seed_result.route]
        # tour includes the origin twice (first/last); work on the open order.
        order = tour[1:-1]
        origin = problem.origin_index
        n = len(order)
        evaluated = seed_result.routes_evaluated

        def respects_precedence(candidate: list[int]) -> bool:
            if not self._precedence:
                return True
            position = {city: pos for pos, city in enumerate(candidate)}
            return all(
                position.get(after, -1) > position.get(before, -1)
                for after, before in self._precedence.items()
                if after in position and before in position
            )

        improved = True
        while improved:
            improved = False
            for i in range(n - 1):
                for j in range(i + 1, n):
                    candidate = order[:i] + order[i : j + 1][::-1] + order[j + 1 :]
                    if not respects_precedence(candidate):
                        continue
                    before_cost = _tour_cost(
                        problem, _closed(tuple(order), origin)
                    )
                    after_cost = _tour_cost(
                        problem, _closed(tuple(candidate), origin)
                    )
                    evaluated += 1
                    if after_cost < before_cost - 1e-9:
                        order = candidate
                        improved = True
        return RouteResult(
            route=_labels(problem, _closed(tuple(order), origin)),
            total_cost=_tour_cost(problem, _closed(tuple(order), origin)),
            solver_name=self.solver_name,
            execution_time_ns=perf_counter_ns() - started,
            routes_evaluated=evaluated,
        )
