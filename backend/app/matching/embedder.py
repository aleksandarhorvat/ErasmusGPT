"""Bi-encoder + on-disk embedding cache. Owner: Person A. Stage 2, task S2-A1.

Contract for whoever implements this:
  encode_programme(programme_id) -> np.ndarray of shape (n_courses, dim), L2-normalised,
  row order identical to CurriculumStore.get_courses(programme_id).
  Cached at data/.cache/{programme_id}.{model_tag}.npy, keyed by a hash of the
  concatenated course documents. Encoding must NEVER happen inside a /match request.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import numpy as np

from app.core.config import Settings, get_settings
from app.ingest.loader import CurriculumStore
from app.matching.document import build_document

log = logging.getLogger(__name__)


def programme_documents(store: CurriculumStore, programme_id: str) -> list[str]:
    """The text that represents each course, in get_courses order.

    The same call feeds retrieval, reranking and eval/run_eval.py. Raises KeyError if
    the programme is unknown.
    """
    documents = []
    for course in store.get_courses(programme_id):
        raw = store.raw_course(course.course_uid)
        documents.append(
            build_document(
                course,
                learning_outcomes=raw.get("learning_outcomes"),
                topics=raw.get("topics"),
            )
        )
    return documents


def content_hash(documents: list[str]) -> str:
    digest = hashlib.sha256()
    for document in documents:
        digest.update(document.encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()[:16]


class Embedder:
    """Sentence-transformer bi-encoder with a per-programme .npy cache.

    The model is loaded on first use and kept, so a request never pays for it. Inputs
    are course documents; outputs are L2-normalised float32 rows, which makes cosine
    similarity a plain dot product (see dense.py).
    """

    def __init__(self, store: CurriculumStore, settings: Settings | None = None) -> None:
        self.store = store
        self.settings = settings or get_settings()
        self.model_tag = self.settings.bi_encoder
        self._model = None

    @property
    def dim(self) -> int:
        return int(self.model.get_sentence_embedding_dimension())

    @property
    def model(self):  # noqa: ANN201 - SentenceTransformer, imported lazily
        if self._model is None:
            # Imported here so the module can be used, and tested, without torch, and so
            # that importing app.matching never pulls in a 400 MB dependency by accident.
            from sentence_transformers import SentenceTransformer

            repo = self.settings.bi_encoder_repo
            log.info("loading bi-encoder %s", repo)
            self._model = SentenceTransformer(repo, device="cpu")
        return self._model

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode arbitrary texts. Shape (len(texts), dim), L2-normalised float32."""
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vectors = self.model.encode(
            texts,
            batch_size=self.settings.encode_batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)

    def cache_path(self, programme_id: str) -> Path:
        return self.settings.cache_dir / f"{programme_id}.{self.model_tag}.npy"

    def encode_programme(self, programme_id: str) -> np.ndarray:
        """Embeddings for one programme, from cache when the documents are unchanged.

        Row i belongs to store.get_courses(programme_id)[i]. Raises KeyError if the
        programme is unknown.
        """
        documents = programme_documents(self.store, programme_id)
        digest = content_hash(documents)
        path = self.cache_path(programme_id)
        meta_path = path.with_suffix(".json")

        if path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("content_hash") == digest:
                vectors = np.load(path)
                if vectors.shape[0] == len(documents):
                    log.info("embedding cache hit for %s (%s)", programme_id, self.model_tag)
                    return vectors
            log.info("embedding cache stale for %s, re-encoding", programme_id)

        log.info("encoding %d courses of %s with %s", len(documents), programme_id,
                 self.settings.bi_encoder_repo)
        vectors = self.encode(documents)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, vectors)
        meta_path.write_text(
            json.dumps({
                "content_hash": digest,
                "model": self.settings.bi_encoder_repo,
                "model_tag": self.model_tag,
                "courses": len(documents),
                "dim": int(vectors.shape[1]) if vectors.size else 0,
            }, indent=1),
            encoding="utf-8",
        )
        return vectors
