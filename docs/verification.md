# Verification record

Measured on the committed tree — rerun with `python scripts/check.py`
(plus `scripts/bench/routing_benchmark.py` for the benchmark artifacts).

| Gate | Command | Last result |
| --- | --- | --- |
| Backend tests | `python -m pytest tests -q` | 216 passed |
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

- The shipped graph is a **real OpenStreetMap extract** of central São Paulo
  (2,405 nodes, 3,431 directed edges, © OpenStreetMap contributors, ODbL 1.0),
  filtered to its largest strongly connected component — proved by forward and
  backward BFS over every node in the test suite.
- Point-to-point ladder, 200 sampled pairs, time objective: Dijkstra 1,350
  median expansions (56.1% of the graph), A* 815 (33.9%), **ALT 352 (14.6%)**,
  bidirectional 594 (24.7%), weighted ε=1.5 662 (27.6% with a 0.26% worst-case
  overshoot). ALT preprocessing costs about 37 ms once per graph and objective
  and is reported separately from query time. See `docs/benchmarks/routing.md`.
- Every exact solver agrees with the Dijkstra oracle on cost — asserted on 150
  sampled pairs of the synthetic fixture and 40 pairs of the real streets, for
  both objectives.
- Multi-stop: Held-Karp matches brute force at ≤9 stops; at 13 stops it stays
  under ~40 ms where brute force is infeasible. On graph-derived matrices the
  exact tour beats nearest-neighbor by 18% on a 7-stop batch, which costs about
  17.6 ms end to end (matrix 17.4 ms + exact tour 0.2 ms, median of three runs;
  wall times vary by machine, and `routing.md` records the machine context).
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
