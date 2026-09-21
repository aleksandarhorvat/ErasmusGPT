"""Owner: Person B. The ingest bookkeeping table (S2-B3).

The point of the table is to tell "same data as last boot" from "somebody edited a
curriculum", and to never be a reason the app fails to start.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings
from app.db.ingest_log import content_hash, record_curricula


def _settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path, database_url=f"sqlite:///{tmp_path / 'test.db'}")


def _curriculum(tmp_path: Path, courses: list[dict]) -> Path:
    directory = tmp_path / "curricula"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "x-bsc.json"
    path.write_text(json.dumps({
        "programme_id": "x-bsc", "institution_id": "x", "institution_name": "X",
        "programme_name": "BSc X", "country": "XX", "level": "bachelor",
        "total_ects": 180, "scraped_at": "2026-01-01T00:00:00Z", "courses": courses,
    }), encoding="utf-8")
    return path


COURSE = {"code": "C1", "title": "One", "ects": 6.0, "description": "d"}


def test_new_then_same_then_changed(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _curriculum(tmp_path, [COURSE])
    assert record_curricula(settings) == {"x-bsc": "new"}
    assert record_curricula(settings) == {"x-bsc": "same"}
    _curriculum(tmp_path, [COURSE, {**COURSE, "code": "C2", "title": "Two"}])
    assert record_curricula(settings) == {"x-bsc": "changed"}


def test_the_hash_ignores_when_it_was_scraped(tmp_path: Path) -> None:
    """A re-scrape that changes only the timestamp is the same data, not a change."""
    path = _curriculum(tmp_path, [COURSE])
    before = content_hash(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["scraped_at"] = "2026-09-21T12:00:00Z"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert content_hash(path) == before


def test_an_unwritable_database_does_not_stop_the_app(tmp_path: Path) -> None:
    _curriculum(tmp_path, [COURSE])
    settings = Settings(
        data_dir=tmp_path, database_url="sqlite:////nonexistent-directory/no.db"
    )
    assert record_curricula(settings) == {}  # logged, swallowed, app still boots
