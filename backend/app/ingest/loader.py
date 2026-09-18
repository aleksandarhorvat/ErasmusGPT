"""Loads curriculum JSON into memory. Owner: Person A.

The JSON files under data/curricula/ are the source of truth; SQLite is only a cache
(ADR-0002). This loader is intentionally dumb and synchronous - a few hundred courses.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.schemas.programme import CourseSummary, ProgrammeSummary

log = logging.getLogger(__name__)


@dataclass
class Programme:
    summary: ProgrammeSummary
    courses: list[CourseSummary]
    raw: dict = field(repr=False, default_factory=dict)


class CurriculumStore:
    def __init__(self, curricula_dir: Path) -> None:
        self.dir = Path(curricula_dir)
        self._programmes: dict[str, Programme] = {}
        self._courses: dict[str, CourseSummary] = {}
        self.reload()

    def reload(self) -> None:
        self._programmes.clear()
        self._courses.clear()
        if not self.dir.exists():
            log.error(
                "curricula directory %s does not exist. The API will report zero "
                "programmes and the dropdowns will be empty. Check DATA_DIR and the "
                "./data volume mount in docker-compose.yml.",
                self.dir,
            )
            return
        files = sorted(self.dir.glob("*.json"))
        if not files:
            log.error("no *.json curricula found in %s", self.dir)
            return
        for path in files:
            self._load_file(path)
        log.info(
            "loaded %d programmes (%d courses) from %s",
            len(self._programmes),
            len(self._courses),
            self.dir,
        )

    def _load_file(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        institution_id = data["institution_id"]
        courses: list[CourseSummary] = []
        for raw in data.get("courses", []):
            course = CourseSummary(
                course_uid=f"{institution_id}:{raw['code']}",
                code=str(raw["code"]),
                title=raw["title"],
                ects=float(raw.get("ects") or 0.0),
                year=raw.get("year"),
                semester=raw.get("semester"),
                mandatory=bool(raw.get("mandatory", False)),
                module=raw.get("module"),
                url=raw.get("url"),
                description=raw.get("description", "") or "",
            )
            courses.append(course)
            self._courses[course.course_uid] = course

        summary = ProgrammeSummary(
            programme_id=data["programme_id"],
            institution_name=data["institution_name"],
            programme_name=data["programme_name"],
            country=data.get("country", ""),
            level=data.get("level", "bachelor"),
            course_count=len(courses),
            total_ects=data.get("total_ects"),
        )
        self._programmes[summary.programme_id] = Programme(summary, courses, data)

    # --- read API -----------------------------------------------------------
    def list_programmes(self) -> list[ProgrammeSummary]:
        return [p.summary for p in self._programmes.values()]

    def get_programme(self, programme_id: str) -> Programme:
        if programme_id not in self._programmes:
            raise KeyError(programme_id)
        return self._programmes[programme_id]

    def get_courses(self, programme_id: str) -> list[CourseSummary]:
        return self.get_programme(programme_id).courses

    def get_course(self, course_uid: str) -> CourseSummary:
        if course_uid not in self._courses:
            raise KeyError(course_uid)
        return self._courses[course_uid]

    def raw_course(self, course_uid: str) -> dict:
        """The unmodified JSON record - needed for learning_outcomes / topics."""
        institution_id, code = course_uid.split(":", 1)
        for programme in self._programmes.values():
            if programme.raw.get("institution_id") != institution_id:
                continue
            for raw in programme.raw.get("courses", []):
                if str(raw["code"]) == code:
                    return raw
        raise KeyError(course_uid)
