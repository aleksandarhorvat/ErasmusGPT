"""The real Matcher. Owner: Person A. Stage 2 -> 4.

Built up incrementally: S2-A3 adds strategy='dense', S3-A2 adds 'bm25' and
'hybrid', S4-A2 adds 'hybrid+ce'. Each stage only needs the strategies of that
stage to work - the others may raise NotImplementedError.

Assembles document -> (lexical | dense | fusion) -> reranker and exposes exactly the
Matcher protocol from interface.py. app/api/** never imports anything below this.

Until it is implemented, factory.get_matcher() logs loudly and falls back to StubMatcher,
so the app still boots and Person B is never blocked.
"""
from __future__ import annotations

import logging

from app.core.config import Settings, get_settings
from app.ingest.loader import CurriculumStore
from app.matching.dense import DenseIndex
from app.matching.embedder import Embedder, programme_documents
from app.matching.fusion import reciprocal_rank_fusion
from app.matching.lexical import BM25Index
from app.schemas.match import Confidence, CourseRef, MatchCandidate, Strategy
from app.schemas.programme import CourseSummary, ProgrammeSummary

log = logging.getLogger(__name__)

IMPLEMENTED: set[Strategy] = {"dense", "bm25", "hybrid"}


def score_to_pct(score: float) -> int:
    """Placeholder calibration until S3-B1 puts it in one place.

    Read raw, a cosine would call every pair a match: over PMF x Twente with
    bge-small-en-v1.5, unrelated pairs ("English 1" vs anything) sit near 0.63 and the
    best pair seen ("Formal languages and automata" vs "Theory of Computation") is 0.88.
    This stretches 0.55 -> 0, 0.95 -> 100 and clamps.
    """
    return int(round(min(max((score - 0.55) / 0.40, 0.0), 1.0) * 100))


def relative_pct(score: float, best: float) -> int:
    """Display value for scores with no fixed range: BM25 and RRF.

    A BM25 score means nothing on its own, and an RRF score is bounded by the number of
    lists fused. Both are reported relative to the best hit for the same home course, so
    the top row reads 100 %. S3-B1 replaces this with one calibration for all strategies.
    """
    if best <= 0:
        return 0
    return int(round(min(max(score / best, 0.0), 1.0) * 100))


def confidence_of(score_pct: int) -> Confidence:
    if score_pct >= 75:
        return "high"
    if score_pct >= 50:
        return "medium"
    return "low"


class PipelineMatcher:
    """Implements the Matcher protocol from interface.py.

    Every programme is encoded once in __init__, which FastAPI runs during startup
    (app/main.py lifespan), so no request ever waits for the model or for encoding.
    """

    def __init__(self, store: CurriculumStore, settings: Settings | None = None) -> None:
        self.store = store
        self.settings = settings or get_settings()
        self.embedder = Embedder(store, self.settings)
        self.indexes: dict[str, DenseIndex] = {}
        self.lexical: dict[str, BM25Index] = {}
        self.documents: dict[str, dict[str, str]] = {}
        self._warm()

    def _warm(self) -> None:
        for programme in self.store.list_programmes():
            programme_id = programme.programme_id
            uids = [c.course_uid for c in self.store.get_courses(programme_id)]
            self.indexes[programme_id] = DenseIndex(
                uids, self.embedder.encode_programme(programme_id)
            )
            documents = programme_documents(self.store, programme_id)
            self.lexical[programme_id] = BM25Index(uids, documents)
            self.documents[programme_id] = dict(zip(uids, documents, strict=True))
        log.info(
            "pipeline ready: %d programmes encoded with %s",
            len(self.indexes),
            self.settings.bi_encoder_repo,
        )

    @property
    def models_loaded(self) -> bool:
        return bool(self.indexes)

    def list_programmes(self) -> list[ProgrammeSummary]:
        return self.store.list_programmes()

    def get_courses(self, programme_id: str) -> list[CourseSummary]:
        return self.store.get_courses(programme_id)

    def _vector(self, course_uid: str):  # noqa: ANN202 - np.ndarray, one row
        for index in self.indexes.values():
            if course_uid in index.uids:
                return index.matrix[index.uids.index(course_uid)]
        raise KeyError(course_uid)

    def _document(self, course_uid: str) -> str:
        for documents in self.documents.values():
            if course_uid in documents:
                return documents[course_uid]
        raise KeyError(course_uid)

    def _retrieve(
        self, home_uid: str, host_programme_id: str, strategy: Strategy, n: int
    ) -> list[tuple[str, float]]:
        """Ranked (course_uid, score) for one home course, before any reranking."""
        dense_index = self.indexes[host_programme_id]
        bm25_index = self.lexical[host_programme_id]
        if strategy == "dense":
            return dense_index.search(self._vector(home_uid), n)
        if strategy == "bm25":
            return bm25_index.search(self._document(home_uid), n)

        # hybrid: fuse the two full ranked lists by rank, not by score. Cosines and BM25
        # scores are not comparable, and normalising them adds a knob nobody can defend.
        candidates = self.settings.candidate_top_n
        lists = [
            [uid for uid, _ in dense_index.search(self._vector(home_uid), candidates)],
            [uid for uid, _ in bm25_index.search(self._document(home_uid), candidates)],
        ]
        return reciprocal_rank_fusion(lists, k=self.settings.rrf_k, top_n=n)

    def _candidate(
        self, home: CourseSummary, host_uid: str, score: float, rank: int, pct: int
    ) -> MatchCandidate:
        host = self.store.get_course(host_uid)
        return MatchCandidate(
            host_course=CourseRef(
                course_uid=host.course_uid, title=host.title, ects=host.ects, url=host.url
            ),
            score=round(float(score), 4),
            score_pct=pct,
            confidence=confidence_of(pct),
            ects_delta=round(host.ects - home.ects, 1),
            rank=rank,
            evidence=None,  # S4-A3
        )

    def match_course(
        self,
        home_course_uid: str,
        host_programme_id: str,
        strategy: Strategy,
        top_k: int,
    ) -> list[MatchCandidate]:
        if strategy not in IMPLEMENTED:
            raise NotImplementedError(f"strategy {strategy!r} lands in a later stage")
        if host_programme_id not in self.indexes:
            raise KeyError(host_programme_id)
        home = self.store.get_course(home_course_uid)
        hits = self._retrieve(home_course_uid, host_programme_id, strategy, top_k)
        best = hits[0][1] if hits else 0.0
        return [
            self._candidate(
                home,
                uid,
                score,
                rank,
                score_to_pct(score) if strategy == "dense" else relative_pct(score, best),
            )
            for rank, (uid, score) in enumerate(hits, start=1)
        ]

    def match_programme(
        self,
        home_programme_id: str,
        host_programme_id: str,
        strategy: Strategy,
        top_k: int,
        course_uids: list[str] | None = None,
    ) -> list[tuple[CourseSummary, list[MatchCandidate]]]:
        homes = self.store.get_courses(home_programme_id)
        if not homes:
            raise KeyError(home_programme_id)
        if course_uids:
            wanted = set(course_uids)
            homes = [c for c in homes if c.course_uid in wanted]
        return [
            (home, self.match_course(home.course_uid, host_programme_id, strategy, top_k))
            for home in homes
        ]
