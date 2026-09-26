"""Which strategies have a fitted calibration. Owner: Person B.

`score_pct` means different things per strategy: a probability where
`eval/fit_calibration.py` has fitted one (S6-A4), a stretched cosine for `dense`, and a
per-query relative value for `bm25` and `hybrid`. The UI must not print "87 % chance"
over a number that is not a probability, so it needs to know which is which.

This reads the same directory the pipeline reads, rather than asking the matcher, so
nothing in Person A's zone has to change.
"""
from __future__ import annotations

import json
import logging

from app.core.config import Settings
from app.schemas.match import Strategy

log = logging.getLogger(__name__)

VALID: set[str] = {"bm25", "dense", "hybrid", "hybrid+ce"}


def calibrated_strategies(settings: Settings) -> set[Strategy]:
    """Strategies with a usable calibration file in data/calibration/."""
    directory = settings.data_dir / "calibration"
    if not directory.is_dir():
        return set()
    found: set[Strategy] = set()
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            log.warning("ignoring unreadable calibration file %s", path)
            continue
        strategy = data.get("strategy")
        if strategy in VALID and {"a", "b"} <= data.keys():
            found.add(strategy)  # type: ignore[arg-type]
    return found


def provisional_strategies(settings: Settings) -> set[Strategy]:
    """Calibrations fitted on machine labels rather than human-checked ones.

    `fit_calibration.py` stamps `label_source` into the file and starts it with
    PROVISIONAL while any of its labels are not a person's: first the pre-labels, then a
    partial human pass, and since 2026-09-26 a gold set partly labelled by a second model.
    The UI has to say so, or it presents a model's judgement as a measured probability.
    """
    directory = settings.data_dir / "calibration"
    if not directory.is_dir():
        return set()
    provisional: set[Strategy] = set()
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("strategy") in VALID and "PROVISIONAL" in str(data.get("label_source", "")):
            provisional.add(data["strategy"])
    return provisional
