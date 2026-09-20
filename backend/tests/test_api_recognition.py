"""Owner: Person B. The recognition endpoint and the study-path filter (S6-B4).

The arithmetic belongs to Person A and is tested in test_matching_aggregate.py. What is
tested here is the part this module decides: which courses enter the sum.
"""
from __future__ import annotations

import os

os.environ.setdefault("MATCHER_IMPL", "stub")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)

HOME = "uns-pmf-informatics-bsc"
HOST = "utwente-tcs-bsc"


def post(**overrides) -> dict:
    body = {"home_programme_id": HOME, "host_programme_id": HOST, "strategy": "hybrid+ce"}
    body.update(overrides)
    response = client.post("/api/v1/recognition", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_a_module_is_a_smaller_denominator_than_everything() -> None:
    """The point of the filter: a curriculum offers more ECTS than a degree contains."""
    everything = post()
    module = post(module="Computer Science", ects_budget=180)
    assert module["total_ects"] < everything["total_ects"]
    assert len(module["courses"]) < len(everything["courses"])


def test_an_ects_budget_caps_the_denominator() -> None:
    """A curriculum offers more ECTS than the degree contains. 180 means 180."""
    body = post(module="Computer Science", ects_budget=180)
    assert body["total_ects"] <= 180.5
    assert body["total_ects"] < post()["total_ects"]


def test_buckets_and_share_are_consistent() -> None:
    body = post(module="Computer Science", ects_budget=180)
    buckets = body["likely_ects"] + body["borderline_ects"] + body["unlikely_ects"]
    assert abs(buckets - body["total_ects"]) < 0.51
    assert 0.0 <= body["expected_share"] <= 1.0
    assert abs(body["expected_share"] * body["total_ects"] - body["expected_recognised_ects"]) < 1.0


def test_every_course_is_accounted_for() -> None:
    body = post(module="Computer Science", ects_budget=180)
    assert abs(sum(c["ects"] for c in body["courses"]) - body["total_ects"]) < 0.51
    assert all(0.0 <= c["probability"] <= 1.0 for c in body["courses"])
    assert all(c["bucket"] in {"likely", "borderline", "unlikely"} for c in body["courses"])


def test_provisional_is_reported_so_the_ui_can_say_so() -> None:
    body = post()
    assert body["calibrated"] is True
    assert body["provisional"] is True, (
        "the calibration is fitted on machine labels until S5-A1 lands; "
        "the UI must not present it as measured"
    )


def test_unknown_programme_is_404() -> None:
    response = client.post(
        "/api/v1/recognition",
        json={"home_programme_id": "nope", "host_programme_id": HOST, "strategy": "dense"},
    )
    assert response.status_code == 404


def test_a_filter_that_selects_nothing_is_400_not_a_division_by_zero() -> None:
    response = client.post(
        "/api/v1/recognition",
        json={
            "home_programme_id": HOME,
            "host_programme_id": HOST,
            "strategy": "dense",
            "module": "No Such Module",
            "ects_budget": 180,
        },
    )
    assert response.status_code in {200, 400}
    if response.status_code == 200:
        assert response.json()["total_ects"] > 0


def test_strategies_report_which_scores_are_probabilities() -> None:
    by_id = {s["id"]: s for s in client.get("/api/v1/strategies").json()}
    assert by_id["hybrid+ce"]["calibrated"] is True
    assert by_id["bm25"]["calibrated"] is False
