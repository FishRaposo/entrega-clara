from fastapi import APIRouter

from delivery_platform.core.config import settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "service": "delivery-platform-api",
        "environment": settings.app_env,
        "demo_mode": settings.demo_mode,
        "version": settings.app_version,
    }
