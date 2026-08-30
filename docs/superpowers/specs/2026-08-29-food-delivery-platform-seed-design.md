# Entrega Clara

## Seed Design Document

**Status:** Portfolio foundation
**Date:** 2026-08-29
**Source:** College requirements exercise, summarized into this public seed document.

## 1. Executive Summary

Entrega Clara is a full-scale food-delivery application designed as a portfolio piece.

The original university requirements document is the product seed. It defines the customer, restaurant, courier, security, performance, and operational concerns that the application must represent.

The route-optimization exercise is a technical subsystem inside that product. It begins as an intentionally naive legacy implementation and is progressively superseded by more practical routing strategies. The application gives the algorithms a real product context: a courier needs to reach restaurants and customers, the platform needs to assign deliveries, and customers need accurate status and location updates.

The portfolio piece should feel like a coherent product rather than a collection of unrelated screens:

1. A customer places an order.
2. A restaurant accepts and prepares it.
3. The platform assigns a courier.
4. The routing engine generates a delivery plan.
5. The courier follows the plan.
6. The customer tracks the delivery.
7. The system records notifications, ratings, and audit history.

The application will be Brazil-first but internationally extensible. Brazil supplies the initial identity, language, payment methods, and seeded geography. Market-specific behavior will be configuration-driven rather than hard-coded.

## 2. Portfolio Thesis

The project demonstrates the complete engineering path from requirements to product:

> I started with a real delivery-app requirements specification, built the product surfaces around its actors and constraints, identified delivery routing as a difficult subsystem, measured the failure mode of a brute-force academic implementation, and replaced it with more scalable, explainable approaches.

The strongest portfolio evidence is not the existence of a map. It is the connection between:

- explicit requirements;
- domain modeling;
- responsive and accessible user experiences;
- simulated but coherent operational workflows;
- measurable algorithmic trade-offs;
- security and privacy boundaries;
- tests and observability;
- a documented evolution from legacy code to replacement architecture.

## 3. Product Positioning

### 3.1 Product identity

The application is a fictional delivery marketplace with:

- a customer-facing ordering experience;
- restaurant operations;
- courier operations;
- platform administration;
- support, notifications, payments, and audit history;
- an embedded delivery-intelligence layer.

The working product is not presented as a real commercial service. It is a production-shaped portfolio system with a deterministic demo environment.

### 3.2 Brazil-first, internationally extensible

Brazil is the default market:

- default locale: Portuguese (Brazil);
- default currency: BRL;
- default payment options: PIX, credit card, debit card, and digital wallets;
- default seed geography: Brazilian urban neighborhoods;
- default privacy framing: LGPD-aware;
- default examples: local restaurant and delivery scenarios.

The application must not assume that every market uses those values. A market configuration controls:

| Concern | Brazil default | International design |
|---|---|---|
| Locale | pt-BR | Locale selection |
| Currency | BRL | ISO currency configuration |
| Payment methods | PIX, cards, wallets | Market-supported methods |
| Address format | Brazilian address fields | Country-specific address schema |
| Time zone | America/Sao_Paulo | Per-market or per-address time zone |
| Legal/privacy copy | LGPD-oriented | Market policy adapter |
| Map seed | Brazilian city scenario | Replaceable region dataset |
| Notifications | Portuguese | Translation catalog |

Money is stored as integer minor units with an explicit currency. Dates and times are stored in a canonical format and rendered in the active market time zone. Country-specific behavior belongs behind adapters or configuration objects.

## 4. Goals and Boundaries

### 4.1 Goals

- Deliver a polished, navigable, responsive application.
- Represent every functional requirement from the source document.
- Make the main customer-to-delivery journey executable in demo mode.
- Give every required role a credible interface.
- Make the route engine a visible, measurable part of the product.
- Preserve the brute-force solution as a documented legacy baseline.
- Show the algorithmic replacement inside the courier and operations experiences.
- Demonstrate the non-functional requirements through instrumentation, tests, and architecture evidence.
- Keep all external integrations replaceable so the demo remains reliable.

### 4.2 Explicit boundaries

This is not a production payment platform, logistics company, or identity provider.

The initial portfolio release will use:

- seeded users and data;
- a demo authentication layer with role switching;
- a simulated payment gateway;
- a deterministic order and GPS simulator;
- a local or seeded route graph;
- mockable notification and chat transports;
- a lightweight database configuration suitable for local development and deployment.

The demo must behave like a complete system without claiming that it has production-grade banking, GPS, uptime, or regulatory certification.

The application will not initially require:

- real card processing;
- real customer funds;
- real driver identity verification;
- a native mobile binary;
- a large-scale production database cluster;
- a live support operation;
- a full marketplace settlement system.

## 5. Users and Roles

### Customer

The customer searches for food, selects a restaurant and items, checks out, follows the delivery, receives notifications, contacts support, and rates the restaurant and courier.

### Restaurant

The restaurant manages its menu, controls item availability, receives orders, progresses preparation states, and reviews operational history.

### Courier

The courier controls availability, receives delivery assignments, sees the route to the restaurant and customer, updates delivery states, and shares simulated location updates.

### Admin

The admin investigates platform activity, reviews audit logs, observes delivery operations, manages roles and access, and inspects system-level metrics.

Support conversations are represented within the platform and can be handled by an administrative or support-facing interface without creating a fifth required role.

## 6. Primary Demo Story

The portfolio presentation is anchored by a single continuous scenario called the lunch-rush delivery:

1. The customer opens the marketplace and filters nearby restaurants.
2. The customer opens a restaurant, selects items, adds an observation, applies a coupon, and checks out using PIX.
3. The restaurant dashboard receives the order and advances it from confirmed to preparing.
4. The courier dashboard receives an availability-compatible assignment.
5. The route engine calculates the courier’s trip to the restaurant and then to the customer.
6. The courier marks the order as picked up.
7. The simulator advances the courier’s position while the customer watches the map and status timeline.
8. The customer receives notifications as the delivery progresses.
9. The courier completes the delivery.
10. The customer rates both the restaurant and courier.
11. The admin view exposes the order’s audit trail and delivery metrics.

The scenario can be paused, advanced step by step, reset, or replayed. A second multi-order scenario demonstrates why route optimization matters beyond a single shortest path.

## 7. Product Surfaces

### Customer experience

- Home and restaurant discovery
- Search and filters
- Restaurant details and menu
- Item customization and observations
- Cart
- Checkout
- Payment selection
- Coupon validation
- Order confirmation
- Active-order tracking
- Order history
- Saved addresses
- Payment preferences
- Notifications
- Support chat
- Ratings and reviews
- Privacy and account controls

### Restaurant experience

- Restaurant overview
- Incoming order queue
- Order detail and state transitions
- Menu management
- Price editing
- Image management
- Item availability
- Operating status
- Order history
- Basic performance summary

### Courier experience

- Availability toggle
- Delivery offer queue
- Assignment detail
- Route to restaurant
- Pickup confirmation
- Route to customer
- Delivery status controls
- Simulated GPS movement
- Active delivery timeline
- Completed-delivery history
- Earnings or distance summary in demo form

### Admin and operations experience

- Platform overview
- Live delivery board
- Order lookup
- Courier and restaurant status
- Route and ETA metrics
- Audit log
- User and role inspection
- Coupon management
- Notification inspection
- Support conversation queue
- Demo scenario controls

### Algorithm laboratory

- Legacy brute-force solver
- Replacement solver
- Shortest-path comparison
- Route distance and estimated travel time
- Execution time
- Routes evaluated
- Branches or candidates pruned where applicable
- Route history for small instances
- Benchmark charts
- Scenario size controls
- Explanation of why pathfinding and route optimization are different problems

## 8. Requirement Traceability

### 8.1 Functional requirements

| ID | Source requirement | Product implementation | Demonstration evidence |
|---|---|---|---|
| RF01 | Pesquisa de Restaurantes e Pratos | Marketplace search by restaurant, cuisine, dish, price, rating, and delivery time | Customer searches, filters, and opens a result |
| RF02 | Realização de Pedidos | Cart, item observations, address selection, checkout, coupon, payment, and confirmation | Complete order flow |
| RF03 | Acompanhamento em Tempo Real | Order-state timeline, courier marker, ETA, last-update timestamp, and live delivery map | Customer tracks the lunch-rush order |
| RF04 | Feedback e Avaliação | Separate restaurant and courier ratings with comments | Post-delivery rating flow |
| RF05 | Processamento de Pagamentos | Payment adapter with PIX, credit, debit, and wallet demo methods | Successful and declined simulated payments |
| RF06 | Painel para Restaurantes | Menu, prices, images, availability, order queue, and preparation states | Restaurant accepts and prepares an order |
| RF07 | Perfil do Usuário | History, saved addresses, preferred payment methods, and account settings | Customer profile and history screens |
| RF08 | Painel do Entregador | Availability, assignment notifications, route to restaurant, route to customer, and delivery controls | Courier completes the assigned route |
| RF09 | Sistema de Notificações | In-app notifications, toasts, and simulated push events | Status and promotional notification events |
| RF10 | Gestão de Cupons | Coupon entry, validation, discount calculation, expiry, and minimum-order rules | Valid and invalid checkout cases |
| RF11 | Suporte e Chat | Support inbox, seeded conversation, issue category, and message states | Customer opens and continues a support thread |
| RF12 | Segurança de Dados | Tokenized demo payment references, protected secrets, input validation, redaction, and access checks | Security notes, tests, and safe failure states |
| RF13 | Logs de Auditoria | Append-only audit events for order, payment, menu, role, and delivery changes | Admin reviews an order’s history |
| RF14 | Controle de Acessos | Customer, Restaurant, Courier, and Admin roles with protected surfaces | Role-specific navigation and authorization tests |

### 8.2 Non-functional requirements

| ID | Source requirement | Portfolio implementation and evidence |
|---|---|---|
| RNF01 | Disponibilidade: 99.9% | Health checks, isolated adapters, graceful degraded states, demo reset, and a documented target. The project will not claim measured production uptime. |
| RNF02 | Missing in source document | Project-derived requirement: transactional consistency for order, payment, delivery, and audit state. State changes are validated, idempotent where needed, and recorded atomically. |
| RNF03 | Desempenho: map delay up to 5 seconds | GPS simulator, last-update indicator, latency metrics, and an acceptance test for tracking updates. |
| RNF04 | Escalabilidade during peaks | Pagination, caching boundaries, asynchronous event handling, queue-ready interfaces, and a peak-demand simulation. |
| RNF05 | Usabilidade | Short checkout, clear status language, task-oriented dashboards, consistent loading states, and frictionless rating flow. |
| RNF06 | Android and iOS compatibility | Mobile-first responsive web application and PWA behavior tested at mobile viewports. Native wrappers remain an optional later surface. |
| RNF07 | Accessibility | Semantic controls, keyboard operation, focus states, screen-reader labels, contrast checks, motion reduction, and automated accessibility scans. |
| RNF08 | Conformidade LGPD | Data minimization, consent and privacy surfaces, transparent data use, export/delete demonstration, and retention rules. |
| RNF09 | Backup and recoverability | Seed snapshots, demo export/import, reproducible reset, database backup documentation, and recovery verification. |
| RNF10 | Friendly errors | Domain errors translated into user-facing messages without stack traces, internal codes, or infrastructure details. |

RNF02 is intentionally defined as a project-owned clarification. The source document skips that number, and the portfolio must make the correction visible rather than silently pretending the source was complete.

### 8.3 Dependency map

The source dependency table covers RF01 through RF11. This project preserves those dependencies and extends the map:

| Requirement | Depends on | Reason |
|---|---|---|
| RF01 | RNF03, RNF05 | Search needs responsive data loading and an intuitive discovery flow |
| RF02 | RF12, RNF02, RNF05 | Checkout must be secure, consistent, and easy to complete |
| RF03 | RNF01, RNF03 | Tracking requires availability and low-latency updates |
| RF04 | RNF05 | Feedback needs a low-friction post-delivery flow |
| RF05 | RNF01, RF12, RNF02 | Payments need availability, data protection, and consistent state |
| RF06 | RNF01, RNF04 | Restaurant operations must remain usable during demand growth |
| RF07 | RF12, RF14 | Profile data requires privacy and protected access |
| RF08 | RNF01, RNF03, RNF04 | Courier operations require live updates and peak-capable assignment |
| RF09 | RNF01 | Notification delivery depends on available messaging services |
| RF10 | RF02, RNF05 | Coupons are part of checkout and must not create friction |
| RF11 | RNF01, RNF10 | Support requires a reliable and understandable communication path |
| RF12 | RF14, RNF08 | Security controls depend on identity boundaries and privacy rules |
| RF13 | RNF02, RF14 | Audit events must be consistent and access-controlled |
| RF14 | Security foundation | Every role-specific operation must be authorization-aware |

## 9. Domain Model

The initial domain model contains:

| Entity | Responsibility |
|---|---|
| User | Identity, profile, preferences, and account state |
| Role | Customer, Restaurant, Courier, or Admin permission set |
| Restaurant | Marketplace partner and operating state |
| MenuItem | Name, description, price, image, category, and availability |
| Address | Saved delivery or restaurant address with market-aware formatting |
| Cart | Temporary customer selection before order creation |
| Order | Customer purchase, items, totals, payment reference, and state |
| OrderItem | Snapshot of menu item details and quantity at purchase time |
| Payment | Provider-neutral payment attempt and outcome |
| Coupon | Discount rule, validity window, and eligibility constraints |
| CourierProfile | Availability, current position, capacity, and status |
| Delivery | Operational delivery record connected to an order and courier |
| RoutePlan | Solver output for one delivery or a grouped assignment |
| RouteStop | Pickup or drop-off stop with ordering and status |
| TrackingEvent | Position or delivery-state event with timestamp |
| Notification | User-facing event and delivery status |
| Conversation | Support thread and participants |
| Message | Individual support message |
| Review | Customer rating and comment for a restaurant or courier |
| AuditEvent | Append-only record of sensitive system activity |
| MarketConfig | Locale, currency, payment methods, address rules, and policies |
| DemoScenario | Deterministic data and transitions for replayable demonstrations |

### 9.1 Order state machine

~~~mermaid
stateDiagram-v2
    [*] --> placed
    placed --> confirmed
    placed --> cancelled
    confirmed --> preparing
    confirmed --> cancelled
    preparing --> ready_for_pickup
    ready_for_pickup --> courier_assigned
    courier_assigned --> picked_up
    picked_up --> en_route
    en_route --> delivered
    delivered --> rated
    delivered --> [*]
    cancelled --> [*]
~~~

Every transition is validated against the current state, creates an audit event, and emits the relevant notification event.

## 10. Technical Architecture

### 10.1 Recommended shape

The application is a modular monolith with explicit interfaces. This gives the portfolio a credible architecture without creating unnecessary distributed-system overhead.

- **Frontend:** TypeScript responsive web application with a mobile-first component system.
- **Backend:** FastAPI application with domain services and typed request/response schemas.
- **Persistence:** PostgreSQL-oriented schema with a lightweight local/demo configuration.
- **Realtime:** Server-sent events or WebSocket adapter for tracking and notifications.
- **Background work:** Queue-ready event handlers for notifications, GPS simulation, and future optimization jobs.
- **Maps:** Map rendering separated from graph and routing logic.
- **Testing:** Unit, integration, contract, end-to-end, accessibility, and benchmark suites.
- **Deployment:** Containerized local stack and a simple hosted demo profile.

The exact provider for maps, payments, messaging, and storage is an adapter decision. The domain layer must not depend directly on a vendor SDK.

### 10.2 System boundaries

~~~mermaid
flowchart TD
    Client[Responsive customer, restaurant, courier, and admin UI]
    API[FastAPI application boundary]
    Domain[Domain services and state machines]
    Data[(Database and seeded demo data)]
    Events[Events, simulator, and realtime adapters]
    Routing[Routing and optimization engine]
    Maps[Map renderer and route geometry]

    Client --> API
    API --> Domain
    Domain --> Data
    Domain --> Events
    Domain --> Routing
    Routing --> Maps
    Events --> Client
~~~

### 10.3 Module boundaries

#### Identity and access

Owns demo sessions, role selection, authorization checks, and protected route behavior.

#### Catalog

Owns restaurants, menu items, filters, availability, and market-aware formatting.

#### Orders

Owns cart conversion, totals, observations, state transitions, idempotency, and order history.

#### Payments

Owns a provider-neutral payment interface and demo gateway implementations. The system stores references and outcomes, never raw card data.

#### Delivery operations

Owns courier availability, assignment, pickup, drop-off, delivery state, and operational metrics.

#### Routing

Owns graph representation, shortest-path solvers, stop-ordering solvers, route results, and benchmark metrics.

#### Realtime and simulation

Owns demo clock, GPS replay, notification delivery, event broadcasting, and reset/advance controls.

#### Communication

Owns notifications and support conversations.

#### Trust and governance

Owns access logs, audit records, privacy actions, error translation, and admin inspection.

## 11. Routing and Optimization Design

### 11.1 Terminology

The portfolio must distinguish three related problems:

- **Pathfinding:** finding a route between two points in a graph.
- **Route optimization:** choosing the order of multiple stops.
- **Dispatch optimization:** assigning orders and stops to available couriers under constraints.

The original exercise is primarily a brute-force TSP implementation. It is useful as a correctness baseline but is not, by itself, a complete delivery optimizer.

### 11.2 Solver progression

#### Legacy baseline: brute-force TSP

The legacy solver:

- fixes the starting city;
- enumerates every permutation;
- calculates total distance;
- stores the current best route;
- records execution time;
- optionally stores every tested route for small instances;
- exposes the factorial growth in evaluated routes.

It is intentionally preserved as a superseded implementation. It must remain understandable, testable, and available to the algorithm laboratory.

#### Shortest-path solver

A* or Dijkstra solves the navigation subproblem between two known points. The solver accepts a graph and produces:

- ordered graph nodes;
- route geometry;
- distance;
- estimated travel cost;
- visited or expanded-node metrics.

#### Exact replacement for small instances

Branch-and-bound or dynamic programming can replace exhaustive permutation enumeration for small, controlled cases. The implementation should expose pruning or memoization metrics so the improvement is explainable.

#### Practical multi-stop solver

Nearest-neighbor initialization followed by 2-opt improvement provides a practical, easy-to-explain heuristic for the demo. It can be extended with:

- pickup-before-drop-off precedence;
- courier capacity;
- delivery time windows;
- late-delivery penalties;
- multiple couriers;
- reassignment when a courier becomes unavailable.

The initial product should ship with a reliable single-courier multi-stop scenario. General vehicle-routing complexity is introduced only when it improves the demo or the evidence.

### 11.3 Stable solver contract

The domain-facing routing API is independent of the algorithm:

**RouteProblem**

- origin or depot;
- pickup and drop-off stops;
- graph or travel-matrix reference;
- constraints;
- objective;
- deterministic seed where relevant.

**RouteResult**

- ordered stops;
- route segments;
- distance;
- estimated travel time;
- solver name and version;
- computation time;
- routes or candidates evaluated;
- pruning or improvement metrics;
- warnings and constraint violations;
- optional route history for bounded experiments.

**RouteSolver**

- accepts a RouteProblem;
- returns a RouteResult;
- exposes metadata describing the algorithm and assumptions.

### 11.4 Product integration

The courier dashboard consumes RouteResult rather than knowing which solver produced it. The algorithm laboratory can compare solvers using the same problem input. This allows the legacy implementation to be superseded without rewriting the customer or courier experiences.

## 12. Demo Mode

Demo mode is a first-class product capability.

### 12.1 Controls

- Start scenario
- Pause scenario
- Advance one event
- Advance one simulated minute
- Reset scenario
- Switch role
- View event stream
- Toggle algorithm explanation
- Select single-order or multi-order scenario

### 12.2 Determinism

Every demo run uses:

- seeded entities;
- stable IDs;
- a deterministic clock;
- deterministic route inputs;
- reproducible GPS points;
- resettable state;
- stable expected outcomes.

The demo must never depend on a real payment, live GPS device, or external service being available.

### 12.3 Simulation events

The simulator can emit:

- order.created
- order.confirmed
- order.preparing
- order.ready
- courier.assigned
- courier.location_updated
- delivery.picked_up
- delivery.en_route
- delivery.delivered
- notification.created
- review.requested
- audit.recorded

The same event model should remain usable when a real provider is introduced later.

## 13. API and Event Surface

The initial API surface is intentionally small and domain-oriented:

| Area | Example operations |
|---|---|
| Catalog | List restaurants, search menu, view restaurant |
| Cart and order | Create order, view order, advance order state |
| Payment | List methods, authorize demo payment, retrieve outcome |
| Customer | View profile, manage addresses, view history |
| Restaurant | View queue, update menu, change availability, advance preparation |
| Courier | Set availability, accept assignment, update delivery state, submit location |
| Tracking | Retrieve current route, subscribe to tracking events |
| Notifications | List notifications, mark as read |
| Coupons | Validate coupon, apply discount |
| Support | List conversations, send message |
| Reviews | Submit restaurant or courier review |
| Admin | Inspect operations, audit events, demo metrics |
| Demo | Reset scenario, advance clock, inspect event stream |

Commands that change state should be safe to retry or should expose an idempotency strategy. Read models should be paginated where lists can grow.

## 14. Security, Privacy, and Trust

### 14.1 Payment boundary

The demo never stores raw card numbers or security codes. Payment methods are represented by safe test labels or token-like references. The project demonstrates the correct boundary but does not claim PCI-DSS certification.

### 14.2 Access control

Authorization is enforced at the API/domain boundary, not only by hiding frontend navigation. Every protected operation checks:

- authenticated demo identity;
- role;
- ownership or operational scope;
- current entity state;
- allowed command.

### 14.3 LGPD-aware behavior

The application demonstrates:

- clear explanation of collected data;
- minimal profile data;
- privacy settings;
- consent state;
- export request;
- deletion request;
- retention behavior;
- redaction of personal data in logs.

The demo should use fictional personal data only.

### 14.4 Auditability

Audit events record:

- actor;
- role;
- action;
- target entity;
- previous state where relevant;
- new state where relevant;
- timestamp;
- correlation or request identifier;
- safe metadata.

Audit records are append-only from the application’s perspective and are visible to authorized administrators.

## 15. Error Handling and Degraded States

The UI must translate domain failures into useful language.

Representative conditions include:

- payment declined;
- coupon invalid or expired;
- restaurant temporarily unavailable;
- item sold out;
- courier unavailable;
- delivery state conflict;
- route unavailable;
- tracking temporarily delayed;
- support message failed;
- permission denied;
- demo scenario reset.

The user sees a clear action or explanation. Technical stack traces, database errors, provider response bodies, and internal identifiers remain outside the user-facing interface.

When realtime tracking is unavailable, the customer sees the last known position and a clear update timestamp. When route generation fails, the courier sees a recoverable state and the operations view records the failure for investigation.

## 16. Data and Map Strategy

### 16.1 Seed data

Seed data should include:

- multiple restaurants;
- multiple cuisines;
- menu availability differences;
- realistic prices in BRL;
- customer addresses;
- couriers with different availability;
- valid and invalid coupons;
- completed and active orders;
- support conversations;
- reviews;
- audit history;
- single-order and multi-order delivery scenarios.

### 16.2 Map data

The demo uses a stable, reproducible map source:

- a pre-baked city or neighborhood graph for algorithm experiments;
- route geometry represented as GeoJSON;
- fictional or safely generalized addresses;
- map attribution where external geographic data is used;
- optional provider adapter for real street-network routing.

The algorithm tests must not require a network request. External map services are an enhancement, not a prerequisite for correctness.

## 17. Quality Strategy

### Unit tests

- order state transitions;
- totals and coupon rules;
- payment outcomes;
- access-control decisions;
- error translation;
- route distance calculations;
- solver correctness;
- route-result invariants;
- market formatting.

### Differential algorithm tests

For small problems, the legacy brute-force solver acts as a correctness oracle. Replacement solvers are compared against it for:

- total route distance;
- valid start and end;
- every required stop visited;
- pickup-before-drop-off precedence;
- equivalent optimal results where exactness is expected.

### Integration tests

- checkout to order creation;
- restaurant state changes;
- courier assignment;
- tracking event propagation;
- notification creation;
- audit-event creation;
- role-protected commands;
- demo reset and replay.

### End-to-end tests

At least one complete scenario must run through:

customer browse → checkout → restaurant acceptance → courier assignment → route → tracking → delivery → review.

### Accessibility tests

- keyboard-only navigation;
- focus visibility;
- screen-reader names;
- form error association;
- color and contrast;
- reduced-motion behavior;
- responsive layout checks.

### Performance and benchmarking

Algorithm timing excludes plotting, browser rendering, and network calls. Benchmarks record:

- number of cities or stops;
- solver;
- route distance;
- estimated travel time;
- computation time;
- candidates evaluated;
- pruning or improvement count;
- random seed;
- machine/runtime context.

Application telemetry records:

- tracking update lag;
- API response latency;
- event processing time;
- route-generation time;
- failed transitions;
- notification delivery state.

## 18. Implementation Milestones

### Milestone 0 — Foundation

Deliver:

- requirements traceability;
- domain terminology;
- market configuration;
- application shell;
- role switcher;
- seed/reset mechanism;
- initial design system;
- error model.

Proof:

- every role can enter the correct surface;
- demo data can be reset;
- no requirement is unassigned.

### Milestone 1 — Customer ordering

Deliver RF01, RF02, RF05, RF07, RF10, and the customer portion of RF09.

Proof:

- customer can search, filter, select, customize, coupon, pay, and receive confirmation.

### Milestone 2 — Restaurant operations

Deliver RF06 and restaurant-facing order events.

Proof:

- restaurant can manage menu availability and advance an order through preparation.

### Milestone 3 — Courier operations and tracking

Deliver RF03, RF08, and the tracking portion of RF09.

Proof:

- courier can become available, receive an assignment, see both route legs, update status, and share simulated location.

### Milestone 4 — Routing evolution

Deliver:

- legacy brute-force solver;
- shortest-path solver;
- replacement multi-stop solver;
- stable RouteProblem and RouteResult contracts;
- benchmark and comparison views.

Proof:

- the courier flow uses the replacement solver;
- the laboratory shows why the legacy implementation does not scale.

### Milestone 5 — Trust and operations

Deliver RF04, RF11, RF12, RF13, RF14, admin operations, privacy surfaces, and support.

Proof:

- role boundaries, audit history, reviews, support, and safe payment behavior are visible and testable.

### Milestone 6 — Portfolio hardening

Deliver RNF01 through RNF10 evidence, responsive polish, accessibility checks, deployment, documentation, screenshots, and demo recording.

Proof:

- a reviewer can open the application, understand the story, run the scenario, inspect the algorithm comparison, and read the technical evidence.

## 19. Portfolio Deliverables

The final repository and presentation should contain:

- README with product story and demo instructions;
- requirements traceability matrix;
- architecture diagram;
- domain model and state-machine documentation;
- setup and seed/reset instructions;
- demo accounts or role selector;
- legacy solver and replacement solver;
- benchmark results and methodology;
- test report;
- accessibility notes;
- security and privacy boundary notes;
- ADR explaining why the legacy implementation is retained;
- ADR explaining the routing abstraction;
- known limitations;
- screenshots or short demo video;
- deployed demo link where feasible.

The README should lead with the product experience, then explain why routing is the technical centerpiece. The algorithm laboratory is a supporting proof surface, not the entire application.

## 20. Definition of Done

The portfolio release is complete when:

- the lunch-rush scenario can be completed from customer order to review;
- restaurant, courier, customer, and admin surfaces are all explorable;
- the demo can reset and replay deterministically;
- every RF01–RF14 requirement has a mapped surface and evidence;
- every RNF01 and RNF03–RNF10 requirement has an implementation decision and evidence;
- RNF02 is documented as a project-derived consistency requirement;
- the legacy solver remains available and tested;
- the replacement route solver is used by the courier flow;
- tracking visibly updates within the configured demo target;
- payment, privacy, and security limitations are honestly stated;
- accessibility and responsive behavior are tested;
- errors are understandable;
- benchmarks exclude visualization and network noise;
- the project can be explained in a short portfolio walkthrough.

## 21. Known Limitations

The portfolio must state these plainly:

- demo payments are simulated;
- GPS movement is simulated;
- uptime is designed for, not proven in production;
- the initial routing engine is not a nationwide logistics optimizer;
- map data may be seeded or generalized;
- support is a demonstration workflow, not a staffed service;
- responsive PWA behavior is the initial mobile target;
- production compliance would require additional operational, legal, and security work.

These limitations do not weaken the project. They distinguish a credible portfolio system from an exaggerated production claim.

## 22. Final Narrative

This project begins with a university requirements document and grows into a complete product demonstration.

The food-delivery application supplies the human and operational context. The routing engine supplies the technical depth. The legacy implementation is not hidden or discarded: it is preserved as evidence of where the project began, measured honestly, and deliberately superseded.

The finished portfolio piece should make the progression obvious:

**requirements → product model → full UI → simulated operations → route optimization → measurement → replacement architecture**
