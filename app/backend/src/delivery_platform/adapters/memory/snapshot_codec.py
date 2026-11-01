"""Serialize a ``MemoryStore`` to JSON and rebuild it — no database needed.

Export uses ``dataclasses.asdict`` with a small encoder (datetime → ISO,
StrEnum/tuple → JSON-native). Import rebuilds every entity through explicit
per-collection builders — deterministic, mypy-friendly, and free of pickle.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar, cast, get_args, get_origin, get_type_hints

from delivery_platform.adapters.memory.store import MemoryStore


def store_to_json(store: MemoryStore) -> str:
    def encode(value: Any) -> Any:
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            return {
                f.name: encode(getattr(value, f.name))
                for f in dataclasses.fields(value)
            }
        if isinstance(value, datetime):
            return {"__dt__": value.isoformat()}
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, (list, tuple)):
            return [encode(v) for v in value]
        if isinstance(value, dict):
            return {
                (json.dumps(k) if isinstance(k, tuple) else k): encode(v)
                for k, v in value.items()
            }
        return value

    return json.dumps(encode(store), ensure_ascii=False, sort_keys=True)


T = TypeVar("T")


def _convert(value: Any, hint: Any) -> Any:
    """Rebuild a field value from JSON according to its type hint."""
    if value is None:
        return None
    origin = get_origin(hint)
    if origin is not None and type(None) in get_args(hint):  # Optional
        inner = next(a for a in get_args(hint) if a is not type(None))
        return _convert(value, inner)
    if hint is datetime or (origin is None and hint is datetime):
        return datetime.fromisoformat(value["__dt__"])
    if origin in (list, tuple):
        inner = get_args(hint)[0] if get_args(hint) else Any
        converted = [_convert(v, inner) for v in value]
        return tuple(converted) if origin is tuple else converted
    if origin is dict:
        args = get_args(hint) or (Any, Any)
        out = {}
        for k, v in value.items():
            key: Any = k
            if get_origin(args[0]) is tuple:  # tuple keys were JSON-encoded
                key = tuple(json.loads(k))
            out[key] = _convert(v, args[1])
        return out
    if isinstance(value, dict) and isinstance(hint, type) and dataclasses.is_dataclass(hint):
        return _build(value, hint)
    if isinstance(hint, type) and issubclass(hint, Enum):
        return hint(value)
    return value


def _build(data: dict[str, Any], cls: type[T]) -> T:
    hints = get_type_hints(cls)
    return cls(
        **{
            field.name: _convert(data[field.name], hints.get(field.name, Any))
            for field in dataclasses.fields(cast(Any, cls))
            if field.name in data
        }
    )


def store_from_json(payload: str) -> MemoryStore:
    from delivery_platform.domain.entities import (
        Address,
        AuditEvent,
        Cart,
        Coupon,
        CourierProfile,
        Delivery,
        DeliveryBatch,
        DemoIdentity,
        IdempotencyRecord,
        MenuItem,
        Notification,
        Order,
        PaymentAttempt,
        Restaurant,
        RoutePlan,
        TrackingEvent,
    )
    from delivery_platform.domain.events import DomainEvent

    raw = json.loads(payload)
    if not isinstance(raw, dict):
        raise TypeError("snapshot payload must be a JSON object")

    store = MemoryStore()
    dict_fields: dict[str, type] = {
        "identities": DemoIdentity,
        "restaurants": Restaurant,
        "menu_items": MenuItem,
        "addresses": Address,
        "carts": Cart,
        "coupons": Coupon,
        "orders": Order,
        "payment_attempts": PaymentAttempt,
        "couriers": CourierProfile,
        "deliveries": Delivery,
        "batches": DeliveryBatch,
        "route_plans": RoutePlan,
        "notifications": Notification,
    }
    for name, cls in dict_fields.items():
        for key, entity in (raw.get(name) or {}).items():
            getattr(store, name)[key] = _build(entity, cls)

    list_fields: dict[str, type] = {
        "tracking_events": TrackingEvent,
        "audit_events": AuditEvent,
        "event_log": DomainEvent,
    }
    for name, cls in list_fields.items():
        setattr(
            store,
            name,
            [_build(entity, cls) for entity in (raw.get(name) or [])],
        )

    for key, record in (raw.get("idempotency") or {}).items():
        parsed = json.loads(key)
        store.idempotency[(parsed[0], parsed[1])] = _build(
            record, IdempotencyRecord
        )
    store.event_sequence = int(raw.get("event_sequence") or 0)
    return store
