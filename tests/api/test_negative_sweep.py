"""Negative-sweep checks from the M1 runbook §7 not covered elsewhere.

Covers: route-generation failure leaves a recoverable delivery, and a
route/map outage keeps the tracking timeline visible.
"""

import uuid

import pytest
from delivery_platform.adapters.memory.routing import StraightLineRoutePlanner
from delivery_platform.api.main import create_app
from delivery_platform.application.ports import DeliveryRouteRequest
from delivery_platform.domain.entities import RoutePlan
from delivery_platform.domain.errors import RouteUnavailableError
from fastapi.testclient import TestClient

CUSTOMER = {"x-demo-identity": "demo-customer"}
RESTAURANT = {"x-demo-identity": "demo-rest-seu-manoel"}
COURIER = {"x-demo-identity": "demo-courier"}


class FlakyRoutePlanner:
    """Fails once with a domain error, then delegates to the real planner."""

    solver_name = "flaky"
    solver_version = "0.0.1"

    def __init__(self) -> None:
        self._delegate = StraightLineRoutePlanner()
        self.failures_left = 1

    def plan(self, request: DeliveryRouteRequest, *, route_id: str) -> RoutePlan:
        if self.failures_left > 0:
            self.failures_left -= 1
            raise RouteUnavailableError()
        return self._delegate.plan(request, route_id=route_id)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def _drive_to_picked_up(client: TestClient) -> tuple[str, str]:
    """Place → confirm → prepare → ready → accept → pickup."""
    client.post(
        "/api/v1/me/cart/items",
        json={"menu_item_id": "menu-sm-01", "quantity": 1},
        headers=CUSTOMER,
    )
    order = client.post(
        "/api/v1/me/orders/checkout",
        json={"address_id": "addr-casa", "payment_method": "pix"},
        headers={**CUSTOMER, "Idempotency-Key": f"key-{uuid.uuid4().hex[:8]}"},
    ).json()
    order_id = order["order_id"]
    for action in ("confirm", "prepare", "ready"):
        response = client.post(
            f"/api/v1/restaurant/orders/{order_id}/{action}", headers=RESTAURANT
        )
        assert response.status_code == 200, (action, response.json())
    offers = client.get("/api/v1/courier/deliveries/offers", headers=COURIER).json()
    delivery_id = next(d["id"] for d in offers["deliveries"] if d["order_id"] == order_id)
    for action in ("accept", "pickup"):
        response = client.post(
            f"/api/v1/courier/deliveries/{delivery_id}/{action}", headers=COURIER
        )
        assert response.status_code == 200, (action, response.json())
    return order_id, delivery_id


def test_route_failure_leaves_recoverable_delivery(client: TestClient):
    order_id, delivery_id = _drive_to_picked_up(client)
    assert client.app.state.container is not None
    client.app.state.container.route_planner = FlakyRoutePlanner()

    failed = client.post(
        f"/api/v1/courier/deliveries/{delivery_id}/start", headers=COURIER
    )
    assert failed.status_code == 503
    envelope = failed.json()
    assert envelope["code"] == "route_unavailable"
    assert "traceback" not in envelope["detail"].lower()

    # The delivery and order are rolled back to a retryable state.
    active = client.get("/api/v1/courier/deliveries/active", headers=COURIER).json()
    assert active["delivery"]["status"] == "picked_up"
    order_view = client.get(f"/api/v1/orders/{order_id}", headers=CUSTOMER).json()
    assert order_view["state"] == "picked_up"

    retry = client.post(
        f"/api/v1/courier/deliveries/{delivery_id}/start", headers=COURIER
    )
    assert retry.status_code == 200
    assert retry.json()["delivery"]["status"] == "en_route"
    tracking = client.get(
        f"/api/v1/orders/{order_id}/tracking", headers=CUSTOMER
    ).json()
    assert tracking["route"] is not None


def test_map_outage_keeps_timeline_and_last_known_visible(client: TestClient):
    order_id, _ = _drive_to_picked_up(client)

    # No route plan exists yet, but the tracking read must not fail.
    tracking = client.get(f"/api/v1/orders/{order_id}/tracking", headers=CUSTOMER)
    assert tracking.status_code == 200
    body = tracking.json()
    assert body["route"] is None
    assert body["order_status"] == "picked_up"
    assert body["positions"] == []

    # Notifications (the timeline surface) remain readable without a route.
    notifications = client.get(
        f"/api/v1/orders/{order_id}/notifications", headers=CUSTOMER
    )
    assert notifications.status_code == 200
    assert len(notifications.json()["notifications"]) >= 2
