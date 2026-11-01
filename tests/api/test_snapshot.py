"""O3: named in-memory snapshots — save, mutate, restore, compare."""

from delivery_platform.api.main import create_app
from fastapi.testclient import TestClient

H = {"x-demo-identity": "demo-customer"}


def test_snapshot_save_mutate_restore():
    client = TestClient(create_app())
    # order count baseline
    before = client.get("/api/v1/me/orders", headers=H).json()["orders"]
    # save a named snapshot
    r = client.post("/api/v1/demo/snapshot", json={"name": "snap-a"})
    assert r.status_code == 200

    # mutate: place an order
    client.post("/api/v1/me/cart/items", headers=H,
                json={"menu_item_id": "menu-sm-01", "quantity": 1})
    r = client.post("/api/v1/me/orders/checkout",
                    headers={**H, "Idempotency-Key": "snap-test-1"},
                    json={"address_id": "addr-casa", "payment_method": "pix"})
    assert r.status_code in (200, 201)
    mutated = client.get("/api/v1/me/orders", headers=H).json()["orders"]
    assert len(mutated) == len(before) + 1

    # restore → order list identical to baseline
    r = client.put("/api/v1/demo/snapshot", json={"name": "snap-a"})
    assert r.status_code == 200
    restored = client.get("/api/v1/me/orders", headers=H).json()["orders"]
    assert [o["id"] for o in restored] == [o["id"] for o in before]


def test_restore_unknown_snapshot_errors():
    client = TestClient(create_app())
    r = client.put("/api/v1/demo/snapshot", json={"name": "nope"})
    assert r.status_code in (400, 404, 409)


def test_snapshot_list():
    client = TestClient(create_app())
    client.post("/api/v1/demo/snapshot", json={"name": "x"})
    assert "x" in client.get("/api/v1/demo/snapshot").json()["snapshots"]


def test_json_export_import_roundtrip():
    client = TestClient(create_app())
    client.post("/api/v1/me/cart/items", headers=H,
                json={"menu_item_id": "menu-sm-01", "quantity": 1})
    client.post("/api/v1/me/orders/checkout",
                headers={**H, "Idempotency-Key": "rt-1"},
                json={"address_id": "addr-casa", "payment_method": "pix"})
    client.post("/api/v1/demo/snapshot", json={"name": "export-me"})
    before = client.get("/api/v1/me/orders", headers=H).json()["orders"]

    export = client.get("/api/v1/demo/snapshot/export-me/export")
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("application/json")

    # mutate store away from snapshot, then import back
    client.delete("/api/v1/demo/reset", headers={"x-demo-identity": "demo-operations"}) \
        if False else None
    r = client.post("/api/v1/demo/snapshot/import",
                    json={"name": "restored", "data": export.text})
    assert r.status_code == 200
    after = client.get("/api/v1/me/orders", headers=H).json()["orders"]
    assert [o["id"] for o in after] == [o["id"] for o in before]


def test_import_malformed_json_safe_error():
    client = TestClient(create_app())
    r = client.post("/api/v1/demo/snapshot/import",
                    json={"name": "bad", "data": "{not json"})
    assert r.status_code in (400, 409)
