# eval/

Owner: **Person A**. Protocol: `docs/05-evaluation.md`.

```bash
python eval/run_eval.py --host-programme utwente-tcs-bsc --out eval/report
```

`report/` holds the generated tables. Commit both `results.md` and `results.csv`: the
Markdown so the numbers are reviewable in a diff, the CSV because `S5-B3` renders it as
the evaluation page in the app.
