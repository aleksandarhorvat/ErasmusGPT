# ErasmusGPT

**Automatic matching of courses for Erasmus exchange.** Pick your home curriculum and a
host curriculum; for every one of your courses the system returns the five most
semantically equivalent courses abroad, ranked, with an ECTS comparison and the evidence
behind the match.

Course project for Information Retrieval + Natural Language Processing.
Built on the `transformers` / `sentence-transformers` ecosystem, served by FastAPI,
with a React front end, packaged with Docker Compose.

## First time on this machine

```bash
git clone https://github.com/aleksandarhorvat/ErasmusGPT.git
cd ErasmusGPT
cp .env.example .env
docker compose up --build
```

- UI: <http://localhost:8080>
- API: <http://localhost:8000/api/v1/health>. The interactive docs at `/docs` load their
  scripts from a CDN, so they need a network connection; `/openapi.json` does not.

The two switches, `MATCHER_IMPL` and `BAKE_MODELS`, are set in `.env`. Compose reads that
file by itself, so you never put variables in front of the command: `VAR=x docker
compose up` is bash syntax and does nothing in PowerShell or CMD. The model names and
candidate depth are pinned in `docker-compose.yml`, because the calibration was fitted
with them.

`.env.example` ships with the fast settings, `MATCHER_IMPL=stub` and `BAKE_MODELS=0`:
the build takes about a minute, skips the model download, and the app returns fake but
plausible matches. That is what you want for front-end, API and Docker work.

When you want the real pipeline, change two lines in `.env`:

```dotenv
MATCHER_IMPL=real
BAKE_MODELS=1
```

and rebuild.

Measured on 2026-09-21 on Windows with Docker Desktop, after `docker system prune -a`:
**the full build takes 5 minutes** (297 s) and pulls about 1 GB. Most of it is the CPU
torch wheel (126 s) and the rest of the Python dependencies (70 s); the models themselves
are 30 s. Builds after that are cached.

First **startup** is slower than the one you will usually see. `data/.cache/` holds the
embeddings and is git-ignored, so a fresh clone has none and the first boot encodes about
756 course vectors (378 courses, document and query side) and about 4100 sentence
vectors before the API answers. The healthcheck
allows five minutes for that. Later starts read the cache and are immediate.

### Offline

Building needs the network: pip, npm and the model download all reach out. **Running does
not.** Build once, then

```bash
docker compose up        # note: no --build
```

works with the network disconnected. Neither Dockerfile carries a `# syntax=` directive,
so BuildKit never asks Docker Hub for a frontend image, and the backend runs with
`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`, so nothing reaches huggingface.co.
No GPU either: CPU only.

To prove it: build, stop the stack, disconnect, `docker compose up`, use the app at
:8080. Running `--build` while disconnected fails, and that is expected.

`python scripts/rehearse_demo.py --start` does the checking part for you: it starts the
stack, times the boot, runs every step of the live demo against the API and fails if
huggingface.co is reachable. The full rehearsal, with the demo script and the fallback
screenshots, is `docs/07-demo-script.md`.

## Working on the code

You need **Python 3.11** and Node 20. 3.10 no longer works: the scrapers and the
evaluation harness import `datetime.UTC`, which 3.11 added.

```bash
# backend - terminal 1
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1
pip install -r requirements.txt
uvicorn app.main:app --reload                       # http://localhost:8000

# frontend - terminal 2
cd frontend
npm install
npm run dev                                         # http://localhost:5173
```

The Vite dev server proxies `/api` to port 8000, so the front end uses the same relative
paths in development as it does behind nginx in Docker.

The backend reads the same `.env`, so `MATCHER_IMPL=stub` there applies here too.

Before every commit:

```bash
python scripts/check_style.py                  # writing style, CONTEXT.md section 11
ruff check backend eval scripts                # lint, including the 100-character line limit
python backend/scripts/validate_curricula.py   # curricula parse and carry the fields
python scripts/check_gold.py                   # gold set is well formed
(cd backend && pytest tests -q)
(cd frontend && npm run build)
```

CI runs exactly these six, plus a smoke test that starts the whole stack. Run them all
before you push: a docstring one character too long fails the build.

## What we found

The project set out to show that cross-encoder reranking beats naive retrieval. On the
final gold set it does not. Against Twente Technical Computer Science (TCS, 27 queries)
and Twente Applied Mathematics (AM, 19 queries):

| Strategy | TCS P@1 | TCS Recall@5 | TCS MRR@10 | AM P@1 | AM Recall@5 | ms/query |
|---|---|---|---|---|---|---|
| `bm25` | 0.85 | 0.74 | 0.89 | 0.79 | 0.78 | 3 |
| `dense-minilm` (baseline) | 0.78 | 0.83 | 0.85 | 0.84 | 0.82 | <1 |
| `dense-bge` | 0.70 | 0.78 | 0.78 | 0.89 | 0.95 | <1 |
| **`hybrid`** (default) | 0.78 | 0.83 | 0.85 | 0.84 | 0.95 | 3 |
| `hybrid+ce` | 0.78 | 0.82 | 0.85 | 0.84 | 0.84 | about 860 |

- **One significant result:** `hybrid` beats the `dense-minilm` baseline on Recall@5
  against AM, +0.13, paired bootstrap p = 0.021. Everything else is level within the
  95 % intervals.
- **The reranker buys nothing measurable** at about 300 times the cost of `hybrid`.
  During development, letting it replace the retrieval order made it the worst strategy;
  fused by RRF like BM25 and dense, it is level. So the finding is about **how** to
  combine a reranker, and `hybrid` is the default because it is level and cheaper.

Full tables with intervals: `eval/report/results.md` and
`eval/report/utwente-am-bsc/results.md`. Reasoning: `docs/adr/0005-hybrid-is-the-default.md`.

**How the labels were made.** Of the 1142 gold pairs, 680 were checked by a person with
the model's proposal shown. For lack of time, the other 462 were labelled by a second
model (Claude) and not checked by a person; `data/gold/provenance.json` records which.
The two humans agree at weighted kappa 0.73, on only 8 shared pairs; Claude against a
human on the 30 cold pairs is 0.52 (`eval/report/kappa.md`). Every report and the app's
"how well does this work?" panel state the split.

## How it works

```
  BM25 candidates  --+
                     +--> Reciprocal Rank Fusion --> top-25 --> cross-encoder --> top-5
  dense candidates --+
```

| Step | Model |
|---|---|
| Dense retrieval | `BAAI/bge-small-en-v1.5` (33 M params) |
| Lexical retrieval | BM25 (`rank_bm25`) |
| Reranking (selectable, not the default) | `cross-encoder/ms-marco-MiniLM-L6-v2` (22.7 M params) |
| Baseline to beat | `sentence-transformers/all-MiniLM-L6-v2`, cosine only |

All four strategies (`bm25`, `dense`, `hybrid`, `hybrid+ce`) are selectable in the UI and
in the API, and the evaluation harness runs the identical code path.

**The default is `hybrid`.** The project set out to show that cross-encoder reranking beats
naive retrieval. Measured, it only helps when fused with the other two rankings rather
than replacing them, and fused it is level with plain `hybrid` at about 300 times the
cost per query. That comparison is the main result rather than a footnote. See "What we
found" above and ADR-0005.

## Repository map

| Path | What |
|---|---|
| `AGENTS.md` | Start here if you are an AI coding agent |
| `CONTEXT.md` | Architecture, contracts, ownership between the two authors |
| `PROGRESS.md` | Running log of what each author did |
| `TASKS.md` | Staged board: project state, per-stage lane A / lane B tasks |
| `docs/00-map.md` | Diagrams: request path, ownership boundary, stage graph |
| `docs/adr/` | The decisions, including ADR-0005 on why `hybrid` is the default |
| `eval/report/` | `ablations.md`, `errors.md`, `smoke.md` |
| `docs/` | Universities, models, data schema, API contract, evaluation protocol, ADRs |
| `backend/` | FastAPI service and the matching pipeline |
| `frontend/` | React + Vite UI |
| `data/` | Curriculum JSON + the labelled gold set |
| `eval/` | Evaluation harness and report |
| `tools/` | `annotate.html`, the gold-set annotator |
| `scripts/` | Repository checks (writing style, gold set), the kappa slice and the demo rehearsal |

## Development without Docker

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1
pip install -r requirements.txt
uvicorn app.main:app --reload

# frontend (second terminal)
cd frontend && npm install && npm run dev
```

## Authors

Person A - matching engine, data, evaluation.
Person B - web service, front end, packaging.
See `CONTEXT.md` section Ownership.
