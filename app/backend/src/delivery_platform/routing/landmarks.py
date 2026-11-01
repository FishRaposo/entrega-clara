"""ALT landmark bounds: preprocessing that sharpens the A* heuristic.

A straight line is a weak lower bound on a street network — the road has to go
around the block, often the long way — so plain A* still expands much of the
city. ALT (A*, Landmarks, Triangle inequality) pays one preprocessing pass to
learn exact distances between a few landmark nodes and every other node, then
combines them with the triangle inequality:

    d(v, t) >= d(v, L) - d(t, L)
    d(v, t) >= d(L, t) - d(L, v)

The best of those over all landmarks is both admissible and consistent. Because
the graph is directed, each landmark needs distances in *both* directions
(``dist_from``: L → v, ``dist_to``: v → L) — one Dijkstra run over the graph and
one over its reverse index.

Preprocessing is paid once per (graph, objective) and reused by every query;
``PathResult.preprocessing_time_ns`` reports it separately from query time.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from delivery_platform.routing.graph import StreetGraph
from delivery_platform.routing.path import Objective, distances_from, distances_to

DEFAULT_LANDMARK_COUNT = 8


@dataclass(frozen=True)
class LandmarkTable:
    """Landmark distances backing one (graph, objective) potential."""

    objective: str
    landmarks: tuple[str, ...]
    dist_from: tuple[dict[str, float], ...]
    dist_to: tuple[dict[str, float], ...]
    preprocessing_time_ns: int

    @classmethod
    def build(
        cls,
        graph: StreetGraph,
        *,
        objective: Objective | str = "time",
        count: int = DEFAULT_LANDMARK_COUNT,
    ) -> LandmarkTable:
        started = time.perf_counter_ns()
        landmarks, dist_from = select_landmarks(graph, objective=objective, count=count)
        dist_to = tuple(distances_to(graph, landmark, objective) for landmark in landmarks)
        return cls(
            objective=objective,
            landmarks=landmarks,
            dist_from=dist_from,
            dist_to=dist_to,
            preprocessing_time_ns=time.perf_counter_ns() - started,
        )

    def bound_for(self, target: str) -> Callable[[str], float]:
        """Lower bound on the cost from any node to ``target`` — admissible and consistent."""
        from_target = tuple(table.get(target) for table in self.dist_from)
        to_target = tuple(table.get(target) for table in self.dist_to)
        from_tables, to_tables = self.dist_from, self.dist_to

        def bound(node: str) -> float:
            best = 0.0
            for index in range(len(from_tables)):
                landmark_to_node = from_tables[index].get(node)
                landmark_to_target = from_target[index]
                if landmark_to_node is not None and landmark_to_target is not None:
                    best = max(best, landmark_to_target - landmark_to_node)
                node_to_landmark = to_tables[index].get(node)
                target_to_landmark = to_target[index]
                if node_to_landmark is not None and target_to_landmark is not None:
                    best = max(best, node_to_landmark - target_to_landmark)
            return best

        return bound


def select_landmarks(
    graph: StreetGraph,
    *,
    objective: Objective | str = "time",
    count: int = DEFAULT_LANDMARK_COUNT,
) -> tuple[tuple[str, ...], tuple[dict[str, float], ...]]:
    """Greedy farthest-point selection, deterministic for a given graph.

    The first landmark is the smallest node id; each following landmark is the
    node farthest from the ones already chosen (ties broken by node id), which
    spreads landmarks across the map. The forward tables computed here are the
    ones :class:`LandmarkTable` reuses, so selection costs no extra searches.
    """
    nodes = sorted(graph.nodes)
    if not nodes or count <= 0:
        return (), ()
    if len(nodes) <= count:
        return tuple(nodes), tuple(distances_from(graph, node, objective) for node in nodes)

    chosen = [nodes[0]]
    tables = [distances_from(graph, nodes[0], objective)]
    distance_to_set = {node: tables[0].get(node, float("inf")) for node in nodes}
    while len(chosen) < count:
        candidate = _farthest(nodes, distance_to_set)
        if candidate is None:
            break
        chosen.append(candidate)
        table = distances_from(graph, candidate, objective)
        tables.append(table)
        for node in nodes:
            distance_to_set[node] = min(distance_to_set[node], table.get(node, float("inf")))
    return tuple(chosen), tuple(tables)


def _farthest(nodes: list[str], distance_to_set: dict[str, float]) -> str | None:
    """Node with the largest distance to the chosen set; ties keep the smallest id."""
    best_node, best_score = None, 0.0
    for node in nodes:
        score = distance_to_set[node]
        if score > best_score:
            best_node, best_score = node, score
    return best_node


_TABLE_CACHE: dict[tuple[int, str, int], LandmarkTable] = {}
_GRAPH_REFS: dict[int, StreetGraph] = {}


def landmark_table(
    graph: StreetGraph,
    *,
    objective: Objective | str = "time",
    count: int = DEFAULT_LANDMARK_COUNT,
) -> LandmarkTable:
    """Cached landmark table: preprocessing is paid once per (graph, objective)."""
    key = (id(graph), objective, count)
    cached = _TABLE_CACHE.get(key)
    if cached is not None:
        return cached
    table = LandmarkTable.build(graph, objective=objective, count=count)
    # Hold a reference so the cached id() cannot be reused by another object.
    _GRAPH_REFS[id(graph)] = graph
    _TABLE_CACHE[key] = table
    return table
