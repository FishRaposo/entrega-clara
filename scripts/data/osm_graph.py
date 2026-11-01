"""Shared plumbing for turning OpenStreetMap element data into a routing graph.

Both builders use this module: ``fetch_osm_graph.py`` (Overpass tiles, the
centro-SP demo artifact) and ``build_city_graph.py`` (a regional PBF extract).
It owns the parts that decide correctness: edge weights and directional rules,
degree-2 contraction, the strongly connected component filter and its
self-check, and the two document formats (object-per-node for the demo graph,
compact index arrays for the city graph).
"""

from __future__ import annotations

import itertools
import math
from collections import deque
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

EARTH_RADIUS_M = 6_371_000.0

#: Fallback travel speeds by OSM highway class (km/h), used when a way has no
#: usable ``maxspeed`` tag. Link roads are slower than their parent class.
HIGHWAY_SPEEDS_KMH: dict[str, float] = {
    "motorway": 90.0,
    "motorway_link": 60.0,
    "trunk": 80.0,
    "trunk_link": 50.0,
    "primary": 60.0,
    "primary_link": 40.0,
    "secondary": 50.0,
    "secondary_link": 35.0,
    "tertiary": 40.0,
    "tertiary_link": 30.0,
    "unclassified": 30.0,
    "residential": 30.0,
    "living_street": 10.0,
    "service": 20.0,
}
DEFAULT_SPEED_KMH = 30.0
ONEWAY_FORWARD = {"yes", "true", "1"}
ONEWAY_REVERSE = {"-1", "reverse"}

EdgeMap = dict[tuple[str, str], tuple[float, float]]
NodeMap = dict[str, tuple[float, float]]


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlon = math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def speed_kmh(tags: Mapping[str, Any]) -> float:
    """Travel speed for a way: literal ``maxspeed`` when usable, class table otherwise."""
    raw = str(tags.get("maxspeed", "")).strip().lower()
    if raw:
        text = raw.split(";")[0].strip()
        factor = 1.609344 if "mph" in text else 1.0
        number = text.replace("km/h", "").replace("kmh", "").replace("mph", "").strip()
        try:
            value = float(number) * factor
        except ValueError:
            value = 0.0
        if 5.0 <= value <= 130.0:
            return value
    return HIGHWAY_SPEEDS_KMH.get(str(tags.get("highway", "")), DEFAULT_SPEED_KMH)


def oneway_directions(tags: Mapping[str, Any]) -> tuple[bool, bool]:
    """(allow forward, allow backward) for a way's node order."""
    if str(tags.get("junction", "")).strip().lower() in {"roundabout", "circular"}:
        return True, False
    value = str(tags.get("oneway", "")).strip().lower()
    if value in ONEWAY_FORWARD:
        return True, False
    if value in ONEWAY_REVERSE:
        return False, True
    if "oneway" not in tags and str(tags.get("highway", "")) in {"motorway", "motorway_link"}:
        return True, False
    return True, True


def put_edge(edges: EdgeMap, key: tuple[str, str], distance: float, speed: float) -> None:
    """Keep the fastest variant when several ways connect the same node pair."""
    current = edges.get(key)
    if current is None or distance / speed < current[0] / current[1]:
        edges[key] = (distance, speed)


def build_edges(
    nodes: NodeMap,
    segments: Iterable[tuple[Sequence[str], Mapping[str, Any]]],
) -> tuple[EdgeMap, int]:
    """Directed edges from ``(refs, tags)`` segments; the fastest duplicate wins.

    Distances are ceiled to 0.1 m so every stored edge is at least its
    straight-line length: rounding down would let the A* heuristic overestimate.
    """
    edges: EdgeMap = {}
    dropped_refs = 0
    for refs, tags in segments:
        forward, backward = oneway_directions(tags)
        speed = speed_kmh(tags)
        kept: list[str] = []
        for ref in refs:
            if ref in nodes:
                kept.append(ref)
            else:
                dropped_refs += 1
        for a, b in itertools.pairwise(kept):
            if a == b:
                continue
            lat_a, lon_a = nodes[a]
            lat_b, lon_b = nodes[b]
            distance = math.ceil(haversine_m(lat_a, lon_a, lat_b, lon_b) * 10) / 10
            if distance <= 0:
                continue
            if forward:
                put_edge(edges, (a, b), distance, speed)
            if backward:
                put_edge(edges, (b, a), distance, speed)
    return edges, dropped_refs


def _merged_edge(
    edges: EdgeMap, first: tuple[str, str], second: tuple[str, str]
) -> tuple[float, float]:
    """Join two chained legs, preserving travel time exactly."""
    d1, s1 = edges[first]
    d2, s2 = edges[second]
    distance = round(d1 + d2, 1)
    seconds = d1 / (s1 * 1000 / 3600) + d2 / (s2 * 1000 / 3600)
    return distance, round(distance / seconds * 3.6, 2)


def contract_degree_two(
    nodes: NodeMap, edges: EdgeMap
) -> tuple[set[str], EdgeMap, int]:
    """Collapse chain nodes: A—X—B becomes A—B carrying the summed travel time.

    Only nodes with exactly two distinct neighbors in a consistent through
    pattern are contracted — a full bidirectional through (four edges) or a
    pure one-way through (one in, one out, different neighbors). Intersections
    and one-way conflicts are never touched.
    """
    incoming: dict[str, set[str]] = {node: set() for node in nodes}
    outgoing: dict[str, set[str]] = {node: set() for node in nodes}
    for a, b in edges:
        incoming[b].add(a)
        outgoing[a].add(b)

    remaining = set(nodes)
    candidates = deque(sorted(nodes))
    contracted = 0
    while candidates:
        node = candidates.popleft()
        if node not in remaining:
            continue
        sources, targets = incoming[node], outgoing[node]
        pairs: list[tuple[tuple[str, str], tuple[str, str], tuple[str, str]]] = []
        if sources == targets and len(sources) == 2:
            a, b = sorted(sources)
            if a == b:
                continue
            pairs = [
                ((a, node), (node, b), (a, b)),
                ((b, node), (node, a), (b, a)),
            ]
        elif len(sources) == 1 and len(targets) == 1:
            (source,) = tuple(sources)
            (target,) = tuple(targets)
            if source == target:
                continue
            pairs = [((source, node), (node, target), (source, target))]
        else:
            continue

        for first, second, merged in pairs:
            put_edge(edges, merged, *_merged_edge(edges, first, second))
            del edges[first]
            del edges[second]
        for neighbor in sources | targets:
            if neighbor == node:
                continue
            outgoing[neighbor].discard(node)
            incoming[neighbor].discard(node)
            if neighbor in remaining:
                candidates.append(neighbor)
        remaining.discard(node)
        incoming.pop(node)
        outgoing.pop(node)
        contracted += 1
    return remaining, edges, contracted


def largest_strongly_connected(nodes: set[str], edges: EdgeMap) -> list[set[str]]:
    """Strongly connected components (iterative Kosaraju)."""
    adjacency: dict[str, list[str]] = {node: [] for node in nodes}
    reverse: dict[str, list[str]] = {node: [] for node in nodes}
    for a, b in edges:
        if a in adjacency and b in adjacency:
            adjacency[a].append(b)
            reverse[b].append(a)

    order: list[str] = []
    seen: set[str] = set()
    for root in sorted(nodes):
        if root in seen:
            continue
        seen.add(root)
        work: list[tuple[str, int]] = [(root, 0)]
        while work:
            node, position = work[-1]
            children = adjacency[node]
            if position < len(children):
                work[-1] = (node, position + 1)
                child = children[position]
                if child not in seen:
                    seen.add(child)
                    work.append((child, 0))
            else:
                work.pop()
                order.append(node)

    components: list[set[str]] = []
    assigned: set[str] = set()
    for root in reversed(order):
        if root in assigned:
            continue
        component = {root}
        assigned.add(root)
        stack = [root]
        while stack:
            node = stack.pop()
            for child in reverse[node]:
                if child not in assigned:
                    assigned.add(child)
                    component.add(child)
                    stack.append(child)
        components.append(component)
    return components


def verify_strongly_connected(component: set[str], edges: EdgeMap) -> None:
    """Self-check: every node must reach and be reached by every other node."""
    if not component:
        raise RuntimeError("Largest component is empty")
    adjacency: dict[str, list[str]] = {node: [] for node in component}
    reverse: dict[str, list[str]] = {node: [] for node in component}
    for a, b in edges:
        if a in adjacency and b in adjacency:
            adjacency[a].append(b)
            reverse[b].append(a)

    def reachable(graph: dict[str, list[str]], start: str) -> set[str]:
        seen = {start}
        stack = [start]
        while stack:
            node = stack.pop()
            for child in graph[node]:
                if child not in seen:
                    seen.add(child)
                    stack.append(child)
        return seen

    for node in sorted(component)[:3]:
        for direction, graph in (("forward", adjacency), ("backward", reverse)):
            reached = reachable(graph, node)
            if reached != component:
                raise RuntimeError(
                    f"Component is not strongly connected: {len(reached)} of "
                    f"{len(component)} nodes {direction}-reachable from {node}"
                )


def prune_isolated(nodes: NodeMap, edges: EdgeMap) -> tuple[NodeMap, int]:
    """Drop nodes no edge touches.

    A bbox node pass sees every OSM node in the box — buildings, POIs, benches —
    and only a small share of them end up on a road. Contracting millions of
    degree-zero nodes is pure waste, so they are removed before that step.
    """
    referenced = {node for edge in edges for node in edge}
    kept = {node: point for node, point in nodes.items() if node in referenced}
    return kept, len(nodes) - len(kept)


def trim_to_component(
    nodes: NodeMap, edges: EdgeMap
) -> tuple[set[str], EdgeMap, dict[str, Any]]:
    """Keep the largest strongly connected component and prove it is closed."""
    components = largest_strongly_connected(set(nodes), edges)
    largest = max(components, key=len) if components else set()
    kept_edges = {
        key: value for key, value in edges.items() if key[0] in largest and key[1] in largest
    }
    verify_strongly_connected(largest, kept_edges)
    summary = {
        "components": len(components),
        "largest": len(largest),
        "share": round(len(largest) / max(len(nodes), 1), 4),
    }
    return largest, kept_edges, summary


def build_object_document(
    *,
    graph_id: str,
    version: str,
    nodes: NodeMap,
    edges: EdgeMap,
    bbox: tuple[float, float, float, float],
    source: str,
    attribution: str,
    fetched_at: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Object-per-node document (the format the centro demo graph uses)."""
    document: dict[str, Any] = {
        "graph_id": graph_id,
        "version": version,
        "source": source,
        "attribution": attribution,
        "fetched_at": fetched_at,
        "bbox": {
            "south": bbox[0],
            "west": bbox[1],
            "north": bbox[2],
            "east": bbox[3],
        },
        "nodes": [
            {
                "id": node,
                "latitude": round(nodes[node][0], 6),
                "longitude": round(nodes[node][1], 6),
            }
            for node in sorted(nodes)
        ],
        "edges": [
            {
                "from": a,
                "to": b,
                "distance_meters": round(distance, 1),
                "speed_kmh": round(speed, 2),
            }
            for (a, b), (distance, speed) in sorted(edges.items())
        ],
    }
    if extra:
        document.update(extra)
    return document


def build_compact_document(
    *,
    graph_id: str,
    version: str,
    nodes: NodeMap,
    edges: EdgeMap,
    bbox: tuple[float, float, float, float],
    source: str,
    attribution: str,
    fetched_at: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Index-aligned document for large graphs: ``ids[i]`` names ``nodes[i]``."""
    ids = sorted(nodes)
    index_of = {node: position for position, node in enumerate(ids)}
    document: dict[str, Any] = {
        "format": "compact-v1",
        "graph_id": graph_id,
        "version": version,
        "source": source,
        "attribution": attribution,
        "fetched_at": fetched_at,
        "bbox": {
            "south": bbox[0],
            "west": bbox[1],
            "north": bbox[2],
            "east": bbox[3],
        },
        "ids": ids,
        "nodes": [
            [round(nodes[node][0], 6), round(nodes[node][1], 6)] for node in ids
        ],
        "edges": [
            [index_of[a], index_of[b], round(distance, 1), round(speed, 2)]
            for (a, b), (distance, speed) in sorted(edges.items())
        ],
    }
    if extra:
        document.update(extra)
    return document
