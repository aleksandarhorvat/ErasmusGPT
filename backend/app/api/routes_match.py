from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import Matcher, get_matcher
from app.schemas import (
    CourseRef,
    MatchCandidate,
    MatchRequest,
    MatchResponse,
    MatchRow,
    SingleCourseMatchRequest,
)

router = APIRouter(prefix="/match", tags=["match"])


@router.post("", response_model=MatchResponse)
def match_programme(
    request: MatchRequest, matcher: Matcher = Depends(get_matcher)
) -> MatchResponse:
    started = time.perf_counter()

    # An explicit course_uids list is validated here rather than passed straight down.
    # The matcher treats a falsy list as "no filter", so [] would quietly match the whole
    # programme, and an id that does not exist would be dropped without a word. Both are
    # answers to a question the caller did not ask. (S6-B3)
    if request.course_uids is not None:
        try:
            known = {c.course_uid for c in matcher.get_courses(request.home_programme_id)}
        except KeyError as exc:
            raise HTTPException(
                status_code=404, detail=f"Unknown programme: {request.home_programme_id}"
            ) from exc
        unknown = [uid for uid in request.course_uids if uid not in known]
        if unknown:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"{len(unknown)} course id(s) are not in {request.home_programme_id}: "
                    + ", ".join(sorted(unknown)[:5])
                ),
            )
        if not request.course_uids:
            try:
                matcher.get_courses(request.host_programme_id)
            except KeyError as exc:
                raise HTTPException(
                    status_code=404, detail=f"Unknown programme: {request.host_programme_id}"
                ) from exc
            return MatchResponse(
                home_programme_id=request.home_programme_id,
                host_programme_id=request.host_programme_id,
                strategy=request.strategy,
                took_ms=0,
                results=[],
            )

    try:
        rows = matcher.match_programme(
            home_programme_id=request.home_programme_id,
            host_programme_id=request.host_programme_id,
            strategy=request.strategy,
            top_k=request.top_k,
            course_uids=request.course_uids,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown programme or course: {exc}") from exc

    return MatchResponse(
        home_programme_id=request.home_programme_id,
        host_programme_id=request.host_programme_id,
        strategy=request.strategy,
        took_ms=int((time.perf_counter() - started) * 1000),
        results=[
            MatchRow(
                home_course=CourseRef(
                    course_uid=course.course_uid,
                    title=course.title,
                    ects=course.ects,
                    url=course.url,
                ),
                matches=candidates,
            )
            for course, candidates in rows
        ],
    )


@router.post("/course", response_model=list[MatchCandidate])
def match_single_course(
    request: SingleCourseMatchRequest, matcher: Matcher = Depends(get_matcher)
) -> list[MatchCandidate]:
    try:
        return matcher.match_course(
            home_course_uid=request.home_course_uid,
            host_programme_id=request.host_programme_id,
            strategy=request.strategy,
            top_k=request.top_k,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown programme or course: {exc}") from exc
