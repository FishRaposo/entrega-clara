"""Courier-side commands: availability, offers, delivery lifecycle, locations."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from delivery_platform.application.authorization import require_role
from delivery_platform.application.context import CommandContext
from delivery_platform.application.ports import (
    BatchRouteRequest,
    BatchStopRequest,
    DeliveryRouteRequest,
    UnitOfWork,
)
from delivery_platform.domain.entities import (
    CourierProfile,
    Delivery,
    DeliveryBatch,
    DeliveryStatus,
    GeoPoint,
    RoutePlan,
    TrackingEvent,
)
from delivery_platform.domain.errors import (
    CourierUnavailableError,
    DomainError,
    InvalidOrderTransition,
    NotFoundError,
    OwnershipForbiddenError,
    RouteUnavailableError,
    StaleLocationError,
)
from delivery_platform.domain.events import EventType
from delivery_platform.domain.geo import point_along_polyline
from delivery_platform.domain.order_states import OrderState, transition_order

if TYPE_CHECKING:
    from delivery_platform.application.container import AppContainer

MAX_BATCH_DELIVERIES = 4
PROMISE_DELIVERY_MINUTES = 45


def _batch_stop(uow: UnitOfWork, delivery: Delivery) -> BatchStopRequest:
    """Translate a delivery into a solver-neutral stop with its promise."""
    order = uow.orders.get(delivery.order_id)
    restaurant = uow.restaurants.get(order.restaurant_id)
    address = uow.addresses.get(order.address_id)
    return BatchStopRequest(
        delivery_id=delivery.id,
        pickup_point=restaurant.location,
        pickup_label=restaurant.name,
        dropoff_point=address.location,
        dropoff_label=order.address_label,
        volume=1 if len(order.items) <= 3 else 2,
        picked_up=delivery.status in ("picked_up", "en_route"),
        # The promise is a deadline: the order only reaches this point once the
        # kitchen marked it ready, so there is no release window to wait for.
        promise_start_at=None,
        promise_end_at=(
            order.created_at + timedelta(minutes=PROMISE_DELIVERY_MINUTES)
            if order.created_at is not None
            else None
        ),
    )


class CourierCommands:
    def __init__(self, container: AppContainer) -> None:
        self._container = container

    def set_availability(self, ctx: CommandContext, *, available: bool) -> CourierProfile:
        courier_id = self._courier_id(ctx)
        with self._container.uow() as uow:
            courier = uow.couriers.get(courier_id)
            if not available and uow.deliveries.list_active_by_courier(courier_id):
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
            if uow.deliveries.list_active_by_courier(courier_id):
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

    def batch_accept(self, ctx: CommandContext, delivery_ids: list[str]) -> DeliveryBatch:
        """Accept 2-3 offered deliveries as one optimized tour (ADR 0007).

        The tour is computed at accept time: cost matrix over every stop pair,
        Held-Karp with pickup-before-dropoff precedence.
        """
        courier_id = self._courier_id(ctx)
        unique_ids = list(dict.fromkeys(delivery_ids))
        if not 2 <= len(unique_ids) <= 3 or len(unique_ids) != len(delivery_ids):
            raise DomainError("Um lote aceita de 2 a 3 entregas distintas.")
        with self._container.uow() as uow:
            courier = uow.couriers.get(courier_id)
            if courier.status != "available":
                raise CourierUnavailableError()
            if uow.deliveries.list_active_by_courier(courier_id):
                raise CourierUnavailableError()
            deliveries = [uow.deliveries.get(delivery_id) for delivery_id in unique_ids]
            for delivery in deliveries:
                self._require_delivery_status(delivery, "offered")

            batch = DeliveryBatch(
                id=self._container.ids.new_id("bat"),
                courier_id=courier_id,
                delivery_ids=unique_ids,
                status="assigned",
                created_at=self._container.clock.now(),
                scenario_id=deliveries[0].scenario_id,
            )
            uow.batches.add(batch)

            orders = [uow.orders.get(d.order_id) for d in deliveries]
            route = self._container.route_planner.plan_batch(
                BatchRouteRequest(
                    batch_id=batch.id,
                    courier_location=courier.location,
                    departure_at=self._container.clock.now(),
                    deliveries=tuple(
                        _batch_stop(uow, delivery) for delivery in deliveries
                    ),
                ),
                route_id=self._container.ids.new_id("rpl"),
            )
            route.scenario_id = batch.scenario_id
            uow.route_plans.add(route)

            courier.status = "assigned"
            uow.couriers.update(courier)
            recorder = self._container.recorder(uow, ctx)
            for delivery, order in zip(deliveries, orders, strict=True):
                delivery.courier_id = courier_id
                delivery.status = "assigned"
                delivery.batch_id = batch.id
                order.state = transition_order(order.state, OrderState.COURIER_ASSIGNED)
                order.updated_at = self._container.clock.now()
                uow.deliveries.update(delivery)
                uow.orders.update(order)
                recorder.event(
                    EventType.DELIVERY_ASSIGNED,
                    aggregate_type="delivery",
                    aggregate_id=delivery.id,
                    payload={
                        "order_id": order.id,
                        "courier_id": courier_id,
                        "batch_id": batch.id,
                        "order_status": order.state.value,
                    },
                )
                recorder.notify(
                    order.customer_id,
                    "Um entregador aceitou sua entrega (em lote).",
                    order_id=order.id,
                )
            recorder.audit(
                "delivery.batch_accepted",
                target_type="batch",
                target_id=batch.id,
                detail=f"{len(unique_ids)} entregas, rota {route.id}",
            )
            uow.commit()
            return batch

    def add_to_batch(
        self, ctx: CommandContext, batch_id: str, delivery_id: str
    ) -> RoutePlan:
        """Insert a new order into an active batch and re-plan the remaining stops.

        Only stops still ahead are optimized: a delivery already picked up
        contributes its drop-off alone and its volume starts on board. The
        previous plan is replaced, and a ``route.replanned`` event records the
        delta so the console can show what the change cost.
        """
        courier_id = self._courier_id(ctx)
        with self._container.uow() as uow:
            batch = uow.batches.get(batch_id)
            if batch.courier_id != courier_id:
                raise OwnershipForbiddenError()
            if batch.status not in ("assigned", "en_route"):
                raise DomainError("Este lote não aceita novas entregas.")
            delivery = uow.deliveries.get(delivery_id)
            self._require_delivery_status(delivery, "offered")
            existing = [uow.deliveries.get(item) for item in batch.delivery_ids]
            remaining = [item for item in existing if item.status != "delivered"]
            if len(remaining) + 1 > MAX_BATCH_DELIVERIES:
                raise DomainError("O lote já está no limite de entregas.")
            courier = uow.couriers.get(courier_id)
            previous = uow.route_plans.find_by_batch(batch.id)
            route = self._container.route_planner.plan_batch(
                BatchRouteRequest(
                    batch_id=batch.id,
                    courier_location=courier.location,
                    departure_at=self._container.clock.now(),
                    deliveries=tuple(
                        _batch_stop(uow, item) for item in [*remaining, delivery]
                    ),
                ),
                route_id=self._container.ids.new_id("rpl"),
            )
            route.scenario_id = batch.scenario_id
            uow.route_plans.replace(route)
            batch.delivery_ids = [item.id for item in remaining] + [delivery.id]
            uow.batches.update(batch)
            delivery.courier_id = courier_id
            delivery.status = "assigned"
            delivery.batch_id = batch.id
            uow.deliveries.update(delivery)
            order = uow.orders.get(delivery.order_id)
            order.state = transition_order(order.state, OrderState.COURIER_ASSIGNED)
            order.updated_at = self._container.clock.now()
            uow.orders.update(order)
            recorder = self._container.recorder(uow, ctx)
            recorder.event(
                EventType.ROUTE_REPLANNED,
                aggregate_type="batch",
                aggregate_id=batch.id,
                payload={
                    "batch_id": batch.id,
                    "delivery_id": delivery.id,
                    "stops": len(route.stops),
                    "previous_estimated_seconds": previous.estimated_seconds
                    if previous is not None
                    else None,
                    "estimated_seconds": route.estimated_seconds,
                    "delta_seconds": (
                        route.estimated_seconds - previous.estimated_seconds
                        if previous is not None
                        else None
                    ),
                },
            )
            recorder.audit(
                "delivery.batch_replanned",
                target_type="batch",
                target_id=batch.id,
                detail=f"entrega {delivery.id} inserida, rota {route.id}",
            )
            uow.commit()
            return route

    def pickup(self, ctx: CommandContext, delivery_id: str) -> Delivery:
        # When a batch tour is already en_route, a later pickup stop moves the
        # order straight to en_route (picked_up is still recorded).
        return self._delivery_transition(
            ctx,
            delivery_id,
            current="assigned",
            target="picked_up",
            order_target=OrderState.PICKED_UP,
            event_type=EventType.DELIVERY_PICKED_UP,
            customer_message="O entregador retirou seu pedido.",
            continue_en_route_if_batch_started=True,
        )

    def start_route(self, ctx: CommandContext, delivery_id: str) -> Delivery:
        courier_id = self._courier_id(ctx)
        with self._container.uow() as uow:
            delivery = self._own_delivery(ctx, uow, courier_id, delivery_id)
            if delivery.batch_id:
                return self._start_batch_route(ctx, uow, courier_id, delivery)
            courier = uow.couriers.get(courier_id)
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
                    departure_at=self._container.clock.now(),
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
            if delivery.batch_id:
                siblings = uow.deliveries.list_by_batch(delivery.batch_id)
                if all(s.status == "delivered" or s.id == delivery.id for s in siblings):
                    batch = uow.batches.get(delivery.batch_id)
                    batch.status = "delivered"
                    uow.batches.update(batch)
                    courier.status = "available"
                else:
                    courier.status = "delivering"
            else:
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
        continue_en_route_if_batch_started: bool = False,
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
            batch_moving = (
                continue_en_route_if_batch_started
                and delivery.batch_id is not None
                and uow.batches.get(delivery.batch_id).status == "en_route"
            )
            if batch_moving:
                delivery.status = "en_route"
                order.state = transition_order(order.state, OrderState.EN_ROUTE)
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
            if batch_moving:
                recorder.event(
                    EventType.DELIVERY_EN_ROUTE,
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

    def _start_batch_route(
        self,
        ctx: CommandContext,
        uow: UnitOfWork,
        courier_id: str,
        delivery: Delivery,
    ) -> Delivery:
        """Start a pre-planned batch tour once at least one pickup happened."""
        batch = uow.batches.get(delivery.batch_id or "")
        if batch.status != "assigned":
            raise InvalidOrderTransition(
                "Este lote não pode iniciar a partir do estado atual."
            )
        siblings = uow.deliveries.list_by_batch(batch.id)
        picked_up = [s for s in siblings if s.status == "picked_up"]
        if not picked_up:
            raise InvalidOrderTransition(
                "Retire ao menos um pedido antes de iniciar a rota do lote."
            )
        courier = uow.couriers.get(courier_id)
        batch.status = "en_route"
        courier.status = "delivering"
        uow.batches.update(batch)
        uow.couriers.update(courier)
        recorder = self._container.recorder(uow, ctx)
        for sibling in picked_up:
            sibling.status = "en_route"
            uow.deliveries.update(sibling)
            order = uow.orders.get(sibling.order_id)
            order.state = transition_order(order.state, OrderState.EN_ROUTE)
            order.updated_at = self._container.clock.now()
            uow.orders.update(order)
            recorder.event(
                EventType.DELIVERY_EN_ROUTE,
                aggregate_type="delivery",
                aggregate_id=sibling.id,
                payload={
                    "order_id": order.id,
                    "batch_id": batch.id,
                    "order_status": order.state.value,
                },
            )
            recorder.notify(
                order.customer_id,
                "Seu pedido saiu para entrega.",
                order_id=order.id,
            )
        recorder.audit(
            "delivery.batch_started",
            target_type="batch",
            target_id=batch.id,
            detail=f"{len(picked_up)} de {len(siblings)} retiradas",
        )
        uow.commit()
        return delivery

    def advance_route_location(
        self, ctx: CommandContext, delivery_id: str
    ) -> list[TrackingEvent]:
        """Simulated device GPS: next point along the planned route.

        Position is interpolated along the route polyline at the fraction of
        elapsed deterministic time over the route's estimated seconds — every
        emitted point lies on a route segment. For a batch, the courier's
        position is reported on every in-flight sibling delivery.
        """
        courier_id = self._courier_id(ctx)
        with self._container.uow() as uow:
            anchor = self._own_delivery(ctx, uow, courier_id, delivery_id)
            if anchor.batch_id:
                deliveries = [
                    d
                    for d in uow.deliveries.list_by_batch(anchor.batch_id)
                    if d.status == "en_route"
                ]
                route = uow.route_plans.find_by_batch(anchor.batch_id)
            else:
                deliveries = [anchor] if anchor.status == "en_route" else []
                route = uow.route_plans.find_by_delivery(anchor.id)
            if not deliveries:
                raise InvalidOrderTransition(
                    "Posições só avançam durante a entrega."
                )
            if route is None or not route.geometry.get("coordinates"):
                raise RouteUnavailableError()

            started = next(
                (
                    e.occurred_at
                    for e in uow.event_log.list_for_aggregate(anchor.id)
                    if e.type == EventType.DELIVERY_EN_ROUTE
                ),
                None,
            )
            now = self._container.clock.now()
            elapsed = (
                max(0.0, (now - started).total_seconds()) if started else 0.0
            )
            fraction = elapsed / route.estimated_seconds if route.estimated_seconds > 0 else 1.0
            point = point_along_polyline(route.geometry["coordinates"], fraction)

            courier = uow.couriers.get(courier_id)
            courier.location = point
            uow.couriers.update(courier)
            recorder = self._container.recorder(uow, ctx)
            events: list[TrackingEvent] = []
            for delivery in deliveries:
                sequence = uow.tracking_events.next_sequence(delivery.id)
                event = TrackingEvent(
                    id=self._container.ids.new_id("trk"),
                    delivery_id=delivery.id,
                    courier_id=courier_id,
                    sequence=sequence,
                    location=point,
                    occurred_at=now,
                    scenario_id=delivery.scenario_id,
                )
                uow.tracking_events.add(event)
                recorder.event(
                    EventType.COURIER_LOCATION_UPDATED,
                    aggregate_type="delivery",
                    aggregate_id=delivery.id,
                    payload={
                        "order_id": delivery.order_id,
                        "sequence": sequence,
                        "latitude": point.latitude,
                        "longitude": point.longitude,
                        "simulated": True,
                    },
                )
                events.append(event)
            uow.commit()
            return events
