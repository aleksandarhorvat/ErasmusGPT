"""Structural checks on the gold set. Owner: Person B. Runs in CI.

Not about whether a label is right, which is Person A's judgement. About the things that
silently corrupt an evaluation: a duplicate pair counted twice, a course id that no
longer exists after a re-scrape, a stray label value, or a row marked checked with no
label in it.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD = REPO_ROOT / "data" / "gold" / "gold_pairs.csv"
SLICE = REPO_ROOT / "data" / "gold" / "gold_pairs_b.csv"
PRELABELS = REPO_ROOT / "data" / "gold" / "llm_prelabels.csv"
HALF_A = REPO_ROOT / "data" / "gold" / "half_a_luka.csv"
HALF_B = REPO_ROOT / "data" / "gold" / "half_b_aleksandar.csv"


def known_uids() -> set[str]:
    uids: set[str] = set()
    for path in sorted((REPO_ROOT / "data" / "curricula").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for course in data.get("courses", []):
            uids.add(f"{data['institution_id']}:{course['code']}")
    return uids


def check(path: Path, uids: set[str], label_column: str, problems: list[str]) -> None:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    name = path.name
    if not rows:
        problems.append(f"{name}: no rows")
        return

    seen = Counter((r["home_uid"], r["host_uid"]) for r in rows)
    for pair, count in seen.items():
        if count > 1:
            problems.append(f"{name}: {pair[0]} -> {pair[1]} appears {count} times")

    for number, row in enumerate(rows, start=2):
        for column in ("home_uid", "host_uid"):
            if row[column] not in uids:
                problems.append(f"{name}:{number}: {row[column]} is not in any curriculum")
        value = (row.get(label_column) or "").strip()
        checked = (row.get("checked") or "").strip().lower()
        if value and value not in {"0", "1", "2"}:
            problems.append(f"{name}:{number}: label {value!r} is not 0, 1 or 2")
        if checked == "yes" and not value:
            problems.append(f"{name}:{number}: marked checked but has no label")
        if checked not in {"yes", "no", ""}:
            problems.append(f"{name}:{number}: checked is {checked!r}, expected yes or no")


def pairs(path: Path) -> set[tuple[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return {(r["home_uid"], r["host_uid"]) for r in csv.DictReader(handle)}


def check_halves(problems: list[str]) -> None:
    """The split made by split_gold.py still covers gold_pairs.csv exactly once."""
    if not (HALF_A.exists() and HALF_B.exists() and GOLD.exists()):
        return
    half_a, half_b, gold = pairs(HALF_A), pairs(HALF_B), pairs(GOLD)
    if half_a & half_b:
        problems.append(f"{len(half_a & half_b)} pairs are in both halves")
    if (half_a | half_b) != gold:
        problems.append(
            f"the halves cover {len(half_a | half_b)} pairs, gold_pairs.csv has {len(gold)}; "
            "they have drifted apart")
    if SLICE.exists() and pairs(SLICE) & half_b:
        problems.append(
            f"{len(pairs(SLICE) & half_b)} cold-slice pairs are in Aleksandar's half, so he "
            "would see the model's label before labelling them blind")


def main() -> int:
    uids = known_uids()
    problems: list[str] = []
    check(GOLD, uids, "label", problems)
    check(SLICE, uids, "label", problems)
    check(PRELABELS, uids, "llm_label", problems)
    check(HALF_A, uids, "label", problems)
    check(HALF_B, uids, "label", problems)
    check_halves(problems)

    if GOLD.exists() and PRELABELS.exists():
        with GOLD.open(encoding="utf-8") as handle:
            gold = {(r["home_uid"], r["host_uid"]) for r in csv.DictReader(handle)}
        with PRELABELS.open(encoding="utf-8") as handle:
            pre = {(r["home_uid"], r["host_uid"]) for r in csv.DictReader(handle)}
        missing = pre - gold
        if missing:
            problems.append(
                f"gold_pairs.csv is missing {len(missing)} pairs that llm_prelabels.csv has; "
                "the correction rate would be computed over a subset"
            )

    if problems:
        print(f"{len(problems)} problem(s) in the gold set:\n")
        for problem in problems[:40]:
            print("  " + problem)
        if len(problems) > 40:
            print(f"  ... and {len(problems) - 40} more")
        return 1
    print("gold set ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
