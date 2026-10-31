"""Request/response schemas for the /api/v1 surface."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

StrictBody = ConfigDict(extra="forbid", strict=True)


class AddCartItemRequest(BaseModel):
    model_config = StrictBody

    menu_item_id: StrictStr
    quantity: Annotated[StrictInt, Field(ge=1, le=20)]
    observation: str = ""


class UpdateCartItemRequest(BaseModel):
    model_config = StrictBody

    quantity: Annotated[StrictInt, Field(ge=1, le=20)] | None = None
    observation: str | None = None


class ApplyCouponRequest(BaseModel):
    model_config = StrictBody

    code: StrictStr


class CheckoutRequest(BaseModel):
    model_config = StrictBody

    address_id: StrictStr
    payment_method: Literal["pix", "card", "wallet"]
    simulate_outcome: Literal["approved", "declined"] | None = None


class SetAvailabilityRequest(BaseModel):
    model_config = StrictBody

    available: bool


class UpdateLocationRequest(BaseModel):
    model_config = StrictBody

    sequence: Annotated[StrictInt, Field(ge=1)]
    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]


class ErrorEnvelope(BaseModel):
    type: str
    title: str
    status: int
    code: str
    detail: str
    field_errors: dict[str, str] = {}
    correlation_id: str


class RateOrderRequest(BaseModel):
    stars: int = Field(ge=1, le=5)
