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
- API docs: <http://localhost:8000/docs>

Everything is configured in `.env`. Compose reads that file by itself, so you never put
variables in front of the command: `VAR=x docker compose up` is bash syntax and does
nothing in PowerShell or CMD.

`.env.example` ships with the fast settings, `MATCHER_IMPL=stub` and `BAKE_MODELS=0`:
the build takes about a minute, skips the model download, and the app returns fake but
plausible matches. That is what you want for front-end, API and Docker work.

When you want the real pipeline, change two lines in `.env`:

```dotenv
MATCHER_IMPL=real
BAKE_MODELS=1
```

and rebuild. That build takes 5 to 10 minutes and pulls about 1 GB once, because it
downloads the models and bakes them into the image. Builds after that are cached.

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

## Working on the code

You need Python 3.11 (3.10 works) and Node 20.

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
python scripts/check_style.py        # writing style, CONTEXT.md section 11
ruff check backend eval scripts      # lint, including the 100-character line limit
cd backend && pytest tests -q
cd frontend && npm run build
```

CI runs exactly these four, plus a smoke test that starts the whole stack. Run them all
before you push: a docstring one character too long fails the build.

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
| Reranking | `cross-encoder/ms-marco-MiniLM-L6-v2` (22.7 M params) |
| Baseline to beat | `sentence-transformers/all-MiniLM-L6-v2`, cosine only |

All four strategies (`bm25`, `dense`, `hybrid`, `hybrid+ce`) are selectable in the UI and
in the API, and the evaluation harness runs the identical code path. Numbers:
`eval/report/results.md`.

## Repository map

| Path | What |
|---|---|
| `AGENTS.md` | Start here if you are an AI coding agent |
| `CONTEXT.md` | Architecture, contracts, ownership between the two authors |
| `PROGRESS.md` | Running log of what each author did |
| `TASKS.md` | Staged board: project state, per-stage lane A / lane B tasks |
| `docs/00-map.md` | Diagrams: request path, ownership boundary, stage graph |
| `docs/` | Universities, models, data schema, API contract, evaluation protocol, ADRs |
| `backend/` | FastAPI service and the matching pipeline |
| `frontend/` | React + Vite UI |
| `data/` | Curriculum JSON + the labelled gold set |
| `eval/` | Evaluation harness and report |
| `tools/` | `annotate.html`, the gold-set annotator |
| `scripts/` | Repository checks (writing style, curriculum validation) |

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
