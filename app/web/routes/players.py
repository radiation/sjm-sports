from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.core.database import get_session
from app.repositories.rosters import PlayerRosterRepository
from app.schemas.players import PlayerSearchFilters
from app.services.players import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, PlayerSearchService

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def get_player_search_service(session: Session = Depends(get_session)) -> PlayerSearchService:
    return PlayerSearchService(rosters=PlayerRosterRepository(session))


@router.get("/players", response_class=HTMLResponse)
def players(
    request: Request,
    year: int | None = None,
    college: str | None = None,
    conference: str | None = None,
    position: str | None = None,
    roster_year: str | None = None,
    is_transfer: bool | None = None,
    hometown_state: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    service: PlayerSearchService = Depends(get_player_search_service),
) -> Response:
    filters = PlayerSearchFilters(
        year=year,
        college=college,
        conference=conference,
        position=position,
        roster_year=roster_year,
        is_transfer=is_transfer,
        hometown_state=hometown_state,
    )
    results = service.search(filters=filters, page=page, page_size=page_size)
    return templates.TemplateResponse(
        request,
        "players.html",
        {
            "page_title": "Players",
            "results": results,
        },
    )
