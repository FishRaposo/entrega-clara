# Local development

This repository is a staged runtime for a deterministic portfolio demo. It is not a production deployment and must not be configured with real payment, GPS, map, or notification credentials.

## Prerequisites

- Python 3.11 or newer
- Node 22 or newer

Nothing else is required to install, run, demo, or test the project: no Docker, WSL, database, `make`, or provider accounts. Everything that needs external infrastructure is a documented future expansion; see [external dependencies](../architecture/external-dependencies.md).

## Install

From the repository root:

```bash
python -m pip install -e "app/backend[dev]"
cd app/web && npm install
```

Copy `.env.example` to `.env` only if you want to adjust local values; the defaults are safe and require no credentials.

## Run

Start the API from the repository root:

```bash
uvicorn delivery_platform.api.main:app --port 8000
```

Start the web shell in a second terminal:

```bash
cd app/web && npm run dev
```

The API is available at `http://localhost:8000`, including `GET /api/v1/health`; the web shell is available at `http://localhost:3000`. Browser requests use same-origin `/api/...` paths, and Next.js rewrites forward them to `http://localhost:8000` (override with `API_INTERNAL_BASE_URL`).

## Quality gate

The Makefile wraps these commands for environments that have `make`; the plain commands below are the contract and run anywhere:

```bash
python scripts/data/validate_seed.py data/scenarios/lunch-rush.json
python scripts/quality/check_requirement_coverage.py docs/requirements/traceability.md
python scripts/repo/check_app_boundary.py
python -m pytest tests -q
ruff check app/backend/src tests
mypy app/backend/src
cd app/web && npm run lint && npm run typecheck && npm test -- --run && npm run build
```

The browser suite is dev-only tooling:

```bash
cd app/web
npx playwright install        # one-time browser download (or rely on a system Edge/Chrome channel locally)
npm run test:e2e              # boots the API + web servers itself
```

The repository smoke test can run before any application tooling exists:

```bash
python -m pytest tests/repo/test_repository_layout.py -q
```

## Optional tooling

- **GNU make**: convenience aliases only; each target maps to the plain commands above.
- **Playwright**: dev-only e2e tooling; `npx playwright install` downloads a browser once, and the config can also drive an installed Edge/Chrome channel. Not needed to run the app.
- **MapTiler**: an optional, browser-visible key upgrades the map surface from its deterministic SVG fallback to real tiles once a MapLibre adapter ships. See [M1 runbook §9](milestone-1-development.md); never put a service token in the web bundle.
- **Docker Compose** (`docker-compose.yml`, `Dockerfile`, `app/web/Dockerfile`): an optional container path defining `db`, `api`, and `web` services. It is not required to run or test the project and becomes relevant when the PostgreSQL adapter lands as a future expansion.

## Non-production boundary

Payments are simulated, GPS movement is simulated, map data may be seeded or generalized, and notifications have no provider credentials. Role navigation is a demo aid, not authentication or identity verification. This project does not claim payment certification, production compliance, real courier operations, or measured uptime.
