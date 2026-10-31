"""Versioned synthetic street graph for the central São Paulo demo market.

The graph is deliberately small and fictional: enough structure to exercise a
real shortest-path solver without shipping external map data. Every route
result carries ``graph_id`` and ``version`` so consumers can pin the dataset
that produced it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from delivery_platform.domain.entities import GeoPoint


@dataclass(frozen=True)
class GraphEdge:
    to_node: str
    distance_meters: float
    speed_kmh: float

    @property
    def seconds(self) -> float:
        return self.distance_meters / (self.speed_kmh * 1000 / 3600)


@dataclass(frozen=True)
class StreetGraph:
    graph_id: str
    version: str
    nodes: dict[str, GeoPoint]
    adjacency: dict[str, tuple[GraphEdge, ...]]

    def neighbors(self, node: str) -> tuple[GraphEdge, ...]:
        return self.adjacency.get(node, ())

    def nearest_node(self, point: GeoPoint) -> str:
        """Snap an arbitrary coordinate to the closest graph node."""
        if not self.nodes:
            raise ValueError("Cannot snap to an empty graph")
        from delivery_platform.adapters.memory.routing import haversine_m

        return min(
            self.nodes,
            key=lambda node: haversine_m(point, self.nodes[node]),
        )


def load_graph(path: str | Path) -> StreetGraph:
    """Load and validate a versioned graph document."""
    raw: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("Graph document must be an object")
    graph_id = raw.get("graph_id")
    version = raw.get("version")
    if not isinstance(graph_id, str) or not graph_id:
        raise ValueError("Graph requires a graph_id")
    if not isinstance(version, str) or not version:
        raise ValueError("Graph requires a version")

    raw_nodes = raw.get("nodes")
    if not isinstance(raw_nodes, list) or len(raw_nodes) < 2:
        raise ValueError("Graph requires at least two nodes")
    nodes: dict[str, GeoPoint] = {}
    for entry in raw_nodes:
        if not isinstance(entry, dict):
            raise TypeError("Graph nodes must be objects")
        node_id = entry.get("id")
        lat, lon = entry.get("latitude"), entry.get("longitude")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("Graph node requires an id")
        if not isinstance(lat, int | float) or not isinstance(lon, int | float):
            raise TypeError(f"Graph node {node_id} requires numeric coordinates")
        if node_id in nodes:
            raise ValueError(f"Duplicate graph node {node_id}")
        nodes[node_id] = GeoPoint(latitude=float(lat), longitude=float(lon))

    raw_edges = raw.get("edges")
    if not isinstance(raw_edges, list) or not raw_edges:
        raise ValueError("Graph requires edges")
    adjacency: dict[str, list[GraphEdge]] = {node: [] for node in nodes}
    for entry in raw_edges:
        if not isinstance(entry, dict):
            raise TypeError("Graph edges must be objects")
        from_node, to_node = entry.get("from"), entry.get("to")
        distance, speed = entry.get("distance_meters"), entry.get("speed_kmh", 25.0)
        if from_node not in nodes or to_node not in nodes:
            raise ValueError("Graph edges must reference known nodes")
        if not isinstance(distance, int | float) or distance <= 0:
            raise ValueError("Graph edges require positive distance_meters")
        if not isinstance(speed, int | float) or speed <= 0:
            raise ValueError("Graph edges require positive speed_kmh")
        adjacency[from_node].append(
            GraphEdge(to_node=to_node, distance_meters=float(distance), speed_kmh=float(speed))
        )

    return StreetGraph(
        graph_id=graph_id,
        version=version,
        nodes=nodes,
        adjacency={node: tuple(edges) for node, edges in adjacency.items()},
    )
