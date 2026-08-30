"""Typed routing inputs and outputs that are independent of solver choice."""

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import TypedDict


class RouteHistoryEntry(TypedDict):
    """One evaluated closed route retained for a bounded experiment."""

    route: tuple[str, ...]
    cost: float


@dataclass(frozen=True)
class RouteProblem:
    """A complete travel-cost matrix and the index of its route origin."""

    labels: tuple[str, ...]
    costs: tuple[tuple[Real, ...], ...]
    origin_index: int = 0

    def __post_init__(self) -> None:
        try:
            labels = tuple(self.labels)
            costs = tuple(tuple(row) for row in self.costs)
        except TypeError as error:
            raise ValueError("Route labels and cost rows must be iterable") from error
        object.__setattr__(self, "labels", labels)
        object.__setattr__(self, "costs", costs)

        label_count = len(self.labels)
        if label_count < 2:
            raise ValueError("RouteProblem requires at least two labels")
        if not isinstance(self.origin_index, int) or isinstance(self.origin_index, bool):
            raise ValueError("origin_index must be an integer")  # noqa: TRY004
        if not 0 <= self.origin_index < label_count:
            raise ValueError("origin_index must reference a label")

        matrix_size = len(self.costs)
        if matrix_size != label_count:
            raise ValueError("Cost matrix dimensions must equal the label count")

        for row in self.costs:
            if len(row) != label_count:
                raise ValueError("Cost matrix must be square")
            for cost in row:
                if isinstance(cost, bool) or not isinstance(cost, Real) or not isfinite(cost):
                    raise ValueError("Costs must be finite numeric values")
                if cost < 0:
                    raise ValueError("Costs must not be negative")


@dataclass(frozen=True)
class RouteResult:
    """A solver's closed route and computation metadata."""

    route: tuple[str, ...]
    total_cost: float
    solver_name: str
    execution_time_ns: int
    routes_evaluated: int
    route_history: tuple[RouteHistoryEntry, ...] | None = None
