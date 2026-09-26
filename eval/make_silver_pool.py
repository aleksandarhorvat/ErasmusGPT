"""Pool the pairs of the silver set: every host, the same stratified home courses.

    python eval/make_silver_pool.py [--n 20] [--seed 20260926] [--packets DIR]

The gold set (`data/gold/`) covers Twente only, because it was built when Twente was
the only host. The silver set covers every host programme with the same design, at no
human cost: the labels come from a model (Claude) working blind, and every report built
on it says so. It measures breadth, and it is checked against the gold set where the
two overlap (Twente), so its reliability is a number rather than an assumption.

Design, chosen so the sample is representative and the metrics are fair:
- Home courses: `--n` of the 50, stratified by subject type
  (`data/silver/home_strata.csv`, eight strata), proportional allocation by largest
  remainder, random within a stratum with a fixed seed. The same courses against every
  host, so hosts are comparable.
- Pool: for each (home course, host) the union of the top 5 of all five evaluated
  configurations, `dense-minilm` included. Every configuration is therefore fully
  judged down to rank 5, and the @5 metrics have no unjudged pairs at all.

Writes `data/silver/silver_pool.csv`. With `--packets`, also writes one labelling
packet per host with candidates in a fixed order unrelated to any ranking, and without
scores, ranks or the names of the strategies that proposed them.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "eval"))

STRATA = REPO_ROOT / "data" / "silver" / "home_strata.csv"
POOL = REPO_ROOT / "data" / "silver" / "silver_pool.csv"
HOME = "uns-pmf-informatics-bsc"
DEPTH = 5


def stratified_sample(strata: dict[str, list[str]], n: int, seed: int) -> list[str]:
    """n items, allocated to strata in proportion to their size (largest remainder).

    Deterministic for a given seed. Every stratum whose exact share rounds to at least
    one item gets one; within a stratum the choice is random.
    """
    total = sum(len(items) for items in strata.values())
    exact = {name: n * len(items) / total for name, items in strata.items()}
    counts = {name: int(share) for name, share in exact.items()}
    by_remainder = sorted(exact, key=lambda name: (-(exact[name] - counts[name]), name))
    for name in by_remainder[: n - sum(counts.values())]:
        counts[name] += 1
    rng = random.Random(seed)
    chosen: list[str] = []
    for name in sorted(strata):
        chosen += sorted(rng.sample(sorted(strata[name]), min(counts[name],
                                                             len(strata[name]))))
    return chosen


def read_strata(path: Path = STRATA) -> dict[str, list[str]]:
    strata: dict[str, list[str]] = defaultdict(list)
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            strata[row["stratum"]].append(row["home_uid"])
    return dict(strata)


def packet_order(home_uid: str, host_uid: str) -> str:
    """A stable order that carries no information about any ranking."""
    return hashlib.sha256(f"{home_uid}|{host_uid}".encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260926)
    parser.add_argument("--packets", type=Path)
    args = parser.parse_args()

    from app.core.config import Settings
    from app.ingest.loader import CurriculumStore
    from app.matching.pipeline import PipelineMatcher
    from run_eval import CONFIG_SETUP

    homes = stratified_sample(read_strata(), args.n, args.seed)
    matchers: dict[str, PipelineMatcher] = {}
    for bi_encoder in sorted({encoder for encoder, _ in CONFIG_SETUP.values()}):
        settings = Settings(bi_encoder=bi_encoder)
        matchers[bi_encoder] = PipelineMatcher(CurriculumStore(settings.curricula_dir),
                                               settings)
    store = next(iter(matchers.values())).store
    hosts = [p.programme_id for p in store.list_programmes() if p.programme_id != HOME]

    pool: dict[tuple[str, str], str] = {}
    for host in hosts:
        for home in homes:
            for bi_encoder, strategy in CONFIG_SETUP.values():
                for candidate in matchers[bi_encoder].match_course(home, host, strategy,
                                                                   DEPTH):
                    pool[(home, candidate.host_course.course_uid)] = host
    POOL.parent.mkdir(parents=True, exist_ok=True)
    with POOL.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["home_uid", "host_uid", "host_programme"])
        for (home, host_uid), host in sorted(pool.items(), key=lambda kv: (kv[1], kv[0])):
            writer.writerow([home, host_uid, host])
    per_host = defaultdict(int)
    for host in pool.values():
        per_host[host] += 1
    print(f"{len(homes)} home courses x {len(hosts)} hosts -> {len(pool)} pairs "
          f"-> {POOL.relative_to(REPO_ROOT)}")
    for host in hosts:
        print(f"  {host}: {per_host[host]}")

    if args.packets:
        write_packets(args.packets, pool, store, hosts)
    return 0


def write_packets(directory: Path, pool: dict[tuple[str, str], str], store,
                  hosts: list[str]) -> None:
    """One text packet per host: each home course with its candidates, no rankings."""
    directory.mkdir(parents=True, exist_ok=True)
    raw = {}
    for programme in store.list_programmes():
        data = store.get_programme(programme.programme_id).raw
        for course in data["courses"]:
            raw[f"{data['institution_id']}:{course['code']}"] = (data["programme_name"],
                                                                 course)

    def document(uid: str, limit: int) -> str:
        programme, course = raw[uid]
        text = (f"[{uid}] {course['title']} ({programme}, {course.get('ects')} ECTS)\n"
                f"{(course.get('description') or '')[:limit]}")
        outcomes = course.get("learning_outcomes") or []
        if outcomes:
            text += "\nOutcomes: " + " | ".join(outcomes)[:700]
        return text

    for host in hosts:
        by_home: dict[str, list[str]] = defaultdict(list)
        for (home, host_uid), owner in pool.items():
            if owner == host:
                by_home[home].append(host_uid)
        lines: list[str] = []
        for home in sorted(by_home):
            lines.append("=" * 70)
            lines.append("HOME COURSE (University of Novi Sad, BSc Informatics):")
            lines.append(document(home, 2500))
            lines.append("CANDIDATE HOST COURSES:")
            for host_uid in sorted(by_home[home], key=lambda uid: packet_order(home, uid)):
                lines.append("---")
                lines.append(document(host_uid, 1800))
        (directory / f"{host}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (directory / "manifest.json").write_text(json.dumps(
        {host: sum(1 for owner in pool.values() if owner == host) for host in hosts},
        indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
