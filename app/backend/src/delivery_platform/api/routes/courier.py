"""Courier endpoints: availability, offers, delivery lifecycle, locations."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from delivery_platform.api import serializers
from delivery_platform.api.deps import command_context, get_container
from delivery_platform.api.schemas import (
    BatchAcceptRequest,
    BatchInsertRequest,
    SetAvailabilityRequest,
    UpdateLocationRequest,
)
from delivery_platform.application.commands.courier import CourierCommands
from delivery_platform.application.container import AppContainer
from delivery_platform.application.context import CommandContext
from delivery_platform.application.queries import CourierQueries

router = APIRouter(prefix="/api/v1/courier", tags=["courier"])

Container = Annotated[AppContainer, Depends(get_container)]
Ctx = Annotated[CommandContext, Depends(command_context)]


@router.get("/profile")
def get_profile(container: Container, ctx: Ctx) -> dict[str, Any]:
    return serializers.courier_view(CourierQueries(container).profile(ctx))


@router.put("/availability")
def set_availability(
    body: SetAvailabilityRequest, container: Container, ctx: Ctx
) -> dict[str, Any]:
    courier = CourierCommands(container).set_availability(ctx, available=body.available)
    return {
        "courier_id": courier.id,
        "status": courier.status,
        "version": courier.version,
    }


@router.get("/deliveries/offers")
def list_offers(container: Container, ctx: Ctx) -> dict[str, Any]:
    offers = CourierQueries(container).offers(ctx)
    return {"deliveries": [serializers.delivery_view(d) for d in offers]}


@router.get("/deliveries/active")
def get_active(container: Container, ctx: Ctx) -> dict[str, Any]:
    deliveries, batch, route = CourierQueries(container).active(ctx)
    return {
        "deliveries": [serializers.delivery_view(d) for d in deliveries],
        "delivery": serializers.delivery_view(deliveries[0] if deliveries else None),
        "batch": serializers.batch_view(batch),
        "route": serializers.route_view(route),
    }


@router.post("/batches/accept")
def accept_batch(body: BatchAcceptRequest, container: Container, ctx: Ctx) -> dict[str, Any]:
    batch = CourierCommands(container).batch_accept(ctx, list(body.delivery_ids))
    return {"batch": serializers.batch_view(batch)}


@router.post("/batches/{batch_id}/insert")
def insert_into_batch(
    batch_id: str, body: BatchInsertRequest, container: Container, ctx: Ctx
) -> dict[str, Any]:
    """Insert one offered delivery into an active batch and re-plan the rest."""
    route = CourierCommands(container).add_to_batch(ctx, batch_id, body.delivery_id)
    return {"route": serializers.route_view(route)}


@router.post("/deliveries/{delivery_id}/accept")
def accept_delivery(delivery_id: str, container: Container, ctx: Ctx) -> dict[str, Any]:
    delivery = CourierCommands(container).accept(ctx, delivery_id)
    return {"delivery": serializers.delivery_view(delivery)}


@router.post("/deliveries/{delivery_id}/pickup")
def pickup_delivery(delivery_id: str, container: Container, ctx: Ctx) -> dict[str, Any]:
    delivery = CourierCommands(container).pickup(ctx, delivery_id)
    return {"delivery": serializers.delivery_view(delivery)}


@router.post("/deliveries/{delivery_id}/start")
def start_delivery(delivery_id: str, container: Container, ctx: Ctx) -> dict[str, Any]:
    delivery = CourierCommands(container).start_route(ctx, delivery_id)
    return {"delivery": serializers.delivery_view(delivery)}


@router.post("/deliveries/{delivery_id}/route-advance")
def advance_route(delivery_id: str, container: Container, ctx: Ctx) -> dict[str, Any]:
    events = CourierCommands(container).advance_route_location(ctx, delivery_id)
    return {
        "events": [
            {
                "delivery_id": e.delivery_id,
                "sequence": e.sequence,
                "latitude": e.location.latitude,
                "longitude": e.location.longitude,
            }
            for e in events
        ]
    }


@router.post("/deliveries/{delivery_id}/location")
def update_location(
    delivery_id: str, body: UpdateLocationRequest, container: Container, ctx: Ctx
) -> dict[str, Any]:
    event = CourierCommands(container).update_location(
        ctx,
        delivery_id=delivery_id,
        sequence=body.sequence,
        latitude=body.latitude,
        longitude=body.longitude,
    )
    return {"position": serializers.tracking_event_view(event)}


@router.post("/deliveries/{delivery_id}/complete")
def complete_delivery(delivery_id: str, container: Container, ctx: Ctx) -> dict[str, Any]:
    delivery = CourierCommands(container).complete(ctx, delivery_id)
    return {"delivery": serializers.delivery_view(delivery)}
