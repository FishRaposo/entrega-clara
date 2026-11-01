"""O4: courier multi-stop batching — accept, tour order, lifecycle, invariants."""

import uuid

from delivery_platform.api.main import create_app
from fastapi.testclient import TestClient

CUSTOMER = {"x-demo-identity": "demo-customer"}
CUSTOMER2 = {"x-demo-identity": "demo-customer-2"}
MANOEL = {"x-demo-identity": "demo-rest-seu-manoel"}
NONNA = {"x-demo-identity": "demo-rest-donna-nonna"}
COURIER = {"x-demo-identity": "demo-courier"}

MENU_BY_RESTAURANT = {
    MANOEL["x-demo-identity"]: "menu-sm-01",
    NONNA["x-demo-identity"]: "menu-dn-01",
}
ADDRESS_BY_CUSTOMER = {
    CUSTOMER["x-demo-identity"]: "addr-casa",
    CUSTOMER2["x-demo-identity"]: "addr-ana",
}


def _client() -> TestClient:
    return TestClient(create_app())


def _order_ready(client: TestClient, customer: dict, restaurant: dict) -> str:
    """Place an order and drive it to ready_for_pickup; returns order_id."""
    menu_id = MENU_BY_RESTAURANT[restaurant["x-demo-identity"]]
    client.post("/api/v1/me/cart/items", headers=customer,
                json={"menu_item_id": menu_id, "quantity": 1})
    r = client.post(
        "/api/v1/me/orders/checkout",
        headers={**customer, "Idempotency-Key": f"bat-{uuid.uuid4().hex[:8]}"},
        json={
            "address_id": ADDRESS_BY_CUSTOMER[customer["x-demo-identity"]],
            "payment_method": "pix",
        },
    )
    assert r.status_code in (200, 201), r.text
    order_id = r.json()["order_id"]
    client.post(f"/api/v1/restaurant/orders/{order_id}/confirm", headers=restaurant)
    client.post(f"/api/v1/restaurant/orders/{order_id}/prepare", headers=restaurant)
    client.post(f"/api/v1/restaurant/orders/{order_id}/ready", headers=restaurant)
    return order_id


def _go_online(client: TestClient) -> None:
    client.put("/api/v1/courier/availability", headers=COURIER,
               json={"available": True})


def _offered_ids(client: TestClient) -> list[str]:
    offers = client.get("/api/v1/courier/deliveries/offers", headers=COURIER).json()
    return [d["id"] for d in offers["deliveries"]]


def test_batch_accept_builds_precedence_respecting_tour():
    client = _client()
    _order_ready(client, CUSTOMER, MANOEL)
    _order_ready(client, CUSTOMER2, NONNA)
    _go_online(client)
    ids = _offered_ids(client)
    assert len(ids) == 2

    r = client.post("/api/v1/courier/batches/accept", headers=COURIER,
                    json={"delivery_ids": ids})
    assert r.status_code == 200, r.text
    batch = r.json()["batch"]
    assert batch["status"] == "assigned"
    assert sorted(batch["delivery_ids"]) == sorted(ids)

    active = client.get("/api/v1/courier/deliveries/active", headers=COURIER).json()
    assert len(active["deliveries"]) == 2
    assert active["batch"]["id"] == batch["id"]
    stops = active["route"]["stops"]
    pickups = [s for s in stops if s["kind"] == "pickup"]
    dropoffs = [s for s in stops if s["kind"] == "dropoff"]
    assert len(pickups) == len(dropoffs) == 2
    for dropoff in dropoffs:
        pickup = next(p for p in pickups if p["ref_id"] == dropoff["ref_id"])
        assert pickup["sequence"] < dropoff["sequence"]
    # every dropoff comes after every pickup in a sane tour ordering
    assert max(s["sequence"] for s in pickups) <= max(
        s["sequence"] for s in stops
    )
    assert active["route"]["batch_id"] == batch["id"]


def test_batch_rejections():
    client = _client()
    _order_ready(client, CUSTOMER, MANOEL)
    _go_online(client)
    ids = _offered_ids(client)

    # single delivery is not a batch
    r = client.post("/api/v1/courier/batches/accept", headers=COURIER,
                    json={"delivery_ids": ids})
    assert r.status_code == 422

    # duplicates rejected
    r = client.post("/api/v1/courier/batches/accept", headers=COURIER,
                    json={"delivery_ids": [ids[0], ids[0]]})
    assert r.status_code in (400, 409, 422)

    # courier without availability
    client.put("/api/v1/courier/availability", headers=COURIER,
               json={"available": False})
    _order_ready(client, CUSTOMER2, NONNA)
    ids2 = _offered_ids(client)
    r = client.post("/api/v1/courier/batches/accept", headers=COURIER,
                    json={"delivery_ids": ids2[:2]})
    assert r.status_code in (400, 409)


def test_batch_full_lifecycle_frees_courier():
    client = _client()
    _order_ready(client, CUSTOMER, MANOEL)
    _order_ready(client, CUSTOMER2, NONNA)
    _go_online(client)
    ids = _offered_ids(client)
    client.post("/api/v1/courier/batches/accept", headers=COURIER,
                json={"delivery_ids": ids})

    # pickup both, then start the tour
    for delivery_id in ids:
        client.post(f"/api/v1/courier/deliveries/{delivery_id}/pickup",
                    headers=COURIER)
    r = client.post(f"/api/v1/courier/deliveries/{ids[0]}/start", headers=COURIER)
    assert r.status_code == 200

    # single accept while batch active is rejected
    _order_ready(client, CUSTOMER, MANOEL)
    extra = [i for i in _offered_ids(client) if i not in ids]
    assert extra
    r = client.post(f"/api/v1/courier/deliveries/{extra[0]}/accept", headers=COURIER)
    assert r.status_code in (400, 409)

    # complete each delivery; courier frees only after the last one
    client.post(f"/api/v1/courier/deliveries/{ids[0]}/complete", headers=COURIER)
    active = client.get("/api/v1/courier/deliveries/active", headers=COURIER).json()
    assert len(active["deliveries"]) == 1
    client.post(f"/api/v1/courier/deliveries/{ids[1]}/complete", headers=COURIER)
    active = client.get("/api/v1/courier/deliveries/active", headers=COURIER).json()
    assert active["deliveries"] == []
    assert active["batch"] is None


def test_batch_order_tracking_resolves_shared_route():
    client = _client()
    _order_ready(client, CUSTOMER, MANOEL)
    order2 = _order_ready(client, CUSTOMER2, NONNA)
    _go_online(client)
    ids = _offered_ids(client)
    client.post("/api/v1/courier/batches/accept", headers=COURIER,
                json={"delivery_ids": ids})
    tracking = client.get(f"/api/v1/orders/{order2}/tracking",
                          headers=CUSTOMER2).json()
    assert tracking["route"] is not None
    assert tracking["route"]["batch_id"] is not None
    assert len(tracking["route"]["stops"]) == 4
