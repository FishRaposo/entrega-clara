import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from delivery_platform.api.routes.demo import router as demo_router
from delivery_platform.api.routes.health import router as health_router
from delivery_platform.domain.errors import DemoScenarioError

app = FastAPI(title="Entrega Clara API", version="0.1.0")
app.include_router(health_router, prefix="/api/v1")
app.include_router(demo_router, prefix="/api/v1")


@app.exception_handler(DemoScenarioError)
async def demo_scenario_error_handler(request: Request, error: DemoScenarioError) -> JSONResponse:
    logging.getLogger(__name__).warning("Demo scenario command failed", exc_info=error)
    return JSONResponse(status_code=409, content={"detail": str(error)})


@app.get("/")
def root() -> dict[str, str]:
    return {"health": "/api/v1/health"}
