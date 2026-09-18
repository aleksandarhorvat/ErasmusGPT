from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    matcher: str
    models_loaded: bool
    version: str
