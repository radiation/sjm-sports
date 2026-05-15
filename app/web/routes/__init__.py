from fastapi import APIRouter

from app.web.routes.home import router as home_router

web_router = APIRouter()
web_router.include_router(home_router)
