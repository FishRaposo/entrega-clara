from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from delivery_platform.domain.order_states import OrderState

NonEmptyString = Annotated[str, Field(strict=True, min_length=1)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
Latitude = Annotated[float, Field(strict=True, ge=-90, le=90)]
Longitude = Annotated[float, Field(strict=True, ge=-180, le=180)]
CourierStatus = Literal["available", "assigned", "delivering"]
OrderStateValue = Annotated[OrderState, Field(strict=False)]


class StrictSeedModel(BaseModel):
    """Reject coercion and unknown seed fields at every schema level."""

    model_config = ConfigDict(extra="forbid", strict=True)


class CustomerSeed(StrictSeedModel):
    id: NonEmptyString
    name: NonEmptyString


class RestaurantSeed(CustomerSeed):
    latitude: Latitude
    longitude: Longitude


class CourierSeed(RestaurantSeed):
    status: CourierStatus


class ActiveOrderSeed(StrictSeedModel):
    id: NonEmptyString
    state: OrderStateValue
    total_brl_centavos: NonNegativeInt


class CouponSeed(StrictSeedModel):
    code: NonEmptyString
    valid: bool
    discount_brl_centavos: NonNegativeInt


class PaymentSeed(StrictSeedModel):
    method: Literal["pix", "card", "wallet"]
    outcome: Literal["approved", "declined"]
    reference: NonEmptyString


class CourierUpdate(StrictSeedModel):
    status: CourierStatus | None = None
    latitude: Latitude | None = None
    longitude: Longitude | None = None

    @model_validator(mode="after")
    def require_a_change(self) -> Self:
        if self.status is None and self.latitude is None and self.longitude is None:
            raise ValueError("courier_update must contain at least one value")
        return self


class ScenarioEvent(StrictSeedModel):
    """One completely validated seed-defined scenario mutation."""

    minutes: NonNegativeInt
    order_state: OrderStateValue | None = None
    courier_update: CourierUpdate | None = None
    notification: NonEmptyString | None = None

    @model_validator(mode="after")
    def require_a_mutation(self) -> Self:
        if (
            self.order_state is None
            and self.courier_update is None
            and self.notification is None
        ):
            raise ValueError("event must contain at least one scenario mutation")
        return self


class ScenarioState(StrictSeedModel):
    scenario_id: NonEmptyString
    clock_minutes: NonNegativeInt
    customer: CustomerSeed
    restaurant: RestaurantSeed
    courier: CourierSeed
    active_order: ActiveOrderSeed
    coupon: CouponSeed
    payment: PaymentSeed
    notifications: list[NonEmptyString]


class ScenarioSeed(StrictSeedModel):
    """Complete schema consumed by deterministic scenario replay."""

    scenario_id: NonEmptyString
    initial_state: ScenarioState
    events: Annotated[list[ScenarioEvent], Field(min_length=1)]

    @model_validator(mode="after")
    def require_matching_scenario_ids(self) -> Self:
        if self.initial_state.scenario_id != self.scenario_id:
            raise ValueError("initial_state scenario_id must match the seed scenario_id")
        return self


def validate_scenario_seed(value: object) -> ScenarioSeed:
    """Validate and return the canonical strict scenario schema."""
    return ScenarioSeed.model_validate(value)
