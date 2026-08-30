"""Protocol shared by routing implementations."""

from typing import Protocol

from .models import RouteProblem, RouteResult


class RouteSolver(Protocol):
    """Solves a route problem without exposing an implementation choice."""

    def solve(self, problem: RouteProblem) -> RouteResult:
        """Return a route result for ``problem``."""
