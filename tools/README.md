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
   - Start from `data/gold/llm_prelabels.csv`. The tool refuses to overwrite that file
     and asks where to write `gold_pairs.csv` instead, so the pre-labels stay frozen.
   - Resume from a part-finished `data/gold/gold_pairs.csv`.
3. Judge each pair. `0` `1` `2` set the label, `Enter` accepts and moves on, the arrow
   keys move without deciding, `Ctrl+S` saves. Most pairs are obvious, so the usual
   action is one keystroke.
4. Save often. Progress is also kept in this browser's local storage as a backup, but
   that is a convenience, not the file.

The header shows how many rows are checked and how many you corrected. The correction
count is the number the report quotes, so it is worth watching as you go.

Output columns: `home_uid,host_uid,label,checked`. Only `checked=yes` rows count in the
evaluation. Rubric and the reasoning behind the design: `docs/05-evaluation.md`.
