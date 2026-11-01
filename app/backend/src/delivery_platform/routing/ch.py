"""Contraction-hierarchy solver behind the same contract as every other rung.

The product deliberately keeps plain A*: it needs no preprocessing, and a
delivery dispatcher that plans one route at a time cannot amortize a minute of
contraction. CH is the answer when the same graph is queried thousands of times,
which is exactly what the benchmark's break-even table quantifies.

Preprocessing is cached twice: in memory for the process, and on disk under
``.cache/ch/`` keyed by graph id, version and parameters. The disk entry stores
the original build cost in its stats, so a cache hit never pretends the build
was free.
"""

from __future__ import annotations

import gzip
import json
import os
import time
from pathlib import Path

from delivery_platform.routing.contraction import (
    DEFAULT_SETTLE_LIMIT,
    DEFAULT_WITNESS_HOPS,
    CHGraph,
    CHStats,
    preprocess,
)
from delivery_platform.routing.graph import StreetGraph
from delivery_platform.routing.path import (
    Objective,
    PathProblem,
    PathResult,
    geometry_for,
    path_totals,
)

CACHE_DIR = Path(os.environ.get("CH_CACHE_DIR", ".cache/ch"))

_CACHE: dict[tuple[int, str, int, int], CHGraph] = {}
_GRAPH_REFS: dict[int, StreetGraph] = {}


def _cache_file(
    graph: StreetGraph, objective: str, settle_limit: int, witness_hops: int
) -> Path:
    raw = f"{graph.graph_id}-{graph.version}-{objective}-{settle_limit}-{witness_hops}"
    safe = "".join(
        character if character.isalnum() or character in "-._" else "_" for character in raw
    )
    return CACHE_DIR / f"{safe}.json.gz"


def _load_cached(path: Path) -> CHGraph | None:
    if not path.exists():
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            document = json.load(handle)
        ids = tuple(str(node) for node in document["ids"])
        up_forward = tuple(
            tuple((int(target), float(weight)) for target, weight in edges)
            for edges in document["up_forward"]
        )
        up_backward = tuple(
            tuple((int(target), float(weight)) for target, weight in edges)
            for edges in document["up_backward"]
        )
        children = {
            (int(from_node), int(to_node)): (
                (int(left_from), int(left_to)),
                (int(right_from), int(right_to)),
            )
            for (
                from_node,
                to_node,
                left_from,
                left_to,
                right_from,
                right_to,
            ) in document["children"]
        }
        return CHGraph(
            ids=ids,
            index={node: position for position, node in enumerate(ids)},
            levels=tuple(int(level) for level in document["levels"]),
            up_forward=up_forward,
            up_backward=up_backward,
            children=children,
            stats=CHStats(**document["stats"]),
        )
    except (OSError, KeyError, TypeError, ValueError, EOFError):
        return None


def _save_cached(path: Path, hierarchy: CHGraph) -> None:
    document = {
        "ids": list(hierarchy.ids),
        "levels": list(hierarchy.levels),
        "up_forward": [[list(edge) for edge in edges] for edges in hierarchy.up_forward],
        "up_backward": [[list(edge) for edge in edges] for edges in hierarchy.up_backward],
        "children": [
            [from_node, to_node, left[0], left[1], right[0], right[1]]
            for (from_node, to_node), (left, right) in hierarchy.children.items()
        ],
        "stats": {
            "nodes": hierarchy.stats.nodes,
            "original_edges": hierarchy.stats.original_edges,
            "shortcuts": hierarchy.stats.shortcuts,
            "settle_limit": hierarchy.stats.settle_limit,
            "witness_hops": hierarchy.stats.witness_hops,
            "preprocessing_time_ns": hierarchy.stats.preprocessing_time_ns,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(document, handle, separators=(",", ":"))


def contraction_hierarchy(
    graph: StreetGraph,
    *,
    objective: Objective = "time",
    settle_limit: int = DEFAULT_SETTLE_LIMIT,
    witness_hops: int = DEFAULT_WITNESS_HOPS,
) -> CHGraph:
    """Cached hierarchy: in memory, then on disk, then a fresh build."""
    key = (id(graph), objective, settle_limit, witness_hops)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    path = _cache_file(graph, objective, settle_limit, witness_hops)
    hierarchy = _load_cached(path)
    if hierarchy is None:
        hierarchy = preprocess(
            graph,
            objective=objective,
            settle_limit=settle_limit,
            witness_hops=witness_hops,
        )
        try:
            _save_cached(path, hierarchy)
        except OSError:
            pass  # a read-only cache directory must not break routing
    # Hold a reference so the cached id() cannot be reused by another object.
    _GRAPH_REFS[id(graph)] = graph
    _CACHE[key] = hierarchy
    return hierarchy


class ChPathSolver:
    """Exact queries over a contraction hierarchy (per objective)."""

    solver_name = "contraction-hierarchy"
    solver_version = "1.0.0"

    def __init__(
        self,
        *,
        settle_limit: int = DEFAULT_SETTLE_LIMIT,
        witness_hops: int = DEFAULT_WITNESS_HOPS,
    ) -> None:
        self._settle_limit = settle_limit
        self._witness_hops = witness_hops

    def solve(self, problem: PathProblem, *, trace: bool = False) -> PathResult:
        started = time.perf_counter_ns()
        hierarchy = contraction_hierarchy(
            problem.graph,
            objective=problem.objective,
            settle_limit=self._settle_limit,
            witness_hops=self._witness_hops,
        )
        found = hierarchy.shortest_path(problem.origin, problem.destination, trace=trace)
        if found is None:
            raise ValueError(f"No path from {problem.origin} to {problem.destination}")
        node_path = tuple(found.nodes)
        distance, seconds = path_totals(problem.graph, node_path)
        return PathResult(
            node_path=node_path,
            geometry=geometry_for(problem.graph, node_path),
            distance_meters=distance,
            estimated_seconds=seconds,
            solver_name=self.solver_name,
            solver_version=self.solver_version,
            computation_time_ns=time.perf_counter_ns() - started,
            nodes_expanded=found.settled,
            objective=problem.objective,
            expanded_order=found.settle_order if trace else (),
            preprocessing_time_ns=hierarchy.stats.preprocessing_time_ns,
        )
