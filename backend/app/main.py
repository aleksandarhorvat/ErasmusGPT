from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Load curricula and models once, at boot - never inside a request."""
    from app.matching.factory import get_matcher

    matcher = get_matcher()
    log.info(
        "matcher=%s models_loaded=%s programmes=%d",
        type(matcher).__name__,
        matcher.models_loaded,
        len(matcher.list_programmes()),
    )
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
    description=(
        "Automatic matching of courses between a home and a host curriculum "
        "for Erasmus exchange. See docs/04-api-contract.md."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)
