# Hugging Face models

Owner: **Person A**

## Constraints that drove these choices

- **The Docker demo runs on CPU.** One laptop has an AMD RX 6700 XT (no CUDA, and
  ROCm on Windows is not a battle worth fighting); the other GPU is unknown. Assume
  neither exists at demo time.
- **Models are baked into the image at build time.** `HF_HUB_OFFLINE=1` at runtime, so
  a grader with no internet can still run the project. Total model payload target:
  **< 400 MB**.
- **Apache-2.0 or MIT only.** Avoid gated repos (`google/embeddinggemma-300m` is Gemma-
  licensed and requires accepting terms - that breaks an unattended `docker build`).
- A corpus is one study programme: **30-120 courses**. This is tiny. No vector database
  is justified; NumPy cosine over a `(n_courses, dim)` matrix is exact and instant.
  (ADR-0003)

## Chosen stack

### Bi-encoder - candidate retrieval

| Model | Params | Dim | Disk | Role |
|---|---|---|---|---|
| **`BAAI/bge-small-en-v1.5`** | 33 M | 384 | ~130 MB | **Default.** Best BEIR score per megabyte in the small class; encodes a 100-course programme in a couple of seconds on CPU. |
| `sentence-transformers/all-MiniLM-L6-v2` | 22.7 M | 384 | ~90 MB | **Baseline to beat.** The model everyone reaches for first; ~255 M downloads. Reporting "we beat the default choice by X points" is a cleaner story than beating nothing. |
| `Alibaba-NLP/gte-modernbert-base` | 149 M | 768 | ~600 MB | **Optional quality run.** MTEB 64.38, BEIR nDCG@10 55.33, 8192-token context, Apache-2.0. Too big to bake in alongside everything else - run it in Colab for the evaluation table and report the gap. |

Practical notes:

- BGE models want a **query prefix** for asymmetric retrieval
  (`"Represent this sentence for searching relevant passages: "`). This file used to say
  to skip it, on the reasoning that course-to-course matching is symmetric. Measured on
  2026-09-20, that reasoning was wrong: with the prefix on the home side only, Recall@5
  goes from 0.78 to 0.87 against Twente Applied Mathematics and from 0.75 to 0.77 against
  Twente TCS, with P@1 unchanged either way. It is in `embedder.QUERY_INSTRUCTION`, and
  the home side now has its own cached matrix. Re-run the eval if you change it.
- Normalise embeddings once, then cosine similarity is a dot product.
- Cache: `data/.cache/<programme_id>.<model_tag>.npy`, invalidated by a hash of the
  course documents. Never inside `data/curricula/`, which is committed. Encoding must never happen inside a `/match` request.

### Cross-encoder - reranking

| Model | Params | Disk | Role |
|---|---|---|---|
| **`cross-encoder/ms-marco-MiniLM-L6-v2`** | 22.7 M | ~90 MB | **Default reranker.** The community standard (~87 M downloads). Scoring 50 courses x 25 candidates = 1250 pairs takes a few seconds on CPU - fine for a request, fine for a demo. |
| `cross-encoder/ms-marco-MiniLM-L12-v2` | 33 M | ~130 MB | Drop-in upgrade if L6 underperforms and latency allows. |
| `mixedbread-ai/mxbai-rerank-base-v2` | 0.5 B | ~1 GB | **Colab only.** Apache-2.0, BEIR avg 55.57, works with `sentence_transformers.CrossEncoder`. Use it to show the ceiling in the evaluation table; do not ship it in the image. |

Caveat to state in the report: `ms-marco-*` rerankers are trained on
**web search relevance** (short query -> passage), not on **course equivalence**
(long document <-> long document). This file used to add "out of the box they still
help". They do not. Measured on 2026-09-20 they lose to plain `hybrid` retrieval on both
host programmes, and three alternative rerankers inside the size budget are worse still.
See `eval/report/ablations.md`. S6-A3 (fine-tuning on the gold set) is the principled
fix, and now it is the only one left.

### What we are NOT using, and why

- **Lucene or PyLucene.** The assignment allows either base and we chose transformers.
  `rank_bm25` gives us the same ranking function in about 200 lines of Python, with no
  JVM and no index files to ship in the Docker image. With 30 to 120 documents per
  corpus there is nothing for a search engine to do.
- **No generative LLM in the matching path.** It would be slow, unreproducible and
  ungradeable, and it would hide the IR contribution. If a natural-language explanation
  of a match is wanted, produce it extractively: return the sentence pair with the
  highest cross-encoder attribution.
- **No multilingual model.** Both sides are in English by construction (ADR-0001).
  If a partner without English descriptions is added later, reopen this.
- **No FAISS / Qdrant / pgvector.** 120 vectors. NumPy.

## Baking models into the image

`backend/scripts/download_models.py` runs during `docker build`:

```dockerfile
ENV HF_HOME=/models
ARG BAKE_MODELS=1
RUN if [ "$BAKE_MODELS" = "1" ]; then python scripts/download_models.py; fi
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
```

`BAKE_MODELS=0` skips the download so the CI smoke test and stub-only runs build in
about a minute. It is only valid with `MATCHER_IMPL=stub`, because the real pipeline has
nothing to load. Both switches live in `.env`.

The model list lives in one place, `backend/app/core/config.py`, and both the downloader
and the runtime read it from there, so the two cannot drift apart.

Expected image size: base python-slim + torch CPU wheels (~800 MB, the real cost) +
318 MB of models. Use `--index-url https://download.pytorch.org/whl/cpu` for torch so
you do not pull 2.5 GB of CUDA libraries into a CPU-only image.

### What the three baked models actually weigh

Measured on 2026-09-20 from the repository metadata, with the filters
`backend/scripts/download_models.py` applies:

| Repository | Baked | Was |
|---|---|---|
| `BAAI/bge-small-en-v1.5` | 134 MB | 268 MB |
| `sentence-transformers/all-MiniLM-L6-v2` | 92 MB | 273 MB |
| `cross-encoder/ms-marco-MiniLM-L6-v2` | 92 MB | 183 MB |
| **Total** | **318 MB** | **724 MB** |

The "was" column is what the build pulled before S5-A2's clean-up. Hugging Face
repositories publish the same weights several times over: `pytorch_model.bin` next to
`model.safetensors`, and for MiniLM a Rust `rust_model.ot` as well. Each copy is the
full model. The downloader now keeps safetensors where a repository has it and skips
the other formats, and it fails the build if one model passes 200 MB or the set passes
400 MB, so this cannot creep back unnoticed.

## What the measurements say about these choices (2026-09-20)

`eval/report/ablations.md` has the tables, measured on the pre-labels while choosing settings;
`eval/report/results.md` has the final numbers. The short version:

- The **cross-encoder, used to replace the retrieval order, lost to plain hybrid
  retrieval** on both host programmes, by 0.18 of P@1 against Twente TCS. Fused into
  the order by RRF instead (`64f949c`), it is level with `hybrid`, for about 400 times
  the latency. Two rescues were
  tried: a shorter query side (recovers a third of the gap, adopted) and three other
  rerankers inside the budget (all worse, including both sentence-similarity models).
- The **bge query instruction** was missing and is worth up to 0.09 of Recall@5.
- The cross-encoder runs at **256 tokens**, not 512: same P@1, better Recall@5, 2.5
  times faster. Cutting the learning outcomes instead makes everything worse, so the
  outcomes stay in the document.

None of this is settled until the gold set is human-checked (`S5-A1`).

## Where the GPU is actually used

`notebooks/` on Colab free (T4), for:

- the evaluation sweep across all four strategies x three bi-encoders x two rerankers,
- S6-A3 fine-tuning with `MultipleNegativesRankingLoss` on the gold set.

Results come back into the repo as CSV/Markdown in `eval/report/`. The Docker image
never needs a GPU.
