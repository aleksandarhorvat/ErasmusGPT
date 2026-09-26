# Defence notes: the engineering questions

Owner: **Person B**. Person A's half is `docs/06-defence-notes-a.md`. Task `S7-B1`.

Answers are short on purpose. Each one names the file so a follow-up can be opened live.

## Why is there a protocol between the API and the matching engine?

`backend/app/matching/interface.py` defines four methods and a `Matcher` protocol.
`app/api/**` imports that and the factory, nothing else from the matching package.

Two people worked at once from day one. Person B built the whole surface against
`StubMatcher`, which returns plausible fake results in microseconds, while Person A built
the real pipeline behind the same four methods. Neither had to wait, and neither could
break the other's boot. `MATCHER_IMPL=stub|real` switches them; `real` falls back to the
stub with a loud log if the models are missing, which is why the container still serves
when the pipeline is half finished.

That is not a hypothetical benefit. When the real pipeline first appeared it raised
`NotImplementedError` for a week and the app kept running.

## Why SQLite and not Postgres?

ADR-0002. The dataset is seven study programmes and 378 courses. The grading criterion is
that somebody else can run this with minimal effort, and two compose services beat three.
The curriculum JSON files are the source of truth, so the database is bookkeeping, not
data: deleting the volume loses nothing. `app/db/ingest_log.py` uses it to tell "the same
curricula as last boot" from "somebody edited one", keyed by a hash of the courses rather
than of the file, so a re-scrape that only moves `scraped_at` is not a change.

## Why are the models inside the image?

`backend/Dockerfile` downloads them at build time and then sets `HF_HUB_OFFLINE=1` and
`TRANSFORMERS_OFFLINE=1`. The demo has to run on a machine with no network, and we tested
that literally: built, disconnected, `docker compose up`, used the app. Building needs the
network, running does not, and the README separates the two because the first version of
that instruction asked for something impossible.

`BAKE_MODELS=0` skips the download for CI and stub-only work, which is how the smoke test
starts the whole stack in about a minute.

## Why does the UI show a percentage for one strategy and a bare number for the others?

Because they are different kinds of number, and printing them the same way would be a
lie. `frontend/src/lib/score.ts` is the only place allowed to format a score.

`hybrid` and `hybrid+ce` have a fitted calibration, so their `score_pct` is an estimated
probability that a coordinator would recognise the pair. `dense` is a stretched cosine.
`bm25` is relative to the best hit for that course, so the top row always reads 100. The
calibrated ones get recognition bands and a "% chance" tooltip; the others get neutral badges and a
tooltip saying so. For the same reason the recognition panel refuses to give a
whole-programme ECTS estimate for an uncalibrated strategy: summing `ects x score` over
display values is arithmetic on the wrong thing.

## Why does a lower-ranked candidate sometimes show a higher percentage?

Because the rank and the percentage answer two different questions. The rank is the
fused retrieval order: how strongly BM25 and the bi-encoder agree that the host course
is close to yours. The percentage is the calibrated probability that a coordinator would
sign the pair off, and its model uses the fused score **and** the plain cosine similarity
of the two descriptions (Person A added the cosine because rank agreement alone gave
Calculus and Software Diamond the same 68 %). So against TU Delft, Introduction to
algebra can show 29 % at rank 2 and 41 % at rank 3.

We could sort by the percentage, but that is a learned ranking fitted on the gold labels,
and the evaluation would then score it on the same labels it was fitted on. The honest
version needs held-out folds and more labels than we have. What we did instead: the
recognition estimate uses the most probable of the five candidates, not rank 1, and the
table says "no suitable match" when even that one is under 20 %.

## Why is `hybrid` the default when the proposal promised a cross-encoder?

ADR-0005, amended as the numbers came in. The reranker originally replaced the retrieval
order and measured worst of four. Person A found that fusing it by RRF instead, the same
way BM25 and dense are fused, makes it level, and the final labels confirm it: against
Twente TCS both have P@1 0.78 and Recall@5 0.83 and 0.82. `hybrid` stays the default
because it is level and about 300 times cheaper per query (3 ms against about 860 ms),
not because the reranker is bad.

The honest framing is that the finding is about **how** to combine a reranker rather than
whether to have one, and that is a better result than the one we set out to get.

## How do you know the numbers are not made up?

They rest on a gold set of 1142 pooled pairs, and we say exactly who labelled it: 680
rows checked by one of us with the model's proposal shown, and 462 labelled by a second
model (Claude) and not checked by a person, because we ran out of time. That split is in
`data/gold/provenance.json`, in every report, on the evaluation page and on the limits
slide. `GET /api/v1/evaluation` returns it as `gold_human` and `gold_model`, so the page
cannot say "checked by a human" about rows no human checked.

The expected follow-up is "then how good is the model as a labeller?". On the 30 pairs
Aleksandar labelled blind, Claude agrees with him at weighted kappa 0.52; the two of us
agree at 0.73, but on only 8 shared pairs. And with the proposal visible Aleksandar
changed 2.2 % of labels, against 33 % disagreement when he labelled blind, which is
anchoring. We report both instead of choosing the flattering one.

The gold set is built the other way round from how it looks: a model pre-labels, a human
reads every row and corrects it, and the two files are kept separate so the correction
rate can be measured. `scripts/check_gold.py` runs in CI and catches duplicate pairs,
course ids that stopped existing after a re-scrape, labels that are not 0, 1 or 2, and
rows marked checked with no label.

## What stops the two of you breaking each other's work?

Ownership zones in `CONTEXT.md` section 7, a frozen contract in `app/schemas/`, and a
`PROGRESS.md` entry per commit. Cross-zone edits are allowed but have to be announced:
Person A changed one of Person B's files once, asked twice first, and wrote why.

CI runs the style check, ruff, the curriculum validator, the gold-set validator, the
backend tests, the frontend build, and a smoke test that starts the whole stack and fails
unless the API serves the curricula. That last one exists because a path bug once made the
app work from a checkout and serve an empty list inside the image.

## What would you do next with more time?

Fine-tune the reranker on the gold set, which is the version where the original claim
could still hold. Add a host university outside the two Twente catalogues, because the
gold set currently measures generalisation across programmes rather than across
institutions. And finish the human check of the 462 model-labelled rows (about an hour)
plus the 22 cold pairs only a model has labelled, so kappa covers all 30 pairs and the
calibration stops being flagged as provisional.
