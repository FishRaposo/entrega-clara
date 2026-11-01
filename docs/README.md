# Documentation

The seed design and the user-approved M1 design under `docs/superpowers/specs/` govern product decisions. Requirements traceability records implementation evidence, architecture documents repository contracts, ADRs record durable decisions, and the research/roadmap documents explain how future capabilities should be added.

## Start here

- [Platform build research](research/2026-09-01-platform-build-research.md) — source-backed technical, product, security, privacy, provider, testing, and operations findings.
- [M1 core delivery loop](superpowers/specs/2026-09-01-milestone-1-core-delivery-loop-design.md) — the current implementation contract.
- [Platform evolution roadmap](roadmap/platform-evolution.md) — M1 through portfolio release, with dependencies and exit evidence.
- [Portfolio improvement plan](roadmap/portfolio-improvements.md) — review findings and a prioritized backlog (routing, benchmarks, reviewer experience, Windows tooling) within the Python + Node toolchain.
- [M1 development runbook](runbooks/milestone-1-development.md) — local modes, planned commands, acceptance journey, and release checks.
- [PostgreSQL, outbox and metrics](runbooks/postgres.md) — persistent mode, the worker and the two metric views.
- [Deploying the demo](runbooks/deploy.md) — Fly.io, Vercel and GitHub Pages artifacts.
- [Static lab](../site/index.html) — self-contained replay of the committed traces.

## Architecture

- [System boundaries](architecture/system-boundaries.md)
- [Provider and integration boundaries](architecture/provider-and-integration-boundaries.md)
- [M1 API and event contract](architecture/api-and-events.md)
- [Persistence and seeding guide](architecture/persistence-and-seeding.md)
- [Routing contract](architecture/routing-contract.md)
- [Solver selection guide](architecture/solver-selection.md) — which rung to use, with the measured evidence
- [Repository layout](architecture/repository-layout.md)
- [External dependencies](architecture/external-dependencies.md)

## Durable decisions

- [ADR 0001: modular monolith](adr/0001-modular-monolith.md)
- [ADR 0002: solver-independent routing contract](adr/0002-solver-independent-routing-contract.md)
- [ADR 0003: hybrid persistence](adr/0003-hybrid-persistence.md)
- [ADR 0004: local routing and provider-neutral map rendering](adr/0004-local-routing-and-provider-neutral-map-rendering.md)
- [ADR 0005: SSE for M1 realtime updates](adr/0005-sse-for-m1-realtime-updates.md)
- [ADR 0006: defer real providers behind ports](adr/0006-defer-real-providers-behind-ports.md)
- [ADR 0007: multi-stop batching](adr/0007-multi-stop-batching.md)
- [ADR 0008: real street graph and landmark-based acceleration](adr/0008-real-street-graph-and-landmarks.md)
- [ADR 0009: city-scale graph and contraction hierarchies](adr/0009-city-scale-graph-and-contraction-hierarchies.md)
- [ADR 0010: time-dependent routing under a FIFO speed profile](adr/0010-time-dependent-routing.md)
- [ADR 0011: capacity, promised windows and dynamic re-planning](adr/0011-capacity-windows-and-dynamic-replanning.md)
- [ADR 0012: PostgreSQL adapter, transactional outbox and process metrics](adr/0012-postgres-adapter-outbox-and-metrics.md)

## Evidence

- [Verification record](verification.md) — exact gate results, routing evidence highlights, and the honest scope notes.
- [Routing benchmark](benchmarks/routing.md) — the solver ladder measured on the committed OSM extract (JSON and two SVG charts alongside).
- [City-scale benchmark](benchmarks/routing-city.md) — the same ladder on 105k nodes, with CH preprocessing, peak memory and break-even.
- [Static lab](../site/index.html) — self-contained replay of the committed traces (open it directly; no server or network).
- [Recorded tour](../docs/media/demo-tour.webm) — 35-second walkthrough of the demo, console, tracking and lab.
- [Benchmarks directory](benchmarks/) — machine-readable results and the replayable search trace (`lab-trace.json`).
- [Media](media/) — role screenshots, the ALT-vs-Dijkstra replay GIF and the static-lab poster.
- [ADR 0008](adr/0008-real-street-graph-and-landmarks.md) — why a real graph and landmark acceleration; ADR 0009 later added contraction hierarchies at city scale.

## Source materials

- [Original requirements document](requirements/Levantamento%20de%20Requisitos_%20Aplicativo%20de%20Delivery%20de%20Comida.docx) — the college requirements exercise (pt-BR, DOCX) that the seed design summarizes.
- [FoodExpress wireframe](design/foodexpress/README.md) — the medium-fidelity wireframe built alongside that exercise.
