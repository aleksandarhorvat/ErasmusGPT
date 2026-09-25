"""Scrape Politecnico di Milano BSc Engineering of Computing Systems into data/curricula/.

The programme is the Laurea in Ingegneria Informatica (code 531, Milano Leonardo).
Polimi has no English-taught bachelor in computer engineering: the official language of
531 is Italian and only a handful of third-year courses are taught in English. The
English "Manifesto degli studi" on onlineservices.polimi.it still publishes an English
course description for every course, which is what the matching pipeline needs.

Sources, all server-rendered HTML:
- the manifesto of track IT1 (years 1 and 2, shared with telecommunications) and track
  I3I "Informatica" (year 3), which gives code, title, CFU, year, semester, the teaching
  language flag and the elective groups;
- one detail page per course, which carries the English "Course Description";
- the lecturer's syllabus ("scheda incarico"), which carries the expected learning
  outcomes. Lecturers of Italian-taught courses write it in Italian, so outcomes are
  kept only when the text is English.

robots.txt asks for a five second crawl delay. Raw pages are cached under
data/.cache/polimi/ so a re-run only re-parses.

    pip install -r backend/scripts/requirements-scrape.txt
    python backend/scripts/scrape_polimi.py            # fetch what is missing, write JSON
    python backend/scripts/scrape_polimi.py --offline  # parse the cache only

Scope: the Milano Leonardo computer science path in one academic year: years 1-2 from
track IT1 and year 3 from track I3I, including the elective groups those tracks list.
Final examinations and internships are left out. The Cremona, online and
telecommunications tracks are not scraped. Integrated courses keep the manifesto
description only, because their syllabi are split per module. `mandatory` follows the
manifesto literally: a course in a block where students choose between alternatives is
not mandatory, even when the computer science path always picks it.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from bs4 import BeautifulSoup, Tag

REPO = Path(__file__).resolve().parents[2]
CURRICULA = REPO / "data" / "curricula"
CACHE = REPO / "data" / ".cache" / "polimi"
BASE = "https://onlineservices.polimi.it"
MANIFESTO = f"{BASE}/manifesti/manifesti/controller/ManifestoPublic.do"
SYLLABUS = f"{BASE}/schedaincarico/schedaincarico/controller/scheda_pubblica/SchedaPublic.do"
HEADERS = {"User-Agent": "ErasmusGPT course project (University of Novi Sad student)"}
CRAWL_DELAY = 5  # seconds, from onlineservices.polimi.it/robots.txt

SCHOOL = "225"  # School of Industrial and Information Engineering
PROGRAMME = "531"  # Engineering of Computing Systems, ordinamento D.M. 96/23
# In September 2026 the 2026/2027 manifesto was out, but its syllabi still answered
# "Teaching assignment is not yet available", so 2025/2026 is the last complete year.
ACADEMIC_YEAR = 2025
# Track -> programme years taken from it. IT1 also prints a year 3 section, which only
# links to the year 3 tracks.
TRACKS = {"IT1": (1, 2), "I3I": (3,)}
KEEP_TYPES = {"M", "I"}  # mono-disciplinary and integrated; V is the final exam, T internship

YEAR_HEADER = re.compile(r"^(\d)(st|nd|rd) Year$")
GROUP_ANCHOR = re.compile(r"#idGruppo(\d+)")
GROUP_NAME = re.compile(r"Group\s+(\S+)")
# Dublin descriptor headings ("DdD1. Knowledge and understanding", "Making judgements
# (DD3)") label a list of outcomes and are not outcomes themselves. Some lecturers also
# repeat the section title inside the box, or mark a descriptor "(not applicable)".
DUBLIN_HEADING = re.compile(
    r"^(DdD\s*\d.*|Dublin Descriptor.*|\(not applicable\)"
    r"|(Expected learning outcomes|Knowledge and understanding"
    r"|Applying knowledge and understanding|Making judge?ments|Communication( skills)?"
    r"|(Lifelong )?learning skills)\s*(\((DD\s*)?\d\))?:?)$",
    re.IGNORECASE,
)
ENGLISH_WORDS = {"the", "of", "and", "to", "is", "are", "for", "with", "on", "be", "this"}
ITALIAN_WORDS = {"il", "di", "e", "della", "delle", "dei", "del", "per", "che", "con", "la",
                 "le", "gli", "un", "una", "sono", "degli", "alla", "nel"}


def fetch(session: requests.Session | None, url: str, path: Path) -> str:
    """The cached page when there is one, otherwise fetch and cache it."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    if session is None:
        raise FileNotFoundError(path)
    response = session.get(url, timeout=60)
    response.raise_for_status()
    time.sleep(CRAWL_DELAY)
    path.write_text(response.text, encoding="utf-8")
    return response.text


def manifesto_url(track: str) -> str:
    query = {"EVN_DEFAULT": "evento", "lang": "EN", "aa": ACADEMIC_YEAR, "k_cf": SCHOOL,
             "k_corso_la": PROGRAMME, "k_indir": track}
    return f"{MANIFESTO}?{urlencode(query)}"


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def is_english(text: str) -> bool:
    words = re.findall(r"[a-z]+", text.lower())
    english = sum(word in ENGLISH_WORDS for word in words)
    italian = sum(word in ITALIAN_WORDS for word in words)
    return english > italian


def _cells(row: Tag) -> list[Tag]:
    # Cells 1% wide draw the brackets for "teachings in sequence" and shift the columns.
    return [td for td in row.find_all("td", recursive=False) if td.get("width") != "1%"]


def _float(text: str) -> float | None:
    """The leading number of a CFU cell.

    Credits taught with innovative methods follow in brackets, as in "10.0 [1.0]".
    """
    match = re.match(r"\d+(\.\d+)?", text)
    return float(match.group()) if match else None


def parse_manifesto(page: str, track: str) -> list[dict]:
    """Course rows of one track, in page order, with year, group and mandatory flag."""
    soup = BeautifulSoup(page, "html.parser")
    rows: list[dict] = []
    group_year: dict[str, int] = {}
    group_name: dict[str, str] = {}
    year: int | None = None
    in_group_table = False
    block: list[dict] = []  # rows sharing one "CFU Group" cell
    block_total: float | None = None
    block_left = 0

    def close_block() -> None:
        # A block whose courses add up to more than its credit total is a choice
        # between alternatives; otherwise every course in it is required.
        concrete = sum(r["ects"] for r in block)
        for r in block:
            r["mandatory"] = block_total is not None and concrete <= block_total + 1e-9
        block.clear()

    for node in soup.find_all(["td", "tr"]):
        if node.name == "td" and "TitleInfoCard" in (node.get("class") or []):
            title = clean(node.get_text(" "))
            match = YEAR_HEADER.match(title)
            if match:
                year, in_group_table = int(match.group(1)), False
            elif title.startswith("Courses of the Group"):
                in_group_table = True
            continue
        if node.name != "tr":
            continue
        cells = _cells(node)
        anchor = node.find("a", href=GROUP_ANCHOR)
        link = node.find("a", href=re.compile("EVN_DETTAGLIO_RIGA_MANIFESTO"),
                         string=re.compile(r"\S"))
        target = anchor or link
        # Layout tables wrap the whole page, so only a row that owns the link counts.
        if target is None or target.find_parent("tr") is not node:
            continue
        title_index = cells.index(target.find_parent("td"))
        after = cells[title_index + 1:]
        if not in_group_table and len(after) >= 6:
            if block_left:
                close_block()
            block_total = _float(clean(after[5].get_text()))
            block_left = int(after[5].get("rowspan", 1))
        if anchor:
            group_id = GROUP_ANCHOR.search(anchor["href"]).group(1)
            group_year[group_id] = year
            name = GROUP_NAME.search(anchor.get_text(" "))
            group_name[group_id] = name.group(1) if name else group_id
        else:
            query = parse_qs(urlparse(html.unescape(link["href"])).query)
            group_id = query.get("idGruppo", [None])[0]
            flags = [img["src"] for img in node.find_all("img") if "flag_collection" in img["src"]]
            row = {
                "code": clean(cells[0].get_text()),
                "title": clean(link.get_text(" ")),
                "type": clean(after[2].get_text()),
                "half": int(query["semestre"][0]) if query.get("semestre") else None,
                "ects": _float(clean(after[4].get_text())) or 0.0,
                "year": int(query["anno_corso"][0]) if query.get("anno_corso")
                else group_year.get(group_id, year),
                "group": group_name.get(group_id) if group_id else None,
                "language": "en" if any("gb.png" in f for f in flags) else "it",
                "detail": link["href"],
                "mandatory": False,
                "track": track,
            }
            rows.append(row)
            if not in_group_table and block_left:
                block.append(row)
        if not in_group_table and block_left:
            block_left -= 1
            if block_left == 0:
                close_block()
    if block:
        close_block()
    return rows


def section_after(soup: BeautifulSoup, heading: str) -> Tag | None:
    """The box that follows a TitleInfoCard heading on a detail or syllabus page."""
    for td in soup.find_all("td", class_="TitleInfoCard"):
        if clean(td.get_text()) == heading:
            return td.find_next("table")
    return None


def parse_detail(page: str) -> tuple[str, list[str]]:
    """English course description and the syllabus ids (c_classe) of its sections."""
    soup = BeautifulSoup(page, "html.parser")
    description = ""
    label = soup.find(string=re.compile(r"^\s*Course Description\s*$"))
    if label:
        cell = label.find_parent("td").find_next_sibling("td")
        if cell:
            description = clean(cell.get_text(" "))
    classes = []
    for a in soup.find_all("a", href=re.compile(r"c_classe=\d+")):
        c_classe = re.search(r"c_classe=(\d+)", a["href"]).group(1)
        if c_classe not in classes:
            classes.append(c_classe)
    return description, classes


def parse_syllabus(page: str) -> tuple[str, list[str]]:
    """Goals text and expected learning outcomes of one syllabus, as published."""
    soup = BeautifulSoup(page, "html.parser")
    goals = section_after(soup, "Goals")
    outcomes = section_after(soup, "Expected learning outcomes")
    items: list[str] = []
    if outcomes:
        items = [clean(li.get_text(" ")) for li in outcomes.find_all("li")]
        if not items:
            items = [clean(p.get_text(" ")) for p in outcomes.find_all("p")]
        if not items:
            items = [clean(outcomes.get_text(" "))]
        items = [i for i in items if i and not DUBLIN_HEADING.match(i)]
    return (clean(goals.get_text(" ")) if goals else ""), items


def build_course(row: dict, description: str, outcomes: list[str]) -> dict:
    return {
        "code": row["code"],
        "title": row["title"],
        "ects": row["ects"],
        "year": row["year"],
        "semester": (row["year"] - 1) * 2 + row["half"] if row["year"] and row["half"] else None,
        "mandatory": row["mandatory"],
        "module": None,
        "language": row["language"],
        "description": description,
        "learning_outcomes": outcomes,
        "topics": [],
        "prerequisites": [],
        "url": BASE + re.sub(r";jsessionid=[^?]*", "", html.unescape(row["detail"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="use cached files only")
    parser.add_argument("--programme-id", default="polimi-ecs-bsc")
    parser.add_argument("--programme-name", default="BSc Engineering of Computing Systems")
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    session = None
    if not args.offline:
        session = requests.Session()
        session.headers.update(HEADERS)

    try:
        rows: list[dict] = []
        seen: set[str] = set()
        for track, years in TRACKS.items():
            page = fetch(session, manifesto_url(track),
                         CACHE / f"manifesto.{ACADEMIC_YEAR}.{track}.html")
            for row in parse_manifesto(page, track):
                # IT1 lists a course once per year; I3I repeats year 2 courses in a
                # catch-up group for year 3. The first listing is the regular one.
                if row["year"] in years and row["type"] in KEEP_TYPES and row["code"] not in seen:
                    seen.add(row["code"])
                    rows.append(row)

        courses = []
        dropped = []
        for row in rows:
            detail = fetch(session, BASE + html.unescape(row["detail"]),
                           CACHE / f"detail.{ACADEMIC_YEAR}.{row['track']}.{row['code']}.html")
            description, classes = parse_detail(detail)
            goals, outcomes = "", []
            if row["type"] == "M" and classes:
                syllabus = fetch(session, f"{SYLLABUS}?evn_default=evento&c_classe={classes[0]}"
                                 "&lang=EN", CACHE / f"syllabus.{classes[0]}.html")
                goals, outcomes = parse_syllabus(syllabus)
            if not is_english(" ".join(outcomes)):
                outcomes = []
            if not (description and is_english(description)):
                description = goals if goals and is_english(goals) else ""
            if not description:
                dropped.append(row["code"])
                continue
            courses.append(build_course(row, description, outcomes))
    except FileNotFoundError as exc:
        print(f"missing from cache: {exc}", file=sys.stderr)
        return 1

    programme = {
        "programme_id": args.programme_id,
        "institution_id": "polimi",
        "institution_name": "Politecnico di Milano",
        "country": "IT",
        "programme_name": args.programme_name,
        "level": "bachelor",
        # The language of the stored text, as for uns-pmf-informatics-bsc. The teaching
        # language is Italian and each course records its own.
        "language": "en",
        "total_ects": 180,
        "academic_year": f"{ACADEMIC_YEAR}/{ACADEMIC_YEAR + 1}",
        "source_url": manifesto_url("IT1"),
        "scraped_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "courses": courses,
    }
    out = CURRICULA / f"{args.programme_id}.json"
    out.write_text(json.dumps(programme, indent=2) + "\n", encoding="utf-8")

    with_outcomes = sum(1 for c in courses if c["learning_outcomes"])
    print(f"wrote {len(courses)} courses to {out.relative_to(REPO)}, "
          f"{with_outcomes} with English learning outcomes")
    if dropped:
        print(f"no English description, left out: {', '.join(dropped)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
