# Entrega Clara: platform build research

**Status:** Research baseline for Milestone 1 and later implementation
**Date checked:** 2026-09-01
**Product:** Entrega Clara
**Repository:** [FishRaposo/entrega-clara](https://github.com/FishRaposo/entrega-clara)
**Governing design:** [Milestone 1 core delivery loop](../superpowers/specs/2026-09-01-milestone-1-core-delivery-loop-design.md)

This document records the research, recommendations, constraints, and unresolved choices that should guide implementation. It is a technical planning document, not a claim that the future capabilities already exist. The current repository is still a scaffold with a deterministic demo scenario; the M1 design turns that scaffold into the first complete product slice.

The research was checked against primary or authoritative sources on 2026-09-01. Technology versions, provider terms, pricing, legal requirements, and security guidance can change. Re-check the source index and the dependency manifests before implementing or deploying.

## 1. Executive conclusions

| Area | Milestone 1 decision | Later direction |
| --- | --- | --- |
| Application shape | FastAPI modular monolith with explicit application, domain, repository, and adapter boundaries | Split only measured bottlenecks into services or workers |
| Persistence | In-memory adapter by default; PostgreSQL adapter is opt-in; one active adapter per process | Managed PostgreSQL, migrations, backups, read replicas, and PostGIS when justified |
| ORM and migrations | SQLAlchemy 2-style repositories and Alembic migrations | Keep database access behind ports; add an outbox before durable asynchronous delivery |
| Product flow | Customer discovery through delivery, with restaurant, courier, customer, and read-only operations views | Reviews, support, refunds, richer admin, and marketplace breadth |
| Payments | Provider-neutral simulated gateway with approved and declined outcomes | Evaluate Mercado Pago for Brazil/PIX and Stripe for international expansion; verify webhooks server-side |
| Identity | Seeded demo identities and API-enforced role/ownership checks | OIDC/OAuth authorization-code flow with PKCE and secure sessions |
| Routing | Local deterministic A* over a versioned synthetic graph; Dijkstra is a correctness oracle; legacy brute-force TSP remains a baseline | Multi-stop optimization, dispatch, real-road graph/provider comparison, and benchmark laboratory |
| Maps | MapLibre GL renderer with a MapTiler browser key when configured; backend owns route geometry | Provider comparison, geocoding, road-network data, and usage/cost controls |
| Realtime | REST commands plus SSE snapshot-and-stream for order and tracking updates | Durable outbox, broker/consumer groups, push notifications, and horizontally scalable subscriptions |
| Testing | Unit, repository-contract, API, frontend, accessibility, and one complete Playwright journey | Cross-browser/device matrix, load/chaos tests, security automation, and production observability |
| Public safety | Synthetic data only; no payment secrets, exact personal locations, or private source links | Formal data inventory, retention/deletion/export, incident response, and legal review for real processing |

The most important architectural rule is that every role acts on the same order through application commands. The UI is not allowed to become four independent mock dashboards.

## 2. Current baseline and gap

The published repository currently proves the following:

- FastAPI health and deterministic demo endpoints.
- A domain order state machine and validation errors.
- Resettable lunch-rush seed data with reproducible events.
- A responsive role shell for Customer, Restaurant, Courier, Admin, and Demo routes.
- A solver-independent routing contract and the preserved brute-force TSP baseline.
- CI, traceability, seed-safety, repository-boundary, lint, type, test, and build checks.
- A PostgreSQL Compose service, but not yet a PostgreSQL-backed application repository.

The current repository does not yet provide:

- restaurant discovery, menus, carts, checkout, or order creation;
- a persistent application data model or migrations;
- a real shared customer/restaurant/courier order workflow;
- route geometry rendered on a map;
- SSE or another live event transport;
- real authentication, provider payment, notification, geocoding, or support integrations;
- the replacement routing solver or benchmark laboratory.

This distinction matters in portfolio language: the scaffold demonstrates architectural intent and one deterministic state loop; M1 must demonstrate the product loop.

## 3. Scope hierarchy

### 3.1 Milestone 1: the complete core loop

M1 is complete when a seeded demo customer, or a dynamically created customer order, can travel through:

```text
discover → menu → cart → coupon → simulated checkout → restaurant prep
→ courier assignment → local route → simulated tracking → delivered
```

The same domain commands must be available from interactive role surfaces and deterministic Demo Mode. M1 ends at `delivered`; reviews and ratings are explicitly deferred.

M1 must work in both persistence modes:

- `memory`: default, fast, offline, resettable, and deterministic;
- `postgres`: opt-in, transactionally persistent, migration-backed, and restart-safe.

The map is an enhancement to the operational story, not a correctness dependency. If MapTiler is absent or unavailable, the timeline, last-known location, and route metrics remain usable.

### 3.2 Beyond M1

Later work is ordered around dependencies rather than feature volume:

1. Trust and identity: real sessions, ownership, reviews, support, cancellations, and refunds.
2. Routing intelligence: replacement solvers, multi-stop constraints, dispatch, and benchmark evidence.
3. Production integrations: payment webhooks, geocoding, road routing, notifications, and provider health.
4. Scale and operations: outbox, workers, caching, observability, recovery, and deployment hardening.
5. Market expansion and portfolio polish: market packs, accessibility maturity, PWA/mobile behavior, screenshots, and a narrated demo.

The full stage plan is in [platform evolution roadmap](../roadmap/platform-evolution.md).

## 4. M1 build contract

| Capability | Required behavior | Evidence required |
| --- | --- | --- |
| Discovery | Search/filter a focused Brazilian catalog and open a restaurant/menu | API tests, component tests, browser journey |
| Cart | Add, update, remove, and observe cart totals | Domain tests and customer journey |
| Coupons | Accept a valid coupon and give a safe reason for invalid/expired/ineligible codes | Rule tests and declined-case journey |
| Checkout | Snapshot cart lines, calculate BRL minor-unit totals, create an order, and create a payment attempt | Transaction test and idempotency test |
| Payment | Simulate approved and declined PIX/card/wallet outcomes without raw card data | Gateway contract tests |
| Restaurant | Confirm, start preparation, and mark ready | Authorization and transition tests |
| Courier | Set availability, accept one offer, pick up, start delivery, update location, complete | Ownership, sequence, and transition tests |
| Route | Generate courier→restaurant→customer legs through local A* | Solver tests, Dijkstra oracle, route-invariant tests |
| Map | Render backend GeoJSON using MapLibre/MapTiler when configured | Fake-adapter tests, manual map check, attribution check |
| Realtime | Send current snapshot then authorized order/tracking events over SSE | Stream contract, reconnect, and permission tests |
| Operations | Read shared order state, route metrics, audit records, and demo controls | API/read-model tests and role-access tests |
| Reset/replay | Reset only the named deterministic scenario; replay yields identical results | Snapshot equality and isolation tests |
| Safety | No real identities, payment data, exact private coordinates, credentials, or provider payloads in fixtures/logs | Seed validator, secret scan, public-repo review |
| Documentation | Keep API, event, persistence, map, environment, testing, and deferred-roadmap docs in sync | Docs review checklist |

## 5. Recommended architecture

### 5.1 Module responsibilities

| Module | Owns | Does not own |
| --- | --- | --- |
| `identity` | Demo identity resolution, roles, ownership, future sessions | UI-only role visibility |
| `catalog` | Restaurants, menus, availability, search filters | Checkout totals or payment status |
| `cart` | Mutable pre-order selection and coupon application | Immutable order snapshots |
| `orders` | Order creation, item snapshots, totals, lifecycle transitions | Provider SDK behavior |
| `payments` | Payment attempt state and provider-neutral gateway port | Raw card data or client-trusted success |
| `delivery` | Courier availability, assignment, pickup, route reference, delivery lifecycle | Route algorithm internals |
| `routing` | Graphs, shortest path, route result, solver metadata | Map rendering or browser state |
| `tracking` | Ordered positions, timestamps, ETA projection, simulation clock | Live device authentication |
| `notifications` | User-facing lifecycle projections and read state | Payment or order truth |
| `audit` | Append-only actor/action/target/state records | Mutable business state |
| `operations` | Read-only cross-module operational projections in M1 | Arbitrary admin mutation |
| `demo` | Seed loading, scenario reset, deterministic advancement | Direct repository mutation outside application commands |

Application services orchestrate use cases. Domain objects enforce invariants. Repositories persist aggregates. Adapters implement ports for memory, PostgreSQL, simulated payments, events, maps, clocks, and future vendors.

### 5.2 Command flow

Every state-changing request follows the same sequence:

1. Resolve the identity and correlation ID.
2. Authorize the operation and ownership scope.
3. Load the aggregate(s) through repository ports.
4. Validate the command against current state and version.
5. Apply domain changes.
6. Append audit, notification, and event-log records in the same unit of work.
7. Commit atomically.
8. Publish committed events to the in-process hub.
9. Return a typed response with the new aggregate version.

No event is published as a success signal before commit. SSE is a projection channel, not the source of truth. A reconnecting client gets a fresh snapshot.

### 5.3 Concurrency model

M1 should use a monotonically increasing `version` on mutable aggregates such as cart, order, delivery, courier, and scenario state. A command that carries an optional expected version must fail with a safe conflict if the stored version changed. Tracking updates also carry a per-delivery sequence; an older sequence is ignored or rejected and can never overwrite newer location state.

This is enough to demonstrate correct boundaries without introducing distributed locks. PostgreSQL constraints remain the last line of structural protection.

## 6. Hybrid persistence research and plan

### 6.1 Recommendation

Use SQLAlchemy 2-style repositories with explicit transactions and Alembic migrations for the PostgreSQL adapter. Keep the default M1 application path in memory. The two adapters must satisfy the same repository-contract test suite.

For M1, prefer synchronous SQLAlchemy sessions inside short application commands. This keeps domain/application code straightforward and avoids coupling the entire codebase to implicit async ORM behavior. The SSE endpoint is a separate asynchronous transport and must not hold a database session open while streaming. Revisit SQLAlchemy `AsyncSession` only if measured concurrency or I/O requires it; the official async documentation warns that implicit lazy I/O needs explicit handling.

Research basis:

- [SQLAlchemy ORM](https://docs.sqlalchemy.org/orm/) and [session basics](https://docs.sqlalchemy.org/en/latest/orm/session_basics.html) describe the ORM/session model.
- [SQLAlchemy transactions](https://docs.sqlalchemy.org/en/latest/orm/session_transaction.html) document explicit transaction boundaries.
- [SQLAlchemy asyncio](https://docs.sqlalchemy.org/en/latest/orm/extensions/asyncio.html) documents the async ORM and its I/O constraints.
- [Alembic](https://alembic.sqlalchemy.org/) is the migration tool for SQLAlchemy; [autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html) produces candidate revisions that must be reviewed rather than blindly trusted.
- [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html), [indexes](https://www.postgresql.org/docs/current/sql-createindex.html), and [transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html) provide the database safeguards.

### 6.2 M1 relational shape

The schema should be introduced by versioned migrations. Exact table names can change during implementation, but the following responsibilities must remain explicit:

| Table family | Core records |
| --- | --- |
| Identity and market | `demo_identities`, `market_configs`, `addresses` |
| Catalog | `restaurants`, `menu_items`, `menu_categories` |
| Cart and promotion | `carts`, `cart_items`, `coupons`, `cart_coupons` |
| Order and payment | `orders`, `order_items`, `payment_attempts` |
| Delivery | `couriers`, `deliveries`, `route_plans`, `route_stops` |
| Tracking and communication | `tracking_events`, `notifications` |
| Governance | `audit_events`, `domain_events` or `event_log` |
| Demo control | `scenario_instances` or equivalent scoped scenario metadata |

Structural rules:

- Store money as integer minor units plus ISO currency, never floating point.
- Store UTC timestamps and localize only at the presentation boundary.
- Snapshot item name, unit price, and relevant modifiers into `order_items` at checkout.
- Use unique constraints for stable identifiers, coupon codes, and one active M1 delivery per courier.
- Use check constraints for nonnegative quantities, amounts, and sequence values.
- Use indexes for customer order history, restaurant queue, active courier lookup, order events, and tracking sequence.
- Consider a partial unique index for an active delivery per courier; review the exact status predicate during migration design.
- Keep lifecycle transitions in the domain; database constraints should protect structure, not duplicate the entire state machine.
- Use foreign keys and deliberate delete behavior. Do not cascade-delete audit or payment history accidentally.

### 6.3 Migrations, seed, and reset

Schema migrations and demo data are different concerns:

- migrations change structure and must be reviewed, reversible where practical, and run before the API starts in persistent mode;
- seed loaders insert stable catalog/identity fixtures idempotently;
- scenario reset restores only records owned by the scenario and never truncates the database;
- dynamic orders created outside the scenario survive a scenario reset;
- public seed validation rejects secret-like values and realistic personal identities/locations;
- production data must never be used as a fixture or copied into the public repository.

The current Compose service should gain a database healthcheck and an API startup/migration strategy before PostgreSQL mode is presented as reliable. Docker Compose's startup-order guidance states that `depends_on` alone does not wait for a database to be ready; use a healthcheck and `condition: service_healthy`.

Research basis: [Compose startup order and healthchecks](https://docs.docker.com/compose/how-tos/startup-order/), [Compose configuration](https://docs.docker.com/compose/how-tos/environment-variables/), and [PostgreSQL partial indexes](https://www.postgresql.org/docs/current/indexes-partial.html).

### 6.4 Future durability path

M1 may publish events from an in-process hub after commit. That is sufficient for one API process and a demo, but it is not crash-proof: a process can commit the database and fail before publishing. Before multiple API instances or external notifications, add a transactional outbox:

```text
application transaction → aggregate rows + audit + outbox row
worker claims outbox row → publishes event → records retry/dead-letter outcome
```

Outbox records need stable event IDs, attempts, visibility time, and a bounded payload version. Consumers must be idempotent. Redis Streams or a task system such as Celery are later options, not M1 dependencies. [Redis Streams](https://redis.io/docs/latest/develop/data-types/streams/) provide an append-only log-like structure with consumer groups; [Celery task guidance](https://docs.celeryq.dev/en/stable/userguide/tasks.html) emphasizes idempotent tasks and careful acknowledgement/retry behavior.

## 7. API and contract research

### 7.1 HTTP contract

Use `/api/v1` and treat FastAPI's generated OpenAPI document as the machine-readable API contract. OpenAPI is designed to let humans and tools understand an HTTP interface without reading implementation code; see the [OpenAPI 3.1 specification](https://spec.openapis.org/oas/v3.1.1.html).

M1 read resources:

```text
GET  /api/v1/restaurants
GET  /api/v1/restaurants/{restaurant_id}
GET  /api/v1/restaurants/{restaurant_id}/menu
GET  /api/v1/me/cart
GET  /api/v1/me/addresses
GET  /api/v1/me/orders
GET  /api/v1/orders/{order_id}
GET  /api/v1/orders/{order_id}/tracking
GET  /api/v1/orders/{order_id}/notifications
GET  /api/v1/restaurant/orders
GET  /api/v1/courier/deliveries/offers
GET  /api/v1/courier/deliveries/active
GET  /api/v1/operations/orders/{order_id}
GET  /api/v1/operations/events
GET  /api/v1/operations/metrics
```

M1 commands:

```text
POST   /api/v1/me/cart/items
PATCH  /api/v1/me/cart/items/{line_id}
DELETE /api/v1/me/cart/items/{line_id}
POST   /api/v1/me/cart/coupon
DELETE /api/v1/me/cart/coupon
POST   /api/v1/me/orders/checkout
POST   /api/v1/restaurant/orders/{order_id}/confirm
POST   /api/v1/restaurant/orders/{order_id}/prepare
POST   /api/v1/restaurant/orders/{order_id}/ready
PUT    /api/v1/courier/availability
POST   /api/v1/courier/deliveries/{delivery_id}/accept
POST   /api/v1/courier/deliveries/{delivery_id}/pickup
POST   /api/v1/courier/deliveries/{delivery_id}/start
POST   /api/v1/courier/deliveries/{delivery_id}/location
POST   /api/v1/courier/deliveries/{delivery_id}/complete
GET    /api/v1/orders/{order_id}/stream
```

Demo controls remain explicitly namespaced under `/api/v1/demo` and must call the same application services as role actions.

### 7.2 Error envelope

All domain and integration failures should serialize to a stable safe shape:

```json
{
  "type": "https://entrega-clara.example/errors/coupon-invalid",
  "title": "Coupon cannot be applied",
  "status": 422,
  "code": "coupon_invalid",
  "detail": "The coupon is not valid for this cart.",
  "field_errors": {},
  "correlation_id": "cor_..."
}
```

The example hostname is illustrative; do not make a public endpoint from this document without choosing a canonical error namespace. `type`, `code`, and `status` are stable contract fields. `detail` is safe user-facing language. Provider payloads, SQL text, stack traces, credentials, and internal object addresses never leave the server.

### 7.3 Idempotency and pagination

`POST /me/orders/checkout` requires an `Idempotency-Key`. The server stores a scoped request fingerprint and response. Repeating the same key with the same request returns the original result; reusing it with a different payload returns a conflict. The same principle must be used for future payment creation and webhook handling.

List endpoints should start with bounded page sizes and a cursor-compatible response shape, even if the first seed is small. Do not make an unbounded `GET /orders` the future contract.

### 7.4 Demo identity boundary

M1 may use a server-known demo identity selected by the role switcher, but the resolver must be isolated behind an `IdentityContext` port. A client-provided role string is never authorization. In development/demo mode, an explicit demo identity header or cookie can be accepted only after validating that the identity exists and that the environment permits demo identities. In any future authenticated environment, the demo resolver is disabled.

## 8. Realtime and event research

SSE is appropriate for M1 because the browser needs server-to-client order, tracking, notification, and demo updates; commands still use ordinary HTTP. FastAPI documents SSE support and event responses in its [SSE tutorial](https://fastapi.tiangolo.com/tutorial/server-sent-events/) and [SSE reference](https://fastapi.tiangolo.com/reference/sse/). The browser API is documented by [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) and [MDN's SSE usage guide](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events).

### 8.1 M1 event envelope

Every event should include:

| Field | Purpose |
| --- | --- |
| `id` | Globally unique event ID and SSE `id` value |
| `type` | Stable event name such as `order.confirmed` |
| `aggregate_type` / `aggregate_id` | Resource whose state changed |
| `actor_id` / `actor_role` | Authorized actor or simulator |
| `correlation_id` | Ties command, logs, audit, and downstream effects together |
| `sequence` | Monotonic aggregate or delivery sequence |
| `occurred_at` | UTC event time |
| `payload_version` | Compatibility/versioning marker |
| `payload` | Typed, redacted event data |

M1 event names:

```text
order.placed
payment.approved
payment.declined
order.confirmed
order.preparing
order.ready
delivery.assigned
delivery.picked_up
delivery.en_route
courier.location_updated
delivery.delivered
notification.created
audit.recorded
tracking.delayed
```

### 8.2 Stream behavior

`GET /orders/{order_id}/stream` should:

1. authenticate/resolve the identity for the request;
2. authorize access to the order;
3. send the current order/tracking snapshot;
4. send subsequent authorized events as `text/event-stream`;
5. include an event ID and event name for each event;
6. send keepalive comments or an agreed heartbeat;
7. close cleanly on cancellation;
8. let the browser reconnect with `Last-Event-ID`, but still refetch a snapshot because M1's in-process hub is not a durable history.

The API should not promise lossless replay until an outbox/event log and retention policy exist. When the stream is unavailable, the UI shows the last known state and timestamp.

### 8.3 Scale path

The future progression is:

```text
in-process hub → transactional outbox → broker/consumer groups → provider delivery
```

Do not introduce Redis, Celery, or WebSockets only because they sound production-like. Add them when there are multiple API processes, external notification work, long-running route jobs, or measured SSE fan-out needs.

## 9. Map and routing research

### 9.1 Ownership decision

The backend owns route calculation and returns a provider-neutral route result. The frontend owns rendering. MapTiler supplies tiles/style data; it does not become the domain's routing authority. This separation preserves the routing thesis and allows a different map or directions provider later.

MapLibre GL JS is a WebGL map renderer with style and GeoJSON source APIs. Use a client-only React adapter because Next.js server components cannot access browser APIs. The [Next.js Server and Client Components guide](https://nextjs.org/docs/app/getting-started/server-and-client-components) describes the boundary; MapLibre documents its [GL JS API](https://www.maplibre.org/maplibre-gl-js/docs/) and [GeoJSON source updates](https://www.maplibre.org/maplibre-gl-js/docs/API/classes/GeoJSONSource/).

### 9.2 M1 route contract

`RouteProblem` should contain:

- graph ID and graph version;
- current courier origin node/coordinate;
- ordered pickup and drop-off stops;
- travel-cost assumptions;
- solver name/version and deterministic seed where applicable.

`RouteResult` should contain:

- ordered stop IDs;
- one courier→restaurant segment and one restaurant→customer segment;
- route geometry as GeoJSON or an equivalent provider-neutral representation;
- distance and estimated travel time with units;
- solver name/version;
- computation time and nodes expanded;
- warnings and degraded-state metadata.

Required invariants:

- all required stops occur exactly once;
- restaurant pickup precedes customer drop-off;
- geometry endpoints correspond to the segment endpoints;
- distance is finite and nonnegative;
- a route is associated with the graph version that produced it;
- stale location updates cannot rewrite a newer tracking sequence.

### 9.3 Solver progression

M1:

- A* is the live local shortest-path solver;
- Dijkstra is a small correctness oracle in tests;
- the legacy brute-force TSP remains available for comparison but is not used for the live two-leg route;
- the graph is synthetic, versioned, and geographically aligned with the chosen viewport.

Later:

- exact or branch-and-bound solver for bounded comparisons;
- nearest-neighbor plus 2-opt for explainable multi-stop optimization;
- pickup/drop-off precedence, capacity, time windows, and late-delivery penalties;
- dispatch assignment across multiple couriers;
- provider/solver comparisons using the same input contract;
- real-road graph or routing service only after licensing, freshness, and cost are addressed.

### 9.4 Map provider safety

MapTiler states that unprotected public keys can be stolen and used against the account quota; its [API key documentation](https://docs.maptiler.com/cloud/api/authentication-key/) recommends protecting keys. Its [key-protection guide](https://docs.maptiler.com/guides/maps-apis/maps-platform/how-to-protect-your-map-key) documents allowed HTTP origins and user-agent restrictions. A browser map key is not a secret: restrict it through the provider's protection controls, monitor quota, and never use a service token in browser code. MapTiler distinguishes service tokens for hidden backend use in its [authentication guide](https://docs.maptiler.com/cloud/api/authentication/).

The UI must show required attribution. See [MapTiler attribution guidance](https://docs.maptiler.com/guides/map-design/attribution/add-attribution/). If OpenStreetMap-derived data is bundled or transformed, review the [OpenStreetMap Foundation attribution guidelines](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines) and ODbL obligations before publishing it. The safest M1 public fixture is a custom synthetic graph plus a properly attributed external basemap.

When no browser key is configured, use a fake/static map state or a clear unavailable panel. The order flow cannot fail merely because a tile provider is unavailable.

### 9.5 Future geospatial data

PostGIS becomes useful when the system owns spatial queries, nearby restaurants, real courier positions, geofences, or a road graph. Its documentation covers geometry/geography, spatial indexes, and indexed spatial queries: [database management](https://postgis.net/docs/using_postgis_dbmanagement.html) and [spatial queries](https://postgis.net/docs/using_postgis_query.html).

OSRM is one possible later road-routing adapter; its [HTTP API documentation](https://project-osrm.org/docs/v26.4.0/http) covers route, table, and trip services. It would require an explicit data acquisition, update, hosting, latency, and attribution decision. It is not an M1 dependency.

## 10. Frontend research and design

### 10.1 Next.js boundary

Keep server components as the default for static/read-oriented composition and use client components for forms, role switching, EventSource, MapLibre, and browser APIs. Keep all API/provider calls in typed adapters; role pages should not manually construct untyped fetch payloads.

The web manifest currently declares a `^15.5.9` range, while the checked-in lockfile resolves Next and `eslint-config-next` to `15.5.24`. The official [August 2026 Next.js security release](https://nextjs.org/blog/august-2026-security-release) says applications should update to at least Next 15.5.24 (Maintenance LTS) or Next 16.3.3 (Active LTS). Before M1 implementation, raise the manifest floor to the patched 15 line and keep the matching ESLint package aligned; the lockfile already provides the patched resolution. Evaluate Next 16 as a separate migration, not as incidental feature work.

Node 22 remains a valid LTS line for the repository; Node's [release schedule](https://nodejs.org/en/about/previous-releases) should be consulted when choosing the next major. Keep CI and local development on the same supported major.

### 10.2 UI state and errors

Use server/API state as the source of truth. A cart can be optimistic only with rollback and a subsequent authoritative response. Order state, tracking, notifications, and role permissions must be refetched after reconnect, tab focus, or command conflict.

Every async surface needs:

- loading state;
- empty state;
- recoverable error state;
- unavailable provider state;
- last-updated timestamp where freshness matters;
- keyboard-visible focus and semantic status messaging;
- reduced-motion behavior for courier movement and status transitions.

### 10.3 Accessibility target

Use WCAG 2.2 AA as the product target for the portfolio release, with keyboard and screen-reader checks on the M1 path. [WCAG 2.2](https://www.w3.org/TR/WCAG22/) adds relevant guidance for focus visibility, target size, redundant entry, accessible authentication, and mobile/cognitive needs. Automated checks do not replace manual keyboard and semantic review.

## 11. Payments and identity research

### 11.1 M1 simulated payment

The simulated gateway should model the provider boundary, not merely return a boolean. Use statuses such as:

```text
created → processing → approved
                    ↘ declined
                    ↘ requires_action (future-capable)
```

Store only a safe payment method label, safe reference, status, failure code, and timestamps. Checkout creates one order/payment attempt with an idempotency key. A declined attempt must leave a safe, retryable cart state and must not create a delivered order.

### 11.2 Future provider evaluation

For a Brazil-first implementation, Mercado Pago is a candidate because its Brazil documentation covers PIX and webhook notifications: [PIX payment submission](https://www.mercadopago.com.br/developers/pt/docs/checkout-bricks/payment-brick/payment-submission/pix) and [Checkout API notifications](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/notifications). Stripe is a candidate for international markets; its [Payment Intents](https://docs.stripe.com/payments/payment-intents), [idempotency](https://docs.stripe.com/api/idempotent_requests), and [webhooks](https://docs.stripe.com/webhooks) documentation describes the corresponding flow.

This is not a provider selection. Before integration, compare country availability, PIX/card/wallet coverage, settlement and refund semantics, webhook guarantees, fees, fraud/3DS behavior, merchant onboarding, tax obligations, SDK support, and test environments.

Rules for any real provider:

- create payment intents server-side;
- use idempotency keys;
- verify webhook signatures and deduplicate event IDs;
- treat webhooks/server status as authoritative, not a browser redirect;
- never log or persist raw card data, CVV, client secrets, or full provider payloads;
- reconcile provider and order state;
- keep the provider SDK inside an adapter.

### 11.3 Future authentication

M1 uses seeded demo identities, not passwords or external login. For real accounts, use an external OIDC provider with Authorization Code + PKCE, server-side session handling, secure cookies, and explicit role/ownership checks. [RFC 7636](https://www.rfc-editor.org/rfc/rfc7636) defines PKCE; [RFC 9700](https://datatracker.ietf.org/doc/html/rfc9700) is the current OAuth 2.0 security best-current-practice reference. [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html) defines the identity layer.

Do not build password storage, email verification, account recovery, or social-login policy as an incidental M1 feature. First decide whether the project uses a managed identity provider or a self-hosted one, then document trust boundaries and data processing.

## 12. Brazil-first and international market model

The domain should use a `MarketConfig` rather than scattered country conditionals. At minimum it supplies:

| Concern | Brazil M1 example | Future market variation |
| --- | --- | --- |
| Locale | `pt-BR` | `en-CA`, `es-MX`, etc. |
| Currency | BRL, minor-unit integers | CAD, USD, and currency-specific rounding |
| Payment methods | simulated PIX, card, wallet | provider and market-specific methods |
| Address | seeded Brazilian format | country-specific fields and validation |
| Time zone | configured market zone | user/restaurant/courier zone policy |
| Tax/fees | explicit demo values | tax engine or market rules |
| Distance | metric | market display preference |
| Legal copy | LGPD-aware demo text | local privacy/consumer/payment rules |
| Map/geocoding | provider adapter and synthetic graph | provider/data licensing by market |

Money, timestamps, addresses, payment method labels, privacy copy, and notification templates must be market-aware at the boundary. The domain should not embed `BRL` or Portuguese strings in generic rules.

## 13. Security, privacy, and LGPD-aware design

This repository can be privacy-aware without claiming legal compliance. The [LGPD compiled text](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/L13709compilado.htm), [ANPD data-subject rights](https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados-1/direito-dos-titulares), and [ANPD RIPD guidance](https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/relatorio-de-impacto-a-protecao-de-dados-pessoais-ripd) are the starting references for future legal/privacy work. Legal counsel is required before real processing or a compliance claim.

### 13.1 Data classes

| Class | Examples | M1 policy | Future policy |
| --- | --- | --- | --- |
| Public synthetic | Fictional restaurant/menu labels, demo IDs | Allowed in repo after safety checks | Keep provenance and license metadata |
| Operational | Order state, route metrics, audit event | Synthetic or local-only | Role-restrict, retain by policy |
| Personal | Customer identity/address, courier location | Seeded/generalized only | Purpose limitation, access/export/delete, retention |
| Sensitive/financial | Payment credentials, auth secrets, precise location history | Never commit or process real values | Provider tokenization, encryption, access review, incident plan |

Exact courier location and delivery addresses should be treated as personal-data risk even in a demo. Logs use IDs and generalized coordinates; they do not dump full request bodies or provider responses.

### 13.2 M1 security baseline

- API authorization is enforced independently of frontend route visibility.
- All state-changing commands validate actor, ownership, current state, and version.
- CORS, allowed origins, request size, and rate limits are explicit environment/configuration decisions.
- Secrets are supplied at runtime and excluded from images, fixtures, logs, and commits.
- Map browser keys are referrer/origin restricted; service tokens remain backend-only.
- Error responses are safe and correlated but do not reveal infrastructure details.
- Audit events record sensitive changes without storing unnecessary personal payloads.
- Security tests cover forbidden cross-role and cross-owner access.
- The portfolio release uses [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) Level 1 as a minimum checklist and selected Level 2 controls for authentication, data protection, and logging. ASVS is a verification baseline, not a certification.

### 13.3 Future data-subject operations

Before production-like identity or tracking data, design:

- data inventory and controller/operator responsibilities;
- purpose and lawful-basis records with legal review;
- retention/deletion schedule;
- account export and deletion workflow;
- correction and access request handling;
- consent/preference records where applicable;
- incident response and breach notification process;
- privacy impact assessment/RIPD if processing creates high risk.

## 14. Testing and quality research

### 14.1 Test pyramid

| Layer | Scope | M1 requirement |
| --- | --- | --- |
| Domain unit | transitions, totals, coupons, permissions, route invariants | Fast and exhaustive edge cases |
| Solver differential | A*/Dijkstra/legacy baseline on bounded graphs | Correctness and metadata, no network |
| Repository contract | Same scenario against memory and PostgreSQL adapters | Behavior parity and transaction rollback |
| API integration | FastAPI routes, error envelopes, SSE authorization | Commands, snapshots, conflict/idempotency |
| Frontend unit/component | forms, cart, role surfaces, error/loading states | Vitest with fake API/map/event adapters |
| Browser E2E | one complete customer-to-delivery journey | Playwright API setup + browser assertions |
| Accessibility | semantics, keyboard, focus, status announcements, contrast, motion | Automated scan plus manual review |
| Operational | migration, seed, reset, Compose readiness, build | CI and documented local checks |

Keep Vitest for fast frontend unit/component tests. Add Playwright Test for browser and API-level end-to-end work; its official docs cover [browser projects](https://playwright.dev/docs/browsers), [writing tests](https://playwright.dev/docs/writing-tests), and [API testing](https://playwright.dev/docs/api-testing). Tests must not depend on MapTiler availability or real payment providers.

### 14.2 Required M1 scenarios

1. Happy path: browse → cart → valid coupon → approved checkout → delivered.
2. Declined payment: checkout returns safe decline; cart/order behavior is explicit and retryable.
3. Invalid coupon: no total mutation and safe error.
4. Item unavailable during checkout: no partial order.
5. Duplicate checkout request: same idempotent result, no duplicate order.
6. Restaurant ownership: operator cannot mutate another restaurant's order.
7. Courier ownership/capacity: courier cannot accept another courier's offer or a second active delivery.
8. Transition conflict: stale or invalid command leaves state unchanged.
9. Tracking ordering: old location sequence cannot overwrite new state.
10. SSE reconnect: snapshot restores current truth after disconnect.
11. Scenario reset isolation: dynamic order survives lunch-rush reset.
12. Memory/PostgreSQL parity: repository-contract results match.
13. Map unavailable: delivery workflow remains usable.
14. Keyboard/mobile: customer checkout and courier actions remain operable without pointer-only interactions.

### 14.3 Accessibility and browser matrix

The portfolio target is WCAG 2.2 AA-oriented behavior, not a formal conformance claim until a manual audit exists. Test Chromium in CI first, then add Firefox/WebKit and mobile emulation with Playwright when the flow stabilizes. Use stable semantic locators and assertions that wait for observable state instead of arbitrary timeouts.

### 14.4 Benchmarks

Routing benchmarks must record solver, graph/stops, graph version, deterministic seed, distance, ETA, computation time, candidates/routes evaluated, nodes expanded, pruning/improvement counts, and runtime context. Exclude browser rendering, network, tile loading, and charting from solver timing.

## 15. Operations, deployment, and scaling

### 15.1 Local Compose

The current Compose stack is a useful local profile, but before persistent mode is claimed it needs:

- PostgreSQL healthcheck;
- API startup migration strategy, or a separate one-shot migration command;
- `depends_on` health conditions;
- explicit volume/backup note for local data;
- a way to start memory mode without requiring a database;
- a safe `.env.example` that distinguishes browser-visible map config from backend secrets.

Validate resolved variables with `docker compose config`. Do not bake secrets into images. See the [Compose documentation](https://docs.docker.com/compose/), [environment variable guidance](https://docs.docker.com/compose/how-tos/environment-variables/), and [startup-order guidance](https://docs.docker.com/compose/how-tos/startup-order/).

### 15.2 CI and supply chain

The existing CI should evolve to include:

- patched Next.js dependency verification;
- backend and frontend lockfile consistency;
- migration/seed checks;
- Playwright E2E in a separate job when the browser flow exists;
- accessibility scan;
- dependency review on pull requests;
- Dependabot or an equivalent update policy;
- secret scanning and public-fixture safety checks;
- pinned or reviewed GitHub Actions versions and least-privilege `permissions`.

GitHub documents [dependency review](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/configure-dependency-review-action), [Dependabot security updates](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-security-updates), and [workflow permissions/security](https://docs.github.com/actions/security-for-github-actions). Dependency update automation reduces known-vulnerability drift but still needs a human review of breaking changes.

### 15.3 Observability

M1 should add a correlation ID to commands, responses, events, audit entries, and logs. It should expose basic counters/timers for command latency, failed transitions, route generation, tracking lag, and SSE connections without recording personal payloads.

Adopt OpenTelemetry only when there is a real collector/deployment target or when instrumentation itself is a portfolio objective. The [OpenTelemetry overview](https://opentelemetry.io/docs/), [Python guidance](https://opentelemetry.io/docs/languages/python/), and [JavaScript guidance](https://opentelemetry.io/docs/languages/js/) cover vendor-neutral traces, metrics, and logs.

### 15.4 Deployment shape

Keep deployment host-neutral until the app is functional:

- web: Next.js Node runtime or a compatible managed platform;
- API: containerized FastAPI service;
- database: managed PostgreSQL for any public persistent environment;
- map: restricted browser key and visible attribution;
- workers: separate process only when an outbox/queue exists;
- secrets: platform secret store or OIDC-based short-lived credentials;
- releases: migration plan, health/readiness checks, rollback path, backup verification, and environment-specific config.

GitHub Actions environments can hold protected deployment secrets and approvals; see [deployment environments](https://docs.github.com/actions/deployment/targeting-different-environments/using-environments-for-deployment). A public demo must not imply production availability or data protection that has not been measured and reviewed.

## 16. Dependency and prerequisite watchlist

| Item | Current observation | Action before relying on it |
| --- | --- | --- |
| Next.js | Manifest declares `^15.5.9`; lockfile resolves `15.5.24` | Raise the manifest floor to patched 15.5.24 or evaluate 16.3.3 separately |
| React/TypeScript | Existing React 19 and TypeScript 5.9 scaffold | Keep compatible with selected Next line; run build/typecheck after upgrades |
| Node | Repository uses Node 22 | Keep CI/local major aligned; re-check LTS schedule before deployment |
| FastAPI | Dependency range is broad (`>=0.115,<1`) | Pin/lock a tested release when adding SSE and production middleware |
| SQLAlchemy | Not yet in backend manifest | Add with psycopg and test sync session/UoW behavior |
| Alembic | Not yet in backend manifest | Add migration environment and review every generated revision |
| MapLibre | Not yet in frontend manifest | Add client adapter and fake-map tests; verify browser bundling |
| MapTiler | Provider selected conceptually, no runtime key needed by default | Use restricted browser key, attribution, quota, and unavailable fallback |
| Playwright | Not yet in the current test setup | Add separate E2E job after stable API/UI flow |
| PostgreSQL Compose | Service exists without readiness healthcheck | Add healthcheck and migration/startup contract |
| Real payments | Not selected/integrated | Evaluate providers and legal/operational obligations first |
| Real auth | Not selected/integrated | Decide managed OIDC provider and session model later |
| Road graph/OSM | Not bundled for M1 | Decide data source/license/update plan before import |

Version numbers and provider terms are observations at the research date, not permanent requirements.

## 17. Risk register

| Risk | Why it matters | Mitigation/trigger |
| --- | --- | --- |
| M1 becomes four disconnected mock screens | Product thesis is not proven | Every role command goes through shared application services; require one E2E journey |
| Memory/PostgreSQL behavior diverges | Demo and persistent mode become different products | Repository-contract tests and transaction tests in both modes |
| Event published before commit | UI shows state that rolled back | Publish only after commit; add outbox before multi-process deployment |
| Map provider outage/quota | Route flow becomes un-demoable | Local geometry remains authoritative; clear map fallback; restricted key |
| Next security drift | Public frontend becomes exposed to known issues | Patch minimum before feature implementation; automate dependency review |
| Realistic seed data leaks personal information | Public repo/privacy harm | Synthetic labels/coordinates, validator, secret scan, manual release review |
| Provider SDK leaks into domain | Future replacement becomes expensive | Ports/adapters and provider-neutral data models |
| Payment client claims success | Fraud/order inconsistency | Server/webhook authority, idempotency, safe provider adapter |
| Exact GPS history becomes personal data | LGPD and safety exposure | Generalized M1 coordinates, redacted logs, retention design before real data |
| Premature queues/services | Complexity hides product gaps | Add only after measured asynchronous or scale need |
| Unbounded list/API payloads | Poor performance and accidental data exposure | Pagination, bounded limits, role-scoped projections |
| Route solver claims real logistics optimization | Portfolio credibility suffers | Label pathfinding/optimization/dispatch separately and publish assumptions |

## 18. Decisions still required at implementation time

These are intentionally documented questions, not hidden assumptions:

1. Exact SQLAlchemy model/table names and whether status columns use text/check constraints or database enums.
2. Whether the in-memory transaction uses copy-on-write snapshots or command-level rollback objects.
3. Exact demo identity transport: development-only header versus signed local cookie.
4. Canonical error `type` URL namespace.
5. Exact graph format and synthetic coordinate policy.
6. MapTiler style URL and browser-key origin restrictions for local/preview deployment.
7. Whether the PostgreSQL adapter is included in the default CI job or an explicitly provisioned integration job.
8. Browser E2E hosting mode: start API/web processes directly or use Compose.
9. Real-auth provider and deployment platform, after M1 has a stable domain.
10. Brazilian payment provider and legal/merchant onboarding model, after simulated payment behavior is proven.
11. Road-network source, ODbL/data refresh obligations, and whether a self-hosted router is warranted.
12. Retention periods and privacy controls before any real identity, address, location, or payment data is accepted.

## 19. Documentation that must remain synchronized

When implementation begins, update these together:

- [M1 design spec](../superpowers/specs/2026-09-01-milestone-1-core-delivery-loop-design.md): user-visible scope and acceptance;
- [requirements traceability](../requirements/traceability.md): RF/RNF evidence and status;
- [system boundaries](../architecture/system-boundaries.md): ownership and provider rules;
- [routing contract](../architecture/routing-contract.md): RouteProblem/RouteResult extensions;
- [provider and integration boundaries](../architecture/provider-and-integration-boundaries.md): adapter contracts;
- [API and event contract](../architecture/api-and-events.md): endpoint, error, idempotency, and SSE shapes;
- [persistence and seeding guide](../architecture/persistence-and-seeding.md): repository parity, migrations, reset, and recovery;
- [platform evolution roadmap](../roadmap/platform-evolution.md): stage status and deferred work;
- [M1 development runbook](../runbooks/milestone-1-development.md): commands, modes, fixtures, and checks;
- ADRs 0003–0006: durable decisions and their consequences;
- README and public-demo runbook: user-facing setup and limitations.

If code and these documents disagree, stop and reconcile the contract before adding more features.

## 20. Source index

### Application and API

- [FastAPI SSE tutorial](https://fastapi.tiangolo.com/tutorial/server-sent-events/)
- [FastAPI SSE reference](https://fastapi.tiangolo.com/reference/sse/)
- [FastAPI security overview](https://fastapi.tiangolo.com/tutorial/security/)
- [OpenAPI 3.1.1 specification](https://spec.openapis.org/oas/v3.1.1.html)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/orm/)
- [SQLAlchemy sessions](https://docs.sqlalchemy.org/en/latest/orm/session_basics.html)
- [SQLAlchemy transactions](https://docs.sqlalchemy.org/en/latest/orm/session_transaction.html)
- [SQLAlchemy asyncio](https://docs.sqlalchemy.org/en/latest/orm/extensions/asyncio.html)
- [Alembic](https://alembic.sqlalchemy.org/)
- [Alembic autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [PostgreSQL indexes](https://www.postgresql.org/docs/current/sql-createindex.html)
- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)

### Frontend, maps, and browser behavior

- [Next.js Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components)
- [Next.js August 2026 security release](https://nextjs.org/blog/august-2026-security-release)
- [Next.js deployment guide](https://nextjs.org/docs/app/guides/deploying)
- [Node.js release schedule](https://nodejs.org/en/about/previous-releases)
- [MapLibre GL JS](https://www.maplibre.org/maplibre-gl-js/docs/)
- [MapLibre GeoJSON source](https://www.maplibre.org/maplibre-gl-js/docs/API/classes/GeoJSONSource/)
- [MapTiler MapLibre integration](https://docs.maptiler.com/maplibre/)
- [MapTiler API key security](https://docs.maptiler.com/cloud/api/authentication-key/)
- [MapTiler key protection](https://docs.maptiler.com/guides/maps-apis/maps-platform/how-to-protect-your-map-key)
- [MapTiler authentication](https://docs.maptiler.com/cloud/api/authentication/)
- [MapTiler attribution](https://docs.maptiler.com/guides/map-design/attribution/add-attribution/)
- [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [MDN Server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)

### Testing and security

- [Vitest guide](https://vitest.dev/guide/)
- [Playwright introduction](https://playwright.dev/docs/intro)
- [Playwright browser projects](https://playwright.dev/docs/browsers)
- [Playwright API testing](https://playwright.dev/docs/api-testing)
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)
- [GitHub dependency review](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/configure-dependency-review-action)
- [GitHub Dependabot security updates](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-security-updates)

### Payments, identity, privacy, and geodata

- [Stripe Payment Intents](https://docs.stripe.com/payments/payment-intents)
- [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests)
- [Stripe webhooks](https://docs.stripe.com/webhooks)
- [Mercado Pago PIX](https://www.mercadopago.com.br/developers/pt/docs/checkout-bricks/payment-brick/payment-submission/pix)
- [Mercado Pago notifications](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/notifications)
- [RFC 7636: Proof Key for Code Exchange](https://www.rfc-editor.org/rfc/rfc7636)
- [RFC 9700 OAuth security BCP](https://datatracker.ietf.org/doc/html/rfc9700)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
- [LGPD compiled text](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/L13709compilado.htm)
- [ANPD data-subject rights](https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados-1/direito-dos-titulares)
- [ANPD RIPD guidance](https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/relatorio-de-impacto-a-protecao-de-dados-pessoais-ripd)
- [PostGIS database management](https://postgis.net/docs/using_postgis_dbmanagement.html)
- [PostGIS spatial queries](https://postgis.net/docs/using_postgis_query.html)
- [OSM Foundation attribution guidelines](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines)
- [OSRM HTTP API](https://project-osrm.org/docs/v26.4.0/http)

### Operations and asynchronous work

- [Docker Compose](https://docs.docker.com/compose/)
- [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/)
- [Compose environment variables](https://docs.docker.com/compose/how-tos/environment-variables/)
- [OpenTelemetry](https://opentelemetry.io/docs/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [OpenTelemetry JavaScript](https://opentelemetry.io/docs/languages/js/)
- [Redis Streams](https://redis.io/docs/latest/develop/data-types/streams/)
- [Celery tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html)
- [GitHub Actions security](https://docs.github.com/actions/security-for-github-actions)
- [GitHub deployment environments](https://docs.github.com/actions/deployment/targeting-different-environments/using-environments-for-deployment)
