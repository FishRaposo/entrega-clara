# System boundaries

Entrega Clara is a modular monolith with explicit interfaces. Application source stays under `app/`; repository-level configuration, deterministic data, tests, scripts, and documentation remain outside that boundary.

| Boundary | Owns | Must not depend on directly |
| --- | --- | --- |
| Web client | Responsive Customer, Restaurant, Courier, and Admin demo surfaces; role navigation | Provider SDKs, production credentials, or authorization-by-visibility |
| API | Typed HTTP boundary, request validation, health and deterministic demo routes | Frontend-only state or vendor-specific business logic |
| Domain | Order state transitions, business rules, errors, and provider-neutral contracts | FastAPI, browser components, or vendor SDKs |
| Demo and simulation | Seed loading, deterministic clock/event progression, reset, replay, and simulated updates | Wall-clock-dependent outcomes, live GPS, or external services |
| Routing | Graph inputs, solver contracts, route results, and benchmark inputs | Map-rendering providers or UI concerns |
| Data | PostgreSQL-oriented persistence boundary and versioned seed/scenario data | Raw card data, secrets, or production customer records |
| Provider adapters | Future payment, map, notification, realtime, and storage integrations | Domain-level dependency on a specific vendor SDK |

## Runtime boundary

Docker Compose provides three local services: `db`, `api`, and `web`. `api` runs the FastAPI package from the root Python image and reads the versioned `data/` scenario files. `web` runs the Node 22 package in `app/web`. The Postgres service exists as the local persistence boundary; current demo routes are deterministic and do not require a live provider integration.

Configuration values are supplied at runtime, not baked into images. The root Python image copies only `app/backend` and `data`, so it excludes `.env` files and other secrets. The fixed Compose database credentials are local demo values, not deployable credentials.

## Trust and non-production boundary

The demo stores only safe test labels or token-like payment references; it does not store raw card numbers or security codes and does not claim PCI-DSS certification. GPS, maps, notifications, support, and role selection are simulated or staged interfaces. Authorization belongs at the API/domain boundary when protected operations are implemented, not only in frontend navigation.

This architecture supports a portfolio demonstration, not a certified production system. It does not claim real payment processing, live courier identity verification, real-time provider connectivity, operational support coverage, or measured uptime.
