import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, Field, StrictInt

from delivery_platform.demo.scenario import DemoScenario

router = APIRouter()
logger = logging.getLogger(__name__)

_seed_path = Path(__file__).resolve().parents[6] / "data/scenarios/lunch-rush.json"
scenario = DemoScenario.from_seed_file(_seed_path)


class AdvanceRequest(BaseModel):
    event_count: Annotated[StrictInt, Field(ge=1, le=10)]


@router.get("/demo/scenario")
def get_scenario() -> dict[str, object]:
    return scenario.snapshot()


@router.post("/demo/reset")
def reset_scenario() -> dict[str, object]:
    return scenario.reset()


@router.post("/demo/advance")
def advance_scenario(request: AdvanceRequest) -> dict[str, object]:
    return scenario.advance_events(request.event_count)
