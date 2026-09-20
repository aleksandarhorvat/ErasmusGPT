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

import json
import logging
import math
import time

import numpy as np

from app.core.config import Settings, get_settings
from app.ingest.loader import CurriculumStore
from app.matching.dense import DenseIndex
from app.matching.document import sentences
from app.matching.embedder import Embedder, programme_documents
from app.matching.fusion import reciprocal_rank_fusion
from app.matching.lexical import BM25Index
from app.matching.reranker import MAX_PAIRS_PER_REQUEST, Reranker
from app.schemas.match import Confidence, CourseRef, Evidence, MatchCandidate, Strategy
from app.schemas.programme import CourseSummary, ProgrammeSummary

log = logging.getLogger(__name__)

IMPLEMENTED: set[Strategy] = {"dense", "bm25", "hybrid", "hybrid+ce"}


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


def load_calibration(settings: Settings) -> dict[Strategy, tuple[float, float]]:
    """strategy -> (a, b) of p = sigmoid(a * score + b), from data/calibration/.

    Written by eval/fit_calibration.py (S6-A4). Missing file means the heuristics below
    are used instead, which keeps the app working before a gold set exists.
    """
    fitted: dict[Strategy, tuple[float, float]] = {}
    directory = settings.data_dir / "calibration"
    if not directory.is_dir():
        return fitted
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            fitted[data["strategy"]] = (float(data["a"]), float(data["b"]))
            log.info("calibration for %s from %s (%s)", data["strategy"], path.name,
                     data.get("label_source", "unknown source"))
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            log.warning("ignoring unreadable calibration file %s", path)
    return fitted


def probability(score: float, coefficients: tuple[float, float] | None) -> float | None:
    """Calibrated probability that a coordinator would recognise the pair, or None."""
    if coefficients is None:
        return None
    a, b = coefficients
    x = a * score + b
    if x < -700:  # exp overflows below this
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def _display_pct(strategy: Strategy, score: float, best: float,
                 calibration: dict[Strategy, tuple[float, float]] | None = None) -> int:
    """A calibrated probability where one has been fitted, a heuristic otherwise.

    The heuristics exist only so the app is usable before the gold set: cross-encoder
    scores are already 0..1, cosines get stretched, and BM25 and RRF have no fixed range.
    """
    calibrated = probability(score, (calibration or {}).get(strategy))
    if calibrated is not None:
        return int(round(calibrated * 100))
    if strategy == "hybrid+ce":
        return int(round(min(max(score, 0.0), 1.0) * 100))
    if strategy == "dense":
        return score_to_pct(score)
    return relative_pct(score, best)


def confidence_of(score_pct: int) -> Confidence:
    """One set of thresholds for the whole system (raised by B, 2026-09-20).

    The contract's high/medium/low and aggregate.py's likely/borderline/unlikely were
    two vocabularies with two sets of cut-offs over the same number. The cut-offs now
    live in aggregate.py, tied to a calibrated probability: high means the model expects
    about seven such pairs in ten to be recognised.
    """
    from app.matching.aggregate import BORDERLINE, LIKELY

    if score_pct >= LIKELY * 100:
        return "high"
    if score_pct >= BORDERLINE * 100:
        return "medium"
    return "low"


class PipelineMatcher:
    """Implements the Matcher protocol from interface.py.

    Every programme is encoded once in __init__, which FastAPI runs during startup
    (app/main.py lifespan), so no request ever waits for the model or for encoding.
    """

    def __init__(
        self,
        store: CurriculumStore,
        settings: Settings | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self.store = store
        self.settings = settings or get_settings()
        self.embedder = Embedder(store, self.settings)
        # Injectable so tests can supply a fake and never touch a real model.
        self.reranker = reranker or Reranker(self.settings)
        self.calibration = load_calibration(self.settings)
        self.indexes: dict[str, DenseIndex] = {}
        self.lexical: dict[str, BM25Index] = {}
        self.documents: dict[str, dict[str, str]] = {}
        # course_uid -> (sentences, one L2-normalised row each), for evidence (S4-A3).
        self.sentences: dict[str, tuple[list[str], np.ndarray]] = {}
        # Reranker pairs left in the current request; reset by the two public entry points.
        self._pair_budget = MAX_PAIRS_PER_REQUEST
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
            self._encode_sentences(uids, documents)
        # Load the cross-encoder now rather than on the first hybrid+ce request, which
        # otherwise pays 17 s for the model load and looks like a hung demo.
        self.reranker.warm()
        log.info(
            "pipeline ready: %d programmes encoded with %s, reranker %s",
            len(self.indexes),
            self.settings.bi_encoder_repo,
            self.settings.cross_encoder_repo,
        )

    def _encode_sentences(self, uids: list[str], documents: list[str]) -> None:
        """Embed every course's sentences once, so evidence costs no model call later.

        One batch for the whole programme: a few hundred short sentences, and batching
        them together is several times faster than one call per course.
        """
        per_course = [sentences(document) for document in documents]
        flat = [sentence for course in per_course for sentence in course]
        vectors = self.embedder.encode(flat)
        offset = 0
        for uid, course in zip(uids, per_course, strict=True):
            self.sentences[uid] = (course, vectors[offset:offset + len(course)])
            offset += len(course)

    def _evidence(self, home_uid: str, host_uid: str) -> Evidence | None:
        """The sentence pair that drove the match: the most similar one either way.

        This explains the match rather than proving it. The ranking came from whole
        documents, and the sentence pair is read off the same embedding space.
        """
        home_sentences, home_vectors = self.sentences.get(home_uid, ([], None))
        host_sentences, host_vectors = self.sentences.get(host_uid, ([], None))
        if not home_sentences or not host_sentences:
            return None
        similarity = home_vectors @ host_vectors.T
        i, j = np.unravel_index(int(np.argmax(similarity)), similarity.shape)
        return Evidence(
            home_sentence=home_sentences[i],
            host_sentence=host_sentences[j],
            similarity=round(float(similarity[i, j]), 4),
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
        # Never fuse a shallower list than the caller asked for: eval/ requests depths
        # larger than candidate_top_n when it measures recall.
        candidates = max(self.settings.candidate_top_n, n)
        lists = [
            [uid for uid, _ in dense_index.search(self._vector(home_uid), candidates)],
            [uid for uid, _ in bm25_index.search(self._document(home_uid), candidates)],
        ]
        fused = reciprocal_rank_fusion(lists, k=self.settings.rrf_k, top_n=candidates)
        if strategy == "hybrid":
            return fused[:n]

        # hybrid+ce: rerank the fused candidates as (home, host) pairs.
        pairs = [(uid, self.documents[host_programme_id][uid]) for uid, _ in fused]
        if self._pair_budget < len(pairs):
            # Over budget: keep the fused order for the rest rather than risk a timeout.
            kept = self.reranker.rerank(self._document(home_uid),
                                        pairs[:self._pair_budget], n)
            rest = [(uid, 0.0) for uid, _ in fused[self._pair_budget:]]
            self._pair_budget = 0
            return (kept + rest)[:n]
        self._pair_budget -= len(pairs)
        return self.reranker.rerank(self._document(home_uid), pairs, n)

    def _candidate(
        self, home: CourseSummary, host_uid: str, score: float, rank: int, pct: int
    ) -> MatchCandidate:
        host = self.store.get_course(host_uid)
        evidence = self._evidence(home.course_uid, host_uid)
        return MatchCandidate(
            host_course=CourseRef(
                course_uid=host.course_uid, title=host.title, ects=host.ects, url=host.url
            ),
            score=round(float(score), 4),
            score_pct=pct,
            confidence=confidence_of(pct),
            ects_delta=round(host.ects - home.ects, 1),
            rank=rank,
            evidence=evidence,
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
        self._pair_budget = MAX_PAIRS_PER_REQUEST
        return self._match_one(home_course_uid, host_programme_id, strategy, top_k)

    def _match_one(
        self,
        home_course_uid: str,
        host_programme_id: str,
        strategy: Strategy,
        top_k: int,
    ) -> list[MatchCandidate]:
        """One home course against one programme. Spends the current pair budget."""
        home = self.store.get_course(home_course_uid)
        started = time.perf_counter()
        hits = self._retrieve(home_course_uid, host_programme_id, strategy, top_k)
        log.debug("%s query for %s took %.0f ms", strategy, home_course_uid,
                  (time.perf_counter() - started) * 1000)
        best = hits[0][1] if hits else 0.0
        return [
            self._candidate(
                home,
                uid,
                score,
                rank,
                _display_pct(strategy, score, best, self.calibration),
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

        if strategy not in IMPLEMENTED:
            raise NotImplementedError(f"strategy {strategy!r} lands in a later stage")
        if host_programme_id not in self.indexes:
            raise KeyError(host_programme_id)

        # One budget for the whole request, shared by every home course in it.
        self._pair_budget = MAX_PAIRS_PER_REQUEST
        started = time.perf_counter()
        rows = [
            (home, self._match_one(home.course_uid, host_programme_id, strategy, top_k))
            for home in homes
        ]
        elapsed = (time.perf_counter() - started) * 1000
        log.info(
            "%s: %d home courses in %.0f ms (%.0f ms/query, %d rerank pairs left)",
            strategy, len(rows), elapsed, elapsed / max(len(rows), 1), self._pair_budget,
        )
        return rows
