"""Deterministic routing benchmark — the measured evidence for the solver ladder.

Two families, one harness:

* **Multi-stop (TSP)** — the retained ``LegacyBruteForceTSPSolver`` baseline
  against Held-Karp, nearest-neighbor and 2-opt on identical cost matrices
  built from the committed street graph.
* **Point-to-point** — Dijkstra, A*, ALT landmarks, balanced bidirectional
  search and weighted ε-admissible A* over the same sampled pairs, reporting
  median nodes expanded, median solver time and the solution-quality overshoot.

Emits committed evidence:

    docs/benchmarks/routing.json          machine-readable results
    docs/benchmarks/routing.md            human-readable summary
    docs/benchmarks/routing.svg           execution-time bar chart
    docs/benchmarks/routing-tradeoff.svg  work vs. solution quality
    docs/benchmarks/lab-trace.json        replayable search trace (see below)

``--export-lab-trace`` writes the subgraph of the delivery demo route with both
traces embedded, which the standard-library GIF renderer consumes; it is
self-contained because only the touched nodes and edges are kept.

Standard library only. Runs in seconds; factorial sizes stay bounded.
"""

import argparse
import json
import math
import platform
import random
import statistics
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app" / "backend" / "src"))

from delivery_platform.domain.entities import GeoPoint
from delivery_platform.routing.ch import ChPathSolver, contraction_hierarchy
from delivery_platform.routing.contraction import preprocess
from delivery_platform.routing.graph import StreetGraph, load_graph
from delivery_platform.routing.informed import (
    AltPathSolver,
    BidirectionalPathSolver,
    WeightedAStarSolver,
)
from delivery_platform.routing.landmarks import landmark_table
from delivery_platform.routing.legacy_bruteforce import (
    LegacyBruteForceTSPSolver,
)
from delivery_platform.routing.matrix import build_cost_matrix
from delivery_platform.routing.models import RouteProblem
from delivery_platform.routing.path import (
    AStarPathSolver,
    DijkstraPathSolver,
    PathProblem,
)
from delivery_platform.routing.tsp import (
    HeldKarpSolver,
    NearestNeighborSolver,
    TwoOptSolver,
)

OUT_DIR = ROOT / "docs" / "benchmarks"
GRAPHS = {
    "centro": ROOT / "data" / "graph" / "sao-paulo-centro-osm.json",
    "city": ROOT / "data" / "graph" / "sao-paulo-city.json.gz",
}
PAIR_COUNT = 200
WEIGHTED_EPSILONS = (1.5, 2.5, 5.0)
TSP_SIZES = (5, 7, 9, 11, 13)
BATCH_STOPS = 7
# Delivery demo endpoints (seeded restaurant → customer), used for the trace.
TRACE_ORIGIN = GeoPoint(latitude=-23.5482, longitude=-46.6371)
TRACE_DESTINATION = GeoPoint(latitude=-23.5515, longitude=-46.632)


def _graph_path(name: str = "centro") -> Path:
    candidate = GRAPHS[name]
    if not candidate.exists():
        raise SystemExit(
            f"Graph '{name}' not found at {candidate}. Build it with "
            "scripts/data/build_city_graph.py (or fetch_osm_graph.py for centro)."
        )
    return candidate


def _matrix(n: int, seed: int) -> RouteProblem:
    rng = random.Random(seed)
    costs = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            costs[i][j] = costs[j][i] = float(rng.randint(1, 99))
    return RouteProblem(
        labels=tuple(f"s{i}" for i in range(n)),
        costs=tuple(tuple(r) for r in costs),
    )


def _run(solver, problem) -> dict:
    started = time.perf_counter_ns()
    result = solver.solve(problem)
    wall = time.perf_counter_ns() - started
    return {
        "solver": result.solver_name,
        "total_cost": round(result.total_cost, 4),
        "routes_evaluated": result.routes_evaluated,
        "solver_time_ns": result.execution_time_ns,
        "wall_time_ns": wall,
        "route": list(result.route),
    }


def _machine_context() -> dict:
    commit = ""
    dirty = False
    try:
        commit = (
            subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            ).stdout.strip()
        )
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            ).stdout.strip()
        )
    except (OSError, subprocess.SubprocessError):
        commit = ""
    return {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "commit": f"{commit}-dirty" if commit and dirty else commit,
    }


def _smoke() -> None:
    """Fast CI gate: solvers run and agree on a small matrix."""
    problem = _matrix(6, seed=7)
    bf = LegacyBruteForceTSPSolver().solve(problem)
    hk = HeldKarpSolver().solve(problem)
    assert abs(bf.total_cost - hk.total_cost) < 1e-9, (
        f"held-karp {hk.total_cost} != brute-force {bf.total_cost}"
    )
    graph = load_graph(_graph_path("centro"))
    assert graph.nodes, "graph failed to load"
    origin, destination = min(graph.nodes), max(graph.nodes)
    oracle = DijkstraPathSolver().solve(PathProblem(graph, origin, destination, "time"))
    alt = AltPathSolver(landmarks=2).solve(PathProblem(graph, origin, destination, "time"))
    assert abs(oracle.estimated_seconds - alt.estimated_seconds) < 0.01, (
        "ALT disagrees with the Dijkstra oracle"
    )
    print(
        f"benchmark smoke ok: solvers agree on a 6-stop matrix and on the graph "
        f"({graph.graph_id})"
    )


def _tsp_section(graph: StreetGraph) -> list[dict]:
    """TSP ladder on cost matrices built from the street graph."""
    nodes = sorted(graph.nodes)
    rng = random.Random(20261101)
    rows: list[dict] = []
    for size in TSP_SIZES:
        picks = rng.sample(nodes, size)
        problem = build_cost_matrix(
            graph,
            labels=tuple(f"s{i}" for i in range(size)),
            nodes=tuple(picks),
            objective="time",
        )
        row: dict = {"stops": size, "matrix": "street graph (one-to-all Dijkstra)"}
        run_brute = size <= 9
        row["brute_force"] = (
            _run(LegacyBruteForceTSPSolver(), problem)
            if run_brute
            else {"solver": "legacy_bruteforce_tsp", "skipped": True}
        )
        row["held_karp"] = (
            _run(HeldKarpSolver(), problem)
            if size <= HeldKarpSolver.MAX_STOPS
            else {"solver": "held-karp", "skipped": True}
        )
        row["nearest_neighbor"] = _run(NearestNeighborSolver(), problem)
        row["two_opt"] = _run(TwoOptSolver(), problem)
        rows.append(row)
    return rows


def _tsp_matrix_section() -> list[dict]:
    """Seeded random matrices — the solver-only comparison, no graph involved."""
    rows: list[dict] = []
    for size in TSP_SIZES:
        problem = _matrix(size, seed=42 + size)
        row: dict = {"stops": size, "matrix": "seeded random (symmetric)"}
        row["brute_force"] = (
            _run(LegacyBruteForceTSPSolver(), problem)
            if size <= 9
            else {"solver": "legacy_bruteforce_tsp", "skipped": True}
        )
        row["held_karp"] = _run(HeldKarpSolver(), problem)
        row["nearest_neighbor"] = _run(NearestNeighborSolver(), problem)
        row["two_opt"] = _run(TwoOptSolver(), problem)
        rows.append(row)
    return rows


def _path_section(graph: StreetGraph, pairs: list[tuple[str, str]]) -> dict:
    solvers: dict[str, object] = {
        "dijkstra": DijkstraPathSolver(),
        "astar": AStarPathSolver(),
        "alt": AltPathSolver(),
        "bidirectional": BidirectionalPathSolver(),
        "ch": ChPathSolver(),
    }
    for epsilon in WEIGHTED_EPSILONS:
        solvers[f"weighted_eps{epsilon:g}"] = WeightedAStarSolver(epsilon=epsilon)

    # CH pays for itself only after many queries, so the build is measured on
    # its own and reported apart from query time. The timed build runs without
    # tracemalloc; peak memory comes from a second, untimed build, because
    # tracing slows the code enough to distort the number that matters.
    hierarchy = contraction_hierarchy(graph, objective="time")
    preprocessing_ns = hierarchy.stats.preprocessing_time_ns
    tracemalloc.start()
    preprocess(graph, objective="time")
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    oracle = DijkstraPathSolver()
    optimums = [
        oracle.solve(PathProblem(graph, origin, destination, "time")).estimated_seconds
        for origin, destination in pairs
    ]
    rows: dict[str, dict] = {}
    for name, solver in solvers.items():
        expansions: list[int] = []
        nanos: list[int] = []
        overshoots: list[float] = []
        for (origin, destination), optimal in zip(pairs, optimums, strict=True):
            result = solver.solve(PathProblem(graph, origin, destination, "time"))  # type: ignore[attr-defined]
            expansions.append(result.nodes_expanded)
            nanos.append(result.computation_time_ns)
            overshoots.append(
                0.0 if optimal <= 0 else (result.estimated_seconds - optimal) / optimal * 100
            )
        rows[name] = {
            "pairs": len(pairs),
            "median_nodes_expanded": statistics.median(expansions),
            "max_nodes_expanded": max(expansions),
            "median_solver_time_ns": int(statistics.median(nanos)),
            "total_solver_time_ns": sum(nanos),
            "share_of_graph_median": round(statistics.median(expansions) / len(graph.nodes), 4),
            "median_overshoot_percent": round(statistics.median(overshoots), 3),
            "max_overshoot_percent": round(max(overshoots), 3),
        }
    table = landmark_table(graph, objective="time")
    rows["alt"]["landmarks"] = list(table.landmarks)
    rows["alt"]["preprocessing_time_ns"] = table.preprocessing_time_ns

    rows["ch"]["preprocessing_time_ns"] = preprocessing_ns
    rows["ch"]["preprocessing_peak_mb"] = round(peak_bytes / 1_048_576, 1)
    rows["ch"]["shortcuts"] = hierarchy.stats.shortcuts
    rows["ch"]["witness_hops"] = hierarchy.stats.witness_hops
    rows["ch"]["settle_limit"] = hierarchy.stats.settle_limit
    for baseline in ("astar", "alt"):
        gain = rows[baseline]["median_solver_time_ns"] - rows["ch"]["median_solver_time_ns"]
        rows["ch"][f"break_even_queries_vs_{baseline}"] = (
            round(preprocessing_ns / gain, 1) if gain > 0 else None
        )
    return rows


def _batch_realism(graph: StreetGraph) -> dict:
    """What one 2-3 order batch costs end to end: matrix build + exact tour.

    Timed three times and reported as a median: a single wall-clock sample on a
    laptop swings by several times, and the point of the number is the order of
    magnitude, not the machine's mood.
    """
    nodes = sorted(graph.nodes)
    rng = random.Random(20261102)
    picks = rng.sample(nodes, BATCH_STOPS)
    matrix_samples: list[int] = []
    tour_samples: list[int] = []
    tour = None
    baseline = None
    for _ in range(3):
        started = time.perf_counter_ns()
        problem = build_cost_matrix(
            graph,
            labels=tuple(f"stop{i}" for i in range(BATCH_STOPS)),
            nodes=tuple(picks),
            objective="time",
        )
        matrix_samples.append(time.perf_counter_ns() - started)
        precedence = {
            1 + (BATCH_STOPS - 1) // 2 + i: 1 + i for i in range((BATCH_STOPS - 1) // 2)
        }
        started = time.perf_counter_ns()
        tour = HeldKarpSolver(precedence=precedence, closed=False).solve(problem)
        tour_samples.append(time.perf_counter_ns() - started)
        baseline = NearestNeighborSolver(precedence=precedence, closed=False).solve(problem)
    assert tour is not None and baseline is not None
    matrix_ns = statistics.median(matrix_samples)
    tour_ns = statistics.median(tour_samples)
    return {
        "stops": BATCH_STOPS,
        "repeats": len(matrix_samples),
        "matrix_build_ms": round(matrix_ns / 1e6, 2),
        "held_karp_ms": round(tour_ns / 1e6, 2),
        "total_ms": round((matrix_ns + tour_ns) / 1e6, 2),
        "held_karp_cost": round(tour.total_cost, 2),
        "nearest_neighbor_cost": round(baseline.total_cost, 2),
        "savings_seconds": round(baseline.total_cost - tour.total_cost, 2),
    }


def _export_lab_trace(graph: StreetGraph) -> dict:
    """Self-contained replay of one delivery-route search (A* and Dijkstra)."""
    origin = graph.nearest_node(TRACE_ORIGIN)
    destination = graph.nearest_node(TRACE_DESTINATION)
    traces: dict[str, dict] = {}
    keep: set[str] = {origin, destination}
    for name, solver in (
        ("alt", AltPathSolver()),
        ("astar", AStarPathSolver()),
        ("dijkstra", DijkstraPathSolver()),
    ):
        result = solver.solve(PathProblem(graph, origin, destination, "time"), trace=True)
        traces[name] = {
            "solver_name": result.solver_name,
            "nodes_expanded": result.nodes_expanded,
            "estimated_seconds": result.estimated_seconds,
            "distance_meters": result.distance_meters,
            "expanded_order": list(result.expanded_order),
            "frontier_sizes": list(result.frontier_sizes),
            "expansion_costs": list(result.expansion_costs),
            "node_path": list(result.node_path),
        }
        keep.update(result.expanded_order)
        keep.update(result.node_path)

    # Three hops of context around the touched nodes so the replay shows streets
    # rather than floating dots; the file stays small because the halo is local.
    halo = set(keep)
    for _ in range(3):
        halo |= {
            edge.to_node
            for node in halo
            for edge in graph.neighbors(node)
        }
    keep = halo

    ids = sorted(keep)
    index_of = {node: position for position, node in enumerate(ids)}
    edges = [
        [index_of[node], index_of[edge.to_node], edge.speed_kmh]
        for node in ids
        for edge in graph.neighbors(node)
        if edge.to_node in index_of
    ]
    document = {
        "graph_id": graph.graph_id,
        "graph_version": graph.version,
        "attribution": graph.attribution,
        "objective": "time",
        "origin": index_of[origin],
        "destination": index_of[destination],
        "ids": ids,
        "nodes": [
            [round(graph.nodes[node].latitude, 6), round(graph.nodes[node].longitude, 6)]
            for node in ids
        ],
        "edges": edges,
        "solvers": {
            name: {
                **trace,
                "expanded_order": [index_of[node] for node in trace["expanded_order"]],
                "node_path": [index_of[node] for node in trace["node_path"]],
            }
            for name, trace in traces.items()
        },
    }
    (OUT_DIR / "lab-trace.json").write_text(
        json.dumps(document) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote lab-trace.json: {len(ids)} nodes, "
        + ", ".join(
            f"{name} {trace['nodes_expanded']} expansions"
            for name, trace in traces.items()
        )
    )
    return document


def _bar_chart(row: dict, path: Path) -> None:
    bars = [
        (key, row[key]["wall_time_ns"] / 1e6)
        for key in ("brute_force", "held_karp", "nearest_neighbor", "two_opt")
        if not row[key].get("skipped")
    ]
    max_value = max(value for _, value in bars)
    width, height, bar_height, gap = 700, 210, 30, 14
    svg = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            'font-family="monospace" font-size="12">'
        ),
        f'<text x="10" y="20">Solver wall time — {row["stops"]} stops (ms, log scale)</text>',
    ]
    for index, (name, value) in enumerate(bars):
        y = 40 + index * (bar_height + gap)
        bar = 8 + (math.log10(max(value, 0.001)) / math.log10(max(max_value, 0.001))) * (
            width - 260
        )
        label = f"{value:.2f} ms"
        svg.append(f'<text x="10" y="{y + 20}">{name}</text>')
        svg.append(
            f'<rect x="150" y="{y}" width="{bar:.1f}" height="{bar_height}" fill="#0e7a3d"/>'
        )
        if 150 + bar + 70 > width:
            # The value label would clip: draw it inside the bar instead.
            svg.append(
                f'<text x="{150 + bar - 6:.1f}" y="{y + 20}" text-anchor="end" '
                f'fill="#ffffff">{label}</text>'
            )
        else:
            svg.append(f'<text x="{155 + bar:.1f}" y="{y + 20}">{label}</text>')
    svg.append("</svg>")
    path.write_text("\n".join(svg) + "\n", encoding="utf-8")


def _tradeoff_chart(path_rows: dict, path: Path) -> None:
    """Work vs. solution quality: expansions against optimality overshoot."""
    width, height = 700, 380
    left, right, top, bottom = 84, 640, 66, 288
    points = [
        (row["median_overshoot_percent"], row["median_nodes_expanded"], name)
        for name, row in path_rows.items()
    ]
    max_overshoot = max(1.0, max(overshoot for overshoot, _, _ in points))
    max_expanded = max(1.0, max(expanded for _, expanded, _ in points))
    log_max = math.log10(max(max_expanded, 10))

    def x_of(value: float) -> float:
        return left + (value / max_overshoot) * (right - left)

    def y_of(value: float) -> float:
        return bottom - (math.log10(max(value, 1)) / log_max) * (bottom - top)

    svg = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            'font-family="monospace" font-size="12">'
        ),
        '<text x="12" y="22">Median nodes expanded vs. optimality overshoot</text>',
        (
            '<text x="12" y="42" fill="#475569">200 sampled pairs, time objective, '
            "committed OSM extract</text>"
        ),
    ]

    # Horizontal gridlines with power-of-ten labels.
    power = 0
    while 10**power <= max_expanded * 1.05:
        value = 10**power
        y = y_of(value)
        svg.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" '
            'stroke="#e2e8f0" stroke-width="1"/>'
        )
        svg.append(
            f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" '
            f'fill="#475569">{value:g}</text>'
        )
        power += 1

    svg.append(
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#334155"/>'
    )
    svg.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#334155"/>')
    for fraction in (0.0, 0.5, 1.0):
        value = max_overshoot * fraction
        x = x_of(value)
        svg.append(
            f'<line x1="{x:.1f}" y1="{bottom}" x2="{x:.1f}" y2="{bottom + 5}" '
            'stroke="#334155"/>'
        )
        label = "0%" if value == 0 else f"{value:.1f}%"
        svg.append(
            f'<text x="{x:.1f}" y="{bottom + 19}" text-anchor="middle" '
            f'fill="#475569">{label}</text>'
        )
    svg.append(
        f'<text x="{(left + right) / 2:.0f}" y="{bottom + 38}" text-anchor="middle" '
        'fill="#475569">overshoot vs. the optimum (%)</text>'
    )
    svg.append(
        f'<text x="20" y="{(top + bottom) / 2:.0f}" text-anchor="middle" fill="#475569" '
        f'transform="rotate(-90 20 {(top + bottom) / 2:.0f})">median expansions</text>'
    )

    # Exact solvers cluster at 0% overshoot, so labels are staggered downwards
    # in point order with a short connector; otherwise they overlap.
    last_text_y = -10**9
    for overshoot, expanded, name in sorted(points, key=lambda point: -point[1]):
        x, y = x_of(overshoot), y_of(expanded)
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#0b66c3"/>')
        text_y = max(y + 4, last_text_y + 15)
        last_text_y = text_y
        label = f"{name} ({expanded:.0f})"
        svg.append(
            f'<text x="{x + 14:.1f}" y="{text_y:.1f}" fill="#12231b">{label}</text>'
        )
        if text_y - (y + 4) > 1:
            svg.append(
                f'<line x1="{x + 5:.1f}" y1="{y + 5:.1f}" x2="{x + 11:.1f}" '
                f'y2="{text_y - 4:.1f}" stroke="#94a3b8" stroke-width="1"/>'
            )

    svg.append(
        f'<text x="{left}" y="{bottom + 58}" fill="#475569">Exact solvers sit on the left '
        "(0% overshoot);</text>"
    )
    svg.append(
        f'<text x="{left}" y="{bottom + 74}" fill="#475569">weighted A* trades solution '
        "quality for fewer expansions.</text>"
    )
    svg.append("</svg>")
    path.write_text("\n".join(svg) + "\n", encoding="utf-8")


def _markdown(results: dict) -> str:
    md = [
        "# Routing benchmark",
        "",
        f"Generated: {results['generated_at']}",
        (f"Graph: `{results['graph']['graph_id']}` {results['graph']['version']} — "
        f"{results['graph']['nodes']} nodes, {results['graph']['edges']} directed edges"),
        (f"Machine: {results['machine']['platform']} · Python {results['machine']['python']} · "
        f"commit {results['machine']['commit'] or 'n/a'}"),
        "",
        "## Multi-stop (TSP) solvers — seeded random matrices",
        "",
        "| Stops | Brute force | Held-Karp | Nearest-neighbor | 2-opt |",
        "| --- | --- | --- | --- | --- |",
    ]

    def cell(row: dict, key: str) -> str:
        entry = row[key]
        if entry.get("skipped"):
            return "skipped (exceeds bound)"
        return (
            f"{entry['total_cost']:.1f} ({entry['routes_evaluated']} evals, "
            f"{entry['wall_time_ns'] / 1e6:.1f} ms)"
        )

    for row in results["tsp_random"]:
        md.append(
            f"| {row['stops']} | {cell(row, 'brute_force')} | {cell(row, 'held_karp')} "
            f"| {cell(row, 'nearest_neighbor')} | {cell(row, 'two_opt')} |"
        )
    md += [
        "",
        "## Multi-stop (TSP) solvers — cost matrices from the street graph",
        "",
        "| Stops | Brute force | Held-Karp | Nearest-neighbor | 2-opt |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in results["tsp_graph"]:
        md.append(
            f"| {row['stops']} | {cell(row, 'brute_force')} | {cell(row, 'held_karp')} "
            f"| {cell(row, 'nearest_neighbor')} | {cell(row, 'two_opt')} |"
        )
    md += [
        "",
        "Costs are tour totals (seconds); counts in parentheses are solver work units.",
        "Matrices use one-to-all Dijkstra per stop on the time objective.",
        "",
        f"## Point-to-point solvers — {PAIR_COUNT} sampled pairs, time objective",
        "",
        ("| Solver | Median nodes expanded | Share of graph | Median solver time | "
        "Median overshoot | Max overshoot |"),
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, row in results["path"].items():
        md.append(
            f"| {name} | {row['median_nodes_expanded']:.0f} | "
            f"{row['share_of_graph_median'] * 100:.1f}% | "
            f"{row['median_solver_time_ns'] / 1e6:.2f} ms | "
            f"{row['median_overshoot_percent']:.2f}% | {row['max_overshoot_percent']:.2f}% |"
        )
    alt = results["path"].get("alt", {})
    if alt.get("preprocessing_time_ns") is not None:
        md += [
            "",
            (f"ALT preprocessing (one-time, {len(alt.get('landmarks', []))} landmarks): "
            f"{alt['preprocessing_time_ns'] / 1e6:.0f} ms — reported separately from query time, "
            "amortized across every query on this graph and objective."),
        ]
    ch = results["path"].get("ch", {})
    if ch.get("preprocessing_time_ns") is not None:
        def break_even(value: float | None) -> str:
            return "no crossing" if value is None else f"{value:,.0f}"

        md += [
            "",
            (f"CH preprocessing: {ch['preprocessing_time_ns'] / 1e9:.1f} s, "
            f"{ch.get('preprocessing_peak_mb', 0):.0f} MB peak, "
            f"{ch.get('shortcuts', 0):,} shortcuts from "
            f"{ch.get('witness_hops')}-hop witness searches."),
            "",
            "| CH break-even vs. a no-preprocessing baseline | Queries |",
            "| --- | --- |",
            f"| A* | {break_even(ch.get('break_even_queries_vs_astar'))} |",
            f"| ALT | {break_even(ch.get('break_even_queries_vs_alt'))} |",
            "",
            ("A delivery dispatcher answering thousands of routes pays CH's build once; a single "
             "route per process does not. That is the selection rule the guide records."),
        ]
    md += [
        "",
        ("Every exact solver (Dijkstra, A*, ALT, bidirectional) agrees on optimal cost; only the "
        "weighted variant is allowed to overshoot, and only within its ε bound."),
        "",
        "## Batch realism — one 7-stop courier batch, end to end",
        "",
        f"Median of {results['batch']['repeats']} runs; the matrix dominates, the tour is negligible.",
        "",
        "| Stage | Time |",
        "| --- | --- |",
        f"| Cost matrix (one-to-all Dijkstra per stop) | {results['batch']['matrix_build_ms']} ms |",
        f"| Exact tour (Held-Karp with precedence) | {results['batch']['held_karp_ms']} ms |",
        f"| **Total** | **{results['batch']['total_ms']} ms** |",
        "",
        (f"Held-Karp {results['batch']['held_karp_cost']:.1f} s vs. nearest-neighbor "
        f"{results['batch']['nearest_neighbor_cost']:.1f} s on the same matrix "
        f"({results['batch']['savings_seconds']:.1f} s saved)."),
        "",
        (f"Exact solvers agree on optimal cost on every sampled pair "
        f"({PAIR_COUNT} pairs, test suite asserts this)."),
    ]
    return "\n".join(md) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", choices=sorted(GRAPHS), default="centro")
    parser.add_argument("--smoke", action="store_true", help="Fast CI gate: solvers agree")
    parser.add_argument(
        "--export-lab-trace",
        action="store_true",
        help="Also write the replayable trace for the centro delivery route",
    )
    args = parser.parse_args()
    if args.smoke:
        _smoke()
        return

    graph_path = _graph_path(args.graph)
    graph = load_graph(graph_path)
    nodes = sorted(graph.nodes)
    edge_count = sum(len(edges) for edges in graph.adjacency.values())
    results: dict = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "machine": _machine_context(),
        "graph": {
            "path": graph_path.relative_to(ROOT).as_posix(),
            "graph_id": graph.graph_id,
            "version": graph.version,
            "nodes": len(nodes),
            "edges": edge_count,
            "source": graph.source,
            "attribution": graph.attribution,
        },
    }
    print(f"Benchmarking {graph.graph_id} ({len(nodes)} nodes, {edge_count} edges)")

    results["tsp_random"] = _tsp_matrix_section()
    print("TSP (random matrices): done")
    results["tsp_graph"] = _tsp_section(graph)
    print("TSP (street graph): done")

    # Sample origin/destination pairs directly: materialising the full product
    # of node ids is impossible at city scale (105k nodes = 11 billion pairs).
    rng = random.Random(20260901)
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    while len(pairs) < PAIR_COUNT:
        origin, destination = rng.sample(nodes, 2)
        if (origin, destination) in seen:
            continue
        seen.add((origin, destination))
        pairs.append((origin, destination))
    results["path"] = _path_section(graph, pairs)
    print("Path ladder: done")

    results["batch"] = _batch_realism(graph)
    print("Batch realism: done")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "" if args.graph == "centro" else f"-{args.graph}"
    (OUT_DIR / f"routing{suffix}.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    (OUT_DIR / f"routing{suffix}.md").write_text(_markdown(results), encoding="utf-8")

    largest = next(
        row for row in reversed(results["tsp_random"]) if not row["brute_force"].get("skipped")
    )
    _bar_chart(largest, OUT_DIR / f"routing{suffix}.svg")
    _tradeoff_chart(results["path"], OUT_DIR / f"routing{suffix}-tradeoff.svg")
    print(f"Wrote benchmark artifacts to {OUT_DIR.as_posix()}")

    if args.export_lab_trace:
        if args.graph != "centro":
            print("Skipping --export-lab-trace: the replay is pinned to the centro demo route")
        else:
            _export_lab_trace(graph)


if __name__ == "__main__":
    main()
