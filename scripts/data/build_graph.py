"""Generate the versioned synthetic street graph for the demo market.

A deterministic lattice over central São Paulo coordinates — fictional but
plausible — so the routing solver exercises real graph traversal without any
external map data. Re-run to regenerate ``data/graph/sao-paulo-centro.json``.

The defaults reproduce the committed demo graph; ``--rows/--cols/--seed`` and
friends generate larger synthetic graphs (for example for benchmarks) without
touching the checked-in file.
"""

import argparse
import json
import math
import random
from pathlib import Path

EARTH_RADIUS_M = 6_371_000.0

LAT_START, LAT_STEP = -23.5530, 0.0015
LON_START, LON_STEP = -46.6450, 0.0016
DIAGONAL_PROBABILITY = 0.12
AVENUE_ROWS = {2, 5}  # faster east-west corridors
AVENUE_COLS = {3, 7}  # faster north-south corridors
DEFAULT_SPEED_KMH = 25.0
AVENUE_SPEED_KMH = 40.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlon = math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def node_id(row: int, col: int) -> str:
    return f"n-{row:02d}-{col:02d}"


def build_document(
    rows: int, cols: int, seed: int, graph_id: str, version: str
) -> dict:
    rng = random.Random(seed)
    nodes = []
    lat_of: dict[str, float] = {}
    lon_of: dict[str, float] = {}
    for row in range(rows):
        for col in range(cols):
            nid = node_id(row, col)
            lat = round(LAT_START + row * LAT_STEP, 6)
            lon = round(LON_START + col * LON_STEP, 6)
            nodes.append({"id": nid, "latitude": lat, "longitude": lon})
            lat_of[nid] = lat
            lon_of[nid] = lon

    edges: list[dict] = []
    seen: set[frozenset[str]] = set()

    def add_pair(a: str, b: str, row: int, col: int) -> None:
        key = frozenset((a, b))
        if key in seen or a == b:
            return
        seen.add(key)
        # ceil so every stored edge is at least its straight-line length:
        # rounding down would break A* admissibility (heuristic overestimate).
        distance = math.ceil(
            haversine_m(lat_of[a], lon_of[a], lat_of[b], lon_of[b]) * 10
        ) / 10
        avenue = row in AVENUE_ROWS or col in AVENUE_COLS
        speed = AVENUE_SPEED_KMH if avenue else DEFAULT_SPEED_KMH
        edges.append(
            {
                "from": a,
                "to": b,
                "distance_meters": distance,
                "speed_kmh": speed,
            }
        )
        edges.append(
            {
                "from": b,
                "to": a,
                "distance_meters": distance,
                "speed_kmh": speed,
            }
        )

    for row in range(rows):
        for col in range(cols):
            here = node_id(row, col)
            if col + 1 < cols:
                add_pair(here, node_id(row, col + 1), row, col)
            if row + 1 < rows:
                add_pair(here, node_id(row + 1, col), row, col)
                if col + 1 < cols and rng.random() < DIAGONAL_PROBABILITY:
                    add_pair(here, node_id(row + 1, col + 1), row, col)
                if col - 1 >= 0 and rng.random() < DIAGONAL_PROBABILITY:
                    add_pair(here, node_id(row + 1, col - 1), row, col)

    return {
        "graph_id": graph_id,
        "version": version,
        "nodes": nodes,
        "edges": edges,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=7)
    parser.add_argument("--cols", type=int, default=11)
    parser.add_argument("--seed", type=int, default=20260901)
    parser.add_argument("--graph-id", default="sao-paulo-centro")
    parser.add_argument("--version", default="1.0.1")
    parser.add_argument(
        "--out",
        default=None,
        help="Output path; defaults to data/graph/<graph-id>.json at the repo root",
    )
    args = parser.parse_args()

    document = build_document(
        rows=args.rows,
        cols=args.cols,
        seed=args.seed,
        graph_id=args.graph_id,
        version=args.version,
    )
    if args.out:
        out = Path(args.out)
    else:
        out = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "graph"
            / f"{args.graph_id}.json"
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {out.as_posix()}: {len(document['nodes'])} nodes, "
        f"{len(document['edges'])} directed edges"
    )


if __name__ == "__main__":
    main()
