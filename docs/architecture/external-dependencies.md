# External dependencies

**Status:** Current for the expanded milestone (routing scale, time dependence, windows, persistence)
**Product:** Entrega Clara
**Related:** [local development runbook](../runbooks/local-development.md), [platform evolution roadmap](../roadmap/platform-evolution.md)

The project is designed so that the complete product story runs with the smallest possible toolchain. This page is the inventory: what is required, what is optional configuration, and what is a documented future expansion with its prerequisites.

## Required to install, run, demo, and test

| Dependency | Purpose |
| --- | --- |
| Python 3.11+ and pip | FastAPI backend, domain/application code, repository and quality scripts |
| Node 24.15+ and npm | Next.js web shell, frontend tests and build |

Development-only tooling installed through the manifests above: pytest, ruff, and mypy for the backend; vitest, eslint, and TypeScript for the web; Playwright browsers for the end-to-end suite (downloaded by `npx playwright install`, test tooling only).

## Optional configuration

| Setting | Effect when present | Behavior when absent |
| --- | --- | --- |
| `ROUTING_GRAPH_PATH` | Loads that graph document for the product and the lab | Falls back to the committed OSM extract, then the synthetic lattice, then straight-line routing |
| `TRAFFIC_PROFILE_PATH` | Loads that time-of-day speed profile | Uses `data/graph/traffic-profile.json`; a missing profile means static ETAs |
| `PERSISTENCE_MODE=postgres` + `DATABASE_URL` | Durable snapshot persistence, optimistic version guard, transactional outbox (extra: `pip install -e "app/backend[postgres]"`) | Memory mode: no driver import, no database, no Docker |
| `MAPTILER_API_KEY` / `MAPTILER_STYLE_URL` | Reserved for the future MapLibre adapter (browser-visible configuration, never a backend secret) | The deterministic map fallback renders the route |

## Committed data derived from external sources

| Artifact | Source | Licence / obligation |
| --- | --- | --- |
| `data/graph/sao-paulo-centro-osm.json` | OpenStreetMap via the Overpass API, fetched offline by `scripts/data/fetch_osm_graph.py` | © OpenStreetMap contributors, ODbL 1.0 — attribution is stored in the document, served by the lab, shown on the lab page and repeated in the README. No network access at run time |
| `data/graph/sao-paulo-city.json.gz` | OpenStreetMap via a Geofabrik regional `.osm.pbf`, built offline by `scripts/data/build_city_graph.py` | Same attribution; committed as a 2.1 MB gzipped compact artifact |
| `data/graph/traffic-profile.json` | Synthetic, deterministic multipliers authored in-repo | Not measured traffic; the file says so |

## Documented future expansions

These are intentionally not part of the current runtime. Each has a designed boundary and prerequisites; none is required to run, demo, or test the project today.

| Expansion | Requires | Enabling contract / notes |
| --- | --- | --- |
| Real map tiles (MapLibre adapter) | `maplibre-gl` package + MapTiler account (free tier) + restricted browser key | The `DeliveryMap` props seam isolates map rendering; the shipped renderer is a deterministic SVG fallback |
| Payment providers (Mercado Pago, Stripe) | Provider account, credentials, webhook handling | `PaymentGateway` port + `PaymentAttempt` safe-reference model |
| Real authentication (OIDC) | Identity provider account, session layer | `IdentityContext` port + demo identity resolver |
| Push/SMS/email notifications | Provider account + credentials | `Notification` entity + `NotificationSender` port |
| Row-per-aggregate PostgreSQL schema / multi-writer | Migration work on top of the current snapshot adapter | Ports unchanged; see [ADR 0012](../adr/0012-postgres-adapter-outbox-and-metrics.md) |
| Geocoding / real road routing | Provider or self-hosted service, license review | Seeded-address and versioned-graph boundaries |

The PostgreSQL adapter and the transactional outbox are **implemented** (optional extra), not future work: see the [PostgreSQL runbook](../runbooks/postgres.md) and ADR 0012. SQLite was considered as a lightweight persistent option and set aside: the portfolio evidence calls for a credible transactional adapter rather than a second lightweight store.

## Non-negotiable rules

- No runtime code path may require an external service to complete the core customer-to-delivery journey.
- Provider SDKs stay in adapters; the domain never imports them.
- Browser bundles never contain service tokens, payment SDKs, or credentials.
- A missing optional provider produces a typed degraded state, never an invented success.
