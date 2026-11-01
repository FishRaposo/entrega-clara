"""ALT landmarks, bidirectional search and weighted A* vs the Dijkstra oracle."""

import itertools
import random
from pathlib import Path

import pytest
from delivery_platform.routing.graph import StreetGraph, load_graph
from delivery_platform.routing.informed import (
    AltPathSolver,
    BidirectionalPathSolver,
    WeightedAStarSolver,
)
from delivery_platform.routing.landmarks import (
    DEFAULT_LANDMARK_COUNT,
    LandmarkTable,
    landmark_table,
)
from delivery_platform.routing.path import (
    AStarPathSolver,
    DijkstraPathSolver,
    PathProblem,
    edge_weight,
)

GRAPH_PATH = Path("data/graph/sao-paulo-centro.json")

EXACT_SOLVERS = (AStarPathSolver, AltPathSolver, BidirectionalPathSolver)


@pytest.fixture(scope="module")
def graph() -> StreetGraph:
    return load_graph(GRAPH_PATH)


@pytest.fixture(scope="module")
def pairs(graph: StreetGraph) -> list[tuple[str, str]]:
    rng = random.Random(20261101)
    nodes = sorted(graph.nodes)
    return rng.sample([(a, b) for a in nodes for b in nodes if a != b], 150)


def _objective_cost(result, objective: str) -> float:
    return result.estimated_seconds if objective == "time" else result.distance_meters


def _assert_valid_path(graph: StreetGraph, node_path: tuple[str, ...]) -> None:
    for current, nxt in itertools.pairwise(node_path):
        assert any(edge.to_node == nxt for edge in graph.neighbors(current)), (
            f"missing edge {current}->{nxt}"
        )


@pytest.mark.parametrize("objective", ["time", "distance"])
@pytest.mark.parametrize("solver_type", EXACT_SOLVERS, ids=lambda t: t.__name__)
def test_exact_solver_matches_oracle_cost(
    graph: StreetGraph, pairs: list[tuple[str, str]], solver_type: type, objective: str
):
    solver = solver_type()
    oracle = DijkstraPathSolver()
    for origin, destination in pairs:
        problem = PathProblem(graph, origin, destination, objective)  # type: ignore[arg-type]
        result = solver.solve(problem)
        expected = oracle.solve(problem)
        assert _objective_cost(result, objective) == pytest.approx(
            _objective_cost(expected, objective), abs=0.01
        ), (origin, destination)
        assert result.node_path[0] == origin
        assert result.node_path[-1] == destination
        _assert_valid_path(graph, result.node_path)


def test_alt_bound_is_admissible(graph: StreetGraph, pairs: list[tuple[str, str]]):
    table = landmark_table(graph, objective="time", count=DEFAULT_LANDMARK_COUNT)
    oracle = DijkstraPathSolver()
    for origin, destination in pairs[:40]:
        bound = table.bound_for(destination)
        optimal = oracle.solve(PathProblem(graph, origin, destination, "time"))
        assert bound(origin) <= optimal.estimated_seconds + 1e-9, (origin, destination)
        assert bound(destination) == pytest.approx(0.0, abs=1e-9)
        assert bound(origin) >= 0.0


def test_alt_bound_is_consistent_on_every_edge(graph: StreetGraph):
    table = landmark_table(graph, objective="time", count=DEFAULT_LANDMARK_COUNT)
    for destination in sorted(graph.nodes)[::9]:
        bound = table.bound_for(destination)
        for node in sorted(graph.nodes):
            for edge in graph.neighbors(node):
                step = edge_weight(edge, "time")
                assert bound(node) <= step + bound(edge.to_node) + 1e-9, (
                    node,
                    edge.to_node,
                    destination,
                )


def test_landmark_selection_is_deterministic(graph: StreetGraph):
    cached = landmark_table(graph, objective="time", count=6)
    rebuilt = LandmarkTable.build(graph, objective="time", count=6)
    assert rebuilt.landmarks == cached.landmarks
    assert len(set(rebuilt.landmarks)) == 6
    assert all(node in graph.nodes for node in rebuilt.landmarks)


def test_informed_solvers_expand_less_than_dijkstra_in_aggregate(
    graph: StreetGraph, pairs: list[tuple[str, str]]
):
    dijkstra = DijkstraPathSolver()
    alt = AltPathSolver()
    bidirectional = BidirectionalPathSolver()
    baseline = 0
    alt_total = 0
    bidirectional_total = 0
    for origin, destination in pairs[:60]:
        problem = PathProblem(graph, origin, destination, "time")
        baseline += dijkstra.solve(problem).nodes_expanded
        alt_total += alt.solve(problem).nodes_expanded
        bidirectional_total += bidirectional.solve(problem).nodes_expanded
    assert alt_total < baseline
    assert bidirectional_total < baseline


@pytest.mark.parametrize("epsilon", [1.5, 2.5, 5.0])
def test_weighted_astar_stays_within_epsilon_bound(
    graph: StreetGraph, pairs: list[tuple[str, str]], epsilon: float
):
    solver = WeightedAStarSolver(epsilon=epsilon)
    oracle = DijkstraPathSolver()
    for origin, destination in pairs[:40]:
        problem = PathProblem(graph, origin, destination, "time")
        result = solver.solve(problem)
        optimal = oracle.solve(problem).estimated_seconds
        assert result.estimated_seconds <= epsilon * optimal + 1e-6, (origin, destination)
        assert result.node_path[0] == origin
        assert result.node_path[-1] == destination
        _assert_valid_path(graph, result.node_path)


def test_weighted_astar_rejects_epsilon_below_one():
    with pytest.raises(ValueError, match="epsilon"):
        WeightedAStarSolver(epsilon=0.5)


def test_informed_solvers_report_work_and_preprocessing(graph: StreetGraph):
    problem = PathProblem(graph, "n-00-00", "n-06-10", "time")
    alt = AltPathSolver(landmarks=4).solve(problem, trace=True)
    assert len(alt.expanded_order) == alt.nodes_expanded
    assert alt.preprocessing_time_ns > 0
    assert alt.computation_time_ns > 0
    bidirectional = BidirectionalPathSolver(landmarks=4).solve(problem, trace=True)
    assert len(bidirectional.expanded_order) == bidirectional.nodes_expanded


def test_bidirectional_handles_trivial_pair(graph: StreetGraph):
    result = BidirectionalPathSolver().solve(PathProblem(graph, "n-03-03", "n-03-03"))
    assert result.node_path == ("n-03-03",)
    assert result.distance_meters == 0.0
    assert result.nodes_expanded == 0
