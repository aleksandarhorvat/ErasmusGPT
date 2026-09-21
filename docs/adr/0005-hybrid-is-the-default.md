# ADR-0005 - Hybrid retrieval is the default, and the cross-encoder is a result

**Status:** accepted 2026-09-20, **amended 2026-09-21**. The original reasoning no
longer holds in full: see the amendment at the bottom. Proposed by Person A in `eval/report/ablations.md`,
accepted by Person B. Supersedes the "hybrid+ce is the product" line in `CONTEXT.md`.

## Context

The proposal said cross-encoder reranking would measurably beat naive retrieval, and the
whole architecture was built to demonstrate that. Measured over the pooled labels against
Twente Technical Computer Science, 28 queries:

| Strategy | P@1 | Recall@5 | MRR@10 | ms/query |
|---|---|---|---|---|
| `bm25` | 0.86 | 0.75 | 0.91 | 2 |
| `dense` | 0.75 | 0.77 | 0.81 | <1 |
| **`hybrid`** | **0.86** | **0.80** | **0.90** | 2 |
| `hybrid+ce` | 0.68 | 0.72 | 0.77 | 979 |

Against Twente Applied Mathematics the reranker draws on P@1 and MRR and loses on recall.
Person A tried a shorter query side (P@1 0.54 to 0.68, adopted) and three other rerankers
inside the size budget (`ms-marco-L12` 0.57, `stsb-TinyBERT-L-4` 0.29,
`stsb-distilroberta-base` 0.18). None closes the gap.

The likely cause is task mismatch rather than a defect: `ms-marco` cross-encoders are
trained on short web queries against passages, and both sides here are course
descriptions of about 1400 characters.

## Decision

`hybrid` becomes the default strategy in the API, the schemas and the UI. `hybrid+ce`
stays implemented, selectable and documented, because the comparison is the finding.

The report presents the reranker as a measured negative result with the ablation table as
a central exhibit rather than an appendix.

## Consequences

- Matching a whole programme drops from about 65 s to under a second.
- The calibration in `data/calibration/` is fitted for `hybrid+ce` only, so with
  `hybrid` as the default the recognition panel has no probability to show and says so.
  Refitting for `hybrid` is Person A's `S6-A4`, and it needs `S5-A1` first.
- Every number above comes from machine-written labels that no human has checked. The
  decision is reversible: if `S5-A1` changes the ranking, this ADR is revisited, and if
  fine-tuning in `S6-A3` rescues the reranker the default moves back.
- Honesty is the point. Shipping the slower, worse configuration to protect a claim from
  the proposal would be the wrong call, and an examiner would be right to ask why.

## Amendment, 2026-09-21

Person A found the cause and largely fixed it (`64f949c`). The reranker was **replacing**
the retrieval order rather than joining it. Fused by RRF, the same way BM25 and dense are
fused, it stops being a veto and becomes one opinion among three:

| Twente TCS | P@1 | Recall@5 | MRR@10 |
|---|---|---|---|
| `hybrid` | 0.86 | 0.80 | 0.90 |
| `hybrid+ce`, reranker replaces (the measurement this ADR was written on) | 0.68 | 0.72 | 0.77 |
| `hybrid+ce`, reranker fused (now) | 0.82 | **0.82** | 0.88 |

Against Applied Mathematics the fused version wins on P@1 (0.86) and MRR (0.91).

**So the sentence "it loses on every metric" is no longer true**, and this ADR would be
wrong to keep claiming it. What is still true: the two are close enough to be
indistinguishable on 28 and 22 machine-labelled queries, and `hybrid` matches a whole
programme in 108 ms against about 40 s.

### The decision stands, for a narrower reason
`hybrid` remains the default because it is level and three hundred times cheaper, not
because the reranker is bad. The reranker is no longer a negative result; it is a result
about **how** to combine a reranker, which is a better finding than either.

### One thing this leaves broken
Only `hybrid+ce` has a fitted calibration, so on the default path `score_pct` is not a
probability and the recognition panel now refuses to give a whole-programme estimate
rather than summing display values. Fitting a calibration for `hybrid` closes the gap;
`fit_calibration.py` standardises scores since `64f949c`, so it should be one command.
Until then, the product's headline feature only works on a non-default strategy, which
is the strongest argument for revisiting this ADR once `S5-A1` gives real labels.
