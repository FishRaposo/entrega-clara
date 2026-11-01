"""One repository contract, two adapters.

The memory adapter is always exercised; the PostgreSQL adapter runs when
``DATABASE_URL`` points at a reachable server (the CI/service path). Without it
the PostgreSQL cases skip with an explicit message instead of pretending to
pass — the verification record says exactly that.

What the contract pins: a committed write is visible to a later unit of work, a
rolled-back one is not, events reach subscribers only after commit, the event
log survives a restart, and PostgreSQL detects a stale write instead of
overwriting it.
"""

import importlib.util
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from delivery_platform.adapters.memory.events import InProcessEventHub
from delivery_platform.adapters.memory.store import MemoryStore
from delivery_platform.adapters.memory.unit_of_work import MemoryUnitOfWork
from delivery_platform.domain.entities import GeoPoint, Order, OrderItem, Restaurant
from delivery_platform.domain.errors import VersionConflictError
from delivery_platform.domain.events import DomainEvent
from delivery_platform.domain.order_states import OrderState

DATABASE_URL = os.environ.get("DATABASE_URL", "")

WORKER_PATH = Path(__file__).resolve().parents[2] / "scripts" / "worker.py"
_worker_spec = importlib.util.spec_from_file_location("outbox_worker", WORKER_PATH)
assert _worker_spec is not None and _worker_spec.loader is not None
worker = importlib.util.module_from_spec(_worker_spec)
_worker_spec.loader.exec_module(worker)


def _postgres():
    if not DATABASE_URL:
        return None
    try:
        from delivery_platform.adapters.postgres.store import PostgresStore

        store = PostgresStore.from_url(DATABASE_URL)
        store.migrate()
        return store
    except Exception:  # noqa: BLE001 - driver missing or server down
        return None


POSTGRES = _postgres()
requires_postgres = pytest.mark.skipif(
    POSTGRES is None,
    reason="DATABASE_URL is not configured or unreachable; PostgreSQL contract unverified",
)


def _restaurant() -> Restaurant:
    return Restaurant(
        id="res_1",
        name="Cantina",
        cuisine="italiana",
        description="",
        available=True,
        delivery_fee_minor=500,
        location=GeoPoint(latitude=-23.55, longitude=-46.65),
        address_label="Rua A",
    )


def _order() -> Order:
    return Order(
        id="ord_1",
        customer_id="cus_1",
        restaurant_id="res_1",
        items=[
            OrderItem(menu_item_id="m1", name="Prato", unit_price_minor=1500, quantity=1)
        ],
        address_id="addr_1",
        address_label="Rua A",
        state=OrderState.PLACED,
        currency="BRL",
        subtotal_minor=1500,
        discount_minor=0,
        delivery_fee_minor=500,
        total_minor=2000,
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )


def _event() -> DomainEvent:
    return DomainEvent(
        id="evt_1",
        type="order.placed",
        aggregate_type="order",
        aggregate_id="ord_1",
        actor_id="cus_1",
        actor_role="customer",
        correlation_id="cor_1",
        sequence=0,
        occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        payload_version=1,
        payload={"order_id": "ord_1"},
    )


@pytest.fixture(params=["memory", "postgres"])
def uow(request) -> Iterator[object]:
    if request.param == "memory":
        store = MemoryStore()
        yield lambda: MemoryUnitOfWork(store, InProcessEventHub())
        return
    if POSTGRES is None:
        pytest.skip("DATABASE_URL is not configured or unreachable")
    from delivery_platform.adapters.postgres.unit_of_work import PostgresUnitOfWork

    POSTGRES.reset()
    boot = MemoryStore()
    yield lambda: PostgresUnitOfWork(POSTGRES, boot, InProcessEventHub())


def test_committed_write_is_visible_to_a_later_unit_of_work(uow):
    with uow() as first:
        first.restaurants.add(_restaurant())
        first.orders.add(_order())
    with uow() as second:
        assert second.orders.get("ord_1").total_minor == 2000
        assert second.restaurants.get("res_1").name == "Cantina"


def test_rollback_discards_everything(uow):
    with pytest.raises(RuntimeError), uow() as transaction:
        transaction.orders.add(_order())
        raise RuntimeError("boom")
    with uow() as after:
        assert after.orders.find("ord_1") is None


def test_events_reach_subscribers_only_after_commit():
    store = MemoryStore()
    hub = InProcessEventHub()
    subscription = hub.subscribe("ord_1")
    transaction = MemoryUnitOfWork(store, hub)
    with transaction as open_transaction:
        open_transaction.event_log.append(_event())
        assert subscription.next_event(0.01) is None, "published before commit"
    assert subscription.next_event(0.01) is not None


def test_event_log_survives_a_restart(uow):
    with uow() as first:
        first.event_log.append(_event())
    with uow() as second:
        stored = second.event_log.list_all()
        assert [event.id for event in stored] == ["evt_1"]
        assert second.event_log.list_since(0)


@requires_postgres
def test_postgres_detects_a_stale_write():
    from delivery_platform.adapters.postgres.unit_of_work import PostgresUnitOfWork

    assert POSTGRES is not None
    POSTGRES.reset()
    boot = MemoryStore()
    first = PostgresUnitOfWork(POSTGRES, boot, InProcessEventHub())
    second = PostgresUnitOfWork(POSTGRES, boot, InProcessEventHub())
    # Both read the same version before either writes.
    first.__enter__()
    second.__enter__()
    try:
        first.orders.add(_order())
        first.commit()
    finally:
        first.rollback()
    second.orders.add(_order())
    with pytest.raises(VersionConflictError):
        second.commit()
    second.rollback()


@requires_postgres
def test_postgres_outbox_recovers_the_commit_publish_window():
    assert POSTGRES is not None
    POSTGRES.reset()
    store, version = POSTGRES.load()
    store.orders["ord_1"] = _order()
    # Simulate a commit whose publisher never ran: snapshot + outbox written,
    # publication missing.
    POSTGRES.save(store, expected_version=version, events=[_event()])
    pending = POSTGRES.pending_outbox()
    assert [row["event_id"] for row in pending] == ["evt_1"]

    published: list[str] = []
    drained = worker.drain_once(
        POSTGRES, publish=lambda rows: published.extend(row["event_id"] for row in rows)
    )
    assert drained == 1
    assert published == ["evt_1"]
    assert POSTGRES.pending_outbox() == []
