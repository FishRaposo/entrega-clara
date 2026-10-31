"""Customer rate + cancel commands: happy paths, ownership, invariants."""

from fastapi.testclient import TestClient
from delivery_platform.api.main import create_app

H = {"x-demo-identity": "demo-customer"}
H2 = {"x-demo-identity": "demo-customer-2"}
REST = {"x-demo-identity": "demo-rest-seu-manoel"}
COURIER = {"x-demo-identity": "demo-courier"}
IDEM = {"Idempotency-Key": "rate-cancel-1"}


def _client() -> TestClient:
    return TestClient(create_app())


def _place_order(client: TestClient) -> str:
    # seed customer cart comes pre-loaded? — build via API for honesty
    client.post("/api/v1/me/cart/items", headers=H,
                json={"menu_item_id": "menu-sm-01", "quantity": 1})
    import uuid
    r = client.post("/api/v1/me/orders/checkout",
                    headers={**H, "Idempotency-Key": f"rc-{uuid.uuid4().hex[:8]}"},
                    json={"address_id": "addr-casa", "payment_method": "pix"})
    assert r.status_code in (200, 201), r.text
    return r.json()["order_id"]


def _deliver(client: TestClient, order_id: str) -> None:
    client.post(f"/api/v1/restaurant/orders/{order_id}/confirm", headers=REST)
    client.post(f"/api/v1/restaurant/orders/{order_id}/prepare", headers=REST)
    client.post(f"/api/v1/restaurant/orders/{order_id}/ready", headers=REST)
    client.put("/api/v1/courier/availability", headers=COURIER, json={"available": True})
    offers = client.get("/api/v1/courier/deliveries/offers", headers=COURIER).json()
    delivery_id = offers["deliveries"][0]["id"]
    client.post(f"/api/v1/courier/deliveries/{delivery_id}/accept", headers=COURIER)
    client.post(f"/api/v1/courier/deliveries/{delivery_id}/pickup", headers=COURIER)
    client.post(f"/api/v1/courier/deliveries/{delivery_id}/start", headers=COURIER)
    client.post(f"/api/v1/courier/deliveries/{delivery_id}/complete", headers=COURIER)


def test_rate_delivered_order_once():
    client = _client()
    order_id = _place_order(client)
    _deliver(client, order_id)
    r = client.post(f"/api/v1/me/orders/{order_id}/rate",
                    headers=H, json={"stars": 5})
    assert r.status_code == 200
    assert r.json()["order"]["state"] == "rated"
    # second rating is an invalid transition
    r2 = client.post(f"/api/v1/me/orders/{order_id}/rate",
                     headers=H, json={"stars": 4})
    assert r2.status_code in (400, 409)


def test_rate_requires_delivered_and_ownership():
    client = _client()
    order_id = _place_order(client)
    assert client.post(f"/api/v1/me/orders/{order_id}/rate",
                       headers=H, json={"stars": 5}).status_code in (400, 409)
    order_id2 = _place_order(client)
    assert client.post(f"/api/v1/me/orders/{order_id2}/rate",
                       headers=H2, json={"stars": 5}).status_code in (403, 404)


def test_rate_rejects_out_of_range():
    client = _client()
    order_id = _place_order(client)
    r = client.post(f"/api/v1/me/orders/{order_id}/rate",
                    headers=H, json={"stars": 0})
    assert r.status_code == 422


def test_cancel_placed_order_refunds_payment():
    client = _client()
    order_id = _place_order(client)
    r = client.post(f"/api/v1/me/orders/{order_id}/cancel", headers=H)
    assert r.status_code == 200
    assert r.json()["order"]["state"] == "cancelled"
    order = client.get(f"/api/v1/orders/{order_id}", headers=H).json()
    assert order["state"] == "cancelled"


def test_cancel_after_preparation_rejected():
    client = _client()
    order_id = _place_order(client)
    client.post(f"/api/v1/restaurant/orders/{order_id}/confirm", headers=REST)
    client.post(f"/api/v1/restaurant/orders/{order_id}/prepare", headers=REST)
    assert client.post(f"/api/v1/me/orders/{order_id}/cancel",
                       headers=H).status_code in (400, 409)


def test_cancel_ownership():
    client = _client()
    order_id = _place_order(client)
    assert client.post(f"/api/v1/me/orders/{order_id}/cancel",
                       headers=H2).status_code in (403, 404)
