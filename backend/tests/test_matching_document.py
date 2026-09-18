"""Owner: Person A."""
from __future__ import annotations

from app.matching.document import build_document, sentences
from app.schemas.programme import CourseSummary


def _course(**kwargs) -> CourseSummary:
    base = dict(course_uid="x:1", code="1", title="Databases 1", ects=6.0, description="")
    base.update(kwargs)
    return CourseSummary(**base)


def test_document_excludes_metadata() -> None:
    doc = build_document(_course(description="Relational model and SQL."))
    assert "6.0" not in doc and "ECTS" not in doc  # ADR-0004


def test_learning_outcomes_and_topics_are_included() -> None:
    doc = build_document(
        _course(description="Relational model."),
        learning_outcomes=["Write SQL queries"],
        topics=["normalisation"],
    )
    assert "Write SQL queries" in doc
    assert "normalisation" in doc


def test_truncation_keeps_whole_sentences() -> None:
    long_text = " ".join(f"Sentence number {i} about databases and indexing." for i in range(200))
    doc = build_document(_course(description=long_text), max_chars=200)
    assert len(doc) <= 260
    assert not doc.endswith("Senten")


def test_sentence_splitter_drops_fragments() -> None:
    assert sentences("Hi. This is a sufficiently long sentence about automata theory.") == [
        "This is a sufficiently long sentence about automata theory."
    ]
