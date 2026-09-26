# data/

- `curricula/*.json` - one study programme per file. Schema: `docs/03-data-schema.md`.
  **Source of truth.** Committed to git. Never scraped at request time.
- `gold/llm_prelabels.csv` - the model's raw proposed labels. Written once, then frozen.
- `gold/half_a_luka.csv`, `gold/half_b_aleksandar.csv` - the two halves the pool was
  split into for checking; `scripts/merge_gold.py` joins them.
- `gold/gold_pairs.csv` - the evaluation set, 1142 rows, all with a final label. 680 were
  checked by a human, 462 labelled by a second model (Claude).
- `gold/provenance.json`, `gold/claude_labels_a.csv` - who produced which label.
- `gold/gold_pairs_b.csv` - Person B's cold slice, for Cohen's kappa.
- `partners.json` - the order programmes are listed in: home first, then ARWU band, then
  distance from Novi Sad.
- `calibration/*.json` - the fitted probability models, one per calibrated strategy.

  Schema for the gold files: `docs/03-data-schema.md` section Gold set.
  Protocol: `docs/05-evaluation.md`.
- `.cache/` - generated embedding caches (`*.npy`) and scraper downloads. Git-ignored,
  safe to delete.

Seven curriculum files, one scraper per institution in `backend/scripts/`, listed in the
order the app shows them:

| File | Courses | Source |
|---|---|---|
| `uns-pmf-informatics-bsc.json` | 50 | PMF programme page plus one syllabus PDF per course (home) |
| `epfl-cs-msc.json` | 78 | edu.epfl.ch coursebooks |
| `tudelft-cse-bsc.json` | 35 | TU Delft study guide API, 2026-2027 |
| `polimi-ecs-bsc.json` | 45 | Polimi English course catalogue, 2025-2026 |
| `kth-cs-msc.json` | 79 | KTH course API |
| `utwente-am-bsc.json` | 51 | Osiris JSON API, 2025-2026 |
| `utwente-tcs-bsc.json` | 40 | Osiris JSON API, 2025-2026 |

Only the two Twente programmes have gold labels, so they are the evaluation hosts.
