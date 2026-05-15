from __future__ import annotations


class HealthService:
    def get_status(self) -> dict[str, str]:
        return {"status": "ok"}


def get_health_service() -> HealthService:
    return HealthService()
