# tools/

Standalone helpers. Not part of the application, not in the Docker image.

## `annotate.html` - gold-set annotator

Owner: Person B built it, Person A uses it. Task `S5-A1`.

Open `tools/annotate.html` by double-clicking it. No server, no build step, no network.
Everything stays in the browser and nothing is uploaded.

1. Load the curricula JSON files the pairs refer to (`data/curricula/*.json`).
2. Load the pairs: **Open CSV for in-place saving** in Chrome or Edge, so Save writes
   straight back to the file. Other browsers use the **Pairs CSV** button, and Save
   downloads a new copy.
   - Open **your half**: `data/gold/half_a_luka.csv` or `data/gold/half_b_aleksandar.csv`
     (see "Two people, two files" below). A half keeps the model's proposal and reason,
     so it can be closed and reopened as often as you like.
   - Without a split, start from `data/gold/llm_prelabels.csv`. The tool refuses to
     overwrite that file and asks where to write `gold_pairs.csv` instead, so the
     pre-labels stay frozen.
3. Judge each pair. `0` `1` `2` set the label, `Enter` accepts and moves on, the arrow
   keys move without deciding, `Ctrl+S` saves. Most pairs are obvious, so the usual
   action is one keystroke.
4. Save often. Progress is also kept in this browser's local storage as a backup, but
   that is a convenience, not the file.

The header shows how many rows are checked and how many you corrected. The correction
count is the number the report quotes, so it is worth watching as you go.

## Two people, two files

The 1142 pooled pairs are split between us so that each person labels in their own file
and git never has to merge the same CSV:

```bash
python scripts/split_gold.py   # once; already done, the halves are in data/gold/
python scripts/merge_gold.py   # any time: both halves -> gold_pairs.csv
```

- The split is by home course, so one person judges every candidate for a course.
- It is balanced on estimated time (a proposed 0 about 7 s, a 1 or 2 about 40 s), about
  two hours each. Aleksandar's half is smaller because he also labels the 30 cold pairs.
- All 30 cold pairs (`gold_pairs_b.csv`) are in Luka's half. **Aleksandar labels the cold
  pairs first**, before opening his half, so the model's way of judging is not in his
  head when he does them.
- Label in your half, save, then `python scripts/merge_gold.py`, and commit your half and
  `gold_pairs.csv` together. Partial progress is fine to push: the evaluation stays
  marked provisional until every row is checked.
- `merge_gold.py` refuses to write if a pair is missing, duplicated, or checked with two
  different labels, and `check_gold.py` in CI checks the same things.

Output columns: `home_uid,host_uid,label,checked` in `gold_pairs.csv`; the halves also
carry `llm_label` and `llm_reason` in front of `label`. Only `checked=yes` rows count in the
evaluation. Rubric and the reasoning behind the design: `docs/05-evaluation.md`.
