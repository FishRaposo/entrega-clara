"""Entity → JSON dict serialization (minor units + currency per contract)."""

from __future__ import annotations

from typing import Any

from delivery_platform.domain.entities import (
    Address,
    AuditEvent,
    CourierProfile,
    Delivery,
    DeliveryBatch,
    MenuItem,
    Notification,
    Order,
    PaymentAttempt,
    Restaurant,
    RoutePlan,
    TrackingEvent,
)
from delivery_platform.domain.events import DomainEvent
from delivery_platform.domain.money import CartTotals


def restaurant_summary(restaurant: Restaurant) -> dict[str, Any]:
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "cuisine": restaurant.cuisine,
        "description": restaurant.description,
        "available": restaurant.available,
        "delivery_fee_minor": restaurant.delivery_fee_minor,
        "address_label": restaurant.address_label,
        "latitude": restaurant.location.latitude,
        "longitude": restaurant.location.longitude,
    }


def menu_item_view(item: MenuItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "restaurant_id": item.restaurant_id,
        "name": item.name,
        "description": item.description,
        "category": item.category,
        "price_minor": item.price_minor,
        "currency": item.currency,
        "available": item.available,
    }


def totals_view(totals: CartTotals) -> dict[str, Any]:
    return {
        "subtotal_minor": totals.subtotal_minor,
        "discount_minor": totals.discount_minor,
        "delivery_fee_minor": totals.delivery_fee_minor,
        "total_minor": totals.total_minor,
        "currency": totals.currency,
    }


def cart_view(cart: Any, totals: CartTotals) -> dict[str, Any]:
    return {
        "id": cart.id,
        "restaurant_id": cart.restaurant_id,
        "coupon_code": cart.coupon_code,
        "version": cart.version,
        "lines": [
            {
                "id": line.id,
                "menu_item_id": line.menu_item_id,
                "quantity": line.quantity,
                "observation": line.observation,
            }
            for line in cart.lines
        ],
        **totals_view(totals),
    }


def address_view(address: Address) -> dict[str, Any]:
    return {
        "id": address.id,
        "label": address.label,
        "formatted": address.formatted,
        "latitude": address.location.latitude,
        "longitude": address.location.longitude,
    }


def payment_view(attempt: PaymentAttempt) -> dict[str, Any]:
    return {
        "id": attempt.id,
        "order_id": attempt.order_id,
        "method": attempt.method,
        "status": attempt.status,
        "safe_reference": attempt.safe_reference,
        "failure_code": attempt.failure_code,
        "created_at": _ts(attempt.created_at),
    }


def order_summary(order: Order) -> dict[str, Any]:
    return {
        "id": order.id,
        "restaurant_id": order.restaurant_id,
        "state": order.state.value,
        "total_minor": order.total_minor,
        "currency": order.currency,
        "version": order.version,
        "created_at": _ts(order.created_at),
    }


def order_view(
    order: Order,
    attempt: PaymentAttempt | None,
    delivery: Delivery | None,
    route: RoutePlan | None,
) -> dict[str, Any]:
    return {
        **order_summary(order),
        "customer_id": order.customer_id,
        "address_label": order.address_label,
        "coupon_code": order.coupon_code,
        "rating": order.rating,
        "subtotal_minor": order.subtotal_minor,
        "discount_minor": order.discount_minor,
        "delivery_fee_minor": order.delivery_fee_minor,
        "items": [
            {
                "menu_item_id": item.menu_item_id,
                "name": item.name,
                "unit_price_minor": item.unit_price_minor,
                "quantity": item.quantity,
                "observation": item.observation,
            }
            for item in order.items
        ],
        "payment": payment_view(attempt) if attempt else None,
        "delivery": delivery_view(delivery) if delivery else None,
        "route": route_view(route) if route else None,
    }


def delivery_view(delivery: Delivery | None) -> dict[str, Any] | None:
    if delivery is None:
        return None
    return {
        "id": delivery.id,
        "order_id": delivery.order_id,
        "courier_id": delivery.courier_id,
        "status": delivery.status,
        "version": delivery.version,
        "batch_id": delivery.batch_id,
    }


def route_view(route: RoutePlan | None) -> dict[str, Any] | None:
    if route is None:
        return None
    return {
        "id": route.id,
        "graph_id": route.graph_id,
        "graph_version": route.graph_version,
        "stops": [
            {
                "kind": stop.kind,
                "ref_id": stop.ref_id,
                "label": stop.label,
                "latitude": stop.location.latitude,
                "longitude": stop.location.longitude,
                "sequence": stop.sequence,
            }
            for stop in route.stops
        ],
        "segments": [
            {
                "from_label": segment.from_label,
                "to_label": segment.to_label,
                "node_path": list(segment.node_path),
                "distance_meters": segment.distance_meters,
                "estimated_seconds": segment.estimated_seconds,
            }
            for segment in route.segments
        ],
        "geometry": route.geometry,
        "distance_meters": route.distance_meters,
        "estimated_seconds": route.estimated_seconds,
        "solver_name": route.solver_name,
        "solver_version": route.solver_version,
        "batch_id": route.batch_id,
        "baseline_solver_name": route.baseline_solver_name,
        "baseline_cost": route.baseline_cost,
        "computation_time_ns": route.computation_time_ns,
        "nodes_expanded": route.nodes_expanded,
        "warnings": route.warnings,
        "objective": route.objective,
    }


def tracking_event_view(event: TrackingEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "delivery_id": event.delivery_id,
        "sequence": event.sequence,
        "latitude": event.location.latitude,
        "longitude": event.location.longitude,
        "occurred_at": _ts(event.occurred_at),
    }


def notification_view(notification: Notification) -> dict[str, Any]:
    return {
        "id": notification.id,
        "order_id": notification.order_id,
        "type": notification.type,
        "message": notification.message,
        "read": notification.read,
        "created_at": _ts(notification.created_at),
    }


def event_view(event: DomainEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "type": event.type,
        "aggregate_type": event.aggregate_type,
        "aggregate_id": event.aggregate_id,
        "actor_id": event.actor_id,
        "actor_role": event.actor_role,
        "correlation_id": event.correlation_id,
        "sequence": event.sequence,
        "occurred_at": _ts(event.occurred_at),
        "payload_version": event.payload_version,
        "payload": event.payload,
    }


def audit_view(audit: AuditEvent) -> dict[str, Any]:
    return {
        "id": audit.id,
        "actor_id": audit.actor_id,
        "actor_role": audit.actor_role,
        "action": audit.action,
        "target_type": audit.target_type,
        "target_id": audit.target_id,
        "detail": audit.detail,
        "correlation_id": audit.correlation_id,
        "occurred_at": _ts(audit.occurred_at),
    }


def courier_view(courier: CourierProfile) -> dict[str, Any]:
    return {
        "id": courier.id,
        "name": courier.name,
        "status": courier.status,
        "latitude": courier.location.latitude,
        "longitude": courier.location.longitude,
        "version": courier.version,
    }


def _ts(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def batch_view(batch: DeliveryBatch | None) -> dict[str, Any] | None:
    if batch is None:
        return None
    return {
        "id": batch.id,
        "courier_id": batch.courier_id,
        "delivery_ids": list(batch.delivery_ids),
        "status": batch.status,
        "created_at": _ts(batch.created_at),
    }
