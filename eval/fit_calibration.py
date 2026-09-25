"""Turn raw strategy scores into probabilities. Stage 6, task S6-A4.

A ranking score is not a probability. Platt scaling fits a logistic curve,
p = sigmoid(a * z(score) + c * z(cosine) + b), from the gold labels, so that "70 %"
means roughly seven in ten such pairs were labelled 1 or 2 by a human.

The cosine is there because the fused scores are rank-based. The top hit of a course
with no equivalent abroad gets the same RRF score as the top hit of a perfect match, so
a score-only fit printed 68 % for Calculus 1 against Software Diamond. Grouped by home
course, 10-fold, on the 2026-09-25 pre-labels, adding the cosine took log loss from
0.273 to 0.219 and AUC from 0.87 to 0.91 for `hybrid`, and the mean top-1 probability
of a wrong match from 0.47 to 0.21. `--score-only` reproduces the old fit. Without it, the number in the UI cannot
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
sys.path.insert(0, str(REPO_ROOT / "eval"))

GOLD = REPO_ROOT / "data" / "gold" / "gold_pairs.csv"
PRELABELS = REPO_ROOT / "data" / "gold" / "llm_prelabels.csv"
OUT_DIR = REPO_ROOT / "data" / "calibration"


def load_labels(path: Path = GOLD, prelabels: Path = PRELABELS) -> tuple[dict, str]:
    """{(home, host): 0|1|2} and where it came from. Checked rows win.

    A partly checked gold set is still provisional: its checked rows cover whichever
    home courses were labelled first, so the source string says PROVISIONAL, which is
    what `app/core/calibration.py` looks for before the UI calls a probability final.
    """
    checked: dict[tuple[str, str], int] = {}
    total = 0
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                total += 1
                if row.get("checked", "").strip().lower() == "yes":
                    checked[(row["home_uid"], row["host_uid"])] = int(row["label"])
    if checked and len(checked) < total:
        return checked, (f"PROVISIONAL: human-checked gold_pairs.csv, {len(checked)} of "
                         f"{total} rows, so only part of the home courses")
    if checked:
        from provenance import model_pairs

        model = len(model_pairs() & set(checked))
        if model:
            # Still PROVISIONAL for app/core/calibration.py: part of the answer key is a
            # model's opinion, so the UI keeps its warning (docs/05-evaluation.md).
            return checked, (f"PROVISIONAL, partly model-labelled: gold_pairs.csv, all "
                             f"{len(checked)} rows: "
                             f"{len(checked) - model} human-checked, {model} labelled by "
                             "a second model (Claude), see data/gold/provenance.json")
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


def standardise(scores: list[float]) -> tuple[float, float]:
    """Mean and standard deviation of the raw scores.

    Strategies produce wildly different ranges: a cross-encoder probability spans 0..1,
    an RRF score sits near 0.02. Fitting a logistic on the raw value makes the gradient
    vanish for the small-range strategies and the curve comes out flat, predicting the
    base rate for every pair. Standardising first removes that.
    """
    n = len(scores)
    if n == 0:
        return 0.0, 1.0
    mean = sum(scores) / n
    variance = sum((s - mean) ** 2 for s in scores) / n
    return mean, math.sqrt(variance) or 1.0


def fit_platt(scores: list[float], positives: list[int], steps: int = 4000,
              learning_rate: float = 0.5) -> tuple[float, float]:
    """Logistic regression on one feature, by gradient descent. Returns (a, b)."""
    weights, b = fit_logistic([[score] for score in scores], positives, steps,
                              learning_rate)
    return weights[0], b


def fit_logistic(rows: list[list[float]], positives: list[int], steps: int = 4000,
                 learning_rate: float = 0.5) -> tuple[list[float], float]:
    """Logistic regression by gradient descent on standardised features.

    Returns (weights, intercept). Hand-rolled rather than pulling in scikit-learn: two
    features, a few hundred points, and no new dependency in a project that ships its
    dependencies in an image.
    """
    n = len(rows)
    width = len(rows[0]) if rows else 1
    weights, b = [1.0] * width, 0.0
    if n == 0:
        return weights, b
    for _ in range(steps):
        grads, grad_b = [0.0] * width, 0.0
        for row, positive in zip(rows, positives, strict=True):
            linear = sum(w * x for w, x in zip(weights, row, strict=True)) + b
            error = sigmoid(linear) - positive
            for index, x in enumerate(row):
                grads[index] += error * x
            grad_b += error
        weights = [w - learning_rate * g / n for w, g in zip(weights, grads, strict=True)]
        b -= learning_rate * grad_b / n
    return weights, b


def reliability(scores: list[float], positives: list[int], a: float, b: float,
                bins: int = 5) -> list[dict]:
    """Predicted against observed rate per bin for a one-feature fit."""
    return reliability_of([sigmoid(a * score + b) for score in scores], positives, bins)


def reliability_of(predicted: list[float], positives: list[int],
                   bins: int = 5) -> list[dict]:
    """Predicted against observed rate per bin: the evidence that the fit is honest."""
    table = []
    for index in range(bins):
        low, high = index / bins, (index + 1) / bins
        chosen = [
            (p, positive) for p, positive in zip(predicted, positives, strict=True)
            if low <= p < high or (index == bins - 1 and p == 1.0)
        ]
        if not chosen:
            continue
        table.append({
            "bin": f"{low:.1f}-{high:.1f}",
            "pairs": len(chosen),
            "predicted": round(sum(p for p, _ in chosen) / len(chosen), 3),
            "observed": round(sum(y for _, y in chosen) / len(chosen), 3),
        })
    return table


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--home-programme", default="uns-pmf-informatics-bsc")
    parser.add_argument("--host-programme", required=True)
    parser.add_argument("--strategy", default="hybrid+ce")
    parser.add_argument("--positive-label", type=int, default=1,
                        help="lowest label counted as a match (1 keeps partials)")
    parser.add_argument("--host-programmes", nargs="*",
                        help="fit over several host programmes; overrides --host-programme")
    parser.add_argument("--score-only", action="store_true",
                        help="fit on the strategy score alone, the pre-2026-09-25 model")
    args = parser.parse_args()
    hosts = args.host_programmes or [args.host_programme]

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
    cosines: list[float] = []
    positives: list[int] = []
    for host in hosts:
        depth = len(matcher.get_courses(host))
        for home_uid in sorted(homes):
            for candidate in matcher.match_course(home_uid, host, args.strategy, depth):
                key = (home_uid, candidate.host_course.course_uid)
                if key in labels:
                    scores.append(candidate.score)
                    cosines.append(matcher.cosine(home_uid, host, key[1]))
                    positives.append(int(labels[key] >= args.positive_label))

    mean, std = standardise(scores)
    cosine_mean, cosine_std = standardise(cosines)
    z_scores = [(score - mean) / std for score in scores]
    z_cosines = [(cosine - cosine_mean) / cosine_std for cosine in cosines]
    if args.score_only:
        rows = [[z] for z in z_scores]
    else:
        rows = [[z, zc] for z, zc in zip(z_scores, z_cosines, strict=True)]
    weights, b = fit_logistic(rows, positives)
    predicted = [sigmoid(sum(w * x for w, x in zip(weights, row, strict=True)) + b)
                 for row in rows]
    table = reliability_of(predicted, positives)
    fitted = {
        "strategy": args.strategy,
        "features": ["score"] if args.score_only else ["score", "cosine"],
        "a": round(weights[0], 6),
        "b": round(b, 6),
        "mean": round(mean, 6),
        "std": round(std, 6),
    }
    if not args.score_only:
        fitted |= {"cosine_coef": round(weights[1], 6),
                   "cosine_mean": round(cosine_mean, 6),
                   "cosine_std": round(cosine_std, 6)}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{args.strategy.replace('+', '-')}.json"
    out.write_text(json.dumps(fitted | {
        "pairs": len(scores),
        "positives": sum(positives),
        "positive_label": args.positive_label,
        "label_source": source,
        "host_programme": ", ".join(hosts),
        "fitted_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reliability": table,
    }, indent=2) + "\n", encoding="utf-8")

    print(f"fitted on {len(scores)} pairs ({sum(positives)} positive) from {source}")
    terms = f"{weights[0]:.3f} * z(score)"
    if not args.score_only:
        terms += f" + {weights[1]:.3f} * z(cosine)"
    print(f"  p = sigmoid({terms} + {b:.3f}) -> {out.relative_to(REPO_ROOT)}")
    for row in table:
        print(f"  {row['bin']}: {row['pairs']:4d} pairs, predicted {row['predicted']:.2f},"
              f" observed {row['observed']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
