"""Copy-on-write memory unit of work.

Entering snapshots the shared store; all repository work mutates the private
copy; ``commit`` swaps the copy back and publishes pending events post-commit;
``rollback`` (or exiting with an exception) discards it.

The repository bindings live in ``build_repositories`` so the PostgreSQL adapter
can reuse the exact same repository implementations over its loaded snapshot —
which is what makes "the same contract passes on both adapters" meaningful.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, fields
from typing import Self

from delivery_platform.adapters.memory.events import InProcessEventHub
from delivery_platform.adapters.memory.repositories import (
    MemoryAddresses,
    MemoryAuditEvents,
    MemoryCarts,
    MemoryCoupons,
    MemoryCouriers,
    MemoryDeliveries,
    MemoryDeliveryBatches,
    MemoryEventLog,
    MemoryIdempotency,
    MemoryIdentities,
    MemoryMenuItems,
    MemoryNotifications,
    MemoryOrders,
    MemoryPaymentAttempts,
    MemoryRestaurants,
    MemoryRoutePlans,
    MemoryScenarios,
    MemoryTrackingEvents,
)
from delivery_platform.adapters.memory.store import MemoryStore
from delivery_platform.application.ports import (
    AddressRepository,
    AuditEventRepository,
    CartRepository,
    CouponRepository,
    CourierRepository,
    DeliveryBatchRepository,
    DeliveryRepository,
    EventLogRepository,
    IdempotencyRepository,
    IdentityRepository,
    MenuItemRepository,
    NotificationRepository,
    OrderRepository,
    PaymentAttemptRepository,
    RestaurantRepository,
    RoutePlanRepository,
    ScenarioRepository,
    TrackingEventRepository,
    UnitOfWork,
)
from delivery_platform.domain.events import DomainEvent


@dataclass
class RepositorySet:
    """The eighteen repository ports bound to one ``MemoryStore``."""

    identities: IdentityRepository
    restaurants: RestaurantRepository
    menu_items: MenuItemRepository
    addresses: AddressRepository
    carts: CartRepository
    coupons: CouponRepository
    orders: OrderRepository
    payment_attempts: PaymentAttemptRepository
    couriers: CourierRepository
    deliveries: DeliveryRepository
    batches: DeliveryBatchRepository
    route_plans: RoutePlanRepository
    tracking_events: TrackingEventRepository
    notifications: NotificationRepository
    audit_events: AuditEventRepository
    event_log: EventLogRepository
    idempotency: IdempotencyRepository
    scenarios: ScenarioRepository

    def bind_to(self, target: object) -> None:
        for field in fields(self):
            setattr(target, field.name, getattr(self, field.name))


class _PublishingEventLog:
    """MemoryEventLog that also queues appended events for post-commit publish."""

    def __init__(
        self,
        events: list[DomainEvent],
        sequence: list[int],
        pending: list[DomainEvent],
    ) -> None:
        self._inner = MemoryEventLog(events, sequence)
        self._pending = pending

    def append(self, event: DomainEvent) -> DomainEvent:
        stored = self._inner.append(event)
        self._pending.append(stored)
        return stored

    def list_since(self, sequence: int) -> list[DomainEvent]:
        return self._inner.list_since(sequence)

    def list_for_aggregate(self, aggregate_id: str) -> list[DomainEvent]:
        return self._inner.list_for_aggregate(aggregate_id)

    def list_all(self) -> list[DomainEvent]:
        return self._inner.list_all()


def build_repositories(
    store: MemoryStore, sequence: list[int], pending: list[DomainEvent]
) -> RepositorySet:
    return RepositorySet(
        identities=MemoryIdentities(store.identities),
        restaurants=MemoryRestaurants(store.restaurants),
        menu_items=MemoryMenuItems(store.menu_items),
        addresses=MemoryAddresses(store.addresses),
        carts=MemoryCarts(store.carts),
        coupons=MemoryCoupons(store.coupons),
        orders=MemoryOrders(store.orders),
        payment_attempts=MemoryPaymentAttempts(store.payment_attempts),
        couriers=MemoryCouriers(store.couriers),
        deliveries=MemoryDeliveries(store.deliveries),
        batches=MemoryDeliveryBatches(store.batches),
        route_plans=MemoryRoutePlans(store.route_plans),
        tracking_events=MemoryTrackingEvents(store.tracking_events),
        notifications=MemoryNotifications(store.notifications),
        audit_events=MemoryAuditEvents(store.audit_events),
        event_log=_PublishingEventLog(store.event_log, sequence, pending),
        idempotency=MemoryIdempotency(store.idempotency),
        scenarios=MemoryScenarios(store),
    )


class MemoryUnitOfWork(UnitOfWork):
    def __init__(self, store: MemoryStore, publisher: InProcessEventHub) -> None:
        self._store = store
        self._publisher = publisher
        self._working: MemoryStore | None = None
        self._sequence: list[int] = [0]
        self._pending_events: list[DomainEvent] = []

        self.identities: IdentityRepository
        self.restaurants: RestaurantRepository
        self.menu_items: MenuItemRepository
        self.addresses: AddressRepository
        self.carts: CartRepository
        self.coupons: CouponRepository
        self.orders: OrderRepository
        self.payment_attempts: PaymentAttemptRepository
        self.couriers: CourierRepository
        self.deliveries: DeliveryRepository
        self.batches: DeliveryBatchRepository
        self.route_plans: RoutePlanRepository
        self.tracking_events: TrackingEventRepository
        self.notifications: NotificationRepository
        self.audit_events: AuditEventRepository
        self.event_log: EventLogRepository
        self.idempotency: IdempotencyRepository
        self.scenarios: ScenarioRepository

    def __enter__(self) -> Self:
        self._working = copy.deepcopy(self._store)
        self._sequence = [self._store.event_sequence]
        self._pending_events = []
        self._bind(self._working)
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        if self._working is None:
            return
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self._working = None

    def commit(self) -> None:
        if self._working is None:
            raise RuntimeError("unit of work is not open")
        self._store.identities = self._working.identities
        self._store.restaurants = self._working.restaurants
        self._store.menu_items = self._working.menu_items
        self._store.addresses = self._working.addresses
        self._store.carts = self._working.carts
        self._store.coupons = self._working.coupons
        self._store.orders = self._working.orders
        self._store.payment_attempts = self._working.payment_attempts
        self._store.couriers = self._working.couriers
        self._store.deliveries = self._working.deliveries
        self._store.batches = self._working.batches
        self._store.route_plans = self._working.route_plans
        self._store.tracking_events = self._working.tracking_events
        self._store.notifications = self._working.notifications
        self._store.audit_events = self._working.audit_events
        self._store.event_log = self._working.event_log
        self._store.event_sequence = self._sequence[0]
        self._store.idempotency = self._working.idempotency
        self._working = None
        self._publisher.publish(self._pending_events)
        self._pending_events = []

    def rollback(self) -> None:
        self._working = None
        self._pending_events = []

    def _bind(self, store: MemoryStore) -> None:
        build_repositories(store, self._sequence, self._pending_events).bind_to(self)
