"""Owner: Person A. BM25 and hybrid fusion (S3-A1, S3-A2).

Tokenisation is the contract here: it defines the lexical baseline in
docs/05-evaluation.md, so changing it should break a test, not pass quietly.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.core.config import Settings
from app.ingest.loader import CurriculumStore
from app.matching.embedder import Embedder
from app.matching.fusion import reciprocal_rank_fusion
from app.matching.lexical import BM25Index, tokenise
from app.matching.pipeline import PipelineMatcher, relative_pct
from app.matching.reranker import Reranker
from tests.test_matching_dense import fake_encode

CURRICULA = Path(__file__).resolve().parents[2] / "data" / "curricula"

DOCUMENTS = {
    "a": "Formal languages and automata. Regular languages, finite automata, grammars.",
    "b": "Databases 1. The relational model, SQL queries and normalisation.",
    "c": "Computer networks. The TCP/IP stack, routing, sockets and DNS.",
}


@pytest.fixture
def index() -> BM25Index:
    return BM25Index(list(DOCUMENTS), list(DOCUMENTS.values()))


# --- tokenisation -----------------------------------------------------------

def test_tokenise_lowercases_and_splits_on_punctuation() -> None:
    assert tokenise("TCP/IP stack, routing!") == ["tcp", "ip", "stack", "routing"]


def test_tokenise_drops_stopwords_and_single_characters() -> None:
    assert tokenise("the aim of a course is to teach X") == ["aim", "teach"]


def test_tokenise_keeps_plurals_distinct() -> None:
    assert tokenise("algorithm algorithms") == ["algorithm", "algorithms"]


# --- BM25 -------------------------------------------------------------------

def test_an_exact_title_match_ranks_first(index: BM25Index) -> None:
    assert index.search("Formal languages and automata", 3)[0][0] == "a"
    assert index.search("Databases 1", 3)[0][0] == "b"


def test_a_query_with_no_shared_terms_scores_zero(index: BM25Index) -> None:
    assert all(score == 0.0 for _, score in index.search("zzz qqq", 3))


def test_search_is_bounded_and_ordered(index: BM25Index) -> None:
    hits = index.search("automata and networks", 2)
    assert len(hits) == 2
    assert [s for _, s in hits] == sorted((s for _, s in hits), reverse=True)


def test_empty_programme_and_empty_query_are_safe() -> None:
    assert BM25Index([], []).search("anything", 5) == []
    assert all(s == 0.0 for _, s in BM25Index(list(DOCUMENTS), list(DOCUMENTS.values()))
               .search("the of and", 3))


def test_index_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        BM25Index(["a"], ["one", "two"])


# --- fusion -----------------------------------------------------------------

def test_rrf_rewards_agreement_between_lists() -> None:
    fused = dict(reciprocal_rank_fusion([["a", "b", "c"], ["b", "a", "c"]], k=60))
    assert fused["b"] > fused["c"] and fused["a"] > fused["c"]


def test_rrf_keeps_documents_only_one_list_found() -> None:
    fused = [uid for uid, _ in reciprocal_rank_fusion([["a"], ["b"]], k=60)]
    assert set(fused) == {"a", "b"}


# --- the pipeline -----------------------------------------------------------

@pytest.fixture
def matcher(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> PipelineMatcher:
    monkeypatch.setattr(Settings, "cache_dir", property(lambda _: tmp_path))
    monkeypatch.setattr(Embedder, "encode", staticmethod(fake_encode))
    monkeypatch.setattr(Reranker, "warm", lambda _: None)
    settings = Settings(data_dir=CURRICULA.parent)
    matcher = PipelineMatcher(CurriculumStore(CURRICULA), settings)
    # The heuristic display rule is under test here, so ignore any fitted calibration
    # that data/calibration/ happens to hold. The calibrated path has its own test.
    matcher.calibration = {}
    return matcher


@pytest.mark.parametrize("strategy", ["bm25", "hybrid"])
def test_strategies_return_ranked_candidates(matcher: PipelineMatcher, strategy: str) -> None:
    home = matcher.get_courses("uns-pmf-informatics-bsc")[0]
    candidates = matcher.match_course(home.course_uid, "utwente-tcs-bsc", strategy, 5)
    assert [c.rank for c in candidates] == [1, 2, 3, 4, 5]
    assert candidates[0].score_pct == 100
    assert all(0 <= c.score_pct <= 100 for c in candidates)


def test_calibrated_strategy_reports_a_probability(matcher: PipelineMatcher) -> None:
    """With a fitted calibration the top hit is a probability, not a pinned 100."""
    matcher.calibration = {"hybrid": (2.0, -3.0, 0.028, 0.0025)}
    home = matcher.get_courses("uns-pmf-informatics-bsc")[0]
    candidates = matcher.match_course(home.course_uid, "utwente-tcs-bsc", "hybrid", 5)
    percentages = [c.score_pct for c in candidates]
    assert all(0 <= pct <= 100 for pct in percentages)
    assert percentages == sorted(percentages, reverse=True)


def test_hybrid_covers_at_least_the_union_of_its_inputs(matcher: PipelineMatcher) -> None:
    """S3-A2's acceptance: fusion must not lose what either input found."""
    hosts = matcher.get_courses("utwente-tcs-bsc")
    depth = len(hosts)
    for home in matcher.get_courses("uns-pmf-informatics-bsc")[:10]:
        union = set()
        for strategy in ("dense", "bm25"):
            union |= {
                c.host_course.course_uid
                for c in matcher.match_course(home.course_uid, "utwente-tcs-bsc",
                                              strategy, depth)
            }
        fused = {
            c.host_course.course_uid
            for c in matcher.match_course(home.course_uid, "utwente-tcs-bsc",
                                          "hybrid", depth)
        }
        assert union <= fused


def test_bm25_finds_the_obvious_pair_the_fake_embedder_cannot(
    matcher: PipelineMatcher,
) -> None:
    """A real lexical hit: PMF "Computer networks" against Twente's networks course."""
    home = next(c for c in matcher.get_courses("uns-pmf-informatics-bsc")
                if c.code == "I243")
    top = matcher.match_course(home.course_uid, "utwente-tcs-bsc", "bm25", 1)[0]
    assert "network" in top.host_course.title.lower()


def test_relative_pct_handles_a_zero_best_score() -> None:
    assert relative_pct(0.0, 0.0) == 0
    assert relative_pct(0.5, 1.0) == 50
    assert relative_pct(2.0, 1.0) == 100


def test_dense_and_bm25_disagree_at_least_somewhere(matcher: PipelineMatcher) -> None:
    """If they agreed everywhere, fusion and the reranker would have nothing to do."""
    home = matcher.get_courses("uns-pmf-informatics-bsc")[0]
    dense = [c.host_course.course_uid
             for c in matcher.match_course(home.course_uid, "utwente-tcs-bsc", "dense", 5)]
    bm25 = [c.host_course.course_uid
            for c in matcher.match_course(home.course_uid, "utwente-tcs-bsc", "bm25", 5)]
    assert dense != bm25
    assert np.isfinite(
        matcher.lexical["utwente-tcs-bsc"].scores("databases and sql")
    ).all()
