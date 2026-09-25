"""Scrape TU Delft BSc Computer Science and Engineering into data/curricula/.

The TU Delft study guide (studiegids.tudelft.nl) is a Nuxt app over a JSON API at
curriculum.tudelft.nl/publisher. One search lists the programme's courses with their
description and learning objectives inline, a second lists the programme parts (study
years, second-year variants, third-year electives) that the courses hang under. TU Delft
also runs Osiris, but its course records there carry a placeholder instead of content.
The search endpoint answers with a redirect unless `Accept: application/json` is sent.
Raw responses are cached under data/.cache/tudelft/ so a re-run only re-parses.

    pip install -r backend/scripts/requirements-scrape.txt
    python backend/scripts/scrape_tudelft.py            # fetch what is missing, write JSON
    python backend/scripts/scrape_tudelft.py --offline  # parse the cache only

Scope: the courses the study guide places in the programme overview for one academic
year. The third year also holds a 30 EC minor and free electives chosen from other
programmes; the guide does not list them under CSE, so they are missing. Zero-credit
units (first-year mentoring) are left out.
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
CACHE = REPO / "data" / ".cache" / "tudelft"
API = "https://curriculum.tudelft.nl/publisher/api/v0/opleidingen"
GUIDE = "https://studiegids.tudelft.nl"
PROGRAMME_NAME = "BSc Computer Science and Engineering"
PROGRAMME_ID = "tudelft-cse-bsc"
# The newest year in the guide, and complete: in September 2026 every course of all
# three years of 2026-2027 carries a description. The first year was redesigned that
# year (codes CSE11A to CSE14B), so 2025-2026 would give a different year 1.
ACADEMIC_YEAR = "2026-2027"
HEADERS = {"User-Agent": "ErasmusGPT course project (University of Novi Sad student)",
           "Accept": "application/json"}

PART_YEAR = re.compile(r"(\d)(?:st|nd|rd|th) year")
COURSE_CODE = re.compile(r"\bCSE\d{3,4}[A-Z]?\b")


def search(session: requests.Session, kind: str, query: str, filters: dict) -> list[dict]:
    """Every hit of one study-guide search, following the API's 100-item pages."""
    hits: list[dict] = []
    offset = 0
    while True:
        response = session.post(
            f"{API}/items/search",
            params={"size": 100, "offset": offset, "type_canonical_name": kind},
            json={"query": query, "filters": filters, "language": "en"},
            timeout=30,
        )
        response.raise_for_status()
        time.sleep(1)  # one request per second, per docs/01-universities.md
        page = response.json()
        hits += page["data"]
        offset += 100
        if offset >= page["meta"]["total"]:
            return hits


def cached(path: Path, offline: bool, fetch) -> list[dict]:
    if not path.exists():
        if offline:
            raise FileNotFoundError(f"missing from cache: {path.name}")
        path.write_text(json.dumps(fetch()), encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))


def find_programme(hits: list[dict]) -> dict:
    for hit in hits:
        data = hit["attributes"]["data"]
        if data["naam_ned"]["en"] == PROGRAMME_NAME and ACADEMIC_YEAR in data["jaar"]["en"]:
            return data
    raise LookupError(f"{PROGRAMME_NAME} {ACADEMIC_YEAR} not in the study guide")


def english(field: object) -> str:
    """The English side of a {nl, en} field. The guide fills both, often with the same text."""
    if isinstance(field, dict):
        field = field.get("en") or ""
    return field if isinstance(field, str) else ""


def html_to_text(value: str) -> str:
    soup = BeautifulSoup(value, "html.parser")
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def html_to_items(value: str) -> list[str]:
    """List items when the field is an HTML list, else its paragraphs, else the whole text.

    Some courses number their objectives as separate paragraphs instead of a list. A
    list item keeps only its own text, so a nested list is not repeated in its parent.
    """
    soup = BeautifulSoup(value, "html.parser")
    for tag in ("li", "p"):
        items = [
            re.sub(r"\s+", " ", " ".join(
                child.get_text(" ") if child.name else str(child)
                for child in node.children if child.name not in ("ul", "ol")
            )).strip()
            for node in soup.find_all(tag)
        ]
        items = [item for item in items if item]
        if items:
            return items
    text = html_to_text(value)
    return [text] if text else []


def part_years(parts: list[dict]) -> dict[int, tuple[int, str | None]]:
    """{part id: (study year, module name)} for every programme part.

    Year parts carry no module; a part below a year part (a second-year variant, the
    third-year electives) is the module and inherits the year of its parent.
    """
    by_id = {int(p["id"]): p["attributes"]["data"] for p in parts}
    out: dict[int, tuple[int, str | None]] = {}
    for part_id, data in by_id.items():
        match = PART_YEAR.search(data["naam"]["en"])
        if match:
            out[part_id] = (int(match.group(1)), None)
    for part_id, data in by_id.items():
        if part_id in out:
            continue
        for parent in data["programmaonderdelen_ids"]:
            if parent in out:
                out[part_id] = (out[parent][0], data["naam"]["en"].strip())
    return out


def build_course(data: dict, parts: dict[int, tuple[int, str | None]],
                 prerequisites: list[str]) -> dict:
    placed = [parts[p] for p in data["programmaonderdelen_ids"] if p in parts]
    year = placed[0][0] if placed else None
    module = next((m for _, m in placed if m), None)
    # Periods are quartiles: 1 and 2 form the first semester of the year, 3 and 4 the
    # second. A course offered in both halves (the research project) has no one semester.
    halves = {1 if period <= 2 else 2 for period in data.get("periodes") or []}
    semester = (year - 1) * 2 + halves.pop() if year and len(halves) == 1 else None
    languages = data.get("voertaal", {}).get("en") or []
    return {
        "code": data["code"],
        "title": english(data["course_name_2"]).strip(),
        "ects": float(data["studiepunten_ects"]),
        "year": year,
        "semester": semester,
        # Year parts hold the compulsory courses; a variant or the electives part is a choice.
        "mandatory": placed != [] and module is None,
        "module": module,
        "language": "en" if "English" in languages or not languages else "nl",
        "description": html_to_text(english(data.get("vakbeschrijving"))),
        "learning_outcomes": html_to_items(english(data.get("leerdoelen"))),
        "topics": [],
        "prerequisites": prerequisites,
        "url": f"{GUIDE}/courses/study-guide/educations/{data['item_id']}",
    }


def find_prerequisites(courses: list[dict]) -> dict[str, list[str]]:
    """{code: prerequisite codes inside the programme}.

    Three sources: codes named in the prior-knowledge text, the required-course field,
    and the reverse of "gives access to", which is how the guide records that the
    research project needs most of the first two years.
    """
    by_id = {c["item_id"]: c["code"] for c in courses}
    codes = set(by_id.values())
    found: dict[str, set[str]] = {c["code"]: set() for c in courses}

    def linked(field: object) -> list[str]:
        values = field.get("en", []) if isinstance(field, dict) else []
        ids = [int(v.split("|", 1)[0]) for v in values if v.split("|", 1)[0].isdigit()]
        return [by_id[i] for i in ids if i in by_id]

    for course in courses:
        code = course["code"]
        prior = html_to_text(english(course.get("cr_expected_prior_knowledge_nld")))
        found[code] |= set(COURSE_CODE.findall(prior)) & codes
        found[code] |= set(linked(course.get("cr_required_course")))
        for later in linked(course.get("cr_gives_access_to")):
            found[later].add(code)
    return {code: sorted(value - {code}) for code, value in found.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="use cached files only")
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        programme = find_programme(cached(
            CACHE / f"programmes.{ACADEMIC_YEAR}.json", args.offline,
            lambda: search(session, "opleiding", PROGRAMME_NAME,
                           {"jaar": [ACADEMIC_YEAR], "soort_programma": ["Bachelor"]}),
        ))
        pid = str(programme["item_id"])
        overview = {"opleiding_filter": [pid]}
        modules = cached(CACHE / f"modules.{pid}.json", args.offline,
                         lambda: search(session, "modules", "", overview))
        parts = cached(CACHE / f"parts.{pid}.json", args.offline,
                       lambda: search(session, "program_part", "", overview))
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    units = [m["attributes"]["data"] for m in modules]
    units = [u for u in units if float(u["studiepunten_ects"] or 0) > 0]
    prerequisites = find_prerequisites(units)
    years = part_years(parts)
    courses = [build_course(u, years, prerequisites[u["code"]])
               for u in sorted(units, key=lambda u: u["path"])]
    result = {
        "programme_id": PROGRAMME_ID,
        "institution_id": "tudelft",
        "institution_name": "Delft University of Technology",
        "country": "NL",
        "programme_name": PROGRAMME_NAME,
        "level": "bachelor",
        "language": "en",
        "total_ects": 180,
        "academic_year": ACADEMIC_YEAR.replace("-", "/"),
        "source_url": f"{GUIDE}/opleidingen/study-guide/educations/{pid}",
        "scraped_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "courses": courses,
    }
    out = CURRICULA / f"{PROGRAMME_ID}.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    empty = [c["code"] for c in courses if not c["description"]]
    print(f"wrote {len(courses)} courses to {out.relative_to(REPO)}")
    if empty:
        print(f"empty description: {', '.join(empty)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
