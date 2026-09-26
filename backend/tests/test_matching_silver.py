"""Owner: Person A. The silver set's sampling (eval/make_silver_pool.py)."""
from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "eval" / "make_silver_pool.py"
_spec = importlib.util.spec_from_file_location("make_silver_pool", SCRIPT)
pool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pool)

STRATA = {
    "maths": [f"m{i}" for i in range(14)],
    "theory": [f"t{i}" for i in range(7)],
    "electives": [f"e{i}" for i in range(7)],
    "systems": [f"s{i}" for i in range(5)],
    "ai": ["a0", "a1"],
}


def test_sample_is_proportional_and_exactly_n() -> None:
    chosen = pool.stratified_sample(STRATA, 14, seed=1)
    assert len(chosen) == 14 and len(set(chosen)) == 14
    counts = Counter(uid[0] for uid in chosen)
    # 35 items, 14 wanted: exact shares 5.6, 2.8, 2.8, 2.0, 0.8
    assert counts == {"m": 5, "t": 3, "e": 3, "s": 2, "a": 1}


def test_sample_is_reproducible_and_seed_dependent() -> None:
    assert pool.stratified_sample(STRATA, 14, seed=1) == pool.stratified_sample(STRATA, 14,
                                                                                seed=1)
    assert pool.stratified_sample(STRATA, 14, seed=1) != pool.stratified_sample(STRATA, 14,
                                                                                seed=2)


def test_committed_strata_cover_the_whole_home_programme() -> None:
    strata = pool.read_strata()
    uids = [uid for items in strata.values() for uid in items]
    assert len(uids) == len(set(uids)) == 50
