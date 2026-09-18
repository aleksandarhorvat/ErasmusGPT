"""Single source of truth for configuration. Owner: Person B.

The MODELS mapping is read by BOTH the runtime and scripts/download_models.py.
Do not duplicate model names anywhere else.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)

# app/core/config.py -> app/core -> app -> the application root.
# That root is <repo>/backend when running from a checkout, and /srv inside the image.
BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


def _default_data_dir() -> Path:
    """Locate data/ in both layouts.

    Inside the image, docker-compose mounts the repository's data/ at /srv/data, so the
    application root is the right parent. From a checkout, data/ sits next to backend/.
    Walking up a fixed number of parents gets this wrong in one of the two layouts, which
    is how the container ended up looking for curricula in the SQLite volume.
    """
    for candidate in (BACKEND_ROOT / "data", REPO_ROOT / "data"):
        if (candidate / "curricula").is_dir():
            return candidate
    log.warning(
        "no data/curricula found under %s or %s; set DATA_DIR explicitly",
        BACKEND_ROOT,
        REPO_ROOT,
    )
    return REPO_ROOT / "data"

# --- models -----------------------------------------------------------------
# tag -> Hugging Face repo id. See docs/02-models.md for the rationale.
BI_ENCODERS: dict[str, str] = {
    "bge-small": "BAAI/bge-small-en-v1.5",
    "minilm": "sentence-transformers/all-MiniLM-L6-v2",
}
CROSS_ENCODERS: dict[str, str] = {
    "ms-marco-l6": "cross-encoder/ms-marco-MiniLM-L6-v2",
}
# Everything that must exist inside the image before HF_HUB_OFFLINE=1 kicks in.
MODELS_TO_BAKE: list[str] = [*BI_ENCODERS.values(), *CROSS_ENCODERS.values()]


class Settings(BaseSettings):
    # Read backend/.env if present, then the repository root .env, which is the one
    # docker compose uses. Later files win, so one file configures both paths.
    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env", REPO_ROOT / ".env"), extra="ignore"
    )

    app_name: str = "ErasmusGPT"
    version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    # stub | real  -- see CONTEXT.md section 8
    matcher_impl: str = "real"

    bi_encoder: str = "bge-small"
    cross_encoder: str = "ms-marco-l6"

    # pipeline knobs (also swept by eval/run_eval.py)
    candidate_top_n: int = 25
    default_top_k: int = 5
    rrf_k: int = 60
    encode_batch_size: int = 32
    rerank_batch_size: int = 32
    max_seq_tokens: int = 512

    data_dir: Path = _default_data_dir()
    database_url: str = "sqlite:///./erasmusgpt.db"

    cors_origins: list[str] = ["http://localhost:8080", "http://localhost:5173"]

    @property
    def curricula_dir(self) -> Path:
        return self.data_dir / "curricula"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / ".cache"

    @property
    def gold_dir(self) -> Path:
        return self.data_dir / "gold"

    @property
    def bi_encoder_repo(self) -> str:
        return BI_ENCODERS[self.bi_encoder]

    @property
    def cross_encoder_repo(self) -> str:
        return CROSS_ENCODERS[self.cross_encoder]


@lru_cache
def get_settings() -> Settings:
    return Settings()
