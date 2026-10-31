"""Generate the versioned synthetic street graph for the demo market.

A deterministic lattice over central São Paulo coordinates — fictional but
plausible — so the routing solver exercises real graph traversal without any
external map data. Re-run to regenerate ``data/graph/sao-paulo-centro.json``.
"""

import json
import math
import random
from pathlib import Path

EARTH_RADIUS_M = 6_371_000.0
GRAPH_ID = "sao-paulo-centro"
VERSION = "1.0.0"
SEED = 20260901

LAT_START, LAT_STEP, LAT_COUNT = -23.5530, 0.0015, 7
LON_START, LON_STEP, LON_COUNT = -46.6450, 0.0016, 11
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


def main() -> None:
    rng = random.Random(SEED)
    nodes = []
    lat_of: dict[str, float] = {}
    lon_of: dict[str, float] = {}
    for row in range(LAT_COUNT):
        for col in range(LON_COUNT):
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
        distance = round(haversine_m(lat_of[a], lon_of[a], lat_of[b], lon_of[b]), 1)
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

    for row in range(LAT_COUNT):
        for col in range(LON_COUNT):
            here = node_id(row, col)
            if col + 1 < LON_COUNT:
                add_pair(here, node_id(row, col + 1), row, col)
            if row + 1 < LAT_COUNT:
                add_pair(here, node_id(row + 1, col), row, col)
                if col + 1 < LON_COUNT and rng.random() < DIAGONAL_PROBABILITY:
                    add_pair(here, node_id(row + 1, col + 1), row, col)
                if col - 1 >= 0 and rng.random() < DIAGONAL_PROBABILITY:
                    add_pair(here, node_id(row + 1, col - 1), row, col)

    document = {
        "graph_id": GRAPH_ID,
        "version": VERSION,
        "nodes": nodes,
        "edges": edges,
    }
    out = Path(__file__).resolve().parents[2] / "data" / "graph" / f"{GRAPH_ID}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out.as_posix()}: {len(nodes)} nodes, {len(edges)} directed edges")


if __name__ == "__main__":
    main()
