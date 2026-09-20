"""Draw Person B's cold slice for Cohen's kappa (S5-B1). Owner: Person B.

The slice has to be labelled without seeing the model's suggestion or Person A's
corrections, or kappa measures how similarly two people anchor on a machine rather than
how much two people agree. So this script strips every label on the way out, and the
sample is stratified by the model's own distribution only so that the 30 pairs are not
all obvious non-matches.

    python scripts/make_kappa_slice.py [--n 30] [--seed 20260920]

Writes data/gold/gold_pairs_b.csv with empty labels. Label it in tools/annotate.html,
then Person A computes kappa against the same pairs in gold_pairs.csv.
"""
from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PRELABELS = REPO_ROOT / "data" / "gold" / "llm_prelabels.csv"
OUT = REPO_ROOT / "data" / "gold" / "gold_pairs_b.csv"

# Over-sample the pairs the model thinks are matches. Agreement on 30 obvious zeroes
# would be a meaningless kappa, because both annotators would say zero every time.
SHARE = {2: 0.30, 1: 0.40, 0: 0.30}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260920)
    parser.add_argument("--force", action="store_true", help="overwrite an existing slice")
    args = parser.parse_args()

    if OUT.exists() and not args.force:
        print(f"{OUT.name} already exists. Re-drawing it after labelling would throw the "
              f"work away, so pass --force if that is really what you want.")
        return 1
    if not PRELABELS.exists():
        print(f"missing {PRELABELS}. Run eval/make_pool.py first (S5-A0).")
        return 1

    buckets: dict[int, list[dict]] = defaultdict(list)
    with PRELABELS.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("llm_label", "").strip():
                buckets[int(row["llm_label"])].append(row)

    rng = random.Random(args.seed)
    drawn: list[dict] = []
    for label, share in SHARE.items():
        pool = buckets.get(label, [])
        want = min(round(args.n * share), len(pool))
        drawn.extend(rng.sample(pool, want))
    # top up from whatever is left if a bucket was too small
    remaining = [r for label in buckets for r in buckets[label] if r not in drawn]
    while len(drawn) < args.n and remaining:
        drawn.append(remaining.pop(rng.randrange(len(remaining))))
    rng.shuffle(drawn)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["home_uid", "host_uid", "label", "checked"])
        for row in drawn:
            writer.writerow([row["home_uid"], row["host_uid"], "", "no"])

    print(f"wrote {len(drawn)} unlabelled pairs to {OUT.relative_to(REPO_ROOT)}")
    print("Label them cold in tools/annotate.html. Do not open gold_pairs.csv first.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
