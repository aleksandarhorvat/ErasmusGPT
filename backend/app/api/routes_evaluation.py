"""Serves the evaluation results to the app. Owner: Person B. Task S5-B3.

The numbers themselves are Person A's, produced by `eval/run_eval.py`. This endpoint only
finds them and says how much to trust them, because the honest answer right now is "not
much yet": every figure in `eval/report/` was computed against labels a model wrote and
no human has checked (`S5-A1`). A page that showed the table without that sentence would
be worse than no page.
"""
from __future__ import annotations

import csv
import json
import logging

from fastapi import APIRouter, Depends

from app.api.deps import Settings, get_settings
from app.schemas import EvaluationResponse

log = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

RESULTS = "results.csv"


def _gold_progress(settings: Settings) -> tuple[int, int]:
    """(checked rows, total rows) in the gold set."""
    path = settings.data_dir / "gold" / "gold_pairs.csv"
    if not path.exists():
        return (0, 0)
    checked = total = 0
    try:
        # utf-8-sig: a file saved by Excel starts with a BOM, which would otherwise glue
        # itself to the first column name.
        with path.open(encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                total += 1
                checked += ((row.get("checked") or "").strip().lower() == "yes")
    except (OSError, UnicodeDecodeError, csv.Error):
        log.warning("cannot read %s; reporting the gold set as empty", path)
        return (0, 0)
    return (checked, total)


def is_provisional(checked: int, total: int) -> bool:
    """True until the human pass has read every pooled row.

    A partial pass is still provisional: `eval/run_eval.py` scores only checked rows, so
    with 200 of 1142 checked the table covers whichever home courses happened to be
    labelled first, and it is not the number the report will quote.
    """
    return total == 0 or checked < total


def label_sources(settings: Settings, checked: int) -> tuple[int, int]:
    """(rows labelled by a person, rows labelled by a model) among the checked rows.

    `checked=yes` only says a row has its final label, not who gave it. Since
    2026-09-26 part of the gold set was labelled by a second model at Person A's
    decision, recorded in data/gold/provenance.json. Without that file every checked
    row is a human one, which was true before it existed.
    """
    path = settings.data_dir / "gold" / "provenance.json"
    if not path.is_file():
        return (checked, 0)
    try:
        counts = json.loads(path.read_text(encoding="utf-8")).get("counts", {})
        model = int(counts.get("model", 0))
    except (OSError, ValueError, TypeError, AttributeError, OverflowError):
        log.warning("ignoring unreadable %s", path)
        return (checked, 0)
    model = max(0, min(model, checked))
    return (checked - model, model)


@router.get("", response_model=EvaluationResponse)
def evaluation(settings: Settings = Depends(get_settings)) -> EvaluationResponse:
    checked, total = _gold_progress(settings)
    human, model = label_sources(settings, checked)
    reports = sorted(p.name for p in settings.report_dir.glob("*.md")) \
        if settings.report_dir.is_dir() else []

    rows: list[dict[str, str]] = []
    columns: list[str] = []
    path = settings.report_dir / RESULTS
    if path.is_file():
        try:
            with path.open(encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                columns = [c for c in (reader.fieldnames or []) if c]
                # A short row gives None values and a long one a None key; the page wants
                # a plain table of strings either way.
                rows = [{c: (r.get(c) or "") for c in columns} for r in reader]
        except (OSError, UnicodeDecodeError, csv.Error):
            log.warning("cannot read %s; showing no results table", path)
            columns, rows = [], []

    return EvaluationResponse(
        available=bool(rows),
        provisional=is_provisional(checked, total),
        gold_checked=checked,
        gold_total=total,
        gold_human=human,
        gold_model=model,
        columns=columns,
        rows=rows,
        reports=reports,
    )
