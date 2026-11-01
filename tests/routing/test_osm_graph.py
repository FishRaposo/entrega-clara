"""The real OpenStreetMap extract: connectivity, geometry and the solver ladder.

The committed artifact is built by ``scripts/data/fetch_osm_graph.py``, which
keeps only the largest strongly connected component — a directed street
network with one-way streets has plenty of nodes you can enter but not leave,
and routing must never snap a stop into one of those.
"""

import itertools
import random
from pathlib import Path

import pytest
from delivery_platform.domain.entities import GeoPoint
from delivery_platform.domain.geo import haversine_m
from delivery_platform.routing.graph import StreetGraph, load_graph
from delivery_platform.routing.informed import AltPathSolver, BidirectionalPathSolver
from delivery_platform.routing.path import (
    AStarPathSolver,
    DijkstraPathSolver,
    PathProblem,
)

GRAPH_PATH = Path("data/graph/sao-paulo-centro-osm.json")
SEEDED_POINTS = {
    "rest-seu-manoel": GeoPoint(latitude=-23.5482, longitude=-46.6371),
    "addr-casa": GeoPoint(latitude=-23.5515, longitude=-46.632),
    "addr-ana": GeoPoint(latitude=-23.558, longitude=-46.634),
    "courier": GeoPoint(latitude=-23.549, longitude=-46.636),
}


@pytest.fixture(scope="module")
def graph() -> StreetGraph:
    return load_graph(GRAPH_PATH)


@pytest.fixture(scope="module")
def pairs(graph: StreetGraph) -> list[tuple[str, str]]:
    rng = random.Random(20261101)
    nodes = sorted(graph.nodes)
    return rng.sample([(a, b) for a in nodes for b in nodes if a != b], 40)


def test_osm_graph_loads_with_provenance(graph: StreetGraph):
    assert graph.graph_id == "sao-paulo-centro-osm"
    assert graph.version.startswith("osm-")
    assert graph.source.startswith("OpenStreetMap")
    assert "OpenStreetMap" in graph.attribution and "ODbL" in graph.attribution
    assert 1_000 <= len(graph.nodes) <= 40_000
    assert graph.max_speed_mps > 0


def test_osm_graph_keeps_only_a_strongly_connected_component(graph: StreetGraph):
    """Every node must reach, and be reached by, every other node."""
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

    assert reachable(reverse=False) == set(graph.nodes)
    assert reachable(reverse=True) == set(graph.nodes)


def test_every_osm_edge_is_at_least_the_straight_line(graph: StreetGraph):
    # The A* heuristic stays admissible only while this holds.
    for node, edges in graph.adjacency.items():
        for edge in edges:
            straight = haversine_m(graph.nodes[node], graph.nodes[edge.to_node])
            assert edge.distance_meters >= straight - 1e-6, (node, edge.to_node)


def test_seeded_demo_points_snap_nearby(graph: StreetGraph):
    for name, point in SEEDED_POINTS.items():
        node = graph.nearest_node(point)
        assert node in graph.nodes
        # Distances include the streets lost to the connectivity filter.
        assert haversine_m(point, graph.nodes[node]) < 700, name


@pytest.mark.parametrize(
    "solver_type", (AStarPathSolver, AltPathSolver, BidirectionalPathSolver)
)
def test_exact_solvers_match_the_oracle_on_real_streets(
    graph: StreetGraph, pairs: list[tuple[str, str]], solver_type: type
):
    solver = solver_type()
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
        assert result.node_path[0] == origin
        assert result.node_path[-1] == destination


def test_landmarks_beat_the_straight_line_heuristic_on_real_streets(
    graph: StreetGraph, pairs: list[tuple[str, str]]
):
    """The claim the benchmark table makes, asserted as a regression guard."""
    astar = AStarPathSolver()
    alt = AltPathSolver()
    astar_total = 0
    alt_total = 0
    for origin, destination in pairs:
        problem = PathProblem(graph, origin, destination, "time")
        astar_total += astar.solve(problem).nodes_expanded
        alt_total += alt.solve(problem).nodes_expanded
    assert alt_total < astar_total


def test_delivery_legs_land_in_a_plausible_range(graph: StreetGraph):
    restaurant = graph.nearest_node(SEEDED_POINTS["rest-seu-manoel"])
    customer = graph.nearest_node(SEEDED_POINTS["addr-casa"])
    leg = DijkstraPathSolver().solve(PathProblem(graph, restaurant, customer, "time"))
    assert 100 < leg.distance_meters < 6_000
    assert leg.estimated_seconds > 0
