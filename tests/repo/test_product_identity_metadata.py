import json
from pathlib import Path

import tomllib

ROOT = Path(__file__).parents[2]


def test_product_identity_metadata_uses_entrega_clara():
    backend = tomllib.loads((ROOT / "app/backend/pyproject.toml").read_text())
    web = json.loads((ROOT / "app/web/package.json").read_text())
    lock = json.loads((ROOT / "app/web/package-lock.json").read_text())
    example_env = dict(
        line.split("=", maxsplit=1)
        for line in (ROOT / ".env.example").read_text().splitlines()
        if line and not line.startswith("#")
    )

    assert backend["project"]["name"] == "entrega-clara-backend"
    assert web["name"] == "entrega-clara-web"
    assert lock["name"] == web["name"]
    assert lock["packages"][""]["name"] == web["name"]
    assert example_env["APP_NAME"] == "Entrega Clara"
