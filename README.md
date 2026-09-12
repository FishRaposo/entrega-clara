# Entrega Clara

Entrega Clara is a Brazil-first, internationally extensible food-delivery platform whose distinctive portfolio thesis is making the customer-to-delivery operation visible, measurable, and replaceable from a legacy route baseline. It is a production-shaped scaffold with a working FastAPI demo scenario, API-backed web controls, role-based web surfaces, and a solver-independent routing baseline.

## Primary demo story

The implemented lunch-rush scenario resets and atomically replays a seeded order from `placed` through `rated`, including restaurant preparation, courier state and location updates, notifications, and a deterministic clock. The web Demo Mode inspects, advances, and resets that running API scenario. Customer checkout, operational role workflows, route visualization, and production integrations remain explicitly deferred scaffold scope.

## Market boundary

Brazil is the default market: `pt-BR`, BRL, PIX, cards, wallets, Brazilian seed geography, and LGPD-aware privacy copy. It is not a Brazil-only design: locale, currency, payment methods, addresses, time zones, legal copy, maps, and notifications remain configuration-driven for future markets. Money uses integer minor units plus currency; time is stored canonically and rendered in the active market time zone.

## Repository layout

| Path | Purpose |
| --- | --- |
| `app/backend/` | FastAPI health/demo boundaries, domain state machine, and routing baseline |
| `app/web/` | Responsive role shell and API-backed demo controls |
| `data/seed/` | Deterministic seed data |
| `data/scenarios/` | Replayable demo scenarios |
| `docs/` | Architecture, ADRs, requirements, and governing specifications |
| `scripts/` | Development and demo automation |
| `tests/` | Repository and application tests |

All application source belongs under `app/`.

## Demo access

The local web shell provides role selection for Customer, Restaurant, Courier, and Admin. The role switcher is a demo aid rather than real authentication; support is represented by the intended admin/support-facing surface.

## Local setup

1. Copy `.env.example` to `.env` and adjust only local, non-production values.
2. Run `make install` to install the declared backend and web development dependencies.
3. Run `make check` to validate deterministic data, repository quality gates, and application checks.
4. Run `make dev` to start the local Compose services `db`, `api`, and `web` when Docker Compose is available.

See the [local development runbook](docs/runbooks/local-development.md) for local URLs and service details, and the [demo-mode runbook](docs/runbooks/demo-mode.md) for deterministic reset, advancement, replay, and role-navigation instructions.

For the next implementation phase, read the [M1 development runbook](docs/runbooks/milestone-1-development.md), the [M1 design](docs/superpowers/specs/2026-09-01-milestone-1-core-delivery-loop-design.md), and the [platform build research](docs/research/2026-09-01-platform-build-research.md). The [platform evolution roadmap](docs/roadmap/platform-evolution.md) records the capabilities intentionally deferred beyond M1.

## Commands

| Command | Purpose |
| --- | --- |
| `make test` | Run backend and web tests |
| `make lint` | Run backend and web linters |
| `make typecheck` | Run backend and web type checks |
| `make check` | Run lint, type checking, and tests |
| `make dev` | Start the local Compose services `api`, `web`, and `db` |
| `make demo-reset` | Reset the running local API scenario |
| `make demo-preview` | Preview the offline seed without contacting the API |

The repository smoke test can run before application tooling exists:

```bash
python -m pytest tests/repo/test_repository_layout.py -q
```

## Release and publication status

This scaffold is public at [FishRaposo/entrega-clara](https://github.com/FishRaposo/entrega-clara). It remains a non-production demo platform: follow the [public demo release runbook](docs/runbooks/public-demo-release.md) to reproduce local validation, and record any Docker-unavailable check as unverified rather than passed.

Clone it with:

```bash
git clone https://github.com/FishRaposo/entrega-clara.git
```

## Non-production limitations

This is not a production payment platform, logistics company, or identity provider. The current runtime uses seeded or simulated payment references, roles, GPS updates, notifications, and operational data. It must not process real funds, customer card data, production credentials, real courier identity verification, or live support operations. Availability targets and privacy controls are documented portfolio evidence, not claims of production certification or measured uptime.

The governing product specification is [the seed design](docs/superpowers/specs/2026-08-29-food-delivery-platform-seed-design.md).
