# API contract (frozen)

Owner: **Person B**, but **shared** - changing it requires a `CONTRACT CHANGE` entry in
`PROGRESS.md` and matching updates to `backend/app/schemas/` and the frontend client.

Base path: `/api/v1`. All responses are JSON. Errors follow FastAPI's
`{"detail": "..."}` shape with a proper status code.

## `GET /api/v1/health`
```json
{ "status": "ok", "matcher": "real", "models_loaded": true, "version": "0.1.0" }
```

## `GET /api/v1/programmes`
```json
[
  { "programme_id": "uns-pmf-informatics-bsc",
    "institution_name": "University of Novi Sad, Faculty of Sciences",
    "programme_name": "BSc Informatics", "country": "RS",
    "level": "bachelor", "course_count": 54, "total_ects": 180 }
]
```

## `GET /api/v1/programmes/{programme_id}/courses`
```json
[ { "course_uid": "uns-pmf:I101", "code": "I101", "title": "Introduction to Programming",
    "ects": 8.0, "year": 1, "semester": 1, "mandatory": true, "module": null } ]
```
404 if unknown.

## `POST /api/v1/match`
Request:
```json
{
  "home_programme_id": "uns-pmf-informatics-bsc",
  "host_programme_id": "utwente-tcs-bsc",
  "strategy": "hybrid",             // bm25 | dense | hybrid | hybrid+ce (default: hybrid)
  "top_k": 5,                       // 1..10
  "course_uids": null               // null = all home courses; or a subset
}
```
Response:
```json
{
  "home_programme_id": "uns-pmf-informatics-bsc",
  "host_programme_id": "utwente-tcs-bsc",
  "strategy": "hybrid+ce",
  "took_ms": 1840,
  "results": [
    {
      "home_course": { "course_uid": "uns-pmf:I101", "title": "Introduction to Programming", "ects": 8.0 },
      "matches": [
        {
          "host_course": { "course_uid": "utwente:202001032",
                           "title": "Programming Paradigms", "ects": 6.0,
                           "url": "https://..." },
          "score": 0.87,            // 0..1, comparable ONLY within one strategy
          "score_pct": 87,          // calibrated 0..100 for display
          "confidence": "high",     // high | medium | low
          "ects_delta": -2.0,       // host - home
          "rank": 1,
          "evidence": { "home_sentence": "...", "host_sentence": "...", "similarity": 0.91 }
        }
      ]
    }
  ]
}
```

Rules:
- `results` is ordered like the home programme (year, semester, code), not by score.
- `matches` is ordered by `rank` ascending, length <= `top_k`, possibly 0.
- `score` is whatever the active strategy produces (cosine, RRF, or cross-encoder
  logit passed through a sigmoid). Never compare raw scores across strategies in the
  UI - that is what `score_pct` is for.
- `score_pct` **means different things per strategy**, which the old wording
  ("calibrated 0..100 for display") hid. Raised by B on 2026-09-20; see the CONTRACT
  CHANGE note in `PROGRESS.md` for that date.

  | Strategy | What `score_pct` is | Safe to read as a probability |
  |---|---|---|
  | `hybrid`, `hybrid+ce` (since 2026-09-25) | calibrated probability that a coordinator recognises the pair, fitted on the gold set (`data/calibration/`) | yes |
  | `dense` | cosine stretched from 0.55-0.95 onto 0-100 | no |
  | `bm25` | score relative to the best hit for the same home course, so rank 1 always reads 100 | no |

  The field is still an integer 0..100 and still ordered within one strategy, so nothing
  in the schema changes. Only a strategy that `GET /strategies` reports as `calibrated`
  may be shown as a percentage chance; for the others the UI shows a bare number and a
  band. A calibration file for another strategy moves it to the first row without a
  schema change, and the UI follows because it reads the flag rather than a list.
- `confidence` is derived from `score_pct` by one set of thresholds, in
  `aggregate.py`: high at 0.70, medium at 0.40. `aggregate.py` calls the same bands
  likely, borderline and unlikely when summarising a whole programme; the mapping is
  `BUCKET_OF_CONFIDENCE`. One threshold, two vocabularies, no third set of cut-offs.
- `evidence` may be `null` until S4-A3 lands.
- Long requests: matching a full 54-course programme with `hybrid+ce` on CPU can take
  ~10-30 s. The UI must show progress; do not add a timeout below 120 s.

## `POST /api/v1/match/course`
Single home course against a host programme. Same match object, no wrapper list.
Used by the UI for "re-rank this one row with a different strategy".

## `GET /api/v1/strategies`
```json
[ { "id": "hybrid", "label": "Hybrid (BM25 + dense, RRF)", "description": "...",
    "calibrated": true, "provisional": true } ]
```
Lets the UI build the selector without hardcoding the list.

- `calibrated`: a file in `data/calibration/` exists for this strategy, so its
  `score_pct` is a fitted probability of recognition. Otherwise it is a display number
  and the UI must not print it as a percentage chance (`frontend/src/lib/score.ts`).
- `provisional`: that calibration was fitted on machine labels (`label_source` starts
  with `PROVISIONAL`). The UI says so next to every probability.

## `POST /api/v1/recognition`
The whole-programme estimate (S6-A5, S6-B4). Request:
```json
{ "home_programme_id": "uns-pmf-informatics-bsc", "host_programme_id": "utwente-tcs-bsc",
  "strategy": "hybrid", "module": null, "ects_budget": 180 }
```
`module` (null means every course offered) narrows the home side to one study path;
`ects_budget`, usually the programme's `total_ects`, caps the denominator at the degree
size. Response:
```json
{ "home_programme_id": "uns-pmf-informatics-bsc", "host_programme_id": "utwente-tcs-bsc",
  "strategy": "hybrid", "module": null, "calibrated": true, "provisional": true,
  "took_ms": 451, "total_ects": 179.0, "expected_recognised_ects": 108.1,
  "expected_share": 0.6039, "likely_ects": 18.0, "borderline_ects": 161.0,
  "unlikely_ects": 0.0, "ects_shortfall": 50.5,
  "courses": [ { "course_uid": "uns-pmf:I011", "title": "Introduction to programming",
                 "ects": 9.0, "probability": 0.64, "bucket": "borderline",
                 "best_match_uid": "utwente:202500342",
                 "best_match_title": "Introduction to Programming",
                 "ects_shortfall": 6.0 } ] }
```
The arithmetic (`ects x p`, the bands, the shortfall rule) is Person A's, in
`backend/app/matching/aggregate.py` and `docs/05-evaluation.md`. When `calibrated` is
false the sums are over display values, and the UI refuses to show them as an ECTS
estimate. 404 for an unknown programme, 422 for an unknown strategy or a budget below 1.

## `GET /api/v1/evaluation`
What `eval/report/` holds and how far the human labelling pass has got (S5-B3).
```json
{ "available": true, "provisional": false, "gold_checked": 1142, "gold_total": 1142,
  "gold_human": 680, "gold_model": 462,
  "columns": ["config", "Recall@5", "..."], "rows": [ { "config": "hybrid", "...": "..." } ],
  "reports": ["ablations.md", "errors.md", "kappa.md", "results.md", "smoke.md"] }
```
- `available`: `eval/report/results.csv` exists and has rows. `columns` and `rows` are
  that file as strings, so the harness can add a metric without a contract change.
- `gold_human`, `gold_model` (added 2026-09-26): how the checked rows got their label,
  from `data/gold/provenance.json`. `checked=yes` means "has its final label", which
  since that date is not the same as "a person checked it". Without the file every
  checked row counts as human.
- `provisional`: true until **every** row of `data/gold/gold_pairs.csv` is checked. A
  partial pass is still provisional, because `run_eval.py` scores only checked rows and
  those cover whichever home courses were labelled first.
