from delivery_platform.api.main import app


def test_openapi_title_uses_canonical_product_name():
    assert app.openapi()["info"]["title"] == "Entrega Clara API"
