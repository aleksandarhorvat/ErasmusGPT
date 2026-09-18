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
_SENT = re.compile(r"(?<=[.!?])\s+")


def clean(text: str) -> str:
    text = _WS.sub(" ", text or "").strip()
    for pattern in _BOILERPLATE:
        text = pattern.sub("", text).strip()
    return text


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT.split(clean(text)) if len(s.strip()) > 20]


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
