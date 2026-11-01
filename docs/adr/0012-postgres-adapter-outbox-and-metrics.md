# ADR 0012 — PostgreSQL adapter, transactional outbox and process metrics

Status: accepted. Implemented by `adapters/postgres/`, `scripts/worker.py`,
`core/metrics.py`, `GET /metrics` and `GET /operations/metrics`.

## Context

ADR 0003 promised two interchangeable persistence adapters and named the
limitation of the in-process publisher: an event can be lost if the process dies
between the commit and the publish. ADR 0005 repeated that caveat. The demo has
been memory-only since the first milestone, and ADR 0003 was explicit that
`PERSISTENCE_MODE=postgres` must fail clearly rather than pretend.

Two questions had to be answered together: how much of the port surface the
PostgreSQL adapter implements, and what "verified" means when the reviewer may
not have a database.

## Decision

### Adapter shape

1. **Snapshot persistence, same repositories.** The PostgreSQL adapter loads the
   full store into the same `MemoryStore` collections, binds the **same**
   repository implementations through `build_repositories`, and writes the
   snapshot back in one transaction. This keeps one implementation of every
   repository contract, which is what makes "both adapters pass the same
   contract" a meaningful test instead of two hand-written copies drifting.
2. **Optimistic concurrency is real.** The snapshot row carries a `version`; a
   commit is `UPDATE ... WHERE version = <loaded>`, and a row count of zero
   raises `VersionConflictError`. Two units of work that read the same version
   cannot both write.
3. **Rollback is the absence of a write.** Exiting a unit of work with an
   exception discards the working copy; nothing reaches the database.
4. **Row-per-aggregate is deferred, explicitly.** A normalized schema is the
   right next step when more than one process writes concurrently (or when a
   collection outgrows a snapshot). The ports do not change when that happens;
   this ADR records the boundary instead of hiding it.

### Outbox

5. **Events are enqueued in the committing transaction.** `save` writes the
   snapshot and one `outbox` row per event atomically. The publisher runs after
   commit; rows are marked `published_at` only after the publisher returned
   successfully. A crash between commit and publish therefore leaves unpublished
   rows, and `scripts/worker.py` drains them — at-least-once, never lost.
6. **The worker is boring on purpose.** It publishes to the in-process hub (a
   no-op in a separate process today), marks rows delivered, and logs. When a
   real subscriber exists, only the `publish` callable changes.

### Metrics

7. **One in-process registry, two views.** `core/metrics.py` renders Prometheus
   text for `/metrics` and a JSON snapshot for `/operations/metrics`, which the
   operations panel renders next to the product counters. Families: HTTP
   requests and latency (by route template, not raw path), routing queries and
   latency by kind/solver, routing nodes expanded, events published with their
   lag, and an active-SSE gauge.
8. **Process-local and honest about it.** Counters reset on restart; the metrics
   are not aggregated across workers. That is stated in the code and the
   runbook rather than implied to be a production monitoring stack.

## Verification

* The contract suite (`tests/repo/test_persistence_contract.py`) runs against
  memory **and** PostgreSQL and covers: committed writes visible to a later unit
  of work, rollback, event publication only after commit, the event log
  surviving a restart, stale-write rejection, and outbox recovery of the
  commit/publish window.
* PostgreSQL was exercised locally with the portable 16.9 server described in
  `docs/runbooks/postgres.md`; the same steps run against the Compose service.
* A restart smoke (`create_app()` twice in one process) places an order, builds
  a second application instance, and reads the order back from the database.
* Without `DATABASE_URL`, the PostgreSQL cases skip with an explicit message and
  `docs/verification.md` says they are unverified in that environment. Memory
  stays the default; nothing about the offline demo changed.

## Rejected alternatives

* **Hand-written per-aggregate SQL now.** Fifteen tables, migrations and a second
  copy of every repository contract for a single-writer demo; the snapshot
  adapter proves the transaction, conflict and outbox behaviour with a fraction
  of the surface.
* **Dual writes (memory + database).** Consistency and failure ordering get
  harder before they buy anything; ADR 0003 already rejected this.
* **Publishing before commit.** That is exactly the loss window the outbox
  exists to close.
* **Pulling Prometheus client libraries.** The exposition format is a few dozen
  lines; the project's no-required-dependency rule is worth more than the
  convenience.
