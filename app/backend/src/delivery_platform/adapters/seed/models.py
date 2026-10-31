"""Strict schemas for reference seed data (catalog, identities, couriers).

Same conventions as the scenario seed models: no coercion, no unknown fields.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

NonEmptyString = Annotated[str, Field(strict=True, min_length=1)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, gt=0)]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]


class StrictSeedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class IdentitySeed(StrictSeedModel):
    id: NonEmptyString
    name: NonEmptyString
    role: Literal["customer", "restaurant", "courier", "operations"]
    restaurant_id: NonEmptyString | None = None
    courier_id: NonEmptyString | None = None


class RestaurantSeed(StrictSeedModel):
    id: NonEmptyString
    name: NonEmptyString
    cuisine: NonEmptyString
    description: str = ""
    available: bool
    delivery_fee_minor: NonNegativeInt = 0
    latitude: Latitude
    longitude: Longitude
    address_label: NonEmptyString


class MenuItemSeed(StrictSeedModel):
    id: NonEmptyString
    restaurant_id: NonEmptyString
    name: NonEmptyString
    description: str = ""
    category: NonEmptyString
    price_minor: PositiveInt
    currency: NonEmptyString
    available: bool


class AddressSeed(StrictSeedModel):
    id: NonEmptyString
    customer_id: NonEmptyString
    label: NonEmptyString
    formatted: NonEmptyString
    latitude: Latitude
    longitude: Longitude


class CouponSeed(StrictSeedModel):
    code: NonEmptyString
    description: str = ""
    discount_minor: NonNegativeInt
    currency: NonEmptyString
    min_subtotal_minor: NonNegativeInt = 0
    active: bool
    expires_at: NonEmptyString | None = None  # ISO-8601 UTC


class CourierSeed(StrictSeedModel):
    id: NonEmptyString
    name: NonEmptyString
    status: Literal["available", "assigned", "delivering", "offline"]
    latitude: Latitude
    longitude: Longitude


class ReferenceSeed(StrictSeedModel):
    """Complete reference dataset for one market."""

    market: Literal["br"]
    identities: Annotated[list[IdentitySeed], Field(min_length=1)]
    restaurants: list[RestaurantSeed]
    menu_items: list[MenuItemSeed]
    addresses: list[AddressSeed]
    coupons: list[CouponSeed]
    couriers: list[CourierSeed]


def validate_reference_seed(value: object) -> ReferenceSeed:
    return ReferenceSeed.model_validate(value)
