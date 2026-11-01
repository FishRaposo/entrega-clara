# Repository layout

The repository root is a stable governance contract. Application code is contained by `app/`; tests are in `tests/`; deterministic data is in `data/`; automation is in `scripts/`; and durable product records are in `docs/`.

## Root contracts

- Make targets cover `install`, `test`, `lint`, `typecheck`, `check`, `dev`, `demo-reset`, `demo-preview`, `bench`, `bench-city`, `bench-smoke`, `worker`, `contract`, `db-check`, `media`, `site`, `tour`, and `screens`.
- Docker Compose service names are `api`, `worker`, `web`, and `db`.
- Python tests discover from `tests` and import backend code from `app/backend/src`.
- `site/index.html` is generated (`scripts/media/export_static_lab.py`) and gated by `scripts/media/check_static_lab.py`; do not hand-edit it.
- `.env.example` contains only development-safe, non-secret defaults.
- `.superpowers/` is ignored private task working state and is not versioned.
- `docs/superpowers/specs/` is public, versioned product documentation; it retains the governing seed design.
- `docs/research/` records dated, source-backed research and assumptions.
- `docs/roadmap/` records staged future capabilities, dependencies, and exit evidence.
- `docs/architecture/` records API, event, persistence, routing, and integration contracts.
- `docs/adr/` records durable technical decisions and rejected alternatives.
- `docs/design/` retains historical design artifacts such as the original FoodExpress wireframe; they are reference material, not product surfaces.

Later tasks extend these contracts without renaming targets or services.
