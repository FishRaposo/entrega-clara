"""Lab API: bounded deterministic experiments behind demo identity."""

from delivery_platform.api.main import create_app
from fastapi.testclient import TestClient


def _client() -> TestClient:
    return TestClient(create_app())


def test_graph_summary():
    client = _client()
    r = client.get("/api/v1/lab/graph", headers={"x-demo-identity": "demo-operations"})
    assert r.status_code == 200
    body = r.json()
    assert body["graph_id"] == "sao-paulo-centro"
    assert len(body["nodes"]) == 77
    assert len(body["edges"]) == 302


def test_path_experiment_astar_with_trace():
    client = _client()
    r = client.post(
        "/api/v1/lab/path",
        headers={"x-demo-identity": "demo-operations"},
        json={
            "origin": "n-00-00",
            "destination": "n-06-10",
            "solver": "astar",
            "objective": "time",
            "trace": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["node_path"][0] == "n-00-00"
    assert body["node_path"][-1] == "n-06-10"
    assert len(body["expanded_order"]) == body["nodes_expanded"]
    assert body["objective"] == "time"


def test_path_experiment_unknown_node_safe_error():
    client = _client()
    r = client.post(
        "/api/v1/lab/path",
        headers={"x-demo-identity": "demo-operations"},
        json={"origin": "nope", "destination": "n-00-00"},
    )
    assert r.status_code == 400
    assert "detail" in r.json()


def test_tsp_experiment_two_opt():
    client = _client()
    graph = client.get(
        "/api/v1/lab/graph", headers={"x-demo-identity": "demo-operations"}
    ).json()
    nodes = [n["id"] for n in graph["nodes"][::10][:6]]
    r = client.post(
        "/api/v1/lab/tsp",
        headers={"x-demo-identity": "demo-operations"},
        json={"nodes": nodes, "solver": "two-opt", "objective": "time"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["route"][0] == nodes[0]
    assert sorted(body["route"][:-1]) == sorted(nodes)


def test_lab_requires_identity():
    client = _client()
    assert client.get("/api/v1/lab/graph").status_code in (401, 403)


def test_benchmarks_endpoint_serves_committed_artifact():
    client = _client()
    r = client.get(
        "/api/v1/lab/benchmarks", headers={"x-demo-identity": "demo-operations"}
    )
    assert r.status_code == 200
    assert "tsp" in r.json()
