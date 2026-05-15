from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from app.services.home import HomeService, get_home_service

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


@router.get("/", response_class=HTMLResponse)
def home(request: Request, service: HomeService = Depends(get_home_service)) -> Response:
    context: dict[str, object] = dict(service.get_home_context())
    return templates.TemplateResponse(request, "home.html", context)
