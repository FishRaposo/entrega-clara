# Verification record

Measured on the committed tree — rerun with `python scripts/check.py`
(plus `scripts/bench/routing_benchmark.py` for the benchmark artifacts).

| Gate | Command | Last result |
| --- | --- | --- |
| Backend tests | `python -m pytest tests -q` | 289 passed, 5 skipped (PostgreSQL cases without `DATABASE_URL`) |
| Backend tests, persistent mode | same, with `DATABASE_URL` set | 294 passed |
| Persistence contract | `python -m pytest tests/repo -q` | memory + PostgreSQL (9 tests each environment) |
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

## Persistence and observability highlights

- **PostgreSQL 16.9 was exercised locally** (portable server, `docs/runbooks/postgres.md`).
  The same contract suite passes on the memory and PostgreSQL adapters:
  committed writes visible to a later unit of work, rollback discarding
  everything, events published only after commit, the event log surviving a
  restart, a stale write rejected with `version_conflict`, and the outbox
  recovering the commit → publish window.
- **Restart smoke:** the app places an order through HTTP, a second application
  instance is built (new container, snapshot reloaded from PostgreSQL), and the
  order and catalog are read back unchanged.
- **Outbox worker:** `scripts/worker.py --once` drained a pending event written
  by a commit whose publisher never ran, marked it delivered, and left the
  pending queue empty.
- **Metrics:** `/metrics` renders Prometheus text (HTTP requests and latency by
  route template, routing queries/latency by kind and solver, events and lag,
  SSE gauge) and `/operations/metrics` returns the same series plus the product
  counters the operations panel renders. Counters are process-local and reset on
  restart — stated in the ADR and runbook.

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

- The PostgreSQL adapter persists the store as one transactional snapshot with
  an optimistic version guard, not one table per aggregate. Concurrent writers
  get `version_conflict` instead of silent overwrites; row-per-aggregate is the
  recorded next step (ADR 0012).
- Persistent mode needs the optional `[postgres]` extra and a reachable server;
  memory mode never imports the driver.
- Metrics are in-process and unaggregated across workers. Grafana/Prometheus
  configuration is out of scope; the exposition format is what is claimed.
- Snapshot export/import is still the offline portability path; the durable one
  is `PERSISTENCE_MODE=postgres`.
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
