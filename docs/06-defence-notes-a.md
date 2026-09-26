# Defence notes - Person A (NLP and IR)

Task `S7-A1`. B owns the engineering questions; these are the retrieval, model and
statistics ones. The numbers are the final ones from `eval/report/results.md` (Twente
TCS, 27 queries) and `eval/report/utwente-am-bsc/results.md` (Applied Mathematics, 19
queries), re-run on 2026-09-26.

## The one-paragraph answer to "what did you build"

A student picks their home programme and a partner university. For each of their courses
the system ranks the partner's catalogue by how likely a coordinator would be to
recognise it, shows the sentence pair that drove each match, and adds up the result into
an estimate of how much of the degree would transfer. The retrieval is BM25 plus a
sentence-transformer bi-encoder, fused by reciprocal rank fusion; a cross-encoder
reranker is implemented and measured but is not the default, for reasons that are a
result rather than an omission.

## Why reciprocal rank fusion, and not score normalisation

A BM25 score is an unbounded sum of term weights; a cosine is bounded in -1 to 1 and, for
these models, rarely drops below 0.6. There is no principled way to put them on one
scale, and every normalisation choice (min-max over what set, z-score over what
population) is a hyperparameter nobody can defend at a viva. RRF throws the scores away
and uses only the ranks: `1 / (k + rank)`, summed across lists, k = 60. It has one
parameter, it is the standard choice in the literature, and it cannot be tuned into
looking good by accident.

The same argument applies one level up: the cross-encoder's opinion is fused with the
retrieval order the same way, rather than replacing it.

## Why a cross-encoder at all, and why it is not the default

The standard recipe is retrieve cheaply, then rerank precisely, because a cross-encoder
reads both texts together and can see relationships a single vector cannot. We
implemented it and measured it. Letting it replace the retrieval order lost to plain
hybrid retrieval (P@1 0.68 against 0.86 on the pre-labels). Fused into the order it is
level on the final labels, and never better:

| | TCS Recall@5 | TCS P@1 | AM Recall@5 | AM P@1 | ms/query |
|---|---|---|---|---|---|
| `hybrid` | 0.83 | 0.78 | 0.95 | 0.84 | 3 |
| `hybrid+ce` | 0.82 | 0.78 | 0.84 | 0.84 | about 880 |

Diagnosis: `ms-marco` cross-encoders are trained on short web queries against passages.
Both of our sides are 1400-character course descriptions, so the input is out of
distribution. Two fixes helped and one did not:

- Giving it a short query (course title plus one sentence) instead of the whole
  document: P@1 0.54 to 0.68.
- Fusing its order with the retrieval order instead of letting it overrule: level with
  `hybrid` on P@1 and MRR against both hosts on the final labels.
- Three other rerankers inside the size budget, including two trained on sentence
  similarity: all worse, the STS ones dramatically so (0.18 to 0.29 P@1).

ADR-0005 therefore defaults to `hybrid` and keeps `hybrid+ce` selectable. **If asked
whether this means the project failed:** no, the comparison is the project. An untested
claim that reranking helps would have been worth less than a measured demonstration of
when it does not, with the reason.

## Why these models

| Role | Model | Why |
|---|---|---|
| Bi-encoder | `BAAI/bge-small-en-v1.5`, 33 M params | best BEIR score per megabyte in the small class, 134 MB baked |
| Baseline bi-encoder | `all-MiniLM-L6-v2` | the default everyone reaches for, so the comparison means something |
| Cross-encoder | `ms-marco-MiniLM-L6-v2` | the community standard reranker, 92 MB |

Constraints: the demo runs on CPU in Docker with no network, so everything is baked into
the image and the whole set must stay small. It is 318 MB, and the build fails if it
exceeds 400. bge wants an instruction on the query side; we were not using it, and adding
it lifted Recall@5 from 0.78 to 0.87 on one host.

## Why BM25 and not Lucene

The assignment allows the transformers ecosystem or Lucene. `rank_bm25` is the same
ranking function in pure Python, with no JVM and no index files in the image. Each corpus
is 40 to 80 courses; there is nothing for a search engine to do. Be ready for the
follow-up: yes, BM25 is what Lucene is known for, and no, we are not claiming to have
implemented a search engine.

## What the confidence intervals mean

27 queries against TCS and 19 against Applied Mathematics is a small sample, so a
difference of a few points between two strategies can be noise. The report gives 95 % percentile bootstrap intervals over
queries, 1000 resamples with a fixed seed, and a paired bootstrap test for the headline
comparison. Paired because both strategies answer the same queries; treating them as
independent samples would overstate the uncertainty.

If two intervals overlap heavily, the honest statement is "we cannot distinguish these
with this many queries", and that is in the report rather than hidden.

The one significant result: `hybrid` beats `dense-minilm` on Recall@5 against Applied
Mathematics, +0.13, paired bootstrap p = 0.021. Against TCS every strategy is level with
the naive baseline. Say it that way: the fusion helps where the vocabulary differs (a
mathematics department describing calculus), and changes nothing where both sides use
the same computer science words.

## What `score_pct` is, and the recognition estimate

For `hybrid` and `hybrid+ce` it is a calibrated probability: a logistic curve on two
features, the fused rank score and the embedding cosine, fitted on the gold labels. The
cosine is there because rank alone cannot tell a good top hit from the best of a bad
lot: fitted on rank alone, Calculus 1 against a computer science catalogue showed 68 %,
and 23 of 50 courses showed exactly 68 % at rank 1. The evidence is the grouped 10-fold
cross-validated reliability in `data/calibration/hybrid.json`: 0.29 predicted, 0.29
observed; 0.68 predicted, 0.64 observed. The 0.4 to 0.6 band is optimistic (0.48
against 0.33), say so if asked. For `bm25` and `dense` the number is a display scale,
and the API says so per strategy. Below 20 % the UI shows "no suitable match".

The recognition estimate is then the sum over a study path of `p(best match) x ECTS`,
with the path defined by a module and a 180 ECTS budget so the denominator is a degree
somebody could actually take. Assumptions worth stating before you are asked: only the
best candidate per home course counts, partial matches (label 1) count as matches, which
is the optimistic reading, and the ECTS shortfall where the host course is smaller is
reported separately rather than hidden.

## How the gold set was built, and its biases

Pooling: for each home course, the union of the top 10 from `dense` and `hybrid+ce`,
1142 pairs over 40 home courses, pre-labelled by a model against a rubric ("would a
coordinator sign this off?"). Three things to disclose before the examiner finds them:

1. **Unlabelled pairs count as zero.** A strategy that finds something outside the pool
   is punished for it, and `dense-minilm`, the baseline of the paired test, did not
   feed the pool. Standard for pooled collections, worth one sentence.
2. **Human checking was done with the pre-label shown.** Aleksandar changed 2.2 % of
   his, but on 30 pairs labelled blind he agreed with the model only 67 % of the time,
   which is the anchoring the cold slice exists to measure.
3. **462 of the 1142 labels come from a second model, not a human.** Luka checked 176
   rows of his half and, for lack of time, had Claude label the rest blind. On the 30
   cold pairs, Claude against Aleksandar is weighted kappa 0.52, the pre-labels 0.63,
   and Luka on the 8 pairs he checked himself 0.73. `data/gold/provenance.json` records
   which rows are which; say it plainly, it is a limitation, not a secret.

## Known limits, said before being asked

- Five home courses (two Software Labs, two English courses, Financial mathematics) have
  no acceptable match in any host catalogue we hold. Ranking cannot express "none of
  these", so the calibrated probability does it: below 20 % the UI says "no suitable
  match".
- Every measured number is against Twente, the only host with labels. EPFL, Delft,
  Politecnico di Milano and KTH are in the app, listed by ARWU band and distance from
  Novi Sad, and are not evaluated.
- Both master's catalogues are a level above a bachelor's programme, so those matches
  should be read as weaker by construction.
- English only. Adding German or Dutch means a multilingual model, and the smallest
  usable one breaks the image budget on its own.
- Twente's mathematics is taught by a different department, which is why a second Twente
  programme is ingested. Without it, a third of the home programme had nothing to match
  against, which would have looked like a model failure and was a data gap.
