"""Build a city-scale routing graph from a regional OpenStreetMap PBF extract.

Streams the extract twice (bbox nodes, then ways), applies the same correctness
rules as the centro demo graph — class whitelist, oneway semantics, ceiling of
edge lengths, degree-2 contraction, largest strongly connected component with a
self-check — and writes a gzipped *compact* document (index-aligned arrays)
that ``load_graph`` reads transparently.

Typical use (once, offline; the artifact is committed):

    python scripts/data/build_city_graph.py --pbf sudeste-latest.osm.pbf

Data: © OpenStreetMap contributors, ODbL 1.0 — https://www.openstreetmap.org/copyright
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from osm_graph import (
    HIGHWAY_SPEEDS_KMH,
    build_compact_document,
    build_edges,
    contract_degree_two,
    prune_isolated,
    trim_to_component,
)
from osm_pbf import read_extract

ATTRIBUTION = "© OpenStreetMap contributors (ODbL 1.0)"
SOURCE = "OpenStreetMap (Geofabrik regional extract)"

#: São Paulo municipality with a margin, so the largest component is not
#: clipped by the box itself. Override with --bbox for another city.
DEFAULT_BBOX = (-23.70, -46.85, -23.40, -46.35)  # south, west, north, east
DEFAULT_GRAPH_ID = "sao-paulo-city"
MAX_ARTIFACT_MB = 25.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pbf", required=True, help="Regional .osm.pbf extract")
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        metavar=("SOUTH", "WEST", "NORTH", "EAST"),
        default=DEFAULT_BBOX,
    )
    parser.add_argument("--graph-id", default=DEFAULT_GRAPH_ID)
    parser.add_argument("--version", default=None, help="Defaults to osm-city-<today>")
    parser.add_argument("--out", default=None)
    parser.add_argument("--max-artifact-mb", type=float, default=MAX_ARTIFACT_MB)
    args = parser.parse_args()

    pbf = Path(args.pbf)
    if not pbf.exists():
        raise SystemExit(f"PBF extract not found: {pbf}")
    repo_root = Path(__file__).resolve().parents[2]
    out = Path(args.out) if args.out else repo_root / "data" / "graph" / f"{args.graph_id}.json.gz"
    version = args.version or f"osm-city-{datetime.now(UTC).date().isoformat()}"
    bbox = tuple(float(value) for value in args.bbox)
    classes = set(HIGHWAY_SPEEDS_KMH)
    started = time.perf_counter()

    print(f"Reading {pbf.name} inside {bbox} …", flush=True)
    extract = read_extract(pbf, bbox=bbox, classes=classes)
    print(f"  nodes read {extract.stats.nodes_read:,} · kept {extract.stats.nodes_kept:,}")
    print(
        f"  ways read {extract.stats.ways_read:,} · kept {extract.stats.ways_kept:,} "
        f"({extract.stats.segments_kept:,} contiguous segments)"
    )
    if not extract.nodes:
        raise SystemExit("No nodes inside the bbox — check --bbox against the extract")

    # Round before measuring so the artifact is self-consistent: every stored
    # edge must be at least the straight line between the stored coordinates.
    nodes = {
        node: (round(latitude, 6), round(longitude, 6))
        for node, (latitude, longitude) in extract.nodes.items()
    }
    edges, dropped = build_edges(
        nodes, ((segment.refs, segment.tags) for segment in extract.segments)
    )
    print(f"Directed edges: {len(edges):,} ({dropped:,} refs outside the box)")

    # The node pass sees every OSM node in the box; only those on a road matter.
    nodes, isolated = prune_isolated(nodes, edges)
    print(f"Nodes on roads: {len(nodes):,} ({isolated:,} isolated dropped)")

    remaining, edges, contracted = contract_degree_two(nodes, edges)
    print(
        f"Degree-2 contraction: -{contracted:,} nodes → {len(remaining):,} left, "
        f"{len(edges):,} edges"
    )

    largest, kept_edges, summary = trim_to_component(remaining, edges)
    print(
        f"Strongly connected components: {summary['components']:,} · "
        f"largest {summary['largest']:,} ({summary['share']:.1%}) · self-check passed"
    )

    final_nodes = {node: nodes[node] for node in largest}
    document = build_compact_document(
        graph_id=args.graph_id,
        version=version,
        nodes=final_nodes,
        edges=kept_edges,
        bbox=bbox,  # type: ignore[arg-type]
        source=SOURCE,
        attribution=ATTRIBUTION,
        fetched_at=datetime.now(UTC).isoformat(timespec="seconds"),
        extra={
            "osm_base": (
                datetime.fromtimestamp(extract.stats.osm_base, UTC).isoformat(timespec="seconds")
                if extract.stats.osm_base
                else None
            ),
            "stats": {
                "nodes_read": extract.stats.nodes_read,
                "ways_read": extract.stats.ways_read,
                "nodes_on_roads": len(nodes),
                "nodes_before_contraction": len(remaining),
            },
        },
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    with gzip.open(out, "wb", compresslevel=9) as handle:
        handle.write(payload)
    size_mb = out.stat().st_size / 1_048_576
    print(
        f"Wrote {out.as_posix()}: {len(final_nodes):,} nodes, {len(kept_edges):,} edges, "
        f"{size_mb:.1f} MB gzipped ({len(payload) / 1_048_576:.0f} MB JSON), "
        f"version {version}, {time.perf_counter() - started:.0f}s"
    )
    if size_mb > args.max_artifact_mb:
        print(
            f"WARNING: artifact is {size_mb:.1f} MB, above the {args.max_artifact_mb:.0f} MB "
            "budget. Shrink --bbox, or keep the file out of git and document the build step."
        )


if __name__ == "__main__":
    main()
