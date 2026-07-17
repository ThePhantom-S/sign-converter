from fastapi import APIRouter

from app.api.routes import health, stream

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(stream.router)

