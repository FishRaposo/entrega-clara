"""Operations read-only endpoints: orders, events, audit, couriers, metrics."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from delivery_platform.api import serializers
from delivery_platform.api.deps import command_context, get_container
from delivery_platform.application.container import AppContainer
from delivery_platform.application.context import CommandContext
from delivery_platform.application.queries import OperationsQueries

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])

Container = Annotated[AppContainer, Depends(get_container)]
Ctx = Annotated[CommandContext, Depends(command_context)]


@router.get("/orders")
def list_orders(container: Container, ctx: Ctx) -> dict[str, Any]:
    orders = OperationsQueries(container).list_orders(ctx)
    return {"orders": [serializers.order_summary(o) for o in orders]}


@router.get("/orders/{order_id}")
def get_order(order_id: str, container: Container, ctx: Ctx) -> dict[str, Any]:
    view = OperationsQueries(container).get_order(ctx, order_id)
    return serializers.order_view(view.order, view.payment_attempt, view.delivery, view.route_plan)


@router.get("/events")
def list_events(
    container: Container, ctx: Ctx, since: Annotated[int, Query(ge=0)] = 0
) -> dict[str, Any]:
    events = OperationsQueries(container).list_events(ctx, since=since)
    return {"events": [serializers.event_view(e) for e in events]}


@router.get("/audit")
def list_audit(container: Container, ctx: Ctx) -> dict[str, Any]:
    audit = OperationsQueries(container).list_audit(ctx)
    return {"audit_events": [serializers.audit_view(a) for a in audit]}


@router.get("/couriers")
def list_couriers(container: Container, ctx: Ctx) -> dict[str, Any]:
    couriers = OperationsQueries(container).list_couriers(ctx)
    return {"couriers": [serializers.courier_view(c) for c in couriers]}


@router.get("/metrics")
def get_metrics(container: Container, ctx: Ctx) -> dict[str, Any]:
    return OperationsQueries(container).metrics(ctx)
