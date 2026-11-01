"""Scenario script schema: ordered real-command steps for demo replay.

The scenario file is a script of the same application commands the role
surfaces call — not a scripted state machine. The runner resolves actors and
executes each step through the public command layer.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

NonEmptyString = Annotated[str, Field(strict=True, min_length=1)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]

ScenarioAction = Literal[
    "cart.add_item",
    "cart.apply_coupon",
    "checkout",
    "restaurant.confirm",
    "restaurant.prepare",
    "restaurant.ready",
    "courier.accept",
    "courier.batch_accept",
    "courier.pickup",
    "courier.start",
    "courier.location",
    "courier.route_step",
    "courier.complete",
    "customer.rate",
    "customer.cancel",
    "clock.advance",
]


class StrictSeedModel(BaseModel):
    """Reject coercion and unknown seed fields at every schema level."""

    model_config = ConfigDict(extra="forbid", strict=True)


class ScenarioStep(StrictSeedModel):
    """One script step: an actor, a command action, and its parameters."""

    id: NonEmptyString
    actor: NonEmptyString | None = None
    action: ScenarioAction
    params: dict[str, Any] = Field(default_factory=dict)
    result_var: NonEmptyString | None = None


class ScenarioScript(StrictSeedModel):
    """Complete script consumed by the command-driven scenario runner."""

    scenario_id: NonEmptyString
    description: NonEmptyString
    steps: Annotated[list[ScenarioStep], Field(min_length=1)]


def validate_scenario_seed(value: object) -> ScenarioScript:
    """Validate and return the canonical strict scenario script."""
    return ScenarioScript.model_validate(value)
