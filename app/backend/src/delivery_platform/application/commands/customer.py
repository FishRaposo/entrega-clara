"""Customer order commands: rate a delivered order, cancel before prep.

Cancellation policy (M1): the customer may cancel while the order is still
``placed`` or ``confirmed`` — before preparation starts. An approved simulated
payment is marked ``refunded``; no partial-prep cancellation or refund split
exists yet (deferred to M2's real refund policy).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from delivery_platform.application.authorization import require_same_customer
from delivery_platform.application.context import CommandContext
from delivery_platform.application.ports import UnitOfWork
from delivery_platform.domain.entities import Order
from delivery_platform.domain.errors import DomainError
from delivery_platform.domain.events import EventType
from delivery_platform.domain.order_states import OrderState, transition_order

if TYPE_CHECKING:
    from delivery_platform.application.container import AppContainer


class CustomerCommands:
    def __init__(self, container: AppContainer) -> None:
        self._container = container

    def rate(self, ctx: CommandContext, order_id: str, stars: int) -> Order:
        if not 1 <= stars <= 5:
            raise DomainError("A avaliação deve ser entre 1 e 5 estrelas.")
        with self._container.uow() as uow:
            order = self._load_scoped_order(ctx, uow, order_id)
            order.state = transition_order(order.state, OrderState.RATED)
            order.rating = stars
            order.updated_at = self._container.clock.now()
            uow.orders.update(order)
            recorder = self._container.recorder(uow, ctx)
            recorder.event(
                EventType.ORDER_RATED,
                aggregate_type="order",
                aggregate_id=order.id,
                payload={"order_status": order.state.value, "stars": stars},
            )
            recorder.audit(
                "order.rated",
                target_type="order",
                target_id=order.id,
                detail=f"{stars} estrelas",
            )
            recorder.notify(
                order.customer_id,
                f"Obrigado pela avaliação de {stars} estrelas.",
                order_id=order.id,
            )
            uow.commit()
            return order

    def cancel(self, ctx: CommandContext, order_id: str) -> Order:
        with self._container.uow() as uow:
            order = self._load_scoped_order(ctx, uow, order_id)
            order.state = transition_order(order.state, OrderState.CANCELLED)
            order.updated_at = self._container.clock.now()
            uow.orders.update(order)

            refunded = False
            for attempt in uow.payment_attempts.list_by_order(order.id):
                if attempt.status == "approved":
                    attempt.status = "refunded"
                    attempt.updated_at = self._container.clock.now()
                    uow.payment_attempts.update(attempt)
                    refunded = True

            recorder = self._container.recorder(uow, ctx)
            recorder.event(
                EventType.ORDER_CANCELLED,
                aggregate_type="order",
                aggregate_id=order.id,
                payload={
                    "order_status": order.state.value,
                    "payment_refunded": refunded,
                },
            )
            recorder.audit(
                "order.cancelled",
                target_type="order",
                target_id=order.id,
                detail="estorno simulado" if refunded else "sem cobrança",
            )
            recorder.notify(
                order.customer_id,
                "Seu pedido foi cancelado."
                + (" O valor foi estornado (simulado)." if refunded else ""),
                order_id=order.id,
            )
            uow.commit()
            return order

    @staticmethod
    def _load_scoped_order(ctx: CommandContext, uow: UnitOfWork, order_id: str) -> Order:
        order = uow.orders.get(order_id)
        require_same_customer(ctx.identity, order.customer_id)
        return order
