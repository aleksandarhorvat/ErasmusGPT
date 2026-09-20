"""Owner: Person A. The recognition estimate (S6-A4 calibration, S6-A5 aggregation)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.matching.aggregate import RecognitionSummary, as_dict, bucket_of, summarise
from app.matching.pipeline import load_calibration, probability
from app.schemas.match import CourseRef, MatchCandidate
from app.schemas.programme import CourseSummary


def course(uid: str, ects: float) -> CourseSummary:
    return CourseSummary(course_uid=uid, code=uid, title=f"Course {uid}", ects=ects,
                         description="")


def candidate(uid: str, pct: int, ects: float = 6.0) -> MatchCandidate:
    return MatchCandidate(
        host_course=CourseRef(course_uid=uid, title=f"Host {uid}", ects=ects),
        score=pct / 100, score_pct=pct,
        confidence="high" if pct >= 75 else "medium" if pct >= 50 else "low",
        ects_delta=0.0, rank=1,
    )


# --- calibration ------------------------------------------------------------

def test_probability_is_the_logistic_of_the_score() -> None:
    assert probability(0.0, (1.0, 0.0)) == pytest.approx(0.5)
    assert probability(10.0, (1.0, 0.0)) > 0.99
    assert probability(-10.0, (1.0, 0.0)) < 0.01
    assert probability(-1e6, (1.0, 0.0)) == 0.0  # must not overflow


def test_no_calibration_means_no_probability() -> None:
    assert probability(0.5, None) is None


def test_calibration_is_loaded_from_data_directory(tmp_path: Path) -> None:
    directory = tmp_path / "calibration"
    directory.mkdir()
    (directory / "hybrid-ce.json").write_text(
        json.dumps({"strategy": "hybrid+ce", "a": 2.5, "b": -1.5}), encoding="utf-8"
    )
    (directory / "broken.json").write_text("{not json", encoding="utf-8")
    fitted = load_calibration(Settings(data_dir=tmp_path))
    assert fitted == {"hybrid+ce": (2.5, -1.5)}  # the broken file is skipped, not fatal


def test_missing_calibration_directory_is_fine(tmp_path: Path) -> None:
    assert load_calibration(Settings(data_dir=tmp_path / "nope")) == {}


# --- aggregation ------------------------------------------------------------

def test_expected_ects_is_probability_times_home_ects() -> None:
    rows = [(course("a", 6.0), [candidate("x", 50)]),
            (course("b", 8.0), [candidate("y", 25)])]
    summary = summarise(rows)
    assert summary.total_ects == 14.0
    assert summary.expected_recognised_ects == pytest.approx(5.0)  # 3.0 + 2.0
    assert summary.expected_share == pytest.approx(5.0 / 14.0)


def test_only_the_best_candidate_counts() -> None:
    """A student transfers one course for one course, not the whole top five."""
    rows = [(course("a", 6.0), [candidate("x", 80), candidate("y", 70), candidate("z", 60)])]
    assert summarise(rows).expected_recognised_ects == pytest.approx(4.8)


def test_courses_are_bucketed_by_probability() -> None:
    rows = [(course("a", 6.0), [candidate("x", 90)]),
            (course("b", 6.0), [candidate("y", 50)]),
            (course("c", 6.0), [candidate("z", 10)])]
    summary = summarise(rows)
    assert (summary.likely_ects, summary.borderline_ects, summary.unlikely_ects) == (
        6.0, 6.0, 6.0
    )
    assert bucket_of(0.7) == "likely" and bucket_of(0.4) == "borderline"
    assert bucket_of(0.39) == "unlikely"


def test_a_course_with_no_candidate_is_unlikely_not_an_error() -> None:
    summary = summarise([(course("a", 6.0), [])])
    assert summary.expected_recognised_ects == 0.0
    assert summary.unlikely_ects == 6.0
    assert summary.courses[0].best_match_uid is None


def test_ects_shortfall_is_reported_for_plausible_matches_only() -> None:
    rows = [(course("a", 8.0), [candidate("x", 80, ects=3.0)]),   # 5 short, plausible
            (course("b", 8.0), [candidate("y", 10, ects=3.0)])]   # unlikely, not counted
    assert summarise(rows).ects_shortfall == pytest.approx(5.0)


def test_a_larger_host_course_produces_no_shortfall() -> None:
    rows = [(course("a", 6.0), [candidate("x", 80, ects=15.0)])]
    assert summarise(rows).ects_shortfall == 0.0


def test_summary_says_whether_it_was_calibrated() -> None:
    assert summarise([], calibrated=True).calibrated is True
    assert summarise([]).calibrated is False
    assert RecognitionSummary().expected_share == 0.0  # no division by zero


def test_as_dict_is_json_serialisable() -> None:
    rows = [(course("a", 6.0), [candidate("x", 80)])]
    payload = as_dict(summarise(rows, calibrated=True))
    assert json.loads(json.dumps(payload))["expected_recognised_ects"] == pytest.approx(4.8)
    assert payload["courses"][0]["best_match_title"] == "Host x"


# --- the study path denominator (raised by B, 2026-09-20) -------------------

def module_course(uid: str, ects: float, module: str | None) -> CourseSummary:
    return CourseSummary(course_uid=uid, code=uid, title=f"Course {uid}", ects=ects,
                         description="", module=module)


def test_a_module_and_budget_give_a_real_denominator() -> None:
    """A 353 ECTS catalogue is not a 180 ECTS degree."""
    rows = [
        (module_course("core", 100.0, None), [candidate("x", 100)]),
        (module_course("cs", 60.0, "Computer Science"), [candidate("y", 100)]),
        (module_course("it", 60.0, "Information Technologies"), [candidate("z", 100)]),
        (module_course("elective", 20.0, None), [candidate("w", 100)]),
    ]
    summary = summarise(rows, module="Computer Science", ects_budget=180.0)
    assert summary.total_ects == 180.0
    taken = {course.course_uid for course in summary.courses}
    assert "it" not in taken  # the other module is not part of this path
    assert {"core", "cs"} <= taken


def test_without_a_module_every_row_counts() -> None:
    rows = [(module_course("a", 6.0, None), [candidate("x", 50)])]
    assert summarise(rows).total_ects == 6.0


def test_the_budget_is_never_exceeded() -> None:
    rows = [(module_course(str(i), 30.0, None), [candidate("x", 50)]) for i in range(10)]
    assert summarise(rows, ects_budget=100.0).total_ects <= 100.0


def test_bands_agree_with_the_contract_confidence() -> None:
    """One threshold set: a likely row must never be reported as medium confidence."""
    from app.matching.aggregate import BUCKET_OF_CONFIDENCE
    from app.matching.pipeline import confidence_of

    for pct in range(0, 101, 5):
        assert BUCKET_OF_CONFIDENCE[confidence_of(pct)] == bucket_of(pct / 100)
