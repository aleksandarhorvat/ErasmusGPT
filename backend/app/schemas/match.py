"""FROZEN CONTRACT. See docs/04-api-contract.md.

Changing anything here requires a CONTRACT CHANGE entry in PROGRESS.md and a
matching update to the frontend client in frontend/src/lib/api.ts.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Strategy = Literal["bm25", "dense", "hybrid", "hybrid+ce"]
Confidence = Literal["high", "medium", "low"]


class CourseRef(BaseModel):
    course_uid: str
    title: str
    ects: float
    url: str | None = None


class Evidence(BaseModel):
    home_sentence: str
    host_sentence: str
    similarity: float


class MatchCandidate(BaseModel):
    host_course: CourseRef
    score: float = Field(description="Raw strategy score; comparable only within one strategy")
    score_pct: int = Field(ge=0, le=100, description="Calibrated for display")
    confidence: Confidence
    ects_delta: float
    rank: int
    evidence: Evidence | None = None


class MatchRow(BaseModel):
    home_course: CourseRef
    matches: list[MatchCandidate]


class MatchRequest(BaseModel):
    home_programme_id: str
    host_programme_id: str
    strategy: Strategy = "hybrid+ce"
    top_k: int = Field(default=5, ge=1, le=10)
    course_uids: list[str] | None = None


class SingleCourseMatchRequest(BaseModel):
    home_course_uid: str
    host_programme_id: str
    strategy: Strategy = "hybrid+ce"
    top_k: int = Field(default=5, ge=1, le=10)


class MatchResponse(BaseModel):
    home_programme_id: str
    host_programme_id: str
    strategy: Strategy
    took_ms: int
    results: list[MatchRow]


class StrategyInfo(BaseModel):
    id: Strategy
    label: str
    description: str
