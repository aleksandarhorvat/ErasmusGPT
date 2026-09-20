# Ablations

What was tried, what it cost, what it bought. Written by Person A on 2026-09-20.

**Read the caveat first.** Every number here comes from `data/gold/llm_prelabels.csv`,
which a model wrote and no human has checked yet (`S5-A1`). They are good enough to
choose between two settings, because both settings are judged by the same labels. They
are not good enough to put in the report as results. Re-run everything after the human
pass; the commands are in each section.

Home programme is UNS PMF BSc Informatics in every run. A query is a home course with at
least one pooled pair labelled 1 or 2, so n is 28 against Twente TCS and 22 against
Twente Applied Mathematics.

## 1. The cross-encoder does not earn its place

This is the project's headline claim, and on the current labels it does not hold.

| Strategy | P@1 | Recall@5 | MRR@10 | ms/query |
|---|---|---|---|---|
| `bm25` | 0.86 | 0.75 | 0.91 | 2 |
| `dense` | 0.75 | 0.77 | 0.81 | <1 |
| **`hybrid`** | **0.86** | **0.80** | **0.90** | 2 |
| `hybrid+ce` | 0.68 | 0.72 | 0.77 | 979 |

Against Applied Mathematics: `hybrid` 0.82 / 0.85 / 0.87, `hybrid+ce` 0.82 / 0.73 / 0.87.
So the reranker is neutral at best on one host and clearly worse on the other, for about
500 times the latency.

The likely reason is a task mismatch rather than a bug. `ms-marco-MiniLM-L6-v2` is
trained on short web queries against passages. Here both sides are 1400-character course
descriptions, and "which passage answers this query" is not the same question as "would a
coordinator accept this course in place of that one".

Two things were tried and did not rescue it (sections 2 and 3).

## 2. What the reranker gets as its query

Shortening only the query side, leaving the host document whole:

| Query given to the cross-encoder | P@1 | Recall@5 | MRR@10 |
|---|---|---|---|
| the whole home document | 0.54 | 0.65 | 0.67 |
| **title + first sentence** | **0.68** | **0.71** | **0.77** |
| title only | 0.68 | 0.58 | 0.75 |
| title + first three sentences | 0.64 | 0.65 | 0.75 |

Adopted: `document.rerank_query()` builds title plus one sentence. It recovers a third of
the gap to `hybrid` and costs nothing.

## 3. Other rerankers inside the size budget

Reranking the same fused candidates, same short query:

| Model | Size | P@1 | Recall@5 | MRR@10 | ms/query |
|---|---|---|---|---|---|
| `ms-marco-MiniLM-L6-v2` (ours) | 92 MB | 0.68 | 0.71 | 0.77 | 979 |
| `ms-marco-MiniLM-L12-v2` | 134 MB | 0.57 | 0.65 | 0.70 | 1841 |
| `stsb-TinyBERT-L-4` | 55 MB | 0.29 | 0.26 | 0.42 | 493 |
| `stsb-distilroberta-base` | 330 MB | 0.18 | 0.32 | 0.33 | 2886 |

The sentence-similarity models are far worse, which is worth knowing: they are trained on
short sentence pairs, and a course description is neither short nor a sentence. Nothing
in the budget beats the L6 model, and nothing beats plain `hybrid`.

## 4. Cross-encoder sequence length

| Window | P@1 | Recall@5 | MRR@10 | ms/query |
|---|---|---|---|---|
| 512 tokens | 0.57 | 0.53 | 0.68 | 3638 |
| **256 tokens** | 0.54 | **0.65** | 0.67 | **1449** |
| 512 tokens, learning outcomes removed | 0.50 | 0.47 | 0.60 | - |

Adopted: 256 tokens. B suggested the gain came from cutting the learning-outcomes block
off the tail; row three tests that directly and refutes it. Removing the outcomes makes
every metric worse, so they carry signal. A shorter window simply trades a little P@1 for
more Recall@5 at 2.5 times the speed.

## 5. The bge query instruction

`bge-small-en-v1.5` is trained with an instruction on the query side of a retrieval pair
and none on the document side. We were encoding both sides identically.

| Host programme | Recall@5 without | Recall@5 with | P@1 |
|---|---|---|---|
| Twente TCS | 0.75 | 0.77 | unchanged at 0.75 |
| Twente Applied Mathematics | 0.78 | 0.87 | unchanged at 0.82 |

Adopted: `embedder.QUERY_INSTRUCTION`, with a second cached embedding matrix per
programme for the query side. It costs one more encode per programme at startup and
nothing per request.

## What this means for the project

The claim in `CONTEXT.md` is that the cross-encoder measurably beats the naive approach.
Measured, it loses to a fusion of two naive approaches. That is a result, not a failure,
and the honest write-up is stronger than the claim would have been: the standard recipe
from IR (retrieve then rerank) was tested on a task it was not trained for, with the
evidence and the reasoning for why.

Three options, for A and B to decide together:

1. **Make `hybrid` the default and report the ablation.** Cheapest, and the numbers
   support it today.
2. **Keep `hybrid+ce` as the default** and present the reranker as the thing that was
   tried and did not work. Harder to defend when the UI ships the slower, worse option.
3. **Fine-tune the reranker** on the gold set (`S6-A3`, Colab). This is the version where
   the claim could survive: a cross-encoder trained on course equivalence rather than web
   search. It needs the human-checked labels first, and it is a day of work.

Nothing should be decided from these numbers alone. They rest on labels the model wrote
about its own behaviour, which is precisely what `S5-A1` exists to fix.
