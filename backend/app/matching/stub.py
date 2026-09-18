"""Deterministic fake matcher so Person B can build the API and UI on day one.

Uses only the curriculum JSON files plus a character-trigram Jaccard similarity.
No torch, no model download, instant. Selected with MATCHER_IMPL=stub.
"""
from __future__ import annotations

from app.ingest.loader import CurriculumStore
from app.schemas.match import Confidence, CourseRef, MatchCandidate, Strategy
from app.schemas.programme import CourseSummary, ProgrammeSummary


def _trigrams(text: str) -> set[str]:
    t = " ".join(text.lower().split())
    return {t[i : i + 3] for i in range(max(len(t) - 2, 0))}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def confidence_of(score_pct: int) -> Confidence:
    if score_pct >= 75:
        return "high"
    if score_pct >= 50:
        return "medium"
    return "low"


class StubMatcher:
    """Implements the Matcher protocol. Do not add real NLP here."""

    def __init__(self, store: CurriculumStore) -> None:
        self.store = store

    @property
    def models_loaded(self) -> bool:
        return False

    def list_programmes(self) -> list[ProgrammeSummary]:
        return self.store.list_programmes()

    def get_courses(self, programme_id: str) -> list[CourseSummary]:
        return self.store.get_courses(programme_id)

    def _score(self, home: CourseSummary, host: CourseSummary) -> float:
        a = _trigrams(f"{home.title} {home.description}")
        b = _trigrams(f"{host.title} {host.description}")
        return _jaccard(a, b)

    def match_course(
        self,
        home_course_uid: str,
        host_programme_id: str,
        strategy: Strategy,
        top_k: int,
    ) -> list[MatchCandidate]:
        home = self.store.get_course(home_course_uid)
        hosts = self.store.get_courses(host_programme_id)
        scored = sorted(
            ((self._score(home, h), h) for h in hosts), key=lambda p: p[0], reverse=True
        )[:top_k]
        out: list[MatchCandidate] = []
        for rank, (score, host) in enumerate(scored, start=1):
            pct = int(round(min(score * 250, 100)))  # stub scores are small; stretch them
            out.append(
                MatchCandidate(
                    host_course=CourseRef(
                        course_uid=host.course_uid,
                        title=host.title,
                        ects=host.ects,
                        url=host.url,
                    ),
                    score=round(score, 4),
                    score_pct=pct,
                    confidence=confidence_of(pct),
                    ects_delta=round(host.ects - home.ects, 1),
                    rank=rank,
                    evidence=None,
                )
            )
        return out

    def match_programme(
        self,
        home_programme_id: str,
        host_programme_id: str,
        strategy: Strategy,
        top_k: int,
        course_uids: list[str] | None = None,
    ) -> list[tuple[CourseSummary, list[MatchCandidate]]]:
        homes = self.store.get_courses(home_programme_id)
        if course_uids:
            wanted = set(course_uids)
            homes = [c for c in homes if c.course_uid in wanted]
        return [
            (h, self.match_course(h.course_uid, host_programme_id, strategy, top_k))
            for h in homes
        ]

