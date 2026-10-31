"""Phase 2 API tests: catalog, cart, coupons, checkout, idempotency, errors."""

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


def _add_item(client: TestClient, item_id: str = "menu-sm-01", qty: int = 1) -> dict:
    response = client.post(
        "/api/v1/me/cart/items",
        json={"menu_item_id": item_id, "quantity": qty},
        headers=CUSTOMER,
    )
    assert response.status_code == 201
    return response.json()


# --- catalog ---


def test_catalog_lists_seeded_restaurants(client: TestClient):
    response = client.get("/api/v1/restaurants")
    assert response.status_code == 200
    names = [r["name"] for r in response.json()["restaurants"]]
    assert "Seu Manoel Marmitas" in names
    assert "Tanaka Sushi Express" in names


def test_catalog_filters_by_cuisine_and_query(client: TestClient):
    by_cuisine = client.get("/api/v1/restaurants", params={"cuisine": "japonesa"})
    assert [r["id"] for r in by_cuisine.json()["restaurants"]] == ["rest-tanaka"]

    by_query = client.get("/api/v1/restaurants", params={"query": "marmita"})
    ids = [r["id"] for r in by_query.json()["restaurants"]]
    assert ids == ["rest-seu-manoel"]


def test_restaurant_detail_and_menu(client: TestClient):
    detail = client.get("/api/v1/restaurants/rest-seu-manoel")
    assert detail.status_code == 200
    assert detail.json()["delivery_fee_minor"] == 500

    menu = client.get("/api/v1/restaurants/rest-seu-manoel/menu")
    assert menu.status_code == 200
    item_ids = [item["id"] for item in menu.json()["items"]]
    assert "menu-sm-01" in item_ids
    assert "menu-sm-04" in item_ids  # unavailable items still listed, flagged

    missing = client.get("/api/v1/restaurants/rest-inexistente")
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"


# --- cart ---


def test_cart_add_update_remove_flow(client: TestClient):
    cart = _add_item(client, "menu-sm-01", qty=2)
    assert cart["subtotal_minor"] == 4580
    assert cart["delivery_fee_minor"] == 500
    assert cart["total_minor"] == 5080
    line_id = cart["lines"][0]["id"]

    updated = client.patch(
        f"/api/v1/me/cart/items/{line_id}",
        json={"quantity": 1, "observation": "sem cebola"},
        headers=CUSTOMER,
    )
    assert updated.status_code == 200
    assert updated.json()["lines"][0]["observation"] == "sem cebola"
    assert updated.json()["subtotal_minor"] == 2290

    removed = client.delete(f"/api/v1/me/cart/items/{line_id}", headers=CUSTOMER)
    assert removed.status_code == 204
    empty = client.get("/api/v1/me/cart", headers=CUSTOMER).json()
    assert empty["lines"] == []
    assert empty["restaurant_id"] is None


def test_cart_rejects_items_from_a_second_restaurant(client: TestClient):
    _add_item(client, "menu-sm-01")
    response = client.post(
        "/api/v1/me/cart/items",
        json={"menu_item_id": "menu-dn-01", "quantity": 1},
        headers=CUSTOMER,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "cart_restaurant_conflict"


def test_cart_rejects_unavailable_items_and_restaurants(client: TestClient):
    unavailable_item = client.post(
        "/api/v1/me/cart/items",
        json={"menu_item_id": "menu-sm-04", "quantity": 1},
        headers=CUSTOMER,
    )
    assert unavailable_item.status_code == 422
    assert unavailable_item.json()["code"] == "item_unavailable"

    closed_restaurant = client.post(
        "/api/v1/me/cart/items",
        json={"menu_item_id": "menu-md-01", "quantity": 1},
        headers=CUSTOMER,
    )
    assert closed_restaurant.status_code == 422
    assert closed_restaurant.json()["code"] == "restaurant_unavailable"


# --- coupons ---


def test_coupon_apply_and_remove(client: TestClient):
    _add_item(client, "menu-sm-01", qty=2)
    applied = client.post(
        "/api/v1/me/cart/coupon", json={"code": "BEM-VINDO-DEMO"}, headers=CUSTOMER
    )
    assert applied.status_code == 200
    assert applied.json()["discount_minor"] == 500
    assert applied.json()["total_minor"] == 4580 - 500 + 500

    removed = client.delete("/api/v1/me/cart/coupon", headers=CUSTOMER)
    assert removed.status_code == 204
    cart = client.get("/api/v1/me/cart", headers=CUSTOMER).json()
    assert cart["discount_minor"] == 0


def test_invalid_expired_and_below_minimum_coupons_leave_cart_unchanged(client: TestClient):
    _add_item(client, "menu-sm-01", qty=1)  # subtotal 2290 < 2500 min for BEM-VINDO-DEMO
    below_min = client.post(
        "/api/v1/me/cart/coupon", json={"code": "BEM-VINDO-DEMO"}, headers=CUSTOMER
    )
    assert below_min.status_code == 422
    assert below_min.json()["code"] == "coupon_invalid"

    expired = client.post(
        "/api/v1/me/cart/coupon", json={"code": "EXPIRADO2020"}, headers=CUSTOMER
    )
    assert expired.status_code == 422
    assert expired.json()["code"] == "coupon_expired"

    unknown = client.post(
        "/api/v1/me/cart/coupon", json={"code": "NAO-EXISTE"}, headers=CUSTOMER
    )
    assert unknown.json()["code"] == "coupon_invalid"

    cart = client.get("/api/v1/me/cart", headers=CUSTOMER).json()
    assert cart["coupon_code"] is None
    assert cart["discount_minor"] == 0


# --- checkout ---


def _checkout(client: TestClient, key: str, **overrides: object) -> object:
    body = {
        "address_id": "addr-casa",
        "payment_method": "pix",
        **overrides,
    }
    return client.post(
        "/api/v1/me/orders/checkout", json=body, headers={**CUSTOMER, "Idempotency-Key": key}
    )


def test_checkout_creates_order_with_item_snapshots(client: TestClient):
    _add_item(client, "menu-sm-01", qty=2)
    _add_item(client, "menu-sm-03", qty=1)
    client.post("/api/v1/me/cart/coupon", json={"code": "BEM-VINDO-DEMO"}, headers=CUSTOMER)

    response = _checkout(client, f"key-{uuid.uuid4().hex[:8]}")
    assert response.status_code == 201
    order_id = response.json()["order_id"]
    assert response.json()["state"] == "placed"
    assert response.json()["payment"]["status"] == "approved"
    assert response.json()["total_minor"] == 2290 * 2 + 600 - 500 + 500

    detail = client.get(f"/api/v1/orders/{order_id}", headers=CUSTOMER).json()
    assert detail["items"][0]["name"] == "Marmita executiva de frango"
    assert detail["items"][0]["unit_price_minor"] == 2290
    assert detail["subtotal_minor"] == 5180
    assert detail["discount_minor"] == 500

    cart = client.get("/api/v1/me/cart", headers=CUSTOMER).json()
    assert cart["lines"] == []

    orders = client.get("/api/v1/me/orders", headers=CUSTOMER).json()["orders"]
    assert [o["id"] for o in orders] == [order_id]


def test_checkout_declined_payment_leaves_no_order(client: TestClient):
    _add_item(client, "menu-sm-01")
    response = _checkout(
        client, f"key-{uuid.uuid4().hex[:8]}", simulate_outcome="declined"
    )
    assert response.status_code == 422
    assert response.json()["code"] == "payment_declined"

    orders = client.get("/api/v1/me/orders", headers=CUSTOMER).json()["orders"]
    assert orders == []
    # Cart survives a declined payment so the customer can retry.
    cart = client.get("/api/v1/me/cart", headers=CUSTOMER).json()
    assert len(cart["lines"]) == 1


def test_checkout_empty_cart_and_missing_key(client: TestClient):
    empty = _checkout(client, f"key-{uuid.uuid4().hex[:8]}")
    assert empty.status_code == 422
    assert empty.json()["code"] == "cart_empty"

    _add_item(client)
    no_key = client.post(
        "/api/v1/me/orders/checkout",
        json={"address_id": "addr-casa", "payment_method": "pix"},
        headers=CUSTOMER,
    )
    assert no_key.status_code == 422


def test_idempotent_replay_and_conflict(client: TestClient):
    _add_item(client, "menu-sm-01")
    key = f"key-{uuid.uuid4().hex[:8]}"

    first = _checkout(client, key)
    assert first.status_code == 201
    order_id = first.json()["order_id"]

    replay = _checkout(client, key)
    assert replay.status_code == 201
    assert replay.json()["order_id"] == order_id
    assert replay.json()["replayed"] is True

    orders = client.get("/api/v1/me/orders", headers=CUSTOMER).json()["orders"]
    assert len(orders) == 1

    conflict = _checkout(client, key, payment_method="card")
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


def test_checkout_rejects_another_customers_address(client: TestClient):
    # customer-2 builds a cart, then tries to deliver to customer-1's address
    client.post(
        "/api/v1/me/cart/items",
        json={"menu_item_id": "menu-sm-01", "quantity": 1},
        headers=CUSTOMER_2,
    )
    response = client.post(
        "/api/v1/me/orders/checkout",
        json={"address_id": "addr-casa", "payment_method": "pix"},
        headers={**CUSTOMER_2, "Idempotency-Key": f"key-{uuid.uuid4().hex[:8]}"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "ownership_forbidden"


def test_order_detail_denies_other_customers(client: TestClient):
    _add_item(client, "menu-sm-01")
    created = _checkout(client, f"key-{uuid.uuid4().hex[:8]}")
    order_id = created.json()["order_id"]

    other = client.get(f"/api/v1/orders/{order_id}", headers=CUSTOMER_2)
    assert other.status_code == 403
    assert other.json()["code"] == "ownership_forbidden"

    operator = client.get(f"/api/v1/orders/{order_id}", headers=RESTAURANT)
    assert operator.status_code == 200  # restaurant operator can read its orders

    ops = client.get(f"/api/v1/orders/{order_id}", headers=OPERATIONS)
    assert ops.status_code == 200


# --- authorization & error envelope ---


def test_missing_identity_returns_401(client: TestClient):
    response = client.get("/api/v1/me/cart")
    assert response.status_code == 401
    assert response.json()["code"] == "identity_required"


def test_restaurant_role_cannot_use_customer_cart(client: TestClient):
    response = client.get("/api/v1/me/cart", headers=RESTAURANT)
    assert response.status_code == 403
    assert response.json()["code"] == "role_forbidden"


def test_malformed_request_returns_envelope_not_stack(client: TestClient):
    response = client.post(
        "/api/v1/me/cart/items",
        json={"menu_item_id": 123, "quantity": "two"},
        headers=CUSTOMER,
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert "Traceback" not in str(body)
    assert "correlation_id" in body


def test_checkout_at_closed_restaurant_is_rejected(client: TestClient):
    # Force a cart against rest-madrugada via direct store mutation is not an
    # API path; instead verify the unavailable restaurant rejects items already
    # covered. Here verify checkout honors availability changes mid-flow.
    _add_item(client, "menu-sm-01")
    container = client.app.state.container  # type: ignore[attr-defined]
    container.store.restaurants["rest-seu-manoel"].available = False

    response = _checkout(client, f"key-{uuid.uuid4().hex[:8]}")
    assert response.status_code == 422
    assert response.json()["code"] == "restaurant_unavailable"


def test_notification_and_tracking_endpoints(client: TestClient):
    _add_item(client, "menu-sm-01")
    created = _checkout(client, f"key-{uuid.uuid4().hex[:8]}")
    order_id = created.json()["order_id"]

    tracking = client.get(f"/api/v1/orders/{order_id}/tracking", headers=CUSTOMER)
    assert tracking.status_code == 200
    assert tracking.json()["order_status"] == "placed"
    assert tracking.json()["positions"] == []

    notifications = client.get(
        f"/api/v1/orders/{order_id}/notifications", headers=CUSTOMER
    )
    assert notifications.status_code == 200
    messages = [n["message"] for n in notifications.json()["notifications"]]
    assert any("Pedido realizado" in m for m in messages)
