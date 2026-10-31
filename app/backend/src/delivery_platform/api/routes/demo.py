"""Demo scenario endpoints: scripted replay through real commands."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, StrictInt

from delivery_platform.adapters.memory.store import MemoryStore
from delivery_platform.application.container import AppContainer
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


class SnapshotRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=40, pattern=r"^[\w-]+$")]


# Named in-memory snapshots — deep-copied MemoryStore states for demo
# save/restore without a database. JSON file export stays deferred.
_SNAPSHOTS: dict[str, MemoryStore] = {}


@router.post("/snapshot")
def save_snapshot(request: Request, body: SnapshotRequest) -> dict[str, Any]:
    import copy

    container: AppContainer = request.app.state.container
    _SNAPSHOTS[body.name] = copy.deepcopy(container.store)
    return {"saved": body.name, "snapshots": sorted(_SNAPSHOTS)}


@router.get("/snapshot")
def list_snapshots() -> dict[str, Any]:
    return {"snapshots": sorted(_SNAPSHOTS)}


@router.put("/snapshot")
def restore_snapshot(request: Request, body: SnapshotRequest) -> dict[str, Any]:
    import copy

    if body.name not in _SNAPSHOTS:
        raise DemoScenarioError(f"Não existe snapshot '{body.name}'.")
    container: AppContainer = request.app.state.container
    container.store.identities.clear()
    container.store.identities.update(_SNAPSHOTS[body.name].identities)
    # swap the live store for a deep copy so later restores stay pristine
    restored = copy.deepcopy(_SNAPSHOTS[body.name])
    for field_name in restored.__dataclass_fields__:
        setattr(container.store, field_name, getattr(restored, field_name))
    return {"restored": body.name}
