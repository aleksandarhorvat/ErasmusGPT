"""Owner: Person A. Cohen's kappa in eval/kappa.py (S5-A3). Expected values by hand."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "eval" / "kappa.py"
_spec = importlib.util.spec_from_file_location("kappa", SCRIPT)
kappa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kappa)


def test_perfect_agreement_is_one() -> None:
    labels = [0, 1, 2, 2, 0]
    assert kappa.cohen_kappa(labels, labels) == pytest.approx(1.0)
    assert kappa.cohen_kappa(labels, labels, weighted=True) == pytest.approx(1.0)


def test_unweighted_matches_hand_computation() -> None:
    # A = 0 0 1 2, B = 0 1 1 2. Observed disagreement 1/4.
    # Margins A {0:2, 1:1, 2:1}, B {0:1, 1:2, 2:1}. Expected agreement
    # (2*1 + 1*2 + 1*1) / 16 = 5/16, so expected disagreement 11/16.
    # kappa = 1 - (1/4) / (11/16) = 1 - 4/11 = 7/11.
    assert kappa.cohen_kappa([0, 0, 1, 2], [0, 1, 1, 2]) == pytest.approx(7 / 11)


def test_linear_weights_charge_half_for_adjacent_labels() -> None:
    # A = 0 2, B = 1 2. Observed weighted disagreement (0.5 + 0) / 2 = 0.25.
    # Expected: margins A {0:1, 2:1}, B {1:1, 2:1}; cells (0,1) 0.5, (0,2) 1,
    # (2,1) 0.5, (2,2) 0, each with weight 1/4, so 2/4 = 0.5. kappa = 1 - 0.25/0.5.
    assert kappa.cohen_kappa([0, 2], [1, 2], weighted=True) == pytest.approx(0.5)
    # Unweighted, the same data: observed 1/2, expected 3/4, so 1 - 2/3 = 1/3.
    assert kappa.cohen_kappa([0, 2], [1, 2]) == pytest.approx(1 / 3)


def test_single_shared_category_counts_as_perfect() -> None:
    assert kappa.cohen_kappa([0, 0, 0], [0, 0, 0]) == pytest.approx(1.0)


def test_chance_level_is_zero() -> None:
    # A = 0 0 1 1, B = 0 1 0 1: observed agreement 1/2 equals expected 1/2.
    assert kappa.cohen_kappa([0, 0, 1, 1], [0, 1, 0, 1]) == pytest.approx(0.0)


def test_unequal_lengths_are_rejected() -> None:
    with pytest.raises(ValueError):
        kappa.cohen_kappa([0, 1], [0])


def test_read_labels_skips_blank_and_unchecked(tmp_path: Path) -> None:
    path = tmp_path / "pairs.csv"
    path.write_text(
        "home_uid,host_uid,label,checked\n"
        "h:1,x:1,2,yes\nh:1,x:2,,no\nh:2,x:1,0,no\n",
        encoding="utf-8",
    )
    assert kappa.read_labels(path) == {("h:1", "x:1"): 2, ("h:2", "x:1"): 0}
    assert kappa.read_labels(path, checked_only=True) == {("h:1", "x:1"): 2}
