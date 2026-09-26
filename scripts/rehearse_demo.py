"""Walk the live demo against the running stack and time every step. Owner: Person B.
Task S7-AB2.

    docker compose up -d
    python scripts/rehearse_demo.py

or let the script start the stack and time the boot itself:

    python scripts/rehearse_demo.py --start

It goes through nginx on :8080, the same path the browser takes, and runs the steps of
docs/07-demo-script.md: the page loads, the API reports the real matcher with its
models, TU Delft is the host the page opens on, the whole programme matches against it
with `hybrid`, the evidence for Computer networks is there, a pair we know is right comes
out on top, the recognition estimate is calibrated, `hybrid+ce` finishes inside the UI's
timeout, and the evaluation page (measured against Twente) has its reports.

It also tries to reach huggingface.co. For the rehearsal that is supposed to fail: if it
succeeds the network is up, and a demo that works with the network up proves nothing
about the room. Standard library only, so it runs from any Python 3 on the laptop.
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOME = "uns-pmf-informatics-bsc"
HOST = "tudelft-cse-bsc"          # the demo host; Twente is only the evaluation host
KNOWN_PAIR = ("Operating systems 1", "Operating Systems")
EVIDENCE_COURSE = "Computer networks"
FAST_LIMIT_S = 5.0     # hybrid over a whole programme; measured at about 0.1 s
UI_TIMEOUT_S = 150.0   # MATCH_TIMEOUT_MS in frontend/src/lib/api.ts


class Step:
    def __init__(self, name: str) -> None:
        self.name = name
        self.ok = False
        self.detail = ""
        self.seconds = 0.0


def request(url: str, body: dict | None = None, timeout: float = 180.0) -> tuple[int, bytes]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def get_json(url: str, body: dict | None = None, timeout: float = 180.0):
    status, raw = request(url, body, timeout)
    if status != 200:
        raise RuntimeError(f"HTTP {status}: {raw[:200]!r}")
    return json.loads(raw)


def network_is_up() -> bool:
    try:
        with socket.create_connection(("huggingface.co", 443), timeout=3):
            return True
    except OSError:
        return False


def wait_for_health(api: str, limit_s: float) -> tuple[float, dict | None]:
    """Seconds until /health answers with the models loaded, and its last body."""
    started = time.perf_counter()
    last: dict | None = None
    while time.perf_counter() - started < limit_s:
        try:
            last = get_json(f"{api}/health", timeout=5)
            if last.get("models_loaded") or last.get("matcher") == "stub":
                return time.perf_counter() - started, last
        except (OSError, RuntimeError, ValueError):
            pass
        time.sleep(2)
    return time.perf_counter() - started, last


def run(base: str, start: bool, wait_s: float) -> list[Step]:
    api = f"{base}/api/v1"
    steps: list[Step] = []

    def step(name: str):
        current = Step(name)
        steps.append(current)
        return current

    boot = step("stack is up and the models are loaded")
    if start:
        launched = time.perf_counter()
        subprocess.run(["docker", "compose", "up", "-d"], cwd=REPO_ROOT, check=True)
        _, health = wait_for_health(api, wait_s)
        boot.seconds = time.perf_counter() - launched
    else:
        boot.seconds, health = wait_for_health(api, wait_s)
    if health is None:
        boot.detail = f"no answer from {api}/health after {boot.seconds:.0f} s"
        return steps
    boot.ok = health.get("matcher") == "real" and bool(health.get("models_loaded"))
    boot.detail = f"matcher={health.get('matcher')}, models_loaded={health.get('models_loaded')}"
    if health.get("matcher") == "stub":
        boot.detail += ". Set MATCHER_IMPL=real in .env: the stub is not a demo"

    page = step("front end loads at /")
    began = time.perf_counter()
    status, raw = request(f"{base}/", timeout=10)
    page.seconds = time.perf_counter() - began
    page.ok = status == 200 and b'id="root"' in raw
    page.detail = f"HTTP {status}" + ("" if page.ok else ", not the app's index.html")

    programmes_step = step("the page opens on UNS PMF against TU Delft")
    began = time.perf_counter()
    listed = get_json(f"{api}/programmes")
    programmes = {p["programme_id"]: p for p in listed}
    programmes_step.seconds = time.perf_counter() - began
    # Same rule as frontend/src/App.tsx: the first bachelor's host in /programmes order.
    first = next((p["programme_id"] for p in listed
                  if p["programme_id"] != HOME and p.get("level") == "bachelor"), None)
    programmes_step.ok = HOME in programmes and first == HOST
    programmes_step.detail = f"{len(programmes)} programmes, default host {first}"
    if HOME not in programmes or HOST not in programmes:
        return steps
    home = programmes[HOME]

    match = step("match the whole programme with hybrid")
    body = {"home_programme_id": HOME, "host_programme_id": HOST, "strategy": "hybrid",
            "top_k": 5}
    began = time.perf_counter()
    result = get_json(f"{api}/match", body)
    match.seconds = time.perf_counter() - began
    rows = result["results"]
    match.ok = len(rows) == home["course_count"] and match.seconds < FAST_LIMIT_S
    match.detail = f"{len(rows)} of {home['course_count']} courses, took_ms={result['took_ms']}"

    evidence = step(f"evidence is shown for {EVIDENCE_COURSE}")
    row = next((r for r in rows if r["home_course"]["title"] == EVIDENCE_COURSE), None)
    top = row["matches"][0] if row and row["matches"] else None
    evidence.ok = bool(top and top.get("evidence"))
    evidence.detail = (f"top match {top['host_course']['title']!r}" if top
                       else "course or match missing")

    home_title, expected = KNOWN_PAIR
    known = step(f"{home_title} finds {expected} first")
    row = next((r for r in rows if r["home_course"]["title"] == home_title), None)
    titles = [m["host_course"]["title"] for m in row["matches"]] if row else []
    known.ok = expected in titles[:1]
    known.detail = f"{home_title} -> {titles[0] if titles else 'nothing'}"

    recognition = step("recognition estimate on the default strategy")
    body = {"home_programme_id": HOME, "host_programme_id": HOST, "strategy": "hybrid",
            "ects_budget": home.get("total_ects") or 180}
    began = time.perf_counter()
    summary = get_json(f"{api}/recognition", body)
    recognition.seconds = time.perf_counter() - began
    recognition.ok = bool(summary["calibrated"])
    recognition.detail = (
        f"about {summary['expected_recognised_ects']:.0f} of {summary['total_ects']:.0f} "
        f"ECTS, calibrated={summary['calibrated']}, provisional={summary['provisional']}")

    reranked = step("match the whole programme with hybrid+ce")
    body = {"home_programme_id": HOME, "host_programme_id": HOST, "strategy": "hybrid+ce",
            "top_k": 5}
    began = time.perf_counter()
    result = get_json(f"{api}/match", body, timeout=UI_TIMEOUT_S + 60)
    reranked.seconds = time.perf_counter() - began
    reranked.ok = reranked.seconds < UI_TIMEOUT_S
    reranked.detail = f"took_ms={result['took_ms']}, the UI gives up at {UI_TIMEOUT_S:.0f} s"

    evaluation = step("evaluation page has its reports")
    began = time.perf_counter()
    page_body = get_json(f"{api}/evaluation")
    evaluation.seconds = time.perf_counter() - began
    evaluation.ok = bool(page_body["reports"])
    evaluation.detail = (f"{len(page_body['reports'])} reports; gold "
                         f"{page_body.get('gold_human', 0)} human + "
                         f"{page_body.get('gold_model', 0)} model of {page_body['gold_total']}")
    return steps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://localhost:8080",
                        help="where nginx serves the app (default %(default)s)")
    parser.add_argument("--start", action="store_true",
                        help="run docker compose up -d first and time the boot")
    parser.add_argument("--wait", type=float, default=600,
                        help="seconds to wait for the models to load (default %(default)s; "
                             "a cold first boot encodes every course and can take minutes)")
    parser.add_argument("--allow-network", action="store_true",
                        help="do not fail when huggingface.co is reachable")
    args = parser.parse_args()

    online = network_is_up()
    try:
        steps = run(args.base.rstrip("/"), args.start, args.wait)
    except (OSError, RuntimeError, KeyError, ValueError) as error:
        print(f"stopped: {error}")
        return 1

    width = max(len(s.name) for s in steps)
    for s in steps:
        mark = "ok  " if s.ok else "FAIL"
        print(f"{mark} {s.name:<{width}} {s.seconds:7.2f} s  {s.detail}")
    print()
    if online:
        print("network: huggingface.co is REACHABLE, so this was not an offline rehearsal")
    else:
        print("network: huggingface.co unreachable, offline as intended")

    failed = [s for s in steps if not s.ok]
    if online and not args.allow_network:
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
