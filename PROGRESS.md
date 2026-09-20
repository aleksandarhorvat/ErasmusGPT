# PROGRESS

Append-only work log. **Newest entry goes at the top**, directly under this line.
One entry per commit (or per working session if several commits land together).
Never rewrite or delete someone else's entry.
Entries follow the writing style in `CONTEXT.md` section 11: ASCII only, no filler.

Both people append at the top, so this file is the one place a git conflict is likely.
When it happens, keep **both** entries and order them by date. Never drop one.

An agent starting a session reads the *Project state* block in `TASKS.md`, then the
**top 2-3 entries here**, then `CONTEXT.md`. That is enough to know what state the
project is in and what to do next.

---

## 2026-09-20 - [A] Gold set pooled and pre-labelled, 562 pairs

**Who:** Person A
**Stage:** 5. `S5-A0` done. `S5-A1`, the human pass, is next and only a human can do it.
**Commit:** `[A] pool and pre-label the gold set`
**Tasks touched:** `S5-A0` (done)

### Done
- Pooled the union of the top 10 from `dense` and `hybrid+ce` over 40 PMF courses against
  the real Twente catalogue: **562 pairs, 14.1 per home course**. 238 were found by both
  strategies, 324 by one only.
- Pre-labelled all 562 by reading both course texts against the rubric in
  `docs/05-evaluation.md`, the question being whether a coordinator would sign the host
  course off in place of the home one. Result: **17 twos, 66 ones, 479 zeros.**
- `data/gold/llm_prelabels.csv` is written and frozen. `data/gold/gold_pairs.csv` is the
  working copy, same labels, every row `checked=no`.
- `pool.csv` now goes to `data/.cache/`, not `data/gold/`. It quotes course text verbatim
  and is regenerable, so it does not belong in the repository.

### What the labels say about the data
- **12 of the 40 home courses have no acceptable match at all**: both Calculus courses,
  Linear algebra, Analytic geometry, Numerical analysis, Algebra, both English courses,
  Financial mathematics, and both Software Labs. Twente's mathematics line is run by
  Applied Mathematics and is not in our slice of the catalogue, and nobody teaches
  academic English or a software tools lab there. A third of the programme therefore has
  no correct answer available, and the system still returns five candidates for each.
- Only 17 pairs are outright matches. The clean ones are the obvious ones: Computer
  networks against all three Network Systems parts, Operating systems 1, Computer
  architecture, Databases 1, Information systems 1 against Software Design and Modelling.

### Honesty note for the report
The pre-labels come from the same model family that the pipeline uses for matching. I
labelled from the course texts alone and did not look at which strategy proposed a pair
or at its rank, but the correlation cannot be ruled out, and `S5-A1` exists precisely to
break it. The correction rate from diffing the two files is the number that shows whether
the human pass was real, and it belongs in `results.md`.

### Next
- **Luka (S5-A1):** open `tools/annotate.html`, load `data/gold/gold_pairs.csv`, read each
  row and press Enter to accept or change the label. Only `checked=yes` rows reach the
  metrics, so today `eval/run_eval.py` still has nothing to measure.
- **A:** once rows are checked, run the evaluation and write `eval/report/results.md`.

---

## 2026-09-20 - [A] Three real curricula land. Stage 1 closed

**Who:** Person A
**Stage:** 1 closed, both lanes. Current stage moves to 2, where lane A is already done.
**Commit:** `[A] land the real twente and epfl curricula`
**Tasks touched:** `S1-A2` (done), `S6-A1` (wip)

### I edited a file in B's zone, with A's explicit approval
`scripts/check_style.py` applied the banned-word and sentence-pattern rules to
`data/curricula/*.json`. Those files quote universities word for word, and
`docs/03-data-schema.md` says the text is stored as published. Twente's prose broke six
rules, EPFL's broke eleven, all of it ordinary prospectus English. Editing a university's
wording to satisfy our style guide would make the data wrong.

The change is four lines: files under `data/curricula/` skip the word and pattern checks.
**The ASCII check still applies to them**, because `course_uid`s and the eval harness
depend on ASCII. Every other file is unaffected.

**B: this is your file. Say so if you want it reverted or written differently.** The rule
itself came from the initial scaffold rather than from anyone's decision, and it had
never met real scraped data.

### Done
- `data/curricula/utwente-tcs-bsc.json`: 40 real courses, 2025-2026, replacing the
  9-course sample. `data/curricula/epfl-cs-msc.json`: 78 courses.
- The API now serves three programmes: PMF 50, Twente 40, EPFL 78.
- `eval/report/smoke.md` regenerated against the real Twente catalogue.
- `data/README.md` updated: no placeholders left.

### What the real data shows, good and bad
- **Right:** Computer networks -> Network Systems Part 1, 2, 3 at 92, 88, 87 %.
  Software engineering -> Software Design and Modelling. Against EPFL, Formal languages
  and automata -> Computational complexity, with Goedel and recursivity third.
- **Wrong, and worth writing up in S6-A2:** Databases 1 ranks Information Diamond first
  at 82 % and the actual Databases course third at 53 %. Computer networks against EPFL
  returns Network machine learning at 96 %, a topical trap rather than an equivalent.
- **Structural:** the real Twente catalogue has no automata course, so Formal languages
  and automata gets an answer anyway (Introduction to Artificial Intelligence, 47 %).
  There is no concept of "no acceptable match" in the contract. Worth raising at the
  defence, and worth a threshold discussion with B for the UI.

### Next
- **A:** `S5-A0` pooling, then pre-labelling, which unblocks the whole of stage 5.

---

## 2026-09-20 - [A] EPFL scraper, and what language costs us

**Who:** Person A
**Stage:** 6 - more curricula, pulled forward. `S6-A1` is `wip`: scrapers land, data does not.
**Commit:** `[A] add the epfl scraper`
**Tasks touched:** `S6-A1` (wip, early)

### Done
- `backend/scripts/scrape_epfl.py`. `edu.epfl.ch` renders on the server and gives one
  English page per course with Summary, Content, Keywords and Learning Outcomes, which
  maps onto our schema almost field for field. It produces **78 courses** for MSc
  Computer Science, every one with a description and topics, and the validator passes.
- `validate_curricula.py` now separates errors from notes. A prerequisite naming a course
  outside the file used to be an error; for a master's catalogue that is normal, since
  EPFL's MSc courses require EPFL bachelor courses. It is reported as a note instead.

### The language question, answered with a measurement
Adding German or Dutch curricula is not free. `bge-small-en-v1.5` and `ms-marco-MiniLM`
are English-only (ADR-0001), and the smallest multilingual bi-encoder worth using,
`multilingual-e5-small`, is about 470 MB, which breaks the 400 MB image budget on its
own. So the rule is to ingest the **English-taught** programme at each university, which
for Munich, Graz, Vienna, Zurich and Lausanne means the master's. `docs/01-universities.md`
now carries the table of which programme to take at each of the eight universities.

### Broken / known issues
- **The style checker now blocks every curriculum file, not just Twente's.** EPFL's own
  course text trips 11 rules, four distinct banned words and one banned pattern, all of
  them ordinary prospectus English. Universities write marketing prose; our style rules
  exist for prose we write. Both the
  Twente and EPFL JSON files are parsed, cached and held back.
- Delft and ETH need more work than EPFL did: Delft's study guide is a JavaScript app
  with no plain API found yet, and ETH's VVZ uses session-bound course ids.

### Request to B (second time, now larger)
`scripts/check_style.py` has to skip the banned-word and sentence-pattern checks for
`data/curricula/`, keeping the ASCII check. Until it does, no real curriculum can be
committed, which blocks the gold set, the evaluation, and every university after Twente.

### Next
- **A:** Delft and JKU Linz if the checker is resolved; there is no point scraping more
  data that cannot be committed.

---

## 2026-09-20 - [A] Pooling script for the gold set

**Who:** Person A
**Stage:** 5. `S5-A0` stays blocked: the script is written, the run needs real data.
**Commit:** `[A] add the gold set pooling script`
**Tasks touched:** `S5-A0` (blocked, script written)

### Done
- `eval/make_pool.py` pools the union of the top 10 from `dense` and `hybrid+ce` per home
  course and writes `data/gold/pool.csv` (both course texts, and which strategy and rank
  found the pair) plus an empty `data/gold/llm_prelabels.csv` to fill in.
- It refuses to overwrite `llm_prelabels.csv` once it exists. That file is the frozen
  record the correction rate is measured against, and a re-run must not quietly replace it.
- Trial run against the Twente sample: 45 pairs over 5 home courses, 9 per course. With
  the real 40-course catalogue and 40 home courses, expect 500 to 600 pairs, which
  matches the estimate in `docs/03-data-schema.md`.

### Broken / known issues
- Nothing in lane A can now progress without the real Twente file. `S5-A0` needs it to
  pool against, `S5-A1` needs the pool, `S5-A3` needs the labels, and stage 6 starts by
  ingesting another university, which would hit the same style checker problem.

### Next
- **A:** waiting on the style checker request to B, the one in the entry of 2026-09-20
  titled "Twente scraper written, its data held back".

---

## 2026-09-20 - [A] The image was baking 724 MB of models, not 220 MB

**Who:** Person A
**Stage:** housekeeping while lane A is blocked
**Commit:** `[A] stop baking duplicate model weights`
**Tasks touched:** none directly. It breaks a rule in AGENTS.md, so it gets fixed now.

### The problem
`backend/scripts/download_models.py` pulled whole repositories minus a few formats.
Hugging Face repositories publish the same weights several times: `pytorch_model.bin`
next to `model.safetensors`, and MiniLM adds a Rust `rust_model.ot`. Each is the full
model, and torch loads exactly one of them.

| Repository | Was | Now |
|---|---|---|
| `BAAI/bge-small-en-v1.5` | 268 MB | 134 MB |
| `sentence-transformers/all-MiniLM-L6-v2` | 273 MB | 92 MB |
| `cross-encoder/ms-marco-MiniLM-L6-v2` | 183 MB | 92 MB |
| **Total** | **724 MB** | **318 MB** |

AGENTS.md allows ~200 MB per model and 400 MB in total. The build was over both, by a
lot, and nothing checked.

### Done
- The downloader keeps safetensors when a repository has them and skips `.bin`, `.pt`,
  `.pth`, `.ckpt` and `.ot`. Repositories without safetensors are unaffected, since the
  patterns are chosen per repository from its file list.
- It prints each model's size and **exits 1 if one model passes 200 MB or the set passes
  400 MB**, so the build fails rather than the image quietly growing.
- Measured figures are in `docs/02-models.md`, replacing the "~220 MB" estimate.
- `eval/README.md` now covers `make_smoke.py` and says what each script needs.

### Note for B
The image should shrink by roughly 400 MB on the next `docker compose build`. Nothing in
`backend/Dockerfile` changes: it still calls this script the same way.

### Next
- **A:** still blocked on the style checker before the Twente data and the gold set can
  land.

---

## 2026-09-20 - [A] Evaluation harness and metric tests

**Who:** Person A
**Stage:** 5 - Gold set and evaluation, taken early. The harness runs; it has nothing to
measure until the gold set exists.
**Commit:** `[A] finish the evaluation harness`
**Tasks touched:** `S5-A2`, `S5-A4` (done, early), `S5-A3` (wip)

### Done
- `eval/run_eval.py` is implemented. It imports `app.matching` rather than
  reimplementing scoring, runs every configuration in `CONFIGS`, and writes
  `eval/report/results.md` and `results.csv` with Recall@5, Recall@10, MRR@10, nDCG@10,
  P@1 and ms/query.
- Statistics (`S5-A3`): 95 % percentile bootstrap intervals over queries and a paired
  bootstrap test of `hybrid+ce` against `dense-minilm`, both seeded so the report
  reproduces. The report states in words whether each gain is significant, and discloses
  the pre-labelling and the correction rate.
- `backend/tests/test_matching_metrics.py`, 18 tests with values computed by hand,
  including an nDCG worked through for a swapped pair. 79 tests in total, all offline.

### Verified
Run end to end on a throwaway gold file of 12 queries with random labels, writing to a
temporary directory: the table, the intervals, the paired test and the CSV all come out.
The numbers were nonsense by construction, which is the point of the exercise.

### Decisions
- `CONFIG_SETUP` maps a configuration name to (bi-encoder, strategy) in one place, so
  `dense-minilm` cannot silently report numbers produced by bge.
- An empty gold set exits 1 with the task IDs to run, rather than writing an empty report
  that looks like a result.
- The paired test resamples query pairs, not queries independently: both configurations
  answer the same queries, and discarding that pairing would overstate the uncertainty.

### Broken / known issues
- `S5-A3` stays `wip`: the code is written but no real report can be produced until the
  gold set exists, and that needs the real Twente data.

### Next
- **A:** blocked on B for the style checker. `S5-A0` (pooling) and `S5-A1` (labelling)
  both need the real Twente file to be worth doing, and stage 6 starts with ingesting
  Masaryk, which would hit the same checker problem. Waiting.

---

## 2026-09-20 - [A] Cross-encoder reranking, evidence, smoke sheet

**Who:** Person A
**Stage:** 4 - Cross-encoder rerank, taken early. Lane A is now through its stage 3 and
stage 4 gates.
**Commit:** `[A] add cross-encoder reranking and evidence`
**Tasks touched:** `S3-A3`, `S4-A1`, `S4-A2`, `S4-A3`, `S4-A4` (done, early)

### Done
- `matching/reranker.py`: batched `CrossEncoder` over (home, host) pairs, sigmoid-squashed
  to 0..1 inside the module. Nothing outside needs to know it emits logits.
- `strategy="hybrid+ce"`: RRF -> `candidate_top_n` -> rerank -> `top_k`.
- Evidence (`S4-A3`): every course's sentences are embedded once at startup, and the
  evidence for a pair is the most similar sentence pair between the two courses. No model
  call during a request.
- Latency guard (`S4-A4`): a request may score at most 1500 pairs. Candidates past the
  budget keep their fused order, so a huge request degrades instead of hanging.
- `eval/make_smoke.py` writes `eval/report/smoke.md`: 10 home courses x 4 strategies with
  evidence and per-strategy latency. That is `S3-A3`.

### Verified with both real models on CPU
- Startup 24 s, both models loaded. A `hybrid+ce` query is 400 ms; a whole 50-course
  programme is 19.5 s, well inside the 45 s the task asks for. BM25 2 ms, dense under 1 ms.
- Ranking looks right where it matters: Formal languages and automata -> Theory of
  Computation, Computer networks -> Network Systems, Databases 1 -> Data and Information,
  Data structures and algorithms 1 -> Algorithms and Data Structures. The reranker
  separates the winner from the rest far better than cosine does: 21 % against 6 % for the
  runner-up where dense had 82 % against 42 %.
- Evidence reads like an explanation. For Data structures and algorithms 1 it quotes
  "Implementation of various data structures (list, stack, queue...)" against Twente's
  "Fundamental data structures such as lists, trees, heaps, hash tables and graphs".

### Decisions
- The cross-encoder is loaded in `_warm()`, not on first use. Lazily, the first
  `hybrid+ce` request paid 17.5 s for the model load and looked like a hung demo. Startup
  now costs that instead, once.
- `PipelineMatcher` takes an optional `reranker`, so tests inject a fake and CI never
  downloads a model. All 61 tests run offline in 3 s.
- The pair cap lives in `reranker.py` as a constant, not in `Settings`: `app/core/config.py`
  is Person B's file. If it should be configurable, that is a request to B, not an edit.

### Broken / known issues
- Cross-encoder percentages are low in absolute terms (rank 1 often 10 to 30 %) because
  ms-marco was trained on search relevance, not course equivalence. The ranking is sound;
  the number is not meaningful yet. Calibration is `S3-B1`, and the smoke sheet says so
  in its own words.
- The smoke sheet is against the 9-course Twente **sample**. Re-run `eval/make_smoke.py`
  once the real file lands.

### Next
- **A:** `S5-A0`, pooling the pairs worth labelling. That needs the real Twente data to be
  worth doing, so it waits on B's answer about the style checker.

---

## 2026-09-20 - [A] BM25 and hybrid fusion

**Who:** Person A
**Stage:** 3 - Lexical and hybrid, taken early. `S3-A3` (smoke sheet) still open.
**Commit:** `[A] add bm25 and wire hybrid fusion into the pipeline`
**Tasks touched:** `S3-A1`, `S3-A2` (done, early)

### Done
- `matching/lexical.py`: `BM25Index` over the same `build_document()` text the
  bi-encoder embeds, using `rank_bm25.BM25Okapi` with default k1 and b.
- `strategy="hybrid"` in the pipeline: both retrievers return `candidate_top_n` (25),
  fused by `reciprocal_rank_fusion` at `rrf_k` (60).
- The tokenisation is written down in `docs/05-evaluation.md` under "The BM25 baseline,
  exactly as implemented". It is the number everything else is compared against, so it
  has to be reproducible from the document alone.
- `backend/tests/test_matching_lexical.py`, 16 tests, including S3-A2's acceptance:
  fusion never loses a candidate that either input found.

### Verified with the real model
Per home course, top 3, against the Twente sample:

| Home course | bm25 | dense | hybrid |
|---|---|---|---|
| Formal languages and automata | Theory of Computation | Theory of Computation | Theory of Computation |
| Computer networks | Network Systems | Network Systems | Network Systems |
| Databases 1 | Data and Information | Data and Information | Data and Information |

A whole programme (50 home courses, hybrid, top 5) takes 72 ms once warm. BM25 costs
about 2 ms per query, dense under 1 ms.

### Decisions
- No stemming in the tokeniser. It is an ablation worth measuring in stage 5, not a
  default to assume. Same reasoning for leaving k1 and b untuned: a tuned baseline and
  an untuned one are different claims, and the report has to say which one it made.

### Broken / known issues
- **Display scores for bm25 and hybrid are misleading, and this is B's `S3-B1`.** RRF
  scores sit very close together, so ranks 2 and 3 read 96 % and 97 %. BM25 shows
  "English 1" matching a computer science course at 96 %. The ranking is fine; the
  percentage is not. `relative_pct` in pipeline.py is a placeholder that scales against
  the best hit for the same home course, and `S3-B1` replaces both it and
  `score_to_pct` with one calibration.

### Next
- **A:** `S4-A1` the cross-encoder reranker, then `S4-A2` `hybrid+ce`. `S3-A3`, the
  smoke sheet, comes after that so it can cover all four strategies at once.

---

## 2026-09-20 - [A] Dense retrieval works, stage 2 lane A pulled forward

**Who:** Person A
**Stage:** 2 - Dense retrieval, taken early because `S1-A2` is blocked on B.
**Commit:** `[A] implement the bi-encoder embedder and dense retrieval`
**Tasks touched:** `S2-A1`, `S2-A2`, `S2-A3`, `S2-A4` (all done, early)

### Done
- `matching/embedder.py`: loads the bi-encoder lazily, encodes each programme once and
  caches to `data/.cache/{programme}.{tag}.npy` with a sidecar `.json` holding a
  SHA-256 of the concatenated documents. A changed curriculum re-encodes; an unchanged
  one loads in 0.1 s.
- `matching/dense.py`: exact cosine over the normalised matrix (`DenseIndex`). Ties break
  on course order so the eval harness sees a stable ranking.
- `matching/pipeline.py`: `PipelineMatcher` with `strategy="dense"`. Every programme is
  encoded in `__init__`, which runs in the FastAPI lifespan, so no request ever encodes.
  The other three strategies raise NotImplementedError, as planned for this stage.
- `backend/tests/test_matching_dense.py`, 17 tests, no model downloaded: the bi-encoder is
  replaced by a hash-based fake, so CI stays offline and the suite runs in 2 s.

### Verified with the real model (bge-small-en-v1.5, CPU)
- **The lane A gate: "Formal languages and automata" finds "Theory of Computation" at
  rank 1, cosine 0.878.** Computer networks -> Network Systems (0.817), Operating
  systems 1 -> Computer Systems (0.800), Databases 1 -> Data and Information (0.807).
- Cold start 43 s, almost all of it loading the model. Second start 0.1 s from cache.
  Matching all 50 PMF courses against Twente takes under 10 ms once warm.

### Decisions
- `score_to_pct` in pipeline.py is a placeholder until `S3-B1`, which owns calibration.
  Raw cosines here run 0.63 (unrelated) to 0.88 (best pair), so it stretches 0.55 to 0.95
  onto 0 to 100. Without that, "English 1" scored 57 % against a computer science course.
- Embeddings are cached per programme and model tag, so switching `BI_ENCODER` between
  bge-small and minilm does not invalidate the other model's cache. The eval sweep in
  stage 5 needs both.

### Broken / known issues
- Verified against the **sample** Twente file, since the real one is held back (see the
  entry below). The PMF side is real.
- torch 2.5.1 does not import on this Windows machine until `libiomp5md.dll` in
  `torch/lib` is copied to `libomp140.x86_64.dll`, and `transformers` picks the
  TensorFlow path unless `USE_TF=0` is set. Both are local environment quirks, not the
  project's: the Docker image is Linux and unaffected.

### Next
- **A:** `S3-A1` BM25, then `S3-A2` hybrid fusion. Both are in my lane and need nothing
  from B.

---

## 2026-09-20 - [A] Twente scraper written, its data held back

**Who:** Person A
**Stage:** 1 - Real data, real surface. Lane A gate still open: `S1-A2` is blocked.
**Commit:** `[A] add the twente osiris scraper`
**Tasks touched:** `S1-A2` (blocked)

### Done
- `backend/scripts/scrape_utwente.py`. Osiris is a single-page app over a JSON API, found
  by watching the requests the app makes:
  - `POST /student/osiris/student/cursussen/zoeken` lists courses, filtered by
    `collegejaar` and `coordinerend_onderdeel_oms`.
  - `GET /student/osiris/owc/cursussen/{id}` returns one course, with Content
    (`item-inhoud-3`) and Aim(s) (`item-inhoud-4`) as HTML.
  - Both answer HTTP 500 unless the request carries a `taal: EN` header. That header is
    the whole trick; everything else is a normal JSON request.
- Run against 2025-2026 it produces 40 courses, 213 ECTS, every one with a description,
  and `validate_curricula.py` passes on it.

### Decisions
- **Scraping 2025-2026, not 2026-2027.** Osiris publishes a year one quartile at a time.
  As of today the 2026-2027 catalogue has 9 of year 1's units; 2025-2026 has all of them
  (Diamonds, Software Systems, Network Systems, Data & Information).
- Superseded units stay in the catalogue for resits. Units whose content says "only for
  repeat students" are dropped, and where a title is still listed twice the earliest study
  year wins, then the newest code.
- Osiris does not say which units belong to a programme's curriculum, only which
  department coordinates them. So the file covers the units TCS coordinates. The
  mathematics line, run by Applied Mathematics, is missing. Worth stating at the defence:
  it makes the Twente side smaller than the real programme.

### Request to B
- `scripts/check_style.py` applies the banned-word list to `data/curricula/*.json`. The
  Twente course text hits one of the banned connectives 6 times (the one meaning "in
  addition", which the checker names). That text is the university's, quoted as
  published (`docs/03-data-schema.md`), so it cannot be edited to suit our style rules.
  Please skip the banned-word and sentence-pattern checks for `data/curricula/`, keeping
  the ASCII check. **Until then the scraped file is held back** and the sample Twente file
  stays committed, so CI stays green. Re-running the scraper writes the real file in a few
  seconds; nothing needs to be scraped again.

### Broken / known issues
- `data/curricula/utwente-tcs-bsc.json` is still the 9-course sample. Anyone evaluating
  against Twente before this unblocks is measuring against placeholder data.

### Next
- **A:** waiting on B for the checker. Meanwhile pulling stage 2 lane A forward
  (`S2-A1` embedder, `S2-A2` dense search), marked `early`.

---

## 2026-09-19 - [A] Curriculum validator

**Who:** Person A
**Stage:** 1 - Real data, real surface
**Commit:** `[A] add the curriculum validator`
**Tasks touched:** `S1-A3` (done)

### Done
- `backend/scripts/validate_curricula.py`: checks every `data/curricula/*.json` (or the
  files named on the command line) against `docs/03-data-schema.md`. It checks field
  presence and types, with no nulls in string or list fields, and that `programme_id`
  equals the file name. It also rejects duplicate codes, non-ASCII codes, non-positive
  ECTS and prerequisites that name no course in the programme. Standard library only.
- `backend/tests/test_matching_curricula.py`: the committed PMF file validates and meets
  the S1-A1 bar, and each broken variant (duplicate code, null description, renamed
  file, dangling prerequisite) is caught.

### Broken / known issues
- The validator currently exits 1, on purpose: `utwente-tcs-bsc.json` is still the sample
  with `scraped_at: null`. It goes green when `S1-A2` replaces that file.

### Request to B
- Add `python backend/scripts/validate_curricula.py` as a step in the `backend` job of
  `.github/workflows/ci.yml`, after `S1-A2` lands. Adding it before then turns CI red on
  the Twente sample.

### Next
- **A:** `S1-A2`. After it, lane A passes its stage 1 gate.

---

## 2026-09-19 - [A] Real UNS PMF curriculum, 50 courses

**Who:** Person A
**Stage:** 1 - Real data, real surface. Lane A is not through its gate yet: `S1-A2` and
`S1-A3` remain.
**Commit:** `[A] scrape the full uns pmf informatics curriculum`
**Tasks touched:** `S1-A1` (done)

### Done
- `backend/scripts/scrape_uns_pmf.py`: reads the three course tables on the PMF programme
  page, downloads each course's syllabus PDF into `data/.cache/uns-pmf-pdf/` (one request
  per second) and writes `data/curricula/uns-pmf-informatics-bsc.json`. `--offline`
  re-parses the cache without touching the network.
- `data/curricula/uns-pmf-informatics-bsc.json` replaced: 50 courses, every one with a
  description (objectives plus syllabus text) and learning outcomes. The loader reports
  `uns-pmf-informatics-bsc 50`, which meets the >= 45 criterion.
- `data/gold/gold_pairs.csv` cut to its header. The 10 placeholder rows pointed at sample
  codes (`I102`, `I307`, ...) that do not exist in the real curriculum.
- Notes on the source and its quirks in `docs/01-universities.md`; `data/README.md`
  updated.

### Decisions
- Kept all 50 courses, including English, Sociology and the finance electives. Dropping
  them would leave 43, under the acceptance bar, and a student can ask to have them
  recognised as well.
- Course codes changed from the sample scheme to the real one (`I021` Data structures and
  algorithms 1, `I142` Formal languages and automata). Anything that hardcoded a sample
  code needs the real one.
- `description` = learning objectives + syllabus, `learning_outcomes` = the minimum and
  desirable outcomes, `topics` = `[]`. The PDFs have no topic list, and inventing one
  would break the "store as published" rule.
- Scraper dependencies (`requests`, `beautifulsoup4`, `pypdf`) live in
  `backend/scripts/requirements-scrape.txt`, not in the image. They never ship, so no ADR.

### Broken / known issues
- `pypdf` splits a few words ("databas e", "appr iate"); 52 such fragments across 50
  files. Left as extracted. The bi-encoder tolerates them; BM25 will miss those tokens.
- Electives have `year` and `semester` null, because the source gives none.

### Next
- **A:** `S1-A2` Twente scraper, then `S1-A3` the validator. Those close lane A.

---

## 2026-09-18 - [B] Offline run verified. Lane B gate for stage 1 passed

**Who:** Person B
**Stage:** 1 - Real data, real surface. **Lane B gate passed.** Stage stays open until
lane A passes; A is on `S1-A1`.
**Commit:** `[B] drop the syntax directive and document the offline story`
**Tasks touched:** `S1-B2` (done)

### Verified on a real machine
Two runs. First, built with `MATCHER_IMPL=real` and `BAKE_MODELS=1`: the models
downloaded into the image in 34 s, the healthcheck went green and the nginx proxy served
the API same-origin. Then the network was disconnected and the stack started cold with
`docker compose up`, no `--build`:

- both containers started with no registry lookup,
- `loaded 2 programmes (19 courses) from /srv/data/curricula`,
- the backend healthcheck passed and compose reported the container healthy,
- the UI loaded at :8080 and `/programmes`, `/strategies`, `/health` and two
  `POST /match` calls all returned 200.

That is the acceptance criterion met with nothing reaching the network.

### Two findings

**1. `# syntax=docker/dockerfile:1` broke the offline build.** BuildKit resolves that
frontend image from Docker Hub on every build, so with the network off the build failed
before it reached a single instruction. We use nothing the built-in Dockerfile frontend
lacks, so the directive is removed from both Dockerfiles.

**2. The acceptance criterion for `S1-B2` was impossible as written.** It asked for
`docker compose up --build` to work with no network, but pip, npm and the model download
all need it. Only the *run* can be offline. Criterion rewritten: build once with the
network, then `docker compose up` without `--build` serves with the network disconnected.
The README now separates the two explicitly and gives the recipe for proving it.

### Also
- `GET /` on port 8000 returned a bare 404. It now redirects to `/docs`.

### Broken / known issues
- `MATCHER_IMPL=real` currently logs `NotImplementedError: S2-A3` and falls back to the
  stub. That is the fallback working as designed, not a fault: `PipelineMatcher` is
  Person A's stage 2 task. It does mean one thing is still unproven, namely that
  **loading real models offline** works, because there is no code loading them yet. Once
  `S2-A3` lands, repeat the offline check before calling it settled.

### Next
- **B:** stage 1 lane B is done. Next in my lane is `S2-B1` (strategy selector), which I
  can start early while A works on the curricula.
- **A:** `S1-A1`, then `S1-A2` and `S1-A3` to close the stage.

---

## 2026-09-18 - [B] Stage 1 lane B: the UI happy path and the curriculum browser

**Who:** Person B
**Stage:** 1 - Real data, real surface
**Commit:** `[B] finish the ui happy path and the curriculum browser`
**Tasks touched:** `S1-B1` (done), `S1-B3` (done), `S1-B2` (in progress)

### Done
- Split `App.tsx` into `ProgrammePicker`, `ResultsTable` and `CourseBrowser`. `App.tsx`
  is now a state machine with four phases: booting, ready, matching, failed.
- `lib/api.ts`: added `health()` and `courses()`, and gave every call an abort-based
  timeout. 20 s for the small endpoints, 150 s for `/match`, because a whole programme
  through the cross-encoder is slow by design. Network failures and aborts turn into
  sentences a person can act on rather than "Failed to fetch".
- Match runs show elapsed seconds, so a 40-second request does not read as a hang.
- Three states that used to fail silently now say what is wrong: fewer than two
  curricula loaded (names the `DATA_DIR` and the mount), the same programme picked on
  both sides, and the backend running the stub (says which two lines of `.env` to change).
- `CourseBrowser` (`S1-B3`) lists a programme's courses with expandable descriptions and
  **counts the courses whose description is empty**, listing their codes. That is exactly
  `S1-A1`'s acceptance criterion, so Person A can see his ingestion pass or fail in the
  browser without touching the matching code.
- A swap button between the two dropdowns, and a footer showing backend version, active
  matcher and whether models are loaded.
- `frontend/Dockerfile` now copies `package-lock.json` and runs `npm ci` instead of
  `npm install`, so the image build is reproducible.
- The config path fallback logs at debug rather than warning: it fires during
  `docker build`, before the data volume exists, and a warning there is misleading.

### Verified
- `ruff check backend eval scripts`, `scripts/check_style.py`, 11 backend tests, `tsc`
  and `npm run build` all clean.
- Drove the built bundle in a headless browser against mocked API responses: the stub
  warning, the footer, the browser panel and its empty-description warning, the
  same-programme guard disabling the button, the busy label, the elapsed timer, the
  results table, the "no candidate" row and the evidence panel. No console errors.

### Broken / known issues
- `S1-B2` is not finished. Everything in the repository is in place, but nobody has yet
  run the real build with `BAKE_MODELS=1` and confirmed the container serves with the
  network disconnected. That run is the remaining work, and it cannot be done from CI
  because CI builds with `BAKE_MODELS=0`.

### Next
- **B:** `S1-B2`, the offline build verification.
- **A:** `S1-A1`. The browser panel will tell you whether the descriptions came through.

---

## 2026-09-18 - [B] Fix the lint failure CI caught, and close the gap that let it through

**Who:** Person B
**Stage:** 1. Housekeeping.
**Commit:** `[B] fix E501 in fusion.py and lint eval and scripts in ci`
**Tasks touched:** none

### Done
- `backend/app/matching/fusion.py` had a 144-character docstring first line, left behind
  when the task IDs were renamed to stage IDs. Split across two lines.
- The real problem was that the documented pre-commit list in `README.md` deliberately
  left `ruff` out and said "CI runs the same three plus `ruff check backend`". Nothing
  local caught it. `ruff` is now in the local list and in the definition of done in
  `AGENTS.md`.
- CI linted only `backend`. It now lints `backend eval scripts`, so `eval/run_eval.py`
  and `scripts/check_style.py` are covered too. Both pass.

### Decisions
- Whatever CI runs, the README tells you to run locally, in the same order and with the
  same arguments. A check that only exists in CI is a check nobody runs before pushing.

### Next
- **B:** `S1-B1`, then `S1-B2`.
- **A:** `S1-A1`.

---

## 2026-09-18 - [B] Second consistency pass

**Who:** Person B
**Stage:** 1. Housekeeping, no stage movement.
**Commit:** `[B] second consistency pass`
**Tasks touched:** none

### Done
Eight more disagreements, found by reading the remaining docs end to end and by an
automated cross-check of referenced paths, task IDs and model names.

- `eval/README.md` still said `results.csv` is git-ignored, one commit after it stopped
  being ignored, and `S5-B3` reads that file from the repository.
- `CONTEXT.md` section 10 still described stage 5 as ">=100 labelled pairs". It is ~500
  checked pairs over 40 home courses.
- `CONTEXT.md` stage 0 row ended with a stray "done" left over from the emoji removal.
- `S5-A0` said ~400 pairs while `S5-A1` and `docs/05-evaluation.md` said ~500.
- Stage 5 lane B listed `S5-B1` above `S5-B0`, and `S5-B0` had a status in its
  acceptance-criterion column. It is now `done (early)`, which is what the rule in
  `TASKS.md` actually prescribes for pulled-forward work.
- `docs/02-models.md` showed a Dockerfile snippet that predated `BAKE_MODELS`.
- `AGENTS.md` capped models at "~500 MB on disk", which read as if it applied to the
  Colab-only models too. It now caps what is baked into the image: ~200 MB per model,
  under 400 MB in total, with bigger models allowed in `notebooks/`.
- One aphoristic sentence in `docs/05-evaluation.md` that section 11 bans.

Also added, because both will be asked about:

- A short **"On Lucene"** note in `CONTEXT.md` section 3 and in
  `docs/02-models.md`: the assignment allows Lucene or transformers, we took the
  transformers branch, and BM25 here is `rank_bm25` rather than Lucene or PyLucene.
  BM25 is the ranking function Lucene is known for, so the question will come up.
- `eval/report/.gitkeep`, so the directory survives a clone.
- `docs/00-map.md` had no owner in section 7. It is shared.

### Verified
- `scripts/check_style.py` clean, 11 backend tests pass, `tsc` and `npm run build` clean.
- Both curricula parse and carry the required fields; `gold_pairs.csv` has exactly the
  four agreed columns and no course id that is missing from the curricula.
- `load_gold()` returns only checked rows; `correction_rate()` runs.
- Every task ID referenced anywhere in the repository exists in `TASKS.md`.
- Every model id in the docs is either in `config.py` or explicitly marked Colab-only.
- `BAKE_MODELS`, `MATCHER_IMPL`, `DATA_DIR` and `VITE_API_BASE` agree across
  `.env`, `.env.example`, `docker-compose.yml` and both Dockerfiles.

### Next
- **B:** `S1-B2`, then `S1-B1`.
- **A:** `S1-A1`.

---

## 2026-09-18 - [B] Consistency audit across the repository

**Who:** Person B
**Stage:** 1. Housekeeping, no stage movement.
**Commit:** `[B] reconcile docs and code after the gold-set redesign`
**Tasks touched:** none

### Done
Nine places where the repository disagreed with itself, all found by reading the docs
against the code rather than by anything failing.

- **Embedding cache path.** `docs/02-models.md` said `data/curricula/*.npy` and
  `CONTEXT.md` said "next to the curriculum", while `embedder.py`, `TASKS.md` and
  `.gitignore` all said `data/.cache/`. Following the docs would have written generated
  `.npy` files into the committed curricula directory. All now say `data/.cache/`.
- **Recall@25.** Listed as a primary metric, but a depth-10 pool cannot support it.
  Primary metric is now Recall@10; Recall@25 is a depth-25 subset spot check, kept out
  of the main table. Fixed in `docs/05-evaluation.md`, `eval/run_eval.py` and `TASKS.md`.
- **`eval/run_eval.py` ignored `checked`.** It would have mixed unread machine proposals
  into the metrics. It now skips them and reports how many it skipped.
- Added `correction_rate()` to the same file: diffs `llm_prelabels.csv` against the
  checked labels. That number is what the report quotes as evidence of the human pass.
- **`scripts/`** had no owner in `CONTEXT.md` section 7. It is Person B's.
- **`eval/report/*.csv` was git-ignored** while `S5-B3` plans to read `results.csv` from
  the repository to render the evaluation page. Results are a deliverable, so they are
  committed now.
- **`frontend/Dockerfile` never declared `ARG VITE_API_BASE`**, so the build argument
  compose passes was silently discarded. Declared, defaulting to `/api/v1`.
- `data/README.md` listed only one of the three gold files.
- Repository maps in `README.md` and `AGENTS.md` were missing `tools/`, and `TASKS.md`
  was still described as a backlog rather than a staged board.

### Decisions
- Generated artefacts never live in a committed data directory. `data/curricula/` is
  source, `data/.cache/` is derived.
- A metric goes in the main table only if the pool depth we actually label supports it.

### Next
- **B:** `S1-B2`, then `S1-B1`.
- **A:** `S1-A1`.

---

## 2026-09-18 - [B] Annotation tool, and a smaller gold-set schema

**Who:** Person B
**Stage:** 5 work pulled forward (lane B), marked `early`. Current stage stays 1.
**Commit:** `[B] add the gold-set annotator`
**Tasks touched:** `S5-B0` (done), `S5-A1` unblocked

### Done
- `tools/annotate.html` plus `tools/annotate.js`: a standalone `file://` page that loads
  the curricula JSON and the pairs CSV, shows the two courses side by side with
  descriptions, outcomes and topics, and labels them from the keyboard. `0` `1` `2` set
  the label, `Enter` accepts and advances, `Ctrl+S` saves.
- Saving uses the File System Access API, so in Chrome and Edge it writes straight back
  to `gold_pairs.csv`. Elsewhere it downloads a copy. Loading `llm_prelabels.csv` clears
  the write handle, so the frozen pre-label file can never be overwritten.
- Local storage keeps a backup of checked rows between sessions, wrapped in try/catch
  because it is a convenience and not the file.
- The header tracks checked and corrected counts live. The corrected count is the number
  the report quotes.
- Dropped the `note` column from `gold_pairs.csv`. Four columns now:
  `home_uid,host_uid,label,checked`. Reasoning about a correction belongs in the error
  analysis, not in a column nobody reads back.
- `docs/05-evaluation.md` gained a "How many rows" section: 40 home courses and about
  500 pairs is the target, 25 courses and 320 pairs the minimum, with what that does to
  the confidence intervals.

### Decisions
- The tool is a local page rather than a route in the application. It is evaluation
  tooling, not product, and it must not need Docker or a running backend.
- `tools/**` belongs to Person B in `CONTEXT.md`, even though Person A is the only user.

### Broken / known issues
- `[hidden]` needed `display:none !important` because `#setup` sets `display:grid`, which
  beats the user-agent rule. Fixed, but worth remembering in the React app too.

### Next
- **B:** back to `S1-B2`, then `S1-B1`.
- **A:** `S1-A1`. `S5-A1` is ready whenever the pool exists.

---

## 2026-09-18 - [B] Configure everything through .env

**Who:** Person B
**Stage:** 1 - Real data, real surface
**Commit:** `[B] move runtime switches into .env`
**Tasks touched:** `S1-B2` (in progress)

### Done
- `.env` is now the only place runtime switches live. `MATCHER_IMPL` and the new
  `BAKE_MODELS` both go there, and every documented command is a plain
  `docker compose up --build`.
- `.env.example` ships with the fast pair, `MATCHER_IMPL=stub` and `BAKE_MODELS=0`, and
  explains what to change for the real pipeline.
- `Settings` reads `backend/.env` and then the repository root `.env`, so the same file
  configures both `docker compose` and a local `uvicorn app.main:app --reload`. Before
  this, a local run ignored the root file and silently fell back to `real`.
- Removed the bash-only `VAR=x command` prefixes from the README. They do nothing in
  PowerShell or CMD, which is what we are both on.

### Decisions
- No runtime switch gets documented as a command-line prefix. If it is configuration, it
  goes in `.env`. CI is the exception and sets real environment variables, which override
  the file.

### Next
- **B:** finish `S1-B2`, then `S1-B1`.

---

## 2026-09-18 - [B] Fix empty programme list inside Docker

**Who:** Person B
**Stage:** 1 - Real data, real surface. Unblocks anyone running the stack.
**Commit:** `[B] resolve data dir correctly inside the image`
**Tasks touched:** `S1-B2` (in progress)

### The bug
`app/core/config.py` computed `REPO_ROOT` as `Path(__file__).parents[3]`. From a
checkout that is the repository root, so everything worked locally and all tests passed.
Inside the image the application lives at `/srv`, so `parents[3]` is `/` and `data_dir`
became `/data` - which is the SQLite volume, not the curricula mount at `/srv/data`.
`CurriculumStore.reload()` found no directory, returned silently, and the API served an
empty programme list. The dropdowns were empty and nothing in the logs said why.

### Done
- `config.py` now derives `BACKEND_ROOT` from `parents[2]` (the application root in both
  layouts) and picks whichever of `<app root>/data` and `<app root>/../data` actually
  contains `curricula/`. `DATA_DIR` overrides it.
- `cache_dir` and a new `gold_dir` derive from `data_dir` instead of being separate
  defaults that could point somewhere else.
- `docker-compose.yml` pins `DATA_DIR=/srv/data` next to the `./data:/srv/data` mount, so
  the setting and the mount cannot drift apart.
- `CurriculumStore.reload()` logs an error naming the directory it looked in when it
  finds nothing, and logs the programme and course count when it succeeds.
- Added `backend/tests/test_api_config_paths.py`: both directory layouts plus an
  assertion that the resolved curricula directory exists and holds JSON.
- `Dockerfile` takes `BAKE_MODELS` (default 1). CI builds with `BAKE_MODELS=0` so the new
  `smoke` job can start the whole stack in about a minute.
- New CI job `smoke`: builds, starts compose, waits for the healthcheck, and fails unless
  `/api/v1/programmes` returns at least two programmes and the frontend answers on :8080.

### Decisions
- Walking a fixed number of parents to find the project root is banned. Derive paths from
  the application root and verify the directory exists.
- Any bug that only appears inside the image needs a test that runs inside the image.
  That is what the `smoke` job is for.

### Broken / known issues
- Adding the `BAKE_MODELS` argument changes the model-download layer, so the next full
  build re-downloads the models once. Builds after that are cached again.

### Next
- **B:** finish `S1-B2` (healthcheck timings, offline verification), then `S1-B1`.

---

## 2026-09-18 - [SETUP] Writing-style pass over the whole repository

**Who:** initial scaffold (bootstrap)
**Stage:** 0 (Scaffold), follow-up. Does not change the stage.
**Commit:** `normalise repository text to ascii and add a style check`
**Tasks touched:** none

### Done
- Every text file in the repository is now plain ASCII. Em dashes and en dashes became
  hyphens, curly quotes became straight quotes, the ellipsis character became three dots,
  arrows and maths symbols became `->`, `>=`, `~`, `x`.
- The box-drawing diagrams in `CONTEXT.md` and `README.md` were redrawn with `+ - | v`.
- Status markers in `TASKS.md` are words (`todo`, `wip`, `blocked`, `done`, `early`) and
  `[ ]` / `[x]` checkboxes instead of coloured squares and check marks.
- Rewrote the sentences that read as machine-generated: aphoristic paragraph endings,
  negation-then-reveal constructions, and marketing adjectives.
- Added `CONTEXT.md` section 11 (Writing style) with the character rules, the banned
  word list, the banned sentence patterns, and the formatting and commit-message rules.
- Added `scripts/check_style.py`, which enforces all of it, and a `style` job in CI.

### Decisions
- The pipeline steps inside `CONTEXT.md` are now called steps 0-3, not stages, so they
  no longer collide with the project stages in `TASKS.md`.
- British spelling throughout.

### Next
- Unchanged: Stage 1. A starts `S1-A1`, B starts `S1-B1`.

---

## 2026-09-18 - [SETUP] Repository scaffold - closes Stage 0

**Who:** initial scaffold (neither A nor B - bootstrap)
**Stage:** 0 (Scaffold) -> closed. Current stage is now **1 - Real data, real surface**.
**Commit:** `initial scaffold`
**Tasks touched:** Stage 0 complete; stages 1-7 laid out in `TASKS.md`

### Done
- Created the agent-facing docs: `AGENTS.md`, `CONTEXT.md`, `PROGRESS.md`, `TASKS.md`.
- Wrote `docs/01-universities.md` (partner shortlist + catalogue sources),
  `docs/02-models.md` (Hugging Face model choices), `docs/03-data-schema.md`
  (curriculum JSON schema), `docs/04-api-contract.md` (frozen REST contract),
  `docs/05-evaluation.md` (gold set + metrics protocol), and two ADRs.
- Scaffolded `backend/` (FastAPI app, routers, schemas, `Matcher` protocol,
  `StubMatcher`, empty real-pipeline modules), `frontend/` (React + Vite),
  `eval/`, `docker-compose.yml`.
- Added two sample curriculum files so the stub path returns something visible.

### Verified
- `pytest backend/tests` - 8 passed (`MATCHER_IMPL=stub`).
- `POST /api/v1/match` returns a full table end-to-end on the sample curricula; the stub
  already ranks *Data Structures and Algorithms* -> *Algorithms and Data Structures* first,
  so the plumbing is right even though the NLP is not there yet.
- `MATCHER_IMPL=real` correctly logs the missing pipeline and falls back to the stub
  instead of failing to boot - Person B is never blocked by Person A.
- `npm run build` in `frontend/` succeeds; `tsc -b` clean. (`node_modules/` is installed
  locally and git-ignored.)
- Docker images are **not** built yet - that is S1-B2.

### State after this entry
`docker compose up --build` is expected to serve the UI at http://localhost:8080 and the
API at http://localhost:8000/docs. No real model inference yet: every match comes from
`StubMatcher` (character-trigram Jaccard), which exists purely so the contract is exercised.

### Next - Stage 1
- **A:** `S1-A1` ingest the real UNS PMF curriculum -> `S1-A2` Twente -> `S1-A3` validator.
- **B:** `S1-B1` UI happy path -> `S1-B2` offline Docker build -> `S1-B3` course browser.

Neither lane blocks the other: B works against the stub and the sample data until A's
real curricula land, and nothing B does touches `data/` or `matching/`.

---

<!--
ENTRY TEMPLATE - copy from here, fill in, paste directly under the "---" above.

## YYYY-MM-DD - [A|B] Short title

**Who:** Person A | Person B
**Commit:** `<short sha or message>`
**Tasks touched:** T-0xx (done|in progress|blocked)

### Done
- bullet per meaningful change, with file paths

### Decisions
- anything a future agent would otherwise re-litigate. Big ones get an ADR in docs/adr/.

### CONTRACT CHANGE            (omit this section if nothing shared changed)
- what changed in schemas/ or interface.py or docs/04-api-contract.md
- what the other person must do about it

### Request to A|B             (omit if none)
- a change you need in the other person's zone

### Broken / known issues
- anything left failing, so the next agent does not "discover" it and waste time

### Next
- what you intend to pick up next, so the other person does not take it
- if you closed your lane's gate, say whether the stage is now closed or you are
  waiting on the other lane
-->
