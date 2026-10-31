"""Idempotent loading of safe reference seed data into the memory store."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from delivery_platform.adapters.memory.store import MemoryStore
from delivery_platform.adapters.seed.models import ReferenceSeed, validate_reference_seed
from delivery_platform.domain.entities import (
    Address,
    Coupon,
    CourierProfile,
    DemoIdentity,
    GeoPoint,
    MenuItem,
    Restaurant,
)


def load_reference_seed(store: MemoryStore, seed: ReferenceSeed) -> None:
    """Load or refresh reference data. Keyed upserts keep loading idempotent."""
    for identity in seed.identities:
        store.identities[identity.id] = DemoIdentity(
            id=identity.id,
            name=identity.name,
            role=identity.role,
            market=seed.market,
            restaurant_id=identity.restaurant_id,
            courier_id=identity.courier_id,
        )
    for restaurant in seed.restaurants:
        store.restaurants[restaurant.id] = Restaurant(
            id=restaurant.id,
            name=restaurant.name,
            cuisine=restaurant.cuisine,
            description=restaurant.description,
            available=restaurant.available,
            delivery_fee_minor=restaurant.delivery_fee_minor,
            location=GeoPoint(latitude=restaurant.latitude, longitude=restaurant.longitude),
            address_label=restaurant.address_label,
        )
    for menu_item in seed.menu_items:
        store.menu_items[menu_item.id] = MenuItem(
            id=menu_item.id,
            restaurant_id=menu_item.restaurant_id,
            name=menu_item.name,
            description=menu_item.description,
            category=menu_item.category,
            price_minor=menu_item.price_minor,
            currency=menu_item.currency,
            available=menu_item.available,
        )
    for address in seed.addresses:
        store.addresses[address.id] = Address(
            id=address.id,
            customer_id=address.customer_id,
            label=address.label,
            formatted=address.formatted,
            location=GeoPoint(latitude=address.latitude, longitude=address.longitude),
        )
    for coupon in seed.coupons:
        expires_at = None
        if coupon.expires_at is not None:
            expires_at = datetime.fromisoformat(coupon.expires_at)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
        store.coupons[coupon.code.upper()] = Coupon(
            code=coupon.code.upper(),
            description=coupon.description,
            discount_minor=coupon.discount_minor,
            currency=coupon.currency,
            min_subtotal_minor=coupon.min_subtotal_minor,
            active=coupon.active,
            expires_at=expires_at,
        )
    for courier in seed.couriers:
        store.couriers[courier.id] = CourierProfile(
            id=courier.id,
            name=courier.name,
            status=courier.status,
            location=GeoPoint(latitude=courier.latitude, longitude=courier.longitude),
        )


def load_reference_seed_file(store: MemoryStore, path: str | Path) -> ReferenceSeed:
    loaded: object = json.loads(Path(path).read_text(encoding="utf-8"))
    seed = validate_reference_seed(loaded)
    load_reference_seed(store, seed)
    return seed
