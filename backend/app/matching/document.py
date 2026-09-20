"""The single definition of 'what text represents a course'. Owner: Person A.

Retrieval, reranking and evaluation must all call build_document(). If they ever
diverge, every number in the report becomes meaningless.
See docs/03-data-schema.md.
"""
from __future__ import annotations

import re

from app.schemas.programme import CourseSummary

_WS = re.compile(r"\s+")
_BOILERPLATE = (
    re.compile(r"^this course is part of.*?\.", re.I | re.S),
    re.compile(r"^students who have (passed|completed).*?\.", re.I | re.S),
)
# Semicolons split too: build_document joins learning outcomes with "; ", so without it
# a whole outcomes block is one "sentence" and the evidence panel shows a paragraph
# instead of the one line that explains the match.
_SENT = re.compile(r"(?<=[.!?;])\s+")
# A fragment may start with the field label that build_document inserted.
_FIELD_LABEL = re.compile(r"^(learning outcomes|topics)\s*:\s*", re.I)


def clean(text: str) -> str:
    text = _WS.sub(" ", text or "").strip()
    for pattern in _BOILERPLATE:
        text = pattern.sub("", text).strip()
    return text


def sentences(text: str) -> list[str]:
    """Sentence-ish fragments, long enough to be worth quoting as evidence."""
    out = []
    for fragment in _SENT.split(clean(text)):
        fragment = _FIELD_LABEL.sub("", fragment).strip().rstrip(";")
        if len(fragment) > 20:
            out.append(fragment)
    return out


def rerank_query(title: str, document: str) -> str:
    """The short text a cross-encoder gets as the query side of a pair.

    ms-marco cross-encoders are trained on a short query against a longer passage. Given
    a whole 1400-character course document instead, the reranker degrades badly: over the
    pooled labels, P@1 0.54 with the full document against 0.68 with the title and one
    sentence, and Recall@5 0.65 against 0.71. The document stays the document; only the
    query side is shortened.
    """
    first = sentences(document)
    return f"{clean(title)}. {first[0]}" if first else clean(title)


def build_document(
    course: CourseSummary,
    learning_outcomes: list[str] | None = None,
    topics: list[str] | None = None,
    max_chars: int = 2000,
) -> str:
    """Deliberately excludes ECTS / year / institution - see ADR-0004."""
    parts = [clean(course.title), clean(course.description)]
    if learning_outcomes:
        parts.append("Learning outcomes: " + "; ".join(clean(o) for o in learning_outcomes))
    if topics:
        parts.append("Topics: " + ", ".join(clean(t) for t in topics))
    doc = "\n\n".join(p for p in parts if p)

    if len(doc) <= max_chars:
        return doc
    # truncate by sentence, never mid-word
    out: list[str] = []
    total = 0
    for sentence in sentences(doc):
        if total + len(sentence) > max_chars:
            break
        out.append(sentence)
        total += len(sentence) + 1
    return " ".join(out) or doc[:max_chars]
