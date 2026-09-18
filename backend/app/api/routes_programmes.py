from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import Matcher, get_matcher
from app.schemas import CourseSummary, ProgrammeSummary

router = APIRouter(prefix="/programmes", tags=["programmes"])


@router.get("", response_model=list[ProgrammeSummary])
def list_programmes(matcher: Matcher = Depends(get_matcher)) -> list[ProgrammeSummary]:
    return matcher.list_programmes()


@router.get("/{programme_id}/courses", response_model=list[CourseSummary])
def list_courses(
    programme_id: str, matcher: Matcher = Depends(get_matcher)
) -> list[CourseSummary]:
    try:
        return matcher.get_courses(programme_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown programme: {programme_id}") from exc
