"""Reciprocal Rank Fusion. Owner: Person A. Stage 3, task S3-A2.

The function below is already written; wiring it into the pipeline is the task.

    RRF(d) = sum over lists of 1 / (k + rank_in_that_list(d)),  k = settings.rrf_k

Rank-based on purpose: BM25 scores and cosine similarities are not on a comparable
scale, and normalising them introduces a hyperparameter nobody can defend.
"""
from __future__ import annotations


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]], k: int = 60, top_n: int | None = None
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, uid in enumerate(ranked, start=1):
            scores[uid] = scores.get(uid, 0.0) + 1.0 / (k + rank)
    fused = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    return fused[:top_n] if top_n else fused
