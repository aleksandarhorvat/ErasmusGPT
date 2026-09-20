# ErasmusGPT - Project Context

> Single source of truth. If something here contradicts code, the code is wrong or this
> file is stale - fix one of them in the same commit and note it in `PROGRESS.md`.

## 1. Problem

An outgoing Erasmus student must find, in a foreign university's catalogue, the courses
that their home faculty will recognise in place of their own. Today this is manual:
read a foreign curriculum, guess which course is "the same", write to the academic
coordinator, wait, repeat. It takes days and the criteria are opaque.

## 2. What the system does

Input: a **home study programme** (Faculty of Sciences, University of Novi Sad -
Department of Mathematics and Informatics, BSc Informatics) and a **host study programme**
(one of the European partners in `docs/01-universities.md`).

Output: for each home course, a ranked list of the **top-5 host courses** that are
semantically equivalent, with a similarity score, the ECTS of both sides, and the
evidence (which sentences drove the match).

The user picks two already-imported curricula from a dropdown and gets a table.
No file upload in the MVP.

## 3. Course requirements mapping (do not lose sight of these)

| Requirement | How we satisfy it |
|---|---|
| Based on `transformers` ecosystem | `sentence-transformers` bi-encoder + `CrossEncoder` reranker |
| Main logic behind a web service | FastAPI backend, all matching logic server-side |
| Web UI | React + Vite SPA |
| Dockerised, minimal effort to run | `docker compose up --build`, models baked into the image |
| IR content | BM25 lexical baseline + dense retrieval + reranking + IR metrics (Recall@k, MRR, nDCG@10) |

**On Lucene.** The assignment allows Lucene *or* the transformers ecosystem. We take the
transformers branch. BM25 here is `rank_bm25`, a small pure-Python package used as the
lexical baseline and as half of the hybrid candidate list; it is not Lucene or PyLucene,
and there is no index, no JVM. Worth saying out loud at the defence, because BM25 is the
ranking function Lucene is known for and the question will come up.

## 4. Pipeline

```
home course (title + description + outcomes + topics)
  |
  +-- [step 0] normalise and build the "course document"
  |
  +-- [step 1] CANDIDATE RETRIEVAL over the host programme (fast, recall-oriented)
  |     a) dense:   bi-encoder cosine similarity   (sentence-transformers)
  |     b) lexical: BM25 over the same documents   (rank_bm25)
  |     c) fuse a) and b) with Reciprocal Rank Fusion  -> top-N (N = 25)
  |
  +-- [step 2] RERANKING (slow, precision-oriented)
  |     CrossEncoder scores each (home_doc, host_doc) pair -> top-K (K = 5)
  |
  +-- [step 3] presentation: calibrate the score to 0..100, attach the ECTS delta,
        highlight the best-matching sentence pair as evidence
```

Three retrieval configurations must remain runnable side by side, because the whole
evaluation story is "the cross-encoder measurably beats the naive approach":

- `bm25` - lexical only (naive baseline #1)
- `dense` - bi-encoder only (naive baseline #2)
- `hybrid` - RRF(bm25, dense)
- `hybrid+ce` - RRF then cross-encoder rerank

**`hybrid` is the default** (ADR-0005). The proposal expected `hybrid+ce` to win; measured,
it loses on every metric and costs about 500 times more per query. The reranker stays
implemented and selectable because that comparison is the project's main result. See
`eval/report/ablations.md`.

The configuration is a request parameter (`strategy`) so the UI and the eval harness
hit exactly the same code path.

## 5. Models (details and rationale in `docs/02-models.md`)

| Role | Model | Params | Why |
|---|---|---|---|
| Bi-encoder (primary) | `BAAI/bge-small-en-v1.5` | 33 M | 384-dim, strong BEIR score per MB, ~130 MB on disk, fast on CPU |
| Bi-encoder (baseline) | `sentence-transformers/all-MiniLM-L6-v2` | 22.7 M | The obvious naive choice - we beat it, and say by how much |
| Bi-encoder (optional, quality run) | `Alibaba-NLP/gte-modernbert-base` | 149 M | 8192-token context, MTEB 64.4 / BEIR 55.3, Apache-2.0 |
| Cross-encoder (reranker) | `cross-encoder/ms-marco-MiniLM-L6-v2` | 22.7 M | The standard cheap reranker; ~300 pairs/s on a laptop CPU |
| Cross-encoder (optional) | `mixedbread-ai/mxbai-rerank-base-v2` | 0.5 B | Stronger, Apache-2.0 - only for the Colab evaluation run, not the Docker demo |

Hardware reality: one of us has an AMD RX 6700 XT (no CUDA), the other unknown, plus
Colab free (T4). Therefore **the Docker demo is CPU-only** and every default model is
small enough for that. GPU is used only in `notebooks/` for evaluation sweeps.

## 6. Architecture

```
+---------------+          +--------------------------------------------+
| frontend      |   HTTP   | backend (FastAPI, uvicorn)                 |
| React + Vite  |--------->|   api/       routers, request validation   |
| nginx :8080   |          |   matching/  Matcher protocol + pipeline   |
+---------------+          |   ingest/    curriculum JSON -> DB         |
                           |   db/        SQLAlchemy + SQLite volume    |
                           +--------------------------------------------+
                                       |
                                       | read once, at startup
                                       v
                     +------------------+   +-------------------------+
                     | data/curricula/  |   | /models                 |
                     | *.json           |   | (baked into the image)  |
                     +------------------+   +-------------------------+
```

**Embedding cache.** Course embeddings are computed once per curriculum version and
stored as a `.npy` file under `data/.cache/` plus a row in SQLite. Startup loads
them; a cache miss triggers a one-off encode. Matching a pair of programmes must not
re-encode anything.

**Why SQLite and not Postgres:** the dataset is a few hundred courses. A single file in
a Docker volume keeps `docker compose up` to two services. Revisit only if we add
user accounts. (ADR-0002)

## 7. Ownership zones

Two agents write into this repo. Conflicts are the main risk, so ownership is strict.

### Person A - "Matching engine & data" (the NLP/IR half)
```
data/**
backend/app/matching/**        (except interface.py - shared)
backend/app/ingest/**
backend/scripts/**
eval/**
notebooks/**
docs/01-universities.md
docs/02-models.md
docs/03-data-schema.md
docs/05-evaluation.md
backend/tests/test_matching_*.py
```

### Person B - "Service & platform" (the web half)
```
backend/app/main.py
backend/app/api/**
backend/app/core/**
backend/app/db/**
frontend/**
tools/**
scripts/**                     (repository checks)
docker-compose.yml
backend/Dockerfile
frontend/Dockerfile
.github/**
docs/04-api-contract.md
README.md
backend/tests/test_api_*.py
```

### Shared (change only with a `CONTRACT CHANGE` note in PROGRESS.md)
```
AGENTS.md  CONTEXT.md  PROGRESS.md  TASKS.md  docs/00-map.md
backend/app/schemas/**
backend/app/matching/interface.py
backend/requirements.txt
```

## 8. The contract that lets A and B work in parallel

`backend/app/matching/interface.py` defines a `Matcher` protocol and ships a
`StubMatcher` that returns plausible fake results instantly. B builds the entire API
and UI against the stub from day one; A replaces it with the real pipeline behind the
same protocol. Nothing in `api/` may import from `matching/` except `interface`
and the factory `get_matcher()`.

Switching implementation is one env var: `MATCHER_IMPL=stub|real` (default `real`,
falls back to `stub` with a loud warning if models are missing).

## 9. Conventions

- Python 3.11, FastAPI, pydantic v2. Format with `ruff format`, lint with `ruff`.
- All API paths under `/api/v1`. Responses are pydantic models from `app/schemas/`.
- Typed everywhere. `from __future__ import annotations` at the top of every module.
- Course identity is `f"{institution_id}:{course_code}"` - globally unique, used as the
  primary key everywhere including the gold set.
- Node 20, React 18, TypeScript, plain CSS. No component library. Appearance is
  explicitly not graded - do not spend time there.
- Tests live in `backend/tests/`, named `test_<zone>_<thing>.py`.

## 10. Stages

The work runs in **7 stages**, each with two parallel lanes (A and B) that never touch
the same files. The board, the per-stage tasks and the gates live in `TASKS.md` - that
file is authoritative, this is the one-paragraph summary.

| Stage | What exists at the end of it |
|---|---|
| 0 - Scaffold | repo, docs, frozen contract, stub matcher, compose files (closed) |
| 1 - Real data, real surface | two real curricula, one-command offline Docker run, a table in the browser (matches still fake) |
| 2 - Dense retrieval | the first real NLP: bi-encoder embeddings + cosine, `strategy=dense` |
| 3 - Lexical + hybrid | BM25 baseline, RRF fusion, calibrated scores, CSV export |
| 4 - Cross-encoder rerank | `hybrid+ce` as the default, evidence sentences, side-by-side compare |
| 5 - Gold set + evaluation | ~500 checked pairs over 40 home courses, metrics with confidence intervals, kappa, green CI |
| 6 - Scale out + polish | >=4 host programmes, error analysis, verified clean-machine run |
| 7 - Defence | slides, offline demo rehearsal, who answers which questions |

A stage closes only when **both** lanes pass their gate. If your lane finishes first,
pull your own lane's next-stage tasks rather than crossing into the other lane.

## 11. Writing style

Everything written in this repo - docs, comments, commit messages, PROGRESS entries,
UI copy, the report - follows these rules. They exist because most of the text here is
produced by LLM agents, and LLM prose has a recognisable accent. The examiners read
this repo. Do not give them a reason to wonder who wrote it.

Run `python scripts/check_style.py` before you commit. CI runs it too.

### Characters: ASCII only

| Do not use | Use instead |
|---|---|
| em dash, en dash | a plain hyphen `-`, or split the sentence, or a comma |
| curly quotes and apostrophes | straight `"` and `'` |
| the ellipsis character | three dots `...` |
| arrows, math symbols | `->`, `<->`, `>=`, `<=`, `~`, `x` |
| box-drawing characters | `+`, `-`, `|`, `v`, `>` for ASCII diagrams |
| emoji, check marks, coloured squares | words: `todo`, `wip`, `blocked`, `done`, or `[ ]` / `[x]` |
| the section sign, middle dot, non-breaking space | write the word, or a comma |

Greek letters are allowed in the evaluation report only where they are the standard
notation for a statistic, and only if spelled out on first use ("Cohen's kappa").

### Words that are banned outright

delve, leverage (as a verb), robust, seamless, seamlessly, comprehensive, holistic,
cutting-edge, state-of-the-art, game-changing, elevate, empower, unlock, streamline, foster, embark, journey, realm, landscape, tapestry, testament, showcase,
underscore, myriad, plethora, paramount, pivotal, crucial, vital, meticulous, nuanced,
multifaceted, furthermore, moreover, notably, arguably, ultimately, in essence,
at its core, when it comes to, it is worth noting, in conclusion, at the end of the day.

If a banned word is the only accurate one, you are probably describing the wrong thing.
"important" and "fast" are allowed if you say important to whom and fast compared to what.

### Sentence patterns that are banned

- "It is not just X, it is Y." Also "not merely", "more than just". Say what it is.
- "This isn't a Z. It's a W." Negation-then-reveal. Just state the thing.
- Ending a paragraph on a short aphorism. ("If they can drift, they will.")
- Three items where two would do, purely for rhythm.
- A rhetorical question followed by its own answer.
- A closing paragraph that restates what the section already said.
- "Let's", "we'll", "you'll want to". Write imperatives or plain statements.
- Hedging openers: "generally speaking", "it is important to note that", "essentially".

### Formatting

- Bold at most once per paragraph, and only for a term being defined or a warning.
  Bold every other phrase and none of it registers.
- No emoji anywhere, including commit messages.
- Headings are sentence case and describe content, not vibe. "Evaluation protocol",
  not "Getting the most out of evaluation".
- Tables for things that are genuinely tabular. Prose for reasoning.
- British spelling throughout (normalise, behaviour, catalogue, modelling). Be consistent.

### Code comments

- Say why, not what. `# batch to keep peak RAM under 2 GB` beats `# loop over batches`.
- No comment that restates the function name.
- No "TODO: implement this" without a task ID from `TASKS.md`.
- Docstrings: one line of what it does, then the contract (inputs, outputs, failure
  modes). No sales pitch.

### Commit messages

`[A] ingest twente catalogue`, `[B] bake models into the backend image`.
Prefix, imperative, lowercase, under 60 characters. Body only if the why is not obvious.
No co-author or generator trailers.
