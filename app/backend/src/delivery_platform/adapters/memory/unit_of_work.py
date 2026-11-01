"""Copy-on-write memory unit of work.

Entering snapshots the shared store; all repository work mutates the private
copy; ``commit`` swaps the copy back and publishes pending events post-commit;
``rollback`` (or exiting with an exception) discards it.
"""

from __future__ import annotations

import copy
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
        sequence_proxy = _SequenceProxy(self)
        self.identities = MemoryIdentities(store.identities)
        self.restaurants = MemoryRestaurants(store.restaurants)
        self.menu_items = MemoryMenuItems(store.menu_items)
        self.addresses = MemoryAddresses(store.addresses)
        self.carts = MemoryCarts(store.carts)
        self.coupons = MemoryCoupons(store.coupons)
        self.orders = MemoryOrders(store.orders)
        self.payment_attempts = MemoryPaymentAttempts(store.payment_attempts)
        self.couriers = MemoryCouriers(store.couriers)
        self.deliveries = MemoryDeliveries(store.deliveries)
        self.batches = MemoryDeliveryBatches(store.batches)
        self.route_plans = MemoryRoutePlans(store.route_plans)
        self.tracking_events = MemoryTrackingEvents(store.tracking_events)
        self.notifications = MemoryNotifications(store.notifications)
        self.audit_events = MemoryAuditEvents(store.audit_events)
        self.event_log = _PublishingEventLog(store.event_log, sequence_proxy, self._pending_events)
        self.idempotency = MemoryIdempotency(store.idempotency)
        self.scenarios = MemoryScenarios(store)


class _SequenceProxy:
    """Gives the event log access to the UoW's working sequence counter."""

    def __init__(self, uow: MemoryUnitOfWork) -> None:
        self._uow = uow

    @property
    def value(self) -> list[int]:
        return self._uow._sequence


class _PublishingEventLog:
    """MemoryEventLog that also queues appended events for post-commit publish."""

    def __init__(
        self,
        events: list[DomainEvent],
        sequence: _SequenceProxy,
        pending: list[DomainEvent],
    ) -> None:
        self._inner = MemoryEventLog(events, sequence.value)
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
