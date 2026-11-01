"""O2: route-following GPS — points on the polyline, monotonic, deterministic."""

import uuid
from itertools import pairwise

from delivery_platform.api.main import create_app
from delivery_platform.domain.entities import GeoPoint
from delivery_platform.domain.geo import haversine_m, point_along_polyline
from fastapi.testclient import TestClient

CUSTOMER = {"x-demo-identity": "demo-customer"}
REST = {"x-demo-identity": "demo-rest-seu-manoel"}
COURIER = {"x-demo-identity": "demo-courier"}


def _client() -> TestClient:
    return TestClient(create_app())


def _en_route(client: TestClient) -> tuple[str, str]:
    client.post("/api/v1/me/cart/items", headers=CUSTOMER,
                json={"menu_item_id": "menu-sm-01", "quantity": 1})
    r = client.post("/api/v1/me/orders/checkout",
                    headers={**CUSTOMER, "Idempotency-Key": f"gps-{uuid.uuid4().hex[:8]}"},
                    json={"address_id": "addr-casa", "payment_method": "pix"})
    order_id = r.json()["order_id"]
    for step in ("confirm", "prepare", "ready"):
        client.post(f"/api/v1/restaurant/orders/{order_id}/{step}", headers=REST)
    client.put("/api/v1/courier/availability", headers=COURIER,
               json={"available": True})
    delivery_id = client.get("/api/v1/courier/deliveries/offers",
                             headers=COURIER).json()["deliveries"][0]["id"]
    client.post(f"/api/v1/courier/deliveries/{delivery_id}/accept", headers=COURIER)
    client.post(f"/api/v1/courier/deliveries/{delivery_id}/pickup", headers=COURIER)
    client.post(f"/api/v1/courier/deliveries/{delivery_id}/start", headers=COURIER)
    return order_id, delivery_id


def _dist_to_segment(p: GeoPoint, a: list[float], b: list[float]) -> float:
    pa, pb = GeoPoint(latitude=a[1], longitude=a[0]), GeoPoint(latitude=b[1], longitude=b[0])
    return min(
        haversine_m(p, GeoPoint(
            latitude=pa.latitude + (pb.latitude - pa.latitude) * t,
            longitude=pa.longitude + (pb.longitude - pa.longitude) * t,
        ))
        for t in (0.0, 0.25, 0.5, 0.75, 1.0)
    )


def test_route_advance_points_stay_on_polyline_and_monotonic():
    client = _client()
    order_id, delivery_id = _en_route(client)
    tracking = client.get(f"/api/v1/orders/{order_id}/tracking",
                          headers=CUSTOMER).json()
    coords = tracking["route"]["geometry"]["coordinates"]

    positions = []
    for _ in range(3):
        r = client.post(
            f"/api/v1/courier/deliveries/{delivery_id}/route-advance",
            headers=COURIER)
        assert r.status_code == 200, r.text
        positions.extend(r.json()["events"])

    seqs = [e["sequence"] for e in positions]
    assert seqs == sorted(seqs)
    for e in positions:
        point = GeoPoint(latitude=e["latitude"], longitude=e["longitude"])
        on_line = min(
            _dist_to_segment(point, a, b)
            for a, b in pairwise(coords)
        )
        assert on_line < 50, f"point {on_line:.0f} m off route"


def test_route_advance_requires_en_route():
    client = _client()
    client.post("/api/v1/me/cart/items", headers=CUSTOMER,
                json={"menu_item_id": "menu-sm-01", "quantity": 1})
    r = client.post("/api/v1/me/orders/checkout",
                    headers={**CUSTOMER, "Idempotency-Key": f"gps2-{uuid.uuid4().hex[:8]}"},
                    json={"address_id": "addr-casa", "payment_method": "pix"})
    order_id = r.json()["order_id"]
    for step in ("confirm", "prepare", "ready"):
        client.post(f"/api/v1/restaurant/orders/{order_id}/{step}", headers=REST)
    client.put("/api/v1/courier/availability", headers=COURIER,
               json={"available": True})
    delivery_id = client.get("/api/v1/courier/deliveries/offers",
                             headers=COURIER).json()["deliveries"][0]["id"]
    client.post(f"/api/v1/courier/deliveries/{delivery_id}/accept", headers=COURIER)
    r = client.post(
        f"/api/v1/courier/deliveries/{delivery_id}/route-advance", headers=COURIER)
    assert r.status_code in (400, 409)


def test_point_along_polyline_edges():
    coords = [[-46.64, -23.55], [-46.63, -23.55]]
    start = point_along_polyline(coords, 0.0)
    end = point_along_polyline(coords, 1.0)
    mid = point_along_polyline(coords, 0.5)
    assert (start.longitude, start.latitude) == (-46.64, -23.55)
    assert (end.longitude, end.latitude) == (-46.63, -23.55)
    assert abs(mid.longitude + 46.635) < 1e-3
