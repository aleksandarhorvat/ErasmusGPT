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

from app.ingest.loader import CurriculumStore


class PipelineMatcher:
    def __init__(self, store: CurriculumStore) -> None:
        raise NotImplementedError(
            "S2-A3: implement PipelineMatcher with strategy=dense first (Person A)"
        )
