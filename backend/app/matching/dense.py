"""Dense candidate retrieval. Owner: Person A. Stage 2, task S2-A2.

Contract: search(query_vec, programme_id, top_n) -> list[(course_uid, cosine)].
Exact NumPy matmul over the normalised matrix - no vector DB (ADR-0003).
"""
from __future__ import annotations

import numpy as np


def cosine_scores(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Cosine similarity of one query against every row.

    Both sides are L2-normalised by the embedder, so the dot product is the cosine.
    Rows that are all zero (an empty document) score 0.
    """
    if matrix.size == 0:
        return np.zeros((0,), dtype=np.float32)
    return matrix @ np.asarray(query_vec, dtype=np.float32).reshape(-1)


def top_n(scores: np.ndarray, uids: list[str], n: int) -> list[tuple[str, float]]:
    """The n highest scores as (course_uid, score), ties broken by course order.

    argpartition would be faster, but a programme has a few hundred courses and a full
    sort keeps ties in a stable, reproducible order, which the eval harness depends on.
    """
    if not uids or n <= 0:
        return []
    order = sorted(range(len(uids)), key=lambda i: (-float(scores[i]), i))
    return [(uids[i], float(scores[i])) for i in order[:n]]


class DenseIndex:
    """One programme's embedding matrix, searched by exact cosine similarity."""

    def __init__(self, uids: list[str], matrix: np.ndarray) -> None:
        if len(uids) != matrix.shape[0]:
            raise ValueError(f"{len(uids)} uids but {matrix.shape[0]} rows")
        self.uids = uids
        self.matrix = matrix

    def search(self, query_vec: np.ndarray, n: int) -> list[tuple[str, float]]:
        return top_n(cosine_scores(query_vec, self.matrix), self.uids, n)
