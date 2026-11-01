"""The city-scale graph: size, connectivity, admissibility and CH work bounds.

This is the artifact the headline benchmark runs on. The test is deliberately
sampled — 105k nodes make exhaustive admissibility and oracle checks too slow
for CI — while the properties that must hold everywhere (graph loads, is
strongly connected, and CH agrees with the oracle) are checked exactly or on
large samples.
"""

import itertools
import random
from pathlib import Path

import pytest
from delivery_platform.domain.entities import GeoPoint
from delivery_platform.domain.geo import haversine_m
from delivery_platform.routing.ch import ChPathSolver, contraction_hierarchy
from delivery_platform.routing.graph import StreetGraph, load_graph
from delivery_platform.routing.path import DijkstraPathSolver, PathProblem

GRAPH_PATH = Path("data/graph/sao-paulo-city.json.gz")


@pytest.fixture(scope="module")
def graph() -> StreetGraph:
    return load_graph(GRAPH_PATH)


@pytest.fixture(scope="module")
def pairs(graph: StreetGraph) -> list[tuple[str, str]]:
    rng = random.Random(20261101)
    nodes = sorted(graph.nodes)
    picked: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    while len(picked) < 30:
        pair = tuple(rng.sample(nodes, 2))
        if pair in seen:
            continue
        seen.add(pair)
        picked.append(pair)
    return picked


def test_city_graph_is_committed_and_reads_from_gzip(graph: StreetGraph):
    assert GRAPH_PATH.suffix == ".gz"
    assert graph.graph_id == "sao-paulo-city"
    assert graph.version.startswith("osm-city-")
    assert len(graph.nodes) > 100_000
    assert sum(len(edges) for edges in graph.adjacency.values()) > 150_000
    assert "OpenStreetMap" in graph.source and "ODbL" in graph.attribution


def test_city_graph_is_strongly_connected(graph: StreetGraph):
    """Every node must be reachable from, and reach the, starting node."""
    start = min(graph.nodes)

    def reachable(reverse: bool) -> set[str]:
        seen = {start}
        stack = [start]
        while stack:
            node = stack.pop()
            edges = graph.reverse_neighbors(node) if reverse else graph.neighbors(node)
            for edge in edges:
                if edge.to_node not in seen:
                    seen.add(edge.to_node)
                    stack.append(edge.to_node)
        return seen

    assert reachable(False) == set(graph.nodes)
    assert reachable(True) == set(graph.nodes)


def test_sampled_edges_respect_the_straight_line(graph: StreetGraph):
    rng = random.Random(7)
    nodes = sorted(graph.nodes)
    for _ in range(5_000):
        node = rng.choice(nodes)
        edges = graph.neighbors(node)
        if not edges:
            continue
        edge = rng.choice(edges)
        straight = haversine_m(graph.nodes[node], graph.nodes[edge.to_node])
        assert edge.distance_meters >= straight - 1e-6


def test_city_points_snap_onto_the_network(graph: StreetGraph):
    centro = GeoPoint(latitude=-23.5482, longitude=-46.6371)
    node = graph.nearest_node(centro)
    assert node in graph.nodes
    assert haversine_m(centro, graph.nodes[node]) < 2_000


def test_ch_matches_the_oracle_on_city_streets(graph: StreetGraph, pairs: list[tuple[str, str]]):
    solver = ChPathSolver()
    oracle = DijkstraPathSolver()
    for origin, destination in pairs:
        problem = PathProblem(graph, origin, destination, "time")
        result = solver.solve(problem)
        expected = oracle.solve(problem)
        assert result.estimated_seconds == pytest.approx(
            expected.estimated_seconds, abs=0.01
        ), (origin, destination)
        for current, nxt in itertools.pairwise(result.node_path):
            assert any(edge.to_node == nxt for edge in graph.neighbors(current))


def test_ch_query_work_is_a_fraction_of_the_graph(graph: StreetGraph, pairs: list[tuple[str, str]]):
    """CH is the reason this graph is usable interactively: a few dozen nodes."""
    hierarchy = contraction_hierarchy(graph, objective="time")
    solver = ChPathSolver()
    settled = [
        solver.solve(PathProblem(graph, origin, destination, "time")).nodes_expanded
        for origin, destination in pairs
    ]
    median = sorted(settled)[len(settled) // 2]
    assert median <= len(graph.nodes) * 0.01, (median, len(graph.nodes))
    # And the hierarchy itself stays in the same order of magnitude as the graph.
    assert hierarchy.stats.shortcuts < hierarchy.stats.original_edges * 3
