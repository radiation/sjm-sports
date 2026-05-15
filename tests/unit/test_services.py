from __future__ import annotations

from app.services.health import HealthService
from app.services.home import HomeService


def test_health_service_reports_ok() -> None:
    assert HealthService().get_status() == {"status": "ok"}


def test_home_service_provides_page_title() -> None:
    context = HomeService().get_home_context()

    assert context["page_title"] == "SJM Sports Recruiting Portal"
