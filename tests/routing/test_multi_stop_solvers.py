"""P2: multi-stop solvers — exact Held-Karp vs greedy/2-opt, precedence, matrix."""

from itertools import pairwise, permutations
from pathlib import Path

import pytest
from delivery_platform.routing.graph import load_graph
from delivery_platform.routing.matrix import build_cost_matrix
from delivery_platform.routing.models import RouteProblem
from delivery_platform.routing.tsp import (
    HeldKarpSolver,
    NearestNeighborSolver,
    RouteTooLargeError,
    TwoOptSolver,
)

GRAPH_PATH = Path("data/graph/sao-paulo-centro.json")


def _matrix_problem() -> RouteProblem:
    # Small symmetric distance matrix — courier at index 0.
    return RouteProblem(
        labels=("courier", "a", "b", "c"),
        costs=(
            (0, 5, 9, 4),
            (5, 0, 3, 8),
            (9, 3, 0, 6),
            (4, 8, 6, 0),
        ),
        origin_index=0,
    )


def _brute_force_best(problem: RouteProblem) -> float:
    origin = problem.origin_index
    others = [i for i in range(len(problem.labels)) if i != origin]
    best = float("inf")
    for perm in permutations(others):
        order = (origin, *perm, origin)
        cost = sum(problem.costs[a][b] for a, b in pairwise(order))
        best = min(best, cost)
    return best


def test_held_karp_matches_brute_force():
    problem = _matrix_problem()
    result = HeldKarpSolver().solve(problem)
    assert result.total_cost == pytest.approx(_brute_force_best(problem))
    assert result.route[0] == result.route[-1] == "courier"
    assert sorted(result.route[:-1]) == sorted(problem.labels)
    assert result.solver_name == "held-karp"


def test_held_karp_respects_precedence():
    problem = _matrix_problem()
    # Stop 2 ("b") must come after stop 1 ("a").
    result = HeldKarpSolver(precedence={2: 1}).solve(problem)
    labels = list(result.route)
    assert labels.index("b") > labels.index("a")
    assert result.total_cost >= _brute_force_best(problem)


def test_nearest_neighbor_and_two_opt_valid_tours():
    problem = _matrix_problem()
    nn = NearestNeighborSolver().solve(problem)
    two = TwoOptSolver().solve(problem)
    for result in (nn, two):
        assert result.route[0] == result.route[-1] == "courier"
        assert sorted(result.route[:-1]) == sorted(problem.labels)
    assert two.total_cost <= nn.total_cost + 1e-9
    assert two.total_cost >= _brute_force_best(problem) - 1e-9


def test_two_opt_respects_precedence():
    problem = _matrix_problem()
    result = TwoOptSolver(precedence={2: 1}).solve(problem)
    labels = list(result.route)
    assert labels.index("b") > labels.index("a")


def test_held_karp_size_limit():
    labels = tuple(str(i) for i in range(HeldKarpSolver.MAX_STOPS + 1))
    size = len(labels)
    big = RouteProblem(
        labels=labels,
        costs=tuple(tuple(1.0 for _ in range(size)) for _ in range(size)),
    )
    with pytest.raises(RouteTooLargeError):
        HeldKarpSolver().solve(big)


def test_build_cost_matrix_from_graph():
    graph = load_graph(GRAPH_PATH)
    nodes = sorted(graph.nodes)
    stops = nodes[:5]
    problem = build_cost_matrix(
        graph,
        labels=tuple(f"stop-{i}" for i in range(5)),
        nodes=tuple(stops),
        objective="time",
        origin_index=0,
    )
    assert problem.objective == "time"
    assert len(problem.costs) == 5
    for i in range(5):
        assert problem.costs[i][i] == 0
        for j in range(5):
            if i != j:
                assert problem.costs[i][j] > 0
                # symmetry on this undirected graph
                assert problem.costs[i][j] == pytest.approx(
                    float(problem.costs[j][i]), abs=1e-6
                )


def test_held_karp_beats_or_matches_heuristics_on_graph():
    graph = load_graph(GRAPH_PATH)
    nodes = sorted(graph.nodes)
    problem = build_cost_matrix(
        graph,
        labels=tuple(f"s{i}" for i in range(6)),
        nodes=tuple(nodes[::13][:6]),
        objective="time",
    )
    hk = HeldKarpSolver().solve(problem)
    nn = NearestNeighborSolver().solve(problem)
    two = TwoOptSolver().solve(problem)
    assert hk.total_cost <= nn.total_cost + 1e-9
    assert hk.total_cost <= two.total_cost + 1e-9
