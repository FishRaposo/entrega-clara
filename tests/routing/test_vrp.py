"""VRP core: capacity, windows, precedence and both solvers."""

import pytest
from delivery_platform.routing.vrp import (
    ExactWindowSolver,
    InsertionWindowSolver,
    VrpProblem,
    VrpStop,
    evaluate,
)

# 0 = courier, 1/2 = pickup/drop-off of A, 3/4 = pickup/drop-off of B.
COSTS = (
    (0, 100, 120, 200, 220),
    (100, 0, 20, 120, 140),
    (120, 20, 0, 100, 120),
    (200, 120, 100, 0, 20),
    (220, 140, 120, 20, 0),
)


def _problem(**overrides) -> VrpProblem:
    stops = (
        VrpStop(1, "Cantina", "pickup", "A", volume=1),
        VrpStop(2, "Rua A", "dropoff", "A", volume=-1),
        VrpStop(3, "Padaria", "pickup", "B", volume=1),
        VrpStop(4, "Rua B", "dropoff", "B", volume=-1),
    )
    fields = {"costs": COSTS, "stops": stops, "capacity": 1}
    fields.update(overrides)
    return VrpProblem(**fields)


def test_capacity_forces_one_delivery_at_a_time():
    problem = _problem(capacity=1)
    result = ExactWindowSolver().solve(problem)
    assert result.order == (1, 2, 3, 4)
    assert result.schedule.feasible
    assert result.schedule.travel_seconds == pytest.approx(240)
    assert [visit.load for visit in result.schedule.visits] == [1, 0, 1, 0]


def test_larger_capacity_finds_a_shorter_tour():
    problem = _problem(capacity=2)
    result = ExactWindowSolver().solve(problem)
    assert result.schedule.feasible
    # Carrying both: 0→1→3→2→4 = 100 + 120 + 100 + 120 = 440? No: 0→1=100,
    # 1→3=120, 3→2=100, 2→4=120 → 440; the interleaved order 0→1→3→4→2 is
    # worse. The optimum is the pickup-pair order 0→1→2→4→3? 100+20+120+100=340
    # — but that delivers B's drop at 4 before picking B up, which precedence
    # forbids, so the cheapest allowed tour is 0→1→3→2→4 (440) or 0→1→2→3→4
    # (240, capacity 1). With capacity 2 both are allowed; 240 wins.
    assert result.schedule.travel_seconds == pytest.approx(240)


def test_waiting_for_a_window_and_its_arithmetic():
    stops = (
        VrpStop(1, "Cantina", "pickup", "A", volume=1, window_start=150),
        VrpStop(2, "Rua A", "dropoff", "A", volume=-1),
        VrpStop(3, "Padaria", "pickup", "B", volume=1),
        VrpStop(4, "Rua B", "dropoff", "B", volume=-1),
    )
    schedule = evaluate(_problem(stops=stops, capacity=2), (1, 2, 3, 4))
    first = schedule.visits[0]
    assert first.arrival == pytest.approx(100)
    assert first.wait == pytest.approx(50)
    assert first.start == pytest.approx(150)
    assert schedule.wait_seconds == pytest.approx(50)
    assert schedule.lateness_seconds == 0


def test_lateness_is_reported_and_penalised():
    stops = (
        VrpStop(1, "Cantina", "pickup", "A", volume=1),
        VrpStop(2, "Rua A", "dropoff", "A", volume=-1, window_end=50),
        VrpStop(3, "Padaria", "pickup", "B", volume=1),
        VrpStop(4, "Rua B", "dropoff", "B", volume=-1),
    )
    problem = _problem(stops=stops, capacity=2, max_lateness=0)
    schedule = evaluate(problem, (1, 2, 3, 4))
    assert schedule.visits[1].arrival == pytest.approx(120)
    assert schedule.lateness_seconds == pytest.approx(70)
    assert not schedule.feasible
    assert any("lateness" in violation for violation in schedule.violations)
    assert schedule.cost == pytest.approx(240 + 60 * 70)

    tolerant = _problem(stops=stops, capacity=2, max_lateness=100)
    assert evaluate(tolerant, (1, 2, 3, 4)).feasible


def test_capacity_violation_is_reported():
    stops = (
        VrpStop(1, "Cantina", "pickup", "A", volume=2),
        VrpStop(2, "Padaria", "pickup", "B", volume=2),
        VrpStop(3, "Rua A", "dropoff", "A", volume=-2),
        VrpStop(4, "Rua B", "dropoff", "B", volume=-2),
    )
    schedule = evaluate(_problem(stops=stops, capacity=3, max_lateness=1000), (1, 2, 3, 4))
    assert not schedule.feasible
    assert any("capacity" in violation for violation in schedule.violations)


def test_dropoff_only_replan_starts_with_the_load_on_board():
    """A picked-up order contributes a drop-off and its volume already aboard."""
    costs = (
        (0, 100, 200),
        (100, 0, 100),
        (200, 100, 0),
    )
    stops = (
        VrpStop(1, "Cantina", "pickup", "A", volume=1),
        VrpStop(2, "Rua A", "dropoff", "A", volume=-1),
    )
    problem = VrpProblem(costs=costs, stops=stops, capacity=1)
    assert problem.precedences() == {2: 1}

    replan = VrpProblem(
        costs=((0, 200), (200, 0)),
        stops=(VrpStop(1, "Rua A", "dropoff", "A", volume=-1),),
        capacity=1,
        initial_load=1,
    )
    assert replan.precedences() == {}
    result = ExactWindowSolver().solve(replan)
    assert result.schedule.feasible
    assert result.order == (1,)
    assert result.schedule.visits[0].load == 0


def test_dropoff_before_pickup_is_infeasible():
    schedule = evaluate(_problem(capacity=2), (2, 1, 3, 4))
    assert not schedule.feasible
    assert any("dropoff before pickup" in violation for violation in schedule.violations)


def test_exact_rejects_instances_above_its_cap():
    stops = tuple(
        VrpStop(index, f"stop-{index}", "pickup" if index % 2 else "dropoff", f"d{index // 2}")
        for index in range(1, 10)
    )
    costs = tuple(tuple(10 if a != b else 0 for b in range(10)) for a in range(10))
    problem = VrpProblem(costs=costs, stops=stops, capacity=5)
    with pytest.raises(ValueError, match="capped at 8"):
        ExactWindowSolver().solve(problem)


def test_insertion_solver_is_feasible_and_not_better_than_exact():
    problem = _problem(capacity=2)
    exact = ExactWindowSolver().solve(problem)
    heuristic = InsertionWindowSolver().solve(problem)
    assert heuristic.schedule.feasible
    assert heuristic.schedule.cost >= exact.schedule.cost - 1e-9
    assert heuristic.work > 0


def test_insertion_solver_handles_ten_stops():
    stops = tuple(
        VrpStop(
            index,
            f"stop-{index}",
            "pickup" if index % 2 else "dropoff",
            f"d{(index - 1) // 2}",
            volume=1 if index % 2 else -1,
        )
        for index in range(1, 11)
    )
    size = 11
    costs = tuple(
        tuple(0 if a == b else 30 + abs(a - b) for b in range(size)) for a in range(size)
    )
    problem = VrpProblem(costs=costs, stops=stops, capacity=2)
    result = InsertionWindowSolver().solve(problem)
    assert result.schedule.feasible
    assert len(result.order) == 10
    assert all(
        result.order.index(pickup) < result.order.index(pickup + 1)
        for pickup in range(1, 11, 2)
    )
