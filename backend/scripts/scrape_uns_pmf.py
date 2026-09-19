"""Scrape UNS PMF BSc Informatics into data/curricula/uns-pmf-informatics-bsc.json.

The programme page lists every course in three HTML tables (module Computer Science,
module Information Technologies, electives). Each row links to a one-page English
syllabus PDF, which carries the objectives, outcomes and syllabus text. The PDFs are
cached under data/.cache/uns-pmf-pdf/ so a re-run only re-parses.

    pip install -r backend/scripts/requirements-scrape.txt
    python backend/scripts/scrape_uns_pmf.py            # fetch what is missing, write JSON
    python backend/scripts/scrape_uns_pmf.py --offline  # parse the cache only

Output follows docs/03-data-schema.md. Exits non-zero if a course ends up with an empty
description, because that is the S1-A1 acceptance criterion.
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
from pypdf import PdfReader

REPO = Path(__file__).resolve().parents[2]
SOURCE_URL = "https://www.pmf.uns.ac.rs/en/studies/study-programs/informatics/"
OUT = REPO / "data" / "curricula" / "uns-pmf-informatics-bsc.json"
CACHE = REPO / "data" / ".cache" / "uns-pmf-pdf"
USER_AGENT = "ErasmusGPT course project (University of Novi Sad student)"

# Tables in page order. Electives have no semester column.
TABLES = ["Computer Science", "Information Technologies", None]

# The page mixes Cyrillic letters into Latin text ("M-02" typed with a Cyrillic M). Left
# in, they make two different course_uids that look identical.
HOMOGLYPHS = str.maketrans(
    "\u0410\u0412\u0421\u0415\u041d\u041a\u041c\u041e\u0420\u0422\u0425"
    "\u0430\u0435\u043e\u0440\u0441\u0445",
    "ABCEHKMOPTXaeopcx",
)

# Section headings as they appear across the PDFs, which were written by different
# people and do not agree on wording.
OBJECTIVES = r"Learning objectives?|Learning Objectives?"
OUTCOMES = r"Learning outcomes?|Learning Outcomes?"
SYLLABUS = r"Syllabus|Syllabi"
STOP = r"Weekly teaching load|Literature|Teaching methodology|Grading"
SUBHEADINGS = re.compile(
    r"^(?:Theoretical (?:instruction|part|lessons)|Practical (?:instruction|part)|Theory"
    r"|Practice|Tutorial)\s*(?::|$)",
    re.MULTILINE,
)
OUTCOME_LABELS = re.compile(r"\b(?:Minimum|Minimal|Expected|Desirable|Desired)\s*[:.]")
CODE = re.compile(r"\b(I\d{3}|M\d?-\d{2})\b")


def clean(text: str) -> str:
    text = text.translate(HOMOGLYPHS)
    return re.sub(r"\s+", " ", text).strip()


def fetch(url: str, session: requests.Session) -> bytes:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    time.sleep(1)  # one request per second, per docs/01-universities.md
    return response.content


def parse_tables(html: str) -> list[dict]:
    """One dict per table row that links a syllabus, in page order, duplicates kept."""
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    for table, module in zip(soup.find_all("table"), TABLES, strict=False):
        for tr in table.find_all("tr"):
            link = tr.find("a", href=re.compile(r"\.pdf$"))
            if link is None:
                continue
            cells = [clean(td.get_text(" ")) for td in tr.find_all(["td", "th"])]
            row = {
                "code": cells[1],
                "title": cells[2],
                "module": module,
                "elective_table": module is None,
                "pdf_url": link["href"],
                "ects": float(cells[-1]),
            }
            if module is not None:
                row["semester"] = int(cells[3])
                row["status"] = cells[5]
            rows.append(row)
    return rows


def section(text: str, heading: str, *, until: str) -> str:
    match = re.search(rf"(?:^|\n)\s*(?:{heading})\s*:?(.*?)(?=\n\s*(?:{until})\b|\Z)", text, re.S)
    return match.group(1) if match else ""


def parse_pdf(path: Path) -> dict:
    # Plain extraction splits fewer words than extraction_mode="layout" on these files
    # (52 vs 165 stray fragments across all 50 PDFs).
    text = "\n".join(page.extract_text() for page in PdfReader(path).pages)
    text = "\n".join(line.strip() for line in text.splitlines())
    text = re.sub(r"(\w)-\n(\w)", r"\1-\2", text)
    any_heading = f"{OBJECTIVES}|{OUTCOMES}|{SYLLABUS}|{STOP}"

    objectives = clean(section(text, OBJECTIVES, until=any_heading))
    syllabus = clean(SUBHEADINGS.sub(" ", section(text, SYLLABUS, until=STOP)))
    outcomes_raw = section(text, OUTCOMES, until=any_heading)
    outcomes = [clean(o) for o in OUTCOME_LABELS.split(outcomes_raw) if clean(o)]

    requirements = clean(section(text, r"Requirements", until=any_heading)).split(".")[0]
    return {
        "objectives": objectives,
        "syllabus": syllabus,
        "outcomes": outcomes,
        "requirements": requirements,
    }


def build_courses(rows: list[dict], pdfs: dict[str, dict]) -> list[dict]:
    by_code: dict[str, list[dict]] = {}
    for row in rows:
        by_code.setdefault(row["code"], []).append(row)

    titles = {code: occurrences[0]["title"] for code, occurrences in by_code.items()}
    courses = []
    for code, occurrences in by_code.items():
        in_modules = [r for r in occurrences if not r["elective_table"]]
        first = in_modules[0] if in_modules else occurrences[0]
        semester = first.get("semester")
        modules = {r["module"] for r in in_modules}
        pdf = pdfs[code]

        # C = compulsory for the programme, CM = compulsory for its module.
        mandatory = any(r["status"] in {"C", "CM"} for r in in_modules)

        required = CODE.findall(pdf["requirements"])
        for other, title in titles.items():
            if other != code and title.lower() in pdf["requirements"].lower():
                required.append(other)

        courses.append({
            "code": code,
            "title": first["title"],
            "ects": first["ects"],
            "year": (semester + 1) // 2 if semester else None,
            "semester": semester,
            "mandatory": mandatory,
            "module": modules.pop() if len(modules) == 1 else None,
            "language": "en",
            "description": " ".join(p for p in (pdf["objectives"], pdf["syllabus"]) if p),
            "learning_outcomes": pdf["outcomes"],
            "topics": [],
            "prerequisites": sorted(set(c for c in required if c in titles and c != code)),
            "url": first["pdf_url"],
        })
    return courses


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="use cached files only")
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    page = CACHE / "programme.html"
    if not args.offline:
        page.write_bytes(fetch(SOURCE_URL, session))
    rows = parse_tables(page.read_text(encoding="utf-8"))

    pdfs: dict[str, dict] = {}
    for row in rows:
        if row["code"] in pdfs:
            continue
        path = CACHE / row["pdf_url"].rsplit("/", 1)[1]
        if not path.exists():
            if args.offline:
                print(f"missing from cache: {path.name}", file=sys.stderr)
                return 1
            path.write_bytes(fetch(row["pdf_url"], session))
        pdfs[row["code"]] = parse_pdf(path)

    courses = build_courses(rows, pdfs)
    programme = {
        "programme_id": "uns-pmf-informatics-bsc",
        "institution_id": "uns-pmf",
        "institution_name": "University of Novi Sad, Faculty of Sciences",
        "country": "RS",
        "programme_name": "BSc Informatics",
        "level": "bachelor",
        "language": "en",
        "total_ects": 180,
        "academic_year": "2026/2027",
        "source_url": SOURCE_URL,
        "scraped_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "courses": courses,
    }
    OUT.write_text(json.dumps(programme, indent=2) + "\n", encoding="utf-8")

    empty = [c["code"] for c in courses if not c["description"]]
    print(f"wrote {len(courses)} courses to {OUT.relative_to(REPO)}")
    if empty:
        print(f"empty description: {', '.join(empty)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
