"""Find the queries the system gets worst, for S6-A2.

    python eval/error_analysis.py --host-programme utwente-tcs-bsc

Prints, per home course, where the first relevant host course lands and what the system
returned instead. Classification into the failure categories in docs/01-universities.md
is a human job; this only lays out the evidence to classify.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

GOLD = REPO_ROOT / "data" / "gold" / "gold_pairs.csv"
PRELABELS = REPO_ROOT / "data" / "gold" / "llm_prelabels.csv"


def load_labels() -> tuple[dict[str, dict[str, int]], str]:
    """Checked rows if there are any, the frozen pre-labels otherwise."""
    checked: dict[str, dict[str, int]] = defaultdict(dict)
    if GOLD.exists():
        with GOLD.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row.get("checked", "").strip().lower() == "yes":
                    checked[row["home_uid"]][row["host_uid"]] = int(row["label"])
    if checked:
        return dict(checked), "human-checked gold_pairs.csv"

    machine: dict[str, dict[str, int]] = defaultdict(dict)
    with PRELABELS.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("llm_label", "").strip():
                machine[row["home_uid"]][row["host_uid"]] = int(row["llm_label"])
    return dict(machine), "PROVISIONAL pre-labels"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--home-programme", default="uns-pmf-informatics-bsc")
    parser.add_argument("--host-programme", required=True)
    parser.add_argument("--strategy", default="hybrid")
    parser.add_argument("--worst", type=int, default=10)
    args = parser.parse_args()

    from app.core.config import get_settings
    from app.ingest.loader import CurriculumStore
    from app.matching.pipeline import PipelineMatcher

    settings = get_settings()
    store = CurriculumStore(settings.curricula_dir)
    matcher = PipelineMatcher(store, settings)
    labels, source = load_labels()
    host_uids = {c.course_uid for c in store.get_courses(args.host_programme)}

    rows = []
    for course in store.get_courses(args.home_programme):
        relevant = {
            uid for uid, label in labels.get(course.course_uid, {}).items()
            if label >= 1 and uid in host_uids
        }
        if not relevant:
            continue
        ranked = matcher.match_course(
            course.course_uid, args.host_programme, args.strategy, 10
        )
        order = [c.host_course.course_uid for c in ranked]
        first = next((i + 1 for i, uid in enumerate(order) if uid in relevant), None)
        rows.append({
            "code": course.code,
            "title": course.title,
            "rank_of_first_relevant": first,
            "returned": [(c.host_course.title, c.score_pct) for c in ranked[:3]],
            "expected": [store.get_course(uid).title for uid in sorted(relevant)][:3],
        })

    rows.sort(key=lambda r: (r["rank_of_first_relevant"] or 99), reverse=True)
    print(f"labels: {source}. {len(rows)} queries against {args.host_programme}, "
          f"strategy {args.strategy}.\n")
    for row in rows[: args.worst]:
        rank = row["rank_of_first_relevant"]
        print(f"{row['code']} {row['title']}")
        print(f"  first relevant at rank {rank if rank else 'not in top 10'}")
        print("  returned: " + " | ".join(f"{t} ({p} %)" for t, p in row["returned"]))
        print("  expected: " + ", ".join(row["expected"]))
        print()
    missed = sum(1 for r in rows if r["rank_of_first_relevant"] is None)
    top1 = sum(1 for r in rows if r["rank_of_first_relevant"] == 1)
    print(f"summary: {top1} of {len(rows)} right at rank 1, {missed} with nothing in the top 10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
