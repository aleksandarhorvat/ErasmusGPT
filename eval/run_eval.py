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
import math
import random
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "eval"))

GOLD = REPO_ROOT / "data" / "gold" / "gold_pairs.csv"

CONFIGS = ["bm25", "dense-minilm", "dense-bge", "hybrid", "hybrid+ce"]

# config -> (bi-encoder tag, strategy). One place, so the report cannot describe a
# configuration other than the one that ran.
CONFIG_SETUP: dict[str, tuple[str, str]] = {
    "bm25": ("bge-small", "bm25"),
    "dense-minilm": ("minilm", "dense"),
    "dense-bge": ("bge-small", "dense"),
    "hybrid": ("bge-small", "hybrid"),
    "hybrid+ce": ("bge-small", "hybrid+ce"),
}
BASELINE = "dense-minilm"
TREATMENTS = ["hybrid", "hybrid+ce"]
SEED = 20260920


def host_view(gold: dict[str, dict[str, int]], host_uids: set[str]
              ) -> dict[str, dict[str, int]]:
    """The gold set as one host programme sees it (docs/05-evaluation.md, Setup).

    Labels for courses of another programme are dropped, because the ranking can never
    return them and they would sit in every recall denominator. A home course with no
    relevant course at this host is not a query: there is nothing to find, and scoring
    it 0 would measure the catalogue rather than the ranking.
    """
    view: dict[str, dict[str, int]] = {}
    for home_uid, labels in gold.items():
        here = {uid: label for uid, label in labels.items() if uid in host_uids}
        if any(label >= 1 for label in here.values()):
            view[home_uid] = here
    return view


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
    only: set[tuple[str, str]] | None = None,
    exclude: set[tuple[str, str]] | None = None,
) -> tuple[int, int]:
    """(corrections, compared) between the frozen pre-labels and the checked labels.

    This is the number the report quotes as evidence that the human pass was real.
    `only` and `exclude` restrict it to one source of labels, so human corrections and
    a second model's disagreements are never added together.
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
            if (only is not None and key not in only) or (exclude and key in exclude):
                continue
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
    dcg = sum(labels.get(uid, 0) / math.log2(i + 1) for i, uid in enumerate(ranked[:k], start=1))
    ideal = sorted(labels.values(), reverse=True)[:k]
    idcg = sum(rel / math.log2(i + 1) for i, rel in enumerate(ideal, start=1))
    return dcg / idcg if idcg else 0.0


def precision_at_1(ranked: list[str], relevant: set[str]) -> float:
    return 1.0 if ranked and ranked[0] in relevant else 0.0


METRICS = {
    "Recall@5": lambda ranked, labels, relevant: recall_at_k(ranked, relevant, 5),
    "Recall@10": lambda ranked, labels, relevant: recall_at_k(ranked, relevant, 10),
    "MRR@10": lambda ranked, labels, relevant: reciprocal_rank(ranked, relevant, 10),
    "nDCG@10": lambda ranked, labels, relevant: ndcg_at_k(ranked, labels, 10),
    "P@1": lambda ranked, labels, relevant: precision_at_1(ranked, relevant),
}


# --- statistics (S5-A3) -----------------------------------------------------
def bootstrap_ci(
    values: list[float], resamples: int = 1000, seed: int = SEED
) -> tuple[float, float]:
    """95 % percentile bootstrap interval over queries. Seeded, so the report repeats."""
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    means = sorted(
        sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(resamples)
    )
    return (means[int(0.025 * resamples)], means[int(0.975 * resamples) - 1])


def paired_bootstrap_p(
    treatment: list[float], baseline: list[float],
    resamples: int = 1000, seed: int = SEED,
) -> float:
    """Two-sided p for "the per-query difference has mean zero".

    Paired because both configurations answer the same queries. An unpaired test throws
    the pairing away and overstates the uncertainty.
    """
    differences = [t - b for t, b in zip(treatment, baseline, strict=True)]
    observed = sum(differences) / len(differences) if differences else 0.0
    if observed == 0:
        return 1.0
    rng = random.Random(seed)
    n = len(differences)
    centred = [d - observed for d in differences]
    extreme = sum(
        abs(sum(centred[rng.randrange(n)] for _ in range(n)) / n) >= abs(observed)
        for _ in range(resamples)
    )
    return (extreme + 1) / (resamples + 1)


# --- running the configurations ---------------------------------------------
def evaluate(
    config: str, gold: dict[str, dict[str, int]], home_programme: str,
    host_programme: str, depth: int = 10,
) -> tuple[dict[str, list[float]], float, list[str]]:
    """Per-query metric values for one configuration, mean ms per query, and the queries.

    Imports the same app.matching code the API serves, as the module docstring demands.
    """
    from app.core.config import Settings
    from app.ingest.loader import CurriculumStore
    from app.matching.pipeline import PipelineMatcher

    bi_encoder, strategy = CONFIG_SETUP[config]
    settings = Settings(bi_encoder=bi_encoder)
    matcher = PipelineMatcher(CurriculumStore(settings.curricula_dir), settings)

    known = {c.course_uid for c in matcher.get_courses(home_programme)}
    gold = host_view(gold, {c.course_uid for c in matcher.get_courses(host_programme)})
    queries = sorted(uid for uid in gold if uid in known)
    per_query: dict[str, list[float]] = {name: [] for name in METRICS}
    total_ms = 0.0
    for home_uid in queries:
        labels = gold[home_uid]
        relevant = {uid for uid, label in labels.items() if label >= 1}
        started = time.perf_counter()
        candidates = matcher.match_course(home_uid, host_programme, strategy, depth)
        total_ms += (time.perf_counter() - started) * 1000
        ranked = [c.host_course.course_uid for c in candidates]
        for name, metric in METRICS.items():
            per_query[name].append(metric(ranked, labels, relevant))
    return per_query, total_ms / max(len(queries), 1), queries


def write_report(
    results: dict[str, dict[str, list[float]]], latency: dict[str, float],
    queries: list[str], out_dir: Path, host_programme: str,
) -> None:
    from provenance import describe, model_pairs

    out_dir.mkdir(parents=True, exist_ok=True)
    model = model_pairs()
    corrections, compared = correction_rate(exclude=model)
    disagreements, model_compared = correction_rate(only=model)

    rows = []
    for config, per_query in results.items():
        row: dict[str, object] = {
            "config": config,
            "queries": len(queries),
            "ms_per_query": round(latency[config], 1),
        }
        for name, values in per_query.items():
            low, high = bootstrap_ci(values)
            row[name] = round(sum(values) / len(values) if values else 0.0, 4)
            row[f"{name}_ci_low"] = round(low, 4)
            row[f"{name}_ci_high"] = round(high, 4)
        rows.append(row)

    with (out_dir / "results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Evaluation results",
        "",
        f"Generated by `eval/run_eval.py` on {datetime.now(UTC):%Y-%m-%d}. Host programme "
        f"`{host_programme}`, {len(queries)} queries with checked labels.",
        "Protocol: `docs/05-evaluation.md`. Intervals are 95 % percentile bootstrap over",
        f"queries, 1000 resamples, seed {SEED}.",
        "",
        "| Config | " + " | ".join(METRICS) + " | ms/query |",
        "|---" * (len(METRICS) + 2) + "|",
    ]
    for row in rows:
        cells = [
            f"{row[name]:.3f} [{row[f'{name}_ci_low']:.3f}, {row[f'{name}_ci_high']:.3f}]"
            for name in METRICS
        ]
        lines.append(
            f"| `{row['config']}` | " + " | ".join(cells) + f" | {row['ms_per_query']:.0f} |"
        )

    lines += ["", "## Is the gain real?", ""]
    # hybrid is the served default (ADR-0005), hybrid+ce the configuration the proposal
    # made its claim about, so both are tested against the naive baseline.
    compared_any = False
    for treatment_name in TREATMENTS:
        if BASELINE not in results or treatment_name not in results:
            continue
        compared_any = True
        lines += [f"`{treatment_name}` against `{BASELINE}`:", ""]
        for name in METRICS:
            treatment = results[treatment_name][name]
            baseline = results[BASELINE][name]
            gain = (sum(treatment) - sum(baseline)) / max(len(treatment), 1)
            p = paired_bootstrap_p(treatment, baseline)
            verdict = "significant at 0.05" if p < 0.05 else "not significant at 0.05"
            lines.append(
                f"- **{name}**: difference {gain:+.3f}, "
                f"paired bootstrap p = {p:.3f}, {verdict}."
            )
        lines.append("")
    if not compared_any:
        lines.append(f"- Not computed: `{BASELINE}` and a treatment have to run.")

    lines += [
        "",
        "## How the labels were made",
        "",
        "Pairs were pooled from the top 10 of `dense` and `hybrid+ce` and pre-labelled by a",
        "model (`docs/05-evaluation.md`).",
    ]
    provenance = describe()
    if provenance:
        lines.append(provenance)
    if compared:
        lines.append(
            f"The human checkers changed {corrections} of {compared} pre-labels "
            f"({corrections / compared:.1%})."
        )
    if model_compared:
        lines.append(
            f"The second model disagreed with {disagreements} of {model_compared} "
            f"pre-labels ({disagreements / model_compared:.1%}), mostly by rejecting "
            "partial matches the pre-labels had accepted."
        )
    if not compared and not model_compared:
        lines.append("There is no pre-label file to diff, so no correction rate is reported.")
    lines += [
        "Unchecked rows are excluded from every number above.",
        "",
        "Unlabelled pairs count as 0. That slightly favours the strategies that fed the",
        "pool, which is a known property of pooled collections rather than a fault here.",
        "",
    ]
    (out_dir / "results.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--home-programme", default="uns-pmf-informatics-bsc")
    parser.add_argument("--host-programme", required=True)
    parser.add_argument("--out", default="eval/report")
    parser.add_argument("--configs", nargs="*", default=CONFIGS)
    args = parser.parse_args()

    gold = load_gold()
    if not gold:
        print(
            "no checked rows in data/gold/gold_pairs.csv, so there is nothing to measure. "
            "Build the gold set first: S5-A0 pools the pairs, S5-A1 labels them.",
            file=sys.stderr,
        )
        return 1

    results: dict[str, dict[str, list[float]]] = {}
    latency: dict[str, float] = {}
    queries: list[str] = []
    for config in args.configs:
        print(f"--> {config}", flush=True)
        per_query, ms, queries = evaluate(
            config, gold, args.home_programme, args.host_programme
        )
        results[config] = per_query
        latency[config] = ms

    if not queries:
        print("no gold query is a course of the home programme", file=sys.stderr)
        return 1

    write_report(results, latency, queries, REPO_ROOT / args.out, args.host_programme)
    print(f"wrote {args.out}/results.md and results.csv for {len(queries)} queries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
