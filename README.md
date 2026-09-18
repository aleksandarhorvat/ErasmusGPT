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

That is the whole setup. The first build takes 5 to 10 minutes because it downloads the
models and bakes them into the image, and it pulls about 1 GB (CPU torch wheels plus
roughly 220 MB of models). Every build after that is cached, and the container then runs
**fully offline**: `HF_HUB_OFFLINE=1`, no network needed at run time, no GPU required.

In a hurry, or working on the front end? Skip the models entirely:

```bash
MATCHER_IMPL=stub docker compose up --build
```

The stub returns fake but plausible matches instantly, so the UI, the API and the whole
Docker path can be built and tested before any model exists.

## Working on the code

You need Python 3.11 (3.10 works) and Node 20.

```bash
# backend - terminal 1
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1
pip install -r requirements.txt
MATCHER_IMPL=stub uvicorn app.main:app --reload    # http://localhost:8000

# frontend - terminal 2
cd frontend
npm install
npm run dev                                         # http://localhost:5173
```

The Vite dev server proxies `/api` to port 8000, so the front end uses the same relative
paths in development as it does behind nginx in Docker.

Before every commit:

```bash
python scripts/check_style.py     # writing style, CONTEXT.md section 11
cd backend && MATCHER_IMPL=stub pytest tests -q
cd frontend && npm run build
```

CI runs the same three plus `ruff check backend`.

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
| `TASKS.md` | Backlog |
| `docs/00-map.md` | Diagrams: request path, ownership boundary, stage graph |
| `docs/` | Universities, models, data schema, API contract, evaluation protocol, ADRs |
| `backend/` | FastAPI service and the matching pipeline |
| `frontend/` | React + Vite UI |
| `data/` | Curriculum JSON + the labelled gold set |
| `eval/` | Evaluation harness and report |
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
