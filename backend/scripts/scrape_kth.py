"""Scrape a KTH programme into data/curricula/. Stage 6, task S6-A1.

KTH course pages are server-rendered and published in English at
`kth.se/student/kurser/kurs/<CODE>?l=en`, with "Course contents" and "Intended learning
outcomes" as their own sections. The programme syllabus page that lists the codes is a
JavaScript app, and the KOPPS API answered 502 for a whole day, so the code list is kept
as a small committed file instead:

    data/curricula/kth-cs-msc.codes.txt   one course code per line, comments with #

Refresh it by opening the programme syllabus in a browser and reading the codes out of
the page; it changes about once a year and the file records where it came from.

    pip install -r backend/scripts/requirements-scrape.txt
    python backend/scripts/scrape_kth.py                # fetch and write the JSON
    python backend/scripts/scrape_kth.py --offline      # parse the cache only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parents[2]
CURRICULA = REPO / "data" / "curricula"
CACHE = REPO / "data" / ".cache" / "kth"
BASE = "https://www.kth.se/student/kurser/kurs"
HEADERS = {"User-Agent": "ErasmusGPT course project (University of Novi Sad student)"}

CONTENTS = "Course contents"
OUTCOMES = "Intended learning outcomes"
PREREQUISITES = "Specific prerequisites"
# The page title reads "DD2380 Artificial Intelligence 6.0 credits".
TITLE = re.compile(r"^([A-Z]{2}\d{4})\s+(.*?)\s+([\d.]+)\s+credits", re.S)
COURSE_CODE = re.compile(r"\b[A-Z]{2}\d{4}\b")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fetch(code: str, session: requests.Session, offline: bool) -> str:
    path = CACHE / f"{code}.html"
    if not path.exists():
        if offline:
            raise FileNotFoundError(path)
        response = session.get(f"{BASE}/{code}?l=en", timeout=30)
        response.raise_for_status()
        path.write_text(response.text, encoding="utf-8")
        time.sleep(1)  # one request per second, per docs/01-universities.md
    return path.read_text(encoding="utf-8")


def section(soup: BeautifulSoup, heading: str) -> str:
    for tag in soup.find_all(["h2", "h3", "h4"]):
        if clean(tag.get_text()) == heading:
            sibling = tag.find_next_sibling()
            return clean(sibling.get_text(" ")) if sibling else ""
    return ""


def section_items(soup: BeautifulSoup, heading: str) -> list[str]:
    for tag in soup.find_all(["h2", "h3", "h4"]):
        if clean(tag.get_text()) != heading:
            continue
        sibling = tag.find_next_sibling()
        if sibling is None:
            return []
        items = [clean(li.get_text(" ")) for li in sibling.find_all("li")]
        items = [item for item in items if item]
        if items:
            return items
        text = clean(sibling.get_text(" "))
        return [text] if text else []
    return []


def parse_course(html: str, code: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1")
    match = TITLE.match(clean(heading.get_text(" "))) if heading else None
    if match is None:
        return None

    prerequisites = section(soup, PREREQUISITES)
    return {
        "code": match.group(1),
        "title": clean(match.group(2)),
        "ects": float(match.group(3)),
        "year": None,      # a master's syllabus lists periods, not study years
        "semester": None,
        "mandatory": False,
        "module": None,
        "language": "en",
        "description": section(soup, CONTENTS),
        "learning_outcomes": section_items(soup, OUTCOMES),
        "topics": [],
        "prerequisites": sorted(set(COURSE_CODE.findall(prerequisites)) - {code}),
        "url": f"{BASE}/{code}?l=en",
    }


def read_codes(path: Path) -> list[str]:
    codes = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            codes.append(line)
    return codes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--programme-id", default="kth-cs-msc")
    parser.add_argument("--programme-name", default="MSc Computer Science")
    parser.add_argument("--total-ects", type=int, default=120)
    parser.add_argument("--offline", action="store_true", help="use cached files only")
    args = parser.parse_args()

    codes_path = CURRICULA / f"{args.programme_id}.codes.txt"
    if not codes_path.exists():
        print(f"no code list at {codes_path.relative_to(REPO)}", file=sys.stderr)
        return 1

    CACHE.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)

    courses = []
    for code in read_codes(codes_path):
        try:
            html = fetch(code, session, args.offline)
        except FileNotFoundError:
            print(f"missing from cache: {code}", file=sys.stderr)
            return 1
        except requests.HTTPError as exc:
            print(f"{code}: {exc}", file=sys.stderr)
            continue
        course = parse_course(html, code)
        if course is None:
            print(f"{code}: no title line, skipped", file=sys.stderr)
            continue
        if not course["description"]:
            # Swedish-taught courses publish the syllabus in Swedish only, and an
            # English-only pipeline cannot use them (ADR-0001).
            print(f"{code}: no English course contents, skipped", file=sys.stderr)
            continue
        courses.append(course)

    programme = {
        "programme_id": args.programme_id,
        "institution_id": "kth",
        "institution_name": "KTH Royal Institute of Technology",
        "country": "SE",
        "programme_name": args.programme_name,
        "level": "master",
        "language": "en",
        "total_ects": args.total_ects,
        "academic_year": "2025/2026",
        "source_url": f"{BASE}/",
        "scraped_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "courses": sorted(courses, key=lambda c: c["code"]),
    }
    out = CURRICULA / f"{args.programme_id}.json"
    out.write_text(json.dumps(programme, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(courses)} courses to {out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
