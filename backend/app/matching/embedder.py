"""Bi-encoder + on-disk embedding cache. Owner: Person A. Stage 2, task S2-A1.

Contract for whoever implements this:
  encode_programme(programme_id) -> np.ndarray of shape (n_courses, dim), L2-normalised,
  row order identical to CurriculumStore.get_courses(programme_id).
  Cached at data/.cache/{programme_id}.{model_tag}.npy, keyed by a hash of the
  concatenated course documents. Encoding must NEVER happen inside a /match request.
"""
from __future__ import annotations

raise NotImplementedError("S2-A1: implement the bi-encoder embedder (Person A)")
