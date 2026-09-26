# Error analysis (S6-A2)

Written by Person A on 2026-09-21 from the pre-labels, re-run on 2026-09-26 against the
final gold set, strategy `hybrid` (the default since ADR-0005). 680 of the gold rows
were checked by a human and 462 labelled by a second model (Claude); see
`data/gold/provenance.json`. Commands:

```bash
python eval/error_analysis.py --host-programme utwente-tcs-bsc
python eval/error_analysis.py --host-programme utwente-am-bsc
```

## Where it stands

| Host programme | Queries | Right at rank 1 | Nothing relevant in the top 10 |
|---|---|---|---|
| Twente Technical Computer Science | 27 | 21 | 1 |
| Twente Applied Mathematics | 19 | 16 | 0 |

So 37 of 46 queries put an acceptable course first, and 1 fails completely. A query is a
home course with at least one relevant course at that host, as the protocol defines it.
On the pre-labels it was 42 of 50: the final labels accept fewer partial matches, so
fewer home courses count as queries and slightly fewer are right first time.

The one complete failure is Introduction to algebra against TCS, and its only relevant
label is borderline: the Cybersecurity and Law Diamond, accepted as a partial match
(1) for its number theory. The second model labelled the same pair 0. The categories
below were written from the pre-label run; the examples still hold on the final labels.

## The failures, by category

The categories are the data hazards listed in `docs/01-universities.md`.

### No equivalent exists, and the system answers anyway (the most common failure)

Not in the original hazard list, and the one that matters most for a coordinator.

- **I121 Introduction to algebra** against Technical Computer Science: nothing relevant
  in the top 10. It returns Software Diamond at 100 %. A computer science faculty does
  not teach abstract algebra, so there is no right answer in that catalogue, and the
  ranking has no way to say so. The same course against Applied Mathematics finds
  Algebra at rank 1, which is the correct behaviour and shows the data, not the model,
  was the problem.
- Five home courses have no acceptable match in either Twente catalogue: both Software
  Labs, both English courses, Financial mathematics 1. The system still returns five
  candidates for each.

**This was an argument for a confidence floor in the UI rather than a ranking fix, and
the floor has shipped:** below 20 % the UI shows "no suitable match". The
ranking is doing its job: it orders the catalogue by similarity. Deciding that even the
best candidate is not good enough is a threshold question, which is `S3-B1` and B's
recognition panel.

### Granularity mismatch

Predicted in `docs/01-universities.md`, and visible.

- **I021 Data structures and algorithms 1** ranks Concurrency and Compiler Construction
  first and the correct Software Diamond second. Software Diamond is half algorithmics
  and half functional programming; the home course is entirely data structures. The
  correct answer is a fraction of a module, and a whole-module description dilutes it.
- **I011 Introduction to programming** against Applied Mathematics: the right answer,
  Modelling and Programming 1, is at rank 5 behind three modelling projects, because
  that unit teaches programming as a means to mathematical modelling.

Sentence-level matching was tried against exactly this and did not help; see section 1c
of `ablations.md`.

### Project courses look like each other

- **I331 Seminar paper A** fails on both hosts: rank 4 against TCS, nothing in the top
  10 against Applied Mathematics. Its description says "study a chosen discipline and
  present it", which is textually identical to every project, internship and thesis in
  both catalogues. The system cannot distinguish them, and perhaps neither can a
  reader: the courses differ by supervision and subject, not by text.

### Level collision

- **I032 Object-oriented programming 1** against Applied Mathematics puts Modelling and
  Programming 3 above Modelling and Programming 1. The numbered sequence is invisible to
  the model, which sees three near-identical descriptions. Course codes and levels are
  deliberately excluded from the embedded text (ADR-0004), and this is what that costs.

### Same name, different content

Not observed in the worst queries. The closest case is Databases 1 against Information
Diamond, which is correct rather than an error: the host course really does contain the
home material in one of its two halves.

## What would fix what

| Failure | Fix | Owner | Cost |
|---|---|---|---|
| No equivalent exists | confidence floor and a "no suitable match" state | B, `S3-B1` | done |
| Granularity mismatch | fine-tune the bi-encoder on the gold set | A, `S6-A3` | a day, needs labels |
| Project courses | nothing worth doing; note it as a limit | - | - |
| Level collision | expose the level or sequence number to the ranker | A, ADR-0004 revisit | medium, reopens a decision |

The first is the one a user would notice, and it is already on B's board.
