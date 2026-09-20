# eval/

Owner: **Person A**. Protocol: `docs/05-evaluation.md`.

```bash
python eval/run_eval.py --host-programme utwente-tcs-bsc --out eval/report
python eval/make_smoke.py            # 10 courses x 4 strategies -> report/smoke.md
```

`run_eval.py` needs a gold set with `checked=yes` rows and exits 1 with the task to run
if there is none. `make_smoke.py` needs no labels: it is for eyeballing that each
strategy still returns something sane, not for measuring.

Both import `app.matching`, so they exercise the code the API serves. A first run loads
the models and encodes each programme once; after that the embedding cache under
`data/.cache/` makes startup instant.

`report/` holds the generated tables. Commit both `results.md` and `results.csv`: the
Markdown so the numbers are reviewable in a diff, the CSV because `S5-B3` renders it as
the evaluation page in the app.
