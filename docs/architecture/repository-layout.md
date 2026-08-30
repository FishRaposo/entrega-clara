# Repository layout

The repository root is a stable governance contract. Application code is contained by `app/`; tests are in `tests/`; deterministic data is in `data/`; automation is in `scripts/`; and durable product records are in `docs/`.

## Root contracts

- Make targets are `install`, `test`, `lint`, `typecheck`, `check`, `dev`, `demo-reset`, and `demo-preview`.
- Docker Compose service names are `api`, `web`, and `db`.
- Python tests discover from `tests` and import backend code from `app/backend/src`.
- `.env.example` contains only development-safe, non-secret defaults.
- `.superpowers/` is ignored private task working state and is not versioned.
- `docs/superpowers/specs/` is public, versioned product documentation; it retains the governing seed design.

Later tasks extend these contracts without renaming targets or services.
