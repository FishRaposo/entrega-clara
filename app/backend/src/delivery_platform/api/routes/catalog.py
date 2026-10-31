"""Catalog read endpoints: restaurants and menus."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from delivery_platform.api import serializers
from delivery_platform.api.deps import get_container
from delivery_platform.application.container import AppContainer
from delivery_platform.application.queries import CatalogQueries

router = APIRouter(prefix="/api/v1/restaurants", tags=["catalog"])

Container = Annotated[AppContainer, Depends(get_container)]


@router.get("")
def list_restaurants(
    container: Container,
    cuisine: Annotated[str | None, Query()] = None,
    query: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    restaurants = CatalogQueries(container).list_restaurants(cuisine=cuisine, query=query)
    return {"restaurants": [serializers.restaurant_summary(r) for r in restaurants]}


@router.get("/{restaurant_id}")
def get_restaurant(restaurant_id: str, container: Container) -> dict[str, Any]:
    restaurant = CatalogQueries(container).get_restaurant(restaurant_id)
    return serializers.restaurant_summary(restaurant)


@router.get("/{restaurant_id}/menu")
def get_menu(restaurant_id: str, container: Container) -> dict[str, Any]:
    items = CatalogQueries(container).get_menu(restaurant_id)
    return {"items": [serializers.menu_item_view(item) for item in items]}
