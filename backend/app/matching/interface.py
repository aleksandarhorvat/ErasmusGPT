"""SHARED CONTRACT between Person A (implementation) and Person B (API).

app/api/** may import ONLY from this module and app.matching.factory.
It must never import embedder / dense / lexical / reranker directly.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.matching.aggregate import RecognitionSummary, summarise
from app.schemas.match import MatchCandidate, Strategy
from app.schemas.programme import CourseSummary, ProgrammeSummary

STRATEGIES: dict[Strategy, tuple[str, str]] = {
    "bm25": (
        "BM25 (lexical baseline)",
        "Classic bag-of-words ranking. Fast, but blind to synonyms: "
        "'Formal Languages' will not find 'Theory of Computation'.",
    ),
    "dense": (
        "Dense retrieval (bi-encoder)",
        "Cosine similarity between sentence-transformer embeddings. "
        "Catches paraphrases, occasionally matches on topic rather than content.",
    ),
    "hybrid": (
        "Hybrid (BM25 + dense, RRF)",
        "Reciprocal Rank Fusion of the lexical and dense candidate lists. The default: "
        "level with the reranked version on quality and about 3 ms per query.",
    ),
    "hybrid+ce": (
        "Hybrid + cross-encoder rerank",
        "Hybrid retrieval, then a cross-encoder scores every candidate pair and its "
        "order is fused with the retrieval order. The approach the proposal expected to "
        "win: fused, it is level with plain hybrid and costs about 400 times more per "
        "query. Kept selectable because the comparison is the result.",
    ),
}


@runtime_checkable
class Matcher(Protocol):
    """Everything the API layer is allowed to know about the matching engine."""

    def list_programmes(self) -> list[ProgrammeSummary]: ...

    def get_courses(self, programme_id: str) -> list[CourseSummary]:
        """Raises KeyError if the programme is unknown."""
        ...

    def match_course(
        self,
        home_course_uid: str,
        host_programme_id: str,
        strategy: Strategy,
        top_k: int,
    ) -> list[MatchCandidate]: ...

    def match_programme(
        self,
        home_programme_id: str,
        host_programme_id: str,
        strategy: Strategy,
        top_k: int,
        course_uids: list[str] | None = None,
    ) -> list[tuple[CourseSummary, list[MatchCandidate]]]: ...

    @property
    def models_loaded(self) -> bool: ...


__all__ = ["STRATEGIES", "Matcher", "RecognitionSummary", "summarise"]
