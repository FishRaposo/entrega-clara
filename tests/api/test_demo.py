import json
from pathlib import Path

import pytest
from delivery_platform.api.main import app
from delivery_platform.api.routes import demo as demo_routes
from delivery_platform.demo.scenario import DemoScenario
from fastapi.testclient import TestClient

client = TestClient(app)


def test_demo_reset_returns_a_replayable_scenario():
    response = client.post("/api/v1/demo/reset")

    assert response.status_code == 200
    assert response.json()["scenario_id"] == "lunch-rush"


def test_demo_advance_rejects_more_than_ten_events():
    response = client.post("/api/v1/demo/advance", json={"event_count": 11})

    assert response.status_code == 422


def test_demo_advance_returns_a_safe_error_when_events_are_exhausted():
    client.post("/api/v1/demo/reset")
    response = client.post("/api/v1/demo/advance", json={"event_count": 10})

    assert response.status_code == 200

    exhausted = client.post("/api/v1/demo/advance", json={"event_count": 1})

    assert exhausted.status_code == 409
    assert exhausted.json() == {"detail": "No more demo events are available."}


def test_demo_advance_rejection_does_not_mutate_the_scenario():
    client.post("/api/v1/demo/reset")
    client.post("/api/v1/demo/advance", json={"event_count": 9})
    before = client.get("/api/v1/demo/scenario").json()

    rejected = client.post("/api/v1/demo/advance", json={"event_count": 2})

    assert rejected.status_code == 409
    assert client.get("/api/v1/demo/scenario").json() == before


@pytest.mark.parametrize("event_count", (True, "1", 0, 11))
def test_demo_advance_rejects_non_strict_or_out_of_bounds_event_counts(event_count: object):
    client.post("/api/v1/demo/reset")

    response = client.post("/api/v1/demo/advance", json={"event_count": event_count})

    assert response.status_code == 422


def test_demo_api_batch_failure_keeps_the_previous_snapshot(monkeypatch):
    seed = json.loads(Path("data/scenarios/lunch-rush.json").read_text(encoding="utf-8"))
    seed["events"][1]["order_state"] = "delivered"
    malformed_scenario = DemoScenario.from_seed_data(seed)
    monkeypatch.setattr(demo_routes, "scenario", malformed_scenario)
    before = client.get("/api/v1/demo/scenario").json()

    response = client.post("/api/v1/demo/advance", json={"event_count": 2})

    assert response.status_code == 409
    assert client.get("/api/v1/demo/scenario").json() == before
