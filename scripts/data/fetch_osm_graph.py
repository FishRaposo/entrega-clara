"""Fetch the real São Paulo street graph used by the routing lab.

One-time, offline build step. Queries the Overpass API tile by tile (so a single
rate-limited sub-query cannot fail the whole run), merges the returned ways into
a directed edge list, contracts degree-2 chain nodes, keeps the largest strongly
connected component, and writes a graph document that ``load_graph`` reads.

The graph rules (weights, oneway semantics, contraction, connectivity, document
shape) live in ``osm_graph.py`` and are shared with the city-scale builder; this
script owns only acquisition: tiling, retries and the per-area tile cache.

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
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from osm_graph import (
    HIGHWAY_SPEEDS_KMH,
    NodeMap,
    build_edges,
    build_object_document,
    contract_degree_two,
    trim_to_component,
)

OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"
USER_AGENT = "entrega-clara-portfolio/1.0 (offline graph build)"
ATTRIBUTION = "© OpenStreetMap contributors (ODbL 1.0)"

# Central São Paulo, covering every seeded demo coordinate (restaurants,
# addresses and courier start points) with a wide margin of surrounding blocks.
DEFAULT_BBOX = (-23.5720, -46.6570, -23.5330, -46.6160)  # south, west, north, east
DEFAULT_TILES = (4, 4)


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
    print(
        f"  tile {index}: fetching {bbox[0]:.4f},{bbox[1]:.4f},{bbox[2]:.4f},{bbox[3]:.4f}",
        flush=True,
    )
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
    edges, dropped_refs = build_edges(
        nodes, ((way["nodes"], way["tags"]) for way in ways.values())
    )
    if dropped_refs:
        print(f"Warning: {dropped_refs} way node references had no coordinate", flush=True)
    print(f"Directed edges: {len(edges)}", flush=True)

    remaining, edges, contracted = contract_degree_two(nodes, edges)
    print(
        f"Contract degree-2 chains: -{contracted} nodes, {len(remaining)} left, "
        f"{len(edges)} edges",
        flush=True,
    )

    largest, kept_edges, summary = trim_to_component(remaining, edges)
    print(
        f"Strongly connected components: {summary['components']}, largest {summary['largest']} "
        f"({summary['share']:.1%}) — self-check passed",
        flush=True,
    )
    final_nodes = {node: nodes[node] for node in largest}

    if len(final_nodes) > 30_000:
        print(
            "Warning: more than 30k nodes — shrink --bbox or raise --tiles for a "
            "smaller artifact.",
            flush=True,
        )

    document = build_object_document(
        graph_id=args.graph_id,
        version=version,
        nodes=final_nodes,
        edges=kept_edges,
        bbox=bbox,  # type: ignore[arg-type]
        source="OpenStreetMap via the Overpass API",
        attribution=ATTRIBUTION,
        fetched_at=datetime.now(UTC).isoformat(timespec="seconds"),
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
