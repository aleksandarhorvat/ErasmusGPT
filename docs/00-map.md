# Project map

One page to orient a new reader or a fresh agent. The authoritative board is
`TASKS.md`; this file is the picture of it.

## Request path and the ownership boundary

```mermaid
flowchart TD
  subgraph B["Person B - service and platform"]
    UI["React results table<br/>frontend/src/App.tsx"]
    NGX["nginx :8080<br/>same-origin proxy"]
    API["FastAPI router + pydantic<br/>app/api/routes_match.py"]
  end

  CONTRACT{{"FROZEN CONTRACT<br/>Matcher protocol + MatchResponse"}}

  subgraph A["Person A - matching engine and data"]
    DOC["build course document<br/>title + description + outcomes + topics"]
    BM["BM25<br/>rank_bm25"]
    DEN["bi-encoder cosine<br/>bge-small-en-v1.5, 384-d"]
    RRF["Reciprocal Rank Fusion<br/>k = 60"]
    CE["cross-encoder rerank<br/>ms-marco-MiniLM-L6-v2<br/>(selectable, not the default)"]
    OUT["top 5 + score + confidence<br/>+ ECTS delta + evidence"]
  end

  STORE[("loaded once at startup<br/>curricula JSON, .npy cache, baked models")]

  UI -->|"POST /api/v1/match"| NGX --> API --> CONTRACT
  CONTRACT -->|"match_programme()"| DOC
  DOC --> BM --> RRF
  DOC --> DEN --> RRF
  RRF -->|"top 25"| CE --> OUT
  OUT --> CONTRACT
  CONTRACT -.->|"MatchResponse"| UI
  STORE -.-> DEN
```

Only a pydantic model and a protocol method cross the boundary. Person B builds the
whole surface against `StubMatcher`; Person A replaces it behind the same two methods
without touching a file Person B owns.

## Stages and lanes

Each stage has two lanes that never touch the same files. A stage closes when both
lanes pass their gate. Per-task detail is in `TASKS.md`.

```mermaid
flowchart LR
  S0["Stage 0<br/>Scaffold<br/>(closed)"]

  S1A["1A data<br/>UNS PMF + Twente<br/>curricula, validator"]
  S1B["1B surface<br/>UI happy path,<br/>offline Docker build"]
  S2A["2A dense<br/>bi-encoder, .npy cache,<br/>PipelineMatcher"]
  S2B["2B platform<br/>strategy selector,<br/>slow-request UX, SQLite"]
  S3A["3A lexical<br/>BM25, RRF,<br/>smoke sheet"]
  S3B["3B readable<br/>score calibration,<br/>CSV export, re-match"]
  S4A["4A rerank<br/>cross-encoder,<br/>evidence, latency guard"]
  S4B["4B visible<br/>why panel, compare mode,<br/>model footer"]
  S5A["5A evidence<br/>gold set, metrics,<br/>bootstrap CIs"]
  S5B["5B rigour<br/>second annotator,<br/>CI, results page"]
  S6A["6A breadth<br/>more curricula,<br/>error analysis"]
  S6B["6B delivery<br/>README, clean-machine<br/>run, robustness"]
  S7["Stage 7<br/>Defence<br/>slides, offline rehearsal"]

  S0 --> S1A
  S0 --> S1B
  S1A --> S2A --> S3A --> S4A --> S5A --> S6A --> S7
  S1B --> S2B --> S3B --> S4B --> S5B --> S6B --> S7
  S2A -.->|"real matches to display"| S3B
  S4A -.->|"evidence shape"| S4B
  S5A -.->|"results.csv"| S5B
```

The dotted edges are the only cross-lane dependencies in the whole plan, and each one
is against a shape that is already frozen in `app/schemas/`, so neither lane has to wait.

## Who owns what

| Layer | Tool | Owner |
|---|---|---|
| Embeddings | sentence-transformers, `BAAI/bge-small-en-v1.5` | A |
| Baseline | `sentence-transformers/all-MiniLM-L6-v2` | A |
| Lexical | `rank_bm25` | A |
| Fusion | Reciprocal Rank Fusion, k = 60 | A |
| Reranking | `cross-encoder/ms-marco-MiniLM-L6-v2`, selectable, not the default (ADR-0005) | A |
| Vector maths | NumPy exact cosine, no vector database | A |
| GPU work | Colab T4, evaluation sweep and optional fine-tune | A |
| API | FastAPI, uvicorn, pydantic v2 | B |
| UI | React 18, Vite, TypeScript | B |
| Web server | nginx, same-origin proxy | B |
| Persistence | SQLAlchemy 2.0, SQLite | B |
| Packaging | Docker Compose, CPU torch wheels, models baked in | B |
| CI | GitHub Actions: ruff, pytest, frontend build, style check | B |
| Contract | `Matcher` protocol, `app/schemas/` | shared |
| Curriculum schema | `docs/03-data-schema.md` | shared |
