# Curriculum data schema

Owner: **Person A**. Consumed by `backend/app/ingest/` and `eval/`.

One JSON file per study programme: `data/curricula/<programme_id>.json`.

```jsonc
{
  "programme_id": "utwente-tcs-bsc",          // slug, unique, = filename stem
  "institution_id": "utwente",                // slug
  "institution_name": "University of Twente",
  "country": "NL",
  "programme_name": "BSc Technical Computer Science",
  "level": "bachelor",                        // bachelor | master
  "language": "en",
  "total_ects": 180,
  "academic_year": "2025/2026",
  "source_url": "https://utwente.osiris-student.nl/...",
  "scraped_at": "2026-09-18T12:00:00Z",
  "courses": [
    {
      "code": "202001032",                    // as printed by the institution
      "title": "Data Structures and Algorithms",
      "ects": 6.0,
      "year": 2,                              // 1..3, null if unknown
      "semester": 1,                          // 1..6 or 1..2, null if unknown
      "mandatory": true,
      "module": "Computer Science",           // null when the programme has no modules
      "language": "en",
      "description": "Free text. The main signal.",
      "learning_outcomes": ["...", "..."],    // may be empty
      "topics": ["graphs", "hashing"],        // may be empty
      "prerequisites": ["202001031"],         // course codes, may be empty
      "url": "https://.../course/202001032"
    }
  ]
}
```

## Rules

- `course_uid` = `f"{institution_id}:{code}"`. This is the key used in the API, the
  embedding cache and the gold set. It must be stable across re-scrapes - if an
  institution changes its codes, bump `academic_year` and keep the old file.
- `ects` is a float (some institutions use 7.5).
- `description` may be empty but the field must exist. Never `null` for string fields;
  use `""`. Never `null` for list fields; use `[]`.
- Everything is stored **as published**, unmodified. All normalisation happens at
  runtime in `matching/document.py`, so it can be changed without re-scraping.

## The "course document" (what actually gets embedded)

Built by `backend/app/matching/document.py`. One definition, used by retrieval, reranking and evaluation alike. If they diverge,
the reported numbers stop describing the running system.

```
{title}

{description}

Learning outcomes: {"; ".join(learning_outcomes)}
Topics: {", ".join(topics)}
```

Then: collapse whitespace, strip boilerplate (e.g. "This course is part of module...",
"Students who have passed..."), truncate to the model's max sequence length by
**sentences**, not characters.

Deliberately **not** included in the embedded text: ECTS, year, semester, institution
name. They are strong lexical distractors and they are more useful as post-filters
and as displayed metadata than as embedding content. ECTS difference is shown in the
UI and used for the confidence band, not for ranking. (ADR-0004)

## Gold set - `data/gold/gold_pairs.csv`

```csv
home_uid,host_uid,label,annotator,note
uns-pmf:I101,utwente:202001032,2,A,"same content, host is broader"
uns-pmf:I101,utwente:202001045,0,A,""
```

- `label`: `2` = would be recognised outright, `1` = partial / arguable, `0` = not a match.
- Annotate **positives exhaustively** per home course (every host course that deserves
  a 1 or 2), plus hard negatives. You do not need to label all nxm pairs; unlabelled
  pairs count as 0 for the metrics, and that must be stated in the report.
- Both people annotate an overlapping slice of ~30 pairs so Cohen's kappa can be reported.
  Inter-annotator agreement tells the reader how reliable the labels themselves are.
