"""Demo scenario endpoints: scripted replay through real commands."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, StrictInt

from delivery_platform.demo.runner import ScenarioRunner
from delivery_platform.domain.errors import DemoScenarioError

router = APIRouter(prefix="/demo", tags=["demo"])


def _runner(request: Request) -> ScenarioRunner:
    runner = getattr(request.app.state, "scenario_runner", None)
    if not isinstance(runner, ScenarioRunner):
        raise DemoScenarioError("The demo scenario is unavailable.")
    return runner


class AdvanceRequest(BaseModel):
    event_count: Annotated[StrictInt, Field(ge=1, le=20)]


class ClockRequest(BaseModel):
    minutes: Annotated[StrictInt, Field(ge=0, le=240)]


@router.get("/scenario")
def get_scenario(request: Request) -> dict[str, Any]:
    return _runner(request).snapshot()


@router.post("/reset")
def reset_scenario(request: Request) -> dict[str, Any]:
    return _runner(request).reset()


@router.post("/advance")
def advance_scenario(request: Request, body: AdvanceRequest) -> dict[str, Any]:
    return _runner(request).advance_events(body.event_count)


@router.post("/clock")
def advance_clock(request: Request, body: ClockRequest) -> dict[str, Any]:
    return _runner(request).advance_minutes(body.minutes)
