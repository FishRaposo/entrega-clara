"""Checkout: snapshot the cart into an order with a simulated payment attempt."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from delivery_platform.application.authorization import require_role
from delivery_platform.application.commands.cart import cart_totals, validate_coupon
from delivery_platform.application.context import CommandContext
from delivery_platform.domain.entities import (
    IdempotencyRecord,
    Order,
    OrderItem,
    PaymentAttempt,
    PaymentMethod,
)
from delivery_platform.domain.errors import (
    CartEmptyError,
    DomainError,
    IdempotencyConflictError,
    ItemUnavailableError,
    OwnershipForbiddenError,
    PaymentDeclinedError,
    RestaurantUnavailableError,
)
from delivery_platform.domain.events import EventType
from delivery_platform.domain.order_states import OrderState

if TYPE_CHECKING:
    from delivery_platform.application.container import AppContainer


@dataclass(frozen=True)
class CheckoutResult:
    order: Order
    payment_attempt: PaymentAttempt
    replayed: bool = False


class CheckoutCommands:
    def __init__(self, container: AppContainer) -> None:
        self._container = container

    def checkout(
        self,
        ctx: CommandContext,
        *,
        address_id: str,
        payment_method: PaymentMethod,
        simulate_outcome: str | None = None,
    ) -> CheckoutResult:
        require_role(ctx.identity, "customer")
        key = ctx.idempotency_key
        if not key:
            raise DomainError("A chave de idempotência é obrigatória.")
        identity_id = ctx.identity.identity_id

        with self._container.uow() as uow:
            fingerprint = self._fingerprint(
                address_id=address_id, payment_method=payment_method,
                simulate_outcome=simulate_outcome,
            )
            existing = uow.idempotency.find(identity_id, key)
            if existing is not None:
                if existing.request_fingerprint != fingerprint:
                    raise IdempotencyConflictError()
                order = uow.orders.get(existing.result["order_id"])
                attempt = uow.payment_attempts.get(order.payment_attempt_id or "")
                uow.commit()
                return CheckoutResult(order=order, payment_attempt=attempt, replayed=True)

            cart = uow.carts.find_by_customer(identity_id)
            if cart is None or not cart.lines:
                raise CartEmptyError()
            address = uow.addresses.get(address_id)
            if address.customer_id != identity_id:
                raise OwnershipForbiddenError()
            restaurant = uow.restaurants.get(cart.restaurant_id or "")
            if not restaurant.available:
                raise RestaurantUnavailableError()

            items: list[OrderItem] = []
            for line in cart.lines:
                menu_item = uow.menu_items.get(line.menu_item_id)
                if menu_item.restaurant_id != restaurant.id or not menu_item.available:
                    raise ItemUnavailableError()
                items.append(
                    OrderItem(
                        menu_item_id=menu_item.id,
                        name=menu_item.name,
                        unit_price_minor=menu_item.price_minor,
                        quantity=line.quantity,
                        observation=line.observation,
                    )
                )

            coupon = None
            if cart.coupon_code:
                subtotal = sum(i.unit_price_minor * i.quantity for i in items)
                coupon = validate_coupon(
                    uow.coupons.find(cart.coupon_code),
                    subtotal,
                    self._container.clock.now(),
                )
            totals = cart_totals(uow, cart)

            now = self._container.clock.now()
            order_id = self._container.ids.new_id("order")
            key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
            attempt = self._container.payment_gateway.create_attempt(
                attempt_id=self._container.ids.new_id("pay"),
                order_id=order_id,
                method=payment_method,
                amount_minor=totals.total_minor,
                currency=totals.currency,
                simulate_outcome=simulate_outcome,
                idempotency_key_hash=key_hash,
                now=now,
            )
            attempt.scenario_id = ctx.scenario_id
            recorder = self._container.recorder(uow, ctx)

            if attempt.status == "declined":
                uow.payment_attempts.add(attempt)
                recorder.audit(
                    "payment.declined",
                    target_type="payment",
                    target_id=attempt.id,
                    detail=attempt.failure_code or "declined",
                )
                recorder.event(
                    EventType.PAYMENT_DECLINED,
                    aggregate_type="payment",
                    aggregate_id=attempt.id,
                    payload={"failure_code": attempt.failure_code},
                )
                uow.commit()
                raise PaymentDeclinedError()

            order = Order(
                id=order_id,
                customer_id=identity_id,
                restaurant_id=restaurant.id,
                items=items,
                address_id=address.id,
                address_label=address.formatted,
                state=OrderState.PLACED,
                currency=totals.currency,
                subtotal_minor=totals.subtotal_minor,
                discount_minor=totals.discount_minor,
                delivery_fee_minor=totals.delivery_fee_minor,
                total_minor=totals.total_minor,
                coupon_code=coupon.code if coupon else None,
                payment_attempt_id=attempt.id,
                created_at=now,
                updated_at=now,
                scenario_id=ctx.scenario_id,
            )
            uow.orders.add(order)
            uow.payment_attempts.add(attempt)
            recorder.event(
                EventType.ORDER_PLACED,
                aggregate_type="order",
                aggregate_id=order.id,
                payload={"order_status": order.state.value, "total_minor": order.total_minor},
            )
            recorder.event(
                EventType.PAYMENT_APPROVED,
                aggregate_type="order",
                aggregate_id=order.id,
                payload={"payment_id": attempt.id, "method": attempt.method},
            )
            recorder.audit(
                "order.created",
                target_type="order",
                target_id=order.id,
                detail=f"total {order.total_minor} {order.currency}",
            )
            recorder.notify(
                identity_id,
                "Pedido realizado com sucesso.",
                order_id=order.id,
            )
            for operator in uow.identities.list_all():
                if operator.role == "restaurant" and operator.restaurant_id == restaurant.id:
                    recorder.notify(
                        operator.id,
                        "Novo pedido recebido na fila.",
                        order_id=order.id,
                    )
            cart.lines = []
            cart.restaurant_id = None
            cart.coupon_code = None
            uow.carts.update(cart)
            uow.idempotency.add(
                IdempotencyRecord(
                    key=key,
                    identity_id=identity_id,
                    request_fingerprint=fingerprint,
                    result={"order_id": order.id},
                    created_at=now,
                )
            )
            uow.commit()
            return CheckoutResult(order=order, payment_attempt=attempt)

    @staticmethod
    def _fingerprint(
        *,
        address_id: str,
        payment_method: str,
        simulate_outcome: str | None,
    ) -> str:
        """Fingerprint the request payload only — the cart mutates on success."""
        payload = {
            "address_id": address_id,
            "payment_method": payment_method,
            "simulate_outcome": simulate_outcome,
        }
        canonical: str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
