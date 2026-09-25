"""Split the gold-set check between the two of us. Owner: Person B. Task S5-A1.

    python scripts/split_gold.py

Writes two files next to gold_pairs.csv, one per person, so each of us labels in our own
file and git never has to merge the same CSV twice:

    data/gold/half_a_luka.csv
    data/gold/half_b_aleksandar.csv

`python scripts/merge_gold.py` puts them back into gold_pairs.csv, which is the only file
the evaluation reads. It can be run at any time, so partial progress can be pushed.

How the rows are divided:

- By **home course**, never by row, so one person judges every candidate for a course
  and the scale stays consistent within it.
- The 30 cold pairs in gold_pairs_b.csv (S5-B1) all go to Luka. Aleksandar labels them
  blind, and Cohen's kappa compares that blind label with Luka's checked one. If they
  were in Aleksandar's half he would see the model's label for them first.
- The halves are balanced on estimated time, not row count. A pair the model called 0
  is usually settled from the two titles (about 7 s); a 1 or a 2 means reading both
  descriptions (about 40 s). Aleksandar's side starts with the cold slice, about 75 s a
  pair, because he labels that too.

Each half keeps `llm_label` and `llm_reason`, so the annotator shows the model's
proposal and counts corrections even when a half-finished file is reopened.

Running it again is safe. Once the halves exist their split is kept; the only thing a
re-run does is copy rows already checked in gold_pairs.csv into the half that owns them
and is still unchecked there, so checks done before the split are not lost.
"""
from __future__ import annotations

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = REPO_ROOT / "data" / "gold"
GOLD = GOLD_DIR / "gold_pairs.csv"
PRELABELS = GOLD_DIR / "llm_prelabels.csv"
SLICE = GOLD_DIR / "gold_pairs_b.csv"
HALF_A = GOLD_DIR / "half_a_luka.csv"
HALF_B = GOLD_DIR / "half_b_aleksandar.csv"
COLUMNS = ["home_uid", "host_uid", "llm_label", "llm_reason", "label", "checked"]

SECONDS_OBVIOUS = 7    # model said 0: usually the titles settle it
SECONDS_READ = 40      # model said 1 or 2: both descriptions have to be read
SECONDS_COLD = 75      # a cold-slice pair, no proposal to start from

Pair = tuple[str, str]


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({k: row.get(k, "") for k in COLUMNS} for row in rows)


def cost(row: dict[str, str]) -> int:
    return SECONDS_OBVIOUS if row.get("llm_label", "0") == "0" else SECONDS_READ


def key(row: dict[str, str]) -> Pair:
    return (row["home_uid"], row["host_uid"])


def is_checked(row: dict[str, str]) -> bool:
    return row.get("checked", "").strip().lower() == "yes"


def split() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    gold = read(GOLD)
    proposals = {key(r): r for r in read(PRELABELS)}
    cold = {key(r) for r in read(SLICE)} if SLICE.exists() else set()

    rows: list[dict[str, str]] = []
    for row in gold:
        proposal = proposals.get(key(row), {})
        rows.append({
            "home_uid": row["home_uid"],
            "host_uid": row["host_uid"],
            "llm_label": proposal.get("llm_label", ""),
            "llm_reason": proposal.get("llm_reason", ""),
            "label": row.get("label", ""),
            "checked": "yes" if is_checked(row) else "no",
        })

    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if key(row) not in cold:
            groups.setdefault(row["home_uid"], []).append(row)

    owner: dict[Pair, str] = {pair: "a" for pair in cold}
    load = {"a": sum(cost(r) for r in rows if key(r) in cold),
            "b": SECONDS_COLD * len(cold)}
    for home in sorted(groups, key=lambda h: (-sum(cost(r) for r in groups[h]), h)):
        side = min(load, key=lambda s: (load[s], s))
        load[side] += sum(cost(r) for r in groups[home])
        for row in groups[home]:
            owner[key(row)] = side

    half_a = [r for r in rows if owner[key(r)] == "a"]
    half_b = [r for r in rows if owner[key(r)] == "b"]
    return half_a, half_b


def carry_over(half: list[dict[str, str]], gold: dict[Pair, dict[str, str]]) -> int:
    """Copy checks made in gold_pairs.csv into rows still unchecked in the half."""
    copied = 0
    for row in half:
        done = gold.get(key(row))
        if done and is_checked(done) and not is_checked(row):
            row["label"], row["checked"] = done["label"], "yes"
            copied += 1
    return copied


def minutes(rows: list[dict[str, str]]) -> int:
    return round(sum(cost(r) for r in rows) / 60)


def main() -> int:
    if HALF_A.exists() and HALF_B.exists():
        gold = {key(r): r for r in read(GOLD)}
        half_a, half_b = read(HALF_A), read(HALF_B)
        copied = carry_over(half_a, gold) + carry_over(half_b, gold)
        write(HALF_A, half_a)
        write(HALF_B, half_b)
        print(f"halves already exist, split kept; copied {copied} checked rows "
              "from gold_pairs.csv")
        return 0

    half_a, half_b = split()
    write(HALF_A, half_a)
    write(HALF_B, half_b)
    cold = len(read(SLICE)) if SLICE.exists() else 0
    for path, half, extra in ((HALF_A, half_a, 0), (HALF_B, half_b, cold)):
        homes = len({r["home_uid"] for r in half})
        positives = sum(r["llm_label"] in {"1", "2"} for r in half)
        note = f" + {cold} cold pairs, about {round(extra * SECONDS_COLD / 60)} min" if extra else ""
        print(f"{path.name}: {len(half)} rows over {homes} home courses, "
              f"{positives} proposed 1 or 2, about {minutes(half)} min{note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
