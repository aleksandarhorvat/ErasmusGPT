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
| **Recall@10** | Retrieval-stage ceiling at the pool depth we actually label. If this is low, the reranker cannot save you - fix Stage 1 first. |
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
uses. Do not reimplement scoring in the eval script: the report would then describe a
system that is not the one being demonstrated.

## Building the gold set

A language model proposes every label, and Person A reads every row and corrects it
where he disagrees. His corrected file is the gold standard; the model's raw output is
kept unedited in a second file so the two can be compared afterwards.

### Why the human pass is not optional

The gold set is the definition of "correct" for this project. If the model's labels went
in unchecked, every number in the report would answer "how closely does bge-small plus a
cross-encoder agree with that model?" rather than "how closely does it agree with an
academic coordinator?" Only the second question is the problem we set out to solve.

There is a circularity problem specific to information retrieval as well. Clarke and
Dietz (2024), *LLM-based relevance assessment still can't replace human relevance
assessment*, show three failure modes: a system can be built to score well against
automatic judgements without retrieving better; system rankings get distorted when the
assessor and the systems being ranked share a model family; and models favour outputs
resembling their own. Our retrievers are transformers trained on overlapping web text,
so a transformer assessor is not an independent referee. A human reading every row is
what breaks that loop.

### The procedure

1. **Pool.** Union of the top 10 from `dense` and `hybrid+ce` per home course, over 40
   home courses. See "How many rows" below. Nobody labels anything outside the pool.
2. **Pre-label.** The model writes `llm_label` and a one-sentence `llm_reason` for every
   pooled pair into `data/gold/llm_prelabels.csv`. Give it the two course documents and
   the rubric below, and nothing else: never the system's scores or ranks, or it anchors
   on them. Commit that file and do not edit it again.
3. **Check.** Open `tools/annotate.html`, load the curricula and the pre-labels, and read
   every row. The proposed label and its reason are shown under the two course cards;
   `0` `1` `2` change it and `Enter` accepts. Only `checked=yes` rows count.
4. **Cold slice.** Person B labels about 30 of the same pairs without seeing any of the
   above, for Cohen's kappa. See `docs/03-data-schema.md`.
5. **Disclose.** Name the model and the date, say that every row was human-checked, and
   report the correction rate.

### The correction rate is a result, not an admission

Diffing the two files gives how often the expert overrode the model, and on which kinds
of pair. "The expert corrected 18 percent of the model's labels, almost all of them
granularity mismatches where a 15-ECTS host module covers two home courses" is a
paragraph and a table row in the report. It also tells the reader exactly how much work
the human pass did, which is the evidence that it was a real pass rather than a rubber
stamp.

### How many rows

The unit of statistical power is the **query**, meaning one home course, not one pair.
Confidence intervals narrow with the number of home courses; extra pairs per course only
make each course's score more precise.

| | Home courses | Pairs to check | Time with `tools/annotate.html` |
|---|---|---|---|
| Target | 40 | ~500 | 60 to 90 minutes |
| Minimum that still supports a claim | 25 | ~320 | 40 to 60 minutes |
| Better, if a second host programme is ingested | 40 x 2 | ~1000 | two sessions |

At 40 queries a 95% bootstrap interval on Recall@5 is roughly plus or minus 0.10, which
is wide but usable. The paired test comparing `hybrid+ce` against `dense` is far more
sensitive than that, because it works on per-query differences over the same queries, so
a real improvement shows up well before the individual intervals stop overlapping.

The metrics above all fit inside a depth-10 pool. Recall@25 does not: it needs a
depth-25 pool, so run that on 10 courses only, report it as a subset spot check on the
retrieval ceiling, and do not put it in the main table.

Most pooled pairs are obvious non-matches, so the real pace is much faster than "read two
full descriptions per pair" suggests. In the annotation tool, accepting a proposed label
is one keystroke.

### Known weakness of this design

Reviewing a suggested label is not the same as forming one. People agree with a proposed
answer more often than they would independently, and the effect is strongest on the hard
pairs, which are the ones that matter most here. Two things limit it: the cold slice in
step 4, which is unanchored by construction, and the correction rate itself, which would
be suspiciously near zero if the pass had been shallow. State both in the report rather
than claiming the design has no weakness.

### The rubric to give the model, and to apply yourself

The question is not "are these courses similar?" It is: **would a home-faculty
coordinator sign off on this host course in place of this home course?**

- `2` recognised outright: the host course covers the substance of the home course. A
  broader host course still counts, as long as the home material is inside it.
- `1` partial or arguable: overlapping but not sufficient on its own. This covers the
  granularity cases, where one 15-ECTS host module spans two home courses.
- `0` not a match, including same-title-different-content cases.

ECTS is not part of the judgement. It is reported next to the match and reasoned about
separately, the same way a coordinator does.

### Limits to state in one sentence each

- Pooled judgements favour the strategies that contributed to the pool.
- Labels come from students, not from the faculty office that signs the learning
  agreement.
- One expert checked every row, so kappa measures agreement on a 30-pair slice rather
  than on the whole set.

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

- **Title only vs the full course document.** This is the ablation that justifies the
  whole ingestion effort: if titles alone score nearly as well, scraping descriptions was
  wasted work, and if they do not, the gap is the number that proves descriptions carry
  the signal. Run it first.
- Query prefix on/off for BGE.
- Course document with vs without `learning_outcomes`.
- Course document with vs without `topics`.
- `top_n` into the reranker: 10 / 25 / 50 - where does Recall@5 stop improving?
- Fine-tuned bi-encoder (S6-A3) vs off-the-shelf.
