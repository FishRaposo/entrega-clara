"""Contraction hierarchies: differential correctness, structure, determinism, work."""

import itertools
import random
from pathlib import Path

import pytest
from delivery_platform.domain.entities import GeoPoint
from delivery_platform.routing.ch import ChPathSolver, contraction_hierarchy
from delivery_platform.routing.contraction import preprocess
from delivery_platform.routing.graph import StreetGraph, load_graph
from delivery_platform.routing.path import DijkstraPathSolver, PathProblem

GRAPH_PATH = Path("data/graph/sao-paulo-centro.json")


@pytest.fixture(scope="module")
def graph() -> StreetGraph:
    return load_graph(GRAPH_PATH)


@pytest.fixture(scope="module")
def pairs(graph: StreetGraph) -> list[tuple[str, str]]:
    rng = random.Random(20261101)
    nodes = sorted(graph.nodes)
    return rng.sample([(a, b) for a in nodes for b in nodes if a != b], 300)


def _assert_valid_path(graph: StreetGraph, node_path: tuple[str, ...]) -> None:
    for current, nxt in itertools.pairwise(node_path):
        assert any(edge.to_node == nxt for edge in graph.neighbors(current)), (
            f"missing edge {current}->{nxt}"
        )


def test_ch_matches_the_dijkstra_oracle_on_centro(graph: StreetGraph, pairs: list[tuple[str, str]]):
    solver = ChPathSolver()
    oracle = DijkstraPathSolver()
    for origin, destination in pairs:
        problem = PathProblem(graph, origin, destination, "time")
        result = solver.solve(problem)
        expected = oracle.solve(problem)
        assert result.estimated_seconds == pytest.approx(
            expected.estimated_seconds, abs=0.01
        ), (origin, destination)
        assert result.node_path[0] == origin
        assert result.node_path[-1] == destination
        _assert_valid_path(graph, result.node_path)


def test_ch_matches_the_oracle_on_the_distance_objective(graph: StreetGraph):
    solver = ChPathSolver()
    oracle = DijkstraPathSolver()
    rng = random.Random(7)
    nodes = sorted(graph.nodes)
    for _ in range(60):
        origin, destination = rng.sample(nodes, 2)
        problem = PathProblem(graph, origin, destination, "distance")
        result = solver.solve(problem)
        expected = oracle.solve(problem)
        assert result.distance_meters == pytest.approx(expected.distance_meters, abs=0.01)
        _assert_valid_path(graph, result.node_path)


def test_upward_edges_increase_in_level(graph: StreetGraph):
    hierarchy = contraction_hierarchy(graph, objective="time")
    levels = hierarchy.levels
    for node, edges in enumerate(hierarchy.up_forward):
        for target, _weight in edges:
            assert levels[node] < levels[target]
    for node, edges in enumerate(hierarchy.up_backward):
        for target, _weight in edges:
            assert levels[node] < levels[target]


def test_shortcut_expansions_are_valid_original_paths(graph: StreetGraph):
    hierarchy = contraction_hierarchy(graph, objective="time")
    shortcuts = list(hierarchy.children)[:50]
    assert shortcuts, "expected at least some shortcuts on this graph"
    for edge in shortcuts:
        chain = hierarchy.expand(edge)
        assert chain[0][0] == edge[0] and chain[-1][1] == edge[1]
        for (a, b), (c, _d) in itertools.pairwise(chain):
            assert b == c, "expanded shortcut must be contiguous"
            assert any(
                neighbour.to_node == hierarchy.ids[b]
                for neighbour in graph.neighbors(hierarchy.ids[a])
            )


def test_preprocessing_is_deterministic(graph: StreetGraph):
    first = preprocess(graph, objective="time")
    second = preprocess(graph, objective="time")
    assert first.levels == second.levels
    assert first.stats.shortcuts == second.stats.shortcuts
    assert first.up_forward == second.up_forward


def test_ch_expands_fewer_nodes_than_the_oracle(graph: StreetGraph, pairs: list[tuple[str, str]]):
    """CH's advantage is asymptotic: on 77 nodes it only has to be better.

    The city-graph benchmark asserts the bound that matters (a fraction of a
    percent of the graph); here the hierarchy is shallow and the two-directional
    query pays its constant cost against a tiny search.
    """
    solver = ChPathSolver()
    oracle = DijkstraPathSolver()
    ch_work = 0
    oracle_work = 0
    for origin, destination in pairs[:100]:
        problem = PathProblem(graph, origin, destination, "time")
        ch_work += solver.solve(problem).nodes_expanded
        oracle_work += oracle.solve(problem).nodes_expanded
    assert ch_work < oracle_work


def test_ch_reports_preprocessing_and_trace(graph: StreetGraph):
    solver = ChPathSolver()
    problem = PathProblem(graph, "n-00-00", "n-06-10", "time")
    result = solver.solve(problem, trace=True)
    assert result.preprocessing_time_ns > 0
    assert len(result.expanded_order) == result.nodes_expanded
    assert result.nodes_expanded > 0


def test_hierarchy_is_cached_on_disk_and_reloaded(graph: StreetGraph, tmp_path, monkeypatch):
    from delivery_platform.routing import ch as ch_module

    monkeypatch.setattr(ch_module, "CACHE_DIR", tmp_path)
    ch_module._CACHE.clear()

    first = ch_module.contraction_hierarchy(graph, objective="time")
    assert list(tmp_path.glob("*.json.gz")), "preprocessing must leave a cache entry"

    ch_module._CACHE.clear()
    second = ch_module.contraction_hierarchy(graph, objective="time")

    assert second.levels == first.levels
    assert second.up_forward == first.up_forward
    assert second.stats.shortcuts == first.stats.shortcuts
    # A cache hit reuses the original build cost instead of pretending it is free.
    assert second.stats.preprocessing_time_ns == first.stats.preprocessing_time_ns


def test_unreachable_pair_raises():
    graph = StreetGraph(
        graph_id="tiny",
        version="1",
        nodes={
            "a": GeoPoint(latitude=0.0, longitude=0.0),
            "b": GeoPoint(latitude=1.0, longitude=1.0),
        },
        adjacency={"a": (), "b": ()},
    )
    with pytest.raises(ValueError, match="No path"):
        ChPathSolver().solve(PathProblem(graph, "a", "b"))
