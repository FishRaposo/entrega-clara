"""Phase 4: synthetic graph, A* vs Dijkstra oracle, delivery route results."""

import itertools
import json
import random
from pathlib import Path

import pytest
from delivery_platform.application.ports import DeliveryRouteRequest
from delivery_platform.domain.entities import GeoPoint
from delivery_platform.routing.graph import StreetGraph, load_graph
from delivery_platform.routing.graph_planner import GraphRoutePlanner
from delivery_platform.routing.path import (
    AStarPathSolver,
    DeliveryRouteProblem,
    DeliveryRouteSolver,
    DijkstraPathSolver,
    PathProblem,
)

GRAPH_PATH = Path("data/graph/sao-paulo-centro.json")


@pytest.fixture(scope="module")
def graph() -> StreetGraph:
    return load_graph(GRAPH_PATH)


@pytest.fixture()
def astar() -> AStarPathSolver:
    return AStarPathSolver()


@pytest.fixture()
def dijkstra() -> DijkstraPathSolver:
    return DijkstraPathSolver()


def _assert_valid_path(graph: StreetGraph, node_path: tuple[str, ...]) -> None:
    for current, nxt in itertools.pairwise(node_path):
        assert any(
            edge.to_node == nxt for edge in graph.neighbors(current)
        ), f"missing edge {current}->{nxt}"


def test_graph_loads_versioned_lattice(graph: StreetGraph):
    assert graph.graph_id == "sao-paulo-centro"
    assert graph.version == "1.0.0"
    assert len(graph.nodes) == 77
    assert all(graph.neighbors(node) for node in graph.nodes)


def test_graph_rejects_unknown_edge_nodes(tmp_path: Path):
    bad = {
        "graph_id": "bad",
        "version": "1",
        "nodes": [
            {"id": "a", "latitude": 0.0, "longitude": 0.0},
            {"id": "b", "latitude": 0.0, "longitude": 0.0},
        ],
        "edges": [{"from": "a", "to": "zzz", "distance_meters": 1.0}],
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="known nodes"):
        load_graph(path)


def test_astar_matches_dijkstra_oracle(
    graph: StreetGraph, astar: AStarPathSolver, dijkstra: DijkstraPathSolver
):
    rng = random.Random(20260901)
    nodes = sorted(graph.nodes)
    pairs = rng.sample([(a, b) for a in nodes for b in nodes if a != b], 150)
    for origin, destination in pairs:
        problem = PathProblem(graph, origin, destination)
        a_result = astar.solve(problem)
        d_result = dijkstra.solve(problem)
        assert a_result.distance_meters == pytest.approx(
            d_result.distance_meters, abs=0.01
        ), (origin, destination)
        _assert_valid_path(graph, a_result.node_path)
        assert a_result.node_path[0] == origin
        assert a_result.node_path[-1] == destination


def test_astar_expands_no_more_than_oracle(
    graph: StreetGraph, astar: AStarPathSolver, dijkstra: DijkstraPathSolver
):
    # Heuristic-guided search should never need more expansions on this graph.
    nodes = sorted(graph.nodes)
    a_total = 0
    d_total = 0
    for origin in nodes[:20]:
        for destination in nodes[-20:]:
            if origin == destination:
                continue
            a_total += astar.solve(PathProblem(graph, origin, destination)).nodes_expanded
            d_total += dijkstra.solve(PathProblem(graph, origin, destination)).nodes_expanded
    assert a_total <= d_total


def test_nearest_node_snapping(graph: StreetGraph):
    # Seu Manoel's seeded location should snap inside the lattice.
    snapped = graph.nearest_node(GeoPoint(latitude=-23.5482, longitude=-46.6371))
    assert snapped in graph.nodes
    corner = graph.nearest_node(GeoPoint(latitude=-23.9, longitude=-46.9))
    assert corner in graph.nodes


def test_delivery_route_solver_orders_stops(graph: StreetGraph):
    solver = DeliveryRouteSolver(AStarPathSolver())
    nodes = sorted(graph.nodes)
    problem = DeliveryRouteProblem(
        graph=graph,
        courier_origin=nodes[0],
        pickup_node=nodes[30],
        dropoff_node=nodes[70],
        pickup_label="Restaurante",
        dropoff_label="Cliente",
        delivery_id="dlv-1",
    )
    result = solver.solve(problem)
    assert [s.kind for s in result.stops] == ["pickup", "dropoff"]
    assert len(result.segments) == 2
    assert result.segments[0].to_label == "Restaurante"
    assert result.segments[1].from_label == "Restaurante"
    assert result.graph_id == "sao-paulo-centro"
    assert result.graph_version == "1.0.0"
    assert result.distance_meters > 0
    assert result.geometry["type"] == "LineString"
    assert result.solver_name == "astar-synthetic-graph"


def test_graph_planner_produces_route_plan(graph: StreetGraph):
    planner = GraphRoutePlanner(graph)
    plan = planner.plan(
        DeliveryRouteRequest(
            delivery_id="dlv-1",
            courier_location=GeoPoint(latitude=-23.553, longitude=-46.645),
            pickup_point=GeoPoint(latitude=-23.5482, longitude=-46.6371),
            pickup_label="Seu Manoel Marmitas",
            dropoff_point=GeoPoint(latitude=-23.5445, longitude=-46.6295),
            dropoff_label="Casa",
        ),
        route_id="rpl-1",
    )
    assert plan.graph_id == "sao-paulo-centro"
    assert plan.solver_name == "astar-synthetic-graph"
    assert [s.kind for s in plan.stops] == ["pickup", "dropoff"]
    assert all(seg.node_path for seg in plan.segments)
    assert plan.warnings == []


def test_disconnected_graph_raises_route_unavailable():
    graph = StreetGraph(
        graph_id="tiny",
        version="1",
        nodes={
            "a": GeoPoint(latitude=0.0, longitude=0.0),
            "b": GeoPoint(latitude=1.0, longitude=1.0),
        },
        adjacency={"a": (), "b": ()},
    )
    planner = GraphRoutePlanner(graph)
    from delivery_platform.domain.errors import RouteUnavailableError

    with pytest.raises(RouteUnavailableError):
        planner.plan(
            DeliveryRouteRequest(
                delivery_id="dlv-1",
                courier_location=GeoPoint(latitude=0.0, longitude=0.0),
                pickup_point=GeoPoint(latitude=0.0, longitude=0.0),
                pickup_label="p",
                dropoff_point=GeoPoint(latitude=1.0, longitude=1.0),
                dropoff_label="d",
            ),
            route_id="rpl-x",
        )
