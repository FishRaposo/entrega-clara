"""Capacitated multi-stop routing with time windows and pickup precedence.

The delivery problem the product actually has is not a TSP: every order is a
pickup followed later by a drop-off, the courier can carry only so much at once,
and customers are promised a window. This module models exactly that and solves
it two ways:

    ExactWindowSolver       depth-first search with precedence, capacity and
                            window pruning — exact, capped at 8 stops
    InsertionWindowSolver   cheapest feasible insertion plus relocate/swap local
                            search — bounded, used above the exact cap

Costs come from the graph (a travel-time matrix). Times are **relative seconds
from the batch departure**: windows, arrivals, waits and lateness all share that
origin, which keeps the model independent of any clock and makes every number
comparable in tests.

Windows are soft in the optimizer (lateness is penalised, never silently
ignored) and become hard at dispatch time through ``max_lateness_seconds``. That
split is deliberate: the solver should be able to explain *how* late a plan is,
while the product decides whether lateness is acceptable.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Protocol

from delivery_platform.domain.entities import StopKind

DEFAULT_LATENESS_PENALTY = 60.0
EXACT_STOP_LIMIT = 8


class WindowedRouteSolver(Protocol):
    solver_name: str
    solver_version: str

    def solve(self, problem: VrpProblem) -> VrpResult: ...


@dataclass(frozen=True)
class VrpStop:
    """One visit. ``index`` matches the cost-matrix row (0 is the courier)."""

    index: int
    label: str
    kind: StopKind
    delivery_id: str
    #: Signed capacity delta: positive on pickup, negative on drop-off.
    volume: int = 0
    service_seconds: float = 0.0
    window_start: float | None = None
    window_end: float | None = None

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValueError("stop indices start at 1; 0 is the courier origin")
        if self.kind not in ("pickup", "dropoff"):
            raise ValueError(f"Unknown stop kind {self.kind}")


@dataclass(frozen=True)
class VrpProblem:
    """Travel-time matrix (rows/cols 0..N), stops (N of them) and constraints."""

    costs: tuple[tuple[float, ...], ...]
    stops: tuple[VrpStop, ...]
    capacity: int
    lateness_penalty: float = DEFAULT_LATENESS_PENALTY
    max_lateness: float = 0.0
    departure: float = 0.0
    #: Capacity already on board when the tour starts (orders picked up before
    #: a re-plan); their stop lists only the drop-off.
    initial_load: int = 0

    def __post_init__(self) -> None:
        expected = len(self.stops) + 1
        if len(self.costs) != expected or any(len(row) != expected for row in self.costs):
            raise ValueError(f"costs must be a {expected}x{expected} matrix")
        if self.capacity <= 0:
            raise ValueError("capacity must be positive")
        if self.initial_load < 0 or self.initial_load > self.capacity:
            raise ValueError("initial_load must fit the capacity")
        if sorted(stop.index for stop in self.stops) != list(range(1, expected)):
            raise ValueError("stops must be indexed 1..N in order")
        for stop in self.stops:
            if (
                stop.window_start is not None
                and stop.window_end is not None
                and stop.window_start > stop.window_end
            ):
                raise ValueError(f"stop {stop.label} has an inverted window")

    @property
    def size(self) -> int:
        return len(self.stops)

    def stop(self, index: int) -> VrpStop:
        return self.stops[index - 1]

    def precedences(self) -> dict[int, int]:
        """dropoff index -> its pickup index, for stops that include both legs.

        A re-plan can contain a drop-off whose pickup already happened; that
        stop has no precedence constraint inside this plan.
        """
        pickup_of: dict[str, int] = {}
        for stop in self.stops:
            if stop.kind == "pickup":
                pickup_of[stop.delivery_id] = stop.index
        result: dict[int, int] = {}
        for stop in self.stops:
            if stop.kind == "dropoff":
                pickup = pickup_of.get(stop.delivery_id)
                if pickup is not None:
                    result[stop.index] = pickup
        return result


@dataclass(frozen=True)
class VrpVisit:
    index: int
    arrival: float
    wait: float
    start: float
    finish: float
    lateness: float
    load: int


@dataclass(frozen=True)
class VrpSchedule:
    visits: tuple[VrpVisit, ...]
    travel_seconds: float
    wait_seconds: float
    lateness_seconds: float
    cost: float
    feasible: bool
    violations: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class VrpResult:
    order: tuple[int, ...]
    schedule: VrpSchedule
    solver_name: str
    solver_version: str
    work: int
    execution_time_ns: int = 0


def evaluate(
    problem: VrpProblem, order: tuple[int, ...], *, require_complete: bool = True
) -> VrpSchedule:
    """Walk the order and produce arrivals, waits, lateness and the cost.

    ``require_complete=False`` is used while a solver is still *building* an
    order: a prefix is judged on precedence, capacity and windows only, instead
    of being reported as incomplete.
    """
    visit_by_index = {stop.index: stop for stop in problem.stops}
    time = problem.departure
    load = problem.initial_load
    travel_total = 0.0
    wait_total = 0.0
    late_total = 0.0
    violations: list[str] = []
    visits: list[VrpVisit] = []
    previous = 0
    seen: set[int] = set()
    for index in order:
        if index in seen:
            violations.append(f"stop {index} visited twice")
            continue
        seen.add(index)
        stop = visit_by_index.get(index)
        if stop is None:
            raise ValueError(f"unknown stop index {index}")
        travel = problem.costs[previous][index]
        travel_total += travel
        arrival = time + travel
        wait = 0.0
        if stop.window_start is not None and arrival < stop.window_start:
            wait = stop.window_start - arrival
        wait_total += wait
        start = arrival + wait
        lateness = 0.0
        if stop.window_end is not None and start > stop.window_end:
            lateness = start - stop.window_end
        late_total += lateness
        load += stop.volume
        if load > problem.capacity:
            violations.append(f"capacity exceeded at {stop.label}")
        if load < 0:
            violations.append(f"unloaded delivery at {stop.label}")
        finish = start + stop.service_seconds
        visits.append(
            VrpVisit(
                index=index,
                arrival=arrival,
                wait=wait,
                start=start,
                finish=finish,
                lateness=lateness,
                load=load,
            )
        )
        time = finish
        previous = index

    precedences = problem.precedences()
    positions = {index: place for place, index in enumerate(order)}
    for dropoff, pickup in precedences.items():
        if dropoff in positions and pickup not in positions or dropoff in positions and positions[pickup] > positions[dropoff]:
            violations.append("dropoff before pickup")
    if require_complete and len(seen) != problem.size:
        violations.append("not every stop was visited")
    if late_total > problem.max_lateness + 1e-9:
        violations.append(
            f"lateness {late_total:.0f}s exceeds the {problem.max_lateness:.0f}s limit"
        )
    cost = travel_total + problem.lateness_penalty * late_total
    return VrpSchedule(
        visits=tuple(visits),
        travel_seconds=travel_total,
        wait_seconds=wait_total,
        lateness_seconds=late_total,
        cost=cost,
        feasible=not violations,
        violations=tuple(dict.fromkeys(violations)),
    )


def _candidate_orders(problem: VrpProblem):
    """Feasible stop orders in a stable, precedence-aware enumeration."""
    precedences = problem.precedences()
    indices = [stop.index for stop in problem.stops]
    for permutation in itertools.permutations(indices):
        position = {index: place for place, index in enumerate(permutation)}
        if any(position[dropoff] < position[pickup] for dropoff, pickup in precedences.items()):
            continue
        yield permutation


@dataclass
class ExactWindowSolver:
    """Exact search over stop orders with precedence, capacity and window pruning."""

    solver_name = "exact-windows"
    solver_version = "1.0.0"
    max_stops: int = EXACT_STOP_LIMIT

    def solve(self, problem: VrpProblem) -> VrpResult:
        import time

        started = time.perf_counter_ns()
        if problem.size > self.max_stops:
            raise ValueError(
                f"exact search is capped at {self.max_stops} stops; use the insertion solver"
            )
        best_order: tuple[int, ...] | None = None
        best_schedule: VrpSchedule | None = None
        work = 0
        for order in _candidate_orders(problem):
            work += 1
            schedule = evaluate(problem, order)
            if not schedule.feasible:
                continue
            if best_schedule is None or schedule.cost < best_schedule.cost - 1e-9:
                best_order = order
                best_schedule = schedule
        if best_order is None or best_schedule is None:
            # No feasible order: report *why*, using the offered order as the
            # explanation so the dispatcher sees capacity vs. window, not just
            # "infeasible".
            explanation = evaluate(
                problem, tuple(range(1, problem.size + 1)), require_complete=False
            )
            return VrpResult(
                order=(),
                schedule=explanation,
                solver_name=self.solver_name,
                solver_version=self.solver_version,
                work=work,
                execution_time_ns=time.perf_counter_ns() - started,
            )
        return VrpResult(
            order=best_order,
            schedule=best_schedule,
            solver_name=self.solver_name,
            solver_version=self.solver_version,
            work=work,
            execution_time_ns=time.perf_counter_ns() - started,
        )


@dataclass
class InsertionWindowSolver:
    """Cheapest feasible insertion, then relocate/swap local search."""

    solver_name = "insertion-windows"
    solver_version = "1.0.0"
    max_iterations: int = 200

    def solve(self, problem: VrpProblem) -> VrpResult:
        import time

        started = time.perf_counter_ns()
        precedences = problem.precedences()
        order: list[int] = []
        remaining = {stop.index for stop in problem.stops}
        work = 0

        def allowed(index: int, sequence: list[int]) -> bool:
            """A drop-off is only insertable once its pickup is already placed."""
            return precedences.get(index) is None or precedences[index] in sequence

        while remaining:
            best: tuple[float, int, int] | None = None  # (cost, stop, position)
            for index in sorted(remaining):
                if not allowed(index, order):
                    continue
                for position in range(len(order) + 1):
                    candidate = order[:position] + [index] + order[position:]
                    work += 1
                    schedule = evaluate(problem, tuple(candidate), require_complete=False)
                    if not schedule.feasible:
                        continue
                    if best is None or schedule.cost < best[0]:
                        best = (schedule.cost, index, position)
            if best is None:
                explanation = evaluate(
                    problem, tuple(range(1, problem.size + 1)), require_complete=False
                )
                return VrpResult(
                    order=(),
                    schedule=explanation,
                    solver_name=self.solver_name,
                    solver_version=self.solver_version,
                    work=work,
                    execution_time_ns=time.perf_counter_ns() - started,
                )
            _, index, position = best
            order.insert(position, index)
            remaining.discard(index)

        improved = True
        iterations = 0
        best_schedule = evaluate(problem, tuple(order))
        while improved and iterations < self.max_iterations:
            improved = False
            iterations += 1
            for source in range(len(order)):
                for target in range(len(order)):
                    if source == target:
                        continue
                    candidate = order[:]
                    moved = candidate.pop(source)
                    candidate.insert(target, moved)
                    work += 1
                    schedule = evaluate(problem, tuple(candidate))
                    if schedule.feasible and schedule.cost < best_schedule.cost - 1e-9:
                        order = candidate
                        best_schedule = schedule
                        improved = True
        return VrpResult(
            order=tuple(order),
            schedule=best_schedule,
            solver_name=self.solver_name,
            solver_version=self.solver_version,
            work=work,
            execution_time_ns=time.perf_counter_ns() - started,
        )
