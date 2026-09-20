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
    calibrated: bool = Field(
        default=False,
        description="score_pct is a fitted probability of recognition, not a display number",
    )
    provisional: bool = Field(
        default=False,
        description="the calibration was fitted on machine labels, no human pass yet",
    )


# --- recognition estimate (S6-A5 / S6-B4) -----------------------------------

Bucket = Literal["likely", "borderline", "unlikely"]


class RecognitionRequest(BaseModel):
    """A whole-programme estimate, over one study path rather than every course.

    A curriculum file lists every course a programme offers. Nobody takes all of them:
    UNS PMF Informatics offers 353 ECTS and the degree is 180. `module` and
    `mandatory_only` narrow the home side to a path a student could actually follow, so
    the denominator means something.
    """

    home_programme_id: str
    host_programme_id: str
    strategy: Strategy = "hybrid+ce"
    module: str | None = Field(default=None, description="null means every course offered")
    ects_budget: float | None = Field(
        default=None, ge=1, description="degree size, usually the programme's total_ects"
    )


class CourseOutcome(BaseModel):
    course_uid: str
    title: str
    ects: float
    probability: float = Field(ge=0.0, le=1.0)
    bucket: Bucket
    best_match_uid: str | None = None
    best_match_title: str | None = None
    ects_shortfall: float = 0.0


class RecognitionResponse(BaseModel):
    home_programme_id: str
    host_programme_id: str
    strategy: Strategy
    module: str | None
    calibrated: bool
    provisional: bool
    took_ms: int
    total_ects: float
    expected_recognised_ects: float
    expected_share: float
    likely_ects: float
    borderline_ects: float
    unlikely_ects: float
    ects_shortfall: float
    courses: list[CourseOutcome]
