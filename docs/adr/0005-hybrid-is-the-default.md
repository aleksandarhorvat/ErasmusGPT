# ADR-0005 - Hybrid retrieval is the default, and the cross-encoder is a result

**Status:** accepted - 2026-09-20. Proposed by Person A in `eval/report/ablations.md`,
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
