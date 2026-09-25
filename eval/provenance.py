"""Who produced each gold label. Read by run_eval.py, kappa.py and fit_calibration.py.

On 2026-09-26 Person A decided, for lack of time, that the unchecked rows of his half
would take the labels of a second model (Claude) instead of a human check. Every report
built on the gold set has to say so, and this module is the one place that knows which
rows those are: `data/gold/claude_labels_a.csv` marks them with `final=yes`, and
`data/gold/provenance.json` says in words who did what.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = REPO_ROOT / "data" / "gold"
CLAUDE = GOLD_DIR / "claude_labels_a.csv"
RECORD = GOLD_DIR / "provenance.json"

Pair = tuple[str, str]


def claude_labels(path: Path = CLAUDE) -> dict[Pair, tuple[int, bool]]:
    """(home, host) -> (Claude's label, whether that label is the one in the gold set)."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        return {
            (row["home_uid"], row["host_uid"]): (int(row["claude_label"]),
                                                 row.get("final", "") == "yes")
            for row in csv.DictReader(handle)
        }


def model_pairs(path: Path = CLAUDE) -> set[Pair]:
    """The gold pairs whose label came from a model rather than a human."""
    return {pair for pair, (_, final) in claude_labels(path).items() if final}


def describe(record: Path = RECORD) -> str:
    """One sentence per source, for the top of a report. Empty if all labels are human."""
    if not record.exists():
        return ""
    counts = json.loads(record.read_text(encoding="utf-8")).get("counts", {})
    if not counts.get("model"):
        return ""
    return (
        f"Of {counts['total']} gold rows, {counts['human']} were checked by a human with "
        f"the pre-label shown and {counts['model']} were labelled by a second model "
        "(Claude), blind to the pre-labels, and not checked by a human. Decided by "
        "Person A for lack of time; see `data/gold/provenance.json`."
    )
