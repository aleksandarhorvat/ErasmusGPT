"""Owner: Person A. Cross-encoder reranking, evidence and the latency guard (S4-A4).

The cross-encoder is replaced by a fake that scores on shared words, so the tests check
the plumbing (order, budget, squashing, evidence) rather than the model's judgement.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.core.config import Settings
from app.ingest.loader import CurriculumStore
from app.matching.embedder import Embedder
from app.matching.lexical import tokenise
from app.matching.pipeline import PipelineMatcher
from app.matching.reranker import MAX_PAIRS_PER_REQUEST, Reranker, sigmoid
from tests.test_matching_dense import fake_encode

CURRICULA = Path(__file__).resolve().parents[2] / "data" / "curricula"


def fake_predict(pairs, **_) -> np.ndarray:
    """A logit per pair: how many content words the two texts share."""
    scores = []
    for home, host in pairs:
        shared = set(tokenise(home)) & set(tokenise(host))
        scores.append(np.float32(len(shared) / 5.0 - 2.0))
    return np.array(scores, dtype=np.float32)


class FakeCrossEncoder:
    def __init__(self) -> None:
        self.calls = 0
        self.pairs_seen = 0

    def predict(self, pairs, **kwargs) -> np.ndarray:
        self.calls += 1
        self.pairs_seen += len(pairs)
        return fake_predict(pairs, **kwargs)


@pytest.fixture
def matcher(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> PipelineMatcher:
    monkeypatch.setattr(Settings, "cache_dir", property(lambda _: tmp_path))
    monkeypatch.setattr(Embedder, "encode", staticmethod(fake_encode))
    reranker = Reranker(Settings())
    reranker._model = FakeCrossEncoder()
    return PipelineMatcher(
        CurriculumStore(CURRICULA), Settings(data_dir=CURRICULA.parent), reranker
    )


# --- the reranker -----------------------------------------------------------

def test_scores_are_squashed_into_zero_to_one() -> None:
    reranker = Reranker(Settings())
    reranker._model = FakeCrossEncoder()
    scores = reranker.score("databases and sql", [("a", "databases and sql"), ("b", "zzz")])
    assert all(0.0 <= s <= 1.0 for s in scores)
    assert scores[0] > scores[1]
    assert sigmoid(0.0) == pytest.approx(0.5)


def test_rerank_orders_by_score_and_keeps_top_k() -> None:
    reranker = Reranker(Settings())
    reranker._model = FakeCrossEncoder()
    candidates = [
        ("far", "astronomy of distant galaxies"),
        ("near", "relational databases, sql queries and normalisation"),
        ("mid", "sql in practice"),
    ]
    ranked = reranker.rerank("relational databases and sql queries", candidates, 2)
    assert [uid for uid, _ in ranked] == ["near", "mid"]


def test_empty_candidate_list_costs_no_model_call() -> None:
    reranker = Reranker(Settings())
    reranker._model = FakeCrossEncoder()
    assert reranker.rerank("anything", [], 5) == []
    assert reranker._model.calls == 0


def test_ties_keep_the_retrieval_order() -> None:
    reranker = Reranker(Settings())
    reranker._model = FakeCrossEncoder()
    same = [("first", "identical text"), ("second", "identical text")]
    assert [uid for uid, _ in reranker.rerank("identical text", same, 2)] == [
        "first", "second"
    ]


# --- the pipeline -----------------------------------------------------------

def test_hybrid_ce_is_implemented_and_ranked(matcher: PipelineMatcher) -> None:
    home = matcher.get_courses("uns-pmf-informatics-bsc")[0]
    candidates = matcher.match_course(home.course_uid, "utwente-tcs-bsc", "hybrid+ce", 5)
    assert [c.rank for c in candidates] == [1, 2, 3, 4, 5]
    assert [c.score for c in candidates] == sorted((c.score for c in candidates),
                                                   reverse=True)
    assert all(0 <= c.score_pct <= 100 for c in candidates)


def test_rerank_changes_the_order_dense_alone_produced(matcher: PipelineMatcher) -> None:
    home = next(c for c in matcher.get_courses("uns-pmf-informatics-bsc")
                if c.code == "I243")
    dense = [c.host_course.course_uid
             for c in matcher.match_course(home.course_uid, "utwente-tcs-bsc", "dense", 5)]
    reranked = [c.host_course.course_uid
                for c in matcher.match_course(home.course_uid, "utwente-tcs-bsc",
                                              "hybrid+ce", 5)]
    assert dense != reranked


def test_every_match_carries_evidence(matcher: PipelineMatcher) -> None:
    home = matcher.get_courses("uns-pmf-informatics-bsc")[0]
    for candidate in matcher.match_course(home.course_uid, "utwente-tcs-bsc",
                                          "hybrid+ce", 5):
        assert candidate.evidence is not None
        assert candidate.evidence.home_sentence in matcher.sentences[home.course_uid][0]
        host_sentences = matcher.sentences[candidate.host_course.course_uid][0]
        assert candidate.evidence.host_sentence in host_sentences
        assert -1.0 <= candidate.evidence.similarity <= 1.0


def test_evidence_is_absent_when_a_course_has_no_sentences(
    matcher: PipelineMatcher,
) -> None:
    home = matcher.get_courses("uns-pmf-informatics-bsc")[0]
    matcher.sentences[home.course_uid] = ([], np.zeros((0, 16), dtype=np.float32))
    assert matcher._evidence(home.course_uid,
                             matcher.get_courses("utwente-tcs-bsc")[0].course_uid) is None


def test_pair_budget_is_per_request_and_bounds_a_whole_programme(
    matcher: PipelineMatcher,
) -> None:
    matcher.match_programme("uns-pmf-informatics-bsc", "utwente-tcs-bsc", "hybrid+ce", 5)
    assert matcher.reranker._model.pairs_seen <= MAX_PAIRS_PER_REQUEST
    before = matcher.reranker._model.pairs_seen
    matcher.match_programme("uns-pmf-informatics-bsc", "utwente-tcs-bsc", "hybrid+ce", 5)
    assert matcher.reranker._model.pairs_seen - before <= MAX_PAIRS_PER_REQUEST


def test_no_rerank_allowance_still_returns_top_k(matcher: PipelineMatcher) -> None:
    home = matcher.get_courses("uns-pmf-informatics-bsc")[0]
    candidates = matcher._match_one(home.course_uid, "utwente-tcs-bsc", "hybrid+ce", 5,
                                    rerank_limit=0)
    assert len(candidates) == 5
    assert [c.rank for c in candidates] == [1, 2, 3, 4, 5]


def test_a_course_past_the_budget_scores_like_one_within_it(
    matcher: PipelineMatcher,
) -> None:
    """Unreranked candidates keep their retrieval rank in both lists, so the fused score
    of an unreranked course is on the same scale as a reranked one, not half of it."""
    home = matcher.get_courses("uns-pmf-informatics-bsc")[0]
    full = matcher._match_one(home.course_uid, "utwente-tcs-bsc", "hybrid+ce", 5)
    none = matcher._match_one(home.course_uid, "utwente-tcs-bsc", "hybrid+ce", 5,
                              rerank_limit=0)
    assert none[0].score > 0.5 * full[0].score + 1e-9
    assert none[0].score <= full[0].score * 1.5


def test_blended_scores_never_rise_down_the_list(matcher: PipelineMatcher) -> None:
    for home in matcher.get_courses("uns-pmf-informatics-bsc")[:10]:
        scores = [c.score for c in matcher._match_one(home.course_uid, "utwente-tcs-bsc",
                                                      "hybrid+ce", 25)]
        assert scores == sorted(scores, reverse=True)
