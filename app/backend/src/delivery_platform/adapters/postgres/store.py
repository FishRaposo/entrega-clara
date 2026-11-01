"""PostgreSQL persistence: one transactional snapshot plus a transactional outbox.

The repository ports are aggregate-shaped, and the memory adapter already
implements all of them over a ``MemoryStore``. This adapter satisfies the same
ports by loading the snapshot into those collections, binding the *same*
repository implementations, and writing the snapshot back inside a single
transaction with an optimistic version guard. That keeps one source of truth for
repository semantics — so "memory and PostgreSQL pass the same contract" is a
meaningful statement — while giving PostgreSQL what the demo needs: durability
across restarts, rollback, version conflicts and an outbox written in the same
transaction as the state change.

Tables (see ``SCHEMA``):

* ``store_snapshots`` — one row, ``version`` for optimistic concurrency and a
  ``payload`` JSON document with every collection.
* ``outbox`` — one row per committed event, unpublished until the publisher has
  actually accepted it; a crash between commit and publish is recoverable.

Row-per-aggregate tables are the next step when several processes write at once;
the ports and the domain do not change when that happens (ADR 0012).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine

from delivery_platform.adapters.memory.store import MemoryStore
from delivery_platform.domain.entities import IdempotencyRecord
from delivery_platform.domain.errors import VersionConflictError
from delivery_platform.domain.events import DomainEvent

SNAPSHOT_ID = "primary"
#: Composite idempotency keys are tuples; JSON object keys are strings.
KEY_SEPARATOR = "\x1f"

SCHEMA = """
CREATE TABLE IF NOT EXISTS store_snapshots (
    id          TEXT PRIMARY KEY,
    version     BIGINT NOT NULL,
    payload     JSONB NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outbox (
    id            BIGSERIAL PRIMARY KEY,
    event_id      TEXT NOT NULL UNIQUE,
    type          TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_id  TEXT NOT NULL,
    occurred_at   TIMESTAMPTZ NOT NULL,
    payload       JSONB NOT NULL,
    published_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS outbox_pending_idx ON outbox (published_at) WHERE published_at IS NULL;
"""

_ADAPTER = TypeAdapter(MemoryStore)
_IDEMPOTENCY = TypeAdapter(IdempotencyRecord)

_INSERT_SNAPSHOT = text(
    "INSERT INTO store_snapshots (id, version, payload) "
    "VALUES (:id, :version, :payload) ON CONFLICT (id) DO NOTHING"
).bindparams(bindparam("payload", type_=JSONB))

_UPDATE_SNAPSHOT = text(
    "UPDATE store_snapshots "
    "SET version = :version, payload = :payload, updated_at = now() "
    "WHERE id = :id AND version = :expected"
).bindparams(bindparam("payload", type_=JSONB))

_INSERT_OUTBOX = text(
    "INSERT INTO outbox "
    "(event_id, type, aggregate_type, aggregate_id, occurred_at, payload) "
    "VALUES (:event_id, :type, :aggregate_type, :aggregate_id, :occurred_at, :payload) "
    "ON CONFLICT (event_id) DO NOTHING"
).bindparams(bindparam("payload", type_=JSONB))


def encode_store(store: MemoryStore) -> dict[str, Any]:
    payload = _ADAPTER.dump_python(store, mode="json")
    payload["idempotency"] = {
        f"{identity}{KEY_SEPARATOR}{key}": _IDEMPOTENCY.dump_python(record, mode="json")
        for (identity, key), record in store.idempotency.items()
    }
    return payload


def decode_store(payload: dict[str, Any]) -> MemoryStore:
    data = dict(payload)
    raw_keys = data.pop("idempotency", {}) or {}
    store = _ADAPTER.validate_python(data)
    store.idempotency = {}
    for composite, record in raw_keys.items():
        identity, _, key = str(composite).partition(KEY_SEPARATOR)
        store.idempotency[(identity, key)] = _IDEMPOTENCY.validate_python(record)
    return store


def adopt_store(target: MemoryStore, source: MemoryStore) -> None:
    """Replace every collection on ``target`` with ``source`` (same object identity)."""
    for field in dataclasses.fields(MemoryStore):
        setattr(target, field.name, getattr(source, field.name))


class PostgresUnavailable(RuntimeError):
    """The PostgreSQL adapter is selected but its driver or server is unusable."""


@dataclass
class PostgresStore:
    engine: Engine

    @classmethod
    def from_url(cls, url: str, *, echo: bool = False) -> PostgresStore:
        if not url:
            raise PostgresUnavailable(
                "PERSISTENCE_MODE=postgres requires DATABASE_URL "
                "(for example postgresql+psycopg://delivery:delivery@localhost:5432/delivery)"
            )
        try:
            engine = create_engine(url, pool_pre_ping=True, future=True, echo=echo)
        except Exception as error:
            raise PostgresUnavailable(f"Could not create the PostgreSQL engine: {error}") from error
        return cls(engine=engine)

    def migrate(self) -> None:
        with self.engine.begin() as connection:
            for statement in SCHEMA.split(";"):
                if statement.strip():
                    connection.execute(text(statement))

    def load(self) -> tuple[MemoryStore, int]:
        with self.engine.begin() as connection:
            row = connection.execute(
                text("SELECT version, payload FROM store_snapshots WHERE id = :id"),
                {"id": SNAPSHOT_ID},
            ).first()
        if row is None:
            return MemoryStore(), 0
        return decode_store(dict(row.payload)), int(row.version)

    def save(
        self,
        store: MemoryStore,
        *,
        expected_version: int,
        events: list[DomainEvent],
    ) -> int:
        """Persist the snapshot and enqueue ``events`` in the same transaction."""
        payload = encode_store(store)
        with self.engine.begin() as connection:
            next_version = expected_version + 1
            if expected_version == 0:
                inserted = connection.execute(
                    _INSERT_SNAPSHOT,
                    {"id": SNAPSHOT_ID, "version": next_version, "payload": payload},
                ).rowcount
                if inserted != 1:
                    raise VersionConflictError()
            else:
                updated = connection.execute(
                    _UPDATE_SNAPSHOT,
                    {
                        "id": SNAPSHOT_ID,
                        "version": next_version,
                        "payload": payload,
                        "expected": expected_version,
                    },
                ).rowcount
                if updated != 1:
                    raise VersionConflictError()
            for event in events:
                connection.execute(
                    _INSERT_OUTBOX,
                    {
                        "event_id": event.id,
                        "type": event.type,
                        "aggregate_type": event.aggregate_type,
                        "aggregate_id": event.aggregate_id,
                        "occurred_at": event.occurred_at,
                        "payload": payload_of(event),
                    },
                )
        return next_version

    def pending_outbox(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                text(
                    "SELECT event_id, type, aggregate_type, aggregate_id, occurred_at "
                    "FROM outbox WHERE published_at IS NULL ORDER BY id LIMIT :limit"
                ),
                {"limit": limit},
            ).all()
        return [dict(row._mapping) for row in rows]

    def mark_published(self, event_ids: list[str]) -> int:
        if not event_ids:
            return 0
        with self.engine.begin() as connection:
            result = connection.execute(
                text(
                    "UPDATE outbox SET published_at = now() "
                    "WHERE published_at IS NULL AND event_id = ANY(:ids)"
                ),
                {"ids": event_ids},
            )
        return int(result.rowcount or 0)

    def reset(self) -> None:
        """Test helper: remove every persisted row."""
        with self.engine.begin() as connection:
            connection.execute(text("DELETE FROM outbox"))
            connection.execute(text("DELETE FROM store_snapshots"))

    def now(self) -> datetime | None:
        with self.engine.begin() as connection:
            row = connection.execute(text("SELECT now() AS value")).first()
        return None if row is None else row.value


def payload_of(event: DomainEvent) -> dict[str, Any]:
    return {
        "payload_version": event.payload_version,
        "actor_id": event.actor_id,
        "actor_role": event.actor_role,
        "correlation_id": event.correlation_id,
        "payload": event.payload,
    }
