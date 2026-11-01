# Persistence and seeding guide

**Status:** Implemented — memory is the default, PostgreSQL is an optional adapter
**Product:** Entrega Clara
**Decisions:** [ADR 0003: hybrid persistence](../adr/0003-hybrid-persistence.md),
[ADR 0012: PostgreSQL adapter, outbox and metrics](../adr/0012-postgres-adapter-outbox-and-metrics.md)
**Runbook:** [PostgreSQL, outbox and metrics](../runbooks/postgres.md)
**Related:** [provider boundaries](provider-and-integration-boundaries.md), [M1 runbook](../runbooks/milestone-1-development.md)

This guide describes how the application persists dynamic product state today. The domain says what
the records mean; this page says how the two adapters behave, what is verified, and what is
deliberately not built yet.

## Persistence modes

| Mode | Startup setting | Guarantees | Does not guarantee |
| --- | --- | --- | --- |
| Memory | `PERSISTENCE_MODE=memory` (default) | Fast isolated commands, copy-on-write rollback, reset/replay, deterministic tests | Data survives a process restart |
| PostgreSQL | `PERSISTENCE_MODE=postgres` + `DATABASE_URL` | Durable snapshot, optimistic version check, transactional outbox, restart persistence | Production backup/uptime; multiple writers |

There is one active adapter per process. No dual writes or silent fallback: with
`PERSISTENCE_MODE=postgres` and an unusable driver, URL or server, the application fails with a
precise message instead of quietly using memory.

## What a unit of work does

Every state-changing command goes through the same port (`application/ports.py`):

1. loads the aggregates it needs;
2. validates authorization, version and domain state;
3. mutates the working copy;
4. appends audit/notification/tracking records and event-log entries;
5. commits atomically;
6. publishes events only after the commit returns.

The application layer does not know which adapter is active.

**Memory adapter.** Entering a unit of work deep-copies the store; commits swap the copy back;
raising (or `rollback`) discards it. Events are queued and published post-commit to the in-process
hub.

**PostgreSQL adapter.** Entering loads the stored snapshot into the same `MemoryStore` collections
and binds the *same* repository implementations (so both adapters share one implementation of every
repository contract). Commit writes the snapshot back in one transaction:

```text
UPDATE store_snapshots
   SET version = :loaded + 1, payload = :snapshot
 WHERE id = 'primary' AND version = :loaded
   -- row count 0 → VersionConflictError, nothing written
 + INSERT INTO outbox (event_id, …, published_at = NULL) for every committed event
COMMIT
```

Then the in-process publisher runs and the outbox rows are marked delivered. A crash in that window
leaves rows unpublished; `scripts/worker.py` drains them by logging and marking them (or forwarding
them through the publish hook). Memory mode has no cross-request locking: concurrent writers can
overwrite each other, which is acceptable for the single-process demo and is why PostgreSQL mode adds
the version guard.

## Storage shape (PostgreSQL)

| Table | Purpose |
| --- | --- |
| `store_snapshots` | one row (`id = 'primary'`) with the whole store as JSONB plus its `version` |
| `outbox` | one row per committed event, nullable `published_at` |

The schema is created by idempotent DDL in `adapters/postgres/store.py` on startup. There is no
Alembic migration tree yet: the snapshot document is addressed by `version`, so a schema change means
a new adapter version, not a column migration.

**Why a snapshot instead of tables per aggregate.** The repository ports are aggregate-shaped and
the memory adapter already implements all of them; persisting the snapshot keeps one implementation
of the contract, which is what makes "both adapters pass the same tests" meaningful. The cost is
visible and recorded: there are no per-aggregate foreign keys or indexes, and concurrent writers get
a `version_conflict` rather than row-level contention. Row-per-aggregate tables plus Alembic are the
next step once more than one process writes (ADR 0012).

## Seeding and boot

- Reference data comes from `data/seed/brazil.json`, loaded idempotently by
  `adapters/seed/loader.py`.
- Memory mode seeds the process store and serves.
- PostgreSQL mode loads the persisted snapshot, seeds reference data on top of it, and persists the
  result once at boot (`create_app`); dynamic orders already in the database are preserved.
- The `lunch-rush` scenario owns its order, delivery, route, tracking, notification, audit and clock
  state, identified by `scenario_id`, so reset never truncates unrelated dynamic orders.
- Orders created through customer checkout are dynamic records, not scenario records.

## Reset and replay contract

`ResetScenario("lunch-rush")` must:

- restore the exact initial scenario snapshot;
- restore the deterministic clock and event sequence;
- remove/recreate only scenario-owned dynamic records;
- preserve unrelated customer orders and catalog data;
- publish a reset event only after the transaction commits;
- produce the same subsequent state for the same sequence of commands.

Replay tests compare meaningful state, not generated timestamps or row order.

## Memory adapter semantics

- isolated instances per test;
- copy-on-write snapshot with rollback on failure;
- stable fixture IDs, deterministic clock and ID generator injection;
- scenario-scoped reset;
- post-commit in-process publication;
- process-restart data loss is documented, not hidden.

## PostgreSQL runtime semantics

Before serving requests in PostgreSQL mode:

- connectivity is validated and the DDL applied;
- the snapshot is loaded and reference data seeded;
- the outbox backlog is visible (`scripts/check_postgres.py` prints pending rows);
- health is **process liveness only** (`GET /api/v1/health`); a database readiness probe is not
  implemented yet and is listed below.

## Outbox

Memory mode publishes through the in-process hub after commit. PostgreSQL mode writes the snapshot
and one outbox row per event in the same transaction, publishes after commit, and marks rows
delivered only after the publisher accepted them; the worker drains anything left by a crash.

```text
aggregate change + audit/notification + outbox row → commit
post-commit publish → mark delivered; worker drains unmarked rows
```

Consumers must be idempotent. The current row carries event id, type, aggregate, payload and
timestamp; retry counters, attempt scheduling and dead-lettering are not built.

## Persistence test matrix (what the suite actually runs)

`tests/repo/test_persistence_contract.py` runs each case against memory **and** PostgreSQL:

| Case | Verified |
| --- | --- |
| Committed write visible to a later unit of work | yes, both adapters |
| Rollback discards everything | yes, both adapters |
| Events published only after commit | yes (memory hub) |
| Event log survives a restart | yes, both adapters |
| Optimistic version conflict | PostgreSQL only (memory is single-process copy-on-write) |
| Outbox recovers a commit whose publish never ran | PostgreSQL only |
| Fresh schema creation | PostgreSQL only (idempotent DDL) |

Not covered yet: per-aggregate relational constraints, Alembic upgrade paths, scenario-reset
isolation at the SQL level, and multi-process writers. Where `DATABASE_URL` is absent the PostgreSQL
cases skip with an explicit message and `docs/verification.md` records them as unverified in that
environment rather than passed.

## Backup and recovery

Not implemented. The demo documents seed reset/replay and snapshot export/import; before running a
persistent hosted environment:

- choose a managed/database backup policy;
- define retention and encryption;
- test a restore into an isolated environment;
- verify the adapter against the restored version;
- document data-loss expectations;
- never place backup exports in the public repository.

## Public-safety rules

- All public fixtures are synthetic.
- No raw card data, CVV, access tokens, OIDC secrets, database passwords, or provider payloads.
- No exact real courier traces or private addresses.
- No private source links.
- Logs use safe identifiers and generalized coordinates.
- Data/license provenance is recorded before importing external map or road data.
