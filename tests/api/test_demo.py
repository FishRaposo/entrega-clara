import uuid

import pytest
from delivery_platform.api.main import create_app
from fastapi.testclient import TestClient

CUSTOMER = {"x-demo-identity": "demo-customer"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def test_demo_reset_returns_a_replayable_scenario(client: TestClient):
    response = client.post("/api/v1/demo/reset")

    assert response.status_code == 200
    body = response.json()
    assert body["scenario_id"] == "lunch-rush"
    assert body["step_index"] == 0
    assert body["steps_total"] > 0


def test_demo_advance_rejects_more_than_twenty_steps(client: TestClient):
    response = client.post("/api/v1/demo/advance", json={"event_count": 21})

    assert response.status_code == 422


def test_demo_advance_returns_a_safe_error_when_steps_are_exhausted(client: TestClient):
    snapshot = client.get("/api/v1/demo/scenario").json()
    total = snapshot["steps_total"]
    response = client.post("/api/v1/demo/advance", json={"event_count": total})
    assert response.status_code == 200
    assert response.json()["remaining_steps"] == 0
    assert response.json()["order"]["state"] == "delivered"

    exhausted = client.post("/api/v1/demo/advance", json={"event_count": 1})
    assert exhausted.status_code == 409
    assert exhausted.json()["detail"] == "No more demo events are available."


def test_demo_advance_rejection_does_not_mutate_the_scenario(client: TestClient):
    client.post("/api/v1/demo/reset")
    client.post("/api/v1/demo/advance", json={"event_count": 2})
    before = client.get("/api/v1/demo/scenario").json()

    rejected = client.post("/api/v1/demo/advance", json={"event_count": 20})

    assert rejected.status_code == 409
    assert client.get("/api/v1/demo/scenario").json() == before


@pytest.mark.parametrize("event_count", (True, "1", 0, 21))
def test_demo_advance_rejects_non_strict_or_out_of_bounds_counts(
    client: TestClient, event_count: object
):
    client.post("/api/v1/demo/reset")

    response = client.post("/api/v1/demo/advance", json={"event_count": event_count})

    assert response.status_code == 422


def test_demo_clock_advances_deterministic_time(client: TestClient):
    client.post("/api/v1/demo/reset")
    before = client.get("/api/v1/demo/scenario").json()["clock"]

    response = client.post("/api/v1/demo/clock", json={"minutes": 30})

    assert response.status_code == 200
    assert response.json()["clock"] > before


def test_scenario_reset_preserves_dynamic_orders(client: TestClient):
    """Interactive orders survive a demo reset; scenario records are removed."""
    client.post(
        "/api/v1/me/cart/items",
        json={"menu_item_id": "menu-sm-01", "quantity": 1},
        headers=CUSTOMER,
    )
    created = client.post(
        "/api/v1/me/orders/checkout",
        json={"address_id": "addr-casa", "payment_method": "pix"},
        headers={**CUSTOMER, "Idempotency-Key": f"key-{uuid.uuid4().hex[:8]}"},
    )
    dynamic_order_id = created.json()["order_id"]

    client.post("/api/v1/demo/advance", json={"event_count": 8})
    reset = client.post("/api/v1/demo/reset")
    assert reset.status_code == 200

    kept = client.get(f"/api/v1/orders/{dynamic_order_id}", headers=CUSTOMER)
    assert kept.status_code == 200
    assert kept.json()["id"] == dynamic_order_id

    snapshot = client.get("/api/v1/demo/scenario").json()
    assert snapshot["order"] is None
    assert snapshot["step_index"] == 0


def test_full_scenario_replay_reaches_delivered(client: TestClient):
    snapshot = client.get("/api/v1/demo/scenario").json()
    total = snapshot["steps_total"]
    response = client.post("/api/v1/demo/advance", json={"event_count": total})
    assert response.status_code == 200
    body = response.json()
    assert body["order"]["state"] == "delivered"
    assert body["delivery"]["status"] == "delivered"
    assert body["route"]["graph_id"] == "sao-paulo-centro"
    assert body["tracking_points"] == 2
    assert any("entregue" in n for n in body["notifications"])
