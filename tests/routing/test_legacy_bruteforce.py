import pytest
from delivery_platform.routing.legacy_bruteforce import LegacyBruteForceTSPSolver
from delivery_platform.routing.models import RouteProblem

MATRIX = (
    (0, 10, 15, 20, 25),
    (10, 0, 35, 25, 30),
    (15, 35, 0, 30, 20),
    (20, 25, 30, 0, 15),
    (25, 30, 20, 15, 0),
)


def test_legacy_solver_finds_the_known_optimal_distance():
    result = LegacyBruteForceTSPSolver().solve(
        RouteProblem(labels=("A", "B", "C", "D", "E"), costs=MATRIX)
    )

    assert result.total_cost == 85
    assert result.route[0] == "A"
    assert result.route[-1] == "A"
    assert len(result.route) == 6
    assert result.routes_evaluated == 24
    assert set(result.route) == {"A", "B", "C", "D", "E"}


def test_legacy_solver_can_retain_route_history_for_small_experiments():
    result = LegacyBruteForceTSPSolver(keep_history=True).solve(
        RouteProblem(labels=("A", "B", "C"), costs=((0, 2, 5), (2, 0, 1), (5, 1, 0)))
    )

    assert len(result.route_history) == 2
    assert all("route" in item and "cost" in item for item in result.route_history)


def test_legacy_solver_keeps_the_first_route_when_costs_tie():
    result = LegacyBruteForceTSPSolver().solve(
        RouteProblem(labels=("A", "B", "C"), costs=((0, 1, 1), (1, 0, 1), (1, 1, 0)))
    )

    assert result.route == ("A", "B", "C", "A")


def test_legacy_solver_rejects_a_nonzero_origin():
    problem = RouteProblem(
        labels=("A", "B", "C"),
        costs=((0, 1, 1), (1, 0, 1), (1, 1, 0)),
        origin_index=1,
    )

    with pytest.raises(ValueError, match="origin_index"):
        LegacyBruteForceTSPSolver().solve(problem)


def test_legacy_solver_reports_computation_timing_without_history_by_default():
    result = LegacyBruteForceTSPSolver().solve(
        RouteProblem(labels=("A", "B"), costs=((0, 4), (4, 0)))
    )

    assert isinstance(result.execution_time_ns, int)
    assert result.execution_time_ns >= 0
    assert result.route_history is None
