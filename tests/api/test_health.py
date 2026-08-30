from delivery_platform.api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_endpoint_reports_service_readiness():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "delivery-platform-api",
        "environment": "development",
        "demo_mode": True,
        "version": "0.1.0",
    }


def test_root_links_to_health_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"health": "/api/v1/health"}
