"""Turn raw strategy scores into probabilities. Stage 6, task S6-A4.

A cross-encoder score is not a probability. Platt scaling fits one logistic curve,
p = sigmoid(a * score + b), from the gold labels, so that "70 %" means roughly seven in
ten such pairs were labelled 1 or 2 by a human. Without it, the number in the UI cannot
be summed, and `S6-A5` (expected recognised ECTS) has nothing to add up.

    python eval/fit_calibration.py --host-programme utwente-tcs-bsc

Writes data/calibration/<strategy>.json, which the pipeline loads at startup. Prefers
human-checked rows; falls back to the frozen pre-labels and says so in the file, because
a calibration fitted on machine labels must never be mistaken for one fitted on human
judgement.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

GOLD = REPO_ROOT / "data" / "gold" / "gold_pairs.csv"
PRELABELS = REPO_ROOT / "data" / "gold" / "llm_prelabels.csv"
OUT_DIR = REPO_ROOT / "data" / "calibration"


def load_labels(path: Path = GOLD, prelabels: Path = PRELABELS) -> tuple[dict, str]:
    """{(home, host): 0|1|2} and where it came from. Checked rows win."""
    checked: dict[tuple[str, str], int] = {}
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row.get("checked", "").strip().lower() == "yes":
                    checked[(row["home_uid"], row["host_uid"])] = int(row["label"])
    if checked:
        return checked, "human-checked gold_pairs.csv"

    machine: dict[tuple[str, str], int] = {}
    if prelabels.exists():
        with prelabels.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row.get("llm_label", "").strip():
                    machine[(row["home_uid"], row["host_uid"])] = int(row["llm_label"])
    return machine, "PROVISIONAL: llm_prelabels.csv, no human pass yet"


def sigmoid(x: float) -> float:
    if x < -700:  # exp overflows below this and the answer is 0 either way
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def fit_platt(scores: list[float], positives: list[int], steps: int = 2000,
              learning_rate: float = 0.5) -> tuple[float, float]:
    """Logistic regression on one feature, by gradient descent. Returns (a, b).

    Hand-rolled rather than pulling in scikit-learn: one feature, a few hundred points,
    and no new dependency in a project that ships its dependencies in an image.
    """
    a, b = 1.0, 0.0
    n = len(scores)
    if n == 0:
        return a, b
    for _ in range(steps):
        grad_a = grad_b = 0.0
        for score, positive in zip(scores, positives, strict=True):
            error = sigmoid(a * score + b) - positive
            grad_a += error * score
            grad_b += error
        a -= learning_rate * grad_a / n
        b -= learning_rate * grad_b / n
    return a, b


def reliability(scores: list[float], positives: list[int], a: float, b: float,
                bins: int = 5) -> list[dict]:
    """Predicted against observed rate per bin: the evidence that the fit is honest."""
    table = []
    for index in range(bins):
        low, high = index / bins, (index + 1) / bins
        chosen = [
            (score, positive) for score, positive in zip(scores, positives, strict=True)
            if low <= sigmoid(a * score + b) < high or (index == bins - 1 and
                                                        sigmoid(a * score + b) == 1.0)
        ]
        if not chosen:
            continue
        table.append({
            "bin": f"{low:.1f}-{high:.1f}",
            "pairs": len(chosen),
            "predicted": round(sum(sigmoid(a * s + b) for s, _ in chosen) / len(chosen), 3),
            "observed": round(sum(p for _, p in chosen) / len(chosen), 3),
        })
    return table


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--home-programme", default="uns-pmf-informatics-bsc")
    parser.add_argument("--host-programme", required=True)
    parser.add_argument("--strategy", default="hybrid+ce")
    parser.add_argument("--positive-label", type=int, default=1,
                        help="lowest label counted as a match (1 keeps partials)")
    args = parser.parse_args()

    from app.core.config import get_settings
    from app.ingest.loader import CurriculumStore
    from app.matching.pipeline import PipelineMatcher

    labels, source = load_labels()
    if not labels:
        print("no labels at all: run eval/make_pool.py first", file=sys.stderr)
        return 1

    settings = get_settings()
    matcher = PipelineMatcher(CurriculumStore(settings.curricula_dir), settings)
    homes = {uid for uid, _ in labels}

    scores: list[float] = []
    positives: list[int] = []
    for home_uid in sorted(homes):
        depth = len(matcher.get_courses(args.host_programme))
        for candidate in matcher.match_course(home_uid, args.host_programme,
                                              args.strategy, depth):
            key = (home_uid, candidate.host_course.course_uid)
            if key in labels:
                scores.append(candidate.score)
                positives.append(int(labels[key] >= args.positive_label))

    a, b = fit_platt(scores, positives)
    table = reliability(scores, positives, a, b)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{args.strategy.replace('+', '-')}.json"
    out.write_text(json.dumps({
        "strategy": args.strategy,
        "a": round(a, 6),
        "b": round(b, 6),
        "pairs": len(scores),
        "positives": sum(positives),
        "positive_label": args.positive_label,
        "label_source": source,
        "host_programme": args.host_programme,
        "fitted_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reliability": table,
    }, indent=2) + "\n", encoding="utf-8")

    print(f"fitted on {len(scores)} pairs ({sum(positives)} positive) from {source}")
    print(f"  p = sigmoid({a:.3f} * score + {b:.3f}) -> {out.relative_to(REPO_ROOT)}")
    for row in table:
        print(f"  {row['bin']}: {row['pairs']:4d} pairs, predicted {row['predicted']:.2f},"
              f" observed {row['observed']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
