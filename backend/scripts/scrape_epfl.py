"""Scrape an EPFL study plan into data/curricula/. Stage 6, task S6-A1.

edu.epfl.ch renders on the server and publishes an English coursebook page per course,
with Summary, Content, Keywords and Learning Outcomes as separate sections. That maps
onto docs/03-data-schema.md almost one to one, which is why EPFL is the cheapest
catalogue to ingest of the ones in docs/01-universities.md.

    pip install -r backend/scripts/requirements-scrape.txt
    python backend/scripts/scrape_epfl.py                  # MSc Computer Science
    python backend/scripts/scrape_epfl.py --offline        # parse the cache only

Level note: EPFL's computer science BSc is taught in French, so only the MSc is usable
here. It is the deliberate level-mismatch case in the error analysis (S6-A2): a master's
catalogue should produce lower and more uncertain matches against a bachelor's
programme, and the system reporting that honestly is itself a result.
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
from bs4 import BeautifulSoup, Tag

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "data" / ".cache" / "epfl"
BASE = "https://edu.epfl.ch"
HEADERS = {"User-Agent": "ErasmusGPT course project (University of Novi Sad student)"}

# Sections of a coursebook page, by their English heading.
SUMMARY = "Summary"
CONTENT = "Content"
KEYWORDS = "Keywords"
OUTCOMES = "Learning Outcomes"
REQUIRED = "Required courses"

COURSE_CODE = re.compile(r"\b[A-Z]{2,7}-[0-9]{3}[A-Za-z]?\b")
# The page header reads "CS-433 / 8 credits".
CODE_AND_CREDITS = re.compile(
    r"([A-Z]{2,7}-[0-9]{3}[A-Za-z]?)\s*/\s*([0-9]+(?:\.[0-9]+)?)\s*credit"
)


def fetch(url: str, path: Path, session: requests.Session, offline: bool) -> str:
    if not path.exists():
        if offline:
            raise FileNotFoundError(path)
        response = session.get(url, timeout=30)
        response.raise_for_status()
        path.write_text(response.text, encoding="utf-8")
        time.sleep(1)  # one request per second, per docs/01-universities.md
    return path.read_text(encoding="utf-8")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def section(soup: BeautifulSoup, heading: str) -> Tag | None:
    for tag in soup.find_all(["h2", "h3", "h4"]):
        if clean(tag.get_text()) == heading:
            return tag
    return None


def section_text(soup: BeautifulSoup, heading: str) -> str:
    tag = section(soup, heading)
    return clean(tag.find_next_sibling().get_text(" ")) if tag and tag.find_next_sibling() else ""


def section_items(soup: BeautifulSoup, heading: str) -> list[str]:
    """List items under a heading, or the whole paragraph as one item."""
    tag = section(soup, heading)
    if tag is None:
        return []
    sibling = tag.find_next_sibling()
    if sibling is None:
        return []
    items = [clean(li.get_text(" ")) for li in sibling.find_all("li")]
    items = [item for item in items if item]
    if items:
        return items
    text = clean(sibling.get_text(" "))
    return [text] if text else []


def parse_course(html: str, url: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("h1")
    header = CODE_AND_CREDITS.search(clean(soup.get_text(" ")))
    if title_tag is None or header is None:
        return None

    summary = section_text(soup, SUMMARY)
    content = section_text(soup, CONTENT)
    keywords = section_text(soup, KEYWORDS)
    required = " ".join(section_items(soup, REQUIRED))
    return {
        "code": header.group(1),
        "title": clean(title_tag.get_text()),
        "ects": float(header.group(2)),
        "year": None,      # a master's plan lists semesters, not study years
        "semester": None,
        "mandatory": False,  # the MSc is almost entirely elective
        "module": None,
        "language": "en",
        "description": " ".join(part for part in (summary, content) if part),
        "learning_outcomes": section_items(soup, OUTCOMES),
        "topics": [clean(k) for k in keywords.split(",") if clean(k)],
        "prerequisites": sorted(set(COURSE_CODE.findall(required))),
        "url": url,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan", default="/studyplan/en/master/computer-science/")
    parser.add_argument("--programme-id", default="epfl-cs-msc")
    parser.add_argument("--programme-name", default="MSc Computer Science")
    parser.add_argument("--total-ects", type=int, default=120)
    parser.add_argument("--offline", action="store_true", help="use cached files only")
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)

    plan_html = fetch(BASE + args.plan, CACHE / f"{args.programme_id}.html", session,
                      args.offline)
    hrefs = sorted({
        a["href"] for a in BeautifulSoup(plan_html, "html.parser").find_all("a", href=True)
        if "/coursebook/" in a["href"]
    })

    courses: list[dict] = []
    seen: set[str] = set()
    for href in hrefs:
        slug = href.rstrip("/").rsplit("/", 1)[-1]
        url = href if href.startswith("http") else BASE + href
        try:
            html = fetch(url, CACHE / f"{slug}.html", session, args.offline)
        except FileNotFoundError:
            print(f"missing from cache: {slug}", file=sys.stderr)
            return 1
        course = parse_course(html, url)
        if course is None:
            print(f"no code or credits on {slug}, skipped", file=sys.stderr)
            continue
        if course["code"] in seen:
            continue
        if course["ects"] <= 0:
            # Placeholder entries such as a 0-credit research project slot.
            print(f"{course['code']} has no credits, skipped", file=sys.stderr)
            continue
        seen.add(course["code"])
        courses.append(course)

    programme = {
        "programme_id": args.programme_id,
        "institution_id": "epfl",
        "institution_name": "Ecole Polytechnique Federale de Lausanne",
        "country": "CH",
        "programme_name": args.programme_name,
        "level": "master",
        "language": "en",
        "total_ects": args.total_ects,
        "academic_year": "2026/2027",
        "source_url": BASE + args.plan,
        "scraped_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "courses": sorted(courses, key=lambda c: c["code"]),
    }
    out = REPO / "data" / "curricula" / f"{args.programme_id}.json"
    out.write_text(json.dumps(programme, indent=2) + "\n", encoding="utf-8")

    empty = [c["code"] for c in courses if not c["description"]]
    print(f"wrote {len(courses)} courses to {out.relative_to(REPO)}")
    if empty:
        print(f"empty description: {', '.join(empty)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
