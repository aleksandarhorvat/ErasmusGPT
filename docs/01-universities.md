# Partner universities and curriculum sources

Owner: **Person A**

## Selection criteria

A partner programme is only usable for this project if it satisfies all four:

1. **Course descriptions published in English.** UNS PMF publishes its Informatics
   programme in English too, so the whole pipeline stays monolingual - no multilingual
   model, no translation step, no extra failure mode. (ADR-0001)
2. **A public, structured course catalogue** - an HTML page per course with title,
   ECTS, content and learning outcomes. No PDF-only catalogues, no logins.
3. **Comparable level.** UNS PMF Informatics is a 3-year, 180-ECTS **bachelor**.
   Matching a BSc course to an MSc course is a different (harder) task; keep the MVP
   BSc<->BSc and treat the one MSc catalogue below as a deliberate stress test.
4. **Plausible as a real Erasmus+ destination** for a University of Novi Sad student.
   Serbia is an Erasmus+ programme country, so EU/EEA institutions are all in scope.

## Home programme

| | |
|---|---|
| Institution | University of Novi Sad, Faculty of Sciences (PMF), Department of Mathematics and Informatics |
| Programme | BSc Informatics, 180 ECTS, 3 years |
| Modules | *Computer Science* (algorithm analysis, formal and programming languages, intelligent systems) and *Information Technologies* (architecture and networks, databases, operating systems, software engineering, information systems) |
| Structure | 8 compulsory courses (72 ECTS) + 11 module electives (~84 ECTS) + a pool of 33 electives |
| Source | <https://www.pmf.uns.ac.rs/en/studies/study-programs/informatics/> - each course links to a syllabus with lecture/exercise hours and ECTS |
| `institution_id` | `uns-pmf` |

Ingest **both** modules: ~50-60 courses total. That is the left-hand side of every match.

As ingested (S1-A1, September 2026): 50 distinct courses. 19 per module, 8 of them shared
by both, plus 20 electives that appear in no module table. Non-informatics electives
(English, Sociology, Accounting, Finance) are kept, because a student can ask to have them
recognised too. Notes for whoever re-scrapes:

- The per-course syllabi are one-page English PDFs from the 2016 accreditation, not HTML
  pages. `scrape_uns_pmf.py` extracts them with `pypdf`. Some words come out split
  ("databas e"); they are left as extracted, since fixing them needs a dictionary.
- The page types some codes with Cyrillic letters that look Latin (`M-02` with a
  Cyrillic M). The scraper maps them to Latin so each `course_uid` has one spelling.
- Electives have no semester in the source, so their `year` and `semester` are `null`.
- `mandatory` is true for status C (whole programme) and CM (its module). `module` is set
  only for courses that belong to exactly one module.

## Priority order (2026-09-26)

The app lists partners in this order, from `data/partners.json`: ShanghaiRanking ARWU
2026 band first, distance from Novi Sad second.

| # | Institution | ARWU 2026 | km from Novi Sad | In the app |
|---|---|---|---|---|
| 1 | EPFL | 43 | 1035 | MSc Computer Science |
| 2 | TU Delft | 151-200 | 1356 | BSc Computer Science and Engineering |
| 3 | Politecnico di Milano | 201-300 | 828 | BSc Engineering of Computing Systems |
| 4 | KTH | 201-300 | 1570 | MSc Computer Science |
| 5 | University of Twente | 501-600 | 1225 | BSc TCS, BSc Applied Mathematics |

Twente is last, and stays in for one reason: it is the only host with gold labels, so
every measured number in `eval/report/` is against it. It was chosen early because its
catalogue was the easiest to scrape, not because it is a likely destination.

## Recommended partner shortlist (the original plan, kept for the record)

| # | Institution | Programme | Why it is a good test case | Catalogue |
|---|---|---|---|---|
| 1 | **University of Twente** (NL) | BSc Technical Computer Science | Fully English-taught BSc, public Osiris catalogue with long structured descriptions. **Hard case on purpose:** Twente teaches in 10-week "modules" that bundle several subjects, so one home course often maps to *part* of a host module - exactly the ambiguity a cross-encoder should resolve better than cosine similarity. | <https://utwente.osiris-student.nl/onderwijscatalogus/extern/cursus> |
| 2 | **Masaryk University, Faculty of Informatics** (CZ) | BSc Informatics / Programming and Computer Technology | The realistic destination: a very common Erasmus target for Serbian students, curriculum structurally close to PMF's, catalogue fully available in English. Expect high scores here. If this pair scores badly, something is broken. | <https://www.fi.muni.cz/catalogue-current/?lang=en> - <https://www.muni.cz/en/bachelors-and-masters-study-programmes/faculty-of-informatics> |
| 3 | **TU Wien** (AT) | BSc Media Informatics / Software & Information Engineering | Geographically the obvious partner for Novi Sad. TISS publishes English course pages with content and outcomes. Naming conventions differ a lot from PMF's -> good lexical-vs-semantic contrast (BM25 fails, dense wins). | <https://tiss.tuwien.ac.at/curriculum/> |
| 4 | **University of Ljubljana, Faculty of Computer and Information Science (FRI)** (SI) | BSc Computer Science and Informatics | Regional partner, very similar course structure, English descriptions published for exchange students. | <https://fri.uni-lj.si/en/studies> |
| 5 | **Technical University of Denmark (DTU)** (DK) | BEng/BSc Software Technology courses | `kurser.dtu.dk` is the cleanest machine-readable catalogue in Europe: stable URLs, explicit "Learning objectives" and "Content" sections, ECTS on every page. Cheapest to ingest - do this one when you need a fourth programme fast. | <https://www.dtu.dk/english/education/course-base> |
| 6 | **EPFL** (CH) - *stretch / stress test* | MSc Computer Science | Included because it was the original inspiration, but note: the **BSc is largely in French**, only the MSc is reliably English. Use it as the deliberate level-mismatch case in the error analysis (S6-A2): an MSc catalogue *should* produce lower and more uncertain matches, and if the system reports that honestly, that is a result worth writing up. | <https://edu.epfl.ch/studyplan/en/master/computer-science/> |

**Suggestion:** ship M1-M3 with **UNS PMF + Twente + Masaryk**. Three programmes give
you two host catalogues, one easy and one hard, which is enough to show the
cross-encoder's improvement. Add 4-6 during M4 only if ingestion is already automated.

## Ingestion policy

- Scrape once, commit the result as JSON under `data/curricula/`. **Never scrape at
  request time** - the demo must run offline inside Docker.
- One scraper script per institution: `backend/scripts/scrape_<institution_id>.py`.
  Each writes a file conforming to `docs/03-data-schema.md` and nothing else.
- Record in each JSON file: `source_url`, `scraped_at`, `academic_year`. Graders and
  coordinators will ask where the data came from.
- Be polite: `time.sleep(1)` between requests, a real User-Agent, and honour robots.txt.
  If a site disallows scraping, copy the 30-60 courses by hand - it is one afternoon
  and it is not a research contribution either way.

## Language decides what we can ingest (checked 2026-09-20)

The pipeline is English-only by design (ADR-0001): `bge-small-en-v1.5` and
`ms-marco-MiniLM` have no useful representation of German or Dutch text, so feeding them
a German syllabus does not degrade politely, it returns near-random neighbours. The
smallest decent multilingual bi-encoder, `multilingual-e5-small`, is about 470 MB on its
own and would break the 400 MB image budget in AGENTS.md by itself.

So the rule for adding a university is: **ingest a programme that is taught in English**,
and accept that for several of them this means the master's rather than the bachelor's.

| University | English programme to ingest | Level | Catalogue |
|---|---|---|---|
| Twente | BSc Technical Computer Science | BSc | Osiris JSON API, done |
| Twente | BSc Applied Mathematics | BSc | same scraper, `--programme`, done. It teaches the mathematics that TCS students take, which is why the maths half of PMF had nothing to match against |
| KTH Stockholm | MSc Computer Science | MSc | `kth.se/student/kurser/kurs/<CODE>?l=en`, server-rendered, done. The syllabus page that lists the codes is a JavaScript app, so the code list is committed as `kth-cs-msc.codes.txt` |
| EPFL | MSc Computer Science | MSc | `edu.epfl.ch`, server-rendered, done |
| Delft | BSc Computer Science and Engineering | BSc | `studiegids.tudelft.nl`, JavaScript app |
| JKU Linz | BSc Artificial Intelligence | BSc | JKU online catalogue |
| TU Munich | MSc Informatics | MSc | TUMonline (CAMPUSonline) |
| TU Graz | MSc Computer Science | MSc | TUGRAZonline (CAMPUSonline) |
| TU Wien | MSc programmes in informatics | MSc | TISS |
| ETH Zurich | MSc Computer Science | MSc | VVZ, session-bound URLs |

Mixing master's catalogues into a bachelor's comparison is a level mismatch, not a bug.
It is the case S6-A2 has to write up: a master's course should match a bachelor's course
less confidently, and a system that reports that honestly is showing it works.

## Added 2026-09-26: TU Delft and Politecnico di Milano

Added at Luka's request because they are names students in Serbia recognise. Neither
has gold labels, so they are in the demo and not in the evaluation.

| Institution | Programme | Courses | Source | Caveat |
|---|---|---|---|---|
| TU Delft (NL) | BSc Computer Science and Engineering, 2026/2027 | 35 | study guide JSON API behind `studiegids.tudelft.nl` (`backend/scripts/scrape_tudelft.py`) | Delft's Osiris records are placeholders, so the study guide is used. The 30 EC minor and free electives are not listed under the programme and are missing |
| Politecnico di Milano (IT) | BSc Engineering of Computing Systems (Ingegneria Informatica), 2025/2026 | 45 | English course catalogue on `onlineservices.polimi.it` (`backend/scripts/scrape_polimi.py`) | Polimi has no English-taught computer science bachelor. This one is taught in Italian, but its catalogue publishes an English description for every course, so it breaks criterion 1 for teaching language and meets it for the text we match on. Only 5 courses have English learning outcomes |

The rejected list above (TU Munich, Graz, Wien, ETH) stands: those bachelor's
programmes are taught and described in German. Oxford and Cambridge are out of scope
because the UK left Erasmus+ in 2021.

## Known data hazards (write these into the error analysis)

- **Granularity mismatch** - Twente 15-ECTS modules vs PMF 6-ECTS courses.
- **Level collision** - "Databases 1" at PMF vs "Advanced Databases" at the host.
- **Same name, different content** - "Software Engineering" means requirements
  engineering at one school and a team project at another.
- **Different name, same content** - "Formal Languages and Automata" vs
  "Theory of Computation" vs "Berechenbarkeit". This is where dense retrieval earns
  its place over BM25, and it is the headline example for the defence.
- **Empty or one-line descriptions** - some catalogues give only a title. Fall back to
  title + programme context, and flag the match as low-confidence in the UI.
