"""Time-dependent search: differential correctness, FIFO behaviour, peak effects."""

import random
from pathlib import Path

import pytest
from delivery_platform.domain.entities import GeoPoint
from delivery_platform.routing.graph import GraphEdge, StreetGraph, load_graph
from delivery_platform.routing.path import DijkstraPathSolver, PathProblem
from delivery_platform.routing.time_dependent import (
    TimeDependentAStarPathSolver,
    TimeDependentDijkstraPathSolver,
)
from delivery_platform.routing.time_profile import (
    SpeedBand,
    TravelTimeProfile,
    load_profile,
)

PROFILE = load_profile(Path("data/graph/traffic-profile.json"))
FLAT = TravelTimeProfile(
    profile_id="flat",
    version="1",
    source="test",
    tz_offset_hours=0.0,
    bands=(SpeedBand(band_id="all", up_to_kmh=130, hourly=(1.0,) * 24),),
)
GRAPH_PATH = Path("data/graph/sao-paulo-centro-osm.json")
NOON = 12 * 3600.0  # epoch-agnostic: the profile reads only the local hour
NIGHT = 23.5 * 3600.0


@pytest.fixture(scope="module")
def graph() -> StreetGraph:
    return load_graph(GRAPH_PATH)


@pytest.fixture(scope="module")
def pairs(graph: StreetGraph) -> list[tuple[str, str]]:
    rng = random.Random(20261101)
    nodes = sorted(graph.nodes)
    return rng.sample([(a, b) for a in nodes for b in nodes if a != b], 40)


def _random_graph(rng: random.Random, size: int = 6) -> StreetGraph:
    nodes = {
        f"n{index}": GeoPoint(
            latitude=-23.55 + rng.uniform(-0.01, 0.01),
            longitude=-46.65 + rng.uniform(-0.01, 0.01),
        )
        for index in range(size)
    }
    adjacency: dict[str, list[GraphEdge]] = {node: [] for node in nodes}
    for a in range(size):
        for b in range(size):
            if a == b or rng.random() < 0.45:
                continue
            adjacency[f"n{a}"].append(
                GraphEdge(
                    to_node=f"n{b}",
                    distance_meters=rng.uniform(50, 400),
                    speed_kmh=rng.choice([15.0, 30.0, 50.0]),
                )
            )
    return StreetGraph(graph_id="random", version="1", nodes=nodes, adjacency=adjacency)


def _reference_arrivals(
    graph: StreetGraph, origin: str, departure: float, profile: TravelTimeProfile
) -> dict[str, float]:
    """Bellman-Ford relaxation on arrival times — independent of Dijkstra."""
    arrivals = {origin: departure}
    for _ in range(len(graph.nodes)):
        changed = False
        for node, at in list(arrivals.items()):
            for edge in graph.neighbors(node):
                arrive = at + profile.edge_seconds(edge, at)
                if arrive < arrivals.get(edge.to_node, float("inf")) - 1e-9:
                    arrivals[edge.to_node] = arrive
                    changed = True
        if not changed:
            break
    return arrivals


def test_matches_a_bellman_ford_reference_on_random_graphs():
    solver = TimeDependentDijkstraPathSolver()
    for seed in range(12):
        rng = random.Random(seed)
        graph = _random_graph(rng)
        departure = NOON + rng.uniform(0, 3600)
        reference = _reference_arrivals(graph, "n0", departure, PROFILE)
        for target in graph.nodes:
            if target == "n0":
                continue
            expected = reference.get(target)
            if expected is None:
                with pytest.raises(ValueError):
                    solver.solve(PathProblem(graph, "n0", target, "time", departure, PROFILE))
                continue
            result = solver.solve(PathProblem(graph, "n0", target, "time", departure, PROFILE))
            assert result.arrival_at == pytest.approx(expected, abs=1e-6), (seed, target)
            assert result.estimated_seconds == pytest.approx(expected - departure, abs=1e-6)


def test_flat_profile_reduces_to_static_dijkstra(graph: StreetGraph, pairs: list[tuple[str, str]]):
    """With every multiplier at 1.0 the time-dependent search is the static one."""
    td = TimeDependentDijkstraPathSolver()
    oracle = DijkstraPathSolver()
    for origin, destination in pairs[:20]:
        time_dependent = td.solve(PathProblem(graph, origin, destination, "time", NOON, FLAT))
        static = oracle.solve(PathProblem(graph, origin, destination, "time"))
        assert time_dependent.estimated_seconds == pytest.approx(static.estimated_seconds, abs=1e-6)
        assert time_dependent.node_path == static.node_path


def test_astar_matches_the_time_dependent_oracle(graph: StreetGraph, pairs: list[tuple[str, str]]):
    astar = TimeDependentAStarPathSolver()
    oracle = TimeDependentDijkstraPathSolver()
    for origin, destination in pairs:
        problem = PathProblem(graph, origin, destination, "time", NOON, PROFILE)
        expected = oracle.solve(problem)
        result = astar.solve(problem)
        assert result.arrival_at == pytest.approx(expected.arrival_at, abs=1e-6)
        assert result.nodes_expanded <= expected.nodes_expanded * 1.2


def test_arrival_is_monotone_in_departure(graph: StreetGraph, pairs: list[tuple[str, str]]):
    """FIFO: leaving later must never arrive earlier, across the whole day."""
    solver = TimeDependentDijkstraPathSolver()
    origin, destination = pairs[0]
    previous = None
    for hour in range(24):
        problem = PathProblem(graph, origin, destination, "time", hour * 3600.0, PROFILE)
        arrival = solver.solve(problem).arrival_at
        assert arrival is not None
        if previous is not None:
            assert arrival > previous
        previous = arrival


def test_lunch_peak_is_slower_than_the_night(graph: StreetGraph, pairs: list[tuple[str, str]]):
    solver = TimeDependentDijkstraPathSolver()
    ratios = []
    for origin, destination in pairs[:15]:
        noon = solver.solve(PathProblem(graph, origin, destination, "time", NOON, PROFILE))
        night = solver.solve(PathProblem(graph, origin, destination, "time", NIGHT, PROFILE))
        assert noon.estimated_seconds > night.estimated_seconds
        ratios.append(noon.estimated_seconds / night.estimated_seconds)
    # The peak is damped, not amplified, by rerouting: the search can leave the
    # roads that slow down most, so the end-to-end ratio sits above 1.1 rather
    # than at the 1.5+ of a single arterial edge.
    assert sum(ratios) / len(ratios) > 1.1


def test_time_dependent_search_beats_sticking_to_the_free_flow_path(
    graph: StreetGraph, pairs: list[tuple[str, str]]
):
    """Rerouting is real: the profile-optimal path is never worse, sometimes better."""
    static = DijkstraPathSolver()
    time_dependent = TimeDependentDijkstraPathSolver()
    improved = 0
    for origin, destination in pairs[:15]:
        free_flow_path = static.solve(PathProblem(graph, origin, destination, "time"))
        cost_at_noon = 0.0
        for current, nxt in zip(free_flow_path.node_path, free_flow_path.node_path[1:]):
            edge = next(e for e in graph.neighbors(current) if e.to_node == nxt)
            cost_at_noon += PROFILE.edge_seconds(edge, NOON)
        result = time_dependent.solve(
            PathProblem(graph, origin, destination, "time", NOON, PROFILE)
        )
        assert result.estimated_seconds <= cost_at_noon + 1e-6
        if result.estimated_seconds < cost_at_noon - 1e-6:
            improved += 1
    assert improved > 0


def test_trace_records_expansion_order(graph: StreetGraph, pairs: list[tuple[str, str]]):
    solver = TimeDependentAStarPathSolver()
    origin, destination = pairs[1]
    result = solver.solve(
        PathProblem(graph, origin, destination, "time", NOON, PROFILE), trace=True
    )
    assert len(result.expanded_order) == result.nodes_expanded
    assert len(result.frontier_sizes) == result.nodes_expanded
    assert result.departure_at == NOON
    assert result.arrival_at is not None and result.arrival_at > NOON


def test_requires_a_departure_and_a_profile(graph: StreetGraph, pairs: list[tuple[str, str]]):
    origin, destination = pairs[2]
    solver = TimeDependentDijkstraPathSolver()
    with pytest.raises(ValueError, match="departure_at"):
        solver.solve(PathProblem(graph, origin, destination, "time"))
    with pytest.raises(ValueError, match="traffic profile"):
        solver.solve(PathProblem(graph, origin, destination, "time", NOON))
    with pytest.raises(ValueError, match="time objective"):
        solver.solve(PathProblem(graph, origin, destination, "distance", NOON, PROFILE))
