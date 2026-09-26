"""Evaluate every host on the silver set, a model-labelled breadth check.

    python eval/run_silver.py

The silver set (`eval/make_silver_pool.py`, labels in `data/silver/silver_labels.csv`)
covers all six host programmes with the same 20 stratified home courses, pooled to depth
5 from all five configurations, and labelled blind by a model (Claude). No human checked
it. It answers "does the ranking hold up beyond Twente?", and the report says how far to
trust it by comparing its labels with the gold set where both exist.

Because every configuration is fully judged down to rank 5, only @5 metrics are
reported: Recall@5, P@1, MRR@5, nDCG@5. Imports the same `app.matching` code the API
serves, like `run_eval.py`.

Writes eval/report/silver.md and eval/report/silver.csv.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "eval"))

SILVER = REPO_ROOT / "data" / "silver" / "silver_labels.csv"
STRATA = REPO_ROOT / "data" / "silver" / "home_strata.csv"
GOLD = REPO_ROOT / "data" / "gold" / "gold_pairs.csv"
DEPTH = 5
NO_MATCH_BELOW = 20  # the UI's "no suitable match" floor, frontend/src/lib/score.ts

METRICS5 = ["Recall@5", "P@1", "MRR@5", "nDCG@5"]


def read_silver(path: Path = SILVER) -> dict[str, dict[str, dict[str, int]]]:
    """host programme -> home_uid -> {host_uid: label}."""
    silver: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(dict))
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            silver[row["host_programme"]][row["home_uid"]][row["host_uid"]] = int(row["label"])
    return {host: dict(homes) for host, homes in silver.items()}


def metric_values(ranked: list[str], labels: dict[str, int]) -> dict[str, float]:
    from run_eval import ndcg_at_k, precision_at_1, recall_at_k, reciprocal_rank

    relevant = {uid for uid, label in labels.items() if label >= 1}
    return {
        "Recall@5": recall_at_k(ranked, relevant, DEPTH),
        "P@1": precision_at_1(ranked, relevant),
        "MRR@5": reciprocal_rank(ranked, relevant, DEPTH),
        "nDCG@5": ndcg_at_k(ranked, labels, DEPTH),
    }


def agreement_with_gold(silver: dict, gold_path: Path = GOLD) -> dict[str, tuple]:
    """Silver against gold on the pairs both label, split by who made the gold label."""
    from kappa import cohen_kappa
    from provenance import model_pairs

    silver_labels = {(home, host_uid): label
                     for homes in silver.values()
                     for home, labels in homes.items()
                     for host_uid, label in labels.items()}
    model = model_pairs()
    groups: dict[str, list[tuple[int, int]]] = defaultdict(list)
    with gold_path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (row["home_uid"], row["host_uid"])
            if row.get("checked") != "yes" or key not in silver_labels:
                continue
            pair = (silver_labels[key], int(row["label"]))
            groups["all gold rows"].append(pair)
            groups["gold rows checked by a human" if key not in model
                   else "gold rows labelled by Claude"].append(pair)
    result = {}
    for name, pairs in groups.items():
        a, b = [x for x, _ in pairs], [y for _, y in pairs]
        same = sum(x == y for x, y in pairs)
        result[name] = (len(pairs), same / len(pairs), cohen_kappa(a, b, weighted=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="eval/report")
    args = parser.parse_args()

    from app.core.config import Settings
    from app.ingest.loader import CurriculumStore
    from app.matching.pipeline import PipelineMatcher
    from run_eval import BASELINE, CONFIG_SETUP, CONFIGS, bootstrap_ci, paired_bootstrap_p

    silver = read_silver()
    matchers = {}
    for bi_encoder in sorted({encoder for encoder, _ in CONFIG_SETUP.values()}):
        settings = Settings(bi_encoder=bi_encoder)
        matchers[bi_encoder] = PipelineMatcher(CurriculumStore(settings.curricula_dir),
                                               settings)
    store = next(iter(matchers.values())).store
    hosts = [p.programme_id for p in store.list_programmes() if p.programme_id in silver]

    # config -> list of per-query metric dicts, in one fixed (host, home) order
    per_query: dict[str, list[dict[str, float]]] = {c: [] for c in CONFIGS}
    per_host: dict[tuple[str, str], list[dict[str, float]]] = defaultdict(list)
    queries: list[tuple[str, str]] = []
    declines = {"no relevant course, declined": 0, "no relevant course, answered": 0,
                "relevant course exists, declined": 0,
                "relevant course exists, answered": 0}
    for host in hosts:
        for home, labels in sorted(silver[host].items()):
            has_relevant = any(label >= 1 for label in labels.values())
            best = max((c.score_pct for c in matchers["bge-small"].match_course(
                home, host, "hybrid", DEPTH)), default=0)
            declined = best < NO_MATCH_BELOW
            key = ("relevant course exists" if has_relevant else "no relevant course")
            declines[f"{key}, {'declined' if declined else 'answered'}"] += 1
            if not has_relevant:
                continue
            queries.append((host, home))
            for config in CONFIGS:
                bi_encoder, strategy = CONFIG_SETUP[config]
                ranked = [c.host_course.course_uid for c in matchers[bi_encoder].match_course(
                    home, host, strategy, DEPTH)]
                values = metric_values(ranked, labels)
                per_query[config].append(values)
                per_host[(config, host)].append(values)

    rows = []
    for config in CONFIGS:
        row: dict[str, object] = {"config": config, "host": "all", "queries": len(queries)}
        for name in METRICS5:
            values = [q[name] for q in per_query[config]]
            low, high = bootstrap_ci(values)
            row[name] = round(sum(values) / max(len(values), 1), 4)
            row[f"{name}_ci_low"], row[f"{name}_ci_high"] = round(low, 4), round(high, 4)
        rows.append(row)
    for host in hosts:
        for config in CONFIGS:
            values = per_host[(config, host)]
            row = {"config": config, "host": host, "queries": len(values)}
            for name in METRICS5:
                row[name] = round(sum(v[name] for v in values) / max(len(values), 1), 4)
            rows.append(row)

    out = REPO_ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    fields = ["config", "host", "queries"] + [
        f for name in METRICS5 for f in (name, f"{name}_ci_low", f"{name}_ci_high")]
    with (out / "silver.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({f: row.get(f, "") for f in fields} for row in rows)

    strata: dict[str, str] = {}
    with STRATA.open(encoding="utf-8") as handle:
        strata = {r["home_uid"]: r["stratum"] for r in csv.DictReader(handle)}
    sampled = sorted({home for homes in silver.values() for home in homes})
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for home, stratum in strata.items():
        counts[stratum][0] += 1
        counts[stratum][1] += int(home in sampled)
    pairs = sum(len(labels) for homes in silver.values() for labels in homes.values())

    lines = [
        "# Silver set: every host, model-judged",
        "",
        f"Generated by `eval/run_silver.py` on {datetime.now(UTC):%Y-%m-%d}. **The labels "
        "are a model's (Claude, blind to the system's rankings), not a human's.** This is "
        "a breadth check across all six hosts; the headline numbers are the Twente gold "
        "set in `results.md`.",
        "",
        f"{len(sampled)} home courses, stratified by subject type, against {len(hosts)} host "
        f"programmes: {pairs} pairs, pooled from the top 5 of all five configurations, so "
        f"every configuration is fully judged to rank 5. {len(queries)} (home, host) "
        "queries have at least one relevant course; the rest have none and are counted in "
        "the no-match table instead.",
        "",
        "## All hosts together",
        "",
        "| Config | " + " | ".join(METRICS5) + " |",
        "|---" * (len(METRICS5) + 1) + "|",
    ]
    for row in rows[: len(CONFIGS)]:
        cells = [f"{row[n]:.3f} [{row[f'{n}_ci_low']:.3f}, {row[f'{n}_ci_high']:.3f}]"
                 for n in METRICS5]
        lines.append(f"| `{row['config']}` | " + " | ".join(cells) + " |")
    lines += ["", "Paired bootstrap against the naive baseline, all queries:", ""]
    for treatment in ("hybrid", "hybrid+ce"):
        for name in ("Recall@5", "P@1"):
            t = [q[name] for q in per_query[treatment]]
            b = [q[name] for q in per_query[BASELINE]]
            gain = (sum(t) - sum(b)) / max(len(t), 1)
            p = paired_bootstrap_p(t, b)
            verdict = "significant at 0.05" if p < 0.05 else "not significant"
            lines.append(f"- `{treatment}` vs `{BASELINE}`, {name}: {gain:+.3f}, "
                         f"p = {p:.3f}, {verdict}.")
    lines += ["", "## Per host, Recall@5 / P@1", "",
              "| Host | Queries | " + " | ".join(f"`{c}`" for c in CONFIGS) + " |",
              "|---|---" + "|---" * len(CONFIGS) + "|"]
    for host in hosts:
        n = len(per_host[(CONFIGS[0], host)])
        cells = []
        for config in CONFIGS:
            values = per_host[(config, host)]
            r5 = sum(v["Recall@5"] for v in values) / max(len(values), 1)
            p1 = sum(v["P@1"] for v in values) / max(len(values), 1)
            cells.append(f"{r5:.2f} / {p1:.2f}")
        lines.append(f"| {host} | {n} | " + " | ".join(cells) + " |")

    lines += ["", "## The \"no suitable match\" floor", "",
              f"With `hybrid`, the UI declines to suggest a course when the most probable of "
              f"the five candidates is under {NO_MATCH_BELOW} %. Over every (home, host) "
              "pair of the silver set:", "",
              "| | Declined | Answered |", "|---|---|---|"]
    for key in ("no relevant course", "relevant course exists"):
        lines.append(f"| {key} | {declines[key + ', declined']} | "
                     f"{declines[key + ', answered']} |")

    lines += ["", "## How far to trust these labels", "",
              "Silver labels against the gold set, on the Twente pairs both contain:", "",
              "| Gold rows | Pairs | Raw agreement | Weighted kappa |", "|---|---|---|---|"]
    for name, (n, raw, kappa) in agreement_with_gold(silver).items():
        lines.append(f"| {name} | {n} | {raw:.2f} | {kappa:.2f} |")
    lines += ["", "## Sample", "", "| Subject type | In the programme | Sampled |",
              "|---|---|---|"]
    for stratum in sorted(counts):
        total, taken = counts[stratum]
        lines.append(f"| {stratum} | {total} | {taken} |")
    lines.append("")
    (out / "silver.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out}/silver.md for {len(queries)} queries over {len(hosts)} hosts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
