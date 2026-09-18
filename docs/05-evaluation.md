# Evaluation protocol

Owner: **Person A**. The grade depends on this more than on the UI.

## Claim under test

> Cross-encoder reranking of dense+lexical candidates produces measurably better
> course-equivalence matches than the naive approach (cosine similarity over
> `all-MiniLM-L6-v2`, or BM25).

## Setup

- **Queries** = home courses from `uns-pmf-informatics-bsc` that have at least one
  positive label in the gold set.
- **Corpus** = all courses of one host programme. One evaluation run per host programme,
  plus a micro-averaged total.
- **Relevance** from `data/gold/gold_pairs.csv`: label 2 -> relevant, label 1 -> relevant
  for Recall/MRR but graded as 1 for nDCG, label 0 and unlabelled -> not relevant.

## Metrics

| Metric | Why |
|---|---|
| **Recall@5** | The UI shows 5 candidates. Does the right one appear at all? This is the headline number. |
| **Recall@25** | Retrieval-stage ceiling. If this is low, the reranker cannot save you - fix Stage 1 first. |
| **MRR@10** | How near the top is the first correct answer. |
| **nDCG@10** | Uses the graded 0/1/2 labels; rewards ranking a "2" above a "1". |
| **P@1** | "Is the first suggestion right?" - the number a coordinator actually cares about. |
| **Latency (ms/query, CPU)** | The cost of the improvement. Report it; the trade-off is part of the finding. |

## Configurations to report

| Config | Stage 1 | Stage 2 |
|---|---|---|
| `bm25` | BM25 | - |
| `dense-minilm` | all-MiniLM-L6-v2 | - |
| `dense-bge` | bge-small-en-v1.5 | - |
| `hybrid` | RRF(BM25, bge-small) | - |
| `hybrid+ce` | RRF(BM25, bge-small) | ms-marco-MiniLM-L6-v2 |
| `hybrid+ce-large` *(Colab)* | RRF(BM25, bge-small) | mxbai-rerank-base-v2 |
| `dense-gte+ce` *(Colab)* | gte-modernbert-base | ms-marco-MiniLM-L6-v2 |

Output table goes to `eval/report/results.md` and `eval/report/results.csv`, produced
by `eval/run_eval.py`. The script must import the **same** `matching/` code the API
uses. Never reimplement scoring in the eval script - that is how projects end up
reporting numbers their product does not produce.

## Statistical honesty

- ~50 queries is a small sample. Report **95 % bootstrap confidence intervals** over
  queries (1000 resamples) and a **paired bootstrap / permutation test** for
  `hybrid+ce` vs `dense-minilm`. A 3-point gain with overlapping intervals is not a
  result. Say so; hiding it costs more marks than reporting it.
- Fix seeds. Log model revisions (commit hashes from the HF repos) in the report.
- Report the annotation overlap and Cohen's kappa (see `docs/03-data-schema.md`).

## Error analysis (S6-A2)

Take the 10 queries with the worst rank of their best positive and classify each:
granularity mismatch - level mismatch - same-name-different-content -
different-name-same-content - missing description - genuinely no equivalent.

A table of failure categories with counts answers most of the questions an examiner
will ask, and it takes about an hour to produce.

## Ablations worth one line each

- Query prefix on/off for BGE.
- Course document with vs without `learning_outcomes`.
- `top_n` into the reranker: 10 / 25 / 50 - where does Recall@5 stop improving?
- Fine-tuned bi-encoder (S6-A3) vs off-the-shelf.
