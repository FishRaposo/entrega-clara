# Documentation

The seed design and the user-approved M1 design under `docs/superpowers/specs/` govern product decisions. Requirements traceability records implementation evidence, architecture documents repository contracts, ADRs record durable decisions, and the research/roadmap documents explain how future capabilities should be added.

## Start here

- [Platform build research](research/2026-09-01-platform-build-research.md) — source-backed technical, product, security, privacy, provider, testing, and operations findings.
- [M1 core delivery loop](superpowers/specs/2026-09-01-milestone-1-core-delivery-loop-design.md) — the current implementation contract.
- [Platform evolution roadmap](roadmap/platform-evolution.md) — M1 through portfolio release, with dependencies and exit evidence.
- [M1 development runbook](runbooks/milestone-1-development.md) — local modes, planned commands, acceptance journey, and release checks.

## Architecture

- [System boundaries](architecture/system-boundaries.md)
- [Provider and integration boundaries](architecture/provider-and-integration-boundaries.md)
- [M1 API and event contract](architecture/api-and-events.md)
- [Persistence and seeding guide](architecture/persistence-and-seeding.md)
- [Routing contract](architecture/routing-contract.md)
- [Repository layout](architecture/repository-layout.md)

## Durable decisions

- [ADR 0001: modular monolith](adr/0001-modular-monolith.md)
- [ADR 0002: solver-independent routing contract](adr/0002-solver-independent-routing-contract.md)
- [ADR 0003: hybrid persistence](adr/0003-hybrid-persistence.md)
- [ADR 0004: local routing and provider-neutral map rendering](adr/0004-local-routing-and-provider-neutral-map-rendering.md)
- [ADR 0005: SSE for M1 realtime updates](adr/0005-sse-for-m1-realtime-updates.md)
- [ADR 0006: defer real providers behind ports](adr/0006-defer-real-providers-behind-ports.md)
