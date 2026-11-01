# External dependencies

**Status:** Current for the memory-mode milestone
**Product:** Entrega Clara
**Related:** [local development runbook](../runbooks/local-development.md), [platform evolution roadmap](../roadmap/platform-evolution.md)

The project is designed so that the complete product story runs with the smallest possible toolchain. This page is the inventory: what is required, what is optional configuration, and what is a documented future expansion with its prerequisites.

## Required to install, run, demo, and test

| Dependency | Purpose |
| --- | --- |
| Python 3.11+ and pip | FastAPI backend, domain/application code, repository and quality scripts |
| Node 22+ and npm | Next.js web shell, frontend tests and build |

Development-only tooling installed through the manifests above: pytest, ruff, and mypy for the backend; vitest, eslint, and TypeScript for the web; Playwright browsers for the end-to-end suite (downloaded by `npx playwright install`, test tooling only).

## Optional configuration

| Setting | Effect when present | Behavior when absent |
| --- | --- | --- |
| `ROUTING_GRAPH_PATH` | Loads that graph document for the product and the lab | Falls back to the committed OSM extract, then the synthetic lattice, then straight-line routing |
| `MAPTILER_API_KEY` / `MAPTILER_STYLE_URL` | Reserved for the future MapLibre adapter (browser-visible configuration, never a backend secret) | The deterministic map fallback renders the route |

## Committed data derived from external sources

| Artifact | Source | Licence / obligation |
| --- | --- | --- |
| `data/graph/sao-paulo-centro-osm.json` | OpenStreetMap via the Overpass API, fetched offline by `scripts/data/fetch_osm_graph.py` | © OpenStreetMap contributors, ODbL 1.0 — attribution is stored in the document, served by the lab, shown on the lab page and repeated in the README. No network access at run time |

## Documented future expansions

These are intentionally not part of the current runtime. Each has a designed boundary and prerequisites; none is required to run, demo, or test the project today.

| Expansion | Requires | Enabling contract / notes |
| --- | --- | --- |
| PostgreSQL adapter | Docker or a local PostgreSQL install; `sqlalchemy`, `alembic`, `psycopg` dependencies; Alembic migrations | Repository/unit-of-work ports already defined; see [ADR 0003](../adr/0003-hybrid-persistence.md) and the M1.5 re-entry note in the [roadmap](../roadmap/platform-evolution.md) |
| Docker Compose services (`db`, `api`, `web`) | Docker Engine or compatible runtime | `docker-compose.yml` and Dockerfiles remain in-repo as the future container path; not the local run path |
| Real map tiles (MapLibre adapter) | `maplibre-gl` package + MapTiler account (free tier) + restricted browser key | The `DeliveryMap` props seam isolates map rendering; the shipped renderer is a deterministic SVG fallback — swapping in a MapLibre adapter is a contained component change |
| Payment providers (Mercado Pago, Stripe) | Provider account, credentials, webhook handling | `PaymentGateway` port + `PaymentAttempt` safe-reference model |
| Real authentication (OIDC) | Identity provider account, session layer | `IdentityContext` port + demo identity resolver |
| Push/SMS/email notifications | Provider account + credentials | `Notification` entity + `NotificationSender` port |
| Durable outbox / queue workers | Broker (e.g., Redis Streams, Celery) | Committed `DomainEvent` records; required before multiple API processes |
| Geocoding / real road routing | Provider or self-hosted service, license review | Seeded-address and versioned-graph boundaries |

SQLite was considered as a lightweight persistent option and set aside: the portfolio evidence calls for a credible relational adapter (PostgreSQL via SQLAlchemy/Alembic) rather than a second lightweight store.

## Non-negotiable rules

- No runtime code path may require an external service to complete the core customer-to-delivery journey.
- Provider SDKs stay in adapters; the domain never imports them.
- Browser bundles never contain service tokens, payment SDKs, or credentials.
- A missing optional provider produces a typed degraded state, never an invented success.
