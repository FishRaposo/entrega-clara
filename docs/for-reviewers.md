# Reviewing Entrega Clara

One page, roughly five minutes, for a recruiter, hiring manager or technical reviewer who wants to
judge the repository without reading all of it. Each step says what to look at and what it proves.

## What this is

A São Paulo food-delivery platform that doubles as a pathfinding and dispatch showcase. It began as
two undergraduate assignments — a delivery requirements document and a brute-force route optimizer —
merged into one product, then became a portfolio piece for employers and freelance clients
([origin](origin.md)). It is not an iFood clone and not a startup pitch.

## How it is built

- **Modular monolith:** FastAPI backend, Next.js web shell. Application ports in
  `application/ports.py`; adapters for memory, PostgreSQL, routing, payments and identity.
- **One command layer:** HTTP routes, the role screens and the deterministic demo all call the same
  `application/commands/` handlers; clock and IDs are injectable, so replay is deterministic.
- **Routing on the backend:** graph loading, solvers, matrices and the VRP live behind one contract;
  the browser renders supplied geometry and never decides a business route.
- **Optional infrastructure:** memory persistence by default; PostgreSQL with a transactional outbox
  behind an extra; no required Docker, WSL or database.
- **Observability and gates:** `/metrics` (Prometheus text), an operations metrics view, and
  `scripts/check.py` for the local gate.

## The five-minute path

| Minute | Open | What it shows |
| --- | --- | --- |
| 1 | The **measured ladder** table in the [README](../README.md#the-measured-ladder) | Six solvers on the same 105k-node graph, with the CH break-even |
| 2 | [Live lab](https://fishraposo.github.io/entrega-clara/) (or [`site/index.html`](../site/index.html) offline; no server, no network) | The algorithms replaying frame by frame, plus the day-long ETA curve |
| 3 | [City benchmark artifact](benchmarks/routing-city.md) | The raw measurements behind the table: preprocessing cost, peak memory, break-even, batch matrix cost |
| 4 | [Verification record](verification.md) | Exact gate results and counts, and the honest scope notes |
| 5 | [ADR 0009](adr/0009-city-scale-graph-and-contraction-hierarchies.md) | Why contraction hierarchies, what they cost, and where they stop paying |

If you only read one number: **CH answers a city route in 85 expansions and 2.8 ms, against
53,885 expansions and 172 ms for Dijkstra, after a 2.7 s build that breaks even at 12 queries.** The
expansion counts are stable; the times are from the committed run and vary with the machine.

## What is real, what is simulated

| Real | Simulated or synthetic |
| --- | --- |
| OpenStreetMap streets: 2,405-node centro extract in the product and lab, 104,991-node city artifact for benchmarks (ODbL attribution committed) | Payments, identity, GPS, notifications, support |
| The algorithms: Dijkstra, A\*, ALT, bidirectional, contraction hierarchies, time-dependent Dijkstra/A\*, Held-Karp, 2-opt, capacitated VRP with windows and precedence | The traffic profile: deterministic hourly multipliers, explicitly not measured traffic |
| The product loop: menus, carts, idempotent checkout, restaurant queue, courier lifecycle, batching, tracking, operations — one command layer for API, UI and demo | Restaurants, addresses and couriers: fictional São Paulo data |
| Tests: 290 backend (295 with the database contract), 19 frontend, 5 browser journeys with axe | API/web hosting: the static lab is live on Pages; API and web deploy artifacts exist but are not deployed by CI |
| The optional PostgreSQL adapter: transactional snapshot, optimistic version guard, outbox, drained by a worker | Production operations: no backups, no readiness probe, single writer |

## Five claims and where they are proven

| Claim | Evidence |
| --- | --- |
| Landmark routing cuts work by an order of magnitude on one-way streets | [city benchmark](benchmarks/routing-city.md) (ALT 5.9% of the graph) and `tests/routing/test_informed_solvers.py` |
| A contraction hierarchy makes city queries effectively free after preprocessing | [city benchmark](benchmarks/routing-city.md), [ADR 0009](adr/0009-city-scale-graph-and-contraction-hierarchies.md), `tests/routing/test_city_graph.py` work bounds |
| Batches respect capacity and promised windows, reject infeasible ones, and re-plan only remaining stops | [ADR 0011](adr/0011-capacity-windows-and-dynamic-replanning.md), `tests/routing/test_vrp.py`, `tests/api/test_batching.py` |
| Persistence survives a restart and does not lose committed events | `tests/repo/test_persistence_contract.py`, [verification](verification.md) |
| The project's claims stay honest as it changes | `python scripts/check.py` runs eleven gates, including benchmark smoke and static-lab freshness |

## Pick a path

- **Recruiter / hiring manager (5 min):** the five-minute path above, then the
  [README screenshots](../README.md#see-it-without-running-it).
- **Routing or algorithms (15 min):** [solver selection guide](architecture/solver-selection.md),
  ADRs [0008](adr/0008-real-street-graph-and-landmarks.md),
  [0009](adr/0009-city-scale-graph-and-contraction-hierarchies.md),
  [0010](adr/0010-time-dependent-routing.md),
  [0011](adr/0011-capacity-windows-and-dynamic-replanning.md), then `tests/routing/`.
- **Backend or platform (20 min):** [routing contract](architecture/routing-contract.md),
  [persistence guide](architecture/persistence-and-seeding.md),
  [ADR 0002](adr/0002-solver-independent-routing-contract.md),
  [ADR 0003](adr/0003-hybrid-persistence.md),
  [ADR 0012](adr/0012-postgres-adapter-outbox-and-metrics.md), then `tests/repo/`.
- **Frontend (10 min):** `app/web/src/components/algorithm-lab.tsx` and `lab-canvas.tsx`, the
  [static lab](../site/index.html), then `npm run build` and the Playwright journeys.

## How to run it

```bash
python -m pip install -e "app/backend[dev]"
cd app/web && npm install
python scripts/dev.py      # API :8000, web :3000
python scripts/check.py    # the full local gate
```

The default is memory mode: no Docker, database, `make` or provider accounts. PostgreSQL persistence
is opt-in (`PERSISTENCE_MODE=postgres` + `DATABASE_URL`, optional extra), documented in the
[PostgreSQL runbook](runbooks/postgres.md). Deploy artifacts are in the repository; deployment itself
is an operator action ([deploy runbook](runbooks/deploy.md)).

## What is deliberately not built

Row-per-aggregate PostgreSQL schema and migrations, backups, a database readiness probe, multi-writer
persistence, real payment/identity/notification providers, live traffic, native apps, and hosting.
Each is documented with its boundary rather than implied. The
[verification record](verification.md#honest-scope-notes) lists them together with the rest of the
honest limits.
