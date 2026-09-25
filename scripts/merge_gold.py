"""Put the two halves of the gold-set check back into gold_pairs.csv. Owner: Person B.

    python scripts/merge_gold.py

Reads data/gold/half_a_luka.csv and data/gold/half_b_aleksandar.csv (made by
scripts/split_gold.py) and rewrites data/gold/gold_pairs.csv in its own row order, with
its own four columns. Everything downstream (run_eval.py, kappa.py, fit_calibration.py,
the evaluation page) keeps reading gold_pairs.csv and does not know the split happened.

Safe to run at any point, as often as you like, so half-finished work can be merged and
pushed. It refuses to write when:

- a pair is in neither half, in both, or in a half but not in gold_pairs.csv;
- a pair is checked in gold_pairs.csv with one label and checked in its half with
  another. Two people judged it; settle it by hand, in the half or in gold_pairs.csv,
  rather than letting the script pick.

A row checked in gold_pairs.csv but not yet in its half keeps the gold_pairs.csv check,
so nothing done before the split is lost.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = REPO_ROOT / "data" / "gold"
GOLD = GOLD_DIR / "gold_pairs.csv"
HALVES = {
    "Luka": GOLD_DIR / "half_a_luka.csv",
    "Aleksandar": GOLD_DIR / "half_b_aleksandar.csv",
}
COLUMNS = ["home_uid", "host_uid", "label", "checked"]

Pair = tuple[str, str]


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def key(row: dict[str, str]) -> Pair:
    return (row["home_uid"], row["host_uid"])


def is_checked(row: dict[str, str]) -> bool:
    return row.get("checked", "").strip().lower() == "yes"


def main() -> int:
    missing = [name for name, path in HALVES.items() if not path.exists()]
    if missing:
        print(f"no half for {', '.join(missing)}: run scripts/split_gold.py first")
        return 1

    gold = read(GOLD)
    gold_pairs = [key(r) for r in gold]
    halves = {name: read(path) for name, path in HALVES.items()}

    problems: list[str] = []
    counts = Counter(key(r) for rows in halves.values() for r in rows)
    for pair, count in counts.items():
        if count > 1:
            problems.append(f"{pair[0]} -> {pair[1]} is in both halves or twice in one")
    extra = set(counts) - set(gold_pairs)
    lost = set(gold_pairs) - set(counts)
    if extra:
        problems.append(f"{len(extra)} pairs are in a half but not in gold_pairs.csv")
    if lost:
        problems.append(f"{len(lost)} pairs of gold_pairs.csv are in neither half")

    by_pair = {key(r): r for rows in halves.values() for r in rows}
    merged: list[dict[str, str]] = []
    kept_from_gold = 0
    for old in gold:
        new = by_pair.get(key(old))
        if new is None:
            continue
        if is_checked(new):
            if is_checked(old) and old["label"] != new["label"]:
                problems.append(
                    f"{old['home_uid']} -> {old['host_uid']}: checked as {old['label']} in "
                    f"gold_pairs.csv and as {new['label']} in its half")
            merged.append({"home_uid": old["home_uid"], "host_uid": old["host_uid"],
                           "label": new["label"], "checked": "yes"})
        elif is_checked(old):
            kept_from_gold += 1
            merged.append({k: old[k] for k in COLUMNS})
        else:
            merged.append({"home_uid": old["home_uid"], "host_uid": old["host_uid"],
                           "label": new["label"], "checked": "no"})

    if problems:
        print(f"not written, {len(problems)} problem(s):\n")
        for problem in problems[:40]:
            print("  " + problem)
        return 1

    with GOLD.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(merged)

    for name, rows in halves.items():
        done = sum(is_checked(r) for r in rows)
        print(f"{name}: {done} of {len(rows)} checked")
    total = sum(is_checked(r) for r in merged)
    note = f", {kept_from_gold} of them from before the split" if kept_from_gold else ""
    print(f"gold_pairs.csv: {total} of {len(merged)} checked{note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
