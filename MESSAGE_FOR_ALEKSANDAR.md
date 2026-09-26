# Message for Aleksandar (from Luka, via his Claude)

Written 2026-09-26 while Luka is asleep. Read it, act on it, then delete this file in
your next commit so it does not reach the examiners. Everything below is also in
`PROGRESS.md`, in more detail.

## What changed overnight on the A side

1. **Your audit, all seven items, done.** Rerank budget split per course and passed as
   an argument (no shared state), unreranked candidates keep their retrieval rank so
   late courses keep a sane probability, tie-break made monotone, loader skips a broken
   or duplicate curriculum instead of failing to boot, calibration fitted at the serving
   depth with a grouped cross-validated reliability block, `dense-minilm` pooling
   disclosed, and the docs brought up to date. Results re-run: unchanged at two decimals.
2. **Partners are ordered by ARWU 2026 band, then distance from Novi Sad.**
   `data/partners.json`; `/programmes` now lists UNS PMF, EPFL, TU Delft, Politecnico di
   Milano, KTH, Twente AM, Twente TCS. Twente stays only as the evaluation host.
3. **A silver set across all six hosts.** 20 home courses stratified by subject, the
   same against every host, pooled from all five strategies, labelled blind by a model.
   No human time. Report: `eval/report/silver.md`, one new deck slide, "All six host
   universities". Findings: Recall@5 level everywhere, BM25 has the best P@1 (0.84 vs
   0.70 for hybrid), nothing significant against the baseline, the 20 % floor declines
   half of the no-counterpart cases and wrongly declines 6 of 61. Silver vs the
   human-checked gold rows: weighted kappa 0.63.
4. **Manual test of the running app (backend on the real models plus Vite).** All
   endpoints behave, bad input gives 400/404, a 79-course `hybrid+ce` run completes in
   46 s with no probability collapse on late courses. Docker is not installed on Luka's
   machine, so the container build and the offline run are not re-tested: that is your
   `S7-AB2`.

## What we need from you

1. Done by you already (`342b1dd`): default host and the demo on TU Delft. Thanks.
2. Optional: the evaluation page could link `silver.md` beside `results.md`, labelled as
   model-judged. `routes_evaluation.py` already lists every `*.md` in `eval/report/`, so
   it may show up on its own; check it reads sensibly.
3. `S7-AB2`: the offline Docker rehearsal and the screenshots. The data volume now has
   seven curricula, so the first cold start encodes two more programmes.
4. Read the deck once (`docs/slides/erasmusgpt-defence.pptx`, rebuild with
   `python docs/slides/build_deck.py`); slides 6 and 7 are new or changed.

## How to describe the labels at the defence

Say it the way it happened, because every file in the repo says the same:
a model pre-labelled all 1142 gold pairs; you checked your 504 and Luka 176, with the
suggestion shown; you labelled 30 pairs blind first, for kappa; the remaining 462 were
labelled blind by a second model because we ran out of time. The silver set is
entirely model-labelled and is reported separately. The retrieval itself uses no
labels; only the calibration of the percentage is fitted on them.
