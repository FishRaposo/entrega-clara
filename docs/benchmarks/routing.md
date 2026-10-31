# Routing benchmark

Generated: 2026-10-31T06:14:31Z

## Multi-stop (TSP) solvers — identical matrices

| Stops | Brute force | Held-Karp | Nearest-neighbor | 2-opt |
| --- | --- | --- | --- | --- |
| 5 | 182.0 (24 evals, 0.1 ms) | 182.0 (52 evals, 0.1 ms) | 182.0 (10 evals, 0.0 ms) | 182.0 (16 evals, 0.0 ms) |
| 7 | 179.0 (720 evals, 0.6 ms) | 179.0 (486 evals, 0.2 ms) | 242.0 (21 evals, 0.0 ms) | 209.0 (51 evals, 0.1 ms) |
| 9 | 245.0 (40320 evals, 45.8 ms) | 245.0 (3592 evals, 2.2 ms) | 277.0 (36 evals, 0.0 ms) | 247.0 (92 evals, 0.2 ms) |
| 11 | skipped (exceeds bound) | 255.0 (23050 evals, 8.4 ms) | 342.0 (55 evals, 0.0 ms) | 255.0 (190 evals, 0.5 ms) |
| 13 | skipped (exceeds bound) | 236.0 (135180 evals, 48.8 ms) | 346.0 (78 evals, 0.0 ms) | 236.0 (276 evals, 0.5 ms) |

Costs are the optimized tour total; counts in parentheses are solver work units.

## Path solvers — A* vs. Dijkstra (150 pairs, time objective)

| Solver | Nodes expanded | Solver time |
| --- | --- | --- |
| astar | 2045 | 9.7 ms |
| dijkstra | 5911 | 12.4 ms |

Exact solvers agree on optimal cost on every sampled pair (test suite asserts this).
