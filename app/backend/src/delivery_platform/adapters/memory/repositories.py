"""In-memory repository implementations bound to a working-store snapshot."""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar

from delivery_platform.domain.entities import (
    Address,
    AuditEvent,
    Cart,
    Coupon,
    CourierProfile,
    Delivery,
    DeliveryBatch,
    DemoIdentity,
    IdempotencyRecord,
    MenuItem,
    Notification,
    Order,
    PaymentAttempt,
    Restaurant,
    RoutePlan,
    TrackingEvent,
)
from delivery_platform.domain.errors import NotFoundError, VersionConflictError
from delivery_platform.domain.events import DomainEvent
from delivery_platform.domain.order_states import OrderState


class _HasId(Protocol):
    id: str


class _Versioned(_HasId, Protocol):
    version: int


E = TypeVar("E", bound=_HasId)
V = TypeVar("V", bound=_Versioned)


class MemoryRepository(Generic[E]):
    """Dict-backed collection with find/get semantics."""

    resource_name = "registro"

    def __init__(self, data: dict[str, E]) -> None:
        self._data = data

    def add(self, entity: E) -> None:
        if entity.id in self._data:
            raise ValueError(f"duplicate id: {entity.id}")
        self._data[entity.id] = entity

    def get(self, entity_id: str) -> E:
        try:
            return self._data[entity_id]
        except KeyError:
            raise NotFoundError(self.resource_name) from None

    def find(self, entity_id: str) -> E | None:
        return self._data.get(entity_id)

    def list_all(self) -> list[E]:
        return list(self._data.values())


class MemoryVersionedRepository(MemoryRepository[V], Generic[V]):
    """Adds optimistic version checking on update."""

    def update(self, entity: V) -> None:
        stored = self._data.get(entity.id)
        if stored is None:
            raise NotFoundError(self.resource_name)
        if stored is not entity and stored.version != entity.version:
            raise VersionConflictError()
        entity.version += 1
        self._data[entity.id] = entity


class MemoryIdentities(MemoryRepository[DemoIdentity]):
    resource_name = "identidade"


class MemoryRestaurants(MemoryRepository[Restaurant]):
    resource_name = "restaurante"


class MemoryMenuItems(MemoryRepository[MenuItem]):
    resource_name = "item do cardápio"

    def list_by_restaurant(self, restaurant_id: str) -> list[MenuItem]:
        return [item for item in self._data.values() if item.restaurant_id == restaurant_id]


class MemoryAddresses(MemoryRepository[Address]):
    resource_name = "endereço"

    def list_by_customer(self, customer_id: str) -> list[Address]:
        return [a for a in self._data.values() if a.customer_id == customer_id]


class MemoryCarts:
    def __init__(self, data: dict[str, Cart]) -> None:
        self._data = data  # keyed by customer_id

    def find_by_customer(self, customer_id: str) -> Cart | None:
        return self._data.get(customer_id)

    def add(self, cart: Cart) -> None:
        self._data[cart.customer_id] = cart

    def update(self, cart: Cart) -> None:
        stored = self._data.get(cart.customer_id)
        if stored is None:
            raise NotFoundError("carrinho")
        if stored is not cart and stored.version != cart.version:
            raise VersionConflictError()
        cart.version += 1
        self._data[cart.customer_id] = cart


class MemoryCoupons:
    def __init__(self, data: dict[str, Coupon]) -> None:
        self._data = data

    def find(self, code: str) -> Coupon | None:
        return self._data.get(code.strip().upper())

    def add(self, coupon: Coupon) -> None:
        self._data[coupon.code.strip().upper()] = coupon


class MemoryOrders(MemoryVersionedRepository[Order]):
    resource_name = "pedido"

    def list_by_customer(self, customer_id: str) -> list[Order]:
        return [o for o in self._data.values() if o.customer_id == customer_id]

    def list_by_restaurant(self, restaurant_id: str) -> list[Order]:
        return [o for o in self._data.values() if o.restaurant_id == restaurant_id]

    def list_by_state(self, state: OrderState) -> list[Order]:
        return [o for o in self._data.values() if o.state == state]


class MemoryPaymentAttempts(MemoryRepository[PaymentAttempt]):
    resource_name = "tentativa de pagamento"

    def update(self, attempt: PaymentAttempt) -> None:
        if attempt.id not in self._data:
            raise NotFoundError(self.resource_name)
        self._data[attempt.id] = attempt

    def list_by_order(self, order_id: str) -> list[PaymentAttempt]:
        return [p for p in self._data.values() if p.order_id == order_id]


class MemoryCouriers(MemoryVersionedRepository[CourierProfile]):
    resource_name = "entregador"


_ACTIVE_DELIVERY_STATUSES = {"offered", "assigned", "picked_up", "en_route"}


class MemoryDeliveries(MemoryVersionedRepository[Delivery]):
    resource_name = "entrega"

    def find_by_order(self, order_id: str) -> Delivery | None:
        return next((d for d in self._data.values() if d.order_id == order_id), None)

    def find_active_by_courier(self, courier_id: str) -> Delivery | None:
        return next(
            (
                d
                for d in self._data.values()
                if d.courier_id == courier_id and d.status in _ACTIVE_DELIVERY_STATUSES
            ),
            None,
        )

    def list_active_by_courier(self, courier_id: str) -> list[Delivery]:
        return [
            d
            for d in self._data.values()
            if d.courier_id == courier_id and d.status in _ACTIVE_DELIVERY_STATUSES
        ]

    def list_offered(self) -> list[Delivery]:
        return [d for d in self._data.values() if d.status == "offered"]

    def list_by_batch(self, batch_id: str) -> list[Delivery]:
        return [d for d in self._data.values() if d.batch_id == batch_id]


_ACTIVE_BATCH_STATUSES = {"assigned", "en_route"}


class MemoryDeliveryBatches(MemoryVersionedRepository[DeliveryBatch]):
    resource_name = "lote de entrega"

    def find_active_by_courier(self, courier_id: str) -> DeliveryBatch | None:
        return next(
            (
                b
                for b in self._data.values()
                if b.courier_id == courier_id and b.status in _ACTIVE_BATCH_STATUSES
            ),
            None,
        )


class MemoryRoutePlans(MemoryRepository[RoutePlan]):
    resource_name = "rota"

    def find_by_delivery(self, delivery_id: str) -> RoutePlan | None:
        return next((p for p in self._data.values() if p.delivery_id == delivery_id), None)

    def find_by_batch(self, batch_id: str) -> RoutePlan | None:
        return next((p for p in self._data.values() if p.batch_id == batch_id), None)


class MemoryTrackingEvents:
    def __init__(self, events: list[TrackingEvent]) -> None:
        self._events = events

    def add(self, event: TrackingEvent) -> None:
        self._events.append(event)

    def list_by_delivery(self, delivery_id: str) -> list[TrackingEvent]:
        return sorted(
            (e for e in self._events if e.delivery_id == delivery_id),
            key=lambda e: e.sequence,
        )

    def next_sequence(self, delivery_id: str) -> int:
        return len(self.list_by_delivery(delivery_id)) + 1

    def latest(self, delivery_id: str) -> TrackingEvent | None:
        events = self.list_by_delivery(delivery_id)
        return events[-1] if events else None


class MemoryNotifications(MemoryRepository[Notification]):
    resource_name = "notificação"

    def list_by_recipient(self, recipient_id: str) -> list[Notification]:
        return [n for n in self._data.values() if n.recipient_id == recipient_id]

    def list_by_order(self, order_id: str) -> list[Notification]:
        return [n for n in self._data.values() if n.order_id == order_id]


class MemoryAuditEvents:
    def __init__(self, events: list[AuditEvent]) -> None:
        self._events = events

    def add(self, event: AuditEvent) -> None:
        self._events.append(event)

    def list_all(self) -> list[AuditEvent]:
        return list(self._events)

    def list_by_target(self, target_type: str, target_id: str) -> list[AuditEvent]:
        return [
            e for e in self._events if e.target_type == target_type and e.target_id == target_id
        ]


class MemoryEventLog:
    """Append-only event store assigning a monotonic sequence."""

    def __init__(self, events: list[DomainEvent], sequence: list[int]) -> None:
        self._events = events
        self._sequence = sequence  # single-element list: mutable shared counter

    def append(self, event: DomainEvent) -> DomainEvent:
        self._sequence[0] += 1
        stored = DomainEvent(
            id=event.id,
            type=event.type,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            actor_id=event.actor_id,
            actor_role=event.actor_role,
            correlation_id=event.correlation_id,
            sequence=self._sequence[0],
            occurred_at=event.occurred_at,
            payload_version=event.payload_version,
            payload=event.payload,
        )
        self._events.append(stored)
        return stored

    def list_since(self, sequence: int) -> list[DomainEvent]:
        return [e for e in self._events if e.sequence > sequence]

    def list_for_aggregate(self, aggregate_id: str) -> list[DomainEvent]:
        return [e for e in self._events if e.aggregate_id == aggregate_id]

    def list_all(self) -> list[DomainEvent]:
        return list(self._events)


class MemoryIdempotency:
    def __init__(self, data: dict[tuple[str, str], IdempotencyRecord]) -> None:
        self._data = data

    def find(self, identity_id: str, key: str) -> IdempotencyRecord | None:
        return self._data.get((identity_id, key))

    def add(self, record: IdempotencyRecord) -> None:
        self._data[(record.identity_id, record.key)] = record


class MemoryScenarios:
    """Removes records owned by one scenario without touching dynamic data."""

    def __init__(self, store: MemoryStoreView) -> None:
        self._store = store

    def remove_scenario_records(self, scenario_id: str) -> None:
        store = self._store
        for collection in (
            store.orders,
            store.payment_attempts,
            store.deliveries,
            store.route_plans,
            store.notifications,
            store.carts,
        ):
            for key in [
                key for key, record in collection.items() if record.scenario_id == scenario_id
            ]:
                del collection[key]
        store.tracking_events[:] = [
            e for e in store.tracking_events if e.scenario_id != scenario_id
        ]
        store.audit_events[:] = [
            e for e in store.audit_events if e.scenario_id != scenario_id
        ]
        store.event_log[:] = [
            e for e in store.event_log if e.payload.get("_scenario_id") != scenario_id
        ]


class MemoryStoreView(Protocol):
    """The store shape the scenario repository needs."""

    orders: dict[str, Order]
    payment_attempts: dict[str, PaymentAttempt]
    deliveries: dict[str, Delivery]
    route_plans: dict[str, RoutePlan]
    notifications: dict[str, Notification]
    carts: dict[str, Cart]
    tracking_events: list[TrackingEvent]
    audit_events: list[AuditEvent]
    event_log: list[DomainEvent]
