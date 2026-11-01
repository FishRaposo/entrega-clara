"""O1: operations timeline — stage durations from events, ETA accuracy."""

import uuid

from delivery_platform.api.main import create_app
from fastapi.testclient import TestClient

CUSTOMER = {"x-demo-identity": "demo-customer"}
REST = {"x-demo-identity": "demo-rest-seu-manoel"}
COURIER = {"x-demo-identity": "demo-courier"}
OPS = {"x-demo-identity": "demo-operations"}


def _completed_order(client: TestClient) -> str:
    client.post("/api/v1/me/cart/items", headers=CUSTOMER,
                json={"menu_item_id": "menu-sm-01", "quantity": 1})
    r = client.post("/api/v1/me/orders/checkout",
                    headers={**CUSTOMER, "Idempotency-Key": f"tl-{uuid.uuid4().hex[:8]}"},
                    json={"address_id": "addr-casa", "payment_method": "pix"})
    order_id = r.json()["order_id"]
    for step in ("confirm", "prepare", "ready"):
        client.post(f"/api/v1/restaurant/orders/{order_id}/{step}", headers=REST)
    client.put("/api/v1/courier/availability", headers=COURIER,
               json={"available": True})
    delivery_id = client.get("/api/v1/courier/deliveries/offers",
                             headers=COURIER).json()["deliveries"][0]["id"]
    for step in ("accept", "pickup", "start", "complete"):
        client.post(f"/api/v1/courier/deliveries/{delivery_id}/{step}",
                    headers=COURIER)
    return order_id


def test_timeline_reports_stages_in_order():
    client = TestClient(create_app())
    order_id = _completed_order(client)
    r = client.get("/api/v1/operations/timeline", headers=OPS)
    assert r.status_code == 200
    row = next(o for o in r.json()["orders"] if o["order_id"] == order_id)
    names = [s["stage"] for s in row["stages"]]
    assert names == [
        "placed", "confirmed", "ready", "picked_up", "en_route", "delivered",
    ]
    assert all(s["duration_seconds"] >= 0 for s in row["stages"])
    assert row["eta_estimated_seconds"] is not None
    assert row["eta_actual_seconds"] is not None
    assert row["eta_error_seconds"] >= 0


def test_timeline_requires_operations_role():
    client = TestClient(create_app())
    assert client.get("/api/v1/operations/timeline",
                      headers=CUSTOMER).status_code in (401, 403)
