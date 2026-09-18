"""Offline evaluation harness. Owner: Person A. Stage 5, task S5-A2.

Rule that must not be broken: this script imports the SAME app.matching code the API
serves. Do not reimplement scoring here; the report would then describe a system that is
not the one being demonstrated.

Usage:
    python eval/run_eval.py --host-programme utwente-tcs-bsc --out eval/report

Produces eval/report/results.md and results.csv with, per configuration:
    Recall@5, Recall@10, MRR@10, nDCG@10, P@1, ms/query
plus 95% bootstrap CIs and a paired test against the dense-minilm baseline.
Protocol: docs/05-evaluation.md
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD = REPO_ROOT / "data" / "gold" / "gold_pairs.csv"

CONFIGS = ["bm25", "dense-minilm", "dense-bge", "hybrid", "hybrid+ce"]


def load_gold(path: Path = GOLD) -> dict[str, dict[str, int]]:
    """home_uid -> {host_uid: label}, human-checked rows only.

    Rows with checked != yes are machine proposals nobody has read, so they must not
    reach the metrics (docs/05-evaluation.md). Unlabelled pairs count as 0, which is a
    property of the pooled collection and belongs in the report.
    """
    gold: dict[str, dict[str, int]] = defaultdict(dict)
    skipped = 0
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("checked", "").strip().lower() != "yes":
                skipped += 1
                continue
            gold[row["home_uid"]][row["host_uid"]] = int(row["label"])
    if skipped:
        print(f"note: skipped {skipped} unchecked rows in {path.name}")
    return dict(gold)


def correction_rate(
    prelabels: Path = REPO_ROOT / "data" / "gold" / "llm_prelabels.csv",
    final: Path = GOLD,
) -> tuple[int, int]:
    """(corrections, compared) between the frozen pre-labels and the checked labels.

    This is the number the report quotes as evidence that the human pass was real.
    """
    if not prelabels.exists():
        return (0, 0)
    with prelabels.open(encoding="utf-8") as handle:
        proposed = {
            (r["home_uid"], r["host_uid"]): int(r["llm_label"])
            for r in csv.DictReader(handle)
            if r.get("llm_label", "").strip() != ""
        }
    corrections = compared = 0
    with final.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("checked", "").strip().lower() != "yes":
                continue
            key = (row["home_uid"], row["host_uid"])
            if key in proposed:
                compared += 1
                corrections += int(proposed[key] != int(row["label"]))
    return (corrections, compared)


# --- metrics (pure functions, unit-tested in backend/tests/test_matching_metrics.py) ---
def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(ranked[:k]) & relevant) / len(relevant)


def reciprocal_rank(ranked: list[str], relevant: set[str], k: int = 10) -> float:
    for index, uid in enumerate(ranked[:k], start=1):
        if uid in relevant:
            return 1.0 / index
    return 0.0


def ndcg_at_k(ranked: list[str], labels: dict[str, int], k: int = 10) -> float:
    import math

    dcg = sum(labels.get(uid, 0) / math.log2(i + 1) for i, uid in enumerate(ranked[:k], start=1))
    ideal = sorted(labels.values(), reverse=True)[:k]
    idcg = sum(rel / math.log2(i + 1) for i, rel in enumerate(ideal, start=1))
    return dcg / idcg if idcg else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home-programme", default="uns-pmf-informatics-bsc")
    parser.add_argument("--host-programme", required=True)
    parser.add_argument("--out", default="eval/report")
    parser.parse_args()

    raise NotImplementedError(
        "S5-A2: wire this to app.matching, run every config in CONFIGS, "
        "write results.md + results.csv with bootstrap CIs."
    )


if __name__ == "__main__":
    raise SystemExit(main())
