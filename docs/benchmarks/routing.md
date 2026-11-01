# Routing benchmark

Generated: 2026-11-01T18:08:05Z
Graph: `sao-paulo-centro-osm` osm-2026-11-01 — 2405 nodes, 3431 directed edges
Machine: Windows-11-10.0.26300-SP0 · Python 3.15.2 · commit e9d2637-dirty

## Multi-stop (TSP) solvers — seeded random matrices

| Stops | Brute force | Held-Karp | Nearest-neighbor | 2-opt |
| --- | --- | --- | --- | --- |
| 5 | 182.0 (24 evals, 0.1 ms) | 182.0 (52 evals, 0.1 ms) | 182.0 (10 evals, 0.0 ms) | 182.0 (16 evals, 0.0 ms) |
| 7 | 179.0 (720 evals, 0.8 ms) | 179.0 (486 evals, 0.3 ms) | 242.0 (21 evals, 0.0 ms) | 209.0 (51 evals, 0.1 ms) |
| 9 | 245.0 (40320 evals, 41.7 ms) | 245.0 (3592 evals, 1.2 ms) | 277.0 (36 evals, 0.0 ms) | 247.0 (92 evals, 0.1 ms) |
| 11 | skipped (exceeds bound) | 255.0 (23050 evals, 7.2 ms) | 342.0 (55 evals, 0.0 ms) | 255.0 (190 evals, 0.3 ms) |
| 13 | skipped (exceeds bound) | 236.0 (135180 evals, 40.5 ms) | 346.0 (78 evals, 0.0 ms) | 236.0 (276 evals, 0.5 ms) |

## Multi-stop (TSP) solvers — cost matrices from the street graph

| Stops | Brute force | Held-Karp | Nearest-neighbor | 2-opt |
| --- | --- | --- | --- | --- |
| 5 | 1197.6 (24 evals, 0.0 ms) | 1197.6 (52 evals, 0.0 ms) | 1311.3 (10 evals, 0.0 ms) | 1311.3 (16 evals, 0.0 ms) |
| 7 | 1367.8 (720 evals, 0.7 ms) | 1367.8 (486 evals, 0.2 ms) | 1756.6 (21 evals, 0.0 ms) | 1756.6 (36 evals, 0.0 ms) |
| 9 | 1899.6 (40320 evals, 40.5 ms) | 1899.6 (3592 evals, 1.2 ms) | 2051.2 (36 evals, 0.0 ms) | 1899.6 (92 evals, 0.1 ms) |
| 11 | skipped (exceeds bound) | 2364.2 (23050 evals, 6.7 ms) | 3551.9 (55 evals, 0.0 ms) | 3551.9 (100 evals, 0.1 ms) |
| 13 | skipped (exceeds bound) | 2013.7 (135180 evals, 39.3 ms) | 2181.8 (78 evals, 0.0 ms) | 2181.8 (144 evals, 0.2 ms) |

Costs are tour totals (seconds); counts in parentheses are solver work units.
Matrices use one-to-all Dijkstra per stop on the time objective.

## Point-to-point solvers — 200 sampled pairs, time objective

| Solver | Median nodes expanded | Share of graph | Median solver time | Median overshoot | Max overshoot |
| --- | --- | --- | --- | --- | --- |
| dijkstra | 1098 | 45.7% | 1.16 ms | 0.00% | 0.00% |
| astar | 671 | 27.9% | 1.34 ms | 0.00% | 0.00% |
| alt | 378 | 15.7% | 1.55 ms | 0.00% | 0.00% |
| bidirectional | 706 | 29.4% | 7.27 ms | 0.00% | 0.00% |
| ch | 25 | 1.0% | 0.16 ms | 0.00% | 0.00% |
| weighted_eps1.5 | 544 | 22.6% | 1.81 ms | 0.00% | 0.16% |
| weighted_eps2.5 | 372 | 15.5% | 1.21 ms | 0.00% | 17.45% |
| weighted_eps5 | 348 | 14.4% | 1.72 ms | 0.01% | 98.05% |

ALT preprocessing (one-time, 8 landmarks): 41 ms — reported separately from query time, amortized across every query on this graph and objective.

CH preprocessing: 0.0 s, 3 MB peak, 3,198 shortcuts from 3-hop witness searches.

| CH break-even vs. a no-preprocessing baseline | Queries |
| --- | --- |
| A* | 22 |
| ALT | 18 |

A delivery dispatcher answering thousands of routes pays CH's build once; a single route per process does not. That is the selection rule the guide records.

Every exact solver (Dijkstra, A*, ALT, bidirectional) agrees on optimal cost; only the weighted variant is allowed to overshoot, and only within its ε bound.

## Batch realism — one 7-stop courier batch, end to end

Median of 3 runs; the matrix dominates, the tour is negligible.

| Stage | Time |
| --- | --- |
| Cost matrix (one-to-all Dijkstra per stop) | 32.92 ms |
| Exact tour (Held-Karp with precedence) | 0.47 ms |
| **Total** | **33.39 ms** |

Held-Karp 1979.8 s vs. nearest-neighbor 2405.0 s on the same matrix (425.2 s saved).

Exact solvers agree on optimal cost on every sampled pair (200 pairs, test suite asserts this).
