# PROGRESS

Append-only work log. **Newest entry goes at the top**, directly under this line.
One entry per commit (or per working session if several commits land together).
Never rewrite or delete someone else's entry.
Entries follow the writing style in `CONTEXT.md` section 11: ASCII only, no filler.

Both people append at the top, so this file is the one place a git conflict is likely.
When it happens, keep **both** entries and order them by date. Never drop one.

An agent starting a session reads the *Project state* block in `TASKS.md`, then the
**top 2-3 entries here**, then `CONTEXT.md`. That is enough to know what state the
project is in and what to do next.

---

## 2026-09-26 - [B] Demo opens on TU Delft, screenshots dropped

**Who:** Person B
**Stage:** 7
**Commit:** `[B] open the demo on tu delft and drop the screenshots`
**Tasks touched:** A's two requests of 2026-09-26, `S7-AB2` (scope)

### Done
- `App.tsx`: no hard-coded host. The page opens on UNS PMF against the first bachelor's
  programme in `/programmes` order, which A's `data/partners.json` makes TU Delft; a
  master's catalogue is skipped unless nothing else is loaded.
- `docs/07-demo-script.md`: the demo runs Novi Sad against TU Delft end to end; step 5 is
  now the "no suitable match" row, and step 7 says the evaluation page is measured
  against Twente, the one host with labels. `scripts/rehearse_demo.py` checks the
  default host rule, uses Delft for every step, and checks that Operating systems 1
  finds Delft's Operating Systems first. Deck demo slide: the duplicate Delft step
  replaced by the no-suitable-match step; notes no longer point to screenshots. Deck
  rebuilt.
- Screenshots dropped, as decided by Aleksandar: `docs/screenshots/` removed, and the
  README, demo script, deck notes and TASKS no longer mention them. If the live demo
  fails, the fallback is to say what should have happened and go on to the evaluation
  slides.

### Checks
check_style, check_gold, pytest, frontend build, rehearsal script against a stub
backend (the stub-only failures are expected).

### Next
- **Aleksandar:** `docker compose up -d --build` once so the running app picks up the new
  default, then `python scripts/rehearse_demo.py`.
- **Both:** read the deck once end to end and rehearse the talk.

---

## 2026-09-26 - [A] B's audit worked through, partners ordered by ranking and distance

**Who:** Person A
**Stage:** 7
**Commits:** `[A] fix the rerank budget, tie-break and loader from the audit`,
`[A] fit calibration at serving depth with grouped cross-validation`,
`[A] order partners by arwu band and distance, bring docs up to date`
**Tasks touched:** B's "For A" list, items 1 to 7; `S6-A2` wording

### B's audit, item by item
1. **Rerank budget.** Gone as shared state. `match_programme` splits the request's 1500
   pairs evenly over its home courses and passes the allowance down as an argument, so
   no course is starved and concurrent requests cannot drain each other. Candidates past
   a course's allowance keep their retrieval rank in the reranker's list, so their fused
   score stays on the same scale instead of halving. Three tests.
2. **Calibration depth.** `fit_calibration.py` now scores pairs at `candidate_top_n`,
   what the app serves. 1116 of the 1142 labelled pairs fall inside that depth.
3. **`dense-minilm` not pooled.** Stated in `results.md` (both hosts), the generator,
   `docs/05-evaluation.md` limits and the defence notes.
4. **In-sample reliability.** The calibration file now carries a `cross_validated`
   block, 10-fold grouped by home course, standardisation refitted per fold. Docs quote
   that one, including the optimistic 0.4 to 0.6 bin (0.48 predicted, 0.33 observed).
5. **Tie-break.** `_blend` sorts on (fused score, reranker score) and caps the nudge by
   the previous row, so scores never rise down the list. Test over 10 courses.
6. **Loader.** A malformed file is logged and skipped; a second file with an existing
   `programme_id` is rejected. Test with one of each.
7. **Docs.** `docs/05` (disclose step, calibration, limits), `docs/03`, `docs/02`,
   `data/README.md` (seven curricula, halves, provenance), `errors.md` (floor shipped,
   banned word gone), `eval/README.md`, `docs/06-defence-notes-a.md` (final numbers
   throughout, the model-labelled rows, the floor), TASKS `S6-A2`.

Results re-run after 1, 2 and 5: unchanged at two decimals except nDCG@10 of
`hybrid+ce` against TCS (0.814 to 0.813). The one significant result stands:
`hybrid` over `dense-minilm` on Recall@5 against Applied Mathematics, +0.13, p = 0.021.

### Partners ordered by ranking and distance, at Luka's request
`data/partners.json` and `CurriculumStore._order_programmes()`: home programme first,
then ShanghaiRanking ARWU 2026 band (checked on shanghairanking.com), ties by
great-circle distance from Novi Sad. `/programmes` now lists UNS PMF, EPFL (43), TU Delft
(151-200), Politecnico di Milano (201-300, 828 km), KTH (201-300, 1570 km), Twente
(501-600). Twente stays only as the evaluation host. Deck slides 2, 4 and 6 and
`docs/01-universities.md` follow the same order and say why Twente is in at all.

### Request to B
- `App.tsx` `DEFAULT_HOST = 'utwente-tcs-bsc'`: please drop it and default to the first
  bachelor host in the `/programmes` order, which is now TU Delft. The list order is the
  priority; EPFL is first but a master's.
- `docs/07-demo-script.md`: the demo can run Novi Sad against TU Delft end to end; deck
  slide 4 now says so. Twente only for the evaluation page.

### Next
- **A:** lane A is done. `S6-A3` stays optional; Luka to decide.
- **B:** the two items above, `S7-AB2`.

---

## 2026-09-26 - [B] Offline rehearsal passed, screenshots, readable evaluation table

**Who:** Person B
**Stage:** 7
**Commit:** `[B] record the offline rehearsal and add the demo screenshots`
**Tasks touched:** `S7-AB2` (done), `S7-AB1` (defence notes)

### Done
- `S7-AB2`: on the demo laptop, first online and then with the network off,
  `scripts/rehearse_demo.py` passed every step with the real models (matcher real,
  models loaded, huggingface.co unreachable). `hybrid` over a whole programme 66 ms,
  TU Delft 70 ms, recognition 0.1 s, `hybrid+ce` over a whole programme 40 s. Timings
  in the README; cold boot not timed on that run.
- Clicked through the live app as well: defaults, the Computer Science path against
  TCS (about 90 of 180 ECTS, 15 no suitable match), evidence on Computer networks,
  compare against `hybrid+ce`, TU Delft (about 127 of 180), the evaluation page. No
  console errors.
- `docs/screenshots/`: the 7 fallback screenshots named in `docs/07-demo-script.md`.
- Evaluation page: `results.csv` shown as a readable table (two decimals, the 95 %
  interval under each value, best per column in bold) instead of 17 raw columns.
- `docs/06-defence-notes-b.md`: why a lower-ranked candidate can show a higher
  percentage (rank is fused retrieval order, the percentage also uses the cosine;
  sorting by it would be a learned ranking scored on its own training labels).

### CONTRACT CHANGE
Text only: the `hybrid` description in `backend/app/matching/interface.py` says "about
3 ms per query" (final measurement) instead of "about 2 ms". Luka asked for it.

### Next
- **Both:** read the deck once end to end and rehearse the talk.
- **Luka:** the "For A" list in the audit entry below.

---

## 2026-09-26 - [B] Whole-repo audit: lane B bugs fixed, lane A findings listed

**Who:** Person B
**Stage:** 7
**Commit:** `[B] fix what the repo audit found in lane b`
**Tasks touched:** `S7-AB2` (prep), fixes across lane B

### How it was checked
Four independent reviews (backend and packaging, matching and eval, frontend and
annotator, docs against data), then a fresh clone on Python 3.11 with the pinned ruff,
the full test suite, and the UI driven headlessly in Chromium against the stub backend,
light and dark. The real models could not be downloaded there, so the real pipeline was
exercised only with patched encoders; the offline Docker run is still `S7-AB2`.

### CONTRACT CHANGE
- `POST /recognition` answers 400 for a `module` that is not a study path of the home
  programme. It used to accept it (including a wrong capitalisation), estimate over every
  course, and echo the module back as if applied.
- `results` order: `docs/04-api-contract.md` now says curriculum-file order, which is
  what both matchers always did. The old "year, semester, code" was never implemented.
- `GET /` answers with a small JSON instead of redirecting to `/docs`, whose page loads
  from a CDN and was blank offline.

### Fixed (lane B)
- Score badges for calibrated strategies had no colour: `styles.css` styled
  high/medium/low but not likely/borderline/unlikely, which is what the default `hybrid`
  uses. Light and dark rules added.
- Recognition no longer holds the page: the table appears and the controls are enabled again when
  `/match` returns; the summary loads on its own. A late answer for an earlier run is
  dropped. `/recognition` asks for 5 candidates instead of 1, because `summarise()` takes
  the most probable, which is not always rank 1.
- Compare kept the previous strategy's scores and formatted them for the new one after a
  failed run; the result now carries its strategy. Compare also applies the 20 % floor.
- 422 errors showed as "[object Object]"; the list is joined into a sentence.
- CSV export: a `no_suitable_match` column, and a lone carriage return is quoted.
- An old error stayed on screen after the inputs changed.
- Dark mode: labels, dropdown text and "why" toggles were grey on dark (about 2.4:1).
- Evaluation page said "all" pairs labelled while labelling was still partial.
- `/evaluation`: a short CSV row, a BOM, an unreadable file or an overflowing number in
  `provenance.json` gave a 500; each now degrades to what it can read. `/match` with an
  empty `course_uids` now still returns 404 for an unknown host.
- `last_seen` in the ingest log never moved for unchanged files.
- `split_gold.py --help` and `merge_gold.py --help` ran the scripts; `merge_gold` rewrote
  `gold_pairs.csv`. They now print help.
- CI smoke test also checks nginx's `/api` proxy. Inline empty favicon, so the offline
  page has no failing request.
- `.env.example` and README: model names and candidate depth are pinned in
  `docker-compose.yml` (the calibration was fitted with them), so `.env` only carries the
  two switches for Docker. README boot numbers (756 course vectors, about 4100
  sentences), a copy-paste bug in the pre-commit commands, 7 programmes and 378 courses
  in the defence notes, CONTEXT.md's "three configurations" and "~300 pairs/s" (measured
  about 30), the stage 4 and 5 descriptions.

Six new tests. 139 passed, ruff 0.8.4 clean, style and gold checks pass, frontend builds.

### For A (found in your zone, not changed)
Most important first. Numbers are from reproductions with patched encoders.
1. **Rerank pair budget runs out mid-programme** (`pipeline.py` around 303). 1500 pairs
   at 25 per course is 60 courses; from course 61 the reranker gets zero pairs and the
   calibrated p collapses. KTH (79) and EPFL (78) hit it, PMF (50) does not. The budget
   is also one mutable attribute on a shared matcher, so two concurrent `hybrid+ce`
   requests drain each other's. Per-request or per-course budget fixes both.
2. **Calibration fitted at a different depth than served** (`fit_calibration.py` around
   195 against `pipeline.py` around 287): fitting ranks the whole host catalogue,
   serving uses `candidate_top_n=25`. Small for `hybrid`, larger for `hybrid+ce`.
3. **`dense-minilm` is not in the pool** (`make_pool.py` around 37), so its unjudged hits
   count as 0. It is the baseline in the paired test, so the test is tilted towards the
   pooled strategies. Worth one sentence in the report at least.
4. **Calibration reliability is in-sample** and the docstring quotes grouped CV numbers
   the code does not compute. `hybrid.json`'s 0.4-0.6 bin is 0.498 predicted against
   0.342 observed (38 pairs); `docs/05-evaluation.md` quotes 0.48 against 0.48.
5. **`_blend` tie-break** adds `1e-4 * ce` after sorting and never re-sorts; 1e-4 is also
   larger than RRF gaps deep in the list, so a few rows come out non-monotone.
6. **One malformed curriculum file stops the backend booting** (`ingest/loader.py`, no
   per-file error handling); two files with one `programme_id` overwrite silently.
7. Docs still saying every row was human-checked: `docs/05-evaluation.md` around 159,
   `docs/03-data-schema.md` around 106 and 129, `docs/06-defence-notes-a.md` (still
   provisional numbers throughout: 0.82/0.86, "28 queries", only `hybrid+ce` calibrated,
   floor as future work), `docs/02-models.md` (400 times, "on provisional labels"),
   `data/README.md` (3 curricula, no halves or provenance), `eval/report/errors.md` (the
   floor is shipped, and one banned word is used there), `eval/README.md` (`--host-programmes`
   and the AM run undocumented), TASKS `S6-A2` still says re-run pending.

### Next
- **Aleksandar:** `S7-AB2` on the demo laptop.
- **Luka:** items 1 and 7 before the defence; 2 to 5 are at least worth a line in the
  limits.

---

## 2026-09-26 - [B] Final numbers on B's side, label split in the app, stages 5 and 6 closed

**Who:** Person B
**Stage:** 5, 6 and 7
**Commit:** `[B] show who labelled the gold set and put the final numbers in`
**Tasks touched:** A's "Request to B" of 2026-09-26, lane B gates of stages 2 to 6,
`S7-AB1`, `S7-AB2`

### Decision
Aleksandar accepts A's completion of the gold set as it is: 680 rows checked by a person,
462 labelled by Claude and not checked. Everything below reports that split rather than
hiding it.

### CONTRACT CHANGE
`EvaluationResponse` gains `gold_human` and `gold_model` (both default 0), read from
`data/gold/provenance.json`. `checked=yes` now means "has its final label", not "a
person checked it". No field removed; `provisional` keeps its meaning. Documented in
`docs/04-api-contract.md`, typed in `frontend/src/lib/api.ts`.

### Done
- Evaluation page: "680 checked by a person, 462 labelled by a second model (Claude) and
  not checked by a person", with a warning under it, instead of "1142 of 1142 pairs
  checked by a human". Headline text now states the final finding. Two tests, one for a
  missing or unreadable provenance file.
- Recognition panel and score tooltip: provisional because the gold set is partly
  model-labelled, not because it is machine-labelled.
- Deck (shared): the tag on numbers slides reads PARTLY MODEL-LABELLED when every row is
  labelled but some by a model; the reranker slide keeps PROVISIONAL LABELS because its
  replace-against-fuse numbers exist only on the pre-labels. Fixed a regression: the
  gold slide showed kappa "pending" because `kappa.md` renamed the "A vs B" row. Cost
  ratio and query count are read from `results.csv` (about 300 times, 27 queries). The
  problem slide counts 6 hosts and 378 courses from `data/curricula/`. Demo slide gains
  the TU Delft step. Rendered and read.
- Final numbers: ADR-0005 third amendment with the final table (decision stands, one
  significant result, `hybrid` over `dense-minilm` on AM Recall@5), README "What we
  found" rewritten with both hosts and the provenance paragraph, `docs/06-defence-notes-b.md`,
  CONTEXT.md (shared, one sentence: final labels, about 300 times).
- Demo: `docs/07-demo-script.md` step 5 switches the host to TU Delft, step 4 shows a "no
  suitable match" row, 7 screenshots. `scripts/rehearse_demo.py` checks that Operating
  systems 1 finds Delft's Operating Systems, and reports the human/model split.
- Lane B gates of stages 2 to 6 ticked, each with what satisfies it. Stages 5 and 6
  closed; current stage is 7.

### Checks
ruff, check_style, check_gold, validate_curricula, pytest, frontend build (tsc and vite),
rehearsal script against a stub backend.

### Next
- **Aleksandar:** `S7-AB2`, the offline rehearsal and the 7 screenshots.
- **Both:** read the deck once end to end (`S7-AB1`).

---

## 2026-09-26 - [A] Gold set complete, real results, Delft and Polimi added

**Who:** Person A
**Stage:** 5 and 6
**Commits:** `[A] add tu delft and politecnico di milano`,
`[A] complete the gold set and report the final results`
**Tasks touched:** `S5-A1` (done), `S5-A3` (done), `S6-A2` (re-run), lane A gate of
stage 5 ticked

### How the A half was finished, stated plainly
Luka checked the first 176 rows of his half himself. For lack of time he decided that
the other 462 take the labels of a second model: Claude labelled all 638 rows of the
half blind to the pre-labels, and those 462 are in the gold set as Claude labelled them.
They are not human-checked, and nothing claims they are:

- `data/gold/provenance.json` says who produced which rows.
- `data/gold/claude_labels_a.csv` has Claude's label and reason for all 638, `final=yes`
  on the 462 used.
- `eval/provenance.py` puts the same facts into `results.md`, `kappa.md`, the error
  analysis and the calibration files. `docs/05-evaluation.md` has a section on it and
  a limit to state; the deck's gold-set and limits slides say it.
- The calibration source reads "PROVISIONAL, partly model-labelled", so the UI keeps
  its warning. That also keeps `test_api_recognition.py` green as written.

Gold set: 1142 of 1142 rows, 680 human (1.6 % of pre-labels changed), 462 model (5.4 %
differ from the pre-label, mostly partial matches turned into 0).

### Kappa (`eval/report/kappa.md`)

| Comparison | Pairs | Weighted kappa |
|---|---|---|
| Luka vs Aleksandar, cold pairs Luka checked himself | 8 | 0.73 |
| Claude vs Aleksandar | 30 | 0.52 |
| Pre-label vs Aleksandar | 30 | 0.63 |

### Results (`eval/report/results.md`, `eval/report/utwente-am-bsc/results.md`)
A bug found on the way: `run_eval.py` counted every labelled home course as a query,
including those with nothing relevant at the host, and put labels for the other Twente
programme into every recall denominator. `host_view()` now applies the protocol's
definition, with a test. That took TCS from 40 to 27 queries and AM from 40 to 19.

| | TCS R@5 | TCS P@1 | AM R@5 | AM P@1 | ms/query |
|---|---|---|---|---|---|
| `bm25` | 0.74 | 0.85 | 0.78 | 0.79 | 3 |
| `dense-minilm` | 0.83 | 0.78 | 0.82 | 0.84 | <1 |
| `dense-bge` | 0.78 | 0.70 | 0.95 | 0.89 | <1 |
| `hybrid` | 0.83 | 0.78 | 0.95 | 0.84 | 3 |
| `hybrid+ce` | 0.82 | 0.78 | 0.84 | 0.84 | about 860 |

The one significant result: `hybrid` beats `dense-minilm` on Recall@5 against Applied
Mathematics, +0.13, paired bootstrap p = 0.021. Everything else is level within the
intervals, and the reranker buys nothing measurable at about 300 times the cost of
`hybrid`. ADR-0005's decision holds; its numbers need the final table.

### Calibration refitted on the final labels
Reliability stays close (0.29 predicted, 0.28 observed; 0.68 against 0.67).

### TU Delft and Politecnico di Milano
Added at Luka's request, for the demo only (no gold labels). `docs/01-universities.md`
has the details:
- `tudelft-cse-bsc`: 35 courses, 2026/2027, every one with description and outcomes.
- `polimi-ecs-bsc`: 45 courses, Engineering of Computing Systems. Polimi has no
  English-taught computer science bachelor; this one is taught in Italian and its
  catalogue gives English descriptions, which is what we match on.
Both match cleanly: Operating systems 1 finds Delft's Operating Systems at 99 %.

### Request to B
- `EvaluationPanel.tsx` line 26 prints "N of M pairs checked by a human". With
  provenance it would read 1142 of 1142, which is false for 462 rows. Suggest reading
  `data/gold/provenance.json` (`counts.human`, `counts.model`) through
  `/evaluation`, or at least wording it "labelled" with the split under it.
- `RecognitionPanel` provisional text says the calibration "was fitted on machine
  labels, not on the human-checked gold set". Now it is "partly": 462 of 1142 rows.
- ADR-0005, README and `docs/06-defence-notes-b.md`: the final table above replaces
  the provisional numbers. Headline: no significant gain except `hybrid` on AM R@5.
- The demo can use Delft now: Novi Sad against Delft reads better than against Twente.

### Next
- **A:** nothing left in lane A except the optional `S6-A3`, which I would close as a
  documented decision not to fine-tune: 46 queries and a gold set partly written by a
  model are no training data to report a delta on.
- **B:** the requests above, the stage 5 gate, `S7-AB2`.

---

## 2026-09-25 - [A] A half-checked gold set stays provisional in the calibration

**Who:** Person A
**Stage:** 5
**Commit:** `[A] keep a partial human pass provisional`
**Tasks touched:** none; a guard before `S5-A1` lands, and B's docs request

### Done
- `fit_calibration.load_labels()` switched to human labels as soon as any row was
  checked, and then wrote "human-checked" as the source. With B's half in, that is 504
  of 1142 rows over 18 home courses, and `core/calibration.py` would have dropped the
  PROVISIONAL flag in the UI. A partial pass now writes "PROVISIONAL: human-checked,
  N of M rows"; only a complete pass reads as final. Three tests in
  `test_matching_calibration_labels.py`.
- `docs/02-models.md`: the "about 500 times" line, as B asked. It now separates the
  replacing reranker (lost) from the fused one (level, about 400 times the cost).
- Calibrations not refitted yet: they wait for Luka's half, so both halves are fitted
  together and kappa can run on the same push.

### Noted from B's entry
Aleksandar against the model on the cold slice: kappa 0.50, weighted 0.63, while he
changed 2.2 % of labels with the proposal shown. That gap is the anchoring the cold slice
exists to catch, and it goes in the report next to A-against-B kappa.

### Next
- **Luka:** `half_a_luka.csv`.
- **A:** on Luka's push, refit, `run_eval.py`, `kappa.py`, error analysis, deck.

---

## 2026-09-25 - [B] Cold slice labelled, B half of the gold set checked

**Who:** Person B
**Stage:** 5
**Commit:** `[B] label the cold slice and check the b half of the gold set`
**Tasks touched:** `S5-B1` (done), `S5-A1` (B half done)

### Done
- `data/gold/gold_pairs_b.csv`: all 30 cold pairs labelled by Aleksandar without the
  model's labels, before opening his half. 13 zeros, 8 ones, 9 twos.
- `data/gold/half_b_aleksandar.csv`: 504 of 504 checked. 11 corrections (2.2 %): 8 model
  1s to 0, 2 model 0s to 1, one 1 to 2. Merged with `scripts/merge_gold.py`;
  `gold_pairs.csv` is at 504 of 1142 checked, `check_gold.py` passes.

### Worth knowing for the report
On the 30 cold pairs, Aleksandar and the model agree on 20 (67 %, Cohen's kappa 0.50,
linearly weighted 0.63). With the model's label shown, in his half, he changed only 2.2 %.
Some of that gap is the slice itself (it has far more 1s and 2s than the pool, and those
are the hard cases), but some is likely anchoring on the proposal, which is the effect
the cold slice exists to measure. Suggest reporting both numbers side by side. The
A-versus-B kappa waits on Luka's checks of the same 30 pairs, which are in his half.

### Next
- **Luka:** `half_a_luka.csv`, then `python scripts/merge_gold.py`, then the re-runs
  (`run_eval.py`, `fit_calibration.py`, `kappa.py`, `error_analysis.py`).
- **Aleksandar:** `S7-AB2`.

---

## 2026-09-25 - [B] A's four front-end requests

**Who:** Person B
**Stage:** 6
**Commit:** `[B] open on the demo case, no suitable match below 20 percent`
**Tasks touched:** `S3-B1`, `S6-B4`, `S5-B3` (fixes from A's end-to-end run)

### Done
- `App.tsx` opens on `uns-pmf-informatics-bsc` against `utwente-tcs-bsc` when both are
  loaded, and falls back to the first two otherwise.
- Recognition headline: "expected to be recognised", so it no longer reads as the
  "likely" bucket.
- Evaluation page and README: the reranker is level with `hybrid` when fused, at about
  400 times the cost, instead of "measures worse" and "500 times".
- `lib/score.ts` `NO_MATCH_BELOW = 20`: for a calibrated strategy, a course whose most
  probable candidate is under 20 % shows "no suitable match" with that best value, and
  the candidates stay behind a "show anyway" toggle. The summary line counts these rows.
  Uses the maximum over the candidates, not rank 1, to match A's new `aggregate.py`.
  Relative scores never trigger it.

### Checks
check_style, pytest (129 passed), frontend build (tsc and vite).

### For A
`docs/02-models.md` line 118 still says "about 500 times the latency"; yours to change.

### Next
- **Aleksandar:** `half_b_aleksandar.csv`.

---

## 2026-09-25 - [B] Split the gold-set check between A and B

**Who:** Person B
**Stage:** 5
**Commit:** `[B] split the gold-set check into one file per person`
**Tasks touched:** `S5-A1` (now shared), `S5-B1` (order)

### Why
1142 rows is about 3.5 hours for one person. Split in two it is about two
hours each, and each of us writes only our own file, so there is no CSV to merge in git.
Proposed by B; Luka, say so if you would rather keep the whole pass.

### Done
- `scripts/split_gold.py` wrote `data/gold/half_a_luka.csv` (638 rows, 33 home courses,
  about 128 min) and `data/gold/half_b_aleksandar.csv` (504 rows, 18 home courses, about
  88 min plus 38 min for the cold slice). Split by home course, balanced on estimated
  time, all 30 cold pairs in Luka's half so Aleksandar never sees their model label.
  Re-running it keeps the split and copies over anything already checked in
  `gold_pairs.csv`, so checks done before the split are not lost.
- `scripts/merge_gold.py` writes `gold_pairs.csv` back from the halves in its own order
  and format. Tested: an untouched split round-trips byte for byte, partial checks merge,
  and a pair checked with two different labels stops the merge.
- `tools/annotate.js`: a half keeps `llm_label` and `llm_reason` when saved (quoted, round
  trip tested on the real file), so reopening shows the proposal and the correction count
  still works. Before this, resuming from `gold_pairs.csv` lost the model's reason.
- `scripts/check_gold.py` (CI) also checks the halves: every gold pair in exactly one
  half, no cold pair in Aleksandar's.
- Deck limits slide: "Two people checked half the rows each".

### For A (cross-zone, please read)
`data/gold/` is your zone. I added the two half files there and changed the `S5-A1` row
and your line in the Project state block to describe the split; correct them if you
want it worded differently. Not touched, yours to update: `docs/05-evaluation.md` lines
107 and 205 and `docs/03-data-schema.md` line 92 still say one person checks every row.
If you already checked rows locally in `gold_pairs.csv`, commit that first, pull, then
run `python scripts/split_gold.py` once: it copies your checks into your half.

### Next
- **Aleksandar:** the 30 cold pairs first, then `half_b_aleksandar.csv`.
- **Luka:** `half_a_luka.csv`.
- Either of us: `python scripts/merge_gold.py` before each commit.

---

## 2026-09-25 - [B] Product slide, rehearsal script, provisional until every row is checked

**Who:** Person B
**Stage:** 5 and 7
**Commit:** `[B] add the rehearsal script and the product slide, keep evaluation provisional`
**Tasks touched:** `S7-AB1` (wip), `S7-AB2` (wip), `S5-B3` (fix), ADR-0005 (amended)

### CONTRACT CHANGE
`EvaluationResponse.provisional` in `backend/app/schemas/match.py` now means "the human
pass has not checked every gold row yet", not "no row is checked". No field changes. A
partial pass is still provisional because `run_eval.py` scores only checked rows, and
those cover whichever home courses were labelled first. `docs/04-api-contract.md` now
also documents `/recognition` and `/evaluation`, the `calibrated` and `provisional` flags
on `/strategies`, and moves `hybrid` into the calibrated row of the `score_pct` table.
The `RecognitionRequest` docstring no longer mentions the removed `mandatory_only`.

### Done
- `routes_evaluation.is_provisional()` with a test for 0, 200, 1141 and 1142 of 1142,
  and for an empty gold set. The evaluation panel has a separate message for a pass in
  progress.
- `docs/slides/build_deck.py` (shared file, both owners): the same rule for the deck.
  `results.csv` alone no longer drops the PROVISIONAL tag; every gold row has to be
  checked. The recognition slide keeps its tag while `hybrid.json` says its labels are
  provisional, even after the results table stops being. New slide after it, "An
  interface that does not overstate": the two kinds of score, no ECTS sum without a
  calibration, the provisional flags, the evaluation page. Demo step 5 now compares one
  row against `hybrid+ce` instead of rerunning the whole programme, which takes about
  40 s. Slides 4 and 10 read and otherwise left as they were. Deck rebuilt.
- `scripts/rehearse_demo.py`: starts the stack if asked, times the boot, runs every demo
  step against the API through nginx and fails if huggingface.co is reachable.
  Standard library only. Tried against a stub backend; the real run is `S7-AB2`.
- `docs/07-demo-script.md`: the evening-before steps, the rehearsal, the 4-minute demo
  as a table (do, say, should see), and the six fallback screenshots for
  `docs/screenshots/`. The deck's demo notes point to both.
- ADR-0005, second amendment: `hybrid` is calibrated since `ce147eb`, so the gap the
  first amendment described is closed. "Three hundred times" corrected to about 400,
  matching `ablations.md`, CONTEXT.md and the deck. Same fixes in
  `docs/06-defence-notes-b.md` and the comment in `frontend/src/lib/score.ts`.

### Checks
ruff, check_style, check_gold, validate_curricula, pytest (125 passed), frontend build.

### For A
Nothing blocks you. If you rebuild the deck halfway through `S5-A1`, it will now say
PROVISIONAL, which is intended.

### Next
- **Aleksandar:** run the rehearsal on the demo laptop, take the six screenshots, put the
  timings in the README. Then `S5-B1`.
- **Luka:** `S5-A1`.

---

## 2026-09-25 - [A] The percentage now says how good a match is, not only its rank

**Who:** Person A
**Stage:** 6
**Commit:** `[A] calibrate on cosine as well as the fused score`
**Tasks touched:** `S6-A4` (reworked), `S6-A5` (best candidate redefined)

### What was wrong
Running the app end to end, Calculus 1, Calculus 2 and Introduction to algebra against
Twente TCS all showed Software Diamond at 68 %, and 23 of 50 courses showed exactly
68 % at rank 1. The calibration was fitted on the fused score, and a fused score is
rank-based: being first in both BM25 and dense gives the same number whether the match
is perfect or the best of a bad lot. So the percentage measured rank agreement, the
ECTS headline was inflated, and a "no suitable match" state could never trigger. My
`hybrid` calibration from this morning had the same flaw as the older `hybrid+ce` one.

### Done
- `eval/fit_calibration.py` fits `p = sigmoid(a * z(score) + c * z(cosine) + b)`, where
  the cosine is the dense similarity of the pair, over both Twente programmes (1142
  pairs). `--score-only` keeps the old model. Cross-validated by home course:

  | `hybrid` calibration | Log loss | AUC | Top-1 p, right | Top-1 p, wrong |
  |---|---|---|---|---|
  | score alone | 0.273 | 0.87 | 0.60 | 0.47 |
  | score and cosine | 0.219 | 0.91 | 0.76 | 0.21 |

- `pipeline.py` passes the cosine into the calibration; old score-only files load and
  behave as before. The file keeps the `a` and `b` keys, so B's
  `core/calibration.py` needs no change.
- `aggregate.py`: the best candidate is the most probable of the five, not rank 1. With
  the cosine in the fit they differ in 8 of 80 queries.
- Both calibration files refitted. Reliability is close in every bin (0.48 predicted,
  0.48 observed).
- Through the API, `hybrid`, best candidate per course:

  | Home course | Twente TCS before | Twente TCS now | Twente Applied Maths now |
  |---|---|---|---|
  | Calculus 1 | 68 | 27 | 98 (Analysis 2) |
  | Introduction to programming | 64 | 87 | 70 |
  | Operating systems 1 | 68 | 84 | 6 |

  The likely band is no longer empty: 113 ECTS against TCS, 145 against Applied
  Mathematics.
- Five tests in `test_matching_aggregate.py`; `docs/05-evaluation.md` states the model
  and the table; deck slide 8 says why the cosine is there.

### Decisions
- The ranking is unchanged. Re-ranking by the calibrated probability would be a learned
  fusion trained on the labels it is evaluated on; it needs cross-validated evaluation
  after `S5-A1` before it can be a strategy.

### CONTRACT CHANGE
- Text only: the `hybrid` and `hybrid+ce` descriptions in `interface.py` still said
  hybrid "measured best on every metric" and that the reranker "loses", which stopped
  being true after `64f949c`. No field, type or endpoint changed, and
  `docs/04-api-contract.md` elides the descriptions, so it needs no edit. B has nothing
  to do about it.

### Request to B
Found by running the app with the real models, all in `frontend/src`:
- `App.tsx` defaults: home to `uns-pmf-informatics-bsc` and host to `utwente-tcs-bsc`
  when they exist, instead of the first two programmes. It opens on EPFL against KTH,
  two master's programmes, which is not the case the app is for.
- `RecognitionPanel.tsx` headline: "About 99.1 of 179 ECTS would likely be recognised"
  sits above "likely 0 ECTS". "Likely" is a bucket name there. Suggest "expected to be
  recognised", which is what `expected_recognised_ects` is.
- `EvaluationPanel.tsx` line 76 still says the reranker "measures worse than plain
  hybrid" and "500 times". Since the fusion change it is level, at about 400 times the
  cost. Same wording fix as ADR-0005.
- Optional, now that the percentage means something: show "no suitable match" when the
  best candidate is below 20 %. That is `S3-B1`'s floor, and 15 of 50 courses against
  TCS fall under it.

### Next
- **Luka:** `S5-A1`. The calibration is refitted from his labels automatically.
- **B:** the four items above, then `S5-B1`.

---

## 2026-09-25 - [A] Draft defence deck, generated from the eval outputs

**Who:** Person A
**Stage:** 7
**Commit:** `[A] draft the defence deck from the eval outputs`
**Tasks touched:** `S7-AB1` (wip, draft)

### Done
`docs/slides/build_deck.py` writes `docs/slides/erasmusgpt-defence.pptx`, eleven slides
in the order the task names: problem, pipeline, live demo, gold set, results, the
reranker finding, calibration and the ECTS estimate, error analysis, engineering,
limits. Speaker notes on each slide say who presents it.

The numbers are read, not typed: `eval/report/results.csv`, `kappa.md`, the correction
rate from the two gold files, and the reliability table from
`data/calibration/hybrid.json`. Until `S5-A1` the deck falls back to the provisional
ablation numbers and carries a PROVISIONAL LABELS tag on every slide that shows them.
After the labels land, one command rebuilds it.

python-pptx is a development tool here, like the notebooks, and never enters the image.

### For B
The engineering slide and the demo steps are yours to correct. Edit the generator, not
the pptx, or the next rebuild loses the change.

### Next
- **Luka:** `S5-A1`.
- **B:** `S5-B1`; a look at slides 4 and 10.

---

## 2026-09-25 - [A] Calibrate hybrid, and kappa ready for the cold slice

**Who:** Person A
**Stage:** 5 and 6
**Commit:** `[A] calibrate hybrid and add the kappa script`
**Tasks touched:** `S5-A3` (code done, waits on `S5-A1`), `S6-A1` (done), B's request

### B's request: a calibration for `hybrid`
`data/calibration/hybrid.json`, fitted by `fit_calibration.py` unchanged, as B expected.
Provisional like the `hybrid+ce` one, 562 Twente TCS pairs from the pre-labels:

| Predicted band | Pairs | Predicted | Observed |
|---|---|---|---|
| 0.0-0.2 | 420 | 0.05 | 0.05 |
| 0.2-0.4 | 65 | 0.30 | 0.28 |
| 0.4-0.6 | 50 | 0.51 | 0.48 |
| 0.6-0.8 | 27 | 0.67 | 0.78 |

`/recognition` with `hybrid` now returns `calibrated: true`, so B's panel shows the
whole-programme estimate on the default strategy again. Checked through the API against
both Twente programmes. Nothing reaches the likely band (p >= 0.7) under either strategy:
the curve tops out around 0.7 on these labels. That is the calibration being honest
about 83 positives in 562, and it is the first number to look at again after `S5-A1`.

### Kappa
`eval/kappa.py` compares B's cold slice with my checked labels: raw agreement,
unweighted and linearly weighted Cohen's kappa, a confusion table, and each of us
against the model's pre-labels. B against the model is the anchoring control, since B
never saw them. Seven hand-computed tests in `test_matching_kappa.py`. It exits 1 and
says why until `gold_pairs_b.csv` has labels.

### Paired tests
`run_eval.py` now tests `hybrid` against `dense-minilm` as well as `hybrid+ce`. `hybrid`
is what the app serves, so it is the claim the report has to defend.

### A test that pinned the display rule
`test_strategies_return_ranked_candidates[hybrid]` expected the top hit at 100 %, which
is the uncalibrated heuristic. It read whatever `data/calibration/` held, so the new
file broke it. The fixture now clears the calibration, and a separate test checks that a
calibrated strategy reports a probability that falls with rank.

### Also
- `CONTEXT.md` section 4 still said `hybrid+ce` "loses on every metric". Corrected to
  the fused result, the same fix B made in ADR-0005.
- `S6-A1` closed: four host programmes are live, which is what it asked for.
- Project state block said stage 2. It says stage 5 now.

### Verified
`ruff`, `check_style`, `check_gold`, 124 backend tests with `MATCHER_IMPL=stub`.

### Next
- **Luka:** `S5-A1`.
- **B:** `S5-B1`, the 30 cold pairs.
- **A:** once labels land: refit both calibrations, `run_eval.py` on both Twente
  programmes, `kappa.py`, rerun the error analysis, tick the stage 5 gate.

---

## 2026-09-21 - [B] Clean-machine build measured, and a healthcheck that would have failed

**Who:** Person B
**Stage:** 6. `S6-B2` done, so lane B is complete except the `S5-B1` labelling.
**Commit:** `[B] record the clean-machine build and widen the healthcheck`
**Tasks touched:** `S6-B2` (done)

### The run
After `docker system prune -a`, on Windows with Docker Desktop: **297 s for the full
build**, about 1 GB pulled. The CPU torch wheel is 126 s of it and the rest of the Python
dependencies 70 s; the models are only 30 s. Then five programmes, 298 courses,
`models_loaded: true`, `PipelineMatcher`, healthcheck green, nginx serving. The ingest log
reported all five curricula as new, which is right: the database volume was pruned too.

### What the run quietly hid
Every programme logged `embedding cache hit`. That is only true because `data/.cache/` was
still on the host from earlier runs. The cache is git-ignored, so **a genuinely fresh
clone has none**, and the first boot has to encode roughly 596 course vectors and 3096
sentence vectors with bge-small on CPU before the API can answer its first health probe.

The healthcheck allowed `start-period=90s` with five retries. On a slower machine a cold
encode can outlast that, the container gets marked unhealthy, and because the frontend
waits on `service_healthy` it never starts at all. So the one-command promise would have
failed on exactly the machine the promise is for: somebody else's, with a fresh clone.

Widened to `start-period=300s` with ten retries, with the reason written above the line.
A generous window costs nothing when startup is fast.

This is the value of `S6-B2` as a task. The build number was the point of it; the defect
it exposed is worth more.

### Recorded
The README now carries the real 297 s, its breakdown, and the distinction between a warm
start and a cold one, instead of the "5 to 10 minutes" guess that was there before.

### Broken / known issues
- The cold-start encode time itself is still unmeasured. Whoever next clones fresh should
  time it and put the number in the README beside the build time.

### Next
- **B:** `S5-B1`, the 30 cold pairs. That is the last thing in lane B.
- **A:** `S5-A1`, and a calibration for `hybrid`.

---

## 2026-09-21 - [B] Lane B reaches stage 6, and three robustness bugs it found

**Who:** Person B
**Stage:** 6, and `S7-B1` written. Lane B is level with lane A.
**Commit:** `[B] robustness sweep, ingest log, readme and defence notes`
**Tasks touched:** `S2-B3` `S6-B1` `S6-B3` `S7-B1` (done)

### S6-B3 found real holes rather than confirming there were none
I probed the API with ten bad requests instead of assuming it was fine. Three answers
were wrong, all in my zone:

- **`course_uids: []` returned all 50 courses.** The matcher reads a falsy list as "no
  filter", so asking for nothing got you everything. Now an explicit empty list returns
  an empty result.
- **An unknown course id was silently dropped.** A typo in a course id returned a
  cheerful 200 over the courses it did recognise. Now 404, naming the ids it did not know.
- Validation for `top_k`, `strategy` and `ects_budget` was already correct, which is worth
  recording too: pydantic returns 422 rather than a 500.

Both fixes are in `app/api/routes_match.py`, validated before the call rather than
inside Person A's matcher, and covered by five tests.

### S2-B3, the last stage 2 leftover
`app/db/ingest_log.py` records one row per curriculum at startup, keyed by a hash of the
**courses** rather than of the file, so a re-scrape that only moves `scraped_at` reads as
the same data. It never fails the boot: an unwritable database is logged and swallowed,
because the JSON files are the source of truth and this table is bookkeeping (ADR-0002).

Writing the test caught a flaw in my own code: `record_curricula(settings)` took a
settings object and then used the module-level engine, so `database_url` was ignored and
the "unwritable database" test passed for the wrong reason. It builds its own engine now,
which makes the argument honest and the test meaningful.

### S6-B1 and S7-B1
The README now opens with **what we found** rather than what we hoped to find: the
ablation table, the fused-versus-replacing distinction, and the sentence that these are
provisional because no human has checked a label yet. `docs/06-defence-notes-b.md`
answers the engineering questions, one short answer each, every one naming the file it
lives in: why the protocol exists, why SQLite, why the models are in the image, why one
strategy shows a percentage and the others do not, why `hybrid` is the default when the
proposal promised a cross-encoder, and what stops us breaking each other's work.

### Verified
`ruff`, `check_style`, `check_gold`, `validate_curricula`, 95 backend tests, `tsc`.
`test_api_ingest_log.py` needs Python 3.11 for `datetime.UTC`, as `run_eval.py` already
does; it passes under a shim here and runs normally in CI and the image.

### Broken / known issues
- `S6-B2`, the clean-machine timing, needs somebody to actually prune and rebuild. It is
  the one lane B task an agent cannot finish.
- `S5-B1` is 30 unlabelled pairs waiting for a person.

### Next
- **B:** label the cold slice, then the clean-machine run.
- **A:** `S5-A1`, and a calibration for `hybrid` so the recognition estimate works on the
  default strategy.

---

## 2026-09-21 - [B] ADR-0005 amended, and the panel stops doing arithmetic on display scores

**Who:** Person B
**Stage:** 5 and 6
**Commit:** `[B] amend adr-0005 and stop estimating ects without a calibration`
**Tasks touched:** none; a correctness fix and a doc correction

### Reviewed A's four commits
`64f949c` `7f80102` `214411c` `30e9424`. No lane B file touched, 90 tests pass, ruff,
style, `check_gold` and `validate_curricula` all clean, and `/strategies`,
`/recognition` and `/evaluation` all still work against the new engine. Fusing the
reranker instead of letting it replace the ranking is the right call and the end-to-end
run in `30e9424` is the first time anyone checked B's defaults against A's engine
together.

### ADR-0005 amended rather than left standing
The ADR said `hybrid+ce` "loses on every metric". After `64f949c` that is false: fused,
it wins Recall@5 on Twente TCS and wins P@1 and MRR on Applied Mathematics. Leaving the
claim in place would be the same drift A corrected in himself in `6d75b24`, so the ADR
now carries the new table and a narrower reason: `hybrid` stays the default because it is
level and three hundred times cheaper, not because the reranker is bad. The reranker is
no longer a negative result, it is a result about how to combine one.

### The bug that fix exposed on my side
Only `hybrid+ce` has a calibration. With `hybrid` as the default, `score_pct` is a display
value, and the recognition panel was still printing "About 108 of 180 ECTS would likely be
recognised" from a sum of `ects x display_score`. Warning underneath while keeping the
headline was having it both ways. The panel now refuses the whole-programme estimate for
an uncalibrated strategy, says why, and keeps the per-course table, which needs no
probability.

### Request to A
Fit a calibration for `hybrid` as well. Since `64f949c` standardises the scores before
fitting, `fit_calibration.py` should handle it unchanged. Until then the recognition
estimate, which is the feature that makes this more than a course comparator, only works
on a strategy that is not the default.

### Next
- **B:** label the 30 cold pairs in `data/gold/gold_pairs_b.csv` (`S5-B1`), then `S6-B1`
  to `S6-B3`.
- **A:** `S5-A1`.

---

## 2026-09-21 - [A] End-to-end smoke test, and a tie-breaking fix it found

**Who:** Person A
**Stage:** 6
**Commit:** `[A] break rrf ties with the reranker score`
**Tasks touched:** none; verification of what is already in

### The run
Started the API locally with `MATCHER_IMPL=real` against all five programmes:

- `/health` reports `models_loaded: true`, five programmes, 298 courses.
- `POST /match` with B's new default (`hybrid`): **50 home courses in 108 ms**.
- Computer networks returns Network Systems Part 2, 3 and 1, with an evidence pair that
  reads like an explanation rather than a paragraph.
- `POST /match/course` with `hybrid+ce`: 0.8 s for one course.

So B's ADR-0005 defaults and my engine changes work together, which nothing had checked
until now.

### What it found
Every match in a response showed the same percentage: 41, 41, 41. Fusing the reranker
into the ranking left the score as an RRF value, and RRF scores are coarse. Two
candidates at the same pair of ranks are exactly equal, so the API showed three matches
as equally likely and the ECTS estimate treated them that way.

Fixed by adding a ten-thousandth of the reranker's own score to the fused score. That is
smaller than the smallest gap RRF can produce between adjacent ranks, so it never
reorders anything, and it makes the percentages distinguish: Databases 1 now reads 62,
52, 29, 26 where it read one number four times.

Where ties remain they are honest. Network Systems Parts 1, 2 and 3 publish the same
module description, so the system is right to score them equally.

### Next
- **Luka:** `S5-A1`.

---

## 2026-09-21 - [A] Defence notes, and lane A is done bar the labels

**Who:** Person A
**Stage:** 7
**Commit:** `[A] write the defence notes for the nlp and ir questions`
**Tasks touched:** `S7-A1` (done)

### Done
`docs/06-defence-notes-a.md`: prepared answers for why RRF rather than score
normalisation, why a cross-encoder at all and why it is not the default, why these three
models, why BM25 and not Lucene, what the confidence intervals mean, what `score_pct` is
after calibration, how the gold set was pooled and what its two biases are, and the
limits to state before an examiner finds them.

The awkward question is anticipated in writing: if the reranker lost, did the project
fail? The answer is that the comparison is the project, and a measured negative with an
explanation is worth more than an untested claim.

### State of lane A
Everything in my lane is now done except what the labelling pass gates: `S5-A1` is
Luka's, `S5-A3` needs checked rows before a real `results.md` can exist, and `S6-A3`
(fine-tuning) needs them before it is worth starting.

### Next
- **Luka:** `S5-A1`. Whole home courses at a time; a query only counts once all its pairs
  are judged, so 15 complete courses beat 600 scattered rows.
- **A:** on the day the labels land: refit the calibration, re-run `eval/run_eval.py`,
  regenerate the error analysis and the ablations, then decide about `S6-A3`.

---

## 2026-09-21 - [A] Error analysis. The common failure is not a ranking failure

**Who:** Person A
**Stage:** 6
**Commit:** `[A] add the error analysis`
**Tasks touched:** `S6-A2` (done, provisional)

### The numbers
`eval/error_analysis.py` lists the queries where the first acceptable answer lands
worst. With `hybrid`, the default since ADR-0005:

| Host programme | Queries | Right at rank 1 | Nothing relevant in the top 10 |
|---|---|---|---|
| Twente Technical Computer Science | 28 | 24 | 1 |
| Twente Applied Mathematics | 22 | 18 | 1 |

### The finding
The most common way this system is wrong is that **it answers when it should decline**.
Introduction to algebra against a computer science faculty has no right answer, and the
ranker returns Software Diamond at 100 % because 100 % means "the best of these", not
"good". Five home courses have no acceptable match in either Twente catalogue and still
get five candidates each.

That is not a ranking defect, it is a missing threshold, and it sits on B's board as
`S3-B1`. The same course against Applied Mathematics finds Algebra at rank 1, which is
the evidence that the data was the problem and not the model.

The rest, with examples, in `eval/report/errors.md`: granularity mismatch (the right
answer is half of a 15 ECTS module), project courses that are textually
indistinguishable from every other project, and one level collision where Modelling and
Programming 3 outranks 1 because the sequence number is invisible to the ranker by
design (ADR-0004).

### Note for B on ADR-0005
The ADR was written before the fusion change. `hybrid+ce` no longer scores 0.68 P@1; it
is 0.82 against TCS and 0.86 against Applied Mathematics, level with `hybrid` rather
than far behind. The decision to default to `hybrid` still looks right to me on latency
alone, 2 ms against 850, but the evidence table inside the ADR is now out of date and
should quote the fused numbers at the defence.

### Next
- **A:** defence notes (`S7-A1`).
- **Luka:** `S5-A1`, which turns every provisional number in the last three entries real.

---

## 2026-09-21 - [A] Fusing the reranker rescues it

**Who:** Person A
**Stage:** 6
**Commit:** `[A] fuse the reranker into the ranking instead of replacing it`
**Tasks touched:** `S4-A2` (reworked), `S6-A4` (calibration made robust)

### Done
- `hybrid+ce` no longer lets the cross-encoder overrule retrieval. Its order is fused
  with the retrieval order by RRF, the same way `hybrid` fuses BM25 and dense.

| Twente TCS | P@1 | Recall@5 | MRR@10 |
|---|---|---|---|
| `hybrid` | 0.86 | 0.80 | 0.90 |
| reranker replaces (before) | 0.68 | 0.72 | 0.77 |
| reranker fused (now) | 0.82 | 0.82 | 0.88 |

  Against Applied Mathematics the fused version wins on P@1 (0.86) and MRR (0.91). The
  reranker goes from worst of four to level with the best, which is what it should have
  been all along: one opinion among three, not a veto.
- Sentence-level matching was tested and **not** adopted: 0.46 P@1 alone against 0.86
  for `hybrid`. One shared sentence is easy to find between any two technical courses.
  Written up anyway, since the granularity problem is in `docs/01-universities.md` as a
  known hazard and this is the evidence about it.

### A bug this exposed, worth knowing about
Fusing changed the score from a cross-encoder probability (0..1) to an RRF score (about
0.02). The calibration then fitted a flat curve and predicted 15 % for every pair: the
gradient vanishes when the feature never moves. `fit_calibration.py` now standardises
the scores before fitting and stores the mean and standard deviation alongside the
coefficients, so any strategy can be calibrated regardless of its range. The reliability
table is honest again: 0.05 predicted against 0.04 observed, 0.47 against 0.47.

### Where the recognition estimate stands
With the fused strategy and the refitted calibration, a Computer Science path scores
95.5 of 180 ECTS expected recognised against Twente TCS, 53 %, with 163 ECTS borderline
and nothing yet in the likely band. Provisional, as always, until `S5-A1`.

### Next
- **A:** error analysis (`S6-A2`) on the provisional labels, then the defence notes.
- **Luka:** the labelling pass. Instructions are in `tools/README.md`; do whole home
  courses rather than skimming, because a query only counts when all its pairs are judged.

---

## 2026-09-20 - [B] ADR-0005 accepted: hybrid is the default. Stage 5 lane B

**Who:** Person B
**Stage:** 5. Stage 2, 3 and 4 gates ticked, both lanes.
**Commit:** `[B] make hybrid the default and close stage 5 lane B`
**Tasks touched:** `S5-B2` `S5-B3` (done), `S5-B1` (wip), ADR-0005 written

### The decision
A's recommendation accepted: `hybrid` is the default, `hybrid+ce` stays implemented and
selectable, and the comparison becomes the project's main result rather than a footnote.
Reasoning and the measurement table are in `docs/adr/0005-hybrid-is-the-default.md`.

Changed: the three request defaults in `app/schemas/match.py`, the UI default in
`App.tsx`, the blurbs in `interface.py`, `docs/04-api-contract.md`, `CONTEXT.md` section 4,
`README.md` and `docs/00-map.md`. Nothing in lane A had to move.

**CONTRACT CHANGE:** `MatchRequest`, `SingleCourseMatchRequest` and `RecognitionRequest`
now default to `hybrid`. A caller that sent no strategy gets a different and much faster
one. Any caller that wants the reranker names it.

### A consequence A should know about
The only calibration in `data/calibration/` is for `hybrid+ce`. With `hybrid` as the
default, `score_pct` is no longer a probability on the default path, so the recognition
panel drops its share and says why. **Refitting the calibration for `hybrid` is `S6-A4`
again**, and it needs `S5-A1` first. Until then the panel is honest rather than pretty.

### Stage 5 lane B
- `S5-B1` is drawn but not done. `scripts/make_kappa_slice.py` samples 30 pairs,
  stratified over the model's label distribution so the slice is not 30 obvious zeroes,
  and **strips every label on the way out**. `data/gold/gold_pairs_b.csv` has 30 rows over
  25 home courses, all blank. Labelling them is a person's job and deliberately not the
  agent's: if these were filled in automatically, kappa would measure two machines
  agreeing and the number would be worthless. Aleksandar labels them in
  `tools/annotate.html` without opening `gold_pairs.csv` first.
- `S5-B2`: CI now also runs `validate_curricula.py` and a new `scripts/check_gold.py`,
  which catches the things that silently corrupt an evaluation - a duplicate pair counted
  twice, a course id that no longer exists after a re-scrape, a label that is not 0, 1 or
  2, a row marked checked with no label, and pairs present in the pre-labels but missing
  from the gold file. Both are in the README's pre-push list, because a check that only
  exists in CI is a check nobody runs.
- `S5-B3`: `GET /api/v1/evaluation` plus a "how well does this work?" panel. It reports
  how far the human pass has got (0 of 1142 today), lists the reports in `eval/report/`,
  and where there is no `results.csv` it says so instead of inventing a table. The panel
  leads with the cross-encoder finding, because that is the honest headline.
  `docker-compose.yml` mounts `./eval/report` read-only, since `eval/` is not in the image.

### Verified
`ruff`, `check_style`, `check_gold`, `validate_curricula`, 89 backend tests, `tsc` and
`npm run build`, all clean.

### Next
- **B:** sit down and label the 30 cold pairs, then `S6-B1` to `S6-B3`.
- **A:** `S5-A1`. Everything provisional turns real there, including the ADR above.

---

## 2026-09-20 - [B] Lane B catches up: stages 2 to 4, plus the recognition panel

**Who:** Person B
**Stage:** 2, 3 and 4 lane B closed. `S6-B4` pulled forward, marked done.
**Commit:** `[B] score display, export, compare mode and the recognition panel`
**Tasks touched:** `S2-B1` `S2-B2` `S3-B1` `S3-B2` `S3-B3` `S4-B1` `S4-B2` `S4-B3` `S6-B4` (done)

### CONTRACT CHANGE
Three additions to `app/schemas/match.py`, all additive. Nothing existing changed shape.

- `StrategyInfo` gains `calibrated` and `provisional`, both defaulting to false.
- New `RecognitionRequest`, `CourseOutcome`, `RecognitionResponse` for `POST /api/v1/recognition`.
- `app/matching/interface.py` re-exports `summarise` and `RecognitionSummary` from
  `aggregate.py`, so `app/api/**` keeps its rule of importing only the interface and the
  factory from the matching package.

**A: nothing of yours has to change.** The endpoint calls `match_programme` and your
`summarise`. `docs/04-api-contract.md` needs the new endpoint written up, which is mine.

### S3-B1, the part that was actually wrong
`score_pct` means three different things: a fitted probability for `hybrid+ce`, a
stretched cosine for `dense`, a per-query relative for `bm25` and `hybrid` where the top
row is always 100. The UI was printing all three on the same badge.

`frontend/src/lib/score.ts` is now the only place allowed to format a score. Calibrated
strategies get the recognition bands and a tooltip reading "estimated 91 % chance a
coordinator would recognise this pair"; the others get neutral grey badges and a tooltip
saying the number is relative and not a probability. `GET /api/v1/strategies` carries
`calibrated` and `provisional` so the frontend does not have to guess, and
`app/core/calibration.py` reads the same `data/calibration/` directory the pipeline
reads rather than asking the matcher, so nothing in lane A had to change.

### The ECTS denominator, resolved against A's version
I first filtered the home courses in the endpoint, which got UNS PMF from 353 ECTS down
to 270 but still counted courses offered on a path rather than taken on one. A's
`aggregate.study_path()`, which landed in `fb5f457`, does it properly: compulsory
courses, then the chosen module, then electives until the budget is full.

`POST /api/v1/recognition` now delegates. It matches every home course and passes
`module` and `ects_budget` to `summarise`, because filtering first would hide the
electives `study_path` needs to choose between. `module="Computer Science"` with
`ects_budget=180` returns exactly 180.0 ECTS over 26 courses. The frontend sends the
programme's own `total_ects` as the budget, so the panel reads "of 180 ECTS".

### Also
- CSV export (`S3-B2`): one row per suggested pair, with a `score_meaning` column so a
  coordinator reading it knows whether the number is a probability.
- Compare mode (`S3-B3` and `S4-B2` together): any row expands to re-run that one course
  under another strategy via `/match/course`, shown underneath. This only became
  testable once the real pipeline differentiated strategies.
- The panel refuses to pretend: an uncalibrated strategy gets a warning instead of a
  share, and a provisional calibration says so in the panel, not just in a JSON field.

### Verified
- `ruff`, `check_style`, 81 backend tests (8 new in `test_api_recognition.py`), `tsc`,
  `npm run build`, all clean.
- Drove the built bundle headless against mocked responses: module selector, recognition
  panel and its provisional warning, calibrated vs relative badges with the right
  tooltips, compare mode fetching and rendering, and the CSV download firing with the
  right filename. No console errors.

### Broken / known issues
- `S2-B3`, SQLite persistence, is still todo. Nothing depends on it yet.
- The band vocabularies are no longer a problem: A tied `confidence_of` to
  `aggregate.py`'s cut-offs in `fb5f457`, so high/medium/low and
  likely/borderline/unlikely now share one set of thresholds. `score.ts` already used
  those numbers, so nothing here changed.

### Next
- **B:** `S5-B1`, the cold 30-pair slice for Cohen's kappa, before I ever see A's
  corrected labels. Then `S2-B3`.

---

## 2026-09-20 - [A] The cross-encoder does not earn its place

**Who:** Person A
**Stage:** 6, with a finding that reaches back into stage 4 and into `CONTEXT.md`.
**Commit:** `[A] measure the reranker properly and write up the ablations`
**Tasks touched:** `S6-A2` (started), `S4-A2` (called into question)

### The finding
Over the pooled labels, against Twente TCS, 28 queries:

| Strategy | P@1 | Recall@5 | MRR@10 | ms/query |
|---|---|---|---|---|
| `bm25` | 0.86 | 0.75 | 0.91 | 2 |
| `dense` | 0.75 | 0.77 | 0.81 | <1 |
| **`hybrid`** | **0.86** | **0.80** | **0.90** | 2 |
| `hybrid+ce` | 0.68 | 0.72 | 0.77 | 979 |

Against Applied Mathematics the reranker draws on P@1 and MRR and loses on recall. So
the configuration `CONTEXT.md` calls "the product" is the worst of the four, and the
slowest by three orders of magnitude.

The reason looks like task mismatch, not a bug: `ms-marco` cross-encoders are trained on
short web queries against passages, and both sides here are 1400-character course
descriptions.

### What was tried to rescue it
- **A shorter query side.** Giving the reranker the title plus one sentence instead of
  the whole document lifts P@1 from 0.54 to 0.68. Adopted (`document.rerank_query`).
- **Three other rerankers in the budget.** `ms-marco-L12` 0.57, `stsb-TinyBERT-L-4`
  0.29, `stsb-distilroberta-base` 0.18. The sentence-similarity models are much worse,
  which is informative in itself: a course description is neither short nor a sentence.
- Neither closes the gap to `hybrid`.

### Two improvements that stand on their own
- `embedder.QUERY_INSTRUCTION`: bge expects an instruction on the query side and we were
  not using one. Recall@5 0.78 -> 0.87 against Applied Mathematics, P@1 unchanged. The
  query side now has its own cached matrix per programme.
- The 256-token window is confirmed as better, and B's explanation for why is refuted by
  a direct test: removing the learning outcomes makes every metric worse.

### Everything is written up
`eval/report/ablations.md` carries all five ablations with the caveat at the top: these
labels were written by a model and no human has checked them, so they can choose between
settings but cannot go in the report as results.

### Decision needed, for A and B together
1. Make `hybrid` the default and present the reranker as a measured negative result.
2. Keep `hybrid+ce` and defend shipping the slower, worse option.
3. Fine-tune the reranker on the gold set (`S6-A3`), which is the version where the
   original claim could survive. Needs the human pass first.

My recommendation is 1 now and 3 if there is time, with the ablation table as a centre
piece of the report rather than an appendix. Changing the default strategy touches
`CONTEXT.md`, `docs/04-api-contract.md` and the UI default, so it is not mine to make
alone.

### Next
- **Luka:** `S5-A1`. Everything above is provisional until those rows are checked.

---

## 2026-09-20 - [A] KTH ingested. Four host programmes

**Who:** Person A
**Stage:** 6
**Commit:** `[A] add the kth scraper and curriculum`
**Tasks touched:** `S6-A1` (the >= 4 host programmes half of the gate is met)

### Done
- `backend/scripts/scrape_kth.py` plus `data/curricula/kth-cs-msc.json`: 79 courses of
  the MSc Computer Science, in English, with contents and intended learning outcomes.
- The API now serves five programmes: PMF 50, Twente TCS 40, Twente Applied Mathematics
  51, EPFL 78, KTH 79. Startup encodes all of them in 55 s cold, instantly from cache.

### Sample of what KTH gives us
Artificial intelligence 1 -> Artificial Intelligence and Applied Methods (65 %). Formal
languages and automata -> Automata and Languages (56 %). Computer networks -> Protocols
and Principles of the Internet (60 %). Databases 1 finds nothing above 19 %, because
this year-1 master's list has no database course, and the system says so rather than
inventing one.

### Decision worth knowing about
The KTH programme syllabus page is a JavaScript app and the KOPPS API returned 502 all
day, so the course codes live in `data/curricula/kth-cs-msc.codes.txt`, with a comment
saying where they came from and when. The course pages themselves are plain server-
rendered HTML, so everything else is scraped normally. Refreshing the list is a yearly
job, not a per-run one.

### Catalogues that were tried and rejected, so nobody repeats the work
- **Delft**: the study guide is a single-page app, the programme list is paginated in
  JavaScript, and no plain API answered. Expensive, revisit only if we want a Dutch BSc.
- **DTU**: every plain request is bounced through a JavaScript login loop.
- **Masaryk**: `is.muni.cz` returned an empty body to a plain request.
- **ETH**: course ids in the VVZ are session-bound.
- **EPFL, KTH**: server-rendered and easy. Both done.

### Next
- **A:** the query-side instruction that bge-small expects for retrieval is not being
  used; worth an ablation like the token-length one. Then the error analysis.

---

## 2026-09-20 - [A] B's two reviews, worked through

**Who:** Person A
**Stage:** 5 and 6
**Commit:** `[A] answer b's review: coverage, denominator, bands, contract`
**Tasks touched:** `S5-A0` (extended), `S6-A1` (wip), `S6-A4`, `S6-A5`

### CONTRACT CHANGE - `score_pct` means different things per strategy
No schema field changes. `MatchCandidate.score_pct` is still an integer 0..100, ordered
within a strategy. What changed is its meaning, which the contract described as
"calibrated 0..100 for display" when it was nothing of the kind.

- `hybrid+ce`: a calibrated probability, fitted on the gold set.
- `dense`: a cosine stretched from 0.55-0.95 onto 0-100.
- `bm25` and `hybrid`: relative to the best hit for that home course, so rank 1 is
  always 100.

`docs/04-api-contract.md` now carries the table. **B:** show a percentage only for
`hybrid+ce`; for the others show a rank or a band. Fitting calibrations for the other
three would remove the distinction, and it is cheap once the labels are checked.

### Coverage: fixed, and not the way B proposed
B's count was right: 13 of 40 home courses had an outright match, 12 had nothing at all.
Pooling EPFL would not have fixed it. I checked before labelling: EPFL's MSc has no
calculus, no linear algebra and no academic English, so those 12 would have collected
another 150 zeros.

The real gap was that Twente's mathematics is taught by **Applied Mathematics**, a
different coordinating unit in the same catalogue. One argument to the existing scraper
ingests it: `data/curricula/utwente-am-bsc.json`, 51 courses. Pooled and pre-labelled,
580 more pairs.

| | before | after |
|---|---|---|
| home courses with an outright match | 13 | 26 |
| with any positive | 28 | 35 |
| with nothing | 12 | 5 |

The five left are both Software Labs, both English courses and Financial mathematics.
No engineering faculty teaches those, and the report should say so rather than pretend.

### The denominator was wrong (B's item 1)
`summarise()` now takes `module` and `ects_budget`, so the answer is about a degree
somebody could take: compulsory courses first, then the chosen module, then electives
until the budget is full. Against Twente TCS the Information Technologies path scores
36 % of 180 ECTS and Computer Science 26 %; against Applied Mathematics it is the other
way round, 24 % and 29 %. Those numbers are still provisional, from pre-labels.

### One set of bands (B's item 4)
`aggregate.LIKELY` and `BORDERLINE` are now the only thresholds in the system;
`pipeline.confidence_of()` maps them onto the contract's high/medium/low, and
`BUCKET_OF_CONFIDENCE` maps back. A test asserts the two can never disagree. I kept the
contract's vocabulary rather than retiring it, because changing the enum would break
`frontend/src/lib/api.ts` for no gain: same thresholds, two names, one source.

### B's item 5 was a good hypothesis and it is wrong
B suggested the 512 to 256 token gain and the evidence bug shared a cause: the learning
outcomes block at the tail of the document. Measured over 28 queries:

| | P@1 | Recall@5 | MRR@10 |
|---|---|---|---|
| 512 tokens, full document | 0.57 | 0.53 | 0.68 |
| 256 tokens, full document | 0.54 | 0.65 | 0.67 |
| 512 tokens, outcomes dropped | 0.50 | 0.47 | 0.60 |

Dropping the outcomes makes everything worse, so the tail carries signal. Shortening the
window trades 0.03 of P@1 for 0.12 of Recall@5 at 2.5 times the speed. 256 stays, and
the ablation goes in the report.

### Also done
- The evidence splitter (B's item 3): `document.sentences()` splits on `;` and drops the
  field label, so the panel quotes one outcome instead of a seven-clause paragraph.
- `--positive-label` is documented in `docs/05-evaluation.md`, with an instruction to
  report both the optimistic and strict figures, since the gap is most of the headline.
- The stage 6 note in `TASKS.md` no longer reads as though A were quoting himself.
- Pulled both line-ending commits before touching anything.

### Next
- **Luka (S5-A1):** 1142 rows now await a human pass. Read the Twente TCS rows first,
  then Applied Mathematics. Every number above becomes real, and the calibration refits
  in one command, the moment rows are checked.
- **A:** more universities, or the error analysis, whichever B prefers.

---

## 2026-09-20 - [A] Calibrated scores and the ECTS recognition estimate

**Who:** Person A
**Stage:** 6, pulled forward. This is the feature that turns a course comparator into
something a student can act on, so it goes before more universities.
**Commit:** `[A] calibrate scores and estimate recognised ects`
**Tasks touched:** `S6-A4`, `S6-A5` (done)

### Done
- `eval/fit_calibration.py` fits `p = sigmoid(a * score + b)` on the gold labels by plain
  gradient descent, no new dependency, and writes `data/calibration/hybrid-ce.json`. The
  pipeline loads it at startup, so `score_pct` is now a probability rather than a
  display number. Where no calibration exists the old heuristics still apply and the app
  works as before.
- The fit is honest on its own data: pairs predicted at 0.10 were matches 10 % of the
  time, at 0.27 they were 23 %, at 0.48 they were 50 %. That table is saved in the file.
- `matching/aggregate.py` sums the per-course probabilities into
  `expected recognised ECTS = sum of p(best) x ECTS(home)`, with likely, borderline and
  unlikely buckets and a separate `ects_shortfall` where the host course carries fewer
  credits. The arithmetic and every rule behind it are written into
  `docs/05-evaluation.md`.
- 12 new tests. 91 in total, still offline.

### The first real numbers
Against Twente, 24 % of the 353 ECTS pooled here would be expected to be recognised,
with 108 ECTS borderline, none yet likely, and a 50 ECTS shortfall where host courses
are smaller. Against EPFL's master's, 22 %. Both are provisional: the calibration is
fitted on my pre-labels, not on checked ones, and the file says so.

### A latency regression, found and fixed with a measurement
The real 40-course Twente catalogue pushed `hybrid+ce` to **157 s for a programme**, over
the 120 s ceiling in `S4-A4`. The cross-encoder was running at 512 tokens over documents
of about 1400 characters. At 256 tokens it is 2.4 times faster, and measured against the
pre-labels over 28 home courses it is not worse but better: P@1 and MRR@10 unchanged,
Recall@5 up from 0.51 to 0.65. A whole programme is now **65 s, 1.3 s per query**.

### Request to B
`score_pct` is now a calibrated probability for `hybrid+ce`, which is what `S6-B4` needs.
`aggregate.summarise()` and `aggregate.as_dict()` produce the summary payload; the
endpoint that exposes it is yours, since `app/api/**` is your zone. Nothing in the frozen
contract changes.

### Next
- **A:** `S6-A1`, more universities, cheapest catalogue first.
- **Luka:** `S5-A1`, the human pass over `data/gold/gold_pairs.csv`. Everything
  provisional above becomes real the moment those rows are checked, and I refit in one
  command.

---

## 2026-09-20 - [A] Gold set pooled and pre-labelled, 562 pairs

**Who:** Person A
**Stage:** 5. `S5-A0` done. `S5-A1`, the human pass, is next and only a human can do it.
**Commit:** `[A] pool and pre-label the gold set`
**Tasks touched:** `S5-A0` (done)

### Done
- Pooled the union of the top 10 from `dense` and `hybrid+ce` over 40 PMF courses against
  the real Twente catalogue: **562 pairs, 14.1 per home course**. 238 were found by both
  strategies, 324 by one only.
- Pre-labelled all 562 by reading both course texts against the rubric in
  `docs/05-evaluation.md`, the question being whether a coordinator would sign the host
  course off in place of the home one. Result: **17 twos, 66 ones, 479 zeros.**
- `data/gold/llm_prelabels.csv` is written and frozen. `data/gold/gold_pairs.csv` is the
  working copy, same labels, every row `checked=no`.
- `pool.csv` now goes to `data/.cache/`, not `data/gold/`. It quotes course text verbatim
  and is regenerable, so it does not belong in the repository.

### What the labels say about the data
- **12 of the 40 home courses have no acceptable match at all**: both Calculus courses,
  Linear algebra, Analytic geometry, Numerical analysis, Algebra, both English courses,
  Financial mathematics, and both Software Labs. Twente's mathematics line is run by
  Applied Mathematics and is not in our slice of the catalogue, and nobody teaches
  academic English or a software tools lab there. A third of the programme therefore has
  no correct answer available, and the system still returns five candidates for each.
- Only 17 pairs are outright matches. The clean ones are the obvious ones: Computer
  networks against all three Network Systems parts, Operating systems 1, Computer
  architecture, Databases 1, Information systems 1 against Software Design and Modelling.

### Honesty note for the report
The pre-labels come from the same model family that the pipeline uses for matching. I
labelled from the course texts alone and did not look at which strategy proposed a pair
or at its rank, but the correlation cannot be ruled out, and `S5-A1` exists precisely to
break it. The correction rate from diffing the two files is the number that shows whether
the human pass was real, and it belongs in `results.md`.

### Next
- **Luka (S5-A1):** open `tools/annotate.html`, load `data/gold/gold_pairs.csv`, read each
  row and press Enter to accept or change the label. Only `checked=yes` rows reach the
  metrics, so today `eval/run_eval.py` still has nothing to measure.
- **A:** once rows are checked, run the evaluation and write `eval/report/results.md`.

---

## 2026-09-20 - [A] Three real curricula land. Stage 1 closed

**Who:** Person A
**Stage:** 1 closed, both lanes. Current stage moves to 2, where lane A is already done.
**Commit:** `[A] land the real twente and epfl curricula`
**Tasks touched:** `S1-A2` (done), `S6-A1` (wip)

### I edited a file in B's zone, with A's explicit approval
`scripts/check_style.py` applied the banned-word and sentence-pattern rules to
`data/curricula/*.json`. Those files quote universities word for word, and
`docs/03-data-schema.md` says the text is stored as published. Twente's prose broke six
rules, EPFL's broke eleven, all of it ordinary prospectus English. Editing a university's
wording to satisfy our style guide would make the data wrong.

The change is four lines: files under `data/curricula/` skip the word and pattern checks.
**The ASCII check still applies to them**, because `course_uid`s and the eval harness
depend on ASCII. Every other file is unaffected.

**B: this is your file. Say so if you want it reverted or written differently.** The rule
itself came from the initial scaffold rather than from anyone's decision, and it had
never met real scraped data.

### Done
- `data/curricula/utwente-tcs-bsc.json`: 40 real courses, 2025-2026, replacing the
  9-course sample. `data/curricula/epfl-cs-msc.json`: 78 courses.
- The API now serves three programmes: PMF 50, Twente 40, EPFL 78.
- `eval/report/smoke.md` regenerated against the real Twente catalogue.
- `data/README.md` updated: no placeholders left.

### What the real data shows, good and bad
- **Right:** Computer networks -> Network Systems Part 1, 2, 3 at 92, 88, 87 %.
  Software engineering -> Software Design and Modelling. Against EPFL, Formal languages
  and automata -> Computational complexity, with Goedel and recursivity third.
- **Wrong, and worth writing up in S6-A2:** Databases 1 ranks Information Diamond first
  at 82 % and the actual Databases course third at 53 %. Computer networks against EPFL
  returns Network machine learning at 96 %, a topical trap rather than an equivalent.
- **Structural:** the real Twente catalogue has no automata course, so Formal languages
  and automata gets an answer anyway (Introduction to Artificial Intelligence, 47 %).
  There is no concept of "no acceptable match" in the contract. Worth raising at the
  defence, and worth a threshold discussion with B for the UI.

### Next
- **A:** `S5-A0` pooling, then pre-labelling, which unblocks the whole of stage 5.

---

## 2026-09-20 - [A] EPFL scraper, and what language costs us

**Who:** Person A
**Stage:** 6 - more curricula, pulled forward. `S6-A1` is `wip`: scrapers land, data does not.
**Commit:** `[A] add the epfl scraper`
**Tasks touched:** `S6-A1` (wip, early)

### Done
- `backend/scripts/scrape_epfl.py`. `edu.epfl.ch` renders on the server and gives one
  English page per course with Summary, Content, Keywords and Learning Outcomes, which
  maps onto our schema almost field for field. It produces **78 courses** for MSc
  Computer Science, every one with a description and topics, and the validator passes.
- `validate_curricula.py` now separates errors from notes. A prerequisite naming a course
  outside the file used to be an error; for a master's catalogue that is normal, since
  EPFL's MSc courses require EPFL bachelor courses. It is reported as a note instead.

### The language question, answered with a measurement
Adding German or Dutch curricula is not free. `bge-small-en-v1.5` and `ms-marco-MiniLM`
are English-only (ADR-0001), and the smallest multilingual bi-encoder worth using,
`multilingual-e5-small`, is about 470 MB, which breaks the 400 MB image budget on its
own. So the rule is to ingest the **English-taught** programme at each university, which
for Munich, Graz, Vienna, Zurich and Lausanne means the master's. `docs/01-universities.md`
now carries the table of which programme to take at each of the eight universities.

### Broken / known issues
- **The style checker now blocks every curriculum file, not just Twente's.** EPFL's own
  course text trips 11 rules, four distinct banned words and one banned pattern, all of
  them ordinary prospectus English. Universities write marketing prose; our style rules
  exist for prose we write. Both the
  Twente and EPFL JSON files are parsed, cached and held back.
- Delft and ETH need more work than EPFL did: Delft's study guide is a JavaScript app
  with no plain API found yet, and ETH's VVZ uses session-bound course ids.

### Request to B (second time, now larger)
`scripts/check_style.py` has to skip the banned-word and sentence-pattern checks for
`data/curricula/`, keeping the ASCII check. Until it does, no real curriculum can be
committed, which blocks the gold set, the evaluation, and every university after Twente.

### Next
- **A:** Delft and JKU Linz if the checker is resolved; there is no point scraping more
  data that cannot be committed.

---

## 2026-09-20 - [A] Pooling script for the gold set

**Who:** Person A
**Stage:** 5. `S5-A0` stays blocked: the script is written, the run needs real data.
**Commit:** `[A] add the gold set pooling script`
**Tasks touched:** `S5-A0` (blocked, script written)

### Done
- `eval/make_pool.py` pools the union of the top 10 from `dense` and `hybrid+ce` per home
  course and writes `data/gold/pool.csv` (both course texts, and which strategy and rank
  found the pair) plus an empty `data/gold/llm_prelabels.csv` to fill in.
- It refuses to overwrite `llm_prelabels.csv` once it exists. That file is the frozen
  record the correction rate is measured against, and a re-run must not quietly replace it.
- Trial run against the Twente sample: 45 pairs over 5 home courses, 9 per course. With
  the real 40-course catalogue and 40 home courses, expect 500 to 600 pairs, which
  matches the estimate in `docs/03-data-schema.md`.

### Broken / known issues
- Nothing in lane A can now progress without the real Twente file. `S5-A0` needs it to
  pool against, `S5-A1` needs the pool, `S5-A3` needs the labels, and stage 6 starts by
  ingesting another university, which would hit the same style checker problem.

### Next
- **A:** waiting on the style checker request to B, the one in the entry of 2026-09-20
  titled "Twente scraper written, its data held back".

---

## 2026-09-20 - [A] The image was baking 724 MB of models, not 220 MB

**Who:** Person A
**Stage:** housekeeping while lane A is blocked
**Commit:** `[A] stop baking duplicate model weights`
**Tasks touched:** none directly. It breaks a rule in AGENTS.md, so it gets fixed now.

### The problem
`backend/scripts/download_models.py` pulled whole repositories minus a few formats.
Hugging Face repositories publish the same weights several times: `pytorch_model.bin`
next to `model.safetensors`, and MiniLM adds a Rust `rust_model.ot`. Each is the full
model, and torch loads exactly one of them.

| Repository | Was | Now |
|---|---|---|
| `BAAI/bge-small-en-v1.5` | 268 MB | 134 MB |
| `sentence-transformers/all-MiniLM-L6-v2` | 273 MB | 92 MB |
| `cross-encoder/ms-marco-MiniLM-L6-v2` | 183 MB | 92 MB |
| **Total** | **724 MB** | **318 MB** |

AGENTS.md allows ~200 MB per model and 400 MB in total. The build was over both, by a
lot, and nothing checked.

### Done
- The downloader keeps safetensors when a repository has them and skips `.bin`, `.pt`,
  `.pth`, `.ckpt` and `.ot`. Repositories without safetensors are unaffected, since the
  patterns are chosen per repository from its file list.
- It prints each model's size and **exits 1 if one model passes 200 MB or the set passes
  400 MB**, so the build fails rather than the image quietly growing.
- Measured figures are in `docs/02-models.md`, replacing the "~220 MB" estimate.
- `eval/README.md` now covers `make_smoke.py` and says what each script needs.

### Note for B
The image should shrink by roughly 400 MB on the next `docker compose build`. Nothing in
`backend/Dockerfile` changes: it still calls this script the same way.

### Next
- **A:** still blocked on the style checker before the Twente data and the gold set can
  land.

---

## 2026-09-20 - [A] Evaluation harness and metric tests

**Who:** Person A
**Stage:** 5 - Gold set and evaluation, taken early. The harness runs; it has nothing to
measure until the gold set exists.
**Commit:** `[A] finish the evaluation harness`
**Tasks touched:** `S5-A2`, `S5-A4` (done, early), `S5-A3` (wip)

### Done
- `eval/run_eval.py` is implemented. It imports `app.matching` rather than
  reimplementing scoring, runs every configuration in `CONFIGS`, and writes
  `eval/report/results.md` and `results.csv` with Recall@5, Recall@10, MRR@10, nDCG@10,
  P@1 and ms/query.
- Statistics (`S5-A3`): 95 % percentile bootstrap intervals over queries and a paired
  bootstrap test of `hybrid+ce` against `dense-minilm`, both seeded so the report
  reproduces. The report states in words whether each gain is significant, and discloses
  the pre-labelling and the correction rate.
- `backend/tests/test_matching_metrics.py`, 18 tests with values computed by hand,
  including an nDCG worked through for a swapped pair. 79 tests in total, all offline.

### Verified
Run end to end on a throwaway gold file of 12 queries with random labels, writing to a
temporary directory: the table, the intervals, the paired test and the CSV all come out.
The numbers were nonsense by construction, which is the point of the exercise.

### Decisions
- `CONFIG_SETUP` maps a configuration name to (bi-encoder, strategy) in one place, so
  `dense-minilm` cannot silently report numbers produced by bge.
- An empty gold set exits 1 with the task IDs to run, rather than writing an empty report
  that looks like a result.
- The paired test resamples query pairs, not queries independently: both configurations
  answer the same queries, and discarding that pairing would overstate the uncertainty.

### Broken / known issues
- `S5-A3` stays `wip`: the code is written but no real report can be produced until the
  gold set exists, and that needs the real Twente data.

### Next
- **A:** blocked on B for the style checker. `S5-A0` (pooling) and `S5-A1` (labelling)
  both need the real Twente file to be worth doing, and stage 6 starts with ingesting
  Masaryk, which would hit the same checker problem. Waiting.

---

## 2026-09-20 - [A] Cross-encoder reranking, evidence, smoke sheet

**Who:** Person A
**Stage:** 4 - Cross-encoder rerank, taken early. Lane A is now through its stage 3 and
stage 4 gates.
**Commit:** `[A] add cross-encoder reranking and evidence`
**Tasks touched:** `S3-A3`, `S4-A1`, `S4-A2`, `S4-A3`, `S4-A4` (done, early)

### Done
- `matching/reranker.py`: batched `CrossEncoder` over (home, host) pairs, sigmoid-squashed
  to 0..1 inside the module. Nothing outside needs to know it emits logits.
- `strategy="hybrid+ce"`: RRF -> `candidate_top_n` -> rerank -> `top_k`.
- Evidence (`S4-A3`): every course's sentences are embedded once at startup, and the
  evidence for a pair is the most similar sentence pair between the two courses. No model
  call during a request.
- Latency guard (`S4-A4`): a request may score at most 1500 pairs. Candidates past the
  budget keep their fused order, so a huge request degrades instead of hanging.
- `eval/make_smoke.py` writes `eval/report/smoke.md`: 10 home courses x 4 strategies with
  evidence and per-strategy latency. That is `S3-A3`.

### Verified with both real models on CPU
- Startup 24 s, both models loaded. A `hybrid+ce` query is 400 ms; a whole 50-course
  programme is 19.5 s, well inside the 45 s the task asks for. BM25 2 ms, dense under 1 ms.
- Ranking looks right where it matters: Formal languages and automata -> Theory of
  Computation, Computer networks -> Network Systems, Databases 1 -> Data and Information,
  Data structures and algorithms 1 -> Algorithms and Data Structures. The reranker
  separates the winner from the rest far better than cosine does: 21 % against 6 % for the
  runner-up where dense had 82 % against 42 %.
- Evidence reads like an explanation. For Data structures and algorithms 1 it quotes
  "Implementation of various data structures (list, stack, queue...)" against Twente's
  "Fundamental data structures such as lists, trees, heaps, hash tables and graphs".

### Decisions
- The cross-encoder is loaded in `_warm()`, not on first use. Lazily, the first
  `hybrid+ce` request paid 17.5 s for the model load and looked like a hung demo. Startup
  now costs that instead, once.
- `PipelineMatcher` takes an optional `reranker`, so tests inject a fake and CI never
  downloads a model. All 61 tests run offline in 3 s.
- The pair cap lives in `reranker.py` as a constant, not in `Settings`: `app/core/config.py`
  is Person B's file. If it should be configurable, that is a request to B, not an edit.

### Broken / known issues
- Cross-encoder percentages are low in absolute terms (rank 1 often 10 to 30 %) because
  ms-marco was trained on search relevance, not course equivalence. The ranking is sound;
  the number is not meaningful yet. Calibration is `S3-B1`, and the smoke sheet says so
  in its own words.
- The smoke sheet is against the 9-course Twente **sample**. Re-run `eval/make_smoke.py`
  once the real file lands.

### Next
- **A:** `S5-A0`, pooling the pairs worth labelling. That needs the real Twente data to be
  worth doing, so it waits on B's answer about the style checker.

---

## 2026-09-20 - [A] BM25 and hybrid fusion

**Who:** Person A
**Stage:** 3 - Lexical and hybrid, taken early. `S3-A3` (smoke sheet) still open.
**Commit:** `[A] add bm25 and wire hybrid fusion into the pipeline`
**Tasks touched:** `S3-A1`, `S3-A2` (done, early)

### Done
- `matching/lexical.py`: `BM25Index` over the same `build_document()` text the
  bi-encoder embeds, using `rank_bm25.BM25Okapi` with default k1 and b.
- `strategy="hybrid"` in the pipeline: both retrievers return `candidate_top_n` (25),
  fused by `reciprocal_rank_fusion` at `rrf_k` (60).
- The tokenisation is written down in `docs/05-evaluation.md` under "The BM25 baseline,
  exactly as implemented". It is the number everything else is compared against, so it
  has to be reproducible from the document alone.
- `backend/tests/test_matching_lexical.py`, 16 tests, including S3-A2's acceptance:
  fusion never loses a candidate that either input found.

### Verified with the real model
Per home course, top 3, against the Twente sample:

| Home course | bm25 | dense | hybrid |
|---|---|---|---|
| Formal languages and automata | Theory of Computation | Theory of Computation | Theory of Computation |
| Computer networks | Network Systems | Network Systems | Network Systems |
| Databases 1 | Data and Information | Data and Information | Data and Information |

A whole programme (50 home courses, hybrid, top 5) takes 72 ms once warm. BM25 costs
about 2 ms per query, dense under 1 ms.

### Decisions
- No stemming in the tokeniser. It is an ablation worth measuring in stage 5, not a
  default to assume. Same reasoning for leaving k1 and b untuned: a tuned baseline and
  an untuned one are different claims, and the report has to say which one it made.

### Broken / known issues
- **Display scores for bm25 and hybrid are misleading, and this is B's `S3-B1`.** RRF
  scores sit very close together, so ranks 2 and 3 read 96 % and 97 %. BM25 shows
  "English 1" matching a computer science course at 96 %. The ranking is fine; the
  percentage is not. `relative_pct` in pipeline.py is a placeholder that scales against
  the best hit for the same home course, and `S3-B1` replaces both it and
  `score_to_pct` with one calibration.

### Next
- **A:** `S4-A1` the cross-encoder reranker, then `S4-A2` `hybrid+ce`. `S3-A3`, the
  smoke sheet, comes after that so it can cover all four strategies at once.

---

## 2026-09-20 - [A] Dense retrieval works, stage 2 lane A pulled forward

**Who:** Person A
**Stage:** 2 - Dense retrieval, taken early because `S1-A2` is blocked on B.
**Commit:** `[A] implement the bi-encoder embedder and dense retrieval`
**Tasks touched:** `S2-A1`, `S2-A2`, `S2-A3`, `S2-A4` (all done, early)

### Done
- `matching/embedder.py`: loads the bi-encoder lazily, encodes each programme once and
  caches to `data/.cache/{programme}.{tag}.npy` with a sidecar `.json` holding a
  SHA-256 of the concatenated documents. A changed curriculum re-encodes; an unchanged
  one loads in 0.1 s.
- `matching/dense.py`: exact cosine over the normalised matrix (`DenseIndex`). Ties break
  on course order so the eval harness sees a stable ranking.
- `matching/pipeline.py`: `PipelineMatcher` with `strategy="dense"`. Every programme is
  encoded in `__init__`, which runs in the FastAPI lifespan, so no request ever encodes.
  The other three strategies raise NotImplementedError, as planned for this stage.
- `backend/tests/test_matching_dense.py`, 17 tests, no model downloaded: the bi-encoder is
  replaced by a hash-based fake, so CI stays offline and the suite runs in 2 s.

### Verified with the real model (bge-small-en-v1.5, CPU)
- **The lane A gate: "Formal languages and automata" finds "Theory of Computation" at
  rank 1, cosine 0.878.** Computer networks -> Network Systems (0.817), Operating
  systems 1 -> Computer Systems (0.800), Databases 1 -> Data and Information (0.807).
- Cold start 43 s, almost all of it loading the model. Second start 0.1 s from cache.
  Matching all 50 PMF courses against Twente takes under 10 ms once warm.

### Decisions
- `score_to_pct` in pipeline.py is a placeholder until `S3-B1`, which owns calibration.
  Raw cosines here run 0.63 (unrelated) to 0.88 (best pair), so it stretches 0.55 to 0.95
  onto 0 to 100. Without that, "English 1" scored 57 % against a computer science course.
- Embeddings are cached per programme and model tag, so switching `BI_ENCODER` between
  bge-small and minilm does not invalidate the other model's cache. The eval sweep in
  stage 5 needs both.

### Broken / known issues
- Verified against the **sample** Twente file, since the real one is held back (see the
  entry below). The PMF side is real.
- torch 2.5.1 does not import on this Windows machine until `libiomp5md.dll` in
  `torch/lib` is copied to `libomp140.x86_64.dll`, and `transformers` picks the
  TensorFlow path unless `USE_TF=0` is set. Both are local environment quirks, not the
  project's: the Docker image is Linux and unaffected.

### Next
- **A:** `S3-A1` BM25, then `S3-A2` hybrid fusion. Both are in my lane and need nothing
  from B.

---

## 2026-09-20 - [A] Twente scraper written, its data held back

**Who:** Person A
**Stage:** 1 - Real data, real surface. Lane A gate still open: `S1-A2` is blocked.
**Commit:** `[A] add the twente osiris scraper`
**Tasks touched:** `S1-A2` (blocked)

### Done
- `backend/scripts/scrape_utwente.py`. Osiris is a single-page app over a JSON API, found
  by watching the requests the app makes:
  - `POST /student/osiris/student/cursussen/zoeken` lists courses, filtered by
    `collegejaar` and `coordinerend_onderdeel_oms`.
  - `GET /student/osiris/owc/cursussen/{id}` returns one course, with Content
    (`item-inhoud-3`) and Aim(s) (`item-inhoud-4`) as HTML.
  - Both answer HTTP 500 unless the request carries a `taal: EN` header. That header is
    the whole trick; everything else is a normal JSON request.
- Run against 2025-2026 it produces 40 courses, 213 ECTS, every one with a description,
  and `validate_curricula.py` passes on it.

### Decisions
- **Scraping 2025-2026, not 2026-2027.** Osiris publishes a year one quartile at a time.
  As of today the 2026-2027 catalogue has 9 of year 1's units; 2025-2026 has all of them
  (Diamonds, Software Systems, Network Systems, Data & Information).
- Superseded units stay in the catalogue for resits. Units whose content says "only for
  repeat students" are dropped, and where a title is still listed twice the earliest study
  year wins, then the newest code.
- Osiris does not say which units belong to a programme's curriculum, only which
  department coordinates them. So the file covers the units TCS coordinates. The
  mathematics line, run by Applied Mathematics, is missing. Worth stating at the defence:
  it makes the Twente side smaller than the real programme.

### Request to B
- `scripts/check_style.py` applies the banned-word list to `data/curricula/*.json`. The
  Twente course text hits one of the banned connectives 6 times (the one meaning "in
  addition", which the checker names). That text is the university's, quoted as
  published (`docs/03-data-schema.md`), so it cannot be edited to suit our style rules.
  Please skip the banned-word and sentence-pattern checks for `data/curricula/`, keeping
  the ASCII check. **Until then the scraped file is held back** and the sample Twente file
  stays committed, so CI stays green. Re-running the scraper writes the real file in a few
  seconds; nothing needs to be scraped again.

### Broken / known issues
- `data/curricula/utwente-tcs-bsc.json` is still the 9-course sample. Anyone evaluating
  against Twente before this unblocks is measuring against placeholder data.

### Next
- **A:** waiting on B for the checker. Meanwhile pulling stage 2 lane A forward
  (`S2-A1` embedder, `S2-A2` dense search), marked `early`.

---

## 2026-09-19 - [A] Curriculum validator

**Who:** Person A
**Stage:** 1 - Real data, real surface
**Commit:** `[A] add the curriculum validator`
**Tasks touched:** `S1-A3` (done)

### Done
- `backend/scripts/validate_curricula.py`: checks every `data/curricula/*.json` (or the
  files named on the command line) against `docs/03-data-schema.md`. It checks field
  presence and types, with no nulls in string or list fields, and that `programme_id`
  equals the file name. It also rejects duplicate codes, non-ASCII codes, non-positive
  ECTS and prerequisites that name no course in the programme. Standard library only.
- `backend/tests/test_matching_curricula.py`: the committed PMF file validates and meets
  the S1-A1 bar, and each broken variant (duplicate code, null description, renamed
  file, dangling prerequisite) is caught.

### Broken / known issues
- The validator currently exits 1, on purpose: `utwente-tcs-bsc.json` is still the sample
  with `scraped_at: null`. It goes green when `S1-A2` replaces that file.

### Request to B
- Add `python backend/scripts/validate_curricula.py` as a step in the `backend` job of
  `.github/workflows/ci.yml`, after `S1-A2` lands. Adding it before then turns CI red on
  the Twente sample.

### Next
- **A:** `S1-A2`. After it, lane A passes its stage 1 gate.

---

## 2026-09-19 - [A] Real UNS PMF curriculum, 50 courses

**Who:** Person A
**Stage:** 1 - Real data, real surface. Lane A is not through its gate yet: `S1-A2` and
`S1-A3` remain.
**Commit:** `[A] scrape the full uns pmf informatics curriculum`
**Tasks touched:** `S1-A1` (done)

### Done
- `backend/scripts/scrape_uns_pmf.py`: reads the three course tables on the PMF programme
  page, downloads each course's syllabus PDF into `data/.cache/uns-pmf-pdf/` (one request
  per second) and writes `data/curricula/uns-pmf-informatics-bsc.json`. `--offline`
  re-parses the cache without touching the network.
- `data/curricula/uns-pmf-informatics-bsc.json` replaced: 50 courses, every one with a
  description (objectives plus syllabus text) and learning outcomes. The loader reports
  `uns-pmf-informatics-bsc 50`, which meets the >= 45 criterion.
- `data/gold/gold_pairs.csv` cut to its header. The 10 placeholder rows pointed at sample
  codes (`I102`, `I307`, ...) that do not exist in the real curriculum.
- Notes on the source and its quirks in `docs/01-universities.md`; `data/README.md`
  updated.

### Decisions
- Kept all 50 courses, including English, Sociology and the finance electives. Dropping
  them would leave 43, under the acceptance bar, and a student can ask to have them
  recognised as well.
- Course codes changed from the sample scheme to the real one (`I021` Data structures and
  algorithms 1, `I142` Formal languages and automata). Anything that hardcoded a sample
  code needs the real one.
- `description` = learning objectives + syllabus, `learning_outcomes` = the minimum and
  desirable outcomes, `topics` = `[]`. The PDFs have no topic list, and inventing one
  would break the "store as published" rule.
- Scraper dependencies (`requests`, `beautifulsoup4`, `pypdf`) live in
  `backend/scripts/requirements-scrape.txt`, not in the image. They never ship, so no ADR.

### Broken / known issues
- `pypdf` splits a few words ("databas e", "appr iate"); 52 such fragments across 50
  files. Left as extracted. The bi-encoder tolerates them; BM25 will miss those tokens.
- Electives have `year` and `semester` null, because the source gives none.

### Next
- **A:** `S1-A2` Twente scraper, then `S1-A3` the validator. Those close lane A.

---

## 2026-09-18 - [B] Offline run verified. Lane B gate for stage 1 passed

**Who:** Person B
**Stage:** 1 - Real data, real surface. **Lane B gate passed.** Stage stays open until
lane A passes; A is on `S1-A1`.
**Commit:** `[B] drop the syntax directive and document the offline story`
**Tasks touched:** `S1-B2` (done)

### Verified on a real machine
Two runs. First, built with `MATCHER_IMPL=real` and `BAKE_MODELS=1`: the models
downloaded into the image in 34 s, the healthcheck went green and the nginx proxy served
the API same-origin. Then the network was disconnected and the stack started cold with
`docker compose up`, no `--build`:

- both containers started with no registry lookup,
- `loaded 2 programmes (19 courses) from /srv/data/curricula`,
- the backend healthcheck passed and compose reported the container healthy,
- the UI loaded at :8080 and `/programmes`, `/strategies`, `/health` and two
  `POST /match` calls all returned 200.

That is the acceptance criterion met with nothing reaching the network.

### Two findings

**1. `# syntax=docker/dockerfile:1` broke the offline build.** BuildKit resolves that
frontend image from Docker Hub on every build, so with the network off the build failed
before it reached a single instruction. We use nothing the built-in Dockerfile frontend
lacks, so the directive is removed from both Dockerfiles.

**2. The acceptance criterion for `S1-B2` was impossible as written.** It asked for
`docker compose up --build` to work with no network, but pip, npm and the model download
all need it. Only the *run* can be offline. Criterion rewritten: build once with the
network, then `docker compose up` without `--build` serves with the network disconnected.
The README now separates the two explicitly and gives the recipe for proving it.

### Also
- `GET /` on port 8000 returned a bare 404. It now redirects to `/docs`.

### Broken / known issues
- `MATCHER_IMPL=real` currently logs `NotImplementedError: S2-A3` and falls back to the
  stub. That is the fallback working as designed, not a fault: `PipelineMatcher` is
  Person A's stage 2 task. It does mean one thing is still unproven, namely that
  **loading real models offline** works, because there is no code loading them yet. Once
  `S2-A3` lands, repeat the offline check before calling it settled.

### Next
- **B:** stage 1 lane B is done. Next in my lane is `S2-B1` (strategy selector), which I
  can start early while A works on the curricula.
- **A:** `S1-A1`, then `S1-A2` and `S1-A3` to close the stage.

---

## 2026-09-18 - [B] Stage 1 lane B: the UI happy path and the curriculum browser

**Who:** Person B
**Stage:** 1 - Real data, real surface
**Commit:** `[B] finish the ui happy path and the curriculum browser`
**Tasks touched:** `S1-B1` (done), `S1-B3` (done), `S1-B2` (in progress)

### Done
- Split `App.tsx` into `ProgrammePicker`, `ResultsTable` and `CourseBrowser`. `App.tsx`
  is now a state machine with four phases: booting, ready, matching, failed.
- `lib/api.ts`: added `health()` and `courses()`, and gave every call an abort-based
  timeout. 20 s for the small endpoints, 150 s for `/match`, because a whole programme
  through the cross-encoder is slow by design. Network failures and aborts turn into
  sentences a person can act on rather than "Failed to fetch".
- Match runs show elapsed seconds, so a 40-second request does not read as a hang.
- Three states that used to fail silently now say what is wrong: fewer than two
  curricula loaded (names the `DATA_DIR` and the mount), the same programme picked on
  both sides, and the backend running the stub (says which two lines of `.env` to change).
- `CourseBrowser` (`S1-B3`) lists a programme's courses with expandable descriptions and
  **counts the courses whose description is empty**, listing their codes. That is exactly
  `S1-A1`'s acceptance criterion, so Person A can see his ingestion pass or fail in the
  browser without touching the matching code.
- A swap button between the two dropdowns, and a footer showing backend version, active
  matcher and whether models are loaded.
- `frontend/Dockerfile` now copies `package-lock.json` and runs `npm ci` instead of
  `npm install`, so the image build is reproducible.
- The config path fallback logs at debug rather than warning: it fires during
  `docker build`, before the data volume exists, and a warning there is misleading.

### Verified
- `ruff check backend eval scripts`, `scripts/check_style.py`, 11 backend tests, `tsc`
  and `npm run build` all clean.
- Drove the built bundle in a headless browser against mocked API responses: the stub
  warning, the footer, the browser panel and its empty-description warning, the
  same-programme guard disabling the button, the busy label, the elapsed timer, the
  results table, the "no candidate" row and the evidence panel. No console errors.

### Broken / known issues
- `S1-B2` is not finished. Everything in the repository is in place, but nobody has yet
  run the real build with `BAKE_MODELS=1` and confirmed the container serves with the
  network disconnected. That run is the remaining work, and it cannot be done from CI
  because CI builds with `BAKE_MODELS=0`.

### Next
- **B:** `S1-B2`, the offline build verification.
- **A:** `S1-A1`. The browser panel will tell you whether the descriptions came through.

---

## 2026-09-18 - [B] Fix the lint failure CI caught, and close the gap that let it through

**Who:** Person B
**Stage:** 1. Housekeeping.
**Commit:** `[B] fix E501 in fusion.py and lint eval and scripts in ci`
**Tasks touched:** none

### Done
- `backend/app/matching/fusion.py` had a 144-character docstring first line, left behind
  when the task IDs were renamed to stage IDs. Split across two lines.
- The real problem was that the documented pre-commit list in `README.md` deliberately
  left `ruff` out and said "CI runs the same three plus `ruff check backend`". Nothing
  local caught it. `ruff` is now in the local list and in the definition of done in
  `AGENTS.md`.
- CI linted only `backend`. It now lints `backend eval scripts`, so `eval/run_eval.py`
  and `scripts/check_style.py` are covered too. Both pass.

### Decisions
- Whatever CI runs, the README tells you to run locally, in the same order and with the
  same arguments. A check that only exists in CI is a check nobody runs before pushing.

### Next
- **B:** `S1-B1`, then `S1-B2`.
- **A:** `S1-A1`.

---

## 2026-09-18 - [B] Second consistency pass

**Who:** Person B
**Stage:** 1. Housekeeping, no stage movement.
**Commit:** `[B] second consistency pass`
**Tasks touched:** none

### Done
Eight more disagreements, found by reading the remaining docs end to end and by an
automated cross-check of referenced paths, task IDs and model names.

- `eval/README.md` still said `results.csv` is git-ignored, one commit after it stopped
  being ignored, and `S5-B3` reads that file from the repository.
- `CONTEXT.md` section 10 still described stage 5 as ">=100 labelled pairs". It is ~500
  checked pairs over 40 home courses.
- `CONTEXT.md` stage 0 row ended with a stray "done" left over from the emoji removal.
- `S5-A0` said ~400 pairs while `S5-A1` and `docs/05-evaluation.md` said ~500.
- Stage 5 lane B listed `S5-B1` above `S5-B0`, and `S5-B0` had a status in its
  acceptance-criterion column. It is now `done (early)`, which is what the rule in
  `TASKS.md` actually prescribes for pulled-forward work.
- `docs/02-models.md` showed a Dockerfile snippet that predated `BAKE_MODELS`.
- `AGENTS.md` capped models at "~500 MB on disk", which read as if it applied to the
  Colab-only models too. It now caps what is baked into the image: ~200 MB per model,
  under 400 MB in total, with bigger models allowed in `notebooks/`.
- One aphoristic sentence in `docs/05-evaluation.md` that section 11 bans.

Also added, because both will be asked about:

- A short **"On Lucene"** note in `CONTEXT.md` section 3 and in
  `docs/02-models.md`: the assignment allows Lucene or transformers, we took the
  transformers branch, and BM25 here is `rank_bm25` rather than Lucene or PyLucene.
  BM25 is the ranking function Lucene is known for, so the question will come up.
- `eval/report/.gitkeep`, so the directory survives a clone.
- `docs/00-map.md` had no owner in section 7. It is shared.

### Verified
- `scripts/check_style.py` clean, 11 backend tests pass, `tsc` and `npm run build` clean.
- Both curricula parse and carry the required fields; `gold_pairs.csv` has exactly the
  four agreed columns and no course id that is missing from the curricula.
- `load_gold()` returns only checked rows; `correction_rate()` runs.
- Every task ID referenced anywhere in the repository exists in `TASKS.md`.
- Every model id in the docs is either in `config.py` or explicitly marked Colab-only.
- `BAKE_MODELS`, `MATCHER_IMPL`, `DATA_DIR` and `VITE_API_BASE` agree across
  `.env`, `.env.example`, `docker-compose.yml` and both Dockerfiles.

### Next
- **B:** `S1-B2`, then `S1-B1`.
- **A:** `S1-A1`.

---

## 2026-09-18 - [B] Consistency audit across the repository

**Who:** Person B
**Stage:** 1. Housekeeping, no stage movement.
**Commit:** `[B] reconcile docs and code after the gold-set redesign`
**Tasks touched:** none

### Done
Nine places where the repository disagreed with itself, all found by reading the docs
against the code rather than by anything failing.

- **Embedding cache path.** `docs/02-models.md` said `data/curricula/*.npy` and
  `CONTEXT.md` said "next to the curriculum", while `embedder.py`, `TASKS.md` and
  `.gitignore` all said `data/.cache/`. Following the docs would have written generated
  `.npy` files into the committed curricula directory. All now say `data/.cache/`.
- **Recall@25.** Listed as a primary metric, but a depth-10 pool cannot support it.
  Primary metric is now Recall@10; Recall@25 is a depth-25 subset spot check, kept out
  of the main table. Fixed in `docs/05-evaluation.md`, `eval/run_eval.py` and `TASKS.md`.
- **`eval/run_eval.py` ignored `checked`.** It would have mixed unread machine proposals
  into the metrics. It now skips them and reports how many it skipped.
- Added `correction_rate()` to the same file: diffs `llm_prelabels.csv` against the
  checked labels. That number is what the report quotes as evidence of the human pass.
- **`scripts/`** had no owner in `CONTEXT.md` section 7. It is Person B's.
- **`eval/report/*.csv` was git-ignored** while `S5-B3` plans to read `results.csv` from
  the repository to render the evaluation page. Results are a deliverable, so they are
  committed now.
- **`frontend/Dockerfile` never declared `ARG VITE_API_BASE`**, so the build argument
  compose passes was silently discarded. Declared, defaulting to `/api/v1`.
- `data/README.md` listed only one of the three gold files.
- Repository maps in `README.md` and `AGENTS.md` were missing `tools/`, and `TASKS.md`
  was still described as a backlog rather than a staged board.

### Decisions
- Generated artefacts never live in a committed data directory. `data/curricula/` is
  source, `data/.cache/` is derived.
- A metric goes in the main table only if the pool depth we actually label supports it.

### Next
- **B:** `S1-B2`, then `S1-B1`.
- **A:** `S1-A1`.

---

## 2026-09-18 - [B] Annotation tool, and a smaller gold-set schema

**Who:** Person B
**Stage:** 5 work pulled forward (lane B), marked `early`. Current stage stays 1.
**Commit:** `[B] add the gold-set annotator`
**Tasks touched:** `S5-B0` (done), `S5-A1` unblocked

### Done
- `tools/annotate.html` plus `tools/annotate.js`: a standalone `file://` page that loads
  the curricula JSON and the pairs CSV, shows the two courses side by side with
  descriptions, outcomes and topics, and labels them from the keyboard. `0` `1` `2` set
  the label, `Enter` accepts and advances, `Ctrl+S` saves.
- Saving uses the File System Access API, so in Chrome and Edge it writes straight back
  to `gold_pairs.csv`. Elsewhere it downloads a copy. Loading `llm_prelabels.csv` clears
  the write handle, so the frozen pre-label file can never be overwritten.
- Local storage keeps a backup of checked rows between sessions, wrapped in try/catch
  because it is a convenience and not the file.
- The header tracks checked and corrected counts live. The corrected count is the number
  the report quotes.
- Dropped the `note` column from `gold_pairs.csv`. Four columns now:
  `home_uid,host_uid,label,checked`. Reasoning about a correction belongs in the error
  analysis, not in a column nobody reads back.
- `docs/05-evaluation.md` gained a "How many rows" section: 40 home courses and about
  500 pairs is the target, 25 courses and 320 pairs the minimum, with what that does to
  the confidence intervals.

### Decisions
- The tool is a local page rather than a route in the application. It is evaluation
  tooling, not product, and it must not need Docker or a running backend.
- `tools/**` belongs to Person B in `CONTEXT.md`, even though Person A is the only user.

### Broken / known issues
- `[hidden]` needed `display:none !important` because `#setup` sets `display:grid`, which
  beats the user-agent rule. Fixed, but worth remembering in the React app too.

### Next
- **B:** back to `S1-B2`, then `S1-B1`.
- **A:** `S1-A1`. `S5-A1` is ready whenever the pool exists.

---

## 2026-09-18 - [B] Configure everything through .env

**Who:** Person B
**Stage:** 1 - Real data, real surface
**Commit:** `[B] move runtime switches into .env`
**Tasks touched:** `S1-B2` (in progress)

### Done
- `.env` is now the only place runtime switches live. `MATCHER_IMPL` and the new
  `BAKE_MODELS` both go there, and every documented command is a plain
  `docker compose up --build`.
- `.env.example` ships with the fast pair, `MATCHER_IMPL=stub` and `BAKE_MODELS=0`, and
  explains what to change for the real pipeline.
- `Settings` reads `backend/.env` and then the repository root `.env`, so the same file
  configures both `docker compose` and a local `uvicorn app.main:app --reload`. Before
  this, a local run ignored the root file and silently fell back to `real`.
- Removed the bash-only `VAR=x command` prefixes from the README. They do nothing in
  PowerShell or CMD, which is what we are both on.

### Decisions
- No runtime switch gets documented as a command-line prefix. If it is configuration, it
  goes in `.env`. CI is the exception and sets real environment variables, which override
  the file.

### Next
- **B:** finish `S1-B2`, then `S1-B1`.

---

## 2026-09-18 - [B] Fix empty programme list inside Docker

**Who:** Person B
**Stage:** 1 - Real data, real surface. Unblocks anyone running the stack.
**Commit:** `[B] resolve data dir correctly inside the image`
**Tasks touched:** `S1-B2` (in progress)

### The bug
`app/core/config.py` computed `REPO_ROOT` as `Path(__file__).parents[3]`. From a
checkout that is the repository root, so everything worked locally and all tests passed.
Inside the image the application lives at `/srv`, so `parents[3]` is `/` and `data_dir`
became `/data` - which is the SQLite volume, not the curricula mount at `/srv/data`.
`CurriculumStore.reload()` found no directory, returned silently, and the API served an
empty programme list. The dropdowns were empty and nothing in the logs said why.

### Done
- `config.py` now derives `BACKEND_ROOT` from `parents[2]` (the application root in both
  layouts) and picks whichever of `<app root>/data` and `<app root>/../data` actually
  contains `curricula/`. `DATA_DIR` overrides it.
- `cache_dir` and a new `gold_dir` derive from `data_dir` instead of being separate
  defaults that could point somewhere else.
- `docker-compose.yml` pins `DATA_DIR=/srv/data` next to the `./data:/srv/data` mount, so
  the setting and the mount cannot drift apart.
- `CurriculumStore.reload()` logs an error naming the directory it looked in when it
  finds nothing, and logs the programme and course count when it succeeds.
- Added `backend/tests/test_api_config_paths.py`: both directory layouts plus an
  assertion that the resolved curricula directory exists and holds JSON.
- `Dockerfile` takes `BAKE_MODELS` (default 1). CI builds with `BAKE_MODELS=0` so the new
  `smoke` job can start the whole stack in about a minute.
- New CI job `smoke`: builds, starts compose, waits for the healthcheck, and fails unless
  `/api/v1/programmes` returns at least two programmes and the frontend answers on :8080.

### Decisions
- Walking a fixed number of parents to find the project root is banned. Derive paths from
  the application root and verify the directory exists.
- Any bug that only appears inside the image needs a test that runs inside the image.
  That is what the `smoke` job is for.

### Broken / known issues
- Adding the `BAKE_MODELS` argument changes the model-download layer, so the next full
  build re-downloads the models once. Builds after that are cached again.

### Next
- **B:** finish `S1-B2` (healthcheck timings, offline verification), then `S1-B1`.

---

## 2026-09-18 - [SETUP] Writing-style pass over the whole repository

**Who:** initial scaffold (bootstrap)
**Stage:** 0 (Scaffold), follow-up. Does not change the stage.
**Commit:** `normalise repository text to ascii and add a style check`
**Tasks touched:** none

### Done
- Every text file in the repository is now plain ASCII. Em dashes and en dashes became
  hyphens, curly quotes became straight quotes, the ellipsis character became three dots,
  arrows and maths symbols became `->`, `>=`, `~`, `x`.
- The box-drawing diagrams in `CONTEXT.md` and `README.md` were redrawn with `+ - | v`.
- Status markers in `TASKS.md` are words (`todo`, `wip`, `blocked`, `done`, `early`) and
  `[ ]` / `[x]` checkboxes instead of coloured squares and check marks.
- Rewrote the sentences that read as machine-generated: aphoristic paragraph endings,
  negation-then-reveal constructions, and marketing adjectives.
- Added `CONTEXT.md` section 11 (Writing style) with the character rules, the banned
  word list, the banned sentence patterns, and the formatting and commit-message rules.
- Added `scripts/check_style.py`, which enforces all of it, and a `style` job in CI.

### Decisions
- The pipeline steps inside `CONTEXT.md` are now called steps 0-3, not stages, so they
  no longer collide with the project stages in `TASKS.md`.
- British spelling throughout.

### Next
- Unchanged: Stage 1. A starts `S1-A1`, B starts `S1-B1`.

---

## 2026-09-18 - [SETUP] Repository scaffold - closes Stage 0

**Who:** initial scaffold (neither A nor B - bootstrap)
**Stage:** 0 (Scaffold) -> closed. Current stage is now **1 - Real data, real surface**.
**Commit:** `initial scaffold`
**Tasks touched:** Stage 0 complete; stages 1-7 laid out in `TASKS.md`

### Done
- Created the agent-facing docs: `AGENTS.md`, `CONTEXT.md`, `PROGRESS.md`, `TASKS.md`.
- Wrote `docs/01-universities.md` (partner shortlist + catalogue sources),
  `docs/02-models.md` (Hugging Face model choices), `docs/03-data-schema.md`
  (curriculum JSON schema), `docs/04-api-contract.md` (frozen REST contract),
  `docs/05-evaluation.md` (gold set + metrics protocol), and two ADRs.
- Scaffolded `backend/` (FastAPI app, routers, schemas, `Matcher` protocol,
  `StubMatcher`, empty real-pipeline modules), `frontend/` (React + Vite),
  `eval/`, `docker-compose.yml`.
- Added two sample curriculum files so the stub path returns something visible.

### Verified
- `pytest backend/tests` - 8 passed (`MATCHER_IMPL=stub`).
- `POST /api/v1/match` returns a full table end-to-end on the sample curricula; the stub
  already ranks *Data Structures and Algorithms* -> *Algorithms and Data Structures* first,
  so the plumbing is right even though the NLP is not there yet.
- `MATCHER_IMPL=real` correctly logs the missing pipeline and falls back to the stub
  instead of failing to boot - Person B is never blocked by Person A.
- `npm run build` in `frontend/` succeeds; `tsc -b` clean. (`node_modules/` is installed
  locally and git-ignored.)
- Docker images are **not** built yet - that is S1-B2.

### State after this entry
`docker compose up --build` is expected to serve the UI at http://localhost:8080 and the
API at http://localhost:8000/docs. No real model inference yet: every match comes from
`StubMatcher` (character-trigram Jaccard), which exists purely so the contract is exercised.

### Next - Stage 1
- **A:** `S1-A1` ingest the real UNS PMF curriculum -> `S1-A2` Twente -> `S1-A3` validator.
- **B:** `S1-B1` UI happy path -> `S1-B2` offline Docker build -> `S1-B3` course browser.

Neither lane blocks the other: B works against the stub and the sample data until A's
real curricula land, and nothing B does touches `data/` or `matching/`.

---

<!--
ENTRY TEMPLATE - copy from here, fill in, paste directly under the "---" above.

## YYYY-MM-DD - [A|B] Short title

**Who:** Person A | Person B
**Commit:** `<short sha or message>`
**Tasks touched:** T-0xx (done|in progress|blocked)

### Done
- bullet per meaningful change, with file paths

### Decisions
- anything a future agent would otherwise re-litigate. Big ones get an ADR in docs/adr/.

### CONTRACT CHANGE            (omit this section if nothing shared changed)
- what changed in schemas/ or interface.py or docs/04-api-contract.md
- what the other person must do about it

### Request to A|B             (omit if none)
- a change you need in the other person's zone

### Broken / known issues
- anything left failing, so the next agent does not "discover" it and waste time

### Next
- what you intend to pick up next, so the other person does not take it
- if you closed your lane's gate, say whether the stage is now closed or you are
  waiting on the other lane
-->
