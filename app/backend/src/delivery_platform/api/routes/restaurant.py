"""Restaurant operator endpoints: queue and lifecycle commands."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from delivery_platform.api import serializers
from delivery_platform.api.deps import command_context, get_container
from delivery_platform.application.commands.restaurant import RestaurantCommands
from delivery_platform.application.container import AppContainer
from delivery_platform.application.context import CommandContext
from delivery_platform.application.queries import RestaurantQueries

router = APIRouter(prefix="/api/v1/restaurant", tags=["restaurant"])

Container = Annotated[AppContainer, Depends(get_container)]
Ctx = Annotated[CommandContext, Depends(command_context)]


@router.get("/orders")
def list_queue(container: Container, ctx: Ctx) -> dict[str, Any]:
    orders = RestaurantQueries(container).queue(ctx)
    return {"orders": [serializers.order_summary(o) for o in orders]}


@router.post("/orders/{order_id}/confirm")
def confirm_order(order_id: str, container: Container, ctx: Ctx) -> dict[str, Any]:
    order = RestaurantCommands(container).confirm(ctx, order_id)
    return {"order_id": order.id, "state": order.state.value, "version": order.version}


@router.post("/orders/{order_id}/prepare")
def prepare_order(order_id: str, container: Container, ctx: Ctx) -> dict[str, Any]:
    order = RestaurantCommands(container).prepare(ctx, order_id)
    return {"order_id": order.id, "state": order.state.value, "version": order.version}


@router.post("/orders/{order_id}/ready")
def ready_order(order_id: str, container: Container, ctx: Ctx) -> dict[str, Any]:
    order = RestaurantCommands(container).ready(ctx, order_id)
    return {"order_id": order.id, "state": order.state.value, "version": order.version}
