"""Cross-encoder reranking. Owner: Person A. Stage 4, task S4-A1.

Contract: rerank(home_doc, [(uid, host_doc)]) -> [(uid, score in 0..1)], best first.
Scores are sigmoid-squashed inside this module: ms-marco cross-encoders emit unbounded
logits, and nothing outside should have to know that.
"""
from __future__ import annotations

import logging
import math
import time

from app.core.config import Settings, get_settings

log = logging.getLogger(__name__)

# A whole programme is many requests' worth of pairs: 50 home courses x 25 candidates is
# 1250 pairs. The cap keeps one request bounded; candidates beyond it keep their
# retrieval order, which is a worse ranking but never a timeout.
# Moving this to Settings would mean editing app/core/config.py, which is Person B's.
MAX_PAIRS_PER_REQUEST = 1500

# Course documents run to ~1400 characters, so 512 tokens rarely truncates and costs
# quadratically in attention. Measured on this CPU over 25 real pairs: 512 tokens gives
# 7.9 pairs/s, 256 gives 19.8 pairs/s with the top score unchanged (2.28 against 2.29),
# and 128 changes the ranking. A whole programme goes from 157 s to about 63 s.
RERANK_MAX_TOKENS = 256


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class Reranker:
    """Scores (home, host) pairs jointly. The model loads on first use and stays."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._model = None
        self.pairs_scored = 0
        self.last_ms = 0.0

    @property
    def model(self):  # noqa: ANN201 - CrossEncoder, imported lazily
        if self._model is None:
            from sentence_transformers import CrossEncoder

            repo = self.settings.cross_encoder_repo
            log.info("loading cross-encoder %s", repo)
            self._model = CrossEncoder(
                repo,
                device="cpu",
                max_length=min(self.settings.max_seq_tokens, RERANK_MAX_TOKENS),
            )
        return self._model

    def warm(self) -> None:
        """Load the model now. Called from the pipeline's startup, not from a request."""
        _ = self.model

    def score(self, home_document: str, candidates: list[tuple[str, str]]) -> list[float]:
        """One score in 0..1 per candidate, in the order given."""
        if not candidates:
            return []
        started = time.perf_counter()
        raw = self.model.predict(
            [(home_document, document) for _, document in candidates],
            batch_size=self.settings.rerank_batch_size,
            show_progress_bar=False,
        )
        self.last_ms = (time.perf_counter() - started) * 1000
        self.pairs_scored += len(candidates)
        log.debug("reranked %d pairs in %.0f ms", len(candidates), self.last_ms)
        # Some cross-encoders return one column, others two. Both reduce to one logit.
        return [sigmoid(float(value if value.ndim == 0 else value[-1])) for value in raw]

    def rerank(
        self, home_document: str, candidates: list[tuple[str, str]], top_k: int
    ) -> list[tuple[str, float]]:
        """Best top_k candidates. Ties break on the retrieval order they arrived in."""
        scores = self.score(home_document, candidates)
        order = sorted(range(len(candidates)), key=lambda i: (-scores[i], i))
        return [(candidates[i][0], scores[i]) for i in order[:top_k]]
