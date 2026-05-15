from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.core.database import get_session
from app.repositories.people import PlayerRepository
from app.repositories.rosters import PlayerRosterRepository
from app.repositories.schools import CollegeRepository
from app.services.dashboard import DashboardService
from app.services.home import HomeService, get_home_service

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def get_dashboard_service(session: Session = Depends(get_session)) -> DashboardService:
    return DashboardService(
        colleges=CollegeRepository(session),
        players=PlayerRepository(session),
        rosters=PlayerRosterRepository(session),
    )


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    service: HomeService = Depends(get_home_service),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> Response:
    context: dict[str, object] = dict(service.get_home_context())
    context["dashboard"] = dashboard_service.get_summary()
    return templates.TemplateResponse(request, "home.html", context)
