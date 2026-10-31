"""Cart and coupon commands for the customer role."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from delivery_platform.application.authorization import require_role, require_same_customer
from delivery_platform.application.context import CommandContext
from delivery_platform.application.ports import UnitOfWork
from delivery_platform.domain.entities import Cart, CartLine, Coupon
from delivery_platform.domain.errors import (
    CartRestaurantConflictError,
    CouponExpiredError,
    CouponInvalidError,
    ItemUnavailableError,
    NotFoundError,
    RestaurantUnavailableError,
)
from delivery_platform.domain.money import CartTotals, compute_totals

if TYPE_CHECKING:
    from delivery_platform.application.container import AppContainer

MAX_OBSERVATION_LENGTH = 140
MAX_LINE_QUANTITY = 20


@dataclass(frozen=True)
class CartResult:
    cart: Cart
    totals: CartTotals


def cart_totals(uow: UnitOfWork, cart: Cart) -> CartTotals:
    """Recompute authoritative totals from current menu prices and coupon."""
    line_amounts = [
        (uow.menu_items.get(line.menu_item_id).price_minor, line.quantity)
        for line in cart.lines
    ]
    delivery_fee = 0
    currency = "BRL"
    if cart.restaurant_id is not None:
        restaurant = uow.restaurants.get(cart.restaurant_id)
        delivery_fee = restaurant.delivery_fee_minor
    if line_amounts:
        currency = uow.menu_items.get(cart.lines[0].menu_item_id).currency
    discount = 0
    if cart.coupon_code:
        coupon = uow.coupons.find(cart.coupon_code)
        if coupon is not None:
            discount = coupon.discount_minor
    return compute_totals(
        line_amounts,
        discount_minor=discount,
        delivery_fee_minor=delivery_fee,
        currency=currency,
    )


def validate_coupon(coupon: Coupon | None, subtotal_minor: int, now: datetime) -> Coupon:
    """Return the coupon or raise the stable coupon error."""
    if coupon is None or not coupon.active:
        raise CouponInvalidError()
    if coupon.expires_at is not None and coupon.expires_at <= now:
        raise CouponExpiredError()
    if subtotal_minor < coupon.min_subtotal_minor:
        raise CouponInvalidError()
    return coupon


class CartCommands:
    def __init__(self, container: AppContainer) -> None:
        self._container = container

    def _own_cart(self, ctx: CommandContext, uow: UnitOfWork) -> Cart:
        """Load the caller's cart, registering an empty one if it does not exist."""
        require_role(ctx.identity, "customer")
        cart = uow.carts.find_by_customer(ctx.identity.identity_id)
        if cart is None:
            cart = Cart(
                id=self._container.ids.new_id("cart"),
                customer_id=ctx.identity.identity_id,
                scenario_id=ctx.scenario_id,
            )
            uow.carts.add(cart)
        return cart

    def add_item(
        self,
        ctx: CommandContext,
        *,
        menu_item_id: str,
        quantity: int,
        observation: str = "",
    ) -> CartResult:
        if quantity < 1 or quantity > MAX_LINE_QUANTITY:
            raise ItemUnavailableError()
        if len(observation) > MAX_OBSERVATION_LENGTH:
            raise ItemUnavailableError()
        with self._container.uow() as uow:
            cart = self._own_cart(ctx, uow)
            item = uow.menu_items.find(menu_item_id)
            if item is None or not item.available:
                raise ItemUnavailableError()
            restaurant = uow.restaurants.get(item.restaurant_id)
            if not restaurant.available:
                raise RestaurantUnavailableError()
            if cart.restaurant_id is not None and cart.restaurant_id != item.restaurant_id:
                raise CartRestaurantConflictError()
            cart.restaurant_id = item.restaurant_id
            for line in cart.lines:
                if line.menu_item_id == menu_item_id and line.observation == observation:
                    line.quantity += quantity
                    break
            else:
                cart.lines.append(
                    CartLine(
                        id=self._container.ids.new_id("line"),
                        menu_item_id=menu_item_id,
                        quantity=quantity,
                        observation=observation,
                    )
                )
            for line in cart.lines:
                if line.quantity > MAX_LINE_QUANTITY:
                    raise ItemUnavailableError()
            uow.carts.update(cart)
            self._container.recorder(uow, ctx).audit(
                "cart.item_added",
                target_type="cart",
                target_id=cart.id,
                detail=f"{quantity}x {item.name}",
            )
            uow.commit()
            return CartResult(cart=cart, totals=cart_totals(uow, cart))

    def update_item(
        self,
        ctx: CommandContext,
        *,
        line_id: str,
        quantity: int | None = None,
        observation: str | None = None,
    ) -> CartResult:
        with self._container.uow() as uow:
            cart = self._own_cart(ctx, uow)
            line = next((ln for ln in cart.lines if ln.id == line_id), None)
            if line is None:
                raise NotFoundError("linha do carrinho")
            if quantity is not None:
                if quantity < 1 or quantity > MAX_LINE_QUANTITY:
                    raise ItemUnavailableError()
                line.quantity = quantity
            if observation is not None:
                if len(observation) > MAX_OBSERVATION_LENGTH:
                    raise ItemUnavailableError()
                line.observation = observation
            uow.carts.update(cart)
            self._container.recorder(uow, ctx).audit(
                "cart.item_updated",
                target_type="cart",
                target_id=cart.id,
                detail=f"linha {line_id}",
            )
            uow.commit()
            return CartResult(cart=cart, totals=cart_totals(uow, cart))

    def remove_item(self, ctx: CommandContext, *, line_id: str) -> CartResult:
        with self._container.uow() as uow:
            cart = self._own_cart(ctx, uow)
            before = len(cart.lines)
            cart.lines = [ln for ln in cart.lines if ln.id != line_id]
            if len(cart.lines) == before:
                raise NotFoundError("linha do carrinho")
            if not cart.lines:
                cart.restaurant_id = None
                cart.coupon_code = None
            uow.carts.update(cart)
            self._container.recorder(uow, ctx).audit(
                "cart.item_removed",
                target_type="cart",
                target_id=cart.id,
                detail=f"linha {line_id}",
            )
            uow.commit()
            return CartResult(cart=cart, totals=cart_totals(uow, cart))

    def apply_coupon(self, ctx: CommandContext, *, code: str) -> CartResult:
        with self._container.uow() as uow:
            cart = self._own_cart(ctx, uow)
            coupon = uow.coupons.find(code)
            line_amounts = [
                (uow.menu_items.get(line.menu_item_id).price_minor, line.quantity)
                for line in cart.lines
            ]
            subtotal = sum(price * qty for price, qty in line_amounts)
            coupon = validate_coupon(coupon, subtotal, self._container.clock.now())
            cart.coupon_code = coupon.code
            uow.carts.update(cart)
            self._container.recorder(uow, ctx).audit(
                "cart.coupon_applied",
                target_type="cart",
                target_id=cart.id,
                detail=coupon.code,
            )
            uow.commit()
            return CartResult(cart=cart, totals=cart_totals(uow, cart))

    def remove_coupon(self, ctx: CommandContext) -> CartResult:
        with self._container.uow() as uow:
            cart = self._own_cart(ctx, uow)
            cart.coupon_code = None
            uow.carts.update(cart)
            uow.commit()
            return CartResult(cart=cart, totals=cart_totals(uow, cart))

    def get_cart(self, ctx: CommandContext) -> CartResult:
        require_same_customer(ctx.identity, ctx.identity.identity_id)
        with self._container.uow() as uow:
            cart = self._own_cart(ctx, uow)
            totals = cart_totals(uow, cart)
            uow.rollback()
            return CartResult(cart=cart, totals=totals)
