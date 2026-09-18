"""Cross-encoder reranking. Owner: Person A. Stage 4, task S4-A1.

Contract: rerank(home_doc, [(course_uid, host_doc), ...]) -> list[(course_uid, score)]
ordered desc. Batch with settings.rerank_batch_size; a full programme is ~1200 pairs
and must stay under ~30 s on CPU. Squash the raw logit through a sigmoid before it
leaves this module so the API only ever sees 0..1.
"""
from __future__ import annotations

raise NotImplementedError("S4-A1: implement the cross-encoder reranker (Person A)")
