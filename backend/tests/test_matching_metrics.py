"""Owner: Person A. The IR metrics and the statistics in eval/run_eval.py (S5-A4).

Expected values are worked out by hand in the comments. A metric that silently changes
definition would otherwise move every number in the report with nothing to catch it.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "eval" / "run_eval.py"
_spec = importlib.util.spec_from_file_location("run_eval", SCRIPT)
run_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_eval)


# --- recall -----------------------------------------------------------------

def test_recall_counts_relevant_documents_found() -> None:
    ranked = ["a", "b", "c", "d", "e", "f"]
    relevant = {"b", "f", "z"}  # z is never retrieved
    assert run_eval.recall_at_k(ranked, relevant, 5) == pytest.approx(1 / 3)
    assert run_eval.recall_at_k(ranked, relevant, 10) == pytest.approx(2 / 3)


def test_recall_without_relevant_documents_is_zero_not_an_error() -> None:
    assert run_eval.recall_at_k(["a"], set(), 5) == 0.0


# --- reciprocal rank --------------------------------------------------------

def test_reciprocal_rank_uses_the_first_hit() -> None:
    assert run_eval.reciprocal_rank(["x", "y", "a"], {"a", "y"}) == pytest.approx(0.5)
    assert run_eval.reciprocal_rank(["a"], {"a"}) == 1.0


def test_reciprocal_rank_past_the_cutoff_is_zero() -> None:
    ranked = [f"miss{i}" for i in range(10)] + ["hit"]
    assert run_eval.reciprocal_rank(ranked, {"hit"}, 10) == 0.0


# --- nDCG -------------------------------------------------------------------

def test_ndcg_with_a_perfect_ranking_is_one() -> None:
    labels = {"a": 2, "b": 1}
    assert run_eval.ndcg_at_k(["a", "b"], labels, 10) == pytest.approx(1.0)


def test_ndcg_hand_computed_for_a_swapped_pair() -> None:
    # ranked b, a with labels a=2, b=1:
    #   DCG  = 1/log2(2) + 2/log2(3) = 1 + 1.26186 = 2.26186
    #   IDCG = 2/log2(2) + 1/log2(3) = 2 + 0.63093 = 2.63093
    labels = {"a": 2, "b": 1}
    expected = (1 + 2 / math.log2(3)) / (2 + 1 / math.log2(3))
    assert run_eval.ndcg_at_k(["b", "a"], labels, 10) == pytest.approx(expected)
    assert run_eval.ndcg_at_k(["b", "a"], labels, 10) < 1.0


def test_ndcg_rewards_grade_two_over_grade_one() -> None:
    labels = {"good": 2, "partial": 1}
    assert run_eval.ndcg_at_k(["good", "partial"], labels, 10) > run_eval.ndcg_at_k(
        ["partial", "good"], labels, 10
    )


def test_ndcg_without_labels_is_zero() -> None:
    assert run_eval.ndcg_at_k(["a"], {}, 10) == 0.0


# --- precision at 1 ---------------------------------------------------------

def test_precision_at_1() -> None:
    assert run_eval.precision_at_1(["a", "b"], {"a"}) == 1.0
    assert run_eval.precision_at_1(["b", "a"], {"a"}) == 0.0
    assert run_eval.precision_at_1([], {"a"}) == 0.0


# --- statistics -------------------------------------------------------------

def test_bootstrap_interval_brackets_the_mean_and_repeats() -> None:
    values = [1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 1.0]
    low, high = run_eval.bootstrap_ci(values)
    assert low <= sum(values) / len(values) <= high
    assert (low, high) == run_eval.bootstrap_ci(values)  # seeded


def test_bootstrap_interval_of_a_constant_has_zero_width() -> None:
    assert run_eval.bootstrap_ci([0.5] * 20) == pytest.approx((0.5, 0.5))


def test_paired_test_sees_a_consistent_difference() -> None:
    treatment = [1.0] * 30
    baseline = [0.0] * 30
    assert run_eval.paired_bootstrap_p(treatment, baseline) < 0.05


def test_paired_test_does_not_see_a_difference_that_is_not_there() -> None:
    values = [1.0, 0.0] * 15
    assert run_eval.paired_bootstrap_p(values, values) == 1.0


def test_paired_test_needs_matching_lengths() -> None:
    with pytest.raises(ValueError):
        run_eval.paired_bootstrap_p([1.0, 0.0], [1.0])


# --- the gold set loader ----------------------------------------------------

def test_unchecked_rows_never_reach_the_metrics(tmp_path: Path) -> None:
    path = tmp_path / "gold.csv"
    path.write_text(
        "home_uid,host_uid,label,checked\n"
        "h:1,t:1,2,yes\n"
        "h:1,t:2,1,no\n"
        "h:2,t:3,0,yes\n",
        encoding="utf-8",
    )
    gold = run_eval.load_gold(path)
    assert gold == {"h:1": {"t:1": 2}, "h:2": {"t:3": 0}}


def test_correction_rate_counts_changed_labels(tmp_path: Path) -> None:
    prelabels = tmp_path / "llm_prelabels.csv"
    prelabels.write_text(
        "home_uid,host_uid,llm_label,llm_reason\n"
        "h:1,t:1,2,both cover sql\n"
        "h:1,t:2,2,guessed\n",
        encoding="utf-8",
    )
    final = tmp_path / "gold_pairs.csv"
    final.write_text(
        "home_uid,host_uid,label,checked\n"
        "h:1,t:1,2,yes\n"
        "h:1,t:2,0,yes\n",
        encoding="utf-8",
    )
    assert run_eval.correction_rate(prelabels, final) == (1, 2)


def test_correction_rate_without_prelabels_is_empty(tmp_path: Path) -> None:
    assert run_eval.correction_rate(tmp_path / "missing.csv", tmp_path / "also.csv") == (0, 0)


def test_every_reported_configuration_has_a_setup() -> None:
    assert set(run_eval.CONFIGS) == set(run_eval.CONFIG_SETUP)
    assert run_eval.BASELINE in run_eval.CONFIG_SETUP


# --- which queries count (host_view) -----------------------------------------

def test_host_view_drops_other_programmes_and_queries_with_nothing_to_find() -> None:
    gold = {
        "home:a": {"tcs:1": 2, "am:9": 1},   # relevant at both hosts
        "home:b": {"tcs:2": 0, "am:8": 2},   # relevant only at the other host
        "home:c": {"tcs:3": 1},
    }
    view = run_eval.host_view(gold, {"tcs:1", "tcs:2", "tcs:3"})
    assert view == {"home:a": {"tcs:1": 2}, "home:c": {"tcs:3": 1}}
