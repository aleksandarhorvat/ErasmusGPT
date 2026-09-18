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
  (`"Represent this sentence for searching relevant passages: "`). Our task is
  *symmetric* (course <-> course), so **encode both sides with no prefix** and say so in
  the report. If you change this, re-run the whole eval - it moves numbers.
- Normalise embeddings once, then cosine similarity is a dot product.
- Cache: `data/curricula/<programme_id>.<model_tag>.npy`, invalidated by a hash of the
  course documents. Encoding must never happen inside a `/match` request.

### Cross-encoder - reranking

| Model | Params | Disk | Role |
|---|---|---|---|
| **`cross-encoder/ms-marco-MiniLM-L6-v2`** | 22.7 M | ~90 MB | **Default reranker.** The community standard (~87 M downloads). Scoring 50 courses x 25 candidates = 1250 pairs takes a few seconds on CPU - fine for a request, fine for a demo. |
| `cross-encoder/ms-marco-MiniLM-L12-v2` | 33 M | ~130 MB | Drop-in upgrade if L6 underperforms and latency allows. |
| `mixedbread-ai/mxbai-rerank-base-v2` | 0.5 B | ~1 GB | **Colab only.** Apache-2.0, BEIR avg 55.57, works with `sentence_transformers.CrossEncoder`. Use it to show the ceiling in the evaluation table; do not ship it in the image. |

Caveat to state in the report: `ms-marco-*` rerankers are trained on
**web search relevance** (short query -> passage), not on **course equivalence**
(long document <-> long document). Out of the box they still help, because "is this text
about the same subject matter" transfers. S6-A3 (fine-tuning on the gold set) is the
principled fix if there is time.

### What we are NOT using, and why

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
RUN python scripts/download_models.py          # snapshot_download of every model in MODELS
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
```

The model list lives in one place, `backend/app/core/config.py`, and both the downloader
and the runtime read it from there, so the two cannot drift apart.

Expected image size: base python-slim + torch CPU wheels (~800 MB, the real cost) +
~220 MB of models. Use `--index-url https://download.pytorch.org/whl/cpu` for torch so
you do not pull 2.5 GB of CUDA libraries into a CPU-only image.

## Where the GPU is actually used

`notebooks/` on Colab free (T4), for:

- the evaluation sweep across all four strategies x three bi-encoders x two rerankers,
- S6-A3 fine-tuning with `MultipleNegativesRankingLoss` on the gold set.

Results come back into the repo as CSV/Markdown in `eval/report/`. The Docker image
never needs a GPU.
