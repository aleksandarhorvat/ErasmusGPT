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

## Gold set

Two files. The split exists so that one annotation pass produces both the labels and the
statistic that justifies how they were made.

### `data/gold/llm_prelabels.csv` - written once, never edited

The raw output of the pre-labelling run. Commit it and leave it alone.

```csv
home_uid,host_uid,llm_label,llm_reason
uns-pmf:I102,utwente:TCS-M2,2,"both cover data structures and complexity analysis"
uns-pmf:I203,utwente:TCS-M1,2,"host module teaches object-oriented programming in Java"
```

### `data/gold/gold_pairs.csv` - the working file

Starts as a copy of the pre-labels, with `llm_label` renamed to `label` and `llm_reason`
dropped. It is split by home course into `half_a_luka.csv` and
`half_b_aleksandar.csv`; each person reads every row of their half, corrects `label`
where they disagree, and sets `checked` to `yes`, and `scripts/merge_gold.py` writes
this file back from the halves. Four columns, no free text: use `tools/annotate.html`.

```csv
home_uid,host_uid,label,checked
uns-pmf:I102,utwente:TCS-M2,2,yes
uns-pmf:I203,utwente:TCS-M1,1,yes
uns-pmf:I102,utwente:TCS-M8,0,yes
```

- `label`: the authoritative judgement, and the only column the metrics read.
  `2` = would be recognised outright, `1` = partial or arguable, `0` = not a match.
- `checked`: `yes` once a human has read the row and accepted or corrected the label.
  **Rows with `checked=no` are excluded from every reported number**, so an unfinished
  pass can never silently contaminate the results.

Agreement between the model and the expert is computed by diffing the two files. No
per-row bookkeeping during annotation, and the statistic survives the corrections. The
reasoning behind a correction belongs in the error analysis (`eval/report/errors.md`),
not in a column nobody will read back.

### Which pairs to label

Do not label all n x m pairs. Use pooling: take the union of the top 10 from `dense` and
`hybrid+ce` per home course. Pool depth 10 is all that Recall@5, MRR@10 and nDCG@10
require, and about 40 home courses is enough to make the metrics meaningful. That is
roughly 400 pairs, not several thousand.

Unlabelled pairs count as 0, which slightly favours the strategies that contributed to
the pool. State that in the report in one sentence; it is a known property of pooled
collections, not a flaw specific to this project.

### Inter-annotator agreement

Person B labels an overlapping slice of about 30 pairs **cold**, from
`data/gold/gold_pairs_b.csv`, without seeing the LLM labels or Person A's file. Cohen's
kappa is computed against Person A's final labels on those rows.

This slice has to stay cold. If both people review the same LLM suggestions, kappa
measures how similarly two humans anchor on a machine, which is not a useful number.
