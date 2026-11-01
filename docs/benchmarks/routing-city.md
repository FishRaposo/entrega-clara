# Routing benchmark

Generated: 2026-11-01T07:33:02Z
Graph: `sao-paulo-city` osm-city-2026-11-01 — 104991 nodes, 177114 directed edges
Machine: Windows-11-10.0.26300-SP0 · Python 3.15.2 · commit c3894d4-dirty

## Multi-stop (TSP) solvers — seeded random matrices

| Stops | Brute force | Held-Karp | Nearest-neighbor | 2-opt |
| --- | --- | --- | --- | --- |
| 5 | 182.0 (24 evals, 0.1 ms) | 182.0 (52 evals, 0.1 ms) | 182.0 (10 evals, 0.0 ms) | 182.0 (16 evals, 0.1 ms) |
| 7 | 179.0 (720 evals, 1.3 ms) | 179.0 (486 evals, 0.4 ms) | 242.0 (21 evals, 0.0 ms) | 209.0 (51 evals, 0.1 ms) |
| 9 | 245.0 (40320 evals, 49.1 ms) | 245.0 (3592 evals, 1.3 ms) | 277.0 (36 evals, 0.0 ms) | 247.0 (92 evals, 0.1 ms) |
| 11 | skipped (exceeds bound) | 255.0 (23050 evals, 10.1 ms) | 342.0 (55 evals, 0.0 ms) | 255.0 (190 evals, 0.3 ms) |
| 13 | skipped (exceeds bound) | 236.0 (135180 evals, 45.7 ms) | 346.0 (78 evals, 0.1 ms) | 236.0 (276 evals, 1.0 ms) |

## Multi-stop (TSP) solvers — cost matrices from the street graph

| Stops | Brute force | Held-Karp | Nearest-neighbor | 2-opt |
| --- | --- | --- | --- | --- |
| 5 | 12147.0 (24 evals, 0.0 ms) | 12147.0 (52 evals, 0.1 ms) | 12147.0 (10 evals, 0.0 ms) | 12147.0 (16 evals, 0.0 ms) |
| 7 | 8547.0 (720 evals, 1.3 ms) | 8547.0 (486 evals, 0.2 ms) | 11712.1 (21 evals, 0.0 ms) | 9770.7 (51 evals, 0.1 ms) |
| 9 | 16776.2 (40320 evals, 42.9 ms) | 16776.2 (3592 evals, 2.0 ms) | 18193.5 (36 evals, 0.0 ms) | 17277.9 (92 evals, 0.3 ms) |
| 11 | skipped (exceeds bound) | 15370.8 (23050 evals, 9.2 ms) | 22066.8 (55 evals, 0.1 ms) | 16900.8 (145 evals, 0.3 ms) |
| 13 | skipped (exceeds bound) | 19544.5 (135180 evals, 83.3 ms) | 23794.4 (78 evals, 0.0 ms) | 21826.5 (276 evals, 0.5 ms) |

Costs are tour totals (seconds); counts in parentheses are solver work units.
Matrices use one-to-all Dijkstra per stop on the time objective.

## Point-to-point solvers — 200 sampled pairs, time objective

| Solver | Median nodes expanded | Share of graph | Median solver time | Median overshoot | Max overshoot |
| --- | --- | --- | --- | --- | --- |
| dijkstra | 53885 | 51.3% | 122.83 ms | 0.00% | 0.00% |
| astar | 44759 | 42.6% | 166.13 ms | 0.00% | 0.00% |
| alt | 6186 | 5.9% | 64.11 ms | 0.00% | 0.00% |
| bidirectional | 19272 | 18.4% | 435.39 ms | 0.00% | 0.00% |
| ch | 85 | 0.1% | 2.04 ms | 0.00% | 0.00% |
| weighted_eps1.5 | 39573 | 37.7% | 132.87 ms | 0.00% | 0.00% |
| weighted_eps2.5 | 32444 | 30.9% | 103.44 ms | 0.00% | 1.89% |
| weighted_eps5 | 14470 | 13.8% | 45.39 ms | 0.52% | 13.02% |

ALT preprocessing (one-time, 8 landmarks): 4281 ms — reported separately from query time, amortized across every query on this graph and objective.

CH preprocessing: 2.2 s, 164,517 shortcuts from 3-hop witness searches.

| CH break-even vs. a no-preprocessing baseline | Queries |
| --- | --- |
| A* | 13 |
| ALT | 35 |

A delivery dispatcher answering thousands of routes pays CH's build once; a single route per process does not. That is the selection rule the guide records.

Every exact solver (Dijkstra, A*, ALT, bidirectional) agrees on optimal cost; only the weighted variant is allowed to overshoot, and only within its ε bound.

## Batch realism — one 7-stop courier batch, end to end

Median of 3 runs; the matrix dominates, the tour is negligible.

| Stage | Time |
| --- | --- |
| Cost matrix (one-to-all Dijkstra per stop) | 1427.57 ms |
| Exact tour (Held-Karp with precedence) | 0.25 ms |
| **Total** | **1427.81 ms** |

Held-Karp 10613.9 s vs. nearest-neighbor 17198.2 s on the same matrix (6584.4 s saved).

Exact solvers agree on optimal cost on every sampled pair (200 pairs, test suite asserts this).
