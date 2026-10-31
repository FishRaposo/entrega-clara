"""Customer-scoped endpoints: cart, coupon, checkout, addresses."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status

from delivery_platform.api import serializers
from delivery_platform.api.deps import command_context, get_container
from delivery_platform.api.schemas import (
    AddCartItemRequest,
    ApplyCouponRequest,
    CheckoutRequest,
    RateOrderRequest,
    UpdateCartItemRequest,
)
from delivery_platform.application.commands.cart import CartCommands
from delivery_platform.application.commands.checkout import CheckoutCommands
from delivery_platform.application.commands.customer import CustomerCommands
from delivery_platform.application.container import AppContainer
from delivery_platform.application.context import CommandContext
from delivery_platform.application.queries import CustomerQueries

router = APIRouter(prefix="/api/v1/me", tags=["customer"])

Container = Annotated[AppContainer, Depends(get_container)]
Ctx = Annotated[CommandContext, Depends(command_context)]


@router.get("/cart")
def get_cart(container: Container, ctx: Ctx) -> dict[str, Any]:
    result = CartCommands(container).get_cart(ctx)
    return serializers.cart_view(result.cart, result.totals)


@router.post("/cart/items", status_code=status.HTTP_201_CREATED)
def add_cart_item(
    body: AddCartItemRequest, container: Container, ctx: Ctx
) -> dict[str, Any]:
    result = CartCommands(container).add_item(
        ctx,
        menu_item_id=body.menu_item_id,
        quantity=body.quantity,
        observation=body.observation,
    )
    return serializers.cart_view(result.cart, result.totals)


@router.patch("/cart/items/{line_id}")
def update_cart_item(
    line_id: str, body: UpdateCartItemRequest, container: Container, ctx: Ctx
) -> dict[str, Any]:
    result = CartCommands(container).update_item(
        ctx, line_id=line_id, quantity=body.quantity, observation=body.observation
    )
    return serializers.cart_view(result.cart, result.totals)


@router.delete("/cart/items/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_cart_item(line_id: str, container: Container, ctx: Ctx) -> Response:
    CartCommands(container).remove_item(ctx, line_id=line_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/cart/coupon")
def apply_coupon(body: ApplyCouponRequest, container: Container, ctx: Ctx) -> dict[str, Any]:
    result = CartCommands(container).apply_coupon(ctx, code=body.code)
    return serializers.cart_view(result.cart, result.totals)


@router.delete("/cart/coupon", status_code=status.HTTP_204_NO_CONTENT)
def remove_coupon(container: Container, ctx: Ctx) -> Response:
    CartCommands(container).remove_coupon(ctx)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/addresses")
def list_addresses(container: Container, ctx: Ctx) -> dict[str, Any]:
    addresses = CustomerQueries(container).list_addresses(ctx)
    return {"addresses": [serializers.address_view(a) for a in addresses]}


@router.get("/orders")
def list_my_orders(container: Container, ctx: Ctx) -> dict[str, Any]:
    orders = CustomerQueries(container).list_orders(ctx)
    return {"orders": [serializers.order_summary(o) for o in orders]}


@router.post("/orders/checkout", status_code=status.HTTP_201_CREATED)
def checkout(body: CheckoutRequest, container: Container, ctx: Ctx) -> dict[str, Any]:
    result = CheckoutCommands(container).checkout(
        ctx,
        address_id=body.address_id,
        payment_method=body.payment_method,
        simulate_outcome=body.simulate_outcome,
    )
    return {
        "order_id": result.order.id,
        "state": result.order.state.value,
        "total_minor": result.order.total_minor,
        "currency": result.order.currency,
        "payment": serializers.payment_view(result.payment_attempt),
        "replayed": result.replayed,
    }



@router.post("/orders/{order_id}/rate")
def rate_order(order_id: str, body: RateOrderRequest, container: Container, ctx: Ctx) -> dict[str, Any]:
    order = CustomerCommands(container).rate(ctx, order_id, body.stars)
    return {"order": serializers.order_summary(order)}


@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str, container: Container, ctx: Ctx) -> dict[str, Any]:
    order = CustomerCommands(container).cancel(ctx, order_id)
    return {"order": serializers.order_summary(order)}
