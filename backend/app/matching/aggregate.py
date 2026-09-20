"""From per-course matches to a programme-level answer. Owner: Person A. Task S6-A5.

The pipeline compares courses. A student asks a different question: how much of my
degree would be recognised if I went there? This module turns one `match_programme`
result into that number, and states its arithmetic openly, because an expected value
dressed up as a promise would be worse than no number at all.

    expected recognised ECTS = sum over home courses of p(best match) x ECTS(home course)

Rules, all of them arguable and therefore written down:

- Only the **best** candidate per home course counts. A student transfers one course for
  one course, not five.
- `p` is the calibrated probability from `score_pct / 100` (S6-A4). Without a calibration
  fitted on the gold set that number is a heuristic, and so is everything here, which is
  why `summarise` reports `calibrated` alongside the total.
- ECTS credited is the **home** course's, since that is what the student needs to replace.
  Where the host course carries fewer credits, the gap is reported separately as
  `ects_shortfall`: a coordinator may ask for extra work, and hiding that would flatter
  the result.
- Courses are bucketed by probability so the summary can say "likely, borderline,
  unlikely" rather than implying precision the model does not have.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.match import MatchCandidate
from app.schemas.programme import CourseSummary

LIKELY = 0.70
BORDERLINE = 0.40


@dataclass
class CourseOutcome:
    course_uid: str
    title: str
    ects: float
    probability: float
    bucket: str
    best_match_uid: str | None = None
    best_match_title: str | None = None
    ects_shortfall: float = 0.0


@dataclass
class RecognitionSummary:
    """What a coordinator would want on one line, plus the per-course detail."""

    total_ects: float = 0.0
    expected_recognised_ects: float = 0.0
    likely_ects: float = 0.0
    borderline_ects: float = 0.0
    unlikely_ects: float = 0.0
    ects_shortfall: float = 0.0
    calibrated: bool = False
    courses: list[CourseOutcome] = field(default_factory=list)

    @property
    def expected_share(self) -> float:
        return self.expected_recognised_ects / self.total_ects if self.total_ects else 0.0


def bucket_of(probability: float) -> str:
    if probability >= LIKELY:
        return "likely"
    if probability >= BORDERLINE:
        return "borderline"
    return "unlikely"


def summarise(
    rows: list[tuple[CourseSummary, list[MatchCandidate]]], calibrated: bool = False
) -> RecognitionSummary:
    """Aggregate one match_programme result. Rows with no candidate count as unlikely."""
    summary = RecognitionSummary(calibrated=calibrated)
    for course, candidates in rows:
        best = candidates[0] if candidates else None
        probability = (best.score_pct / 100) if best else 0.0
        bucket = bucket_of(probability)
        shortfall = (
            max(course.ects - best.host_course.ects, 0.0) if best and probability >= BORDERLINE
            else 0.0
        )

        summary.total_ects += course.ects
        summary.expected_recognised_ects += probability * course.ects
        summary.ects_shortfall += shortfall
        setattr(summary, f"{bucket}_ects", getattr(summary, f"{bucket}_ects") + course.ects)
        summary.courses.append(CourseOutcome(
            course_uid=course.course_uid,
            title=course.title,
            ects=course.ects,
            probability=round(probability, 3),
            bucket=bucket,
            best_match_uid=best.host_course.course_uid if best else None,
            best_match_title=best.host_course.title if best else None,
            ects_shortfall=round(shortfall, 1),
        ))

    summary.total_ects = round(summary.total_ects, 1)
    summary.expected_recognised_ects = round(summary.expected_recognised_ects, 1)
    summary.likely_ects = round(summary.likely_ects, 1)
    summary.borderline_ects = round(summary.borderline_ects, 1)
    summary.unlikely_ects = round(summary.unlikely_ects, 1)
    summary.ects_shortfall = round(summary.ects_shortfall, 1)
    return summary


def as_dict(summary: RecognitionSummary) -> dict:
    """JSON-ready, for whoever exposes this over the API or renders it."""
    return {
        "total_ects": summary.total_ects,
        "expected_recognised_ects": summary.expected_recognised_ects,
        "expected_share": round(summary.expected_share, 3),
        "likely_ects": summary.likely_ects,
        "borderline_ects": summary.borderline_ects,
        "unlikely_ects": summary.unlikely_ects,
        "ects_shortfall": summary.ects_shortfall,
        "calibrated": summary.calibrated,
        "courses": [vars(course) for course in summary.courses],
    }
