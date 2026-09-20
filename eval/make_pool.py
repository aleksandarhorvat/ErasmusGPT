"""Pool the pairs worth labelling and lay out the pre-label file. Stage 5, task S5-A0.

Pooling, not the full cross product: the union of the top 10 from `dense` and
`hybrid+ce` per home course. Pool depth 10 is all that Recall@5, MRR@10 and nDCG@10 can
see, so labelling deeper buys nothing (docs/03-data-schema.md, section Which pairs to
label).

    python eval/make_pool.py --host-programme utwente-tcs-bsc --max-home 40

Writes two files:
  data/.cache/pool.<host>.csv - the pairs, with both course texts, for the labeller
  data/gold/llm_prelabels.csv - the same pairs with an empty llm_label column

Fill `llm_label` and `llm_reason` in the second file, commit it unedited, then copy it to
gold_pairs.csv and correct it by hand in tools/annotate.html (S5-A1). The diff between
the two files is the correction rate the report has to disclose.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

GOLD_DIR = REPO_ROOT / "data" / "gold"
# The pool carries both courses' full text for the labeller. It is regenerable, and it
# quotes university prose verbatim, so it lives in the git-ignored cache rather than in
# data/gold next to the labels.
POOL_DIR = REPO_ROOT / "data" / ".cache"
PRELABELS = GOLD_DIR / "llm_prelabels.csv"

POOL_DEPTH = 10
POOLED_STRATEGIES = ("dense", "hybrid+ce")


def build_pool(
    home_programme: str, host_programme: str, max_home: int, depth: int = POOL_DEPTH
) -> list[dict[str, str]]:
    """One row per (home course, host course) pair worth a human's attention."""
    from app.core.config import get_settings
    from app.ingest.loader import CurriculumStore
    from app.matching.embedder import programme_documents
    from app.matching.pipeline import PipelineMatcher

    settings = get_settings()
    store = CurriculumStore(settings.curricula_dir)
    matcher = PipelineMatcher(store, settings)

    homes = store.get_courses(home_programme)[:max_home]
    host_documents = dict(
        zip(
            [c.course_uid for c in store.get_courses(host_programme)],
            programme_documents(store, host_programme),
            strict=True,
        )
    )
    home_documents = dict(
        zip(
            [c.course_uid for c in homes],
            programme_documents(store, home_programme)[:max_home],
            strict=True,
        )
    )

    rows: list[dict[str, str]] = []
    for home in homes:
        pooled: dict[str, list[str]] = {}
        for strategy in POOLED_STRATEGIES:
            for rank, candidate in enumerate(
                matcher.match_course(home.course_uid, host_programme, strategy, depth),
                start=1,
            ):
                pooled.setdefault(candidate.host_course.course_uid, []).append(
                    f"{strategy}#{rank}"
                )
        for host_uid, found_by in pooled.items():
            host = store.get_course(host_uid)
            rows.append({
                "home_uid": home.course_uid,
                "host_uid": host_uid,
                "home_title": home.title,
                "host_title": host.title,
                "home_ects": f"{home.ects:g}",
                "host_ects": f"{host.ects:g}",
                "found_by": " ".join(found_by),
                "home_text": home_documents[home.course_uid],
                "host_text": host_documents[host_uid],
            })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--home-programme", default="uns-pmf-informatics-bsc")
    parser.add_argument("--host-programme", required=True)
    parser.add_argument("--max-home", type=int, default=40)
    parser.add_argument("--depth", type=int, default=POOL_DEPTH)
    args = parser.parse_args()

    rows = build_pool(
        args.home_programme, args.host_programme, args.max_home, args.depth
    )
    if not rows:
        print("the pool is empty: check the programme ids", file=sys.stderr)
        return 1

    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    POOL_DIR.mkdir(parents=True, exist_ok=True)
    pool_path = POOL_DIR / f"pool.{args.host_programme}.csv"
    with pool_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    if PRELABELS.exists():
        print(f"{PRELABELS.name} exists and is frozen; not touching it", file=sys.stderr)
    else:
        with PRELABELS.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=["home_uid", "host_uid", "llm_label", "llm_reason"]
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    "home_uid": row["home_uid"],
                    "host_uid": row["host_uid"],
                    "llm_label": "",
                    "llm_reason": "",
                })

    homes = len({row["home_uid"] for row in rows})
    print(f"pooled {len(rows)} pairs over {homes} home courses "
          f"({len(rows) / homes:.1f} per course), depth {args.depth}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
