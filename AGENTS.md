# Repository guidance

## What this project is

- Entrega Clara combines two undergraduate assignments — a food-delivery requirements document and a
  brute-force route-optimizer exercise — into one working platform, then uses it as a portfolio piece
  for employers and freelance clients.
- It is **not** an iFood clone and **not** a startup pitch. The iFood recruiter section was added
  later, after the project already existed; keep that chronology in docs and copy.
- The engineering framing is conventional: domain modeling, transactions, state machines, algorithms,
  tests, trade-offs. Do not bolt AI features on to make it look modern.
- Keep the default run free of Docker, WSL and database requirements. The PostgreSQL adapter is
  opt-in; see `docs/origin.md` for the reasoning.
- When asked to explain or pitch the repository, start from `docs/for-reviewers.md` (five-minute path,
  real-vs-simulated table) and keep claims tied to `docs/verification.md`.

## Setup and commands

- Requires Python 3.11+ and Node 24.15+. Install from root with `python -m pip install -e "app/backend[dev]"`; run `npm ci` in `app/web` (the only npm package/lockfile, not a root workspace).
- On Windows PowerShell, if execution policy blocks `npm.ps1`, use `npm.cmd` instead of changing the execution policy.
- No database, Docker, or provider accounts are required for the default `PERSISTENCE_MODE=memory`. The PostgreSQL adapter is implemented behind the optional extra (`pip install -e "app/backend[postgres]"`) and selected with `PERSISTENCE_MODE=postgres` + `DATABASE_URL`; it stores a transactional snapshot plus an outbox and is single-writer (ADR 0012, `docs/runbooks/postgres.md`).
- From root, `python scripts/dev.py` starts both servers. Alternatively run `python -m uvicorn delivery_platform.api.main:app --port 8000` from root and `npm run dev` in `app/web` in separate terminals.
- Backend settings read process environment; `core/config.py` does not configure `.env` loading. Copying the root `.env.example` alone does not change backend settings.

| Verification | Command and working directory |
| --- | --- |
| Backend/repository suite | Root: `python -m pytest tests -q` |
| Focused backend test | Root: `python -m pytest tests/api/test_checkout_flow.py -q` (append `::test_name` for one test) |
| Backend lint / types | Root: `ruff check app/backend/src tests`; `mypy app/backend/src` |
| Frontend suite | `app/web`: `npm test -- --run` (without `--run`, Vitest watches) |
| Focused frontend test | `app/web`: `npm test -- --run tests/frontend/api-client.test.ts` |
| Frontend lint / types / build | `app/web`: `npm run lint`; `npm run typecheck`; `npm run build` |
| Persistence contract (memory + PostgreSQL) | Root: `DATABASE_URL=postgresql+psycopg://user:pass@host:port/db python -m pytest tests/repo -q` — the PostgreSQL cases skip with a message when the variable is absent |
| Static lab freshness | Root: `python scripts/media/check_static_lab.py` (regenerates `site/index.html` and fails if it changed) |
| Routing benchmark artifacts | Root: `python scripts/bench/routing_benchmark.py --graph city` and `... --export-lab-trace` |

- `python scripts/check.py` runs seed validation, requirement coverage, app-boundary checks, static-lab freshness, a routing benchmark smoke, ruff, mypy, pytest, Vitest, lint and typecheck. It does **not** run the Next build, Playwright or the PostgreSQL contract. The direct commands above remain the contract:
  - `python scripts/data/validate_seed.py data/scenarios/lunch-rush.json`
  - `python scripts/quality/check_requirement_coverage.py docs/requirements/traceability.md`
  - `python scripts/repo/check_app_boundary.py`
  - `python scripts/media/check_static_lab.py`
- Vitest's root is the repository root, with tests in `tests/frontend`, not `app/web`; `next/navigation` is replaced by `tests/frontend/next-navigation.mock.ts`. The web `tsc` configuration does not include these tests.
- Playwright lives in `app/web/e2e`, **not** root `tests/e2e`. From `app/web`, run `npm run test:e2e` or `npm run test:e2e -- e2e/journeys.spec.ts -g "test title"`. It starts API/web on 8000/3000 and reuses existing servers outside CI; stale in-memory server state can affect journeys.
- Playwright selects system **Microsoft Edge** locally and downloaded Chromium when `CI` is set. `PLAYWRIGHT_CHANNEL` is not read by the config; installing Chromium alone does not satisfy the local Edge selection. CI runs the journeys and a11y scans in the `e2e` job of `.github/workflows/ci.yml`, with downloaded Chromium on ubuntu-24.04.

## Wiring and invariants

- Application source belongs under `app/`; tests, scripts, and deterministic data stay at root. `api/main.py:create_app()` creates a fresh container, loads `data/seed/brazil.json`, and attaches the command-script runner for `data/scenarios/lunch-rush.json`. API tests use `TestClient(create_app())` for isolated seeded state.
- Backend paths below are relative to `app/backend/src/delivery_platform/`: `application/container.py` wires adapters through `application/ports.py`; HTTP routes and `demo/runner.py` share `application/commands/`. Keep business mutations in those commands, not duplicated in routes or demo simulation.
- `MemoryUnitOfWork` snapshots the store; writes go through its repositories and events publish only after commit. New stored collections need snapshot binding and commit-copy support, not just a field in `MemoryStore`. `PostgresUnitOfWork` reuses the same repositories over a loaded snapshot and writes the whole store plus outbox rows in one transaction guarded by the loaded version (ADR 0012); there is no dual write.
- Demo reset is scenario-scoped and must preserve dynamically created orders. Seed validation replays real commands in a throwaway container, so command changes can break seed validation even when JSON remains valid.
- `application/container.py` resolves the product graph from `ROUTING_GRAPH_PATH`, then the centro OSM extract, then the synthetic lattice, then straight-line routing; the city-scale artifact (`data/graph/sao-paulo-city.json.gz`, compact-v1, gzip) is the benchmark/dispatch graph and `load_graph` reads both document shapes. Routing belongs on the backend; the web map renders supplied geometry, not provider-computed business routes. For batching, consult `docs/adr/0007-multi-stop-batching.md`, `docs/adr/0011-capacity-windows-and-dynamic-replanning.md` and the current courier commands rather than assuming the older one-active-delivery rule.
- Time-dependent planning uses `data/graph/traffic-profile.json` (FIFO-validated at load); commands pass the clock's `now`, and plans carry `departure_at`/`arrival_at`. Contraction hierarchies are cached in `.cache/ch` (gitignored) and are a lab/benchmark rung, not the product default (ADR 0009).
- Observability: `core/metrics.py` (process-local counters/gauges/histograms) renders `/metrics` and `/operations/metrics`; instrument new commands/routes through `METRICS`, not ad-hoc logging.
- Browser API calls use same-origin `/api/v1/...`; `app/web/next.config.ts` proxies `/api/...` to `API_INTERNAL_BASE_URL` (default `http://localhost:8000`). Do not switch browser calls to a hard-coded backend origin.
- Authorization resolves server-known `X-Demo-Identity` values; role selection is not real authentication. `app/web/src/lib/use-order-stream.ts` deliberately uses fetch-based SSE because native `EventSource` cannot send this header.
- HTTP contract changes span backend `api/schemas.py` / `api/serializers.py` and manually maintained `app/web/src/lib/api-types.ts` / `api-client.ts`; there is no frontend type-generation script.
- Preserve the non-production boundary: simulated payments/GPS and synthetic identities only; no real funds, card data, or provider credentials.

## Supporting sources

- Some package READMEs and architecture docs still describe an earlier scaffold or planned endpoints; verify current behavior against code/config/tests. Start operational work with `docs/runbooks/local-development.md`, `docs/runbooks/demo-mode.md`, and `docs/runbooks/postgres.md`.
- `CONTRIBUTING.md` requires requirement-traceability updates for product requirements and an ADR under `docs/adr/` for architecture changes.
