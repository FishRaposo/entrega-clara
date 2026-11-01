"""Observability: Prometheus text, operations snapshot and routing counters."""

from delivery_platform.api.main import create_app
from delivery_platform.core.metrics import MetricsRegistry
from fastapi.testclient import TestClient

OPERATIONS = {"x-demo-identity": "demo-operations"}
CUSTOMER = {"x-demo-identity": "demo-customer"}


def test_registry_renders_counters_gauges_and_histograms():
    registry = MetricsRegistry()
    registry.inc("demo_requests_total", {"path": "/x"}, 3)
    registry.set_gauge("demo_connections", 2)
    registry.observe("demo_seconds", 0.02)
    registry.observe("demo_seconds", 7)

    text = registry.render()

    assert "# TYPE demo_requests_total counter" in text
    assert 'demo_requests_total{path="/x"} 3' in text
    assert "# TYPE demo_connections gauge" in text
    assert "demo_connections 2" in text
    assert "# TYPE demo_seconds histogram" in text
    assert 'demo_seconds_bucket{le="0.025"} 1' in text
    assert 'demo_seconds_bucket{le="+Inf"} 2' in text
    assert "demo_seconds_count 2" in text
    # One TYPE line per family, even with several labelled series.
    assert text.count("# TYPE demo_requests_total") == 1


def test_metrics_endpoint_exposes_http_series():
    client = TestClient(create_app())
    client.get("/api/v1/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "# TYPE entrega_http_requests_total counter" in body
    # The label is the route template as registered on the router (without the
    # /api/v1 include prefix), which keeps cardinality bounded.
    assert (
        'entrega_http_requests_total{method="GET",path="/health",status="200"}' in body
    )
    assert "entrega_http_request_seconds_bucket" in body


def test_operations_snapshot_is_role_guarded_and_shaped_for_the_panel():
    client = TestClient(create_app())
    denied = client.get("/api/v1/operations/metrics", headers=CUSTOMER)
    assert denied.status_code == 403

    allowed = client.get("/api/v1/operations/metrics", headers=OPERATIONS)
    assert allowed.status_code == 200
    body = allowed.json()
    assert body["persistence_mode"] == "memory"
    assert isinstance(body["counters"], list)
    assert isinstance(body["histograms"], list)


def test_routing_and_event_counters_move_when_the_app_works():
    client = TestClient(create_app())
    path = client.post(
        "/api/v1/lab/path",
        headers=OPERATIONS,
        json={
            "origin": "n-00-00",
            "destination": "n-06-10",
            "solver": "astar",
            "objective": "time",
            "trace": False,
            "graph": "synthetic",
        },
    )
    assert path.status_code == 200, path.text

    snapshot = client.get("/api/v1/operations/metrics", headers=OPERATIONS).json()
    counters = {entry["name"] for entry in snapshot["counters"]}
    assert "entrega_routing_queries_total" in counters
    histograms = {entry["name"] for entry in snapshot["histograms"]}
    assert "entrega_routing_seconds" in histograms
