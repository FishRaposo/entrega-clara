"""Read-side projections. Reads still go through the unit of work so the
PostgreSQL adapter can satisfy the same shapes later."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from delivery_platform.application.authorization import can_read_order, require_role
from delivery_platform.application.context import CommandContext
from delivery_platform.domain.entities import (
    Address,
    AuditEvent,
    CourierProfile,
    Delivery,
    MenuItem,
    Notification,
    Order,
    PaymentAttempt,
    Restaurant,
    RoutePlan,
    TrackingEvent,
)
from delivery_platform.domain.errors import OwnershipForbiddenError
from delivery_platform.domain.events import DomainEvent
from delivery_platform.domain.order_states import OrderState

if TYPE_CHECKING:
    from delivery_platform.application.container import AppContainer


@dataclass(frozen=True)
class OrderView:
    order: Order
    payment_attempt: PaymentAttempt | None
    delivery: Delivery | None
    route_plan: RoutePlan | None
    tracking: list[TrackingEvent]


class CatalogQueries:
    def __init__(self, container: AppContainer) -> None:
        self._container = container

    def list_restaurants(self, cuisine: str | None = None, query: str | None = None) -> list[Restaurant]:
        with self._container.uow() as uow:
            restaurants = uow.restaurants.list_all()
            uow.rollback()
        if cuisine:
            restaurants = [r for r in restaurants if r.cuisine == cuisine]
        if query:
            needle = query.strip().lower()
            restaurants = [
                r for r in restaurants
                if needle in r.name.lower() or needle in r.cuisine.lower()
            ]
        return restaurants

    def get_restaurant(self, restaurant_id: str) -> Restaurant:
        with self._container.uow() as uow:
            restaurant = uow.restaurants.get(restaurant_id)
            uow.rollback()
            return restaurant

    def get_menu(self, restaurant_id: str) -> list[MenuItem]:
        with self._container.uow() as uow:
            uow.restaurants.get(restaurant_id)
            items = uow.menu_items.list_by_restaurant(restaurant_id)
            uow.rollback()
            return items


class CustomerQueries:
    def __init__(self, container: AppContainer) -> None:
        self._container = container

    def list_addresses(self, ctx: CommandContext) -> list[Address]:
        require_role(ctx.identity, "customer")
        with self._container.uow() as uow:
            addresses = uow.addresses.list_by_customer(ctx.identity.identity_id)
            uow.rollback()
            return addresses

    def list_orders(self, ctx: CommandContext) -> list[Order]:
        require_role(ctx.identity, "customer")
        with self._container.uow() as uow:
            orders = sorted(
                uow.orders.list_by_customer(ctx.identity.identity_id),
                key=lambda o: (o.created_at is not None, o.created_at),
                reverse=True,
            )
            uow.rollback()
            return orders

    def get_order(self, ctx: CommandContext, order_id: str) -> OrderView:
        with self._container.uow() as uow:
            order = uow.orders.get(order_id)
            if not can_read_order(
                ctx.identity, customer_id=order.customer_id, restaurant_id=order.restaurant_id
            ):
                raise OwnershipForbiddenError()
            attempt = (
                uow.payment_attempts.get(order.payment_attempt_id)
                if order.payment_attempt_id
                else None
            )
            delivery = uow.deliveries.find_by_order(order_id)
            route = uow.route_plans.find_by_delivery(delivery.id) if delivery else None
            tracking = uow.tracking_events.list_by_delivery(delivery.id) if delivery else []
            uow.rollback()
            return OrderView(order, attempt, delivery, route, tracking)

    def list_notifications(self, ctx: CommandContext, order_id: str) -> list[Notification]:
        with self._container.uow() as uow:
            order = uow.orders.get(order_id)
            if not can_read_order(
                ctx.identity, customer_id=order.customer_id, restaurant_id=order.restaurant_id
            ):
                raise OwnershipForbiddenError()
            notifications = uow.notifications.list_by_order(order_id)
            uow.rollback()
            return notifications


_QUEUE_STATES = {
    OrderState.PLACED,
    OrderState.CONFIRMED,
    OrderState.PREPARING,
    OrderState.READY_FOR_PICKUP,
    OrderState.COURIER_ASSIGNED,
}

_ACTIVE_DELIVERY_STATUSES = {"assigned", "picked_up", "en_route"}


class RestaurantQueries:
    def __init__(self, container: AppContainer) -> None:
        self._container = container

    def queue(self, ctx: CommandContext) -> list[Order]:
        require_role(ctx.identity, "restaurant")
        if not ctx.identity.restaurant_id:
            return []
        with self._container.uow() as uow:
            orders = [
                order
                for order in uow.orders.list_by_restaurant(ctx.identity.restaurant_id)
                if order.state in _QUEUE_STATES
            ]
            uow.rollback()
            return sorted(
                orders, key=lambda o: o.created_at.timestamp() if o.created_at else 0.0
            )


class CourierQueries:
    def __init__(self, container: AppContainer) -> None:
        self._container = container

    def offers(self, ctx: CommandContext) -> list[Delivery]:
        require_role(ctx.identity, "courier")
        with self._container.uow() as uow:
            offered = uow.deliveries.list_offered()
            uow.rollback()
            return offered

    def active(self, ctx: CommandContext) -> Delivery | None:
        require_role(ctx.identity, "courier")
        if not ctx.identity.courier_id:
            return None
        with self._container.uow() as uow:
            delivery = uow.deliveries.find_active_by_courier(ctx.identity.courier_id)
            uow.rollback()
            return delivery


class OperationsQueries:
    """Read-only operational projections. Operations never mutate."""

    def __init__(self, container: AppContainer) -> None:
        self._container = container

    def list_orders(self, ctx: CommandContext) -> list[Order]:
        require_role(ctx.identity, "operations")
        with self._container.uow() as uow:
            orders = [
                order
                for state in OrderState
                for order in uow.orders.list_by_state(state)
            ]
            uow.rollback()
            return sorted(
                orders, key=lambda o: o.created_at.timestamp() if o.created_at else 0.0
            )

    def get_order(self, ctx: CommandContext, order_id: str) -> OrderView:
        require_role(ctx.identity, "operations")
        with self._container.uow() as uow:
            order = uow.orders.get(order_id)
            attempt = (
                uow.payment_attempts.get(order.payment_attempt_id)
                if order.payment_attempt_id
                else None
            )
            delivery = uow.deliveries.find_by_order(order_id)
            route = uow.route_plans.find_by_delivery(delivery.id) if delivery else None
            tracking = uow.tracking_events.list_by_delivery(delivery.id) if delivery else []
            uow.rollback()
            return OrderView(order, attempt, delivery, route, tracking)

    def list_events(self, ctx: CommandContext, since: int = 0) -> list[DomainEvent]:
        require_role(ctx.identity, "operations")
        with self._container.uow() as uow:
            events = uow.event_log.list_since(since)
            uow.rollback()
            return events

    def list_audit(self, ctx: CommandContext) -> list[AuditEvent]:
        require_role(ctx.identity, "operations")
        with self._container.uow() as uow:
            audit = uow.audit_events.list_all()
            uow.rollback()
            return audit

    def list_couriers(self, ctx: CommandContext) -> list[CourierProfile]:
        require_role(ctx.identity, "operations")
        with self._container.uow() as uow:
            couriers = uow.couriers.list_all()
            uow.rollback()
            return couriers

    def metrics(self, ctx: CommandContext) -> dict[str, object]:
        require_role(ctx.identity, "operations")
        with self._container.uow() as uow:
            orders = [
                order for state in OrderState for order in uow.orders.list_by_state(state)
            ]
            deliveries = [
                delivery
                for order in orders
                if (delivery := uow.deliveries.find_by_order(order.id))
            ]
            routes: list[RoutePlan] = []
            for delivery in deliveries:
                plan = uow.route_plans.find_by_delivery(delivery.id)
                if plan:
                    routes.append(plan)
            attempts = [
                attempt
                for order in orders
                if order.payment_attempt_id
                for attempt in uow.payment_attempts.list_by_order(order.id)
            ]
            couriers = uow.couriers.list_all()
            uow.rollback()
        by_state: dict[str, int] = {}
        for order in orders:
            by_state[order.state.value] = by_state.get(order.state.value, 0) + 1
        courier_status: dict[str, int] = {}
        for courier in couriers:
            courier_status[courier.status] = courier_status.get(courier.status, 0) + 1
        delivery_status: dict[str, int] = {}
        for delivery in deliveries:
            delivery_status[delivery.status] = delivery_status.get(delivery.status, 0) + 1
        total_distance = sum(route.distance_meters for route in routes)
        total_seconds = sum(route.estimated_seconds for route in routes)
        return {
            "orders_total": len(orders),
            "orders_by_state": by_state,
            "deliveries_by_status": delivery_status,
            "payments_approved": sum(1 for a in attempts if a.status == "approved"),
            "payments_declined": sum(1 for a in attempts if a.status == "declined"),
            "couriers_by_status": courier_status,
            "routes_computed": len(routes),
            "route_distance_meters_total": int(total_distance),
            "route_estimated_seconds_total": int(total_seconds),
        }
