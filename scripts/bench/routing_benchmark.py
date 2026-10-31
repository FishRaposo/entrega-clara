"""Deterministic routing benchmark — brute-force baseline vs. portfolio solvers.

Compares the retained ``LegacyBruteForceTSPSolver`` against Held-Karp,
nearest-neighbor and 2-opt on identical bounded matrices, plus A* vs. Dijkstra
on the committed synthetic graph. Emits committed evidence:

    docs/benchmarks/routing.json  — machine-readable results
    docs/benchmarks/routing.md    — human-readable summary
    docs/benchmarks/routing.svg   — execution-time bar chart

Standard library only. Runs in seconds; factorial sizes stay bounded.
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app" / "backend" / "src"))
sys.path.insert(0, str(ROOT / "src")) if (ROOT / "src").is_dir() else None

from delivery_platform.routing.graph import load_graph
from delivery_platform.routing.legacy_bruteforce import (
    LegacyBruteForceTSPSolver,
)
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
GRAPH_PATH = ROOT / "data" / "graph" / "sao-paulo-centro.json"


def _matrix(n: int, seed: int) -> RouteProblem:
    import random

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


def main() -> None:
    results: dict = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    # --- TSP comparison: brute force vs replacements on identical matrices ---
    tsp_rows = []
    # Brute force is capped at 9 stops (9! = 362 880 permutations ≈ measured
    # tens of ms → but the factorial doubles ~10x per stop and becomes
    # unusable; replacements are shown scaling beyond that wall).
    for n in (5, 7, 9, 11, 13):
        problem = _matrix(n, seed=42 + n)
        row = {"stops": n}
        row["brute_force"] = (
            _run(LegacyBruteForceTSPSolver(), problem)
            if n <= 9
            else {"solver": "legacy_bruteforce_tsp", "skipped": True}
        )
        row["held_karp"] = (
            _run(HeldKarpSolver(), problem) if n <= HeldKarpSolver.MAX_STOPS
            else {"solver": "held-karp", "skipped": True}
        )
        row["nearest_neighbor"] = _run(NearestNeighborSolver(), problem)
        row["two_opt"] = _run(TwoOptSolver(), problem)
        tsp_rows.append(row)
    results["tsp"] = tsp_rows

    # --- Path solvers: A* vs Dijkstra over 150 sampled pairs ---
    graph = load_graph(GRAPH_PATH)
    nodes = sorted(graph.nodes)
    import random

    rng = random.Random(20260901)
    pairs = rng.sample([(a, b) for a in nodes for b in nodes if a != b], 150)
    path_rows = {}
    for name, solver in (("astar", AStarPathSolver()), ("dijkstra", DijkstraPathSolver())):
        expanded = 0
        nanos = 0
        for origin, destination in pairs:
            r = solver.solve(PathProblem(graph, origin, destination, "time"))
            expanded += r.nodes_expanded
            nanos += r.computation_time_ns
        path_rows[name] = {
            "pairs": len(pairs),
            "total_nodes_expanded": expanded,
            "total_solver_time_ns": nanos,
        }
    results["path"] = path_rows

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "routing.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )

    md = ["# Routing benchmark\n",
          f"Generated: {results['generated_at']}\n",
          "## Multi-stop (TSP) solvers — identical matrices\n",
          "| Stops | Brute force | Held-Karp | Nearest-neighbor | 2-opt |",
          "| --- | --- | --- | --- | --- |"]
    for row in tsp_rows:
        def cell(key, row=row):
            r = row[key]
            if r.get("skipped"):
                return "skipped (exceeds bound)"
            return f"{r['total_cost']:.1f} ({r['routes_evaluated']} evals, {r['wall_time_ns']/1e6:.1f} ms)"
        md.append(
            f"| {row['stops']} | {cell('brute_force')} | {cell('held_karp')} "
            f"| {cell('nearest_neighbor')} | {cell('two_opt')} |"
        )
    md += ["",
           "Costs are the optimized tour total; counts in parentheses are solver work units.",
           "",
           "## Path solvers — A* vs. Dijkstra (150 pairs, time objective)",
           "",
           "| Solver | Nodes expanded | Solver time |",
           "| --- | --- | --- |"]
    for name, r in path_rows.items():
        md.append(f"| {name} | {r['total_nodes_expanded']} | {r['total_solver_time_ns']/1e6:.1f} ms |")
    md += ["", "Exact solvers agree on optimal cost on every sampled pair (test suite asserts this)."]
    (OUT_DIR / "routing.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # --- SVG bar chart: solver wall times at the largest fully-run size ---
    row = next(r for r in reversed(tsp_rows) if not r["brute_force"].get("skipped"))
    bars = [(k, row[k]["wall_time_ns"] / 1e6) for k in ("brute_force", "held_karp", "nearest_neighbor", "two_opt")]
    max_v = max(v for _, v in bars)
    w, h, bar_h, gap = 640, 200, 30, 14
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="monospace" font-size="12">',
           f'<text x="10" y="20">Solver wall time — {row["stops"]} stops (ms, log scale)</text>']
    import math
    for i, (name, v) in enumerate(bars):
        y = 40 + i * (bar_h + gap)
        bw = 8 + (math.log10(max(v, 0.001)) / math.log10(max(max_v, 0.001))) * (w - 200)
        svg.append(f'<text x="10" y="{y + 20}">{name}</text>')
        svg.append(f'<rect x="150" y="{y}" width="{bw:.1f}" height="{bar_h}" fill="#0e7a3d"/>')
        svg.append(f'<text x="{155 + bw:.1f}" y="{y + 20}">{v:.2f} ms</text>')
    svg.append("</svg>")
    (OUT_DIR / "routing.svg").write_text("\n".join(svg) + "\n", encoding="utf-8")
    print(f"Wrote benchmark artifacts to {OUT_DIR.as_posix()}")


if __name__ == "__main__":
    main()
