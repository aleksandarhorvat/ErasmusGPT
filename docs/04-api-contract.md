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
  "strategy": "hybrid+ce",          // bm25 | dense | hybrid | hybrid+ce
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
- `evidence` may be `null` until S4-A3 lands.
- Long requests: matching a full 54-course programme with `hybrid+ce` on CPU can take
  ~10-30 s. The UI must show progress; do not add a timeout below 120 s.

## `POST /api/v1/match/course`
Single home course against a host programme. Same match object, no wrapper list.
Used by the UI for "re-rank this one row with a different strategy".

## `GET /api/v1/strategies`
```json
[ { "id": "bm25", "label": "BM25 (lexical baseline)", "description": "..." } ]
```
Lets the UI build the selector without hardcoding the list.
