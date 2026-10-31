from datetime import UTC, datetime

import pytest
from delivery_platform.adapters.memory.clock import DeterministicClock
from delivery_platform.adapters.memory.events import InProcessEventHub
from delivery_platform.adapters.memory.ids import SequentialIds
from delivery_platform.adapters.memory.store import MemoryStore
from delivery_platform.adapters.memory.unit_of_work import MemoryUnitOfWork
from delivery_platform.application.context import CommandContext
from delivery_platform.application.identity import IdentityContext
from delivery_platform.application.lifecycle import LifecycleRecorder
from delivery_platform.domain.entities import (
    DemoIdentity,
    GeoPoint,
    Order,
    OrderItem,
    Restaurant,
)
from delivery_platform.domain.errors import NotFoundError, VersionConflictError
from delivery_platform.domain.events import EventType
from delivery_platform.domain.order_states import OrderState


def _order(order_id: str, *, scenario_id: str | None = None) -> Order:
    return Order(
        id=order_id,
        customer_id="customer_1",
        restaurant_id="rest_1",
        items=[OrderItem(menu_item_id="m1", name="Prato", unit_price_minor=1000, quantity=1)],
        address_id="addr_1",
        address_label="Bairro, cidade",
        state=OrderState.PLACED,
        currency="BRL",
        subtotal_minor=1000,
        discount_minor=0,
        delivery_fee_minor=0,
        total_minor=1000,
        scenario_id=scenario_id,
    )


def _ctx() -> CommandContext:
    return CommandContext(
        identity=IdentityContext(identity_id="customer_1", role="customer"),
        correlation_id="cor_1",
        command_id="cmd_1",
    )


def test_commit_persists_and_rollback_discards():
    store = MemoryStore()
    hub = InProcessEventHub()

    with MemoryUnitOfWork(store, hub) as uow:
        uow.orders.add(_order("order_1"))
        uow.commit()

    assert store.orders["order_1"].id == "order_1"

    with MemoryUnitOfWork(store, hub) as uow:
        uow.orders.add(_order("order_2"))
        uow.rollback()

    assert "order_2" not in store.orders


def test_exception_inside_uow_rolls_back():
    store = MemoryStore()
    hub = InProcessEventHub()

    with pytest.raises(RuntimeError), MemoryUnitOfWork(store, hub) as uow:
        uow.orders.add(_order("order_1"))
        raise RuntimeError("boom")

    assert store.orders == {}


def test_update_checks_stale_versions():
    store = MemoryStore()
    hub = InProcessEventHub()
    store.orders["order_1"] = _order("order_1")

    with MemoryUnitOfWork(store, hub) as uow:
        stale_copy = uow.orders.get("order_1")
        assert stale_copy is not None
        uow.orders.update(stale_copy)  # bumps to version 2
        uow.commit()

    assert store.orders["order_1"].version == 2

    # A second UoW sees the new version; replaying the pre-commit entity conflicts.
    older_copy = _order("order_1")  # version=1, simulating a stale held copy
    with MemoryUnitOfWork(store, hub) as uow, pytest.raises(VersionConflictError):
        uow.orders.update(older_copy)


def test_events_publish_only_after_commit():
    store = MemoryStore()
    hub = InProcessEventHub()
    subscription = hub.subscribe("order_1")
    clock = DeterministicClock(datetime(2026, 9, 1, tzinfo=UTC))
    ids = SequentialIds()

    with MemoryUnitOfWork(store, hub) as uow:
        uow.orders.add(_order("order_1"))
        recorder = LifecycleRecorder(uow=uow, ctx=_ctx(), clock=clock, ids=ids)
        recorder.event(
            EventType.ORDER_PLACED,
            aggregate_type="order",
            aggregate_id="order_1",
            payload={"order_status": "placed"},
        )
        assert subscription.next_event(0.01) is None  # nothing before commit
        uow.commit()

    published = subscription.next_event(0.05)
    assert published is not None
    assert published.type == "order.placed"
    assert published.sequence == 1
    assert published.aggregate_id == "order_1"


def test_failed_command_publishes_nothing():
    store = MemoryStore()
    hub = InProcessEventHub()
    subscription = hub.subscribe("order_1")
    clock = DeterministicClock(datetime(2026, 9, 1, tzinfo=UTC))
    ids = SequentialIds()

    with pytest.raises(RuntimeError), MemoryUnitOfWork(store, hub) as uow:
        recorder = LifecycleRecorder(uow=uow, ctx=_ctx(), clock=clock, ids=ids)
        recorder.event(
            EventType.ORDER_PLACED,
            aggregate_type="order",
            aggregate_id="order_1",
            payload={},
        )
        raise RuntimeError("validation failed")

    assert subscription.next_event(0.01) is None
    assert store.event_log == []


def test_scenario_reset_removes_only_scenario_records():
    store = MemoryStore()
    hub = InProcessEventHub()
    store.orders["sc_order"] = _order("sc_order", scenario_id="lunch-rush")
    store.orders["dyn_order"] = _order("dyn_order")

    with MemoryUnitOfWork(store, hub) as uow:
        uow.scenarios.remove_scenario_records("lunch-rush")
        uow.commit()

    assert "sc_order" not in store.orders
    assert store.orders["dyn_order"].id == "dyn_order"


def test_get_missing_raises_not_found():
    store = MemoryStore()
    hub = InProcessEventHub()

    with MemoryUnitOfWork(store, hub) as uow, pytest.raises(NotFoundError):
        uow.orders.get("missing")


def test_seed_fixture_shape():
    store = MemoryStore()
    store.identities["customer_1"] = DemoIdentity(
        id="customer_1", name="Demo", role="customer"
    )
    store.restaurants["rest_1"] = Restaurant(
        id="rest_1",
        name="Demo Kitchen",
        cuisine="brasileira",
        description="",
        available=True,
        delivery_fee_minor=500,
        location=GeoPoint(latitude=-23.55, longitude=-46.63),
        address_label="Centro, São Paulo",
    )

    assert store.identities["customer_1"].role == "customer"
    assert store.restaurants["rest_1"].available is True
