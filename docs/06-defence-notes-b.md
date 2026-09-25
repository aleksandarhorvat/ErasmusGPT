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

ADR-0002. The dataset is five study programmes and 298 courses. The grading criterion is
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

## Why is `hybrid` the default when the proposal promised a cross-encoder?

ADR-0005, and it was amended once. The reranker originally replaced the retrieval order
and measured worst of four. Person A found that fusing it by RRF instead, the same way
BM25 and dense are fused, makes it level. `hybrid` stays the default because it is level
and about 400 times cheaper per query (2 ms against about 850 ms), not because the
reranker is bad.

The honest framing is that the finding is about **how** to combine a reranker rather than
whether to have one, and that is a better result than the one we set out to get.

## How do you know the numbers are not made up?

We do not claim them yet. `GET /api/v1/evaluation` and the "how well does this work?"
panel report how far the human labelling pass has got. Today that is 0 of 1142 pairs, and
the panel says every figure in `eval/report/` came from labels a model wrote about our own
retrieval, so they can choose between settings but cannot be reported as results.

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
institutions. And refit both calibrations on the checked labels: today they are fitted
on the model's pre-labels, so the probabilities are flagged as provisional.
