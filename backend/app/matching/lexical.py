"""BM25 lexical retrieval. Owner: Person A. Stage 3, task S3-A1.

Contract: BM25Index(uids, documents).search(query_text, n) -> [(course_uid, score)].
The tokenisation here defines the lexical baseline every other strategy is compared
against, so it is documented in docs/05-evaluation.md and changed only with a number to
justify it. rank_bm25, not Lucene: see CONTEXT.md section 3.
"""
from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

_TOKEN = re.compile(r"[a-z0-9]+")

# Words that appear in nearly every course description and only add noise. Kept short on
# purpose: an aggressive list would quietly do the work the ranking function should do.
STOPWORDS = frozenset("""
a an the and or of to in for on with by from as at is are be being been this that these
those it its their his her they them we you your our us i he she who whom which what
will shall can could should would may might must do does did done have has had having
not no nor but if then than so such also very more most other some any each both
course courses student students study studies lecture lectures teaching learning
instruction instructions practical theoretical introduction basic basics end able
""".split())


def tokenise(text: str) -> list[str]:
    """Lowercase, split on non-alphanumeric, drop stopwords and one-character tokens.

    No stemming: "algorithm" and "algorithms" stay distinct. Stemming is a change worth
    measuring rather than assuming, and the dense side already handles morphology.
    """
    return [t for t in _TOKEN.findall(text.lower()) if len(t) > 1 and t not in STOPWORDS]


class BM25Index:
    """One programme's documents under BM25 Okapi, with rank_bm25's default k1 and b."""

    def __init__(self, uids: list[str], documents: list[str]) -> None:
        if len(uids) != len(documents):
            raise ValueError(f"{len(uids)} uids but {len(documents)} documents")
        self.uids = uids
        self.tokenised = [tokenise(d) for d in documents]
        # BM25Okapi divides by the average document length, which is 0 for an empty
        # programme. Guard rather than let it raise at startup.
        self.model = BM25Okapi(self.tokenised) if any(self.tokenised) else None

    def scores(self, query_text: str) -> list[float]:
        query = tokenise(query_text)
        if self.model is None or not query:
            return [0.0] * len(self.uids)
        return [float(s) for s in self.model.get_scores(query)]

    def search(self, query_text: str, n: int) -> list[tuple[str, float]]:
        """The n best documents. Ties break on course order, as in dense.py."""
        if not self.uids or n <= 0:
            return []
        scores = self.scores(query_text)
        order = sorted(range(len(self.uids)), key=lambda i: (-scores[i], i))
        return [(self.uids[i], scores[i]) for i in order[:n]]
