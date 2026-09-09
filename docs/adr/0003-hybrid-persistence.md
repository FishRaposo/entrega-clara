# ADR 0003: Hybrid persistence with one active repository adapter

## Status

Accepted for Milestone 1.

## Context

Entrega Clara needs two properties that pull in different directions:

- a deterministic, fast, offline demo that can reset and replay reliably;
- a credible persistent application path that survives API restarts and exercises relational transactions.

Using only an in-memory store would make the portfolio's persistence story weak. Requiring PostgreSQL for every test and demo would make the deterministic experience slower, less portable, and dependent on local infrastructure. Writing to both stores would create consistency and failure-order problems before the product needs them.

The existing Compose file already provides PostgreSQL, but the current application does not use it as an application repository.

## Decision

Implement repository and unit-of-work ports with two interchangeable adapters:

1. **Memory adapter:** the default for tests, Demo Mode, offline development, and presentations.
2. **PostgreSQL adapter:** an opt-in persistent runtime selected by `PERSISTENCE_MODE=postgres`.

Only one adapter is active in a process. There is no dual write and no cross-store synchronization job.

The PostgreSQL adapter will use SQLAlchemy 2-style repositories, explicit short-lived transactions, psycopg, and Alembic migrations. M1 will prefer synchronous SQLAlchemy sessions for simple application-command transactions. An SSE connection must never hold a database session open. Async SQLAlchemy remains a measured future option, not an unplanned dependency.

Both adapters must pass the same contract tests for reads, writes, rollback, ownership, optimistic version conflicts, idempotent checkout, event/audit consistency, and scenario-reset isolation.

### Transaction rule

Each state-changing command persists its aggregate changes, audit record, notification record, and event intent in one unit of work. Events are published to the in-process hub only after commit. A transactional outbox is required before multiple API processes or external workers are introduced.

### Data rule

Migrations own schema changes. Seed loaders own safe, idempotent reference/demo data. Scenario reset is scoped to scenario-owned records and never truncates unrelated dynamic orders.

## Consequences

### Positive

- M1 remains runnable without a database.
- The same domain behavior is exercised against memory and PostgreSQL.
- PostgreSQL constraints, indexes, and transaction behavior become visible portfolio evidence.
- The domain does not know which persistence technology is active.
- A later managed-Postgres deployment does not require redesigning the order model.

### Costs and risks

- Two repository implementations require contract tests and maintenance.
- Memory rollback semantics must be deliberately designed rather than assumed.
- PostgreSQL startup needs a healthcheck and migration strategy.
- An in-process publisher can lose an event after commit if the process crashes; this limitation is documented until an outbox exists.
- Async database access may eventually be useful, but adopting it now would add complexity without a measured need.

## Rejected alternatives

| Alternative | Reason not selected |
| --- | --- |
| PostgreSQL only | Makes offline demos/tests and deterministic replay unnecessarily infrastructure-dependent |
| Memory only | Does not demonstrate durable persistence or relational transaction behavior |
| Dual write | Introduces consistency, retry, and failure-order problems before they provide product value |
| Database access from domain objects | Couples business rules to ORM/session behavior and makes adapters harder to replace |

## Implementation guardrails

- `PERSISTENCE_MODE=memory` must not require a reachable database.
- `PERSISTENCE_MODE=postgres` must fail clearly if the URL is missing/unusable.
- Postgres mode must run migrations before serving application traffic.
- Database health/readiness must be distinct from process liveness.
- Audit/payment history must not be cascade-deleted accidentally.
- Money is stored as integer minor units plus currency.
- Timestamps are stored in UTC.
- A partial unique index may enforce one active M1 delivery per courier after its exact status predicate is agreed.

## References

- [SQLAlchemy ORM](https://docs.sqlalchemy.org/orm/)
- [SQLAlchemy sessions](https://docs.sqlalchemy.org/en/latest/orm/session_basics.html)
- [SQLAlchemy transactions](https://docs.sqlalchemy.org/en/latest/orm/session_transaction.html)
- [Alembic](https://alembic.sqlalchemy.org/)
- [Alembic autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [Docker Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/)
