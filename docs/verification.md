# Verification record

Measured on the committed tree — rerun with `python scripts/check.py`
(plus `scripts/bench/routing_benchmark.py` for the benchmark artifacts).

| Gate | Command | Last result |
| --- | --- | --- |
| Backend tests | `python -m pytest tests -q` | 175 passed |
| Ruff | `ruff check app/backend/src tests scripts` | clean |
| Mypy (strict-ish) | `mypy app/backend/src` | clean, 65 files |
| Web vitest | `npm test -- --run` (app/web) | 7 passed |
| Web lint / typecheck / build | `npm run lint` / `typecheck` / `build` | clean |
| Playwright + axe | `npm run e2e` (app/web) | 2/2 pass, 0 violations |
| Seed validation | `python scripts/data/validate_seed.py data/scenarios/lunch-rush.json` | pass |
| Requirement coverage | `scripts/quality/check_requirement_coverage.py` | pass |
| App boundary | `scripts/repo/check_app_boundary.py` | pass |
| Routing benchmark | `scripts/bench/routing_benchmark.py` | artifacts in `docs/benchmarks/` |

## Routing evidence highlights (committed, reproducible)

- A* with the time objective matches a Dijkstra oracle on 150 sampled pairs —
  both optimal cost and expanded-node bounds are asserted in
  `tests/routing/test_graph_solvers.py`.
- Heuristic admissibility and consistency are proven over **every** node/goal
  and edge in the synthetic graph (not sampled).
- Held-Karp matches brute-force optimality at ≤9 stops while doing ~10× less
  work; at 13 stops it remains under ~50 ms where brute force is infeasible.
  See `docs/benchmarks/routing.md|json|svg`.

## Honest scope notes

- Memory persistence only; `PERSISTENCE_MODE=postgres` fails fast by design.
- Snapshots (`POST/GET/PUT /api/v1/demo/snapshot`) are in-process deep copies,
  not durable files — JSON export is deferred.
- Courier multi-stop batching: solver layer + ADR 0007 exist; dispatch
  integration (batch accept, sequence UI) is the remaining work.
- Cancellation covers pre-preparation only with simulated refund; full M2
  refund policy is deferred.
