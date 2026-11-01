"""PostgreSQL unit of work: load the snapshot, work in memory, commit atomically.

Exiting with an exception (or calling ``rollback``) discards the working copy and
touches nothing. ``commit`` writes the snapshot and the outbox in one
transaction guarded by the version it loaded; a stale version raises
``VersionConflictError`` instead of overwriting a concurrent commit. Events are
published only after the commit returns, and marked published only after the
publisher accepted them — a crash in between leaves them in the outbox for the
worker to drain (at-least-once).
"""

from __future__ import annotations

from typing import Self

from delivery_platform.adapters.memory.events import InProcessEventHub
from delivery_platform.adapters.memory.store import MemoryStore
from delivery_platform.adapters.memory.unit_of_work import build_repositories
from delivery_platform.adapters.postgres.store import PostgresStore, adopt_store
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


class PostgresUnitOfWork(UnitOfWork):
    def __init__(
        self, store: PostgresStore, boot: MemoryStore, publisher: InProcessEventHub
    ) -> None:
        self._store = store
        self._boot = boot
        self._publisher = publisher
        self._working: MemoryStore | None = None
        self._version = 0
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
        self._working, self._version = self._store.load()
        self._sequence = [self._working.event_sequence]
        self._pending_events = []
        build_repositories(self._working, self._sequence, self._pending_events).bind_to(self)
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
        self._working.event_sequence = self._sequence[0]
        events = list(self._pending_events)
        self._version = self._store.save(
            self._working, expected_version=self._version, events=events
        )
        adopt_store(self._boot, self._working)
        self._working = None
        self._publisher.publish(events)
        self._store.mark_published([event.id for event in events])
        self._pending_events = []

    def rollback(self) -> None:
        self._working = None
        self._pending_events = []
