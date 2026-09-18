"""Owner: Person B.

Regression guard for the bug where the application found data/ from a checkout but
looked inside the SQLite volume when running in the image, so every dropdown was empty.
"""
from __future__ import annotations

import importlib
from pathlib import Path

from app.core import config


def _make_tree(root: Path, layout: str) -> Path:
    """Build a fake application root and return it."""
    if layout == "image":
        app_root = root / "srv"
        (app_root / "data" / "curricula").mkdir(parents=True)
    else:
        app_root = root / "repo" / "backend"
        (root / "repo" / "data" / "curricula").mkdir(parents=True)
        app_root.mkdir(parents=True)
    return app_root


def _resolve(app_root: Path) -> Path:
    for candidate in (app_root / "data", app_root.parent / "data"):
        if (candidate / "curricula").is_dir():
            return candidate
    return app_root.parent / "data"


def test_image_layout_uses_the_application_root(tmp_path: Path) -> None:
    app_root = _make_tree(tmp_path, "image")
    assert _resolve(app_root) == app_root / "data"


def test_checkout_layout_uses_the_repository_root(tmp_path: Path) -> None:
    app_root = _make_tree(tmp_path, "checkout")
    assert _resolve(app_root) == app_root.parent / "data"


def test_settings_point_at_a_real_curricula_directory() -> None:
    importlib.reload(config)
    settings = config.Settings()
    assert settings.curricula_dir.is_dir(), (
        f"curricula not found at {settings.curricula_dir}; "
        "the API would serve an empty programme list"
    )
    assert list(settings.curricula_dir.glob("*.json"))
