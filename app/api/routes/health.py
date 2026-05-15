from __future__ import annotations

from fastapi import APIRouter, Depends

from app.services.health import HealthService, get_health_service

router = APIRouter()


@router.get("/health", tags=["health"])
def health(service: HealthService = Depends(get_health_service)) -> dict[str, str]:
    return service.get_status()
