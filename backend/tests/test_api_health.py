"""Owner: Person B."""
from __future__ import annotations

import os

os.environ.setdefault("MATCHER_IMPL", "stub")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_strategies_lists_all_four() -> None:
    response = client.get("/api/v1/strategies")
    assert response.status_code == 200
    ids = {s["id"] for s in response.json()}
    assert ids == {"bm25", "dense", "hybrid", "hybrid+ce"}


def test_programmes_and_match_round_trip() -> None:
    programmes = client.get("/api/v1/programmes").json()
    assert len(programmes) >= 2, "sample curricula are missing from data/curricula/"
    home, host = programmes[0]["programme_id"], programmes[1]["programme_id"]

    response = client.post(
        "/api/v1/match",
        json={"home_programme_id": home, "host_programme_id": host, "top_k": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"]
    assert all(len(row["matches"]) <= 3 for row in body["results"])


def test_unknown_programme_is_404() -> None:
    assert client.get("/api/v1/programmes/nope/courses").status_code == 404
