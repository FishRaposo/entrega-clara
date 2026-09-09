# Milestone 1 development runbook

**Status:** Implementation guide; commands marked “planned” are not yet available in the scaffold
**Product:** Entrega Clara
**Design:** [M1 core delivery loop](../superpowers/specs/2026-09-01-milestone-1-core-delivery-loop-design.md)
**Research:** [platform build research](../research/2026-09-01-platform-build-research.md)

This runbook is for implementing and reviewing M1. It keeps the deterministic portfolio demo usable while the dynamic customer-to-delivery path is built.

## 1. M1 operating modes

| Mode | Persistence | External providers | Intended use |
| --- | --- | --- | --- |
| Memory demo | In-memory | Simulated payment, optional MapTiler | Default local demo, presentations, offline work |
| Memory test | In-memory/fakes | No network | Unit, API, component, and most E2E tests |
| PostgreSQL local | PostgreSQL | Simulated payment, optional MapTiler | Migration, repository, transaction, restart tests |
| Preview | Offline seed preview | No API/provider | Public-safe inspection of deterministic data |
| Future hosted | Managed PostgreSQL | Explicitly selected providers | Later deployment; requires security/legal/operations review |

M1 does not require real payment, GPS, geocoding, notification, or authentication credentials.

## 2. Prerequisites

- Python 3.11.
- Node 22, matching CI and the web package engine.
- Docker Compose for PostgreSQL/restart/Compose checks; Docker is optional for memory-mode work.
- A MapTiler browser key only if a real basemap is desired locally. It must be origin-restricted and never be a service token.
- A clean, public-safe fixture set. Do not copy personal, payment, courier, or private source data into the repository.

Before M1 implementation begins, raise the web manifest's current `^15.5.9` floor to at least the patched 15.5.24 maintenance release; the checked-in lockfile already resolves Next and `eslint-config-next` to 15.5.24. Alternatively, evaluate the Next 16.3.3 migration separately. Re-run lint, typecheck, tests, and build after the manifest change.

## 3. Configuration contract

The exact settings should be validated at application startup. The following names are the planned contract:

| Variable | Memory default | PostgreSQL/provider behavior |
| --- | --- | --- |
| `APP_ENV` | `development` | Use environment-specific value; never enable demo identity bypass in production |
| `APP_NAME` | `Entrega Clara` | Product metadata only |
| `PERSISTENCE_MODE` | `memory` | Set `postgres` to activate the SQLAlchemy adapter |
| `DATABASE_URL` | Not required | Required and reachable when `PERSISTENCE_MODE=postgres` |
| `DEMO_MODE` | `true` | Enables seeded identities/scenario controls; false for future authenticated runtime |
| `DEFAULT_LOCALE` | `pt-BR` | Market-configured |
| `DEFAULT_CURRENCY` | `BRL` | Market-configured; money remains integer minor units |
| `MAPTILER_API_KEY` | Empty | Browser-visible restricted key; empty means map fallback |
| `MAPTILER_STYLE_URL` | Empty | Public style URL; no provider means fallback |
| `PUBLIC_WEB_ORIGIN` | `http://localhost:3000` | CORS/redirect allowlist |
| `TRACKING_UPDATE_INTERVAL_SECONDS` | `2` | Deterministic simulator setting |
| `LOG_LEVEL` | `INFO` | Structured/redacted logs |

Never put payment secrets, OIDC secrets, MapTiler service tokens, or real database credentials in `.env.example`, fixtures, Dockerfiles, or browser code.

## 4. First-time local flow

The current scaffold supports the first four commands today. PostgreSQL migration and M1 route commands are planned additions.

```bash
cp .env.example .env
make install
make check
make demo-preview
```

When M1 implementation lands, add the following verification path:

```bash
# Memory mode: no database or provider required
PERSISTENCE_MODE=memory make dev-memory       # planned target

# PostgreSQL mode: Compose healthcheck and migrations required
docker compose up -d db
make db-migrate                                # planned target
PERSISTENCE_MODE=postgres make dev             # planned/updated target

# Full feature evidence
make test-e2e                                   # planned target
make test-postgres                              # planned target
```

Do not make `make check` depend on MapTiler, payment sandboxes, or a live geocoder.

## 5. M1 implementation order

Implement one vertical slice at a time:

1. Add domain/application ports and the memory transaction model.
2. Add SQLAlchemy models, Alembic environment, migrations, and Postgres repository.
3. Add catalog queries, cart commands, coupon rules, and authoritative totals.
4. Add checkout, payment simulator, order/item snapshots, and idempotency.
5. Add restaurant commands and role-scoped queue reads.
6. Add courier availability, assignment, pickup, delivery, and sequence-safe locations.
7. Add versioned graph, A*, Dijkstra oracle, route result, and route metrics.
8. Add MapLibre client adapter, MapTiler configuration, attribution, and fallback.
9. Add event envelope, audit/notification projections, deterministic simulator, and SSE.
10. Add operations read model, browser E2E, accessibility checks, docs, and release evidence.

Every command must go through the application service. Demo Mode must call those same commands rather than mutating a scenario object directly.

## 6. Manual acceptance journey

Run the journey once in memory mode and once in PostgreSQL mode:

1. Select the seeded Brazilian customer identity.
2. Search the focused restaurant catalog.
3. Open a restaurant and menu.
4. Add an available menu item, quantity, and observation.
5. Apply a valid coupon and inspect the authoritative total.
6. Submit simulated PIX, card, or wallet checkout.
7. Repeat the checkout request with the same idempotency key and verify no duplicate order.
8. Use the restaurant surface to confirm, prepare, and mark the order ready.
9. Use the courier surface to become available and accept the one active offer.
10. Verify route order: courier → restaurant → customer.
11. Start pickup/delivery and advance location through the deterministic simulator.
12. Observe order/tracking/notification updates via SSE.
13. Complete delivery and verify the customer sees `delivered`.
14. Open operations and inspect route metrics, audit history, and event sequence.
15. Reset only the lunch-rush scenario.
16. Verify the lunch-rush replay is identical and any dynamically created order remains.

The absence of a MapTiler key should change only the map panel, not the rest of this journey.

## 7. Required negative checks

Before calling M1 complete, verify:

- invalid or expired coupon leaves cart totals unchanged;
- unavailable menu item cannot be checked out;
- declined payment returns a safe reason and does not advance the order;
- a duplicate idempotency key returns the original result;
- a different request with an existing key returns a conflict;
- a customer cannot access another customer's order;
- a restaurant cannot act on another restaurant's order;
- a courier cannot act for another courier or accept a second active delivery;
- invalid lifecycle commands leave state unchanged;
- stale location sequences cannot overwrite newer locations;
- unauthorized SSE cannot reveal order/tracking data;
- SSE disconnect/reconnect returns a current snapshot;
- route generation failure leaves a recoverable delivery state;
- provider/map outage leaves timeline and last-known state visible;
- reset does not delete dynamic data;
- malformed requests return the safe error envelope, not a stack trace.

## 8. Database workflow

### Local PostgreSQL

The Compose database is for local development only. Before relying on it:

- add a healthcheck;
- make API startup wait for database readiness;
- run migrations through a controlled command or one-shot service;
- keep the database volume local and disposable;
- use synthetic fixtures only;
- test restart persistence separately from memory-mode replay.

### Migration rules

- One migration describes one intentional schema change.
- Review autogenerated Alembic output manually.
- Test upgrade from the previous release and a fresh database.
- Keep seed loading separate from schema migration.
- Do not silently drop columns/tables that contain audit/payment history.
- Document rollback or forward-fix behavior for destructive changes.

### Repository contract

The same contract suite must run against memory and PostgreSQL for:

- order creation and item snapshots;
- totals/coupon/payment behavior;
- lifecycle transactions and rollback;
- ownership filters;
- optimistic version conflict;
- event/audit/notification creation;
- scenario reset isolation.

## 9. Map setup and fallback

To enable the local map:

1. Create a MapTiler browser key.
2. Restrict it to local and preview origins.
3. Set `MAPTILER_API_KEY` and the selected public `MAPTILER_STYLE_URL` in local `.env`.
4. Confirm visible attribution.
5. Inspect provider quota/cost behavior before publishing a hosted demo.

Do not put the key in a backend secret variable and then assume it is hidden from the browser. Do not use a MapTiler service token in the web bundle. If the key is absent, the map adapter shows a static/fallback state and the route/timeline remains functional.

M1 route correctness is tested with local geometry and no network. Do not use provider directions as an implicit test oracle.

## 10. SSE troubleshooting

Expected behavior:

- response content type is `text/event-stream`;
- first message is the current snapshot;
- subsequent messages have stable IDs and event names;
- the browser reconnects after a temporary disconnect;
- reconnect triggers snapshot reconciliation;
- the stream closes when the request is cancelled;
- no long-lived ORM session is held by the stream.

If updates appear stale:

1. refetch the order/tracking snapshot;
2. inspect event sequence and aggregate version;
3. inspect correlation ID in API logs;
4. verify the command committed before event publication;
5. check that the client is authorized for the order;
6. check keepalive/proxy buffering before changing domain logic.

Do not “fix” an SSE symptom by making the browser invent state.

## 11. Quality commands and evidence

Current repository gates:

```bash
make seed-validate
make requirement-coverage
make app-boundary
make lint
make typecheck
make test
make check
```

M1 additions should include:

```bash
make test-postgres       # memory/Postgres repository contract and migrations
make test-api            # API integration, errors, authorization, SSE
make test-e2e            # Playwright complete journey
make test-a11y           # automated accessibility scan
make benchmark-routing  # bounded, reproducible solver measurements
```

The final report must distinguish:

- passed locally;
- passed in CI;
- skipped because Docker/browser/provider was unavailable;
- intentionally deferred by the M1 scope.

## 12. Public-demo release checklist

- [ ] M1 design and requirements traceability match the implementation.
- [ ] README states the current supported journey and all simulations.
- [ ] No real personal/payment data, credentials, private links, or generated environment files are tracked.
- [ ] Scenario seed passes public-safety validation.
- [ ] Memory mode works without external services.
- [ ] PostgreSQL mode is migration/restart tested or explicitly marked unverified.
- [ ] MapTiler key is not committed and attribution is visible.
- [ ] Dependency manifests/lockfiles are current and security-patched.
- [ ] Backend tests, frontend tests, type checks, lint, build, and browser journey pass.
- [ ] WCAG-oriented keyboard/focus/error checks are recorded.
- [ ] Route metrics state assumptions and exclude network/rendering time.
- [ ] Docker and provider checks are reported honestly.
- [ ] Future work is linked to the [platform evolution roadmap](../roadmap/platform-evolution.md).

## 13. Useful references

- [Docker Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/)
- [MapTiler API-key security](https://docs.maptiler.com/cloud/api/authentication-key/)
- [MapTiler key protection](https://docs.maptiler.com/guides/maps-apis/maps-platform/how-to-protect-your-map-key)
- [MapTiler attribution](https://docs.maptiler.com/guides/map-design/attribution/add-attribution/)
- [FastAPI SSE](https://fastapi.tiangolo.com/tutorial/server-sent-events/)
- [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [Playwright API testing](https://playwright.dev/docs/api-testing)
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)
