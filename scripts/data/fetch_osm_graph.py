"""Fetch the real São Paulo street graph used by the routing lab.

One-time, offline build step. Queries the Overpass API tile by tile (so a single
rate-limited sub-query cannot fail the whole run), merges the returned ways into
a directed edge list, contracts degree-2 chain nodes, keeps the largest strongly
connected component, and writes a graph document in the same schema as the
synthetic ``build_graph.py`` output — so ``load_graph`` reads both.

Runtime never talks to Overpass: the committed JSON is the artifact. Raw tile
responses are cached under ``data/graph/.osm-cache/`` so that iteration on the
post-processing steps does not re-query the API.

Data: © OpenStreetMap contributors, ODbL 1.0 — https://www.openstreetmap.org/copyright

Usage:
    python scripts/data/fetch_osm_graph.py
    python scripts/data/fetch_osm_graph.py --tiles 2 2 --refresh
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EARTH_RADIUS_M = 6_371_000.0
OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"
USER_AGENT = "entrega-clara-portfolio/1.0 (offline graph build)"
ATTRIBUTION = "© OpenStreetMap contributors (ODbL 1.0)"

# Fallback travel speeds by OSM highway class (km/h), used when a way has no
# usable ``maxspeed`` tag. Link roads are slower than their parent class.
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

# Central São Paulo, covering every seeded demo coordinate (restaurants,
# addresses and courier start points) with a wide margin of surrounding blocks.
DEFAULT_BBOX = (-23.5720, -46.6570, -23.5330, -46.6160)  # south, west, north, east
DEFAULT_TILES = (4, 4)

EdgeMap = dict[tuple[str, str], tuple[float, float]]
NodeMap = dict[str, tuple[float, float]]


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlon = math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def tile_bboxes(
    bbox: tuple[float, float, float, float], rows: int, cols: int
) -> list[tuple[float, float, float, float]]:
    south, west, north, east = bbox
    lat_step = (north - south) / rows
    lon_step = (east - west) / cols
    tiles = []
    for row in range(rows):
        for col in range(cols):
            tiles.append(
                (
                    south + row * lat_step,
                    west + col * lon_step,
                    south + (row + 1) * lat_step,
                    west + (col + 1) * lon_step,
                )
            )
    return tiles


def _query_for(bbox: tuple[float, float, float, float], timeout: int) -> str:
    south, west, north, east = bbox
    classes = "|".join(sorted(HIGHWAY_SPEEDS_KMH))
    return (
        f"[out:json][timeout:{timeout}];"
        f'way["highway"~"^({classes})$"]({south:.5f},{west:.5f},{north:.5f},{east:.5f});'
        "(._;>;);out body;"
    )


def fetch_tile(
    bbox: tuple[float, float, float, float],
    *,
    endpoint: str,
    timeout: int,
    attempts: int = 4,
) -> dict[str, Any]:
    """Query one bbox, retrying with backoff on rate limits and server errors."""
    payload = urllib.parse.urlencode({"data": _query_for(bbox, timeout)}).encode()
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
        },
    )
    delay = 15.0
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout + 60) as response:
                document = json.loads(response.read().decode("utf-8"))
            remark = str(document.get("remark", ""))
            if "error" in remark.lower():
                raise RuntimeError(f"Overpass remark: {remark}")
            return document
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            last_error = error
            if attempt == attempts:
                break
            print(f"    retry {attempt}/{attempts - 1} in {delay:.0f}s ({error})", flush=True)
            time.sleep(delay)
            delay *= 3
    raise RuntimeError(f"Overpass query failed for {bbox}: {last_error}")


def load_tile(
    cache_dir: Path,
    index: int,
    bbox: tuple[float, float, float, float],
    *,
    endpoint: str,
    timeout: int,
    refresh: bool,
) -> dict[str, Any]:
    cached = cache_dir / f"tile-{index:02d}.json"
    if cached.exists() and not refresh:
        print(f"  tile {index}: cached ({cached.name})", flush=True)
        return json.loads(cached.read_text(encoding="utf-8"))
    print(f"  tile {index}: fetching {bbox[0]:.4f},{bbox[1]:.4f},{bbox[2]:.4f},{bbox[3]:.4f}", flush=True)
    started = time.perf_counter()
    document = fetch_tile(bbox, endpoint=endpoint, timeout=timeout)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(document), encoding="utf-8")
    payload_mb = cached.stat().st_size / 1_048_576
    print(
        f"  tile {index}: {len(document.get('elements', []))} elements in "
        f"{time.perf_counter() - started:.0f}s ({payload_mb:.1f} MB)",
        flush=True,
    )
    return document


def merge_elements(documents: list[dict[str, Any]]) -> tuple[NodeMap, dict[str, dict[str, Any]]]:
    """De-duplicate nodes and ways across tile responses."""
    nodes: NodeMap = {}
    ways: dict[str, dict[str, Any]] = {}
    for document in documents:
        for element in document.get("elements", []):
            kind = element.get("type")
            if kind == "node" and "lat" in element and "lon" in element:
                nodes[str(element["id"])] = (float(element["lat"]), float(element["lon"]))
            elif kind == "way":
                ways[str(element["id"])] = {
                    "nodes": [str(ref) for ref in element.get("nodes", [])],
                    "tags": element.get("tags", {}),
                }
    return nodes, ways


def speed_kmh(tags: dict[str, Any]) -> float:
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


def oneway_directions(tags: dict[str, Any]) -> tuple[bool, bool]:
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


def build_edges(nodes: NodeMap, ways: dict[str, dict[str, Any]]) -> tuple[EdgeMap, int]:
    """Directed edges keyed by (from, to); the fastest variant wins a duplicate pair."""
    edges: EdgeMap = {}
    dropped_refs = 0
    for way in ways.values():
        tags = way["tags"]
        forward, backward = oneway_directions(tags)
        speed = speed_kmh(tags)
        refs = []
        for ref in way["nodes"]:
            if ref in nodes:
                refs.append(ref)
            else:
                dropped_refs += 1
        for a, b in itertools.pairwise(refs):
            if a == b:
                continue
            lat_a, lon_a = nodes[a]
            lat_b, lon_b = nodes[b]
            # ceil to 0.1 m so every stored edge is at least its straight-line
            # length: rounding down would let the A* heuristic overestimate.
            distance = math.ceil(haversine_m(lat_a, lon_a, lat_b, lon_b) * 10) / 10
            if distance <= 0:
                continue
            if forward:
                _put_edge(edges, (a, b), distance, speed)
            if backward:
                _put_edge(edges, (b, a), distance, speed)
    return edges, dropped_refs


def _put_edge(edges: EdgeMap, key: tuple[str, str], distance: float, speed: float) -> None:
    current = edges.get(key)
    if current is None or distance / speed < current[0] / current[1]:
        edges[key] = (distance, speed)


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
            _put_edge(edges, merged, *_merged_edge(edges, first, second))
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

    # Pass 1: finishing order over the forward graph.
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

    # Pass 2: components on the reversed graph, in reverse finishing order.
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
    """Self-check: every node must reach and be reached by every other node.

    Guards the artifact against a wrong component computation: a graph that
    silently lost its return paths would still look plausible in benchmarks.
    """
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

    sample = sorted(component)[:3]
    for node in sample:
        for direction, graph in (("forward", adjacency), ("backward", reverse)):
            reached = reachable(graph, node)
            if reached != component:
                raise RuntimeError(
                    f"Component is not strongly connected: {len(reached)} of "
                    f"{len(component)} nodes {direction}-reachable from {node}"
                )


def build_document(
    *,
    graph_id: str,
    version: str,
    nodes: NodeMap,
    edges: EdgeMap,
    bbox: tuple[float, float, float, float],
) -> dict[str, Any]:
    return {
        "graph_id": graph_id,
        "version": version,
        "source": "OpenStreetMap via the Overpass API",
        "attribution": ATTRIBUTION,
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        metavar=("SOUTH", "WEST", "NORTH", "EAST"),
        default=DEFAULT_BBOX,
    )
    parser.add_argument("--tiles", type=int, nargs=2, default=DEFAULT_TILES, metavar=("ROWS", "COLS"))
    parser.add_argument("--graph-id", default="sao-paulo-centro-osm")
    parser.add_argument("--version", default=None, help="Defaults to osm-<today>")
    parser.add_argument("--endpoint", default=OVERPASS_ENDPOINT)
    parser.add_argument("--timeout", type=int, default=300, help="Overpass query timeout, seconds")
    parser.add_argument("--refresh", action="store_true", help="Ignore the tile cache")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out = Path(args.out) if args.out else repo_root / "data" / "graph" / f"{args.graph_id}.json"
    version = args.version or f"osm-{datetime.now(UTC).date().isoformat()}"
    bbox = tuple(float(value) for value in args.bbox)
    rows, cols = args.tiles
    # Per-area cache so tiles fetched for another bbox or grid are never reused.
    area_key = "-".join(f"{value:.4f}" for value in bbox)
    cache_dir = out.parent / ".osm-cache" / f"{area_key}-{rows}x{cols}"

    tiles = tile_bboxes(bbox, rows, cols)
    print(f"Fetching {len(tiles)} tiles for {bbox}", flush=True)
    documents = [
        load_tile(
            cache_dir,
            index,
            tile,
            endpoint=args.endpoint,
            timeout=args.timeout,
            refresh=args.refresh,
        )
        for index, tile in enumerate(tiles)
    ]

    nodes, ways = merge_elements(documents)
    # Round coordinates before measuring: the artifact must stay self-consistent,
    # i.e. every stored edge length >= the straight line between the *stored*
    # coordinates, or the A* heuristic would overestimate.
    nodes = {
        node: (round(latitude, 6), round(longitude, 6))
        for node, (latitude, longitude) in nodes.items()
    }
    print(f"Raw: {len(nodes)} nodes, {len(ways)} ways", flush=True)
    edges, dropped_refs = build_edges(nodes, ways)
    if dropped_refs:
        print(f"Warning: {dropped_refs} way node references had no coordinate", flush=True)
    print(f"Directed edges: {len(edges)}", flush=True)

    remaining, edges, contracted = contract_degree_two(nodes, edges)
    print(
        f"Contract degree-2 chains: -{contracted} nodes, {len(remaining)} left, "
        f"{len(edges)} edges",
        flush=True,
    )

    components = largest_strongly_connected(remaining, edges)
    largest = max(components, key=len) if components else set()
    print(
        f"Strongly connected components: {len(components)}, largest {len(largest)} "
        f"({len(largest) / max(len(remaining), 1):.1%})",
        flush=True,
    )
    kept_edges = {
        key: value for key, value in edges.items() if key[0] in largest and key[1] in largest
    }
    verify_strongly_connected(largest, kept_edges)
    print("Self-check: kept component is strongly connected", flush=True)
    final_nodes = {node: nodes[node] for node in largest}

    if len(final_nodes) > 30_000:
        print(
            "Warning: more than 30k nodes — shrink --bbox or raise --tiles for a "
            "smaller artifact.",
            flush=True,
        )

    document = build_document(
        graph_id=args.graph_id,
        version=version,
        nodes=final_nodes,
        edges=kept_edges,
        bbox=bbox,  # type: ignore[arg-type]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    size_mb = out.stat().st_size / 1_048_576
    print(
        f"Wrote {out.as_posix()}: {len(document['nodes'])} nodes, "
        f"{len(document['edges'])} directed edges, {size_mb:.1f} MB, version {version}",
        flush=True,
    )


if __name__ == "__main__":
    main()
