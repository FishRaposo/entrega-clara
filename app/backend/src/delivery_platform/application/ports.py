"""Ports: persistence, provider, and infrastructure contracts.

The application layer depends only on these protocols. Adapters (memory now,
PostgreSQL later) implement them; domain code never sees a storage technology.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Self

from delivery_platform.domain.entities import (
    Address,
    AuditEvent,
    Cart,
    Coupon,
    CourierProfile,
    Delivery,
    DeliveryBatch,
    DemoIdentity,
    GeoPoint,
    IdempotencyRecord,
    MenuItem,
    Notification,
    Order,
    PaymentAttempt,
    PaymentMethod,
    Restaurant,
    RoutePlan,
    TrackingEvent,
)
from delivery_platform.domain.events import DomainEvent
from delivery_platform.domain.order_states import OrderState


class IdentityRepository(Protocol):
    def get(self, identity_id: str) -> DemoIdentity: ...
    def find(self, identity_id: str) -> DemoIdentity | None: ...
    def add(self, identity: DemoIdentity) -> None: ...
    def list_all(self) -> list[DemoIdentity]: ...


class RestaurantRepository(Protocol):
    def get(self, restaurant_id: str) -> Restaurant: ...
    def add(self, restaurant: Restaurant) -> None: ...
    def list_all(self) -> list[Restaurant]: ...


class MenuItemRepository(Protocol):
    def get(self, item_id: str) -> MenuItem: ...
    def find(self, item_id: str) -> MenuItem | None: ...
    def add(self, item: MenuItem) -> None: ...
    def list_by_restaurant(self, restaurant_id: str) -> list[MenuItem]: ...


class AddressRepository(Protocol):
    def get(self, address_id: str) -> Address: ...
    def add(self, address: Address) -> None: ...
    def list_by_customer(self, customer_id: str) -> list[Address]: ...


class CartRepository(Protocol):
    def find_by_customer(self, customer_id: str) -> Cart | None: ...
    def add(self, cart: Cart) -> None: ...
    def update(self, cart: Cart) -> None: ...


class CouponRepository(Protocol):
    def find(self, code: str) -> Coupon | None: ...
    def add(self, coupon: Coupon) -> None: ...


class OrderRepository(Protocol):
    def get(self, order_id: str) -> Order: ...
    def find(self, order_id: str) -> Order | None: ...
    def add(self, order: Order) -> None: ...
    def update(self, order: Order) -> None: ...
    def list_by_customer(self, customer_id: str) -> list[Order]: ...
    def list_by_restaurant(self, restaurant_id: str) -> list[Order]: ...
    def list_by_state(self, state: OrderState) -> list[Order]: ...


class PaymentAttemptRepository(Protocol):
    def get(self, attempt_id: str) -> PaymentAttempt: ...
    def add(self, attempt: PaymentAttempt) -> None: ...
    def update(self, attempt: PaymentAttempt) -> None: ...
    def list_by_order(self, order_id: str) -> list[PaymentAttempt]: ...


class CourierRepository(Protocol):
    def get(self, courier_id: str) -> CourierProfile: ...
    def find(self, courier_id: str) -> CourierProfile | None: ...
    def add(self, courier: CourierProfile) -> None: ...
    def update(self, courier: CourierProfile) -> None: ...
    def list_all(self) -> list[CourierProfile]: ...


class DeliveryRepository(Protocol):
    def get(self, delivery_id: str) -> Delivery: ...
    def find(self, delivery_id: str) -> Delivery | None: ...
    def add(self, delivery: Delivery) -> None: ...
    def update(self, delivery: Delivery) -> None: ...
    def find_by_order(self, order_id: str) -> Delivery | None: ...
    def find_active_by_courier(self, courier_id: str) -> Delivery | None: ...
    def list_active_by_courier(self, courier_id: str) -> list[Delivery]: ...
    def list_offered(self) -> list[Delivery]: ...
    def list_by_batch(self, batch_id: str) -> list[Delivery]: ...


class DeliveryBatchRepository(Protocol):
    def get(self, batch_id: str) -> DeliveryBatch: ...
    def add(self, batch: DeliveryBatch) -> None: ...
    def update(self, batch: DeliveryBatch) -> None: ...
    def find_active_by_courier(self, courier_id: str) -> DeliveryBatch | None: ...


class RoutePlanRepository(Protocol):
    def get(self, plan_id: str) -> RoutePlan: ...
    def add(self, plan: RoutePlan) -> None: ...
    #: Swap the plan stored for a batch (dynamic re-planning).
    def replace(self, plan: RoutePlan) -> None: ...
    def find_by_delivery(self, delivery_id: str) -> RoutePlan | None: ...
    def find_by_batch(self, batch_id: str) -> RoutePlan | None: ...


class TrackingEventRepository(Protocol):
    def add(self, event: TrackingEvent) -> None: ...
    def list_by_delivery(self, delivery_id: str) -> list[TrackingEvent]: ...
    def next_sequence(self, delivery_id: str) -> int: ...
    def latest(self, delivery_id: str) -> TrackingEvent | None: ...


class NotificationRepository(Protocol):
    def add(self, notification: Notification) -> None: ...
    def list_by_recipient(self, recipient_id: str) -> list[Notification]: ...
    def list_by_order(self, order_id: str) -> list[Notification]: ...


class AuditEventRepository(Protocol):
    def add(self, event: AuditEvent) -> None: ...
    def list_all(self) -> list[AuditEvent]: ...
    def list_by_target(self, target_type: str, target_id: str) -> list[AuditEvent]: ...


class EventLogRepository(Protocol):
    """Append-only store of committed domain events."""

    def append(self, event: DomainEvent) -> DomainEvent: ...
    def list_since(self, sequence: int) -> list[DomainEvent]: ...
    def list_for_aggregate(self, aggregate_id: str) -> list[DomainEvent]: ...
    def list_all(self) -> list[DomainEvent]: ...


class IdempotencyRepository(Protocol):
    def find(self, identity_id: str, key: str) -> IdempotencyRecord | None: ...
    def add(self, record: IdempotencyRecord) -> None: ...


class ScenarioRepository(Protocol):
    """Scenario-scoped reset support: removes records owned by one scenario."""

    def remove_scenario_records(self, scenario_id: str) -> None: ...


class UnitOfWork(Protocol):
    """One transaction: aggregate changes + audit + notification + event intent."""

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

    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


class PaymentGateway(Protocol):
    """Deterministic simulated gateway for M1."""

    def create_attempt(
        self,
        *,
        attempt_id: str,
        order_id: str,
        method: PaymentMethod,
        amount_minor: int,
        currency: str,
        simulate_outcome: str | None,
        idempotency_key_hash: str | None,
        now: datetime,
    ) -> PaymentAttempt: ...


class EventPublisher(Protocol):
    """Post-commit, in-process publication for M1."""

    def publish(self, events: list[DomainEvent]) -> None: ...


@dataclass(frozen=True)
class DeliveryRouteRequest:
    """Solver-neutral inputs for a two-leg courier route."""

    delivery_id: str
    courier_location: GeoPoint
    pickup_point: GeoPoint
    pickup_label: str
    dropoff_point: GeoPoint
    dropoff_label: str
    #: When set, the planner prices travel with the traffic profile at this time.
    departure_at: datetime | None = None


@dataclass(frozen=True)
class BatchStopRequest:
    """One delivery inside a batch: its pickup and drop-off points."""

    delivery_id: str
    pickup_point: GeoPoint
    pickup_label: str
    dropoff_point: GeoPoint
    dropoff_label: str
    #: Capacity units carried from pickup to drop-off (bags, boxes).
    volume: int = 1
    #: Already on board (dynamic re-plan): only the drop-off is scheduled.
    picked_up: bool = False
    #: Promise window on the drop-off; honoured only when the batch has a departure.
    promise_start_at: datetime | None = None
    promise_end_at: datetime | None = None


@dataclass(frozen=True)
class BatchRouteRequest:
    """Solver-neutral inputs for a multi-stop courier tour (ADR 0007)."""

    batch_id: str
    courier_location: GeoPoint
    deliveries: tuple[BatchStopRequest, ...]
    #: When set, matrix cells and legs are priced with the traffic profile.
    departure_at: datetime | None = None
    #: Hard capacity (sum of volumes on board at any time).
    capacity: int = 3
    #: Lateness the dispatcher is willing to accept; 0 makes windows hard.
    max_lateness_seconds: float = 0.0


class DeliveryRoutePlanner(Protocol):
    """Computes a provider-neutral route plan for a delivery."""

    def plan(self, request: DeliveryRouteRequest, *, route_id: str) -> RoutePlan: ...

    def plan_batch(self, request: BatchRouteRequest, *, route_id: str) -> RoutePlan: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self, prefix: str) -> str: ...
