# eval/

Owner: **Person A**. Protocol: `docs/05-evaluation.md`.

```bash
python eval/run_eval.py --host-programme utwente-tcs-bsc --out eval/report
```

`report/` holds the generated tables. `results.csv` is git-ignored; commit
`results.md` so the numbers are reviewable in a diff and end up in the defence.
