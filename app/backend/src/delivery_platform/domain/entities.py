"""Milestone 1 domain entities.

Aggregates are plain dataclasses. Mutable aggregates carry a ``version`` for
optimistic conflict detection. Records that can belong to a demo scenario carry
``scenario_id`` so reset can scope to scenario-owned data without touching
dynamic records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from delivery_platform.domain.order_states import OrderState

Role = Literal["customer", "restaurant", "courier", "operations"]
PaymentMethod = Literal["pix", "card", "wallet"]
PaymentStatus = Literal["created", "processing", "approved", "declined", "requires_action", "refunded"]
CourierStatus = Literal["available", "assigned", "delivering", "offline"]
DeliveryStatus = Literal["offered", "assigned", "picked_up", "en_route", "delivered"]
StopKind = Literal["pickup", "dropoff"]


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float


@dataclass
class DemoIdentity:
    """A seeded user known to the server; role switching selects one of these."""

    id: str
    name: str
    role: Role
    market: str = "br"
    restaurant_id: str | None = None
    courier_id: str | None = None


@dataclass
class Restaurant:
    id: str
    name: str
    cuisine: str
    description: str
    available: bool
    delivery_fee_minor: int
    location: GeoPoint
    address_label: str


@dataclass
class MenuItem:
    id: str
    restaurant_id: str
    name: str
    description: str
    category: str
    price_minor: int
    currency: str
    available: bool


@dataclass
class Address:
    id: str
    customer_id: str
    label: str
    formatted: str
    location: GeoPoint


@dataclass
class CartLine:
    id: str
    menu_item_id: str
    quantity: int
    observation: str = ""


@dataclass
class Cart:
    id: str
    customer_id: str
    restaurant_id: str | None = None
    lines: list[CartLine] = field(default_factory=list)
    coupon_code: str | None = None
    version: int = 1
    scenario_id: str | None = None


@dataclass
class Coupon:
    code: str
    description: str
    discount_minor: int
    currency: str
    min_subtotal_minor: int
    active: bool
    expires_at: datetime | None = None


@dataclass
class OrderItem:
    """An immutable snapshot of a menu line taken at checkout."""

    menu_item_id: str
    name: str
    unit_price_minor: int
    quantity: int
    observation: str = ""


@dataclass
class Order:
    id: str
    customer_id: str
    restaurant_id: str
    items: list[OrderItem]
    address_id: str
    address_label: str
    state: OrderState
    currency: str
    subtotal_minor: int
    discount_minor: int
    delivery_fee_minor: int
    total_minor: int
    coupon_code: str | None = None
    payment_attempt_id: str | None = None
    rating: int | None = None
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    scenario_id: str | None = None


@dataclass
class PaymentAttempt:
    """A simulated payment record; safe_reference never holds raw card data."""

    id: str
    order_id: str
    method: PaymentMethod
    status: PaymentStatus
    safe_reference: str
    failure_code: str | None = None
    idempotency_key_hash: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    scenario_id: str | None = None


@dataclass
class CourierProfile:
    id: str
    name: str
    status: CourierStatus
    location: GeoPoint
    version: int = 1


@dataclass
class Delivery:
    """One-to-one link between an order and at most one courier in M1."""

    id: str
    order_id: str
    courier_id: str | None
    status: DeliveryStatus
    version: int = 1
    scenario_id: str | None = None


@dataclass
class RouteStop:
    kind: StopKind
    ref_id: str
    label: str
    location: GeoPoint
    sequence: int


@dataclass
class RouteSegment:
    from_label: str
    to_label: str
    node_path: tuple[str, ...]
    distance_meters: float
    estimated_seconds: float


@dataclass
class RoutePlan:
    id: str
    delivery_id: str
    graph_id: str
    graph_version: str
    stops: list[RouteStop]
    segments: list[RouteSegment]
    geometry: dict[str, Any]
    distance_meters: float
    estimated_seconds: float
    solver_name: str
    solver_version: str
    computation_time_ns: int
    nodes_expanded: int
    warnings: list[str] = field(default_factory=list)
    scenario_id: str | None = None
    objective: str = "time"


@dataclass
class TrackingEvent:
    id: str
    delivery_id: str
    courier_id: str
    sequence: int
    location: GeoPoint
    occurred_at: datetime | None = None
    scenario_id: str | None = None


@dataclass
class Notification:
    id: str
    recipient_id: str
    order_id: str | None
    type: str
    message: str
    read: bool = False
    created_at: datetime | None = None
    scenario_id: str | None = None


@dataclass
class AuditEvent:
    """Append-only actor/action/target history."""

    id: str
    actor_id: str
    actor_role: str
    action: str
    target_type: str
    target_id: str
    detail: str
    correlation_id: str
    occurred_at: datetime | None = None
    scenario_id: str | None = None


@dataclass
class IdempotencyRecord:
    """A stored command result keyed by (identity, key) for safe retries."""

    key: str
    identity_id: str
    request_fingerprint: str
    result: dict[str, Any]
    created_at: datetime | None = None
