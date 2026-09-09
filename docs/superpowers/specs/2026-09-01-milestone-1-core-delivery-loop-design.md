# Milestone 1: Core Delivery Loop

## Design Specification

**Status:** Draft for user review  
**Date:** 2026-09-01  
**Product:** Entrega Clara  
**Build strategy:** Vertical slice first  
**Parent specification:** [Entrega Clara seed design](2026-08-29-food-delivery-platform-seed-design.md)
**Research basis:** [Platform build research](../../research/2026-09-01-platform-build-research.md)
**Future sequence:** [Platform evolution roadmap](../../roadmap/platform-evolution.md)

## 1. Decision summary

Milestone 1 turns the current scaffold into a complete, demonstrable order-to-delivery loop:

customer discovery → checkout → restaurant preparation → courier assignment → route generation → live tracking → delivery

The milestone is intentionally one complete operational slice, not the entire platform. It supports dynamically created orders and preserves the deterministic lunch-rush scenario for presentations, testing, reset, and replay.

The application uses a hybrid persistence design:

- In-memory persistence is the default for demos, tests, and offline development.
- PostgreSQL is an opt-in persistent runtime selected through configuration.
- Both implementations satisfy the same repository and transaction contracts.
- Only one persistence implementation is active in a process; there is no dual write.

Our local routing solver owns route calculation. MapLibre GL with MapTiler renders the resulting route on a real map. Provider-calculated directions and ETA comparison are explicitly deferred.

## 2. Goal and definition of done

Milestone 1 is complete when a seeded demo customer identity can perform the following journey with either the deterministic lunch-rush order or a dynamically created order:

1. Search and filter a focused set of Brazilian restaurants.
2. Open a restaurant and browse its menu.
3. Add menu items, quantities, and observations to a cart.
4. Select a seeded delivery address.
5. Apply a valid or invalid coupon.
6. Select a simulated PIX, card, or wallet payment method.
7. Complete an approved checkout or receive a safe declined-payment result.
8. Watch the resulting order move from placed to confirmed, preparing, ready for pickup, courier assigned, picked up, en route, and delivered.
9. See the restaurant, courier, and operations surfaces observe the same order.
10. See the courier route and location updates on the real map when MapTiler is configured.
11. Receive order and tracking updates through SSE.
12. Reset and replay the lunch-rush scenario through the same commands used by interactive role actions.

The journey must work with the in-memory repository and with the PostgreSQL repository. The deterministic scenario must remain reproducible, while a scenario reset must not delete unrelated dynamically created orders.

## 3. Scope

### 3.1 Included

- Focused catalog with multiple restaurants, cuisines, menu items, prices, availability states, and seeded Brazilian addresses.
- Customer discovery, restaurant details, menu browsing, cart management, coupon application, checkout, order detail, and order history.
- Simulated payment gateway with approved and declined outcomes.
- Restaurant queue with confirmation, preparation, and ready-for-pickup commands.
- One-to-one delivery assignment between one order and one courier.
- Courier availability, offer acceptance, pickup, en-route, location, and completion commands.
- Deterministic local shortest-path routing for courier-to-restaurant and restaurant-to-customer legs.
- MapLibre GL and MapTiler map rendering with backend-provided route geometry.
- Deterministic GPS simulation with manual commands and Demo Mode fast-forward.
- Server-Sent Events for order state, courier location, ETA, and notification updates.
- In-app notifications and append-only audit events.
- Read-only Operations surface with order state, courier state, route metrics, events, audit history, and demo controls.
- Seeded demo identities with role switching and API-enforced permissions.
- In-memory and PostgreSQL repository implementations behind common interfaces.
- Unit, repository-contract, integration, frontend, security, accessibility, and end-to-end tests.
- Public-safe documentation, synthetic seed data, and extension guidance for future developers.

### 3.2 Explicitly deferred

- Post-delivery reviews and ratings.
- More than one active delivery in the operational flow.
- Concurrent-delivery dispatch and simple multi-courier assignment.
- Multi-stop routing, batching, capacity, time windows, and dispatch optimization.
- Provider directions, provider ETA, and solver-versus-provider comparison.
- Full algorithm laboratory and benchmark UI.
- Real authentication and external identity providers.
- Real payment processing, settlement, or card data.
- Free-form address entry, production geocoding, and address validation.
- Push notifications, SMS, email, and external messaging providers.
- Full Admin mutations for users, coupons, roles, support, and operations.
- Support chat and conversation management.
- Large marketplace breadth, restaurant self-service, and advanced menu management.
- Dynamic rerouting after a courier deviates from the planned path.
- Native mobile applications.

The foundation-first and demo-first build strategies remain documented alternatives, but they are not the implementation strategy for this milestone.

## 4. Approved design decisions

| Decision | Choice | Reason |
| --- | --- | --- |
| Build shape | Vertical slice first | Produces a working product at every stage and limits speculative infrastructure |
| Persistence | Hybrid | Demonstrates real persistence without sacrificing deterministic offline demos |
| Default backend | In-memory | Keeps demos, tests, and replay reliable |
| Persistent backend | PostgreSQL | Proves a credible application data path and survives process restarts |
| Identity | Seeded demo identities with role switching | Proves authorization without introducing a separate authentication project |
| Dynamic data | Dynamic orders plus deterministic lunch-rush scenario | Makes checkout real while preserving a repeatable portfolio presentation |
| Workflow control | Interactive commands plus Demo Mode | Both paths exercise one application-command pipeline |
| Map | MapLibre GL and MapTiler | Real map presentation with a replaceable provider boundary |
| Route ownership | Local solver | Keeps the portfolio thesis centered on explainable routing work |
| Live route | Single delivery with two ordered legs | Delivers the operational value without introducing dispatch optimization |
| Realtime transport | SSE | Fits one-way order and tracking updates with lower complexity than WebSockets |
| Operational surface | Read-only Operations view | Makes shared state and auditability visible without expanding into admin management |
| Rating boundary | End at delivered | Keeps post-delivery trust features available as a clean next milestone |

## 5. Architecture

Entrega Clara remains a modular monolith under app/backend/src, with the existing web application under app/web.

### 5.1 Boundaries

- Web owns screens, form state, typed API calls, SSE consumption, and map rendering.
- API owns HTTP validation, identity resolution, authorization invocation, response serialization, and SSE connection management.
- Application services own use cases and transaction orchestration.
- Domain owns entities, value objects, state transitions, business rules, and provider-neutral contracts.
- Repository ports own persistence abstractions and transaction boundaries.
- Adapter implementations own in-memory state, PostgreSQL access, simulated payment, event publication, and configuration.
- Simulation owns deterministic clocks, scenario commands, and reproducible location progression.
- Routing owns graph inputs, shortest-path solving, route results, and route metrics.
- MapLibre/MapTiler remains a frontend adapter. The backend never imports a map-provider SDK.

The frontend may depend on a single map-renderer adapter that wraps MapLibre. Customer, restaurant, courier, and operations components must not call MapTiler directly.

### 5.2 Composition

At application startup, configuration selects the active persistence mode and constructs the application services with repository, payment, routing, event, clock, and identifier ports. Domain code receives ports rather than concrete adapters.

The default local configuration is:

- persistence mode: memory
- demo mode: enabled
- market: Brazil
- payment gateway: simulated
- route solver: local deterministic shortest path
- event publisher: in-process
- map provider: MapTiler when a browser token is configured

The PostgreSQL mode uses the same services and contracts. It changes composition, not business behavior.

### 5.3 Transaction and event rule

Every state-changing command runs inside one unit of work:

1. Resolve the demo identity.
2. Check authorization and operational scope.
3. Load the required aggregates.
4. Validate the command against current state.
5. Apply domain changes.
6. Record audit and notification records.
7. Persist all changes atomically.
8. Commit.
9. Publish post-commit events to the in-process event hub and SSE subscribers.

If validation or persistence fails, the whole command is rolled back and no success event is published. SSE is a projection channel, not the source of truth. A reconnecting client refetches the current snapshot.

## 6. Domain model

### 6.1 Milestone entities

| Entity | Milestone responsibility | Future extension |
| --- | --- | --- |
| DemoIdentity | Seeded user, role, ownership, and operational scope | Real sessions and external identity |
| Restaurant | Discoverable partner and operating status | Self-service operations |
| MenuItem | Price, category, description, and availability | Variants, modifiers, images, inventory |
| Address | Seeded delivery destination and market-aware formatting | Free-form address and geocoding |
| Cart / CartItem | Mutable customer selection before checkout | Saved carts and cross-device sync |
| Coupon | Code, validity, minimum subtotal, and fixed discount | Percentage, stacking, campaigns |
| Order / OrderItem | Purchase snapshot, totals, customer, restaurant, and lifecycle | Refunds, cancellations, substitutions |
| PaymentAttempt | Method, safe reference, status, and failure reason | External providers and settlement |
| CourierProfile | Availability, status, current position, and identity | Capacity, earnings, verification |
| Delivery | Assignment, pickup/drop-off, route, and delivery state | Batching and multi-courier dispatch |
| RoutePlan / RouteStop | Solver output and ordered pickup/drop-off legs | Time windows and optimization |
| TrackingEvent | Courier position, sequence, and timestamp | Device telemetry and historical playback |
| Notification | User-facing lifecycle event and read state | Push, email, and SMS delivery |
| AuditEvent | Append-only actor, action, target, and state history | Compliance exports and retention policies |

### 6.2 Invariants

- Money is stored as integer minor units with an explicit currency.
- All timestamps are stored canonically and localized only at the presentation boundary.
- IDs are stable opaque values; deterministic fixtures use stable synthetic IDs.
- Cart lines can change before checkout.
- Order items snapshot menu names and prices at checkout and are immutable afterward.
- A delivery belongs to exactly one order. Its courier is empty until assignment and exactly one courier after assignment in Milestone 1.
- A courier cannot accept a second active delivery.
- A route always visits the restaurant before the customer.
- Payment references never contain raw card numbers, security codes, or provider payloads.
- Every successful lifecycle mutation produces an audit event and relevant notification.
- A scenario reset is scoped to the selected scenario and does not erase unrelated dynamic data.
- A stale location sequence cannot overwrite a newer location.

### 6.3 Order lifecycle

The existing state model remains the shared lifecycle:

placed → confirmed → preparing → ready_for_pickup → courier_assigned → picked_up → en_route → delivered

The existing rated and cancelled states remain in the domain model. Ratings are deferred, and cancellation is limited to the already-defined valid transitions until a dedicated cancellation design is approved.

Order transitions and delivery changes are committed together. For example, assigning a courier creates or updates the delivery, changes the order to courier_assigned, records the actor and timestamp, and emits the assignment notification as one transaction.

## 7. Application commands and API

### 7.1 Commands

All commands carry an identity context, correlation ID, and command ID. Checkout additionally requires an idempotency key.

Customer commands:

- AddCartItem
- UpdateCartItem
- RemoveCartItem
- ApplyCoupon
- RemoveCoupon
- CheckoutOrder

Restaurant commands:

- ConfirmOrder
- StartPreparation
- MarkReadyForPickup

Courier commands:

- SetCourierAvailability
- AcceptDelivery
- ConfirmPickup
- StartDelivery
- UpdateCourierLocation
- CompleteDelivery

Demo commands:

- ResetScenario
- AdvanceScenario
- AdvanceClock

No generic update-order-state command is exposed. Each role gets only the domain command appropriate to its responsibility.

### 7.2 Read APIs

The versioned REST surface uses /api/v1 and JSON:

- GET /restaurants
- GET /restaurants/{restaurant_id}
- GET /restaurants/{restaurant_id}/menu
- GET /me/cart
- GET /me/addresses
- GET /me/orders
- GET /orders/{order_id}
- GET /orders/{order_id}/tracking
- GET /orders/{order_id}/notifications
- GET /restaurant/orders
- GET /courier/deliveries/offers
- GET /courier/deliveries/active
- GET /operations/orders/{order_id}
- GET /operations/events
- GET /operations/metrics

### 7.3 State-changing APIs

- POST /me/cart/items
- PATCH /me/cart/items/{line_id}
- DELETE /me/cart/items/{line_id}
- POST /me/cart/coupon
- DELETE /me/cart/coupon
- POST /me/orders/checkout
- POST /restaurant/orders/{order_id}/confirm
- POST /restaurant/orders/{order_id}/prepare
- POST /restaurant/orders/{order_id}/ready
- PUT /courier/availability
- POST /courier/deliveries/{delivery_id}/accept
- POST /courier/deliveries/{delivery_id}/pickup
- POST /courier/deliveries/{delivery_id}/start
- POST /courier/deliveries/{delivery_id}/location
- POST /courier/deliveries/{delivery_id}/complete

Existing demo endpoints remain available:

- GET /demo/scenario
- POST /demo/reset
- POST /demo/advance
- POST /demo/clock

### 7.4 Identity and authorization

The role switcher selects one of the server-known demo identities. The API derives role, ownership, and operational scope from that identity. A client-supplied role string cannot grant access.

Examples:

- A customer may read and mutate only their own cart, addresses, and orders.
- A restaurant operator may act only on orders for their restaurant.
- A courier may act only on their own availability, offers, active delivery, and location.
- Operations may read all M1 operational records but may not mutate them.

## 8. Realtime and event contract

The event envelope contains:

- event ID
- event type
- aggregate type and ID
- actor identity and role
- correlation ID
- event sequence
- UTC timestamp
- payload version
- domain payload

M1 event types include:

- order.placed
- payment.approved
- payment.declined
- order.confirmed
- order.preparing
- order.ready
- delivery.assigned
- delivery.picked_up
- delivery.en_route
- courier.location_updated
- delivery.delivered
- notification.created
- audit.recorded
- tracking.delayed

The authorized SSE endpoint is GET /orders/{order_id}/stream. On connection, it sends the current order/tracking snapshot followed by new events. Reconnection begins with a fresh snapshot; clients do not assume that an event stream is complete or durable.

The simulator and interactive role surfaces publish through the same event publisher. Notifications are derived from lifecycle events and are not handcrafted separately by each screen.

## 9. Hybrid persistence

### 9.1 Repository ports

The application layer depends on focused repositories and a unit-of-work port for:

- identities
- restaurants and menu items
- addresses
- carts
- coupons
- orders and order items
- payment attempts
- courier profiles
- deliveries
- route plans and stops
- tracking events
- notifications
- audit events
- domain/event log records

The exact storage technology is hidden behind these ports.

### 9.2 In-memory implementation

The in-memory implementation is the default. It supports:

- fast isolated tests
- deterministic demo playback
- dynamic order creation for the active process
- transaction snapshots and rollback
- scenario-scoped reset
- an in-process event hub

It is not presented as durable storage. Restarting the API discards in-memory dynamic records.

### 9.3 PostgreSQL implementation

The PostgreSQL implementation uses SQLAlchemy and Alembic. M1 migrations cover the entities needed for the core loop and include indexes for customer order history, restaurant queues, courier active delivery, and order event lookup.

PostgreSQL transactions persist order, payment, delivery, audit, notification, and event-log changes together. The local event publisher may remain in-process in M1; a durable outbox/queue worker is documented as the future scaling path.

The runtime setting PERSISTENCE_MODE accepts memory or postgres and defaults to memory. The application fails clearly if postgres is selected without a usable connection.

### 9.4 Seed and reset

Static catalog and identity data is loaded idempotently. The lunch-rush scenario is identified by scenario ID and reset inside a transaction. Resetting it restores its initial order, courier, tracking, notifications, audit fixtures, and route state without truncating unrelated orders.

All public fixtures remain synthetic and must pass the repository’s seed-safety checks.

## 10. Routing, map, and simulation

### 10.1 Live M1 route

The live delivery uses A* with an admissible coordinate heuristic over a versioned seeded graph. A small Dijkstra implementation is required as a test oracle for route correctness and is not exposed as the live solver.

The route problem contains:

- current courier origin
- restaurant pickup stop
- customer drop-off stop
- graph reference and version
- travel-cost assumptions

The result contains:

- ordered stops
- one segment to the restaurant
- one segment to the customer
- route geometry
- distance
- estimated travel time
- solver name and version
- computation time
- nodes expanded and warnings

Route generation happens when the courier accepts the assignment. M1 does not dynamically reroute after deviation.

The existing brute-force TSP remains the legacy baseline for bounded experiments and future laboratory work. It is not used for the live two-leg delivery.

### 10.2 Map adapter

The frontend map adapter uses MapLibre GL and MapTiler tiles/styles. The backend returns route geometry independently of the provider. The seeded graph is safely generalized but geographically aligned with the selected map viewport so the route overlay is visually coherent without requiring provider directions. The provider token is supplied through a browser-safe environment setting, with attribution rendered on the map surface.

Without a configured MapTiler token or when the provider is unavailable:

- checkout and order progression continue;
- tracking timeline and last-known location remain visible;
- the map area shows a clear unavailable state;
- no provider error payload is exposed to the user.

Tests use a fake map adapter and never require MapTiler network access.

### 10.3 Deterministic simulator

The simulator uses:

- a seeded clock
- stable route geometry
- monotonic location sequences
- deterministic event durations
- resettable scenario state

Manual role commands and Demo Mode fast-forward call the same application services. The simulator never mutates repository records directly and never consults wall-clock time for scenario outcomes.

## 11. User experience

### Customer

The customer surface is mobile-first and includes:

- marketplace search and filters
- restaurant detail and menu
- cart and checkout
- approved/declined payment states
- order confirmation
- active-order tracking
- order history
- notification list

The active-order view shows state timeline, courier marker, route line, ETA, last update, SSE connection state, and map fallback behavior.

### Restaurant

The restaurant surface includes:

- incoming order queue
- order detail
- confirm action
- start-preparation action
- ready-for-pickup action
- safe empty, loading, and failure states

### Courier

The courier surface includes:

- availability toggle
- delivery offer
- assignment detail
- route to restaurant and customer
- pickup, start, location, and completion actions
- current location and delivery timeline

### Operations

The read-only Operations surface includes:

- active order and lifecycle state
- restaurant and courier state
- route distance, ETA, solver, and computation metrics
- audit history
- event stream
- deterministic demo controls

All role surfaces use Portuguese/Brazilian copy initially, semantic controls, visible focus, keyboard operation, screen-reader names, responsive layouts, reduced-motion behavior, and explicit loading/error/empty states.

## 12. Error, security, and privacy contract

The API returns a stable error envelope containing:

- machine-readable code
- localized user-facing message
- request ID
- safe structured details

Representative codes include:

- item_unavailable
- restaurant_unavailable
- cart_empty
- coupon_invalid
- coupon_expired
- payment_declined
- invalid_transition
- role_forbidden
- ownership_forbidden
- courier_unavailable
- route_unavailable
- tracking_delayed
- map_provider_unavailable

Expected HTTP meanings are 400 for malformed commands, 401 for a missing or invalid demo identity, 403 for an authenticated identity without permission, 404 for missing resources, 409 for state conflicts, 422 for schema validation, and 503 for unavailable optional infrastructure.

M1 security requirements:

- API authorization is enforced independently of frontend visibility.
- Simulated payments store only method, outcome, and safe reference.
- Logs and audit metadata redact secret-like and payment-like values.
- Demo data contains no real personal data, precise real courier traces, private source links, or production credentials.
- MapTiler browser configuration is documented as public configuration, not a server secret.
- User-facing errors never contain stack traces, database errors, provider payloads, or internal implementation details.

## 13. Quality strategy

### Required automated evidence

- Domain tests for totals, coupons, payment outcomes, permissions, state transitions, delivery invariants, and route results.
- Repository contract tests executed against memory and PostgreSQL implementations.
- Integration tests for checkout, transaction rollback, restaurant commands, courier commands, route creation, SSE authorization, event ordering, and scenario reset isolation.
- Browser end-to-end coverage for the complete customer-to-delivery journey.
- Frontend tests for loading, errors, role controls, SSE updates, map fallback, responsive behavior, and accessibility semantics.
- Security tests for forbidden actions, ownership boundaries, redaction, synthetic seed safety, and safe errors.
- Deterministic replay tests proving that interactive and Demo Mode execution produce equivalent final state.

### Required acceptance checks

- In-memory mode runs the complete journey without a database.
- PostgreSQL mode runs the same journey with persistent records.
- A successful checkout creates exactly one order for one idempotency key.
- A declined payment does not create a deliverable order.
- Invalid coupons do not alter cart totals.
- Invalid transitions do not mutate order, delivery, audit, notification, or event state.
- A courier cannot accept a second active delivery.
- Courier location sequences are monotonic.
- SSE reconnect returns a current snapshot before subsequent events.
- Map provider failure does not block order progression.
- Reset restores the lunch-rush scenario and preserves unrelated dynamic orders.
- The public release contains only synthetic fixtures and safe documentation.

The repository quality gate must continue to cover seed validation, requirement traceability, application-boundary checks, linting, type checking, backend tests, frontend tests, and production build validation. Docker availability is recorded separately from code-level test results.

## 14. Milestone 1 requirement coverage

| Requirement | M1 status | Evidence |
| --- | --- | --- |
| RF01 Restaurant and dish search | Included | Customer catalog search, filters, restaurant details, and menu tests |
| RF02 Order placement | Included | Cart, coupon, checkout, payment outcome, order creation, and E2E journey |
| RF03 Real-time tracking | Included | Route overlay, courier marker, timeline, ETA, SSE, and reconnect tests |
| RF04 Feedback and ratings | Deferred | Delivered state and event boundary retained for the next milestone |
| RF05 Payment processing | Simulated | Payment port, approved/declined gateway, safe references, and transaction tests |
| RF06 Restaurant panel | M1 core subset | Order queue and preparation actions; menu administration deferred |
| RF07 User profile | M1 core subset | Seeded identity, addresses, order history, and ownership checks |
| RF08 Courier panel | M1 core subset | Availability, assignment, route, pickup, tracking, and completion |
| RF09 Notifications | Included | In-app notifications, event-derived messages, and SSE delivery |
| RF10 Coupon management | M1 customer subset | Validation and checkout calculation; admin management deferred |
| RF11 Support and chat | Deferred | Notification/event boundaries documented for later |
| RF12 Data security | Included for demo boundary | API authorization, redaction, synthetic data, safe payment references, and errors |
| RF13 Audit logs | Included | Append-only lifecycle and operational audit records |
| RF14 Access control | Included for demo identity boundary | Server-known identities, role checks, ownership, and forbidden-action tests |
| RNF01 Availability | Demonstrated locally | Health checks, graceful optional-provider degradation, reset, and documented non-production target |
| RNF02 Transactional consistency | Included | Unit-of-work rollback and atomic order/payment/delivery/audit/notification tests |
| RNF03 Tracking performance | Demonstrated locally | Deterministic location updates, sequence ordering, SSE lag/state indicators |
| RNF04 Peak scalability | Boundary only | Repository, event, and provider ports; multi-delivery workload deferred |
| RNF05 Usability | Included | Short checkout, state-aware controls, localized copy, and explicit UI states |
| RNF06 Mobile compatibility | Included | Responsive mobile-first web surfaces and viewport checks |
| RNF07 Accessibility | Included | Semantic controls, keyboard/focus behavior, labels, contrast, and reduced motion |
| RNF08 LGPD-aware behavior | Demo boundary | Data minimization, synthetic fixtures, redaction, and privacy-safe documentation |
| RNF09 Backup and recovery | Demo boundary | Seed snapshots, deterministic reset/replay, and PostgreSQL recovery runbook |
| RNF10 Friendly errors | Included | Stable error codes, localized messages, request IDs, and safe details |

## 15. Documentation deliverables

The implementation must update or add the following documentation:

- This milestone specification.
- A hybrid-persistence ADR covering repository parity, default mode, transactions, and reset isolation.
- A map-and-routing ADR covering MapLibre/MapTiler rendering, local route ownership, fallback behavior, and deferred provider directions.
- An SSE-and-demo-command ADR covering post-commit events, reconnection, deterministic simulation, and the shared command pipeline.
- An M1 architecture document showing module boundaries, composition, data flow, and dependency rules.
- An API and event reference with endpoint tables, command payloads, response schemas, error codes, identity rules, and SSE event examples.
- A persistence guide covering environment selection, migrations, seed loading, reset semantics, and memory/PostgreSQL differences.
- A demo runbook covering interactive role flow, fast-forward, reset, replay, MapTiler configuration, and known limitations.
- A contributor extension guide explaining how to add a repository, payment provider, map provider, route solver, market configuration, role command, and event consumer.
- Updated RF/RNF traceability mapping each requirement to code modules, screens, endpoints, and tests.
- A deferred roadmap with the rationale and enabling contracts for ratings, concurrent deliveries, multi-stop routing, provider comparison, real authentication, support, and full administration.

Documentation must remain public-safe: no private source URLs, credentials, real personal data, or claims of production certification.

## 16. Implementation slices

The later implementation plan will preserve the vertical-slice strategy:

1. Shared contracts, identity context, domain entities, repository ports, and transaction boundary.
2. Catalog, cart, coupons, simulated payment, checkout, and customer order views.
3. Restaurant queue and preparation commands.
4. Courier availability, assignment, pickup, and completion commands.
5. Local route solver, MapLibre/MapTiler adapter, deterministic GPS simulation, and SSE.
6. Operations read model, audit/notification projections, Demo Mode integration, and full end-to-end flow.
7. PostgreSQL adapter, migrations, repository parity, release documentation, and final quality gates.

Each slice must leave the application runnable, tested, documented, and compatible with the contracts established by earlier slices.

## 17. Deferred roadmap

| Future capability | Why deferred | M1 contract that enables it |
| --- | --- | --- |
| Reviews and ratings | Post-delivery trust flow is separate from delivery execution | Delivered order, identity, and notification events |
| Concurrent deliveries | Requires dispatch policy and courier capacity | Delivery aggregate and courier availability boundary |
| Multi-stop optimization | Requires richer constraints and benchmarks | RouteProblem, RouteResult, and ordered stops |
| Provider route comparison | Adds external route cost and attribution concerns | Solver-independent routing contract |
| Real authentication | Separate identity/security subsystem | Demo identity and API authorization ports |
| Full administration | Adds mutation and governance workflows | Operations read models and audit events |
| Support chat | Separate conversation and messaging lifecycle | Notification and event contracts |
| Real payments | External credentials, webhooks, and financial risk | PaymentGateway interface and safe payment records |
| Free-form addresses | Requires geocoding and validation providers | Address and map adapter boundaries |
| Push notifications | Requires external transport and delivery guarantees | Notification entity and transport port |

## 18. Review status

The scope, build strategy, persistence choice, identity approach, map choice, routing ownership, concurrency boundary, rating boundary, SSE choice, operations surface, and documentation requirements were approved in conversation on 2026-09-01. This written specification remains subject to user review before the implementation plan is created.
