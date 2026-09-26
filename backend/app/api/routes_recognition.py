"""Whole-programme recognition estimate. Owner: Person B. Task S6-B4.

Person A's `aggregate.summarise` does the arithmetic (S6-A5). This module decides which
home courses go into it, which is the part that makes the number honest: a curriculum
file lists everything a programme offers, and a student takes one path through it.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import Matcher, Settings, get_matcher, get_settings
from app.core.calibration import calibrated_strategies, provisional_strategies
from app.matching.interface import summarise
from app.schemas import CourseOutcome, RecognitionRequest, RecognitionResponse

router = APIRouter(prefix="/recognition", tags=["recognition"])


@router.post("", response_model=RecognitionResponse)
def recognition(
    request: RecognitionRequest,
    matcher: Matcher = Depends(get_matcher),
    settings: Settings = Depends(get_settings),
) -> RecognitionResponse:
    started = time.perf_counter()
    try:
        courses = matcher.get_courses(request.home_programme_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Unknown programme: {request.home_programme_id}"
        ) from exc
    if not courses:
        raise HTTPException(status_code=400, detail="That programme has no courses.")
    modules = sorted({c.module for c in courses if c.module})
    if request.module is not None and request.module not in modules:
        # Accepting it would silently estimate over every course while echoing the
        # module back, which reads as if the filter had been applied.
        raise HTTPException(
            status_code=400,
            detail=(f"{request.module!r} is not a study path of {request.home_programme_id}. "
                    f"Known: {', '.join(modules) or 'none'}."),
        )

    # Match everything, then let Person A's study_path() pick the degree out of it: it
    # keeps the compulsory courses, then the chosen module, then electives up to the
    # budget. Filtering here first would hide the electives it needs to choose from.
    try:
        rows = matcher.match_programme(
            home_programme_id=request.home_programme_id,
            host_programme_id=request.host_programme_id,
            strategy=request.strategy,
            # summarise() takes the most probable candidate, which with the
            # cosine-aware calibration is not always rank 1, so it needs more than one.
            top_k=5,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown programme or course: {exc}") from exc

    calibrated = request.strategy in calibrated_strategies(settings)
    summary = summarise(
        rows, calibrated=calibrated, module=request.module, ects_budget=request.ects_budget
    )

    return RecognitionResponse(
        home_programme_id=request.home_programme_id,
        host_programme_id=request.host_programme_id,
        strategy=request.strategy,
        module=request.module,
        calibrated=calibrated,
        provisional=request.strategy in provisional_strategies(settings),
        took_ms=int((time.perf_counter() - started) * 1000),
        total_ects=round(summary.total_ects, 1),
        expected_recognised_ects=round(summary.expected_recognised_ects, 1),
        expected_share=round(summary.expected_share, 4),
        likely_ects=round(summary.likely_ects, 1),
        borderline_ects=round(summary.borderline_ects, 1),
        unlikely_ects=round(summary.unlikely_ects, 1),
        ects_shortfall=round(summary.ects_shortfall, 1),
        courses=[CourseOutcome(**vars(c)) for c in summary.courses],
    )
