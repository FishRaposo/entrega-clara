"""Phase 5 API tests: authorized SSE stream + operations read endpoints."""

import json
import threading
import uuid

import pytest
from delivery_platform.api.main import create_app
from fastapi.testclient import TestClient

CUSTOMER = {"x-demo-identity": "demo-customer"}
CUSTOMER_2 = {"x-demo-identity": "demo-customer-2"}
RESTAURANT = {"x-demo-identity": "demo-rest-seu-manoel"}
OPERATIONS = {"x-demo-identity": "demo-operations"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def _place_order(client: TestClient) -> str:
    client.post(
        "/api/v1/me/cart/items",
        json={"menu_item_id": "menu-sm-01", "quantity": 1},
        headers=CUSTOMER,
    )
    response = client.post(
        "/api/v1/me/orders/checkout",
        json={"address_id": "addr-casa", "payment_method": "pix"},
        headers={**CUSTOMER, "Idempotency-Key": f"key-{uuid.uuid4().hex[:8]}"},
    )
    assert response.status_code == 201
    return response.json()["order_id"]


def _next_lines(iterator, count: int) -> list[str]:
    """Pull up to count non-empty SSE lines from a live iterator."""
    lines: list[str] = []
    for line in iterator:
        if line:
            lines.append(line)
        if len(lines) >= count:
            break
    return lines


# --- SSE stream ---


def test_stream_sends_snapshot_first(client: TestClient):
    order_id = _place_order(client)
    with client.stream(
        "GET", f"/api/v1/orders/{order_id}/stream", headers=CUSTOMER
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        lines = _next_lines(response.iter_lines(), 2)
    assert lines[0] == "event: snapshot"
    snapshot = json.loads(lines[1].removeprefix("data: "))
    assert snapshot["id"] == order_id
    assert snapshot["state"] == "placed"


def test_stream_pushes_committed_events(client: TestClient):
    order_id = _place_order(client)
    with client.stream(
        "GET", f"/api/v1/orders/{order_id}/stream", headers=CUSTOMER
    ) as response:
        iterator = response.iter_lines()
        lines = _next_lines(iterator, 2)  # consume snapshot
        assert lines[0] == "event: snapshot"

        # Confirm the order from another thread while the stream is open.
        def confirm() -> None:
            client.post(
                f"/api/v1/restaurant/orders/{order_id}/confirm", headers=RESTAURANT
            )

        worker = threading.Thread(target=confirm)
        worker.start()
        seen_types: list[str] = []
        for line in iterator:
            if line.startswith("event: ") and line != "event: snapshot":
                seen_types.append(line.removeprefix("event: "))
            if "order.confirmed" in seen_types:
                break
        worker.join(timeout=5)
    assert "order.confirmed" in seen_types


def test_stream_requires_authorization(client: TestClient):
    order_id = _place_order(client)
    response = client.get(f"/api/v1/orders/{order_id}/stream", headers=CUSTOMER_2)
    assert response.status_code == 403
    missing = client.get(f"/api/v1/orders/{order_id}/stream")
    assert missing.status_code == 401


def test_stream_reconnect_returns_current_snapshot(client: TestClient):
    order_id = _place_order(client)
    client.post(f"/api/v1/restaurant/orders/{order_id}/confirm", headers=RESTAURANT)
    with client.stream(
        "GET", f"/api/v1/orders/{order_id}/stream", headers=CUSTOMER
    ) as response:
        lines = _next_lines(response.iter_lines(), 2)
    snapshot = json.loads(lines[1].removeprefix("data: "))
    assert snapshot["state"] == "confirmed"  # snapshot reflects current state


# --- operations ---


def test_operations_reads_orders_events_metrics(client: TestClient):
    order_id = _place_order(client)
    client.post(f"/api/v1/restaurant/orders/{order_id}/confirm", headers=RESTAURANT)

    orders = client.get("/api/v1/operations/orders", headers=OPERATIONS).json()
    assert any(o["id"] == order_id for o in orders["orders"])

    detail = client.get(
        f"/api/v1/operations/orders/{order_id}", headers=OPERATIONS
    ).json()
    assert detail["state"] == "confirmed"
    assert detail["payment"]["status"] == "approved"

    events = client.get("/api/v1/operations/events", headers=OPERATIONS).json()["events"]
    types = {e["type"] for e in events}
    assert "order.placed" in types
    assert "payment.approved" in types
    assert "order.confirmed" in types
    assert all(e["sequence"] >= 1 for e in events)

    metrics = client.get("/api/v1/operations/metrics", headers=OPERATIONS).json()
    assert metrics["orders_total"] == 1
    assert metrics["orders_by_state"]["confirmed"] == 1
    assert metrics["payments_approved"] == 1

    couriers = client.get("/api/v1/operations/couriers", headers=OPERATIONS).json()
    assert {c["id"] for c in couriers["couriers"]} == {"courier-ana", "courier-bruno"}

    audit = client.get("/api/v1/operations/audit", headers=OPERATIONS).json()
    actions = {a["action"] for a in audit["audit_events"]}
    assert "order.created" in actions
    assert "order.confirmed" in actions


def test_operations_events_since_filter(client: TestClient):
    _place_order(client)
    events = client.get("/api/v1/operations/events", headers=OPERATIONS).json()["events"]
    max_seq = max(e["sequence"] for e in events)
    later = client.get(
        "/api/v1/operations/events", params={"since": max_seq}, headers=OPERATIONS
    ).json()["events"]
    assert later == []


def test_operations_requires_operations_role(client: TestClient):
    order_id = _place_order(client)
    for path in (
        "/api/v1/operations/orders",
        f"/api/v1/operations/orders/{order_id}",
        "/api/v1/operations/events",
        "/api/v1/operations/metrics",
        "/api/v1/operations/audit",
        "/api/v1/operations/couriers",
    ):
        response = client.get(path, headers=CUSTOMER)
        assert response.status_code == 403, path
        assert response.json()["code"] == "role_forbidden"
