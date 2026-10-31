"""ASGI entry point: composition, middleware, error envelope, routers."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, Request

from delivery_platform.adapters.seed.loader import load_reference_seed_file
from delivery_platform.api.errors import register_error_handlers
from delivery_platform.api.routes.catalog import router as catalog_router
from delivery_platform.api.routes.courier import router as courier_router
from delivery_platform.api.routes.demo import router as demo_router
from delivery_platform.api.routes.health import router as health_router
from delivery_platform.api.routes.lab import router as lab_router
from delivery_platform.api.routes.me import router as me_router
from delivery_platform.api.routes.operations import router as operations_router
from delivery_platform.api.routes.orders import router as orders_router
from delivery_platform.api.routes.restaurant import router as restaurant_router
from delivery_platform.application.container import build_container
from delivery_platform.core.config import settings
from delivery_platform.demo.runner import ScenarioRunner
from delivery_platform.domain.errors import DemoScenarioError

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[5]
_SEED_PATH = _REPO_ROOT / "data" / "seed" / "brazil.json"
_SCENARIO_PATH = _REPO_ROOT / "data" / "scenarios" / "lunch-rush.json"


def create_app() -> FastAPI:
    app = FastAPI(title="Entrega Clara API", version=settings.app_version)

    container = build_container(settings)
    if _SEED_PATH.exists():
        load_reference_seed_file(container.store, _SEED_PATH)
    else:
        logger.warning("Reference seed not found at %s; catalog starts empty", _SEED_PATH)
    app.state.container = container
    try:
        app.state.scenario_runner = ScenarioRunner.from_seed_file(container, _SCENARIO_PATH)
    except (OSError, TypeError, ValueError, DemoScenarioError) as error:
        # demo must not block the API boot
        logger.warning("Scenario runner unavailable (%s)", error)
        app.state.scenario_runner = None

    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.correlation_id = request.headers.get(
            "x-correlation-id", f"cor_{uuid.uuid4().hex[:12]}"
        )
        response = await call_next(request)
        response.headers["x-correlation-id"] = request.state.correlation_id
        return response

    register_error_handlers(app)

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(demo_router, prefix="/api/v1")
    app.include_router(catalog_router)
    app.include_router(me_router)
    app.include_router(orders_router)
    app.include_router(restaurant_router)
    app.include_router(courier_router)
    app.include_router(operations_router)
    app.include_router(lab_router, prefix="/api/v1")

    @app.get("/")
    def root() -> dict[str, str]:
        return {"health": "/api/v1/health"}

    return app


app = create_app()
