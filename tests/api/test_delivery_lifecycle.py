"""Phase 3 API tests: restaurant queue, courier lifecycle, invariants."""

import uuid

import pytest
from delivery_platform.api.main import create_app
from fastapi.testclient import TestClient

CUSTOMER = {"x-demo-identity": "demo-customer"}
RESTAURANT = {"x-demo-identity": "demo-rest-seu-manoel"}
OTHER_RESTAURANT = {"x-demo-identity": "demo-rest-tanaka"}
COURIER = {"x-demo-identity": "demo-courier"}
COURIER_2 = {"x-demo-identity": "demo-courier-bruno"}
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


def _drive_to_ready(client: TestClient, order_id: str) -> str:
    """Confirm + prepare + ready; returns the offered delivery id."""
    for action in ("confirm", "prepare", "ready"):
        response = client.post(
            f"/api/v1/restaurant/orders/{order_id}/{action}", headers=RESTAURANT
        )
        assert response.status_code == 200, (action, response.json())
    offers = client.get("/api/v1/courier/deliveries/offers", headers=COURIER).json()
    delivery = next(d for d in offers["deliveries"] if d["order_id"] == order_id)
    return delivery["id"]


def _accept(client: TestClient, delivery_id: str, headers: dict = COURIER) -> None:
    response = client.post(
        f"/api/v1/courier/deliveries/{delivery_id}/accept", headers=headers
    )
    assert response.status_code == 200, response.json()


# --- restaurant ---


def test_restaurant_queue_and_lifecycle(client: TestClient):
    order_id = _place_order(client)

    queue = client.get("/api/v1/restaurant/orders", headers=RESTAURANT).json()["orders"]
    assert [o["id"] for o in queue] == [order_id]
    assert queue[0]["state"] == "placed"

    client.post(f"/api/v1/restaurant/orders/{order_id}/confirm", headers=RESTAURANT)
    client.post(f"/api/v1/restaurant/orders/{order_id}/prepare", headers=RESTAURANT)
    client.post(f"/api/v1/restaurant/orders/{order_id}/ready", headers=RESTAURANT)

    state = client.get(f"/api/v1/orders/{order_id}", headers=CUSTOMER).json()["state"]
    assert state == "ready_for_pickup"


def test_restaurant_cannot_touch_another_restaurants_order(client: TestClient):
    order_id = _place_order(client)
    response = client.post(
        f"/api/v1/restaurant/orders/{order_id}/confirm", headers=OTHER_RESTAURANT
    )
    assert response.status_code == 403
    assert response.json()["code"] == "ownership_forbidden"
    state = client.get(f"/api/v1/orders/{order_id}", headers=CUSTOMER).json()["state"]
    assert state == "placed"


def test_restaurant_cannot_skip_states(client: TestClient):
    order_id = _place_order(client)
    response = client.post(
        f"/api/v1/restaurant/orders/{order_id}/prepare", headers=RESTAURANT
    )
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_transition"
    state = client.get(f"/api/v1/orders/{order_id}", headers=CUSTOMER).json()["state"]
    assert state == "placed"


def test_customer_cannot_use_restaurant_endpoints(client: TestClient):
    order_id = _place_order(client)
    response = client.post(
        f"/api/v1/restaurant/orders/{order_id}/confirm", headers=CUSTOMER
    )
    assert response.status_code == 403
    assert response.json()["code"] == "role_forbidden"


# --- courier lifecycle ---


def test_full_delivery_lifecycle(client: TestClient):
    order_id = _place_order(client)
    delivery_id = _drive_to_ready(client, order_id)

    _accept(client, delivery_id)
    active = client.get("/api/v1/courier/deliveries/active", headers=COURIER).json()
    assert active["delivery"]["id"] == delivery_id
    assert active["delivery"]["status"] == "assigned"

    pickup = client.post(
        f"/api/v1/courier/deliveries/{delivery_id}/pickup", headers=COURIER
    )
    assert pickup.json()["delivery"]["status"] == "picked_up"

    started = client.post(
        f"/api/v1/courier/deliveries/{delivery_id}/start", headers=COURIER
    )
    assert started.json()["delivery"]["status"] == "en_route"

    detail = client.get(f"/api/v1/orders/{order_id}", headers=CUSTOMER).json()
    assert detail["state"] == "en_route"
    assert detail["route"] is not None
    assert detail["route"]["distance_meters"] > 0
    assert detail["route"]["solver_name"] == "astar-synthetic-graph"
    assert detail["route"]["graph_id"] == "sao-paulo-centro"

    loc = client.post(
        f"/api/v1/courier/deliveries/{delivery_id}/location",
        json={"sequence": 1, "latitude": -23.5495, "longitude": -46.6345},
        headers=COURIER,
    )
    assert loc.status_code == 200
    assert loc.json()["position"]["sequence"] == 1

    done = client.post(
        f"/api/v1/courier/deliveries/{delivery_id}/complete", headers=COURIER
    )
    assert done.json()["delivery"]["status"] == "delivered"
    detail = client.get(f"/api/v1/orders/{order_id}", headers=CUSTOMER).json()
    assert detail["state"] == "delivered"

    active_after = client.get(
        "/api/v1/courier/deliveries/active", headers=COURIER
    ).json()
    assert active_after["delivery"] is None


def test_offline_courier_cannot_accept(client: TestClient):
    order_id = _place_order(client)
    delivery_id = _drive_to_ready(client, order_id)
    client.put(
        "/api/v1/courier/availability", json={"available": False}, headers=COURIER
    )
    response = client.post(
        f"/api/v1/courier/deliveries/{delivery_id}/accept", headers=COURIER
    )
    assert response.status_code == 409
    assert response.json()["code"] == "courier_unavailable"


def test_courier_cannot_hold_two_active_deliveries(client: TestClient):
    first = _drive_to_ready(client, _place_order(client))
    second = _drive_to_ready(client, _place_order(client))
    _accept(client, first)
    response = client.post(
        f"/api/v1/courier/deliveries/{second}/accept", headers=COURIER
    )
    assert response.status_code == 409
    assert response.json()["code"] == "courier_unavailable"


def test_courier_cannot_act_on_anothers_delivery(client: TestClient):
    order_id = _place_order(client)
    delivery_id = _drive_to_ready(client, order_id)
    _accept(client, delivery_id)

    # Bruno comes online but cannot touch Ana's delivery
    client.put(
        "/api/v1/courier/availability", json={"available": True}, headers=COURIER_2
    )
    response = client.post(
        f"/api/v1/courier/deliveries/{delivery_id}/pickup", headers=COURIER_2
    )
    assert response.status_code == 403
    assert response.json()["code"] == "ownership_forbidden"


def test_stale_location_is_rejected(client: TestClient):
    order_id = _place_order(client)
    delivery_id = _drive_to_ready(client, order_id)
    _accept(client, delivery_id)
    client.post(f"/api/v1/courier/deliveries/{delivery_id}/pickup", headers=COURIER)
    client.post(f"/api/v1/courier/deliveries/{delivery_id}/start", headers=COURIER)
    client.post(
        f"/api/v1/courier/deliveries/{delivery_id}/location",
        json={"sequence": 5, "latitude": -23.55, "longitude": -46.63},
        headers=COURIER,
    )
    stale = client.post(
        f"/api/v1/courier/deliveries/{delivery_id}/location",
        json={"sequence": 5, "latitude": -23.551, "longitude": -46.631},
        headers=COURIER,
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "stale_location"

    tracking = client.get(
        f"/api/v1/orders/{order_id}/tracking", headers=CUSTOMER
    ).json()
    assert len(tracking["positions"]) == 1


def test_location_before_pickup_is_rejected(client: TestClient):
    order_id = _place_order(client)
    delivery_id = _drive_to_ready(client, order_id)
    _accept(client, delivery_id)
    response = client.post(
        f"/api/v1/courier/deliveries/{delivery_id}/location",
        json={"sequence": 1, "latitude": -23.55, "longitude": -46.63},
        headers=COURIER,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_transition"


def test_courier_cannot_go_offline_mid_delivery(client: TestClient):
    order_id = _place_order(client)
    delivery_id = _drive_to_ready(client, order_id)
    _accept(client, delivery_id)
    response = client.put(
        "/api/v1/courier/availability", json={"available": False}, headers=COURIER
    )
    assert response.status_code == 409
    assert response.json()["code"] == "courier_unavailable"


def test_invalid_delivery_transition_leaves_state(client: TestClient):
    order_id = _place_order(client)
    delivery_id = _drive_to_ready(client, order_id)
    _accept(client, delivery_id)
    # start without pickup
    response = client.post(
        f"/api/v1/courier/deliveries/{delivery_id}/start", headers=COURIER
    )
    assert response.status_code == 409
    detail = client.get(f"/api/v1/orders/{order_id}", headers=CUSTOMER).json()
    assert detail["state"] == "courier_assigned"
    assert detail["route"] is None


def test_operations_can_read_but_not_mutate(client: TestClient):
    order_id = _place_order(client)
    read = client.get(f"/api/v1/orders/{order_id}", headers=OPERATIONS)
    assert read.status_code == 200

    mutate = client.post(
        f"/api/v1/restaurant/orders/{order_id}/confirm", headers=OPERATIONS
    )
    assert mutate.status_code == 403

    courier_mutate = client.post(
        "/api/v1/courier/deliveries/dlv-x/accept", headers=OPERATIONS
    )
    assert courier_mutate.status_code == 403
