from __future__ import annotations

from fastapi import APIRouter

from app.api import (
    routes_evaluation,
    routes_match,
    routes_programmes,
    routes_recognition,
    routes_system,
)

api_router = APIRouter()
api_router.include_router(routes_system.router)
api_router.include_router(routes_programmes.router)
api_router.include_router(routes_match.router)
api_router.include_router(routes_recognition.router)
api_router.include_router(routes_evaluation.router)
