"""Serves the evaluation results to the app. Owner: Person B. Task S5-B3.

The numbers themselves are Person A's, produced by `eval/run_eval.py`. This endpoint only
finds them and says how much to trust them, because the honest answer right now is "not
much yet": every figure in `eval/report/` was computed against labels a model wrote and
no human has checked (`S5-A1`). A page that showed the table without that sentence would
be worse than no page.
"""
from __future__ import annotations

import csv

from fastapi import APIRouter, Depends

from app.api.deps import Settings, get_settings
from app.schemas import EvaluationResponse

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

RESULTS = "results.csv"


def _gold_progress(settings: Settings) -> tuple[int, int]:
    """(checked rows, total rows) in the gold set."""
    path = settings.data_dir / "gold" / "gold_pairs.csv"
    if not path.exists():
        return (0, 0)
    checked = total = 0
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            total += 1
            checked += (row.get("checked", "").strip().lower() == "yes")
    return (checked, total)


def is_provisional(checked: int, total: int) -> bool:
    """True until the human pass has read every pooled row.

    A partial pass is still provisional: `eval/run_eval.py` scores only checked rows, so
    with 200 of 1142 checked the table covers whichever home courses happened to be
    labelled first, and it is not the number the report will quote.
    """
    return total == 0 or checked < total


@router.get("", response_model=EvaluationResponse)
def evaluation(settings: Settings = Depends(get_settings)) -> EvaluationResponse:
    checked, total = _gold_progress(settings)
    reports = sorted(p.name for p in settings.report_dir.glob("*.md")) \
        if settings.report_dir.is_dir() else []

    rows: list[dict[str, str]] = []
    columns: list[str] = []
    path = settings.report_dir / RESULTS
    if path.is_file():
        with path.open(encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            columns = list(reader.fieldnames or [])
            rows = [dict(r) for r in reader]

    return EvaluationResponse(
        available=bool(rows),
        provisional=is_provisional(checked, total),
        gold_checked=checked,
        gold_total=total,
        columns=columns,
        rows=rows,
        reports=reports,
    )
