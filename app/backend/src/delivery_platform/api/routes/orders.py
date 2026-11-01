"""Order read endpoints: history, detail, tracking, notifications, SSE stream."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from delivery_platform.api import serializers
from delivery_platform.api.deps import command_context, get_container
from delivery_platform.application.container import AppContainer
from delivery_platform.application.context import CommandContext
from delivery_platform.application.queries import CustomerQueries
from delivery_platform.core.metrics import METRICS

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

Container = Annotated[AppContainer, Depends(get_container)]
Ctx = Annotated[CommandContext, Depends(command_context)]


@router.get("/{order_id}")
def get_order(order_id: str, container: Container, ctx: Ctx) -> dict[str, Any]:
    view = CustomerQueries(container).get_order(ctx, order_id)
    return serializers.order_view(view.order, view.payment_attempt, view.delivery, view.route_plan)


@router.get("/{order_id}/tracking")
def get_tracking(order_id: str, container: Container, ctx: Ctx) -> dict[str, Any]:
    view = CustomerQueries(container).get_order(ctx, order_id)
    tracking = view.tracking
    last_known = tracking[-1].location if tracking else None
    return {
        "order_id": order_id,
        "order_status": view.order.state.value,
        "delivery_status": view.delivery.status if view.delivery else None,
        "route": serializers.route_view(view.route_plan),
        "last_known_location": (
            {"latitude": last_known.latitude, "longitude": last_known.longitude}
            if last_known
            else None
        ),
        "positions": [serializers.tracking_event_view(e) for e in tracking],
    }


@router.get("/{order_id}/notifications")
def list_notifications(order_id: str, container: Container, ctx: Ctx) -> dict[str, Any]:
    notifications = CustomerQueries(container).list_notifications(ctx, order_id)
    return {"notifications": [serializers.notification_view(n) for n in notifications]}


@router.get("/{order_id}/stream")
def stream_order(order_id: str, container: Container, ctx: Ctx) -> StreamingResponse:
    """Authorized SSE: snapshot first, then committed events for this order."""
    view = CustomerQueries(container).get_order(ctx, order_id)  # raises if forbidden
    snapshot = serializers.order_view(
        view.order, view.payment_attempt, view.delivery, view.route_plan
    )
    aggregates = (order_id,) + tuple(
        agg
        for agg in (
            view.delivery.id if view.delivery else None,
            view.payment_attempt.id if view.payment_attempt else None,
        )
        if agg
    )
    subscription = container.publisher.subscribe_many(aggregates)

    def event_stream() -> Iterator[str]:
        METRICS.add_gauge("entrega_sse_connections", 1)
        try:
            yield f"event: snapshot\ndata: {json.dumps(snapshot)}\n\n"
            while True:
                event = subscription.next_event(15)
                if event is None:
                    yield ": keepalive\n\n"
                else:
                    payload = json.dumps(serializers.event_view(event))
                    yield f"id: {event.id}\nevent: {event.type}\ndata: {payload}\n\n"
        finally:
            METRICS.add_gauge("entrega_sse_connections", -1)
            subscription.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
