"""Courier-side commands: availability, offers, delivery lifecycle, locations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from delivery_platform.application.authorization import require_role
from delivery_platform.application.context import CommandContext
from delivery_platform.application.ports import DeliveryRouteRequest, UnitOfWork
from delivery_platform.domain.entities import (
    CourierProfile,
    Delivery,
    DeliveryStatus,
    GeoPoint,
    TrackingEvent,
)
from delivery_platform.domain.errors import (
    CourierUnavailableError,
    InvalidOrderTransition,
    NotFoundError,
    OwnershipForbiddenError,
    StaleLocationError,
)
from delivery_platform.domain.events import EventType
from delivery_platform.domain.order_states import OrderState, transition_order

if TYPE_CHECKING:
    from delivery_platform.application.container import AppContainer

class CourierCommands:
    def __init__(self, container: AppContainer) -> None:
        self._container = container

    def set_availability(self, ctx: CommandContext, *, available: bool) -> CourierProfile:
        courier_id = self._courier_id(ctx)
        with self._container.uow() as uow:
            courier = uow.couriers.get(courier_id)
            if not available and uow.deliveries.find_active_by_courier(courier_id) is not None:
                raise CourierUnavailableError()
            courier.status = "available" if available else "offline"
            uow.couriers.update(courier)
            self._container.recorder(uow, ctx).audit(
                "courier.availability_changed",
                target_type="courier",
                target_id=courier.id,
                detail=courier.status,
            )
            uow.commit()
            return courier

    def accept(self, ctx: CommandContext, delivery_id: str) -> Delivery:
        courier_id = self._courier_id(ctx)
        with self._container.uow() as uow:
            courier = uow.couriers.get(courier_id)
            if courier.status != "available":
                raise CourierUnavailableError()
            delivery = uow.deliveries.get(delivery_id)
            self._require_delivery_status(delivery, "offered")
            if uow.deliveries.find_active_by_courier(courier_id) is not None:
                raise CourierUnavailableError()
            order = uow.orders.get(delivery.order_id)
            delivery.courier_id = courier_id
            delivery.status = "assigned"
            courier.status = "assigned"
            order.state = transition_order(order.state, OrderState.COURIER_ASSIGNED)
            order.updated_at = self._container.clock.now()
            uow.deliveries.update(delivery)
            uow.couriers.update(courier)
            uow.orders.update(order)
            recorder = self._container.recorder(uow, ctx)
            recorder.event(
                EventType.DELIVERY_ASSIGNED,
                aggregate_type="delivery",
                aggregate_id=delivery.id,
                payload={
                    "order_id": order.id,
                    "courier_id": courier_id,
                    "order_status": order.state.value,
                },
            )
            recorder.audit(
                "delivery.accepted",
                target_type="delivery",
                target_id=delivery.id,
                detail=f"pedido {order.id}",
            )
            recorder.notify(
                order.customer_id,
                "Um entregador aceitou sua entrega.",
                order_id=order.id,
            )
            uow.commit()
            return delivery

    def pickup(self, ctx: CommandContext, delivery_id: str) -> Delivery:
        return self._delivery_transition(
            ctx,
            delivery_id,
            current="assigned",
            target="picked_up",
            order_target=OrderState.PICKED_UP,
            event_type=EventType.DELIVERY_PICKED_UP,
            customer_message="O entregador retirou seu pedido.",
        )

    def start_route(self, ctx: CommandContext, delivery_id: str) -> Delivery:
        courier_id = self._courier_id(ctx)
        with self._container.uow() as uow:
            courier = uow.couriers.get(courier_id)
            delivery = self._own_delivery(ctx, uow, courier_id, delivery_id)
            self._require_delivery_status(delivery, "picked_up")
            order = uow.orders.get(delivery.order_id)
            restaurant = uow.restaurants.get(order.restaurant_id)
            address = uow.addresses.get(order.address_id)
            route = self._container.route_planner.plan(
                DeliveryRouteRequest(
                    delivery_id=delivery.id,
                    courier_location=courier.location,
                    pickup_point=restaurant.location,
                    pickup_label=restaurant.name,
                    dropoff_point=address.location,
                    dropoff_label=order.address_label,
                ),
                route_id=self._container.ids.new_id("rpl"),
            )
            route.scenario_id = delivery.scenario_id
            uow.route_plans.add(route)
            delivery.status = "en_route"
            courier.status = "delivering"
            order.state = transition_order(order.state, OrderState.EN_ROUTE)
            order.updated_at = self._container.clock.now()
            uow.deliveries.update(delivery)
            uow.couriers.update(courier)
            uow.orders.update(order)
            recorder = self._container.recorder(uow, ctx)
            recorder.event(
                EventType.DELIVERY_EN_ROUTE,
                aggregate_type="delivery",
                aggregate_id=delivery.id,
                payload={
                    "order_id": order.id,
                    "route_plan_id": route.id,
                    "order_status": order.state.value,
                },
            )
            recorder.audit(
                "delivery.started",
                target_type="delivery",
                target_id=delivery.id,
                detail=f"rota {route.id}",
            )
            recorder.notify(
                order.customer_id,
                "Seu pedido saiu para entrega.",
                order_id=order.id,
            )
            uow.commit()
            return delivery

    def update_location(
        self,
        ctx: CommandContext,
        *,
        delivery_id: str,
        sequence: int,
        latitude: float,
        longitude: float,
    ) -> TrackingEvent:
        courier_id = self._courier_id(ctx)
        with self._container.uow() as uow:
            delivery = self._own_delivery(ctx, uow, courier_id, delivery_id)
            if delivery.status not in {"picked_up", "en_route"}:
                raise InvalidOrderTransition(
                    "Posições só podem ser enviadas durante a entrega."
                )
            latest = uow.tracking_events.latest(delivery.id)
            if latest is not None and sequence <= latest.sequence:
                raise StaleLocationError()
            point = GeoPoint(latitude=latitude, longitude=longitude)
            event = TrackingEvent(
                id=self._container.ids.new_id("trk"),
                delivery_id=delivery.id,
                courier_id=courier_id,
                sequence=sequence,
                location=point,
                occurred_at=self._container.clock.now(),
                scenario_id=delivery.scenario_id,
            )
            uow.tracking_events.add(event)
            courier = uow.couriers.get(courier_id)
            courier.location = point
            uow.couriers.update(courier)
            recorder = self._container.recorder(uow, ctx)
            recorder.event(
                EventType.COURIER_LOCATION_UPDATED,
                aggregate_type="delivery",
                aggregate_id=delivery.id,
                payload={
                    "order_id": delivery.order_id,
                    "sequence": sequence,
                    "latitude": latitude,
                    "longitude": longitude,
                },
            )
            uow.commit()
            return event

    def complete(self, ctx: CommandContext, delivery_id: str) -> Delivery:
        courier_id = self._courier_id(ctx)
        with self._container.uow() as uow:
            delivery = self._own_delivery(ctx, uow, courier_id, delivery_id)
            self._require_delivery_status(delivery, "en_route")
            order = uow.orders.get(delivery.order_id)
            courier = uow.couriers.get(courier_id)
            delivery.status = "delivered"
            courier.status = "available"
            order.state = transition_order(order.state, OrderState.DELIVERED)
            order.updated_at = self._container.clock.now()
            uow.deliveries.update(delivery)
            uow.couriers.update(courier)
            uow.orders.update(order)
            recorder = self._container.recorder(uow, ctx)
            recorder.event(
                EventType.DELIVERY_DELIVERED,
                aggregate_type="delivery",
                aggregate_id=delivery.id,
                payload={"order_id": order.id, "order_status": order.state.value},
            )
            recorder.audit(
                "delivery.completed",
                target_type="delivery",
                target_id=delivery.id,
                detail=f"pedido {order.id}",
            )
            recorder.notify(
                order.customer_id,
                "Pedido entregue. Bom apetite!",
                order_id=order.id,
            )
            uow.commit()
            return delivery

    def _delivery_transition(
        self,
        ctx: CommandContext,
        delivery_id: str,
        *,
        current: DeliveryStatus,
        target: DeliveryStatus,
        order_target: OrderState,
        event_type: EventType,
        customer_message: str,
    ) -> Delivery:
        courier_id = self._courier_id(ctx)
        with self._container.uow() as uow:
            delivery = self._own_delivery(ctx, uow, courier_id, delivery_id)
            self._require_delivery_status(delivery, current)
            order = uow.orders.get(delivery.order_id)
            delivery.status = target
            courier = uow.couriers.get(courier_id)
            if target == "picked_up":
                courier.status = "delivering"
            order.state = transition_order(order.state, order_target)
            order.updated_at = self._container.clock.now()
            uow.deliveries.update(delivery)
            uow.couriers.update(courier)
            uow.orders.update(order)
            recorder = self._container.recorder(uow, ctx)
            recorder.event(
                event_type,
                aggregate_type="delivery",
                aggregate_id=delivery.id,
                payload={"order_id": order.id, "order_status": order.state.value},
            )
            recorder.audit(
                f"delivery.{target}",
                target_type="delivery",
                target_id=delivery.id,
                detail=f"pedido {order.id}",
            )
            recorder.notify(order.customer_id, customer_message, order_id=order.id)
            uow.commit()
            return delivery

    @staticmethod
    def _courier_id(ctx: CommandContext) -> str:
        require_role(ctx.identity, "courier")
        if not ctx.identity.courier_id:
            raise CourierUnavailableError()
        return ctx.identity.courier_id

    @staticmethod
    def _own_delivery(
        ctx: CommandContext, uow: UnitOfWork, courier_id: str, delivery_id: str
    ) -> Delivery:
        delivery = uow.deliveries.find(delivery_id)
        if delivery is None:
            raise NotFoundError("entrega")
        if delivery.courier_id != courier_id:
            raise OwnershipForbiddenError()
        return delivery

    @staticmethod
    def _require_delivery_status(delivery: Delivery, expected: str) -> None:
        if delivery.status != expected:
            raise InvalidOrderTransition(
                "Esta entrega não pode avançar a partir do estado atual."
            )
