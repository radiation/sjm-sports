from fastapi import APIRouter

from app.web.routes.home import router as home_router
from app.web.routes.players import router as players_router

web_router = APIRouter()
web_router.include_router(home_router)
web_router.include_router(players_router)
