"""Chooses the Matcher implementation. Owner: shared, thin by design."""
from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import get_settings
from app.ingest.loader import CurriculumStore
from app.matching.interface import Matcher

log = logging.getLogger(__name__)


@lru_cache
def get_matcher() -> Matcher:
    settings = get_settings()
    store = CurriculumStore(settings.curricula_dir)

    if settings.matcher_impl == "stub":
        from app.matching.stub import StubMatcher

        log.warning("MATCHER_IMPL=stub - returning fake matches, no model inference")
        return StubMatcher(store)

    try:
        from app.matching.pipeline import PipelineMatcher

        return PipelineMatcher(store)
    except Exception:  # noqa: BLE001 - deliberately broad: never 500 the whole app
        log.exception(
            "Real matcher unavailable (models missing or pipeline not implemented yet). "
            "FALLING BACK TO THE STUB - results are NOT real."
        )
        from app.matching.stub import StubMatcher

        return StubMatcher(store)
