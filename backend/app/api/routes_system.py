from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import Matcher, Settings, get_matcher, get_settings
from app.matching.interface import STRATEGIES
from app.schemas import HealthResponse, StrategyInfo

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(
    settings: Settings = Depends(get_settings),
    matcher: Matcher = Depends(get_matcher),
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        matcher="stub" if type(matcher).__name__ == "StubMatcher" else "real",
        models_loaded=matcher.models_loaded,
        version=settings.version,
    )


@router.get("/strategies", response_model=list[StrategyInfo])
def strategies() -> list[StrategyInfo]:
    return [
        StrategyInfo(id=key, label=label, description=description)
        for key, (label, description) in STRATEGIES.items()
    ]
