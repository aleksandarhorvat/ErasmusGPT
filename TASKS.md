# TASKS - staged plan

The work is split into **stages**. Inside a stage there are two independent lanes,
**A** (matching engine & data) and **B** (service & platform), which can be worked on
at the same time without touching each other's files. A stage closes only when **both**
lanes have passed their gate.

> **Agents:** update the *Project state* block below in the same commit as your first
> change. It is the first thing the other person's agent reads.

---

## Project state

| | |
|---|---|
| **Current stage** | **Stage 7 - Defence** (stages 0 to 6 closed) |
| **Lane A** | Luka - curriculum domain, matching engine, evaluation |
| **Lane B** | Aleksandar - service, front end, packaging |
| **Person A is on** | lane A done. Gold set, results, kappa, calibration (cross-validated), error analysis, B's audit fixes, partner order by ARWU and distance, silver set across all six hosts (`eval/report/silver.md`, model-labelled). Optional `S6-A3` left to Luka |
| **Person B is on** | nothing open. `S7-AB2` done (offline rehearsal passed); left is the talk itself |
| **Blocked on** | nothing. Left: `S7-AB1` final read of the deck and rehearsing the talk (both), optional `S6-A3` (A) |
| **Last updated** | 2026-09-26 - B: A's overnight note answered, silver report labelled on the evaluation page; left is the deck read and the talk |

### Stage ladder

| Stage | Lane A | Lane B | Gate |
|---|---|---|---|
| 0 - Scaffold | done | done | closed |
| 1 - Real data, real surface | done | done | closed |
| 2 - Dense retrieval | done (early) | done | closed |
| 3 - Lexical + hybrid | done (early) | done | closed |
| 4 - Cross-encoder rerank | done (early) | done | closed |
| 5 - Gold set + evaluation | done | done | closed |
| 6 - Scale out + polish | done | done | closed |
| 7 - Defence | wip | wip | todo |

Status values: `todo`, `wip`, `blocked`, `done`, `early` (pulled forward from a later stage).

### Rules for agents

1. Work on tasks in **your lane, in the current stage**. Task IDs read `S<stage>-<lane><n>`.
2. If every task in your lane for this stage is `done` and the other lane is not, you may
   pull the **next** stage's tasks from your own lane - mark them `early` in the table and
   say so in `PROGRESS.md`. Do not touch the other lane to "help".
3. If you are blocked by the other lane, set your task to blocked, write a
   `### Request to A|B` bullet in your `PROGRESS.md` entry, and pick the next task in your
   own lane instead of waiting.
4. When your lane's last task in a stage is done, tick your half of the stage gate.
   The person who ticks the **second** half moves *Current stage* forward.

---

## Stage 0 - Scaffold closed

Repository, docs, frozen contract, stub matcher, Docker/compose files, sample data.
Nothing to do. See the first entry in `PROGRESS.md`.

---

## Stage 1 - Real data, real surface

**Goal:** the app shows a real UNS PMF curriculum against a real Twente curriculum,
running from a Docker image with the models already inside it. Matches are still fake
(stub) - that is fine and expected at this stage.

### Lane A

| ID | Status | Task | Done when | Needs |
|---|---|---|---|---|
| `S1-A1` | done | Scrape/transcribe the **full UNS PMF BSc Informatics** curriculum into `data/curricula/uns-pmf-informatics-bsc.json` (both modules, English titles, descriptions, outcomes, ECTS). Replaces the sample file. | `GET /api/v1/programmes` reports >= 45 courses and every course has a non-empty `description` | - |
| `S1-A2` | done | Same for **University of Twente, BSc Technical Computer Science** -> `utwente-tcs-bsc.json`, via `backend/scripts/scrape_utwente.py` | file validates against `docs/03-data-schema.md`, `source_url` and `scraped_at` filled in | - |
| `S1-A3` | done | `backend/scripts/validate_curricula.py` - schema check + duplicate-code check, runnable in CI | `python backend/scripts/validate_curricula.py` exits 0 on both files and non-zero on a broken one | - |

**Lane A gate:** [x] two real curricula committed, validator green (three, with EPFL).

### Lane B

| ID | Status | Task | Done when | Needs |
|---|---|---|---|---|
| `S1-B1` | done | Finish the UI happy path: two programme dropdowns, match button, results table, loading and error states, wired to `get_matcher()` | picking two programmes and clicking Match renders a table in the browser | - |
| `S1-B2` | done | Build once with the network, then **run** offline: models baked in, `HF_HUB_OFFLINE=1`, healthcheck green, nginx proxy correct, no image-registry lookups at run time | `docker compose up --build` once, then network off, `docker compose up` -> UI at :8080 still serves matches. Verified 2026-09-18 | - |
| `S1-B3` | done | `GET /api/v1/programmes/{id}/courses` rendered as a "browse this curriculum" panel, so data problems are visible without hitting `/match`. Flags courses with an empty description, which is `S1-A1`'s acceptance criterion | clicking a programme lists its courses with ECTS | - |

**Lane B gate:** [x] one command starts the whole thing offline and shows a table.

**Stage gate:** [x] A   [x] B - a stranger can clone, run one command, and see real PMF course
titles next to real Twente course titles.

---

## Stage 2 - Dense retrieval

**Goal:** the first real NLP. Cosine similarity over sentence-transformer embeddings
replaces the stub. `strategy=dense` returns genuinely sensible top-5 lists.

### Lane A

| ID | Status | Task | Done when | Needs |
|---|---|---|---|---|
| `S2-A1` | done (early) | Implement `matching/embedder.py`: load the bi-encoder from `settings.bi_encoder_repo`, encode course documents, L2-normalise, cache to `data/.cache/{programme}.{model_tag}.npy` keyed by a content hash | second startup loads from cache; encoding never happens inside a request | - |
| `S2-A2` | done (early) | Implement `matching/dense.py` - exact NumPy cosine search returning `[(course_uid, score)]` | unit test: a course matches itself with score ~ 1.0 | `S2-A1` |
| `S2-A3` | done (early) | Implement `matching/pipeline.py` `PipelineMatcher` satisfying the `Matcher` protocol, supporting `strategy="dense"`. Other strategies may raise `NotImplementedError` for now | `MATCHER_IMPL=real` no longer falls back to the stub; `/health` reports `models_loaded: true` | `S2-A2` |
| `S2-A4` | done (early) | Tests: `backend/tests/test_matching_dense.py` - self-match, cache hit, deterministic ordering | `pytest backend/tests` green | `S2-A3` |

**Lane A gate:** [x] `strategy=dense` returns real results and *Formal Languages and Automata*
finds *Theory of Computation* in the top 5 (rank 1, cosine 0.878, verified 2026-09-20).

### Lane B

| ID | Status | Task | Done when | Needs |
|---|---|---|---|---|
| `S2-B1` | done | Strategy selector in the UI driven by `GET /api/v1/strategies`, with the description shown under it; disable strategies the backend reports as unavailable | switching strategy re-runs the match and the table updates | - |
| `S2-B2` | done | Real loading UX: a progress indicator that survives a 60 s request, and a clear timeout message. Raise the nginx/axios timeouts to 180 s | a 60 s match does not look like a hang | - |
| `S2-B3` | done | SQLite persistence of ingested programmes (`app/db/models.py`), `content_hash` bookkeeping so A's cache invalidation has a home | restarting the container does not re-ingest unchanged files | - |

**Lane B gate:** [x] the UI can drive every strategy and survives a slow request (selector from `/strategies`, progress timer, 150 s timeout under nginx's 180 s).

**Stage gate:** [x] A   [x] B - the demo produces real semantic matches end to end.

---

## Stage 3 - Lexical retrieval and hybrid fusion

**Goal:** the IR half of the course. BM25 as an honest baseline, Reciprocal Rank Fusion
as the candidate generator that feeds the reranker.

### Lane A

| ID | Status | Task | Done when | Needs |
|---|---|---|---|---|
| `S3-A1` | done (early) | `matching/lexical.py`: BM25 over the same `build_document()` text. Document the tokenisation in `docs/05-evaluation.md` - it defines the baseline everyone is compared against | `strategy=bm25` works; an exact title match ranks 1st | Stage 2 |
| `S3-A2` | done (early) | Wire `matching/fusion.py` (RRF is already written) into the pipeline as `strategy=hybrid`; `settings.candidate_top_n` controls the cut | `strategy=hybrid` returns >= the union recall of the two inputs | `S3-A1` |
| `S3-A3` | done (early) | Quick manual smoke sheet: 10 home courses x 4 strategies, eyeballed, committed as `eval/report/smoke.md` | the table exists and the obvious pairs look right | `S3-A2` |

**Lane A gate:** [x] all of `bm25`, `dense`, `hybrid` work through the same pipeline.

### Lane B

| ID | Status | Task | Done when | Needs |
|---|---|---|---|---|
| `S3-B1` | done | Score calibration: map each strategy's raw score to `score_pct` 0-100 and a `confidence` band, in **one** place, plus the ECTS delta column | scores are comparable across strategies in the UI; bands are green/amber/red | - |
| `S3-B2` | done | "Export to CSV" button - the artefact a student actually emails to their coordinator (home course, ECTS, top-5 host courses, scores, links) | the downloaded file opens cleanly in Excel | `S1-B1` |
| `S3-B3` | done | Per-row "re-match this course" using `POST /api/v1/match/course`, so a single row can be retried with another strategy without re-running the whole programme | one row updates in place | - |

**Lane B gate:** [x] results are interpretable and exportable (`lib/score.ts`, evidence under "why", CSV export).

**Stage gate:** [x] A   [x] B.

---

## Stage 4 - Cross-encoder reranking

**Goal:** the main claim of the project. If only one stage works, it should be this one.

### Lane A

| ID | Status | Task | Done when | Needs |
|---|---|---|---|---|
| `S4-A1` | done (early) | `matching/reranker.py`: batched `CrossEncoder` over `(home_doc, host_doc)` pairs, sigmoid-squashed to 0-1 before leaving the module | a full 50-course programme reranks in < 45 s on CPU | Stage 3 |
| `S4-A2` | done (early) | `strategy=hybrid+ce` in the pipeline: RRF -> top-`candidate_top_n` -> rerank -> top-`k` | default strategy in the UI returns visibly better lists than `dense` | `S4-A1` |
| `S4-A3` | done (early) | Evidence extraction: best-scoring sentence pair per match, returned as `Evidence` | `evidence` is non-null for every match | `S4-A2` |
| `S4-A4` | done (early) | Latency guard: cap pairs per request, log ms/query, add `backend/tests/test_matching_rerank.py` | tests green, no request over 120 s | `S4-A2` |

**Lane A gate:** [x] `hybrid+ce` is the default and is demonstrably better by eye (see `eval/report/smoke.md`).

### Lane B

| ID | Status | Task | Done when | Needs |
|---|---|---|---|---|
| `S4-B1` | done | Render `evidence` as an expandable "why" under each match - the two sentences, quoted | clicking "why" shows the sentence pair | `S4-A3` (use the contract's shape before it lands; it is frozen) |
| `S4-B2` | done | Side-by-side compare mode: same home course, two strategies, two columns. This is the screenshot for the README and the slides | toggling compare shows `dense` vs `hybrid+ce` next to each other | `S3-B3` |
| `S4-B3` | done | Show `took_ms` and the active model names in the footer (`/health` already carries them) | the demo can answer "what is it actually running?" without opening a terminal | - |

**Lane B gate:** [x] the difference is visible on screen, not only in the eval table (per-row compare against another strategy). Measured, the reranker is level rather than better; see ADR-0005.

**Stage gate:** [x] A   [x] B.

---

## Stage 5 - Gold set and evaluation

**Goal:** replace "it looks good" with a number you can defend. Protocol: `docs/05-evaluation.md`.

### Lane A

| ID | Status | Task | Done when | Needs |
|---|---|---|---|---|
| `S5-A0` | done | Pool the pairs worth labelling: union of the top 10 from `dense` and `hybrid+ce` over ~40 home courses (~500 pairs), then pre-label the pool into `data/gold/llm_prelabels.csv` and commit it unedited | the pool is reproducible from a script and the pre-label file exists | Stage 4 |
| `S5-A1` | done (680 human, 462 model, see `data/gold/provenance.json`) | Read every pooled row in `tools/annotate.html`, correct `label` where you disagree with the model, `Enter` to accept. Rubric: `docs/05-evaluation.md`. **Split since 2026-09-25**: Luka works in `data/gold/half_a_luka.csv` (638 rows, holds all 30 cold pairs), Aleksandar in `half_b_aleksandar.csv` (504 rows, after his cold slice); `python scripts/merge_gold.py` writes `gold_pairs.csv`, see `tools/README.md` | ~500 checked rows over 40 home courses, no duplicate `(home_uid, host_uid)` | `S5-A0` |
| `S5-A2` | done (early) | Finish `eval/run_eval.py`: every configuration, Recall@5, Recall@10, MRR@10, nDCG@10, P@1, ms/query, importing the **same** `app.matching` code the API uses | `python eval/run_eval.py --host-programme utwente-tcs-bsc` writes `eval/report/results.md` | `S5-A1` |
| `S5-A3` | done | Statistics: 95 % bootstrap CIs over queries, paired test `hybrid+ce` vs `dense-minilm`, plus the correction rate from diffing `llm_prelabels.csv` against `gold_pairs.csv` | the report states whether the gain is significant, and discloses the pre-labelling and the correction rate | `S5-A2` |
| `S5-A4` | done (early) | Unit tests for the metric functions (`test_matching_metrics.py`) - hand-computed expected values | green | `S5-A2` |

**Lane A gate:** [x] `eval/report/results.md` is committed with real numbers and CIs.

### Lane B

| ID | Status | Task | Done when | Needs |
|---|---|---|---|---|
| `S5-B0` | done (early) | Annotation tool `tools/annotate.html`: side-by-side course cards, keyboard labelling, saves back to the CSV in place | the tool loads curricula and a pairs CSV and writes checked rows back | - |
| `S5-B1` | done | `scripts/make_kappa_slice.py` has drawn the 30 pairs into `data/gold/gold_pairs_b.csv`, unlabelled. Label them **cold**, without seeing the LLM labels or A's file, into `data/gold/gold_pairs_b.csv`, so Cohen's kappa measures two humans rather than two people anchoring on a machine | the file exists; A computes kappa against his final labels | `S5-A0` |
| `S5-B2` | done | CI green: `ruff`, `pytest` with `MATCHER_IMPL=stub`, frontend build, curriculum validator | the badge is green on `main` | `S1-A3` |
| `S5-B3` | done | Serve the evaluation table in the UI (read `eval/report/results.csv`) as an "About / how well does this work" page | the numbers are one click away during the defence | `S5-A2` |

**Lane B gate:** [x] CI checks green locally, kappa slice annotated (30 of 30), numbers and the human/model label split visible in the app.

**Stage gate:** [x] A   [x] B - you can answer "how do you know it works?" with a table.

---

## Stage 6 - Scale out, aggregate, polish

**Added 2026-09-20 by A:** the system compares *courses*. What a
student actually asks is "how much of my degree would be recognised". That is `S6-A4`,
`S6-A5` and `S6-B4` below, and it is the difference between a demo and something a
coordinator would use. It needs the gold set first: a cross-encoder score is not a
probability until it has been calibrated against real labels.

### Lane A

| ID | Status | Task | Done when | Needs |
|---|---|---|---|---|
| `S6-A1` | done (early) | Ingest 2-3 more curricula (Masaryk, then TU Wien / Ljubljana / DTU - see `docs/01-universities.md`) | `/programmes` lists >= 4 host programmes | Stage 5 |
| `S6-A2` | done (on the final labels) | Error analysis: the 10 worst queries, classified into the failure categories in `docs/01-universities.md`, written into `eval/report/errors.md` | the table exists with counts per category | `S6-A1` |
| `S6-A3` | todo | *Optional, Colab:* fine-tune the bi-encoder on the gold set (`MultipleNegativesRankingLoss`) and report the delta; also run `gte-modernbert-base` and `mxbai-rerank-base-v2` for the ceiling row | an extra row in `results.md`, or a documented decision not to | `S5-A2` |

| `S6-A4` | done | **Recognition estimate, part 1: make the score mean something.** Fit a calibration (Platt or isotonic) on the gold set so `score_pct` is the probability that a human recognises the pair, not an arbitrary display number. Expose the same mapping to `eval/` and report calibration error | `score_pct` of 70 means roughly 70 % of such pairs were labelled 1 or 2 in the gold set | `S5-A1` |
| `S6-A5` | done | **Recognition estimate, part 2: aggregate over a programme.** `GET`/`POST` returns, per home course, the best match and its calibrated probability; the expected recognised ECTS of a whole programme is the sum of `ects x p`. Decide and document the rule for partial matches (label 1) and for ECTS shortfall (6 ECTS home vs 4 ECTS host) | a programme-level number exists with its arithmetic written down in `docs/05-evaluation.md` | `S6-A4` |

**Lane A gate:** [x] >= 4 host programmes; [x] error analysis committed (provisional, re-run
after `S5-A1`); [x] recognition estimate calibrated.

### Lane B

| ID | Status | Task | Done when | Needs |
|---|---|---|---|---|
| `S6-B1` | done (screenshots dropped 2026-09-26) | README final pass: screenshots, the evaluation table, one-command run instructions verified on a clean machine | someone who has never seen the repo runs it without asking you anything | Stage 5 |
| `S6-B2` | done | Clean-machine test: `docker system prune -a`, fresh clone, `docker compose up --build`, time it, record the number in the README | the recorded time is real | `S6-B1` |
| `S6-B3` | done | Accessibility/robustness sweep: empty results, unknown programme, backend down, very long course titles | no unhandled error in the console | - |
| `S6-B4` | done | **Recognition summary panel.** Above the table: "about X of your 180 ECTS would likely be recognised, Y borderline, Z with no match", from `ects x p` over the rows. Colour-code each row by confidence band and show a "no suitable match" state instead of a weak top hit | the panel matches a hand-computed sum for one programme | `S6-A4`, `S3-B1` |

**Lane B gate:** [x] verified clean-machine run (297 s, README) + README + recognition summary.

**Stage gate:** [x] A   [x] B.

---

## Stage 7 - Defence

| ID | Owner | Status | Task |
|---|---|---|---|
| `S7-AB1` | both | wip (A and B slides in `docs/slides/`, rebuild after `S5-A1`) | Slides: problem -> pipeline diagram -> live demo -> evaluation table -> error analysis -> limitations |
| `S7-AB2` | both | done (2026-09-26: offline run passed, timings in README) | Rehearse the live demo **offline** (pull the network cable - the image must not need it) |
| `S7-A1` | A | done | Own the NLP/IR questions: why RRF, why a cross-encoder, why those models, what the CIs mean |
| `S7-B1` | B | done | Own the engineering questions: the contract, the stub/real split, why SQLite, why models are baked in |

---

## Backlog - only if a stage finishes early

| ID | Lane | Task |
|---|---|---|
| `BL-A1` | A | ECTS-aware many-to-one matching (one home course ~ two host courses summing to its ECTS) |
| `BL-A2` | A | Multilingual support, reopening ADR-0001 (a partner without English descriptions) |
| `BL-B1` | B | Upload-your-own-curriculum endpoint (PDF/CSV) |
| `BL-B2` | B | Saved comparisons / shareable link for a match run |
