"""Committed domain events.

Events describe business facts persisted in the transaction and published only
after commit. The envelope matches the API/event contract: stable ID, type,
aggregate identity, actor/correlation metadata, sequence, UTC timestamp, and a
versioned payload.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class EventType(StrEnum):
    ORDER_PLACED = "order.placed"
    PAYMENT_APPROVED = "payment.approved"
    PAYMENT_DECLINED = "payment.declined"
    ORDER_CONFIRMED = "order.confirmed"
    ORDER_PREPARING = "order.preparing"
    ORDER_READY = "order.ready"
    DELIVERY_ASSIGNED = "delivery.assigned"
    DELIVERY_PICKED_UP = "delivery.picked_up"
    DELIVERY_EN_ROUTE = "delivery.en_route"
    COURIER_LOCATION_UPDATED = "courier.location_updated"
    DELIVERY_DELIVERED = "delivery.delivered"
    NOTIFICATION_CREATED = "notification.created"
    AUDIT_RECORDED = "audit.recorded"
    TRACKING_DELAYED = "tracking.delayed"


@dataclass(frozen=True)
class DomainEvent:
    id: str
    type: str
    aggregate_type: str
    aggregate_id: str
    actor_id: str
    actor_role: str
    correlation_id: str
    sequence: int
    occurred_at: datetime
    payload_version: int
    payload: dict[str, Any] = field(default_factory=dict)
