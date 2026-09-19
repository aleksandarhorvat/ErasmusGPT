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
