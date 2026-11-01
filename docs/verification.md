# Verification record

Measured on the committed tree — rerun with `python scripts/check.py`
(plus `scripts/bench/routing_benchmark.py` for the benchmark artifacts).

| Gate | Command | Last result |
| --- | --- | --- |
| Backend tests | `python -m pytest tests -q` | 244 passed |
| Ruff | `ruff check app/backend/src tests scripts` | clean |
| Mypy (strict-ish) | `mypy app/backend/src` | clean, 68 files |
| Web vitest | `npm test -- --run` (app/web) | 19 passed |
| Web lint / typecheck / build | `npm run lint` / `typecheck` / `build` | clean |
| Playwright + axe | `npx playwright test` (app/web) | 4/4 pass, 0 violations on 7 pages |
| Seed validation | `python scripts/data/validate_seed.py data/scenarios/lunch-rush.json` | pass |
| Requirement coverage | `scripts/quality/check_requirement_coverage.py` | pass |
| App boundary | `python scripts/repo/check_app_boundary.py` | pass |
| Routing benchmark | `scripts/bench/routing_benchmark.py` | artifacts in `docs/benchmarks/` |
| Benchmark smoke | `routing_benchmark.py --smoke` | solvers agree on a 6-stop matrix and on the street graph |
| Scenario replay | 40-step `lunch-rush` via `validate_seed.py` | batch + GPS + cancel + rate all pass |

## Routing evidence highlights (committed, reproducible)

- Two real OpenStreetMap artifacts share the same build rules: **centro**
  (2,405 nodes / 3,431 edges, 0.7 MB) for the product and lab, and **city**
  (104,991 nodes / 177,114 edges, 2.1 MB gzipped, compact-v1) for benchmarks and
  dispatch scale. Both are filtered to the largest strongly connected component,
  proved by forward and backward BFS over every node in the test suite.
- **City-scale ladder, 200 sampled pairs, time objective:** Dijkstra 53,885
  median expansions (51.3% of the graph), A\* 44,759 (42.6%), ALT 6,186 (5.9%),
  bidirectional 19,272 (18.4%), **CH 85 (0.1%)**. Weighted ε=5 expands 13.8%
  with a 13% worst-case overshoot. See `docs/benchmarks/routing-city.md`.
- **Contraction hierarchy:** 2.2 s preprocessing, 164,517 shortcuts, 2.04 ms per
  query. Break-even against A\* is 13 queries and against ALT 35 — the measured
  reason the product still ships plain A\* and a dispatcher would not.
- **Centro ladder** (the product graph): Dijkstra 1,098 (45.7%), A\* 671
  (27.9%), ALT 378 (15.7%), bidirectional 706 (29.4%), weighted ε=1.5 544
  (22.6% with a 0.16% worst-case overshoot). ALT preprocessing ≈44 ms.
- Every exact solver agrees with the Dijkstra oracle on cost — asserted on 150
  sampled pairs of the synthetic fixture, 40 pairs of the centro extract and 30
  pairs of the city graph, for both objectives where the graph allows.
- Multi-stop: Held-Karp matches brute force at ≤9 stops; at 13 stops it stays
  under ~55 ms where brute force is infeasible. On city-derived matrices the
  exact tour beats nearest-neighbor by 24% on a 7-stop batch.
- Batch planning at city scale costs ~1.7 s (one-to-all Dijkstra per stop); the
  centro demo batch costs ~18 ms. The difference is reported, not smoothed over.
- The replay of one delivery search (`docs/benchmarks/lab-trace.json`, rendered
  to `docs/media/lab-alt-vs-dijkstra.gif`) shows ALT finishing in 70 expansions
  where Dijkstra needs 167.

## Honest scope notes

- Memory persistence only; `PERSISTENCE_MODE=postgres` fails fast by design.
- Snapshots are in-process deep copies plus a JSON export/import round trip;
  there is no durable store behind them.
- The street graph is a **dated OSM snapshot**: distances, ETAs and benchmark
  numbers change when it is regenerated, and the artifacts must be regenerated
  with it.
- Central São Paulo is one-way-dominant (76% of ways), so the largest strongly
  connected component holds 26.6% of junctions; stops snap to the nearest
  routable node, which can be a few hundred meters away.
- Bidirectional search expands fewer nodes than Dijkstra but is **slower in
  wall time under CPython** (two heaps, two potential lookups per relaxation).
  Weighted A* is inexact by design (≤ ε × optimal) and is labelled as such.
- Cancellation covers pre-preparation only with simulated refund; full M2
  refund policy is deferred.
