# ADR-0003 - NumPy instead of a vector database

**Status:** accepted - 2026-09-18

## Context
One corpus = one study programme = 30-120 course documents at 384 dimensions.
That is under 200 KB of floats.

## Decision
Exact cosine similarity via a normalised NumPy matrix multiply. No FAISS, no Qdrant,
no pgvector.

## Consequences
- Exact results, zero index-building, zero extra service, nothing to explain at the
  defence except the honest reason.
- If the corpus ever reaches ~100k documents, swap `matching/dense.py` for FAISS
  behind the same function signature. The rest of the system does not change.
