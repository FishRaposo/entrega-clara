"""Restaurant-side order commands: confirm, prepare, mark ready."""

from __future__ import annotations

from typing import TYPE_CHECKING

from delivery_platform.application.authorization import require_restaurant_operator
from delivery_platform.application.context import CommandContext
from delivery_platform.application.ports import UnitOfWork
from delivery_platform.domain.entities import Delivery, Order
from delivery_platform.domain.events import EventType
from delivery_platform.domain.order_states import OrderState, transition_order

if TYPE_CHECKING:
    from delivery_platform.application.container import AppContainer


class RestaurantCommands:
    def __init__(self, container: AppContainer) -> None:
        self._container = container

    def confirm(self, ctx: CommandContext, order_id: str) -> Order:
        return self._transition(
            ctx,
            order_id,
            target=OrderState.CONFIRMED,
            event_type=EventType.ORDER_CONFIRMED,
            customer_message="O restaurante confirmou seu pedido.",
        )

    def prepare(self, ctx: CommandContext, order_id: str) -> Order:
        return self._transition(
            ctx,
            order_id,
            target=OrderState.PREPARING,
            event_type=EventType.ORDER_PREPARING,
            customer_message="Seu pedido está sendo preparado.",
        )

    def ready(self, ctx: CommandContext, order_id: str) -> Order:
        with self._container.uow() as uow:
            order = self._load_scoped_order(ctx, uow, order_id)
            order.state = transition_order(order.state, OrderState.READY_FOR_PICKUP)
            order.updated_at = self._container.clock.now()
            uow.orders.update(order)
            if uow.deliveries.find_by_order(order.id) is None:
                uow.deliveries.add(
                    Delivery(
                        id=self._container.ids.new_id("dlv"),
                        order_id=order.id,
                        courier_id=None,
                        status="offered",
                        scenario_id=order.scenario_id,
                    )
                )
            recorder = self._container.recorder(uow, ctx)
            recorder.event(
                EventType.ORDER_READY,
                aggregate_type="order",
                aggregate_id=order.id,
                payload={"order_status": order.state.value},
            )
            recorder.audit(
                "order.ready_for_pickup",
                target_type="order",
                target_id=order.id,
                detail="aguardando entregador",
            )
            recorder.notify(
                order.customer_id,
                "Seu pedido está pronto para retirada.",
                order_id=order.id,
            )
            uow.commit()
            return order

    def _transition(
        self,
        ctx: CommandContext,
        order_id: str,
        *,
        target: OrderState,
        event_type: EventType,
        customer_message: str,
    ) -> Order:
        with self._container.uow() as uow:
            order = self._load_scoped_order(ctx, uow, order_id)
            order.state = transition_order(order.state, target)
            order.updated_at = self._container.clock.now()
            uow.orders.update(order)
            recorder = self._container.recorder(uow, ctx)
            recorder.event(
                event_type,
                aggregate_type="order",
                aggregate_id=order.id,
                payload={"order_status": order.state.value},
            )
            recorder.audit(
                f"order.{target.value}",
                target_type="order",
                target_id=order.id,
                detail="",
            )
            recorder.notify(order.customer_id, customer_message, order_id=order.id)
            uow.commit()
            return order

    @staticmethod
    def _load_scoped_order(ctx: CommandContext, uow: UnitOfWork, order_id: str) -> Order:
        order = uow.orders.get(order_id)
        require_restaurant_operator(ctx.identity, order.restaurant_id)
        return order
