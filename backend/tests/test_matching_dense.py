"""Owner: Person A. Dense retrieval, the embedding cache and the pipeline (S2-A4).

No model is downloaded here. The bi-encoder is replaced by a deterministic fake, so
these run in CI, offline, in under a second. Whether the real model returns sensible
neighbours is a question for eval/, not for a unit test.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from app.core.config import Settings
from app.ingest.loader import CurriculumStore
from app.matching.dense import DenseIndex, cosine_scores, top_n
from app.matching.embedder import Embedder, content_hash, programme_documents
from app.matching.pipeline import PipelineMatcher, score_to_pct
from app.matching.reranker import Reranker

CURRICULA = Path(__file__).resolve().parents[2] / "data" / "curricula"
DIM = 16


def fake_encode(texts: list[str]) -> np.ndarray:
    """Hash each text into a fixed vector. Same text -> same vector, different -> far."""
    rows = []
    for text in texts:
        seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")
        vector = np.random.default_rng(seed).normal(size=DIM).astype(np.float32)
        rows.append(vector / np.linalg.norm(vector))
    return np.vstack(rows) if rows else np.zeros((0, DIM), dtype=np.float32)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=CURRICULA.parent, database_url=f"sqlite:///{tmp_path}/t.db")


@pytest.fixture
def store() -> CurriculumStore:
    return CurriculumStore(CURRICULA)


@pytest.fixture
def embedder(store: CurriculumStore, settings: Settings, tmp_path: Path,
             monkeypatch: pytest.MonkeyPatch) -> Embedder:
    monkeypatch.setattr(Settings, "cache_dir", property(lambda _: tmp_path))
    embedder = Embedder(store, settings)
    monkeypatch.setattr(embedder, "encode", fake_encode)
    return embedder


# --- dense search -----------------------------------------------------------

def test_a_course_matches_itself_with_score_one() -> None:
    matrix = fake_encode(["databases and sql", "computer networks", "linear algebra"])
    index = DenseIndex(["a", "b", "c"], matrix)
    uid, score = index.search(matrix[0], 1)[0]
    assert uid == "a"
    assert score == pytest.approx(1.0, abs=1e-5)


def test_ranking_is_by_descending_score_and_deterministic() -> None:
    matrix = fake_encode([f"course {i}" for i in range(20)])
    index = DenseIndex([str(i) for i in range(20)], matrix)
    first = index.search(matrix[3], 5)
    assert [uid for uid, _ in first] == [uid for uid, _ in index.search(matrix[3], 5)]
    assert [score for _, score in first] == sorted((s for _, s in first), reverse=True)


def test_ties_break_on_course_order() -> None:
    matrix = np.vstack([np.eye(1, DIM, dtype=np.float32)] * 3)
    assert [uid for uid, _ in DenseIndex(["c", "a", "b"], matrix).search(matrix[0], 3)] == [
        "c", "a", "b"
    ]


def test_empty_programme_returns_no_hits() -> None:
    empty = np.zeros((0, DIM), dtype=np.float32)
    assert DenseIndex([], empty).search(np.ones(DIM, dtype=np.float32), 5) == []
    assert cosine_scores(np.ones(DIM), empty).shape == (0,)
    assert top_n(np.array([1.0]), ["a"], 0) == []


def test_index_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        DenseIndex(["a", "b"], fake_encode(["one"]))


# --- the embedding cache ----------------------------------------------------

def test_documents_follow_course_order(store: CurriculumStore) -> None:
    documents = programme_documents(store, "uns-pmf-informatics-bsc")
    courses = store.get_courses("uns-pmf-informatics-bsc")
    assert len(documents) == len(courses)
    assert courses[0].title in documents[0]


def test_second_call_hits_the_cache(embedder: Embedder,
                                    monkeypatch: pytest.MonkeyPatch) -> None:
    first = embedder.encode_programme("uns-pmf-informatics-bsc")
    assert embedder.cache_path("uns-pmf-informatics-bsc").exists()

    def fail(_: list[str]) -> np.ndarray:
        raise AssertionError("re-encoded although the documents did not change")

    monkeypatch.setattr(embedder, "encode", fail)
    assert np.array_equal(embedder.encode_programme("uns-pmf-informatics-bsc"), first)


def test_changed_documents_invalidate_the_cache(embedder: Embedder) -> None:
    programme_id = "uns-pmf-informatics-bsc"
    embedder.encode_programme(programme_id)
    meta_path = embedder.cache_path(programme_id).with_suffix(".json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["content_hash"] = "0" * 16
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    calls: list[int] = []
    original = embedder.encode
    embedder.encode = lambda texts: (calls.append(len(texts)), original(texts))[1]
    embedder.encode_programme(programme_id)
    assert calls, "a stale hash must force a re-encode"


def test_content_hash_depends_on_every_document() -> None:
    assert content_hash(["a", "b"]) != content_hash(["a", "c"])
    assert content_hash(["a", "b"]) != content_hash(["ab"])
    assert content_hash(["a", "b"]) == content_hash(["a", "b"])


def test_unknown_programme_raises_key_error(embedder: Embedder) -> None:
    with pytest.raises(KeyError):
        embedder.encode_programme("nope")


# --- the pipeline -----------------------------------------------------------

@pytest.fixture
def matcher(store: CurriculumStore, settings: Settings, tmp_path: Path,
            monkeypatch: pytest.MonkeyPatch) -> PipelineMatcher:
    monkeypatch.setattr(Settings, "cache_dir", property(lambda _: tmp_path))
    monkeypatch.setattr(Embedder, "encode", staticmethod(fake_encode))
    monkeypatch.setattr(Reranker, "warm", lambda _: None)
    return PipelineMatcher(store, settings)


def test_pipeline_reports_models_loaded(matcher: PipelineMatcher) -> None:
    assert matcher.models_loaded is True
    assert set(matcher.indexes) == {p.programme_id for p in matcher.list_programmes()}


def test_match_course_returns_ranked_candidates(matcher: PipelineMatcher) -> None:
    home = matcher.get_courses("uns-pmf-informatics-bsc")[0]
    candidates = matcher.match_course(home.course_uid, "utwente-tcs-bsc", "dense", 5)
    assert [c.rank for c in candidates] == [1, 2, 3, 4, 5]
    assert all(0 <= c.score_pct <= 100 for c in candidates)
    hosts = {c.course_uid for c in matcher.get_courses("utwente-tcs-bsc")}
    assert {c.host_course.course_uid for c in candidates} <= hosts
    assert candidates[0].ects_delta == round(
        matcher.store.get_course(candidates[0].host_course.course_uid).ects - home.ects, 1
    )


def test_match_programme_covers_every_home_course(matcher: PipelineMatcher) -> None:
    rows = matcher.match_programme(
        "uns-pmf-informatics-bsc", "utwente-tcs-bsc", "dense", 3
    )
    assert len(rows) == len(matcher.get_courses("uns-pmf-informatics-bsc"))
    assert all(len(candidates) == 3 for _, candidates in rows)


def test_course_uids_filter_is_honoured(matcher: PipelineMatcher) -> None:
    wanted = [c.course_uid for c in matcher.get_courses("uns-pmf-informatics-bsc")[:2]]
    rows = matcher.match_programme(
        "uns-pmf-informatics-bsc", "utwente-tcs-bsc", "dense", 2, course_uids=wanted
    )
    assert [course.course_uid for course, _ in rows] == wanted


def test_an_unknown_strategy_is_refused(matcher: PipelineMatcher) -> None:
    """All four contract strategies are implemented now; anything else must not run."""
    home = matcher.get_courses("uns-pmf-informatics-bsc")[0]
    with pytest.raises(NotImplementedError):
        matcher.match_course(home.course_uid, "utwente-tcs-bsc", "magic", 5)
    with pytest.raises(NotImplementedError):
        matcher.match_programme("uns-pmf-informatics-bsc", "utwente-tcs-bsc", "magic", 5)


def test_unknown_ids_raise_key_error(matcher: PipelineMatcher) -> None:
    home = matcher.get_courses("uns-pmf-informatics-bsc")[0]
    with pytest.raises(KeyError):
        matcher.match_course(home.course_uid, "nope", "dense", 5)
    with pytest.raises(KeyError):
        matcher.match_course("uns-pmf:NOPE", "utwente-tcs-bsc", "dense", 5)


def test_score_to_pct_is_monotonic_and_clamped() -> None:
    assert score_to_pct(0.2) == 0
    assert score_to_pct(1.0) == 100
    assert score_to_pct(0.6) < score_to_pct(0.8)
    assert score_to_pct(-1.0) == 0  # cosine can be negative
