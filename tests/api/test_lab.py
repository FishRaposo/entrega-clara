"""Lab API: bounded deterministic experiments behind demo identity."""

from delivery_platform.api.main import create_app
from fastapi.testclient import TestClient


def _client() -> TestClient:
    return TestClient(create_app())


def test_graph_summary():
    client = _client()
    r = client.get(
        "/api/v1/lab/graph?graph=synthetic",
        headers={"x-demo-identity": "demo-operations"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["graph_id"] == "sao-paulo-centro"
    assert body["node_count"] == 77
    assert body["edge_count"] == 302
    assert len(body["ids"]) == len(body["nodes"]) == 77
    assert len(body["edges"]) == 302
    assert all(len(edge) == 3 for edge in body["edges"])


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
            "graph": "synthetic",
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
        "/api/v1/lab/graph?graph=synthetic",
        headers={"x-demo-identity": "demo-operations"},
    ).json()
    nodes = graph["ids"][::10][:6]
    r = client.post(
        "/api/v1/lab/tsp",
        headers={"x-demo-identity": "demo-operations"},
        json={"nodes": nodes, "solver": "two-opt", "objective": "time", "graph": "synthetic"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["route"][0] == nodes[0]
    assert sorted(body["route"][:-1]) == sorted(nodes)


def test_path_experiment_exposes_the_solver_ladder():
    client = _client()
    costs: dict[str, float] = {}
    for solver in ("astar", "dijkstra", "alt", "bidirectional"):
        r = client.post(
            "/api/v1/lab/path",
            headers={"x-demo-identity": "demo-operations"},
            json={
                "origin": "n-00-00",
                "destination": "n-06-10",
                "solver": solver,
                "objective": "time",
                "trace": True,
                "graph": "synthetic",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        costs[solver] = body["cost"]
        assert len(body["expanded_order"]) == body["nodes_expanded"]
        assert len(body["frontier_sizes"]) == body["nodes_expanded"]
        assert len(body["expansion_costs"]) == body["nodes_expanded"]
    assert len({round(cost, 6) for cost in costs.values()}) == 1


def test_weighted_astar_reports_its_epsilon():
    client = _client()
    r = client.post(
        "/api/v1/lab/path",
        headers={"x-demo-identity": "demo-operations"},
        json={
            "origin": "n-00-00",
            "destination": "n-06-10",
            "solver": "weighted-astar",
            "objective": "time",
            "epsilon": 2.5,
            "graph": "synthetic",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["solver_name"] == "weighted-astar-eps2.5"


def test_alt_reports_preprocessing_time():
    client = _client()
    r = client.post(
        "/api/v1/lab/path",
        headers={"x-demo-identity": "demo-operations"},
        json={
            "origin": "n-00-00",
            "destination": "n-06-10",
            "solver": "alt",
            "landmarks": 4,
            "graph": "synthetic",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["preprocessing_time_ns"] > 0


def test_lab_requires_identity():
    client = _client()
    assert client.get("/api/v1/lab/graph").status_code in (401, 403)


def test_benchmarks_endpoint_serves_committed_artifact():
    client = _client()
    r = client.get(
        "/api/v1/lab/benchmarks", headers={"x-demo-identity": "demo-operations"}
    )
    assert r.status_code == 200
    body = r.json()
    assert "tsp_graph" in body
    assert body["tsp_graph"]


def test_graph_payload_is_compact_and_gzip_encoded():
    client = _client()
    r = client.get(
        "/api/v1/lab/graph?graph=synthetic",
        headers={
            "x-demo-identity": "demo-operations",
            "Accept-Encoding": "gzip",
        },
    )
    assert r.status_code == 200
    body = r.json()
    # Index-aligned arrays: ids[i] names nodes[i], edges reference those indices.
    assert len(body["ids"]) == len(body["nodes"])
    size = len(body["ids"])
    assert all(0 <= edge[0] < size and 0 <= edge[1] < size for edge in body["edges"])
    # GZipMiddleware compresses the graph document for the browser.
    assert "gzip" in (r.headers.get("content-encoding") or "").lower() or (
        "accept-encoding" in (r.headers.get("vary") or "").lower()
    )


def test_graph_selector_rejects_unknown_names():
    client = _client()
    r = client.get(
        "/api/v1/lab/graph?graph=atlantis",
        headers={"x-demo-identity": "demo-operations"},
    )
    assert r.status_code == 422
