"""Owner: Person A. Which labels eval/fit_calibration.py fits on, and how it says so."""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "eval" / "fit_calibration.py"
_spec = importlib.util.spec_from_file_location("fit_calibration", SCRIPT)
fit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fit)

HEADER = "home_uid,host_uid,label,checked\n"


def write(tmp_path: Path, gold_rows: str) -> tuple[Path, Path]:
    gold = tmp_path / "gold.csv"
    gold.write_text(HEADER + gold_rows, encoding="utf-8")
    prelabels = tmp_path / "pre.csv"
    prelabels.write_text("home_uid,host_uid,llm_label,llm_reason\nh:1,x:1,2,r\nh:2,x:1,0,r\n",
                         encoding="utf-8")
    return gold, prelabels


def test_no_checked_rows_falls_back_to_the_prelabels(tmp_path: Path) -> None:
    gold, pre = write(tmp_path, "h:1,x:1,2,no\nh:2,x:1,0,no\n")
    labels, source = fit.load_labels(gold, pre)
    assert len(labels) == 2
    assert source.startswith("PROVISIONAL")


def test_a_partial_human_pass_is_still_provisional(tmp_path: Path) -> None:
    gold, pre = write(tmp_path, "h:1,x:1,1,yes\nh:2,x:1,0,no\n")
    labels, source = fit.load_labels(gold, pre)
    assert labels == {("h:1", "x:1"): 1}
    assert source.startswith("PROVISIONAL") and "1 of 2" in source


def test_a_complete_human_pass_is_final(tmp_path: Path) -> None:
    gold, pre = write(tmp_path, "h:1,x:1,1,yes\nh:2,x:1,0,yes\n")
    _, source = fit.load_labels(gold, pre)
    assert "PROVISIONAL" not in source


def test_cross_validation_keeps_each_course_out_of_its_own_fit() -> None:
    # Two courses, each with a perfectly separable pattern of its own. Predicted from the
    # other course only, the held-out predictions cannot be perfect.
    rows = [[0.0], [1.0], [0.0], [1.0]]
    positives = [0, 1, 1, 0]
    result = fit.cross_validate(rows, positives, ["a", "a", "b", "b"], folds=2)
    assert result["log_loss"] > 0.6
    assert sum(row["pairs"] for row in result["reliability"]) == 4
