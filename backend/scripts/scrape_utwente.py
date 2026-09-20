"""Scrape University of Twente BSc Technical Computer Science into data/curricula/.

Osiris, the Twente catalogue, is a single-page app over a JSON API. The search endpoint
lists every course the programme coordinates; the detail endpoint carries the content
and aims. Both answer HTTP 500 unless the `taal` header is set. Raw responses are cached
under data/.cache/utwente/ so a re-run only re-parses.

    pip install -r backend/scripts/requirements-scrape.txt
    python backend/scripts/scrape_utwente.py            # fetch what is missing, write JSON
    python backend/scripts/scrape_utwente.py --offline  # parse the cache only

Scope: units coordinated by "Bachelor Technical Computer Science" in one academic year.
Osiris does not say which units belong to the programme's curriculum, so units run by
other departments for TCS students (the mathematics lines) are missing.
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
OUT = REPO / "data" / "curricula" / "utwente-tcs-bsc.json"
CACHE = REPO / "data" / ".cache" / "utwente"
API = "https://utwente.osiris-student.nl/student/osiris"
SOURCE_URL = "https://utwente.osiris-student.nl/onderwijscatalogus/extern/cursus"
PROGRAMME = "Bachelor Technical Computer Science"
# The last fully published year. Osiris publishes a year quartile by quartile, and in
# September 2026 the 2026-2027 catalogue still lacked most of year 1.
ACADEMIC_YEAR = "2025-2026"
HEADERS = {"User-Agent": "ErasmusGPT course project (University of Novi Sad student)",
           "taal": "EN"}

CATEGORY_YEAR = re.compile(r"Bachelor year (\d)")
# Blocks are quartiles: 1A and 1B form the first semester of the year, 2A and 2B the second.
BLOCK_HALF = {"1A": 1, "1B": 1, "2A": 2, "2B": 2}
COURSE_CODE = re.compile(r"\b\d{9}\b")
# Superseded units stay in the catalogue for students resitting the old exam.
RESIT_ONLY = re.compile(r"only for (repeat|resit)|retake last year", re.IGNORECASE)


def fetch_list(session: requests.Session) -> list[dict]:
    must = [
        {"terms": {"collegejaar": [ACADEMIC_YEAR]}},
        {"terms": {"coordinerend_onderdeel_oms": [PROGRAMME]}},
    ]
    body = {
        "from": 0,
        "size": 500,
        "sort": [{"cursus": {"order": "asc"}}],
        "post_filter": {"bool": {"must": must}},
        "query": {"bool": {"must": must}},
    }
    response = session.post(f"{API}/student/cursussen/zoeken", json=body, timeout=30)
    response.raise_for_status()
    time.sleep(1)
    return [hit["_source"] for hit in response.json()["hits"]["hits"]]


def fetch_detail(course_id: int, session: requests.Session) -> dict:
    response = session.get(f"{API}/owc/cursussen/{course_id}", timeout=30)
    response.raise_for_status()
    time.sleep(1)  # one request per second, per docs/01-universities.md
    return response.json()


def html_to_text(value: str) -> str:
    soup = BeautifulSoup(value, "html.parser")
    for tag in soup(["style", "title", "head"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def html_to_items(value: str) -> list[str]:
    """List items when the field is an HTML list, otherwise the whole text as one item."""
    soup = BeautifulSoup(value, "html.parser")
    items = [re.sub(r"\s+", " ", li.get_text(" ")).strip() for li in soup.find_all("li")]
    items = [item for item in items if item]
    if items:
        return items
    text = html_to_text(value)
    return [text] if text else []


def detail_fields(detail: dict) -> dict[str, str]:
    """Flatten the detail record to {field id: raw value} for the string-valued fields."""
    fields: dict[str, str] = {}

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("veld"), str) and isinstance(node.get("waarde"), str):
                fields.setdefault(node["veld"], node["waarde"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(detail)
    return fields


def select_units(listing: list[dict]) -> list[dict]:
    """Bachelor study units worth credits."""
    return [
        c for c in listing
        if CATEGORY_YEAR.match(c.get("categorie_omschrijving") or "")
        and float(c["punten"].replace(",", ".")) > 0
    ]


def drop_duplicates(units: list[dict]) -> list[dict]:
    """One unit per title: the earliest study year, then the newest code.

    Osiris lists some units twice, for example Network Systems as a year 1 TCS module
    and again as a year 2 unit for another track. TCS students take it in year 1.
    """
    best: dict[str, dict] = {}
    for unit in units:
        title = unit["cursus_lange_naam"].strip().lower()
        key = (_year(unit), -int(unit["cursus"]))
        if title not in best or key < (_year(best[title]), -int(best[title]["cursus"])):
            best[title] = unit
    return sorted(best.values(), key=lambda c: c["cursus"])


def _year(unit: dict) -> int:
    return int(CATEGORY_YEAR.match(unit["categorie_omschrijving"]).group(1))


def build_course(unit: dict, detail: dict, codes: set[str]) -> dict:
    fields = detail_fields(detail)
    year = _year(unit)
    half = BLOCK_HALF.get(unit["blokken"][0]["blok"]) if unit["blokken"] else None
    languages = {v["voertaal_omschrijving"] for v in unit.get("voertalen", [])}
    previous = html_to_text(fields.get("item-ingang-voorkennis", ""))
    return {
        "code": unit["cursus"],
        "title": unit["cursus_lange_naam"].strip(),
        "ects": float(unit["punten"].replace(",", ".")),
        "year": year,
        "semester": (year - 1) * 2 + half if half else None,
        # Every TCS unit in a given quartile is part of that quartile's compulsory module,
        # apart from the year 2 elective modules, which Osiris does not mark.
        "mandatory": year != 2,
        "module": None,
        "language": "en" if "English" in languages or not languages else "nl",
        "description": html_to_text(fields.get("item-inhoud-3", "")),
        "learning_outcomes": html_to_items(fields.get("item-inhoud-4", "")),
        "topics": [],
        "prerequisites": sorted(set(COURSE_CODE.findall(previous)) & codes - {unit["cursus"]}),
        "url": fields.get("deeplink_detailscherm_extern") or None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="use cached files only")
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)

    listing_path = CACHE / "list.json"
    if not args.offline:
        listing_path.write_text(json.dumps(fetch_list(session), indent=1), encoding="utf-8")
    units = select_units(json.loads(listing_path.read_text(encoding="utf-8")))

    details = {}
    for unit in units:
        path = CACHE / f"{unit['id_cursus']}.json"
        if not path.exists():
            if args.offline:
                print(f"missing from cache: {path.name}", file=sys.stderr)
                return 1
            path.write_text(json.dumps(fetch_detail(unit["id_cursus"], session)),
                            encoding="utf-8")
        details[unit["cursus"]] = json.loads(path.read_text(encoding="utf-8"))

    # Resit-only units go first, so a current unit never loses a title tie to one.
    units = drop_duplicates([
        u for u in units
        if not RESIT_ONLY.search(detail_fields(details[u["cursus"]]).get("item-inhoud-3", ""))
    ])
    codes = {unit["cursus"] for unit in units}
    courses = [build_course(unit, details[unit["cursus"]], codes) for unit in units]
    programme = {
        "programme_id": "utwente-tcs-bsc",
        "institution_id": "utwente",
        "institution_name": "University of Twente",
        "country": "NL",
        "programme_name": "BSc Technical Computer Science",
        "level": "bachelor",
        "language": "en",
        "total_ects": 180,
        "academic_year": ACADEMIC_YEAR.replace("-", "/"),
        "source_url": SOURCE_URL,
        "scraped_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "courses": courses,
    }
    OUT.write_text(json.dumps(programme, indent=2) + "\n", encoding="utf-8")

    empty = [c["code"] for c in courses if not c["description"]]
    print(f"wrote {len(courses)} courses to {OUT.relative_to(REPO)}")
    if empty:
        print(f"empty description: {', '.join(empty)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
