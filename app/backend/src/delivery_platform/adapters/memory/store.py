"""The in-memory data store shared by memory repositories."""

from __future__ import annotations

from dataclasses import dataclass, field

from delivery_platform.domain.entities import (
    Address,
    AuditEvent,
    Cart,
    Coupon,
    CourierProfile,
    Delivery,
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
from delivery_platform.domain.events import DomainEvent


@dataclass
class MemoryStore:
    """All entity collections for one process.

    Unit-of-work snapshots deep-copy this store; commits swap the working copy
    back. Entity IDs are unique within their collection.
    """

    identities: dict[str, DemoIdentity] = field(default_factory=dict)
    restaurants: dict[str, Restaurant] = field(default_factory=dict)
    menu_items: dict[str, MenuItem] = field(default_factory=dict)
    addresses: dict[str, Address] = field(default_factory=dict)
    carts: dict[str, Cart] = field(default_factory=dict)  # keyed by customer_id
    coupons: dict[str, Coupon] = field(default_factory=dict)  # keyed by code
    orders: dict[str, Order] = field(default_factory=dict)
    payment_attempts: dict[str, PaymentAttempt] = field(default_factory=dict)
    couriers: dict[str, CourierProfile] = field(default_factory=dict)
    deliveries: dict[str, Delivery] = field(default_factory=dict)
    route_plans: dict[str, RoutePlan] = field(default_factory=dict)
    tracking_events: list[TrackingEvent] = field(default_factory=list)
    notifications: dict[str, Notification] = field(default_factory=dict)
    audit_events: list[AuditEvent] = field(default_factory=list)
    event_log: list[DomainEvent] = field(default_factory=list)
    event_sequence: int = 0
    idempotency: dict[tuple[str, str], IdempotencyRecord] = field(default_factory=dict)
