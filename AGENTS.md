# Repository guidance

## Setup and commands

- Requires Python 3.11+ and Node 22+. Install from root with `python -m pip install -e "app/backend[dev]"`; run `npm ci` in `app/web` (the only npm package/lockfile, not a root workspace).
- On Windows PowerShell, if execution policy blocks `npm.ps1`, use `npm.cmd` instead of changing the execution policy.
- No database, Docker, or provider accounts are required. Only `PERSISTENCE_MODE=memory` is implemented; selecting Postgres fails at startup despite the Compose database service.
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

- `make check` wraps seed validation, requirement coverage, app-boundary checks, lint, typecheck, and unit tests. It does **not** run the Next build or Playwright. Without make, use the commands above plus these root checks:
  - `python scripts/data/validate_seed.py data/scenarios/lunch-rush.json`
  - `python scripts/quality/check_requirement_coverage.py docs/requirements/traceability.md`
  - `python scripts/repo/check_app_boundary.py`
- Vitest's root is the repository root, with tests in `tests/frontend`, not `app/web`; `next/navigation` is replaced by `tests/frontend/next-navigation.mock.ts`. The web `tsc` configuration does not include these tests.
- Playwright lives in `app/web/e2e`, **not** root `tests/e2e`. From `app/web`, run `npm run test:e2e` or `npm run test:e2e -- e2e/journeys.spec.ts -g "test title"`. It starts API/web on 8000/3000 and reuses existing servers outside CI; stale in-memory server state can affect journeys.
- Playwright selects system **Microsoft Edge** locally and downloaded Chromium when `CI` is set. `PLAYWRIGHT_CHANNEL` is not read by the config; installing Chromium alone does not satisfy the local Edge selection. E2E is not currently run by `.github/workflows/ci.yml`.

## Wiring and invariants

- Application source belongs under `app/`; tests, scripts, and deterministic data stay at root. `api/main.py:create_app()` creates a fresh container, loads `data/seed/brazil.json`, and attaches the command-script runner for `data/scenarios/lunch-rush.json`. API tests use `TestClient(create_app())` for isolated seeded state.
- Backend paths below are relative to `app/backend/src/delivery_platform/`: `application/container.py` wires adapters through `application/ports.py`; HTTP routes and `demo/runner.py` share `application/commands/`. Keep business mutations in those commands, not duplicated in routes or demo simulation.
- `MemoryUnitOfWork` snapshots the store; writes go through its repositories and events publish only after commit. New stored collections need snapshot binding and commit-copy support, not just a field in `MemoryStore`.
- Demo reset is scenario-scoped and must preserve dynamically created orders. Seed validation replays real commands in a throwaway container, so command changes can break seed validation even when JSON remains valid.
- `application/container.py` selects graph routing from `data/graph/sao-paulo-centro.json`, falling back to straight-line routing if loading fails. Routing belongs on the backend; the web map renders supplied geometry, not provider-computed business routes. For batching, consult `docs/adr/0007-multi-stop-batching.md` and current courier commands rather than assuming the older one-active-delivery rule.
- Browser API calls use same-origin `/api/v1/...`; `app/web/next.config.ts` proxies `/api/...` to `API_INTERNAL_BASE_URL` (default `http://localhost:8000`). Do not switch browser calls to a hard-coded backend origin.
- Authorization resolves server-known `X-Demo-Identity` values; role selection is not real authentication. `app/web/src/lib/use-order-stream.ts` deliberately uses fetch-based SSE because native `EventSource` cannot send this header.
- HTTP contract changes span backend `api/schemas.py` / `api/serializers.py` and manually maintained `app/web/src/lib/api-types.ts` / `api-client.ts`; there is no frontend type-generation script.
- Preserve the non-production boundary: simulated payments/GPS and synthetic identities only; no real funds, card data, or provider credentials.

## Supporting sources

- Some package READMEs and architecture docs still describe an earlier scaffold or planned endpoints; verify current behavior against code/config/tests. Start operational work with `docs/runbooks/local-development.md` and `docs/runbooks/demo-mode.md`.
- `CONTRIBUTING.md` requires requirement-traceability updates for product requirements and an ADR under `docs/adr/` for architecture changes.
